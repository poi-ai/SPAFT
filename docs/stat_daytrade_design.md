# Phase 3 統計ベースデイトレードRPA 詳細設計書

本ドキュメントは Issue #48 で実装した「統計ベースのエントリー条件を用いたデイトレードRPA(Phase 3 MVP)」の詳細設計を記述する。
実装で参照する戦略仕様は [`report/trading_playbook.md`](../report/trading_playbook.md) を真実の源泉とする。

---

## 1. 目的とスコープ

### 1.1 目的

Phase 2 (#47) の統計分析および #56 / #57 の追加検証で策定したエントリー/エグジット条件を、auカブコム証券 KabuStation API 経由で自動執行する RPA を構築する。

### 1.2 MVP スコープ

プレイブック §8 に従い、本 PR では **戦略B(RSI(9) < 10 で買い、30 分保有)** のみを実装する。

| 戦略 | エントリー | サイド | 保有時間 | 期待勝率 | 本MVP対応 |
|---|---|---|---|---|---|
| A | RCI(26) ≤ -80 | 買い | 15分 | 55.1% | ✕ |
| **B** | **RSI(9) < 10** | **買い** | **30分** | **61.1%** | **○** |
| C | PSY(12) < 10 | 買い | 30分 | 65.2% | ✕ |
| D | close < BB lower 2σ | 買い | 10分 | 52.4% | ✕ |
| E | BB下抜け AND RSI(9)≤10 | 買い | 30分 | 56.0% | ✕ |
| X | BB上抜け AND RSI≥80 AND RCI≥80 | 売り | 10分 | 62.0% | ✕ |
| W | close > BB upper 3σ | 売り | 5-10分 | 54-60% | ✕ |

### 1.3 段階追加対象(本 MVP では非対応)

- 戦略 A / C / D / E / X / W のシグナル条件
- 売り戦略(X/W)の建玉量上限(全建玉の 30%)
- サーキットブレーカー CB-1 / CB-2 / CB-3 / CB-4
- 複数銘柄の同時運用
- WebSocket PUSH 受信(現状は DB の OHLC を毎分ポーリングする方式)

---

## 2. ファイル構成

| ファイル | 区分 | 役割 |
|---|---|---|
| `src/stat_daytrade.py` | Controller(新規) | エントリースクリプト。`Base` を継承して起動 |
| `src/service/trade/stat_daytrade.py` | Service(新規) | `StatDaytrade` クラス本体。`Scalping` を継承 |
| `src/service/trade/__init__.py` | Service registry | `Trade.stat_daytrade` として `StatDaytrade` を登録 |
| `src/db/ohlc.py` | DB | リアルタイム指標計算用 `select_range()` を追加 |
| `src/config.py.sample` | Config | `STAT_*` パラメータを追加 |

### 2.1 アーキテクチャ上の位置付け

CLAUDE.md「Serviceクラス追加時」の手順に従い、`src/service/trade/` 配下に Trade Service として配置している。

```
src/stat_daytrade.py (Controller)
    ↓ 継承
src/base.py (Base)
    ↓ インスタンス生成
src/service/__init__.py (Service)
    ↓
src/service/trade/__init__.py (Trade)
    ↓
src/service/trade/stat_daytrade.py (StatDaytrade ← Scalping ← ServiceBase)
        ↓ 使用
        ├── KabusApi (注文/銘柄情報/余力)
        ├── Db.ohlc.select_range() (直近 OHLC)
        └── Util (indicator / stock_price / culc_time)
```

### 2.2 Scalping 継承の意図

`Scalping` クラスから以下を再利用するため継承している。

| 流用メソッド | 用途 |
|---|---|
| `get_margin_buy_power()` | 信用余力取得 |
| `get_symbol()` | 銘柄情報取得(銘柄登録上限のリカバリ込み) |
| `buy_order()` | 信用新規買い指値注文 |
| `enforce_management()` / `enforce_settlement()` | 強制成行決済(安全弁) |
| `get_today_order()` / `get_today_position()` | 注文・保有株一覧取得 |
| `board_analysis()` | 板情報の整形 |

**`param_check()` は `Scalping` のものをオーバーライド**し、本クラス専用の `STAT_*` パラメータを読み込む。

---

## 3. クラス設計: `StatDaytrade`

### 3.1 クラスツリー

```
ServiceBase (src/service_base.py)
    ↑ 継承
Scalping (src/service/trade/scalping.py)
    ↑ 継承
StatDaytrade (src/service/trade/stat_daytrade.py)
```

### 3.2 クラス変数

```python
STRATEGY_PARAMS = {
    'B': {
        'side': 'buy',
        'hold_minutes': 30,
        'sl_loss_pct': -0.007,   # SL-1: 含み損 -0.7%
        'rsi_threshold': 10,
    },
    # A/C/D/E/X/W は段階追加予定
}

STRATEGY_PRIORITY = ['B', 'C', 'E', 'A', 'D']  # プレイブック §4.1
```

### 3.3 インスタンス変数

| 変数 | 型 | 用途 |
|---|---|---|
| `enabled_strategies` | `list[str]` | `STAT_ENABLED_STRATEGIES` で指定された有効戦略 |
| `bb_width_filter` | `float` | 共通フィルタ。BB幅 / close の最低比率(既定 0.0036) |
| `position` | `dict` or `None` | 現在の建玉。`None` なら未保有 |
| `circuit_break_all` | `bool` | 全停止フラグ(将来の CB 用) |
| `disabled_strategies` | `set[str]` | 戦略単位の停止集合(将来の CB 用) |

#### 3.3.1 `position` の構造

```python
{
    'strategy':     'B',           # 戦略ID
    'entry_price':  1000.0,        # 約定価格(注文価格)
    'entry_time':   datetime(...), # エントリー時刻
    'qty':          100,           # 建玉株数
    'rsi_peak':     85.0,          # 保有中の RSI(9) 最大値(MS-1 判定用)
    'rci_at_entry': -90.0,         # エントリー時 RCI(26)(MS-3 判定用、将来戦略A/E)
}
```

> **複数銘柄対応への拡張余地**: `position` を `dict[stock_code, position_dict]` に変更すれば対応可能な構造としている。

### 3.4 メソッド一覧

| メソッド | 概要 |
|---|---|
| `__init__` | 親(`Scalping`)の初期化 + 本クラス専用変数の初期化 |
| `stat_daytrade_init(config)` | 起動時の初期処理。営業日/取引時間/銘柄情報/余力をチェック |
| `param_check(config)` | `STAT_*` 設定値の読み込みと検証(`Scalping` のオーバーライド) |
| `calc_realtime_indicators(symbol, end_time)` | 直近 60 本 OHLC から RSI(9)/RCI(26)/BB(20) の最新値を返す |
| `is_entry_window(now, hold_minutes)` | プレイブック §6 の時間帯フィルタ |
| `check_common_filter(indicators)` | 共通フィルタ(BB幅 Q3 以上)判定 |
| `evaluate_entry(indicators, now)` | エントリー条件判定。発火戦略を1件返す |
| `evaluate_exit(indicators, now)` | エグジット条件判定。`(should_exit, reason)` を返す |
| `run()` | メイン取引ループ |
| `_sleep_until_next_minute()` | 次の1分の頭まで待機 |

---

## 4. 主要メソッドの設計

### 4.1 `stat_daytrade_init(config)`

`Scalping.scalping_init()` をベースに、本クラス専用の起動前チェックを行う。

```
1. param_check() で設定値を読み込み
2. 営業日チェック (util.culc_time.exchange_date())
3. 取引時間チェック (exchange_time() != 5)
4. 信用余力取得 (get_margin_buy_power())
5. 優先市場コード取得 (api.info.primary_exchange)
6. 銘柄情報取得 (get_symbol)
   - デイトレ信用可否(KCMarginBuy)を確認
   - 売買単位/値幅上限/下限/呼値グループを保存
7. 呼値リスト作成 (util.stock_price.set_yobine_list)
8. 余力チェック(1単元購入可能か)
```

レート制限対策として API 連続呼び出しの間に `time.sleep(1)` を挿入する(KabuStation TIPS 準拠)。

### 4.2 `param_check(config)`

| Config 名 | 既定値 | 役割 |
|---|---|---|
| `STAT_TRADE_PASSWORD` | `TRADE_PASSWORD` を流用 | 取引パスワード |
| `STAT_STOCK_CODE` | `STOCK_CODE` を流用 | 取引対象銘柄 |
| `STAT_ENABLED_STRATEGIES` | `['B']` | 有効化する戦略リスト |
| `STAT_BB_WIDTH_MIN_RATIO` | `0.0036` | BB幅 / close の下限比 |

未実装戦略が `STAT_ENABLED_STRATEGIES` に含まれていた場合は警告ログを出して自動除外する(動作継続)。
有効戦略がゼロになった場合のみ `False` を返して起動失敗とする。

### 4.3 `calc_realtime_indicators(symbol, end_time)`

直近 N 件の OHLC からリアルタイム指標を計算する。

```
1. db.ohlc.select_range(symbol, end_time, n=60) で直近60本を取得
   - 行が21本未満なら指標計算不能 → 失敗を返す
2. close_price が NaN の行を除去
3. util.indicator のメソッドを順に呼び出し:
   - get_rsi(window=9, interval=1, price_column_name='close_price')
   - get_rci(window=26, interval=1, price_column_name='close_price')
   - get_bollinger_bands(window=20, interval=1, price_column_name='close_price')
4. 最新行(df.iloc[-1])から close / rsi9 / rci26 / bb_*sigma / bb_width を抽出
   - NaN は None に変換して返す
```

> **重要**: 遅行スパン(`lagging_span`)系および `pl_*` カラムは絶対に使用しない(#57 のリーク対応 / `report/indicator_leak_audit.md`)。

#### 戻り値 `indicators` の構造

```python
{
    'close':       float,
    'rsi9':        float | None,
    'rci26':       float | None,
    'bb_upper_2':  float | None,
    'bb_lower_2':  float | None,
    'bb_upper_3':  float | None,
    'bb_lower_3':  float | None,
    'bb_width':    float | None,
}
```

### 4.4 `is_entry_window(now, hold_minutes)`

プレイブック §6 の時間帯フィルタを実装。以下のいずれかに該当する場合は `False` を返す。

| 条件 | 理由 |
|---|---|
| `now.hour < 9` または `09:00〜09:30` | 寄付き直後の指標不安定 |
| `11:25〜11:30` | 前場引け跨ぎ |
| `12:00〜12:30` | 昼休み(WS切断)|
| `12:30〜12:35` | 後場寄付き直後の不安定 |
| `15:25〜` | 大引け前/CA |
| `16:00〜` | 取引時間外 |
| `now ≥ (15:25 - hold_minutes)` | 大引け跨ぎ防止(戦略保有時間で動的算出) |

### 4.5 `evaluate_entry(indicators, now)`

エントリー判定ロジック。

```
1. circuit_break_all == True → None
2. check_common_filter(indicators) == False → None
3. enabled_strategies を順に確認:
   - disabled_strategies に入っていればスキップ
   - is_entry_window(now, hold_minutes) で時間帯NGならスキップ
   - 戦略ごとのシグナル条件判定:
     * 戦略B: rsi9 が None でなく、rsi9 < 10
4. 候補を STRATEGY_PRIORITY 順に並べ、先頭の戦略IDを返す
```

### 4.6 `evaluate_exit(indicators, now)`

保有中の建玉に対し、以下の **優先順位順** に判定し、最初に該当した条件で即決済を返す(プレイブック §2 の「複数判定はしない」方針)。

| 順序 | ID | 条件 | 適用戦略 |
|---|---|---|---|
| 1 | SL-4 | `close < bb_lower_3sigma` | 買い |
| 2 | SL-1/2 | 含み損率 ≤ 戦略別閾値(B: -0.7%) | 買い |
| 3 | SL-6 | 保有時間 ≥ hold_minutes × 1.5(保険) | 全 |
| 4 | TP-1 | `close ≥ bb_upper_2sigma` | 買い |
| 5 | TP-2 | `rsi9 ≥ 80 AND rci26 ≥ 80` | 買い |
| 6 | TP-4 | 保有時間 ≥ hold_minutes / 2 AND 含み益 ≥ +0.1% | 買い |
| 7 | MS-1 | `rsi_peak ≥ 80` を経て現 RSI < 50 | 買い |
| 8 | 時間ストップ | 保有時間 ≥ hold_minutes | 全 |

毎呼び出し時に `position['rsi_peak']` を更新する(MS-1 用の状態保持)。

### 4.7 `run()`(メイン取引ループ)

```
無限ループ:
    now = NTPサーバーから現在時刻取得
    exch = exchange_time(now)

    [1] お昼休み(exch=4) → 12:30まで wait_time → continue
    [2] 大引け後(exch=5) または CA(exch=6):
            建玉あれば enforce_management → break
    [3] 15:25 到達:
            建玉あれば enforce_management → break
    [4] 11:28 以降の前場時間:
            建玉あれば enforce_management
            12:30まで wait_time → continue
    [5] 寄り前(exch=3) → 09:00まで wait_time → continue

    end_time = now の分の頭 - 1秒(直近1分のクローズが確定済み時刻)
    indicators = calc_realtime_indicators(stock_code, end_time)
    取得失敗 → 次の分まで sleep して continue

    if 保有中:
        should_exit, reason = evaluate_exit(indicators, now)
        if should_exit:
            log → enforce_management(trade_type=f'戦略エグジット({reason})')
            position = None
    else:
        sid = evaluate_entry(indicators, now)
        if sid is not None:
            ok, order_price = buy_order(stock_price=close)
            if ok: position を新規セット

    次の分まで _sleep_until_next_minute()
```

#### 例外時の安全弁

`run()` 全体を `try` で囲み、`finally` 節で `enforce_management(trade_type='ループ終了時クリーンアップ')` を呼ぶ。
これにより以下が担保される:

- 想定外例外で抜けても建玉が残らない
- KeyboardInterrupt などでも `finally` は実行される
- 二重決済になっても `enforce_settlement()` 内で「未約定 / 保有株あり」のチェックを行うため副作用は限定的

### 4.8 決済の方式

すべて `Scalping.enforce_management()` 経由で **成行決済** を行う(エグジット時/前場引け/15:25/例外時 共通)。

設計上、エグジットシグナル発火時点で次の分まで遅延させず即決済にすることで、シグナル消失や逆行を防ぐ意図がある。プレイブック §2 「最初に該当した条件で即決済」の方針と一致。

---

## 5. DB レイヤ追加: `Ohlc.select_range()`

```python
def select_range(self, symbol, end_time, n):
    '''
    指定銘柄について、end_time 以前の直近 N 件を返す
    
    Returns:
        result(bool)
        rows(list[dict]): trade_time 昇順
    '''
```

### 5.1 SQL

```sql
SELECT *
FROM ohlc
WHERE symbol = %s AND trade_time <= %s
ORDER BY trade_time DESC
LIMIT %s
```

降順で取得後、Python 側で逆順にして昇順で返却する(指標計算は時系列昇順が前提のため)。

### 5.2 想定 N

| 戦略 | 必要指標 | 必要本数 |
|---|---|---|
| B (MVP) | RSI(9) / BB(20) / RCI(26) | 26 + α |

`StatDaytrade.calc_realtime_indicators()` では余裕をもって **60 本** をデフォルトとする。
NaN 行や週またぎを考慮しても実用上十分。

---

## 6. 設定パラメータ

`src/config.py.sample` に以下を追加。

```python
###############################################
##  統計ベースデイトレRPA(Phase 3)関連設定値    ##
###############################################

# 取引対象の証券コード ※未設定の場合は STOCK_CODE を流用
STAT_STOCK_CODE = 1570

# 取引パスワード ※未設定の場合は TRADE_PASSWORD を流用
STAT_TRADE_PASSWORD = 'password'

# 有効化する戦略リスト(プレイブック §1)
# A: RCI(26) <= -80 買い15分 / B: RSI(9) < 10 買い30分(MVP) /
# C: PSY(12) < 10 買い30分 / D: BB下抜け 買い10分 / E: BB+RSI 買い30分 /
# X: BB上抜け+RSI+RCI 売り10分 / W: BB上3σ 売り5-10分
# MVP では戦略B のみ。それ以外は段階追加。
STAT_ENABLED_STRATEGIES = ['B']

# 共通エントリーフィルタ: BB幅/close の下限比率(プレイブック §1, 既定0.0036=BB幅Q3)
STAT_BB_WIDTH_MIN_RATIO = 0.0036
```

---

## 7. Controller(`src/stat_daytrade.py`)

```python
import config
from base import Base


class StatDaytradeMain(Base):
    def __init__(self):
        super().__init__()  # use_db=True, use_api=True
        self.logic = self.service.trade.stat_daytrade

    def main(self):
        self.log.info('SPAFT(統計デイトレRPA Phase3) 起動')

        # RECOVERY_SETTLEMENT で起動した場合は強制決済のみ実行して終了
        if getattr(config, 'RECOVERY_SETTLEMENT', False):
            stock_code = getattr(config, 'STAT_STOCK_CODE', None) or config.STOCK_CODE
            trade_password = getattr(config, 'STAT_TRADE_PASSWORD', None) or config.TRADE_PASSWORD
            self.logic.enforce_management(trade_type='単一', trade_password=trade_password, stock_code=stock_code)
            return True

        if not self.logic.stat_daytrade_init(config):
            return False

        self.logic.run()
        return True


if __name__ == '__main__':
    StatDaytradeMain().main()
```

### 7.1 起動方法

CLAUDE.md「実行コマンド」のルールに従い `src/` 内から実行する。

#### 前提: `ohlc_push_collector.py` の並列起動が必須

本スクリプトはリアルタイム指標(RSI / RCI / BB)を `ohlc` テーブルからの読み出しで計算する(`calc_realtime_indicators()` → `Ohlc.select_range()`)。`ohlc` テーブルへの1分足の継続書き込みは `ohlc_push_collector.py`(WebSocket PUSH)が担当しているため、**こちらを先に起動しておく必要がある**。コレクター未起動の場合、古いデータで指標を計算してしまうか、対象銘柄のレコードが0件でエラー終了する。

`config.RECORD_OHLC_STOCK_CODE_LIST` に `STAT_STOCK_CODE` が含まれているかも事前に確認すること。

```bash
# ターミナル1(先に起動)
cd src
python ohlc_push_collector.py

# ターミナル2(別ウィンドウ)
cd src
python stat_daytrade.py
```

### 7.2 注文種別

本スクリプトの発注は親 `Scalping.buy_order()` をそのまま継承しているため、以下の **一般信用デイトレード(信用デイトレ)** で発注される。

| パラメータ | 値 | 意味 |
|---|---|---|
| `cash_margin` | 2 | 新規 |
| `margin_trade_type` | **3** | **一般信用(デイトレ)** |
| `fund_type` | `'11'` | 信用取引 |
| `account_type` | 4 | 特定口座 |
| `deliv_type` | 0 | 指定なし |

現物・制度信用・一般信用長期は使用しない。auカブコム証券のデイトレ信用は手数料0円であり、当日中の決済が前提となる(`enforce_management()` で同種別の返済発注により決済)。

---

## 8. 安全性検証

### 8.1 `/check-trade-safety` 観点

| チェック項目 | 対応状況 |
|---|---|
| 株価計算で `price + N` を使っていないか | ✅ 全て `util.stock_price.get_updown_price()` 経由(`buy_order` は親 `Scalping` の実装をそのまま流用) |
| デイトレ信用の当日決済が担保されているか | ✅ 正常終了時(`break`) / 例外時(`finally`) / 大引け前(15:25) / 前場引け(11:28+) すべてで `enforce_management()` を呼ぶ |
| 遅行スパン関連カラムを使っていないか | ✅ `calc_realtime_indicators()` は RSI / RCI / BB のみで一目均衡表は使用しない |
| API レート制限対策 | ✅ 初期化フローに `time.sleep(1)` を挿入 |
| KabuStation 再起動時の挙動 | ✅ トークン無効化時は親 `Scalping` の例外伝播 → `finally` で決済 → プロセス終了の流れ(プレイブック CB-5 と一致) |

### 8.2 例外設計

- API エラー時は `self.log.error()` でログ出力後、可能な限り次のループへ継続
- 取り返しがつかない異常(`run()` 内の予期せぬ例外)は `error_output()` で LINE 通知 + `finally` で強制決済 + ループ終了

---

## 9. 単体テスト(実装時に検証済み、テストコードは未コミット)

実装時に一時テスト `src/test_stat_daytrade.py` を作成して以下を検証し、全件成功した。テストファイル自体は要件に従いコミットしていない。

| テスト | 内容 |
|---|---|
| `test_param_check` | 未実装戦略(A)が `STAT_ENABLED_STRATEGIES` に含まれていても自動除外される |
| `test_is_entry_window` | 09:25 / 09:35 / 11:25 / 12:00 / 12:34 / 12:36 / 14:55 / 15:25 の各境界で正しい判定 |
| `test_check_common_filter` | BB幅/close = 0.004 → True、0.003 → False、None → False |
| `test_evaluate_entry_strategy_b` | RSI=8 → 'B' / RSI=15 → None / BB幅不足 → None / circuit_break → None |
| `test_evaluate_exit_priority` | SL-4 / SL含み損 / TP-1 / TP-2 / TP-4 / MS-1 / 時間ストップ / 通常継続 |

> 環境制約により実行時は `db` / `kabusapi` モジュールをモックし、`importlib.util` で対象モジュールを直接ロードして検証した。

---

## 10. 既知の制約と段階追加項目

### 10.1 本 MVP の制約

1. **戦略B 単一**。A/C/D/E/X/W は未実装(`STRATEGY_PARAMS` に追加すれば容易に拡張可能な構造)
2. **単一銘柄**(`position` は単独 dict)
3. **DB ポーリング方式**。WebSocket PUSH での OHLC 受信は未対応 → `ohlc_push_collector.py` を別プロセスで動かしておくことで OHLC が継続的に DB へ書き込まれる前提
4. **サーキットブレーカー未実装**(CB-1〜CB-4)。CB-5/CB-6 は例外伝播 + `finally` 強制決済で実質担保
5. **リアルタイム約定価格でのエントリー**ではない。`calc_realtime_indicators()` で取得した `close`(直前1分の終値)を `buy_order` の基準価格として使う

### 10.2 段階追加(優先順)

1. 戦略 A (RCI(26)≤-80, 15分保有) — `STRATEGY_PARAMS['A']` 追加 + `evaluate_entry` 分岐
2. 戦略 E (BB+RSI, 30分保有) — 戦略B/D の中間
3. 戦略 X (売り建玉) — `Scalping.buy_order` のミラーで `sell_open` メソッド追加が必要
4. CB-1(当日 -3% で全停止) — `realized_pnl` の集計レイヤを追加
5. CB-2/CB-3(直近30シグナルの勝率計算) — 戦略単位の `disabled_strategies` 投入
6. 複数銘柄対応 — `position` を dict 化、`stock_code` のループ化、発注 200ms 間隔
7. WebSocket PUSH 統合 — `ohlc_push_collector.py` の購読ロジックを取り込み

---

## 11. 参照

- Issue #48 — Phase 3 デイトレードRPA
- [`report/trading_playbook.md`](../report/trading_playbook.md) — 真実の源泉
- [`report/trading_strategy_recommendations.md`](../report/trading_strategy_recommendations.md) — エントリー戦略の根拠
- [`report/trading_exit_strategy.md`](../report/trading_exit_strategy.md) — エグジット戦略の根拠
- [`report/indicator_leak_audit.md`](../report/indicator_leak_audit.md) — リーク監査(遅行スパン使用禁止の根拠)
- [`docs/statistic_daytrade_plan.md`](statistic_daytrade_plan.md) — Phase 1〜3 全体計画
- `CLAUDE.md` — コーディング規約 / アーキテクチャ制約 / ブランチ運用
