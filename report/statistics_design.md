# 統計情報設計書

## 調査目的

RPAとして機械的に取引するためのエントリー条件を探索する。
既知シグナル（ゴールデンクロス等）は広く研究済みであり「買いシグナルで儲かる」という
単純な結果は期待しにくい。そのため **シグナルに依存しない生の指標値の状態と価格変動の関係** を
幅広く収集し、未知のシグナル候補を発掘することを主目的とする。

## データ概要

| 項目 | 内容 |
|---|---|
| データソース | `csv/indicator/` 配下の with_indicators CSV |
| 銘柄数 | 16銘柄（1570, 5803, 6146, 6857, 6920, 7011, 7012, 7013, 7203, 8035, 8306, 8308, 9432, 9501, 9983, 9984） |
| 期間 | 2026-04-06 〜 2026-04-07（2日分） |
| 時間足 | 1分足 / 3分足 / 5分足（全データ合算で集計） |
| 総カラム数 | 209カラム |
| 主なカラム群 | 基本情報(9) / SMA(75) / EMA(75) / WMA(75) / BB(11) / RSI・RCI(4) / MACD(16) / SAR・PSY(9) / 一目均衡表(31) / 過去変動(9) / 正解ラベル(36) |

## 正解ラベルの定義

各統計は以下の正解ラベルと組み合わせて集計する。

| カラム名 | 内容 |
|---|---|
| `price_change_flag_Nbar_after` | N本後の上昇フラグ（1=上昇, 0=変化なし, -1=下落） |
| `price_change_amount_Nbar_after` | N本後の株価変動額（円） |
| `price_change_rate_Nbar_after` | N本後の株価変動率（小数点以下5桁） |

**集計対象のN**: 1, 3, 5, 10, 15, 30本後（60/120は日またぎリスクがあるため優先度低）

---

## 統計① シグナル精度統計

### 目的

「クロスや逆転シグナルが発生したとき、N本後に上昇した割合・変動額は？」

既知シグナルの精度をデータで定量化する。世で言われているほど有効かどうかを検証する。

### 集計対象シグナル

| カラム名パターン | シグナル種別 | 発火条件（GC） | 発火条件（DC） |
|---|---|---|---|
| `sma_1min_5to10piece_golden/dead_cross` | SMA 5-10 クロス | == 1 | == 1 |
| `sma_1min_5to20piece_golden/dead_cross` | SMA 5-20 クロス | == 1 | == 1 |
| `sma_1min_5to25piece_golden/dead_cross` | SMA 5-25 クロス | == 1 | == 1 |
| `sma_1min_10to20piece_golden/dead_cross` | SMA 10-20 クロス | == 1 | == 1 |
| `sma_1min_10to25piece_golden/dead_cross` | SMA 10-25 クロス | == 1 | == 1 |
| `sma_1min_20to25piece_golden/dead_cross` | SMA 20-25 クロス | == 1 | == 1 |
| `ema_1min_*_golden/dead_cross`（同6組） | EMA クロス | == 1 | == 1 |
| `wma_1min_*_golden/dead_cross`（同6組） | WMA クロス | == 1 | == 1 |
| `macd_1min_cross` | MACD クロス | == 1 | == -1 |
| `sar_1min_reverse_flag` | SAR（終値）逆転 | == 1 | DC対象外 |
| `sar_hlc_1min_reverse_flag` | SAR（三本値）逆転 | == 1 | DC対象外 |
| `ichimoku_1min_bc_cross` | 一目 転換-基準 クロス | == 1 | == -1 |
| `ichimoku_1min_pl_cross` | 一目 価格-遅行 クロス | == 1 | == -1 |
| `ichimoku_1min_ls_cross` | 一目 先行-遅行 クロス | == 1 | == -1 |
| `ichimoku_1min_cloud_cross` | 一目 雲 上抜け/下抜け | == 1 | == 2 |

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `signal_col` | str | シグナルカラム名 |
| `signal_type` | str | `golden_cross` / `dead_cross` / `reverse` |
| `nbar` | int | 何本後の予測（1, 3, 5, 10, 15, 30） |
| `sample_count` | int | 発火行数（NaNを除く） |
| `rise_count` | int | 上昇（flag==1）の件数 |
| `flat_count` | int | 変化なし（flag==0）の件数 |
| `fall_count` | int | 下落（flag==-1）の件数 |
| `rise_rate` | float | 上昇率 = rise_count / sample_count |
| `fall_rate` | float | 下落率 = fall_count / sample_count |
| `amount_mean` | float | 変動額の平均（円） |
| `amount_std` | float | 変動額の標準偏差（円） |
| `amount_median` | float | 変動額の中央値（円） |
| `rate_mean` | float | 変動率の平均 |
| `rate_std` | float | 変動率の標準偏差 |

---

## 統計② バケット別精度統計

### 目的

「RSI 20〜30の間にいるとき、N本後に上昇した割合は？」

連続値指標を等幅で分割し、各範囲（バケット）ごとの精度を比較する。
どの値域で偏りが生じているかを可視化する。

### 集計対象・バケット設定

| カラム | 範囲 | 分割設定 |
|---|---|---|
| `rsi_1min_9piece` | 0〜100 | 10刻み（10分割） |
| `rsi_1min_14piece` | 0〜100 | 10刻み |
| `rci_1min_9piece` | -100〜100 | 20刻み（10分割） |
| `rci_1min_26piece` | -100〜100 | 20刻み |
| `psy_1min_12piece` | 0〜100 | 10刻み |
| `bb_1min_20piece_position` | 0〜1（clip後） | 0.1刻み（10分割） |
| `macd_1min_diff` | 可変 | 四分位（Q1/Q2/Q3/Q4）で4分割 |
| `bb_1min_20piece_width` | 可変 | 四分位で4分割 |

※ `bb_1min_20piece_position` は実測で範囲外（負値・1超）が出るため `clip(0, 1)` 前処理を行う

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `oscillator_col` | str | オシレーターカラム名 |
| `bucket_label` | str | バケットラベル（例: `[30, 40)`） |
| `bucket_left` | float | バケット下限 |
| `bucket_right` | float | バケット上限 |
| `nbar` | int | 何本後の予測 |
| `sample_count` | int | バケット内のサンプル数 |
| `rise_count` | int | 上昇件数 |
| `flat_count` | int | 変化なし件数 |
| `fall_count` | int | 下落件数 |
| `rise_rate` | float | 上昇率 |
| `fall_rate` | float | 下落率 |
| `amount_mean` | float | 変動額平均（円） |
| `amount_std` | float | 変動額標準偏差 |
| `amount_median` | float | 変動額中央値 |
| `rate_mean` | float | 変動率平均 |
| `rate_std` | float | 変動率標準偏差 |

---

## 統計③ クロス後経過本数別精度統計

### 目的

「ゴールデンクロスから3本後のエントリーでも有効か？」

クロス発生直後だけでなく、経過した本数（バーカウント）ごとに精度がどう変化するかを集計する。
RPAとして「クロス後N本以内にエントリー」という条件を設計するための根拠データになる。

### 集計対象カラム

| カラム名パターン | 本数 | 対応シグナル |
|---|---|---|
| `sma_1min_*_golden_cross_after` / `_dead_cross_after` | 36列（6組×GC/DC） | SMA各クロス後 |
| `ema_1min_*_golden_cross_after` / `_dead_cross_after` | 36列 | EMA各クロス後 |
| `wma_1min_*_golden_cross_after` / `_dead_cross_after` | 36列 | WMA各クロス後 |
| `ichimoku_1min_bc_gc_after` / `_bc_dc_after` | 2列 | 一目 転換-基準クロス後 |
| `ichimoku_1min_pl_gc_after` / `_pl_dc_after` | 2列 | 一目 価格-遅行クロス後 |
| `ichimoku_1min_ls_gc_after` / `_ls_dc_after` | 2列 | 一目 先行-遅行クロス後 |
| `ichimoku_1min_cloud_breakout_up_after` / `_down_after` | 2列 | 一目 雲ブレイクアウト後 |
| `ichimoku_1min_cloud_entry_up_after` / `_down_after` | 2列 | 一目 雲エントリー後 |

バーカウント値（0, 1, 2, ...）ごとに集計。最大値は `unique()` で動的取得。

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `after_col` | str | バーカウントカラム名 |
| `cross_type` | str | `golden_cross` / `dead_cross` |
| `bars_elapsed` | int | クロスから経過した本数（0=クロス発生本） |
| `nbar` | int | 何本後の予測 |
| `sample_count` | int | 該当バーカウント値の行数 |
| `rise_count` | int | 上昇件数 |
| `flat_count` | int | 変化なし件数 |
| `fall_count` | int | 下落件数 |
| `rise_rate` | float | 上昇率 |
| `fall_rate` | float | 下落率 |
| `amount_mean` | float | 変動額平均 |
| `amount_std` | float | 変動額標準偏差 |
| `amount_median` | float | 変動額中央値 |
| `rate_mean` | float | 変動率平均 |
| `rate_std` | float | 変動率標準偏差 |

---

## 統計④ 閾値以上/以下統計（未知シグナル探索の主体）

### 目的

「RSI が30以上のとき」「RCI が -80以下のとき」のように、
連続値指標が特定の閾値を超えている/下回っている状態での上昇率・変動額を集計する。
既知シグナルに依存せず、データから**隠れたシグナル候補を発掘**するための核心統計。

### 集計対象・閾値設定

| カラム | 閾値一覧 | 方向 |
|---|---|---|
| `rsi_1min_9piece` | 10, 20, 30, 40, 50, 60, 70, 80, 90 | 以上・以下の両方 |
| `rsi_1min_14piece` | 同上 | 同上 |
| `rci_1min_9piece` | -80, -60, -40, -20, 0, 20, 40, 60, 80 | 以上・以下の両方 |
| `rci_1min_26piece` | 同上 | 同上 |
| `psy_1min_12piece` | 10, 20, 30, 40, 50, 60, 70, 80, 90 | 以上・以下の両方 |
| `bb_1min_20piece_position` | 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 | 以上・以下の両方 |
| `macd_1min_diff` | 0・Q25・Q75（動的算出） | 以上・以下の両方 |
| `bb_1min_20piece_width` | Q25・Q50・Q75（動的算出） | 以上・以下の両方 |
| `sma_1min_5to10piece_diff` 〜 `sma_1min_20to25piece_diff`（6列） | 0（正/負） | 以上・以下の両方 |
| `ema_1min_*_diff`（6列） | 0（正/負） | 以上・以下の両方 |
| `wma_1min_*_diff`（6列） | 0（正/負） | 以上・以下の両方 |
| `ichimoku_1min_bc_diff` | 0（正/負） | 以上・以下の両方 |
| `ichimoku_1min_cloud_high_diff` | 0（正=雲の上） | 以上・以下の両方 |
| `ichimoku_1min_cloud_low_diff` | 0（正=雲の上） | 以上・以下の両方 |

※ `macd_1min_diff` / `bb_1min_20piece_width` の四分位閾値は全データから動的に算出する

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `indicator_col` | str | 指標カラム名 |
| `threshold` | float | 閾値 |
| `direction` | str | `above`（以上） / `below`（以下） |
| `nbar` | int | 何本後の予測 |
| `sample_count` | int | 条件に該当するサンプル数 |
| `rise_count` | int | 上昇件数 |
| `flat_count` | int | 変化なし件数 |
| `fall_count` | int | 下落件数 |
| `rise_rate` | float | 上昇率 |
| `fall_rate` | float | 下落率 |
| `amount_mean` | float | 変動額平均（円） |
| `amount_std` | float | 変動額標準偏差 |
| `amount_median` | float | 変動額中央値 |
| `rate_mean` | float | 変動率平均 |
| `rate_std` | float | 変動率標準偏差 |

---

## 統計⑤ ボリンジャーバンドσ位置別統計

### 目的

「価格が2σを超えているとき、N本後に平均回帰する（下落する）割合は？」

統計④では `bb_1min_20piece_position` の閾値で間接的に判定するが、
こちらは `close_price` とバンド上下限を直接比較して判定する。
σを超えている状態は「異常値」として逆張りエントリーのシグナル候補になりうる。

### 集計する条件

| 条件名 | 判定式 |
|---|---|
| `1sigma_above` | `close_price > bb_1min_20piece_upper_1sigma` |
| `2sigma_above` | `close_price > bb_1min_20piece_upper_2sigma` |
| `3sigma_above` | `close_price > bb_1min_20piece_upper_3sigma` |
| `1sigma_below` | `close_price < bb_1min_20piece_lower_1sigma` |
| `2sigma_below` | `close_price < bb_1min_20piece_lower_2sigma` |
| `3sigma_below` | `close_price < bb_1min_20piece_lower_3sigma` |
| `within_1sigma` | `lower_1sigma <= close_price <= upper_1sigma` |

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `condition_name` | str | 条件名（上表の左列） |
| `nbar` | int | 何本後の予測 |
| `sample_count` | int | 条件に該当するサンプル数 |
| `rise_count` | int | 上昇件数 |
| `flat_count` | int | 変化なし件数 |
| `fall_count` | int | 下落件数 |
| `rise_rate` | float | 上昇率 |
| `fall_rate` | float | 下落率 |
| `amount_mean` | float | 変動額平均（円） |
| `amount_std` | float | 変動額標準偏差 |
| `amount_median` | float | 変動額中央値 |
| `rate_mean` | float | 変動率平均 |
| `rate_std` | float | 変動率標準偏差 |

---

## 統計⑥ 価格と移動平均の位置関係統計

### 目的

「価格がSMA5より上にいるとき、N本後に上昇し続ける割合は？」

統計④でMAの差分（_diff列の正/負）を集計するが、こちらは `close_price` と
MA値を直接比較した2値（上側/下側）での集計。
「トレンドに乗っているか否か」を判断する基礎統計。

### 集計する条件

| 対象カラム | 条件（above） | 条件（below） |
|---|---|---|
| `sma_1min_5piece` | `close_price > sma_1min_5piece` | `close_price < sma_1min_5piece` |
| `sma_1min_10piece` | 同上 | 同上 |
| `sma_1min_20piece` | 同上 | 同上 |
| `sma_1min_25piece` | 同上 | 同上 |
| `ema_1min_5piece` 〜 `ema_1min_25piece`（4列） | 同上 | 同上 |
| `wma_1min_5piece` 〜 `wma_1min_25piece`（4列） | 同上 | 同上 |
| `ichimoku_1min_base_line` | `close_price > 基準線` | `close_price < 基準線` |
| `ichimoku_1min_conversion_line` | `close_price > 転換線` | `close_price < 転換線` |

### 出力カラム定義

| カラム名 | 型 | 説明 |
|---|---|---|
| `ma_col` | str | 比較対象の移動平均カラム名 |
| `position` | str | `above`（価格がMA上） / `below`（価格がMA下） |
| `nbar` | int | 何本後の予測 |
| `sample_count` | int | 該当サンプル数 |
| `rise_count` | int | 上昇件数 |
| `flat_count` | int | 変化なし件数 |
| `fall_count` | int | 下落件数 |
| `rise_rate` | float | 上昇率 |
| `fall_rate` | float | 下落率 |
| `amount_mean` | float | 変動額平均（円） |
| `amount_std` | float | 変動額標準偏差 |
| `amount_median` | float | 変動額中央値 |
| `rate_mean` | float | 変動率平均 |
| `rate_std` | float | 変動率標準偏差 |

---

## 実装方針・読み方・注意事項

### `_get_statistics()` 実装時の方針

```python
# __init__ に追加するインスタンス変数
self.stat1_rows = []  # 統計①シグナル精度
self.stat2_rows = []  # 統計②バケット別
self.stat3_rows = []  # 統計③クロス後経過本数
self.stat4_rows = []  # 統計④閾値以上/以下
self.stat5_rows = []  # 統計⑤BBσ位置
self.stat6_rows = []  # 統計⑥価格とMAの位置関係

# 処理フロー
# 1. 各CSV読み込み後に _get_statistics(df, csv_name) を呼び出し、rows へ追記
# 2. 全CSV処理完了後に _save_statistics() を呼び出し、CSV出力
# 3. NaN行は dropna() で除外（末尾行の正解ラベルNaNも自動除外）
# 4. NBAR_LIST = [1, 3, 5, 10, 15, 30]
```

### 統計結果の読み方

- **`rise_rate + fall_rate ≦ 1.0`**: 残差が `flat_rate`（変化なし）
- **`rise_rate > 0.55` 程度**: ランダム（0.5）から有意に偏っている可能性あり
- **`sample_count` が少ない場合**: 信頼性が低いため参考値として扱うこと  
  （目安: `sample_count < 30` の行は慎重に解釈する）

### 優先度の考え方

| 統計 | 性質 | RPAとしての活用 |
|---|---|---|
| ①シグナル精度 | 既知シグナルの検証 | 既存ルールの根拠確認 |
| **②バケット別** | **生データの分布確認** | **閾値候補のスクリーニング** |
| ③クロス後経過 | シグナル継続性の検証 | エントリー猶予本数の決定 |
| **④閾値以上/以下** | **未知シグナルの発掘（主体）** | **エントリー条件の候補探索** |
| **⑤BBσ位置** | **逆張り候補の検証** | **平均回帰エントリーの根拠** |
| ⑥価格とMAの位置 | トレンド方向の確認 | トレンドフォロー条件の補助 |
