# 統計情報CSV 分析レポート

- **データ期間**: 2026-04-06 〜 2026-04-10（5営業日分）
  - 根拠: `csv/ohlc/bak/` 配下の 20260406.7z 〜 20260410.7z の5ファイル
- **銘柄数**: 16銘柄（1570, 5803, 6146, 6857, 6920, 7011, 7012, 7013, 7203, 8035, 8306, 8308, 9432, 9501, 9983, 9984）
- **時間足**: 1分足合算
- **対象ファイル**: `csv/statistics/statistics_{1..6}_*.csv`

## 分析の対象外にした指標（リーク疑い）

一目均衡表の **遅行スパン** 系カラムは「現在の終値を過去にシフトしたもの」であり、
分析時点で見ると**未来の価格情報を利用**してしまうため（リーク）、本レポートからは除外している。

除外カラム:
- `ichimoku_1min_lagging_span`
- `ichimoku_1min_pl_diff`
- `ichimoku_1min_pl_position`
- `ichimoku_1min_pl_cross`
- `ichimoku_1min_pl_gc_after`
- `ichimoku_1min_pl_dc_after`

> 備考: 5日分は最低限の目安にはなるが、セクター・市況の偏りを排除するためには**1か月以上**が理想。本レポートの結論は仮説として扱い、より長期で再検証することを推奨する。

---

## 総評: このデータセットの傾向

### 発見① 全体に「平均回帰（mean-reversion）」寄りのバイアス

- オシレーターの売られすぎ側（RSI<30, RCI<-60, PSY<30, BB_position<0.3）で `rise_rate` が有意に上がる
- 価格が中期・長期MAより **下** にいるときの方が、将来的に上昇する確率が高い
- **教科書通りの「トレンドフォロー」シグナル（GC後買い・価格>MAで買い）は、この5日間では優位性が薄い**

### 発見② クロス系シグナル（SMA/EMA/WMA の GC/DC）は全般に弱〜中程度

- 最強でも `rise_rate ≈ 0.55`、サンプル数も数百〜1500程度
- WMA・SMAの中長期ペア（10-25, 20-25, 5-25）の **デッドクロス後に上昇**するという逆行パターンが一定見られる
- **ゴールデンクロス直後の順張り買い**は、短期MA（5-10, 5-20）では効果が出ず

### 発見③ オシレーター深押し（売られすぎ）は大サンプル × 安定した買いシグナル

- `RCI26 <= -80` / `RSI14 <= 30` / `bb_position <= 0.1` あたりは **数千〜数万サンプル** で rise_rate 0.55〜0.60 前後を維持
- 強度は `pl_cross` 除外後の単独シグナルの中では最も信頼できる

---

## 1. 統計① シグナル精度統計の分析

### 1-1. 上昇シグナル TOP10（sample>=100、pl_cross除外）

| signal_col | signal_type | nbar | sample | rise_rate | amount_mean | 備考 |
|---|---|---|---|---|---|---|
| `ichimoku_cloud_cross` | **dead_cross** | 30 | 252 | **0.575** | +14.5円 | 設計書値==2で集計 |
| `ichimoku_ls_cross` | golden_cross | 30 | 123 | 0.561 | -6.3円 | 金額はマイナス（矛盾） |
| `ichimoku_ls_cross` | dead_cross | 15 | 138 | 0.558 | +7.9円 | |
| `wma_20to25_golden_cross` | golden_cross | 30 | 411 | 0.552 | +14.3円 | 長期WMA順張り |
| `wma_20to25_dead_cross` | dead_cross | 30 | 381 | 0.551 | +11.6円 | **DCで上昇（逆行）** |
| `sma_10to25_dead_cross` | dead_cross | 30 | 405 | 0.551 | +10.0円 | 同上 |
| `sma_5to25_dead_cross` | dead_cross | 30 | 474 | 0.549 | +14.4円 | 同上 |
| `ichimoku_cloud_cross` | dead_cross | 15 | 291 | 0.546 | +5.0円 | |
| `wma_10to20_dead_cross` | dead_cross | 10 | **712** | 0.542 | +10.8円 | **サンプル数◎** |
| `wma_20to25_golden_cross` | golden_cross | 15 | 466 | 0.541 | +8.2円 | |

**読み解き:**
- 最強でも `rise_rate 0.575`、サンプル252と小規模。**単独エントリー条件としてはやや弱い**
- 長期MAペアのデッドクロスで「上昇する」という**教科書と逆のパターン**が複数カラムで確認できる（`wma_20to25_dc`, `sma_10to25_dc`, `sma_5to25_dc`）
- 短期MAのGC（5-10, 5-20）は rise_rate が0.5前後で平凡

### 1-2. 下落シグナル TOP10

| signal_col | signal_type | nbar | sample | fall_rate | amount_mean |
|---|---|---|---|---|---|
| `ichimoku_bc_cross` | dead_cross | 10 | 289 | **0.547** | -4.0円 |
| `ichimoku_ls_cross` | dead_cross | 30 | 122 | 0.533 | -8.3円 |
| `ichimoku_ls_cross` | golden_cross | 15 | 147 | 0.531 | -0.7円 |
| `ichimoku_ls_cross` | dead_cross | 3 | 147 | 0.524 | -2.5円 |
| `ema_20to25_golden_cross` | golden_cross | 30 | 499 | 0.519 | +17.0円（矛盾） |
| `sma_10to25_golden_cross` | golden_cross | 3 | 546 | 0.515 | -4.8円 |
| `wma_20to25_dead_cross` | dead_cross | 10 | 459 | 0.510 | +2.5円 |
| `macd_cross` | golden_cross | 30 | 966 | 0.506 | +13.7円 |

**読み解き:**
- 最強でも `fall_rate 0.547`、サンプル289と弱い
- **売り(ショート)シグナルとしての単独強度は低い**
- `amount_mean` が正の行は fall_rate 高めでも「大きく上昇するケースが一部ある」ことを示す

### 1-3. SAR（逆転フラグ）

| signal_col | nbar | sample | rise_rate | fall_rate | amount_mean |
|---|---|---|---|---|---|
| `sar_1min_reverse_flag` | 5 | 2273 | 0.521 | 0.447 | +6.6円 |
| `sar_1min_reverse_flag` | 15 | 2143 | 0.523 | 0.453 | +15.5円 |
| `sar_hlc_1min_reverse_flag` | 10 | 3536 | 0.507 | 0.462 | +11.6円 |
| `sar_hlc_1min_reverse_flag` | 15 | 3429 | 0.511 | 0.462 | +14.8円 |

→ **SAR逆転のみでは優位性は弱い（rise_rate 0.5前後）。** 他条件と組み合わせる補助シグナル程度。

---

## 2. 統計② バケット別精度統計の分析

### 2-1. 上昇側の強いバケット（sample>=100）

| oscillator_col | bucket | nbar | sample | rise_rate |
|---|---|---|---|---|
| `psy_1min_12piece` | `[0, 10)` | 30 | 143 | **0.727** |
| `rsi_1min_9piece` | `[0, 10)` | 30 | 413 | **0.646** |
| `rsi_1min_14piece` | `[10, 20)` | 30 | 515 | **0.625** |
| `psy_1min_12piece` | `[80, 90)` | 30 | 116 | 0.603 |
| `psy_1min_12piece` | `[10, 20)` | 30 | 666 | 0.593 |
| `rci_1min_26piece` | `[-100, -80)` | 15 | **2442** | 0.590 |
| `rci_1min_26piece` | `[-100, -80)` | 30 | 2293 | 0.580 |
| `rsi_1min_9piece` | `[10, 20)` | 30 | 1153 | 0.579 |
| `rsi_1min_14piece` | `[90, 100]` | 15 | 122 | 0.574 |
| `rci_1min_26piece` | `[-100, -80)` | 10 | 2500 | 0.572 |

### 2-2. 下落側の強いバケット

| oscillator_col | bucket | nbar | sample | fall_rate |
|---|---|---|---|---|
| `psy_1min_12piece` | `[80, 90)` | 1 | 139 | 0.554 |
| `rsi_1min_14piece` | `[80, 90)` | 10 | 803 | 0.539 |
| `psy_1min_12piece` | `[80, 90)` | 3 | 139 | 0.532 |
| `rsi_1min_14piece` | `[80, 90)` | 3 | 809 | 0.531 |
| `rsi_1min_14piece` | `[80, 90)` | 5 | 806 | 0.531 |
| `rsi_1min_9piece` | `[90, 100]` | 3 | 573 | 0.522 |
| `rci_1min_9piece` | `[80, 100]` | 10 | 4058 | 0.515 |

**読み解き:**
- **売られすぎ反発（RSI<20, RCI26<-80, PSY<20）は、買いシグナルとして高精度**
- **買われすぎ反落は弱め**（最強でも fall_rate 0.55程度、サンプル少）
- **RCI26 <= -80 が最も実用的**: サンプル数が2442と大規模で、rise_rate 0.58〜0.59

### 2-3. BB width（ボラ）/ macd_diff の四分位分布

| oscillator_col | bucket | nbar | rise_rate | 備考 |
|---|---|---|---|---|
| `bb_1min_20piece_width` | Q4（広い） | 30 | **0.550** | ボラ高でエントリーは上昇寄り |
| `bb_1min_20piece_width` | Q1（狭い） | 30 | 0.49 | ボラ収縮中は動きが鈍い |
| `macd_1min_diff` | Q1〜Q4 | 30 | 0.50〜0.52 | 四分位の差は小さい |

→ **ボラが高い局面（BB幅が上位25%）でのエントリーは平均回帰が加速しやすく、利益期待値も高い**。

---

## 3. 統計③ クロス後経過本数別精度統計の分析

### 3-1. 上昇側 TOP（bars_elapsed<=5, sample>=200、pl除外）

| after_col | cross_type | bars | nbar | sample | rise_rate | amount_mean |
|---|---|---|---|---|---|---|
| `wma_20to25_golden_cross_after` | golden_cross | 1 | 15 | 652 | **0.572** | +29.2円 |
| `ichimoku_ls_dc_after` | dead_cross | 3 | 10 | 332 | 0.566 | +29.8円 |
| `ichimoku_ls_dc_after` | dead_cross | 1 | 15 | 333 | 0.565 | +38.7円 |
| `ichimoku_cloud_breakout_up_after` | golden_cross | 2 | 30 | 413 | 0.564 | +17.8円 |
| `ichimoku_ls_dc_after` | dead_cross | 0 | 10 | 335 | 0.561 | +35.8円 |
| `ichimoku_cloud_entry_up_after` | golden_cross | 0 | 10 | 573 | 0.560 | +19.8円 |
| `ichimoku_ls_dc_after` | dead_cross | 0 | 15 | 333 | 0.559 | **+43.1円** |
| `ichimoku_ls_gc_after` | golden_cross | 0 | 10 | 346 | 0.558 | +33.0円 |
| `wma_10to20_dead_cross_after` | dead_cross | 0 | 10 | 907 | 0.557 | +20.4円 |
| `ichimoku_cloud_breakout_up_after` | golden_cross | 0 | 10 | 503 | 0.555 | +24.8円 |

**読み解き:**
- 一目均衡表 **先行スパン1-2 のデッドクロス後（ls_dc_after）** は0〜3本後までrise_rate 0.55〜0.57と持続し、amount_meanも**+30円超**
- **WMA 20-25 ゴールデンクロスの翌本（bars=1）** は rise_rate 0.57 / amount_mean +29円で比較的大きな利幅
- **エントリー本にこだわらず、発生〜3本程度の猶予がある**ことが確認できる（RPA設計で有用）

### 3-2. 下落側 TOP

| after_col | cross_type | bars | nbar | sample | fall_rate | amount_mean |
|---|---|---|---|---|---|---|
| `ema_20to25_golden_cross_after` | golden_cross | 3 | 30 | 524 | 0.555 | +9.8円（矛盾） |
| `ichimoku_cloud_entry_up_after` | golden_cross | 3 | 30 | 444 | 0.554 | +10.7円 |
| `ichimoku_cloud_breakout_down_after` | dead_cross | 5 | 30 | 416 | 0.550 | -1.0円 |
| `ema_20to25_golden_cross_after` | golden_cross | 4 | 30 | 499 | 0.549 | +11.6円（矛盾） |
| `ichimoku_bc_dc_after` | dead_cross | 1 | 10 | 484 | 0.545 | +9.4円（矛盾） |

**読み解き:**
- 下落シグナルの最強でも fall_rate 0.55 前後で単独優位性は限定的
- amount_mean が正の行が多い = 「下落件数は多いが平均すると勝ちが大きい」= ショートには向かない

---

## 4. 統計④ 閾値以上/以下統計の分析（未知シグナル発掘の主体）

### 4-1. rise_rate が高い閾値条件（sample>=300）

| indicator_col | threshold | direction | nbar | sample | rise_rate | amount_mean |
|---|---|---|---|---|---|---|
| `rsi_1min_14piece` | 20 | below | 30 | 632 | **0.649** | +36.7円 |
| `rsi_1min_9piece` | 10 | below | 30 | 450 | **0.647** | +39.6円 |
| `psy_1min_12piece` | 20 | below | 30 | 809 | **0.617** | +22.7円 |
| `rsi_1min_9piece` | 20 | below | 30 | 1685 | 0.594 | +26.1円 |
| `rci_1min_26piece` | -80 | below | 15 | 2445 | 0.589 | +16.8円 |
| `rsi_1min_14piece` | 30 | below | 30 | 2568 | 0.581 | +21.8円 |
| `rci_1min_26piece` | -80 | below | 30 | 2296 | 0.580 | +18.2円 |
| `rci_1min_26piece` | -80 | below | 10 | 2503 | 0.571 | +8.5円 |
| `psy_1min_12piece` | 30 | below | 30 | 2717 | 0.568 | +16.2円 |
| `rci_1min_26piece` | -60 | below | 30 | 4856 | 0.564 | +12.2円 |
| `bb_1min_20piece_position` | 0.1 | below | 30 | **5980** | 0.560 | +16.9円 |
| `macd_1min_diff` | -1.8 | below | 30 | 5968 | 0.558 | +19.6円 |
| `bb_1min_20piece_width` | 121.44 | above | 15 | 5684 | 0.556 | +19.6円 |
| `ichimoku_1min_cloud_low_diff` | 0 | below | 30 | 4715 | 0.557 | +13.4円 |

### 4-2. fall_rate が高い閾値条件

| indicator_col | threshold | direction | nbar | sample | fall_rate |
|---|---|---|---|---|---|
| `rsi_1min_14piece` | 80 | above | 5 | 930 | 0.529 |
| `rsi_1min_14piece` | 80 | above | 3 | 933 | 0.526 |
| `psy_1min_12piece` | 70 | above | 3 | 815 | 0.524 |
| `rsi_1min_14piece` | 80 | above | 10 | 926 | 0.524 |
| `rsi_1min_9piece` | 90 | above | 3 | 573 | 0.522 |
| `rci_1min_9piece` | 80 | above | 10 | 4058 | 0.515 |

→ **売り側シグナルは最強でも fall_rate=0.53。** 単独での売りエントリー根拠には不十分。

### 4-3. MA diff（短期 - 長期）による偏り

すべてのペアで共通する傾向（nbar=30, sample 10k以上）:

| direction | rise_rate 範囲 | 解釈 |
|---|---|---|
| `above`（短期>長期, トレンド上） | **0.48〜0.50** | 継続性なし |
| `below`（短期<長期, トレンド下） | **0.52〜0.55** | **下落中の方がその後上昇** |

→ このデータでは、MA_diffベースの**順張り戦略は機能せず、逆に平均回帰側が優位**。

### 4-4. MACD diff（動的四分位）

- `macd_diff <= -1.8` (Q25以下) × nbar=30: rise_rate **0.558** (5968件, +19.6円)
- `macd_diff >= +2.1` (Q75以上) × nbar=30: rise_rate 0.522 (5796件, +3.4円)

→ **MACDヒストグラムが深くマイナスの時ほど、以後の反発買いが期待できる**。

### 4-5. BB width（ボラティリティ, 動的四分位）

- `bb_width >= 121.44` (Q75以上) × nbar=15: rise_rate **0.556**, amount +19.6円
- `bb_width >= 36.06` (Q50以上) × nbar=30: rise_rate 0.546
- `bb_width <= 12.67` (Q25以下): rise_rate 0.46〜0.49（不利）

→ **ボラ収縮中のエントリーは避け、ボラ拡大局面で仕込む**のが有効。

---

## 5. 統計⑤ BBσ位置別統計の分析

| condition | nbar | sample | rise_rate | fall_rate | amount_mean |
|---|---|---|---|---|---|
| `1sigma_above` | 5 | 6363 | 0.458 | 0.492 | -2.1円 |
| `1sigma_above` | 30 | 5140 | 0.493 | 0.483 | +8.6円 |
| `2sigma_above` | 3 | 1105 | 0.397 | **0.529** | -2.8円 |
| `2sigma_above` | 5 | 1099 | 0.420 | 0.527 | -3.0円 |
| `2sigma_above` | 10 | 1073 | 0.417 | **0.539** | -4.0円 |
| `3sigma_above` | 10 | 40 | 0.300 | 0.550 | -4.4円（小） |
| `1sigma_below` | 30 | 4934 | **0.564** | 0.422 | +16.5円 |
| `2sigma_below` | 30 | 889 | **0.579** | 0.405 | +32.3円 |
| `2sigma_below` | 3 | 1066 | 0.532 | 0.409 | +7.3円 |
| `within_1sigma` | 全 | 9800〜 | 0.45〜0.51 | 0.43〜0.47 | 中立 |

**読み解き:**
- **`2sigma_below` は明確な反発買い候補**（30本後 rise_rate 0.58 / amount +32円）
- `2sigma_above` は逆張り売りのヒント（fall_rate 0.53〜0.54）
- `3sigma_*` はサンプル40〜60と少なすぎて**信頼性低い**
- `within_1sigma`（レンジ相場）は中立。方向性エントリーには向かない

---

## 6. 統計⑥ 価格とMA位置関係の分析

### 6-1. 「price < MA」時の nbar=30 上昇率（上位）

| ma_col | sample | rise_rate |
|---|---|---|
| `ichimoku_1min_base_line` | 9289 | **0.549** |
| `wma_1min_25piece` | 9288 | 0.540 |
| `sma_1min_25piece` | 9382 | 0.539 |
| `wma_1min_20piece` | 9713 | 0.538 |
| `sma_1min_20piece` | 9799 | 0.535 |

### 6-2. 「price > MA」時の nbar=30 上昇率（上位）

| ma_col | sample | rise_rate | 解釈 |
|---|---|---|---|
| `wma_1min_5piece` | 13256 | 0.478 | わずかにマイナス寄り |
| `sma_1min_5piece` | 13230 | 0.479 | |
| `ema_1min_5piece` | 13698 | 0.479 | |

→ **「price > 短期MA = 買い」という基本戦術は、この5日間では機能しない。**
→ **「price < 中期MA（20, 25本）」の方が、30本後に上昇する確率が高い**（平均回帰寄りの挙動）。

---

## 7. RPAエントリー条件の推奨（仮説）

以下は5日分データからの仮説であり、より長い期間で再検証すること。

### 7-1. 最有力: 複合逆張り買い条件

**条件A（RCI逆張り、大サンプル・中精度）**:
```
rci_1min_26piece <= -80
AND close_price < ichimoku_1min_base_line
→ 期待値: rise_rate ≈ 0.58 以上（nbar=15〜30）、amount_mean +17円
```
※ `rci_1min_26piece<=-80` 単独でも sample 2445件 / rise_rate 0.589（nbar=15）と**最も信頼性が高い**。

**条件B（RSI深押し、中サンプル・高精度）**:
```
rsi_1min_14piece <= 20
AND bb_1min_20piece_position <= 0.1
→ 期待値: rise_rate ≈ 0.63〜0.65（nbar=30）、amount_mean +36円
```

**条件C（ボリンジャー2σ割れ反発）**:
```
close_price < bb_1min_20piece_lower_2sigma
AND macd_1min_diff <= -1.8
→ 期待値: rise_rate ≈ 0.56〜0.58、amount_mean +20〜32円
```

**条件D（ボラ拡大局面での反発買い）**:
```
bb_1min_20piece_width >= 121.44 (Q75以上)
AND rci_1min_26piece <= -60
→ 期待値: rise_rate ≈ 0.56（nbar=15〜30）、amount_mean +16〜20円
```

### 7-2. 補助シグナル（優位性は弱いが組合せ可）

- `ichimoku_cloud_cross == 2` (雲ブレイクアウト up 後、実装コード基準のGC): サンプル500〜 / rise_rate 0.55前後
- `wma_10to20_dead_cross_after bars=0, nbar=10`: rise_rate 0.557（907サンプル）— **DC後に上昇という逆行パターン**
- `sar_1min_reverse_flag`: 単独効果は薄いが、他条件の補強に使えるかも

### 7-3. 避けるべきエントリー条件

- **SMA/EMA/WMA 短期ペア（5-10, 5-20）のGC順張り買い**: rise_rate 0.47〜0.53 で優位性なし
- **price > 短期MA（5本）のタイミングでの買い**: rise_rate 0.48 = 実質マイナス期待値
- **bb_width < Q25（ボラ収縮中）のエントリー**: rise_rate 0.46〜0.49 = 負けやすい
- **`within_1sigma`（レンジ中）の方向性エントリー**: 全般に効果なし
- **`3sigma_above/below`**: サンプルが40〜60件と少なく、統計量として信頼できない

### 7-4. 利確本数（nbar）の選び方

| nbar | 観測される強度 | 採用判断 |
|---|---|---|
| 1〜5本 | どの条件でも rise_rate 0.45〜0.53、差が出にくい | **避ける** |
| 10〜15本 | RCI26<=-80等で 0.57〜0.59 で安定 | **推奨** |
| 30本 | 最高精度だが保有リスク増（ニュース等） | サンプル充実時のみ |

**推奨**: `nbar=15` を基準にエントリー、30分を上限とした利確。

---

## 8. データ品質上の制約と追加調査の方針

### 8-1. 本データの制約

| 項目 | 問題 |
|---|---|
| 期間 | 5営業日 → 1週間未満。**市況バイアスが残る可能性** |
| 銘柄 | 16銘柄 → セクター偏りあり（金融・ハイテク・ETF中心） |
| nbar=60, 120 | 日またぎリスクで集計対象外のため未検証 |
| 遅行スパン系 | リークのため除外（本レポートでは既除外） |
| `cloud_cross` の GC/DC | 設計書と実装で値割当が不整合（要調整） |

### 8-2. 追加で実施すべき調査

1. **期間延長**: 最低1か月、理想は3か月以上の1分足データで再集計
2. **銘柄別の分析**: 全銘柄合算では薄まる銘柄特有の癖を分離
3. **時間帯別の分析**: 前場寄り付き / 前場後半 / 後場寄り / 大引け前のシグナル精度差
4. **複合条件のバックテスト**: 7-1 条件A〜Dを呼値・手数料込みで検証
5. **市況フィルタ**: 日経平均上昇日/下落日、ボラ高/低日での条件別再集計
6. **リーク再確認**: 一目均衡表の `leading_span_a/b`（先行スパン）も26本シフトしているため、
   「未来情報の利用」ではないが「過去の値を未来に表示」しており、解釈に注意
7. **`cloud_cross` の値割当**: 設計書と実装の整合（GC==2, DC==3 に統一するか、
   設計書側を現状の実装に合わせるか）

### 8-3. 5日分のデータでも言えそうなこと

- **平均回帰寄りシグナル（オシレーター売られすぎ）の方が、トレンド追従シグナル（GC/DC/価格>MA）より優位**
- **短期MAの上下関係による順張りは機能せず、逆張り側が勝ちやすい**
- **BB2σ割れ、RSI14<=20、RCI26<=-80 はいずれも「買い候補」として再検証する価値がある**
- **ボラ拡大（BB width が Q75超）局面でのエントリーの方が、収縮局面より有利**

---

## 9. サマリー（一言）

この5日間では **「売られすぎを拾う逆張り買い（RCI26<=-80 / RSI14<=20 / BB2σ割れ）」** が最も安定しており、
**「MAクロスや価格>MA の順張り買い」** は優位性が確認できなかった。
ただし **市況依存の可能性** があるため、本格採用前に期間を延ばして再検証すること。

## 参考ファイル

- 設計書: `report/statistics_design.md`
- 読み方ガイド: `report/statistics_how_to_read.md`
- 集計スクリプト: `src/indicator_statistics.py`
- 集計CSV: `csv/statistics/statistics_{1..6}_*.csv`
