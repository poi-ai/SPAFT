# 統計ベース・デイトレードRPA 設計プラン

作成日: 2026-04-05

---

## 全体フェーズ構成

```
Phase 1: 分足データ収集
    └─ WebSocket PUSH → ohlc テーブル（複数銘柄・複数日）

Phase 2: 統計分析
    └─ ohlc テーブルからデータ取得 → テクニカル指標計算 → パターン抽出・条件策定

Phase 3: デイトレード RPA
    └─ 策定した条件 → リアルタイム判定 → 自動注文
```

---

## Phase 1: 分足データ収集

### REST ポーリング vs WebSocket PUSH

**WebSocket PUSH（`reception_websocket.py`）を使うべき。理由は以下。**

| 観点 | REST ポーリング | WebSocket PUSH |
|---|---|---|
| OHLC の精度 | ポーリング間隔内の動きが欠落する | 全約定を捕捉するため精度が高い |
| 複数銘柄への対応 | 銘柄数×頻度でレート上限（10件/秒）に当たる | 最大50銘柄まで追加 API コストなし |
| インフラ負荷 | 銘柄数が増えるほど負荷増大 | 受信側なので追加負荷がほぼない |
| 1分足 OHLC の蓄積 | 実装がない（boards に保存するだけ） | **既に実装済み** (`ohlc` テーブルへの upsert) |

### 現状の実装で何ができているか

`reception_websocket.py` を起動するだけで以下が動く:

```
python reception_websocket.py

→ config.RECORD_STOCK_CODE_LIST に列挙した銘柄を登録
→ 前場・後場の WebSocket PUSH 受信
→ 1分足 OHLC を ohlc テーブルに自動 upsert（分が変わるたびに確定）
```

**ohlc テーブルのスキーマ:**

| カラム | 型 | 内容 |
|---|---|---|
| `symbol` | str | 証券コード |
| `trade_time` | datetime | 取引分（秒を切り捨て） |
| `open_price` | float | 始値 |
| `high_price` | float | 高値 |
| `low_price` | float | 安値 |
| `close_price` | float | 終値 |
| `volume` | int | 当該分の出来高 |
| `total_volume` | int | 当日累積出来高 |
| `status` | int | ステータス（常に1） |

### 収集にあたって必要な設定変更

`src/config.py` を編集するだけ:

```python
# 収集対象銘柄を追加（最大50銘柄）
RECORD_STOCK_CODE_LIST = [1570, 9432, 9501, 8306, 7203, ...]

# WebSocket 用の設定は BOARD_RECORD_DEBUG を利用（既存フラグを流用）
BOARD_RECORD_DEBUG = False  # 本番: False（営業日判定あり）
```

### 既存実装の問題点（収集前に要修正）

前述のとおり `reception_websocket.py:17` にバグがある:

```python
# 現状（バグあり）
record_init = self.service.collect.record.record_init(...)
if record_init == False:   # タプルは常に truthy → 非営業日でもスルーされる
    return False

# 正しい形
result, target_code_list = self.service.collect.record.record_init(...)
if result == False:
    return False
```

このバグがあると非営業日でも WebSocket 接続を試みてエラーになるため、収集開始前に修正が必要。

### N分足への変換（5分・15分・30分・60分など）

`ohlc` テーブルに蓄積された1分足データから N 分足への変換は SQL で行える:

```sql
-- 例: 5分足に変換（trade_time を5分単位に切り捨て）
SELECT
    symbol,
    FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(trade_time) / 300) * 300) AS trade_time_5min,
    FIRST_VALUE(open_price)  OVER w AS open_price,
    MAX(high_price)          OVER w AS high_price,
    MIN(low_price)           OVER w AS low_price,
    LAST_VALUE(close_price)  OVER w AS close_price,
    SUM(volume)              OVER w AS volume
FROM ohlc
WHERE symbol = '1570'
WINDOW w AS (PARTITION BY symbol, FLOOR(UNIX_TIMESTAMP(trade_time) / 300) ORDER BY trade_time
             ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
```

または Python 側で pandas の `resample()` を使う方法もある（`board_mold.py` の実装パターンを参考）。

---

## Phase 2: 統計分析

### 方針

AI（機械学習）を使わず、**テクニカル指標＋統計的検証**によってエントリー条件を策定する。
具体的には「ある指標がある状態のとき、その後 X 分で Y 円以上上昇する確率は何%か」を過去データから集計する。

### 流用できる既存実装

#### `src/util/indicator.py` — テクニカル指標計算クラス（全て流用可能）

現在は CSV（板情報スナップショット）用途で実装されているが、**pandas DataFrame を受け取るインターフェースのため ohlc テーブルから読んだデータにもそのまま使える**。

| メソッド | 指標 | 引数の `price_column_name` を変える必要 |
|---|---|---|
| `get_sma(df, column_name, window_size, interval)` | 単純移動平均（SMA） | `'current_price'` → `'close_price'` に変更 |
| `get_ema(df, column_name, window_size, interval)` | 指数移動平均（EMA） | 同上 |
| `get_wma(df, column_name, window_size, interval)` | 加重移動平均（WMA） | 同上 |
| `get_ma_cross(df, interval)` | MAクロス・ゴールデン/デッドクロス | 上記3つを事前実行後に呼ぶ |
| `get_bollinger_bands(df, column_name, window_size, interval)` | ボリンジャーバンド（±3σ）| 同上 |
| `get_rsi(df, column_name, window_size, interval)` | RSI | 同上 |
| `get_rci(df, column_name, window_size, interval)` | RCI | 同上 |
| `get_psy(df, column_name, window_size, interval)` | サイコロジカルライン | 同上 |
| `get_parabolic(df, column_name, min_af, max_af, interval)` | パラボリックSAR | 同上 |
| `get_macd(df, column_name, short, long, signal, interval)` | MACD | 同上 |
| `get_ichimoku_cloud(df, column_name, short, long, interval)` | 一目均衡表 | 同上 |

**注意:** 全メソッドのデフォルト `price_column_name = 'current_price'` は板情報CSV用のカラム名。
ohlc テーブルから読んだ DataFrame で使う場合は `price_column_name='close_price'` を明示する必要がある。

呼び出し例:
```python
result, df = self.util.indicator.get_sma(
    df=ohlc_df,
    column_name='sma_5min_9piece',
    window_size=9,
    interval=5,
    price_column_name='close_price'   # ← ここを変えるだけ
)
```

#### `src/db/ohlc.py` — OHLC データ取得クラス

| メソッド | 用途 |
|---|---|
| `select()` | 全レコード取得 |
| `select_time(symbol, target_time)` | 指定時間のレコード取得 |
| `select_latest_total_volume(symbol, target_date)` | 指定日の最新累積出来高取得 |
| `upsert(ohlc_data)` | レコードの追加または更新 |

**不足しているメソッド（統計分析フェーズで追加が必要）:**

```python
# 指定期間のレコードを一括取得するメソッドが存在しない
# 以下のようなメソッドが必要になる想定
def select_range(self, symbol, start_time, end_time):
    '''指定銘柄の指定期間の全レコードを取得する'''
```

### 統計分析の流れ（実装イメージ）

```
1. ohlc テーブルから過去データを取得（select_range を追加して利用）
2. pandas DataFrame に変換
3. indicator.py で指標を追加
4. 「指標がある状態」を条件でフィルタ
5. その X 分後の価格変化を集計
6. 勝率・期待値・最大ドローダウンを計算
```

---

## Phase 3: デイトレード RPA

### 全体構造案

Phase 2 で策定した「エントリー条件」を組み込んだ新しい Controller クラスを作成する。
既存の `main.py` + `scalping.py` の構造を踏襲しつつ、以下を入れ替える:

```
現在の scalping.py:
  板情報を都度取得 → 固定の pip 幅で買い → トレールで利確/損切り

新しい RPA の構造案:
  分足 OHLC（WebSocket）を随時受信 → 指標を計算 → 統計ベースの条件でエントリー判断 → 注文
```

### 流用できる既存実装（Phase 3）

#### `src/service/trade/scalping.py` — 流用可能な処理一覧

| メソッド | 内容 | 流用方法 |
|---|---|---|
| `scalping_init()` | 初期処理（余力チェック・銘柄情報・呼値設定・規制確認） | **ほぼそのまま流用可能**。新クラスで継承または呼び出し |
| `get_margin_buy_power()` | 信用余力取得 | そのまま流用 |
| `board_analysis(board_info)` | 板情報から最良買気配・売気配・スプレッドを抽出 | 注文価格決定に流用 |
| `buy_order(stock_price)` | 指定 pips 下に指値買い注文 | エントリー時に流用（ORDER_LINE の意味が変わる可能性あり） |
| `sell_secure_order(qty, stock_price)` | 利確の売り注文 | そのまま流用 |
| `sell_cut_order(qty, order_price)` | 損切りの売り注文 | そのまま流用 |
| `enforce_management()` | 強制成行決済（前場終了・取引時間切れ時） | **必ず流用すべき**（時間管理の安全弁） |
| `param_check(config)` | 設定ファイルのパラメータ読み込み | 新しいパラメータを追加して流用 |

#### `src/util/stock_price.py` — 呼値計算（必須）

CLAUDE.md にある通り、`price + 1` は誤り。必ず以下を使う:

```python
result, price = self.util.stock_price.get_updown_price(
    stock_price=current_price,
    pips=N,
    updown=1  # 1: 上方向, 0: 下方向
)
```

以下のセットアップが `scalping_init()` の中で行われており、これを引き継ぐ必要がある:

```python
self.util.stock_price.set_yobine_group(stock_info['PriceRangeGroup'])
self.util.stock_price.set_yobine_list(lower_limit, upper_limit, PriceRangeGroup)
```

#### `src/util/culc_time.py` — 時刻管理（必須）

| メソッド | 用途 |
|---|---|
| `get_now(accurate=True)` | NTP 取得の正確な現在時刻 |
| `exchange_date()` | 営業日判定 |
| `exchange_time()` | 現在の時間種別（前場/後場/昼休み等） |
| `wait_time(hour, minute)` | 指定時刻まで待機 |

#### `src/kabusapi/order.py` — 注文 API

`buy_order()`, `sell_secure_order()`, `sell_cut_order()` が内部で使っている。
注文 API はこのクラスが薄くラップしているため、直接は触らない。

#### `src/db/orders.py`, `src/db/holds.py` — 注文・保有管理

`scalping.py` がこれを使って「現在の保有株・未約定注文の確認」を行っている。
デイトレ RPA でも同じテーブルを使う想定で問題ない。

### 新規実装が必要な処理

| 処理 | 理由 |
|---|---|
| エントリー条件判定ロジック | Phase 2 の統計結果次第で変わるため新規実装 |
| リアルタイム指標計算 | 現在の `indicator.py` は「蓄積データの一括バッチ処理」用で、リアルタイム計算には向いていない。直近 N 本を取得して計算するラッパーが必要 |
| 複数銘柄の同時管理 | `scalping.py` は1銘柄専用設計（`self.stock_code` が単一）。複数銘柄に対応するには銘柄ループ or 銘柄ごとのインスタンス管理が必要 |
| `ohlc.select_range()` | Phase 2 の統計分析で必要。`db/ohlc.py` に追加 |

---

## 流用できるもの・できないものの整理

### 流用できる（変更不要）

```
src/kabusapi/websocket.py       WebSocket接続
src/kabusapi/register.py        銘柄登録/解除
src/kabusapi/info.py:board()    板情報取得（注文価格決定用）
src/kabusapi/order.py           注文API
src/kabusapi/wallet.py          余力取得

src/service/collect/record.py   websocket_main(), operate_ohlc(), record_init()
src/service/trade/scalping.py   buy_order(), sell_*(), enforce_management(), scalping_init() の各メソッド

src/util/indicator.py           全テクニカル指標（price_column_name を変えるだけ）
src/util/stock_price.py         呼値計算（必須・変更不要）
src/util/culc_time.py           時刻管理全般
src/util/file_manager.py        ログ・CSV出力

src/db/ohlc.py                  OHLC テーブル操作（select_range 追加が必要）
src/db/orders.py                注文テーブル操作
src/db/holds.py                 保有テーブル操作
src/db/buying_power.py          余力テーブル操作

src/reception_websocket.py      データ収集フェーズはこれをそのまま使用
src/base.py                     初期化チェーン
src/service_base.py             Service 基底クラス
```

### 変更が必要なもの

```
src/reception_websocket.py
  → record_init の戻り値処理バグを修正（非営業日判定が効かない）

src/util/indicator.py
  → price_column_name のデフォルト値は 'current_price'（CSV用）のため
    ohlc テーブル用途では呼び出し時に 'close_price' を明示する必要あり
    （コード変更は不要・呼び出し方の問題）
```

### 新規作成が必要なもの

```
src/db/ohlc.py に select_range() メソッドを追加
  → 指定銘柄・指定期間のOHLCを一括取得（統計分析で必要）

統計分析スクリプト（src/analytics/ 配下が適切）
  → ohlc → pandas → indicator → 勝率/期待値計算 → 条件をパラメータとして出力

デイトレードRPAのメインロジック（src/service/trade/ 配下が適切）
  → エントリー条件判定 + scalping.py の注文メソッドを組み合わせ

デイトレードRPAの起動スクリプト（src/ 直下）
  → main.py 同様のエントリーポイント
```

---

## フェーズ間の依存関係まとめ

```
[Phase 1 完了条件]
  ・reception_websocket.py のバグ修正
  ・RECORD_STOCK_CODE_LIST に収集対象銘柄を設定
  ・数週間〜数ヶ月の実稼働でohlcテーブルにデータを蓄積
         ↓
[Phase 2 完了条件]
  ・ohlc.select_range() の追加
  ・indicator.py を close_price ベースで呼び出す分析スクリプト作成
  ・統計的に有意なエントリー条件をパラメータとして確定
         ↓
[Phase 3 完了条件]
  ・scalping.py の各注文メソッドを流用しつつ
    エントリー条件を差し替えた新しい Trade クラスを実装
  ・デイトレード条件に合った config.py パラメータ追加
```
