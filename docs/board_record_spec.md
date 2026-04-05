# 板情報取得処理 調査レポート

作成日: 2026-04-05

---

## 概要

KabuStation REST API `/board` エンドポイントをポーリングする方式で板情報を取得し、DB または CSV に記録する。
WebSocket PUSH 配信で板情報を受信して OHLC（四本値）に変換し DB に記録する処理も存在する。

---

## 1. Pythonコマンドからの呼び出し方法

### 板情報記録（REST APIポーリング）

```bash
cd src
python board_record.py
```

**設定項目（`src/config.py`）:**

| 設定名 | 型 | 説明 |
|---|---|---|
| `RECORD_STOCK_CODE_LIST` | list | 記録対象の証券コードリスト（例: `[1570, 9432, 7203]`） |
| `BOARD_RECORD_DB` | int | `1`: DBに記録、`0`: CSVに記録 |
| `BOARD_RECORD_MODE` | int | `1`: 1秒ごと、`2`: 1分ごと、`3`: 1回のみ |
| `BOARD_RECORD_DEBUG` | bool | `True`: デバッグモード（営業日判定・時刻チェックをスキップ） |
| `BOARD_RECORD_DEBUG_END_TIME` | str | デバッグモード終了時刻（例: `'14:50'`） |

**処理フロー:**

```
BoardRecord.__init__()
  └─ Base.__init__(use_db=True/False)
       ├─ Log, Util 初期化
       ├─ KabusApi 初期化 → POST /token でトークン取得
       ├─ Db 初期化 → MySQL 接続（BOARD_RECORD_DB==1 の場合のみ）
       └─ Service 初期化
            └─ Collect 初期化
                 └─ Record 初期化

BoardRecord.main()
  └─ ループ
       ├─ 時刻チェック（前場前/昼休み/大引け後に待機）
       ├─ 銘柄ごとに GET /board/{証券コード}@{市場コード}
       ├─ BOARD_RECORD_DB == 1 → response_to_boards() → boards テーブルに INSERT
       └─ BOARD_RECORD_DB == 0 → response_to_csv() → csv/{YYYYMMDD}_{証券コード}.csv に追記
            └─ 終了後 board_mold.main() で指標計算・CSV成形
```

---

## 2. 取得できる情報と保存形式

### 2-A. DB保存（`boards` テーブル）

**テーブル:** `spaft.boards`
**関連ファイル:** `src/db/board.py`, `sql/ddl/boards.sql`
**データ変換:** `src/util/mold.py:response_to_boards()`

| カラム名 | DB型 | 説明 | 変換処理 |
|---|---|---|---|
| `id` | INT AUTO_INCREMENT | プライマリキー | 自動 |
| `stock_code` | VARCHAR(4) | 証券コード | `Symbol` そのまま |
| `market_code` | VARCHAR(1) | 市場コード（1=東証） | `Exchange` そのまま |
| `price` | FLOAT(7,1) | 現在株価 | `CurrentPrice` そのまま |
| `latest_transaction_time` | DATETIME | 直近約定時刻 | `CurrentPriceTime` の `+09:00` を除去（未約定時は NULL） |
| `change_status` | VARCHAR(2) | 価格変動ステータス | `CurrentPriceChangeStatus[2:]`（先頭2文字削除） |
| `present_status` | VARCHAR(2) | 現在ステータス（1〜23） | `CurrentPriceStatus` そのまま |
| `market_buy_qty` | BIGINT(11) | 買成行数量 | `MarketOrderBuyQty` そのまま |
| `buy1_sign` | VARCHAR(3) | 最良買気配フラグ | `Buy1['Sign'][1:]`（先頭1文字削除） |
| `buy1_price`〜`buy10_price` | FLOAT(9,1) | 買気配値段 1〜10段目 | `Buy{N}['Price']` |
| `buy1_qty`〜`buy10_qty` | BIGINT(11) | 買気配数量 1〜10段目 | `Buy{N}['Qty']` |
| `market_sell_qty` | BIGINT(11) | 売成行数量 | `MarketOrderSellQty` そのまま |
| `sell1_sign` | VARCHAR(3) | 最良売気配フラグ | `Sell1['Sign'][1:]`（先頭1文字削除） |
| `sell1_price`〜`sell10_price` | FLOAT(9,1) | 売気配値段 1〜10段目 | `Sell{N}['Price']` |
| `sell1_qty`〜`sell10_qty` | BIGINT(11) | 売気配数量 1〜10段目 | `Sell{N}['Qty']` |
| `over_qty` | BIGINT(11) | OVER売気配数量 | `OverSellQty` そのまま |
| `under_qty` | BIGINT(11) | UNDER買気配数量 | `UnderBuyQty` そのまま |
| `created_at` | TIMESTAMP | レコード追加時刻 | 自動（CURRENT_TIMESTAMP） |

> **注意:** `buy2_sign`〜`buy10_sign` および `sell2_sign`〜`sell10_sign` はDBには保存されない（1段目のみ保存）。

---

### 2-B. CSV保存

**出力先（生CSV）:** `csv/{YYYYMMDD}_{証券コード}.csv`（追記モード）
**成形後:** `csv/formatted/{YYYYMMDD}_{証券コード}_new.csv`
**バックアップ:** `csv/bak/{YYYYMMDD}_{証券コード}.csv` → 7z圧縮

**関連ファイル:** `src/util/mold.py:response_to_csv()`, `src/service/preprocess/board_mold.py`

#### 生CSV列一覧

| カラム名 | 内容 |
|---|---|
| `stock_code` | 証券コード |
| `current_price` | 現在株価 |
| `current_price_change_status` | 価格変動ステータス（完全形、DBより2文字多い） |
| `current_price_status` | 現在ステータス |
| `previous_close` | 前日終値 |
| `change_previous_close` | 前日比 |
| `change_previous_close_per` | 騰落率(%) |
| `opening_price` | 始値 |
| `high_price` | 高値 |
| `high_price_time` | 高値時刻（`YYYY-MM-DD HH:MM:SS` 形式） |
| `low_price` | 安値 |
| `low_price_time` | 安値時刻（`YYYY-MM-DD HH:MM:SS` 形式） |
| `trading_volume` | 出来高 |
| `VWAP` | 売買高加重平均価格 |
| `bid_sign` | 最良売気配フラグ（完全形） |
| `market_order_sell_qty` | 売成行数量 |
| `bid_price_1`〜`bid_price_10` | 売気配値段 1〜10段目 |
| `bid_qty_1`〜`bid_qty_10` | 売気配数量 1〜10段目 |
| `over_sell_qty` | OVER売気配数量 |
| `ask_sign` | 最良買気配フラグ（完全形） |
| `market_order_buy_qty` | 買成行数量 |
| `ask_price_1`〜`ask_price_10` | 買気配値段 1〜10段目 |
| `ask_qty_1`〜`ask_qty_10` | 買気配数量 1〜10段目 |
| `under_buy_qty` | UNDER買気配数量 |
| `get_year` | 取得年 |
| `get_month` | 取得月 |
| `get_day` | 取得日 |
| `get_hour` | 取得時 |
| `get_minute` | 取得分 |

#### 成形後CSVに追加されるカラム（`board_mold.py:create_param()`）

対象時間足: 1, 3, 5, 10, 15, 30, 60, 90, 120, 240分

| カテゴリ | 追加カラム例 |
|---|---|
| 増減率・増減幅・増減フラグ | `change_1min_rate`, `change_1min_diff`, `change_1min_flag`, ... |
| SMA（単純移動平均） | `sma_1min_3piece`, `sma_1min_5piece`, ... |
| EMA（指数移動平均） | `ema_1min_3piece`, ... |
| WMA（加重移動平均） | `wma_1min_3piece`, ... |
| ボリンジャーバンド | `bb_1min_3piece_upper`, `bb_1min_3piece_lower`, ... |
| RSI | `rsi_1min_9piece`, `rsi_1min_14piece`, ... |
| RCI | `rci_1min_9piece`, ... |
| サイコロジカルライン | `psy_1min_10piece`, ... |
| パラボリックSAR | `sar_1min_0.01_0.1af`, `sar_1min_0.02_0.2af`, ... |
| MACD | `macd_1min`, `macd_1min_signal`, ... |
| 一目均衡表（1〜5分足のみ） | `ichimoku_1min_tenkan`, `ichimoku_1min_kijun`, ... |

> 間隔×本数が150を超える組み合わせは計算対象外（データが少なすぎるため）。
> 60分足以上はSMA/EMA/WMA/BB/RSI/RCI/PSY/SAR/MACD等は追加されない。

---

### 2-C. WebSocket PUSH配信 → `ohlc` テーブル

`board_record.py` からは直接呼ばれず、`main.py` 経由で利用される。

**関連ファイル:** `src/service/collect/record.py:websocket_main()`, `operate_ohlc()`
**保存先テーブル:** `spaft.ohlc`

PUSH配信で受信した板情報（REST `/board` と同じJSONフォーマット）を、秒を切り捨てた1分単位でOHLCに集計してメモリに保持し、分が変わるタイミングでDBに upsert する。

---

## 3. コード依存関係 全件調査

### import チェーン（`board_record.py` 起点）

```
board_record.py
 ├─ import config                               ✅ src/config.py
 ├─ from base import Base                       ✅ src/base.py
 │    ├─ from util import Util                  ✅ src/util/__init__.py
 │    │    ├─ util/common.py                    ✅
 │    │    ├─ util/culc_time.py                 ✅
 │    │    ├─ util/file_manager.py              ✅
 │    │    ├─ util/indicator.py                 ✅
 │    │    ├─ util/mold.py                      ✅
 │    │    └─ util/stock_price.py               ✅
 │    ├─ from util.log import Log               ✅ src/util/log.py
 │    ├─ from kabusapi import KabusApi          ✅ src/kabusapi/__init__.py
 │    │    ├─ from .auth import Auth            ✅ src/kabusapi/auth.py
 │    │    ├─ from .info import Info            ✅ src/kabusapi/info.py
 │    │    ├─ from .order import Order          ✅ src/kabusapi/order.py
 │    │    ├─ from .register import Register    ✅ src/kabusapi/register.py
 │    │    ├─ from .wallet import Wallet        ✅ src/kabusapi/wallet.py
 │    │    └─ from .websocket import Websocket  ✅ src/kabusapi/websocket.py
 │    ├─ from db import Db                      ✅ src/db/__init__.py
 │    └─ from service import Service            ✅ src/service/__init__.py
 │         └─ Collect                          ✅ src/service/collect/__init__.py
 │              └─ Record                      ✅ src/service/collect/record.py
 │                   ├─ import websockets       ✅ サードパーティ
 │                   ├─ import pytz             ✅ サードパーティ
 │                   └─ from service_base import ServiceBase ✅ src/service_base.py
 └─ service.preprocess.board_mold              ✅ src/service/preprocess/board_mold.py
      └─ import pandas as pd                   ✅ サードパーティ
```

### サードパーティライブラリ一覧

| ライブラリ | 用途 | 使用ファイル |
|---|---|---|
| `requests` | REST API呼び出し（HTTP） | `kabusapi/auth.py`, `info.py`, `register.py`, `wallet.py` |
| `websockets` | WebSocket接続 | `kabusapi/websocket.py`, `service/collect/record.py` |
| `pytz` | タイムゾーン変換（JST） | `service/collect/record.py` |
| `pandas` | CSV読み書き・指標計算 | `service/preprocess/board_mold.py` |

---

## 4. バグ・問題点 一覧

### 🔴 バグ（動作に影響あり）

#### Bug-1: `self` の二重渡し（再帰呼び出しのシグネチャ崩れ）

- **ファイル:** `src/service/collect/record.py:322`
- **現状コード:**
  ```python
  result, board_info = self.info_board(self, stock_code, market_code = market_code, add_info = add_info, retry_count = 1)
  ```
- **問題:** Python のメソッド呼び出しでは `self` は自動バインドされる。ここで第1引数に `self` を明示渡しすると、シグネチャが1つずれる。具体的には `stock_code` パラメータに `self` オブジェクトが渡り、APIリクエストURLが `.../{<Record object>}@1` のような不正な値になる。
- **正しい呼び出し:**
  ```python
  result, board_info = self.info_board(stock_code, market_code = market_code, add_info = add_info, retry_count = 1)
  ```
- **影響範囲:** 銘柄登録数上限エラー（エラーコード `4002006`）が発生したときのリトライ処理が完全に機能しない。通常50銘柄以下の運用であれば `4002006` は発生しないため、普段は問題にならない。

---

#### Bug-2: リトライ後のエラー判定ミス

- **ファイル:** `src/service/collect/record.py:323`
- **現状コード:**
  ```python
  if board_info == False:
      return False, board_info
  ```
- **問題:** `board_info` にはリトライ成功時は `dict`、失敗時は `int`（エラーコード）が入る。`dict == False` は常に `False`（=判定がすり抜ける）。チェックすべきは `result` の値。
- **正しい判定:**
  ```python
  if result == False:
      return False, board_info
  ```
- **影響範囲:** Bug-1 と同じくリトライ処理の中にあるため、影響は `4002006` エラー発生時のみ。

---

### 🟡 問題（動作はするが不完全）

#### Issue-1: 銘柄登録失敗時にリストから除外されない（TODO 残存）

- **ファイル:** `src/service/collect/record.py:70`
- **現状コード:**
  ```python
  if result != True: ## TODO ここで失敗したコードをインスタンス変数から除く
      self.log.error(f'銘柄登録処理でエラー\n{result}')
      continue
  ```
- **問題:** PUSH 配信モード（`push_mode=True`）で銘柄登録に失敗した銘柄を `target_code_list` から除かないため、その後の受信処理でも無効な銘柄に対して処理を試み続ける可能性がある。
- **影響範囲:** `websocket_main()` を使う PUSH 配信モードのみ。`board_record.py` の REST ポーリングモードでは `push_mode=False` のため影響なし。

---

#### Issue-2: `import time` と `from datetime import time` の名前衝突

- **ファイル:** `src/kabusapi/websocket.py:3,6`
- **現状コード:**
  ```python
  import time                                  # line 3: 標準ライブラリの time モジュール
  ...
  from datetime import datetime, time          # line 6: datetime.time クラスで上書き
  ```
- **問題:** line 6 の `time` が line 3 の `time` モジュールを上書きする。現状このファイル内で `time.sleep()` 等は呼ばれていないため実害はないが、将来的にスリープ処理を追加した場合 `TypeError: 'type' object is not callable` になる。
- **対処案:** `from datetime import datetime as dt_datetime, time as dt_time` のようにエイリアスを使う、または `import time` を削除する（このファイルでは未使用のため）。

---

#### Issue-3: `board_mold.py:read_csv()` の戻り値不整合

- **ファイル:** `src/service/preprocess/board_mold.py:92`
- **現状コード:**
  ```python
  # 正常時
  return True, board_df
  # エラー時
  return None, False
  ```
- **問題:** エラー時の第1要素が `None` であり `False` ではない。呼び出し元 `main()` では `if result == False:` でチェックしているため、`None` は `False` と等価でなく（`None == False` は `False`）、エラーが発生しても `continue` されずに `board_df = False` で次処理に進んでしまう。
- **正しい戻り値:**
  ```python
  return False, None
  ```

---

### 🟢 コメント残存（機能への影響なし）

#### Memo-1: `db/board.py` の意味不明な TODO コメント

- **ファイル:** `src/db/board.py:80`
- **現状:** `# TODO TODO TODO TODO TODO TODO` というコメントが残っているが、処理自体は実装済み。削除して問題なし。

---

## 5. 動作可否サマリー

| 処理 | 可否 | 備考 |
|---|---|---|
| REST ポーリング → DB保存（`BOARD_RECORD_DB=1`） | ✅ 動作する | Bug-1/2 は `4002006` エラー時のみ影響 |
| REST ポーリング → CSV保存（`BOARD_RECORD_DB=0`） | ✅ 動作する | |
| CSV後処理（`board_mold`）| △ ほぼ動作する | Issue-3: CSVが読めない場合でも処理継続するリスクあり |
| WebSocket PUSH → `ohlc` 保存 | ✅ 動作する | Issue-1/2 は現状実害なし |
| 銘柄登録上限エラー（`4002006`）時のリトライ | ❌ 動作しない | Bug-1/2 が原因 |
