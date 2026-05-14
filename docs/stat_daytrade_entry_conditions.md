# 統計デイトレRPA(Phase 3 MVP) エントリー条件 詳細仕様

本ドキュメントは `src/service/trade/stat_daytrade.py` における **戦略B(RSI(9)<10 で買い、30分保有)** のエントリー条件を、判定順に詳細記述する。
全体設計は [`stat_daytrade_design.md`](stat_daytrade_design.md)、戦略仕様の根拠は [`../report/trading_playbook.md`](../report/trading_playbook.md) を参照。

---

## 概要

エントリー判定は `evaluate_entry(indicators, now)` で行う。以下の **6 ステップを順に評価し、全てパスした戦略のみ** をエントリー候補とする。MVP では戦略B のみ実装しているため、候補は最大1件。

| # | 条件 | 判定箇所 | MVP デフォルト |
|---|---|---|---|
| 1 | サーキットブレーカー全停止チェック | `evaluate_entry` 冒頭 | 常にパス(未実装) |
| 2 | 共通フィルタ:BB幅 / close ≥ 閾値 | `check_common_filter` | 0.36%以上 |
| 3 | 戦略単位停止チェック | `evaluate_entry` ループ内 | 常にパス(未実装) |
| 4 | 時間帯フィルタ | `is_entry_window` | 09:30〜14:54(昼休み除く) |
| 5 | 戦略B シグナル:RSI(9) < 10 | `evaluate_entry` ループ内 | RSI<10 |
| 6 | 優先順位選択 | `STRATEGY_PRIORITY` | MVP では影響なし |

`[エントリー判定]` ログで `=> ○` が出るのは、上記 5 つ(優先順位は単独候補のため除外)が全て ○ になった瞬間。

---

## 1. サーキットブレーカー全停止(CB全停止)

### 該当コード

```python
if self.circuit_break_all:
    return None
```

### 判定内容

- インスタンス変数 `circuit_break_all`(bool)が True の場合、全戦略のエントリーを禁止する
- フラグが立つと、共通フィルタ以降の判定をスキップして即 `None` を返す

### MVP での挙動

- `__init__` で `False` 固定。**判定ロジックがどこからも True にしないため、常にパス**
- 将来の段階追加項目: プレイブック CB-1〜CB-4(当日 -3% 損失で全停止 等)を実装する際に True へ切り替える想定

### 解除方法

- 現状はプロセス再起動でしか戻らない
- 将来の管理 UI / API 追加でランタイム解除を予定

---

## 2. 共通フィルタ:BB幅 / close ≥ 0.36%

### 該当コード

```python
def check_common_filter(self, indicators):
    if indicators.get('bb_width') is None or indicators.get('close') in (None, 0):
        return False
    ratio = indicators['bb_width'] / indicators['close']
    return ratio >= self.bb_width_filter
```

### 判定内容

- **BB幅(`bb_width`) を直近終値(`close`) で割ったボラティリティ比率** が下限値以上であることを要求する
- `bb_width = BB上2σ - BB下2σ`(直近20本ベース、σ=2)
- 比率が下限未満なら凪相場とみなしエントリー禁止

### 設定値

| 設定キー | 既定値 | 意味 |
|---|---|---|
| `STAT_BB_WIDTH_MIN_RATIO` | `0.0036`(=0.36%) | BB幅 / close の下限比率 |

### 根拠

- Phase 2(#47) のバックテストで「BB幅/close が Q3(上位四分位)以上の場面でのみ統計的優位性が確認」された
- プレイブック §1 の共通エントリーフィルタに対応
- 既定 0.0036 は対象銘柄(NEXT FUNDS Nikkei 225 Leveraged ETF: 1570)の BB幅 Q3 と一致

### 失敗ケース

- `bb_width` が None(BB計算不能、データ20本未満等) → False
- `close` が None または 0(異常値) → False

### 計算例

```
close = 54830
bb_upper_2sigma = 55100
bb_lower_2sigma = 54600
bb_width = 500
ratio = 500 / 54830 = 0.00912 = 0.912%
0.912% >= 0.36% → ○(パス)
```

---

## 3. 戦略単位停止チェック(disabled_strategies)

### 該当コード

```python
for sid in self.enabled_strategies:
    if sid in self.disabled_strategies:
        continue
```

### 判定内容

- `disabled_strategies`(set)に戦略IDが含まれていれば、その戦略のみエントリー禁止
- 全停止(CB全停止)とは別レイヤで、特定戦略のみ無効化する仕組み

### MVP での挙動

- `__init__` で空 set 固定。**判定ロジックがどこからも追加しないため、常にパス**
- 将来の段階追加項目: プレイブック CB-2/CB-3(直近30シグナルの戦略勝率が閾値未満)を実装する際に投入する想定

---

## 4. 時間帯フィルタ(is_entry_window)

### 該当コード

```python
def is_entry_window(self, now, hold_minutes):
    h, m = now.hour, now.minute
    # 寄り直後 09:00〜09:30 は全戦略禁止
    if h < 9 or (h == 9 and m < 30):
        return False
    # 前場引け前 11:25〜11:30 禁止
    if h == 11 and m >= 25:
        return False
    # 昼休み 11:30〜12:30 禁止
    if h == 12 and m < 30:
        return False
    # 後場寄付き 12:30〜12:35 禁止
    if h == 12 and m < 35:
        return False
    # 15:25 以降禁止
    if h == 15 and m >= 25:
        return False
    if h >= 16:
        return False
    # 大引け 15:25 から hold_minutes 引いた時刻以降は新規禁止
    cutoff = now.replace(hour=15, minute=25, second=0, microsecond=0) - timedelta(minutes=hold_minutes)
    if now >= cutoff:
        return False
    return True
```

### 判定内容

戦略の保有時間 `hold_minutes` を引数に取り、以下のいずれかに該当すれば `False`(エントリー禁止)を返す。

| 区分 | 時間帯 | 理由 |
|---|---|---|
| 寄付き直後 | `now < 09:30` | 寄付き直後30分は指標が不安定で偽シグナル多発 |
| 前場引け直前 | `11:25 ≤ now < 11:30` | 前場引け5分前以降は新規禁止 |
| 昼休み | `12:00 ≤ now < 12:30` | (冗長な防御)昼休み中は KabuStation の WS 切断 |
| 後場寄付き直後 | `12:30 ≤ now < 12:35` | 後場寄付き5分間は不安定 |
| 大引け前/CA | `15:25 ≤ now` | 大引け前/クロージング・オークション |
| 取引時間外 | `now ≥ 16:00` | 営業時間外 |
| **保有時間バックオフ** | `now ≥ (15:25 - hold_minutes)` | 大引けまでに保有時間を消化できないため |

### 戦略B での実質エントリー可能時間

`hold_minutes = 30` を代入すると、バックオフが `15:25 - 30分 = 14:55` となる。

- **前場**: 09:30 〜 11:24(11:25 で禁止になる)
- **後場**: 12:35 〜 14:54(14:55 で禁止になる)

合計エントリー可能時間: 1時間55分(前場) + 2時間20分(後場) = **約4時間15分/日**

### 根拠

- プレイブック §6 の時間帯フィルタ定義に準拠
- 寄付き直後/引け直前/昼休み前後は Phase 2 のバックテストで損失過多
- 大引け跨ぎは戦略の前提(時間ストップ決済)が壊れるため強制バックオフ

---

## 5. 戦略B 個別シグナル:RSI(9) < 10

### 該当コード

```python
if sid == 'B':
    rsi = indicators.get('rsi9')
    if rsi is not None and rsi < self.STRATEGY_PARAMS['B']['rsi_threshold']:
        candidates.append('B')
```

### 判定内容

- 直近9本の終値から計算した **RSI(9) が 10未満** であることを要求する
- RSI が None(計算不能、データ9本未満等)なら判定スキップ(False 扱い)

### 設定値

| 設定キー | 既定値 | 意味 |
|---|---|---|
| `STRATEGY_PARAMS['B']['rsi_threshold']` | `10` | RSI(9) のエントリー閾値(これ未満でシグナル発火) |

> このパラメータはコード側のクラス変数で、`config.py` からは変更不可。閾値変更時はコード修正が必要。

### RSI(9) の計算方法

- 直近9本の **値上がり幅平均 / (値上がり幅平均 + 値下がり幅平均) × 100**
- 0〜100 の範囲を取る
- 一般的には:
  - **70以上**: 買われすぎ
  - **30以下**: 売られすぎ
- 戦略B は **10未満** という極端な売られすぎゾーンを狙う

### 根拠(Phase 2 検証結果)

| 指標 | 値 |
|---|---|
| 勝率 | **61.1%** |
| 期待値 | プラス |
| 1トレード平均リターン | +0.15%(SL/TP込み) |
| 保有時間 | 30分(時間ストップ) |

- 短期RSIの極端な売られすぎは、過剰反応によるテクニカル反発を捉えやすいというリバーサル戦略
- プレイブック §1 / §8 で MVP 採用が決定

### 戦略B 以外の判定(段階追加対象)

`enabled_strategies` に未実装戦略(A/C/D/E/X/W)が含まれていても、`param_check` で警告を出して自動除外するため、ここには到達しない。

---

## 6. 優先順位選択(STRATEGY_PRIORITY)

### 該当コード

```python
STRATEGY_PRIORITY = ['B', 'C', 'E', 'A', 'D']

if not candidates:
    return None

for sid in self.STRATEGY_PRIORITY:
    if sid in candidates:
        return sid
return candidates[0]
```

### 判定内容

- 候補リスト(`candidates`)に複数戦略が並んだ場合、**勝率順** で1件のみ選択する
- 順序: B(61.1%) → C(65.2%) → E(56.0%) → A(55.1%) → D(52.4%)
  - C は勝率最高だが MVP 未実装。実装次第繰り上がる
  - 順序の根拠は Phase 2 統計の勝率と期待値

### MVP での挙動

- 候補に上がるのは戦略B のみ → **常に B が選択される**
- 段階追加で A/C/D/E が候補に入った時に意味を持つ

---

## 全条件のフロー図

```
[毎分ループ]
   ↓
calc_realtime_indicators() で指標計算
   ↓
log_indicator_status() で現状ログ出力
   ↓
evaluate_entry(indicators, now)
   ├─ ① circuit_break_all == True ?  ──Yes──> return None
   │      No
   │      ↓
   ├─ ② check_common_filter() == False ?  ──Yes──> return None
   │      No(BB幅 / close >= 0.36%)
   │      ↓
   ├─ enabled_strategies(=['B']) を順に判定
   │      ↓
   │   ┌──────────────────────────────┐
   │   │ ③ sid in disabled_strategies?    │ ──Yes──> continue
   │   │      No                          │
   │   │      ↓                           │
   │   │ ④ is_entry_window(now, 30) ?    │ ──No───> continue
   │   │      Yes(時間帯OK)                │
   │   │      ↓                           │
   │   │ ⑤ rsi9 != None and rsi9 < 10 ?  │ ──No───> continue
   │   │      Yes(売られすぎ)              │
   │   │      ↓                           │
   │   │ candidates.append('B')           │
   │   └──────────────────────────────┘
   │      ↓
   ├─ ⑥ candidates が空 ?  ──Yes──> return None
   │      No
   │      ↓
   └─ STRATEGY_PRIORITY 順に1件返す → 'B'
            ↓
[エントリー実行]
   1. board API で最良買気配を取得
   2. buy_order(stock_price=最良買気配) で信用デイトレ買い注文
   3. confirm_fill() で約定待機(タイムアウト60秒)
   4. 約定したら position dict に保存
```

---

## 設定パラメータ早見表

| パラメータ | 場所 | 既定値 | 影響する条件 |
|---|---|---|---|
| `STAT_ENABLED_STRATEGIES` | config.py | `['B']` | どの戦略を試すか(MVP では実質B固定) |
| `STAT_BB_WIDTH_MIN_RATIO` | config.py | `0.0036` | 共通フィルタ②の閾値 |
| `STAT_STOCK_CODE` | config.py | `1570` | 取引対象銘柄(指標計算対象も兼ねる) |
| `STRATEGY_PARAMS['B']['rsi_threshold']` | コード(クラス変数) | `10` | 戦略B のRSIエントリー閾値 |
| `STRATEGY_PARAMS['B']['hold_minutes']` | コード(クラス変数) | `30` | バックオフ時刻の計算に使用 |
| `STRATEGY_PRIORITY` | コード(クラス変数) | `['B', 'C', 'E', 'A', 'D']` | 同時発火時の選択優先度 |

---

## ログ出力例

`log_indicator_status()` が毎分出力する `[エントリー判定]` ログを読み解くと、上記のどの条件が満たされているか一目で分かる。

### 通常時(エントリーシグナルなし)

```
[指標] close=54830.00 rsi9=12.34 rci26=-45.60 bb_width=210.50(0.384% / 下限0.36%) BB[u3=55300 u2=55100 l2=54600 l3=54400]
[エントリー判定] CB全停止=○ / BB幅フィルタ=○(0.384% >= 0.36%) / 戦略B[時間帯=○ 停止=○ RSI<10=✕(rsi=12.34)] => ✕
```
→ RSI が 12.34 で 10以上のため戦略B シグナル不発火

### シグナル発火時

```
[指標] close=54520.00 rsi9=8.12 rci26=-78.30 bb_width=480.00(0.880% / 下限0.36%) BB[u3=55100 u2=54900 l2=54200 l3=54000]
[エントリー判定] CB全停止=○ / BB幅フィルタ=○(0.880% >= 0.36%) / 戦略B[時間帯=○ 停止=○ RSI<10=○(rsi=8.12)] => ○
エントリーシグナル: 戦略B (rsi9=8.12, close=54520.00, 最良買気配=54510)
```
→ 全条件合致で買い注文発出

### 時間帯NGで不発火

```
[指標] close=54830.00 rsi9=8.50 rci26=-82.00 bb_width=300.00(0.547% / 下限0.36%) BB[...]
[エントリー判定] CB全停止=○ / BB幅フィルタ=○(0.547% >= 0.36%) / 戦略B[時間帯=✕ 停止=○ RSI<10=○(rsi=8.50)] => ✕
```
→ 14:55 以降など時間帯バックオフでスキップ

### BB幅不足で不発火

```
[指標] close=54830.00 rsi9=7.20 rci26=-90.00 bb_width=150.00(0.274% / 下限0.36%) BB[...]
[エントリー判定] CB全停止=○ / BB幅フィルタ=✕(0.274% >= 0.36%) / 戦略B[時間帯=○ 停止=○ RSI<10=○(rsi=7.20)] => ✕
```
→ 凪相場のため共通フィルタで除外

---

## 参照

- [`stat_daytrade_design.md`](stat_daytrade_design.md) — 全体設計書(クラス構成、エグジット条件、起動方法 等)
- [`../report/trading_playbook.md`](../report/trading_playbook.md) — 戦略仕様の真実の源泉
- [`../report/trading_strategy_recommendations.md`](../report/trading_strategy_recommendations.md) — エントリー戦略の統計的根拠
- `src/service/trade/stat_daytrade.py` — 実装本体
- Issue #48 — Phase 3 デイトレードRPA
