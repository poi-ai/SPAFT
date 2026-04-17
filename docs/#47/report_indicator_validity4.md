# テクニカル指標 正当性チェックレポート（第4回: 一目均衡表バグ修正 + ファントムゼロ問題修正後）

**生成日時:** 2026-04-06 14:21:22
**対象:** `src/util/indicator.py` の各テクニカル指標計算メソッド
**フェーズ:** issue #47 対応前の事前確認（第3回残存WARNING項目の修正後チェック）

## 第3回からの変更点

第3回チェックで残存していたWARNING項目のうち、修正対象とした2種3件を修正した。

| メソッド | 問題 | 修正内容 |
|---|---|---|
| `get_ichimoku_cloud()` | `high`/`low` カラムが存在しない場合に `close_price` で代替する不正なフォールバック | `high_column_name`・`low_column_name` パラメータを追加。フォールバック処理を削除。デフォルト値で後方互換。 |
| `get_rsi()` | `diff[0]=NaN` を `up/down` 計算で `0` として扱うファントムゼロ問題 | NaNを伝播するよう lambda を修正。先頭NaNが window-1行→window行に変化。 |
| `get_psy()` | 同上（`up` 計算で NaN→0 になっていた） | 同上。先頭NaNが window-1行→window行に変化。 |

**後方互換性:** `get_ichimoku_cloud()` の既存呼び出し元（`past_record_mold.py`）は `high`/`low` カラムを持つdfを渡しているため、デフォルト引数のまま動作する。
## 前提・確認観点

フェーズ1(#46)が完了すると、KabuStation WebSocket PUSHで蓄積された1分足OHLCデータが
以下のカラム構成でCSVまたはDBテーブルに存在する想定。

**ohlcテーブル/CSVのカラム構成:**
```
symbol, trade_time, open_price, high_price, low_price, close_price, volume, total_volume, status
```

`indicator.py` の各メソッドはデフォルトで `price_column_name="current_price"` を想定している。
ohlcデータで使う場合は `price_column_name="close_price"` を明示する必要がある。
第2〜4回の修正により、カラム名のハードコード問題および一目均衡表のフォールバックバグは全て解消済み。

## サンプルデータ概要

| 項目 | 値 |
|---|---|
| 銘柄コード | 1570 |
| 行数 | 325 |
| 前場 | 9:00〜11:29 (150行) |
| 後場 | 12:30〜15:24 (175行) |
| 始値 | 28,000円 |
| 終値(最終) | 28,144円 |
| close_price 最小 | 27,594円 |
| close_price 最大 | 28,174円 |
| カラム構成 | symbol, trade_time, open_price, high_price, low_price, close_price, volume, total_volume, status |

## チェック結果サマリー

| # | 指標 | 結果 |
|---|---|---|
| 1 | SMA (sma_1min_3piece, interval=1) | ✅ PASS |
| 2 | EMA (ema_1min_3piece, interval=1) | ✅ PASS |
| 3 | WMA (wma_1min_3piece, interval=1) | ✅ PASS |
| 4 | ボリンジャーバンド (bb_1min_3piece, interval=1) | ✅ PASS |
| 5 | MAクロス (ma_cross, interval=1) | ✅ PASS |
| 6 | RSI (rsi_1min_9piece, interval=1) | ✅ PASS |
| 7 | RCI (rci_1min_9piece, interval=1) | ⚠️ WARNING |
| 8 | MACD (macd_1min, short=12, long=26, signal=9, interval=1) | ✅ PASS |
| 9 | PSY (psy_1min_10piece, interval=1) | ✅ PASS |
| 10 | パラボリックSAR (close_price ベース, min_af=0.02, max_af=0.2, interval=1) | ✅ PASS |
| 11 | パラボリックSAR HLC (high_column_name等を明示した正常動作の確認, interval=1) | ✅ PASS |
| 12 | 一目均衡表 (high_column_name等を明示した正常動作の確認, interval=1) | ✅ PASS |
| 13 | 変化額・変化率(get_change_price, price_column_name="close_price"を指定した正常動作の確認) | ✅ PASS |
| 14 | intervalリサンプリング方式の確認 (interval=5, 時刻ベースか行インデックスベースか) | ⚠️ WARNING |

**集計:** PASS=12 / WARNING=2 / FAIL=0 / ERROR=0

## 詳細結果

### ✅ SMA (sma_1min_3piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 先頭2行がNaN（window_size-1行分の期待する欠損）
- [OK] 有効値323行が全て正の実数
- [OK] 第3行目の値が期待値(28018.7)と一致: 28018.7

**詳細データ:**
```
nan_count: 2
min: 27599.7
max: 28143.3
sample: [28018.7, 28039.0, 28058.3, 28069.0]
```

### ✅ EMA (ema_1min_3piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 全値が正の実数
- [OK] 第1行目のEMAが始値(28015.0)と一致: 28015.0

**詳細データ:**
```
min: 27606.0
max: 28146.5
sample: [28015.0, 28012.3, 28022.4, 28051.0]
```

### ✅ WMA (wma_1min_3piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 先頭2行がNaN（window_size-1行分の期待する欠損）
- [OK] 有効値323行が全て正の実数
- [OK] 第3行目のWMAが期待値(28021.2)と一致: 28021.2

**詳細データ:**
```
nan_count: 2
min: 27600.5
max: 28148.7
sample: [28021.2, 28049.8, 28064.8, 28066.7]
```

### ✅ ボリンジャーバンド (bb_1min_3piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 期待する11カラムが全て生成された
- [OK] upper_1_alpha > lower_1_alpha が全行成立
- [OK] upper_2_alpha > upper_1_alpha が全行成立
- [OK] lower_1_alpha > lower_2_alpha が全行成立（バンドの広がり確認）
- [OK] 幅(width)が全行で正の値
- [OK] position値が概ね0〜1の範囲内

**詳細データ:**
```
sample_upper_1: [28072.4, 28083.1, 28076.0]
sample_lower_1: [28005.6, 28033.5, 28062.0]
sample_width: [66.843, 49.571, 14.0]
```

### ✅ MAクロス (ma_cross, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] クロスカラム90本が生成された
- [OK] sma_1min_3to5piece_golden_cross: 0/1フラグが正常
- [OK] sma_1min_3to10piece_golden_cross: 0/1フラグが正常
- [OK] sma_1min_3to5piece_diff: 合理的な差分値 (range: -48.5〜58.5)
- [OK] sma_1min_3to10piece_diff: 合理的な差分値 (range: -96.7〜120.9)

### ✅ RSI (rsi_1min_9piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] NaNが先頭9行のみ（期待通り: window=9本のデータが揃うまでNaN）
- [OK] 全RSI値が0〜100の範囲内

**詳細データ:**
```
nan_count: 9
expected_nan: 9
sample: [82.51, 78.65, 70.59, 62.84, 46.73]
```

### ⚠️ RCI (rci_1min_9piece, interval=1)

**総合判定:** WARNING

**チェック項目:**

- [WARNING] NaNが8行残存
- [OK] 全RCI値が-100〜100の範囲内

**詳細データ:**
```
nan_count: 8
sample: [-96.67, -96.67, -96.67, -93.33, -90.0]
```

### ✅ MACD (macd_1min, short=12, long=26, signal=9, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 期待する7カラムが全て生成された
- [OK] diff = macd - signal が正しい（最大誤差: 0.0000）
- [OK] diff_flag が正しく 0/1 で設定されている
- [OK] cross 値が -1/0/1 のみ
- [OK] slopeカラム4本が全て生成された

**詳細データ:**
```
sample_macd: [-47.46, -44.41, -41.52, -41.16, -38.53]
sample_signal: [-39.08, -40.15, -40.42, -40.57, -40.16]
sample_diff: [-8.38, -4.26, -1.1, -0.59, 1.63]
```

### ✅ PSY (psy_1min_10piece, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] NaNが先頭10行のみ（期待通り: window=10本のデータが揃うまでNaN）
- [OK] 全PSY値が0〜100の範囲内
- [OK] PSY値が全て10の倍数（window=10に対する正常な離散値）

**詳細データ:**
```
nan_count: 10
expected_nan: 10
sample: [50.0, 50.0, 50.0, 40.0, 40.0, 40.0, 30.0, 30.0, 30.0, 20.0]
```

### ✅ パラボリックSAR (close_price ベース, min_af=0.02, max_af=0.2, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 全SAR値が正の実数
- [OK] flagが0/1のみ
- [OK] SAR平均(27840)が終値平均(27838)の±30%以内

**詳細データ:**
```
sample_sar: [28015.0, 28014.8, 28011.0, 28013.6, 28016.1]
sample_flag: [0, 0, 0, 1, 1]
```

### ✅ パラボリックSAR HLC (high_column_name等を明示した正常動作の確認, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] 全SAR値が正の実数
- [OK] sar_1min_0.02_0.2af_hlc_flag: 0/1フラグが正常
- [OK] sar_1min_0.02_0.2af_hlc_reverse_flag: 0/1フラグが正常
- [OK] SAR平均(27840)が終値平均(27838)の±30%以内

**詳細データ:**
```
sample_sar: [28015.0, 27994.0, 27995.9, 28001.3, 28006.3]
sample_flag: [0, 0, 1, 1, 1]
sample_reverse_flag: [1, 0, 1, 0, 0]
```

### ✅ 一目均衡表 (high_column_name等を明示した正常動作の確認, interval=1)

**総合判定:** PASS

**チェック項目:**

- [OK] ichimoku_1min_base_line が生成された
- [OK] ichimoku_1min_conversion_line が生成された
- [OK] ichimoku_1min_leading_span_a が生成された
- [OK] ichimoku_1min_leading_span_b が生成された
- [OK] ichimoku_1min_lagging_span が生成された
- [OK] 基準線が正の数値型（有効値300行）
- [OK] 転換線が正の数値型（有効値317行）
- [OK] 基準線と転換線が294/300行で異なる値（high_price/low_price が正しく使われている）
- [OK] 先行スパン1: 有効値274行（range: 27649〜28015）
- [OK] 先行スパン2: 有効値248行（range: 27682〜27995）

**詳細データ:**
```
high_column_name: high_price
low_column_name: low_price
base_line_sample: [28002.5, 27989.0, 27984.5]
conversion_line_sample: [28057.0, 28071.5, 28078.0]
```

### ✅ 変化額・変化率(get_change_price, price_column_name="close_price"を指定した正常動作の確認)

**総合判定:** PASS

**チェック項目:**

- [OK] change_1min_price が生成された
- [OK] change_1min_rate が生成された
- [OK] change_1min_flag が生成された
- [OK] change_price: 全325行に値あり（末尾はffillで補完済み）
- [OK] change_price 最大絶対値: 115.0円（妥当な範囲）
- [OK] change_flag: 値が -1/0/1 のみ（有効値325行）
- [OK] change_rate = change_price / close_price の計算が正確

**詳細データ:**
```
price_column_name: close_price
interval: 1
change_price_range: -97.0 ~ 115.0
change_flag_unique: [-1.0, 0.0, 1.0]
nan_rows: 0
末尾補完: 最終1行は shift(-1)=NaN のため直前値で ffill
```

### ⚠️ intervalリサンプリング方式の確認 (interval=5, 時刻ベースか行インデックスベースか)

**総合判定:** WARNING

**チェック項目:**

- [OK] リサンプリング後の先頭5行の時刻: ['2026-04-06 09:00:00', '2026-04-06 09:05:00', '2026-04-06 09:10:00', '2026-04-06 09:15:00', '2026-04-06 09:20:00']
- [WARNING] 行インデックスベースのリサンプリングのため、前場終了(2026-04-06 11:29:00)と後場開始(2026-04-06 12:30:00)が連続した行として扱われる。昼休み(60分)を跨ぐN分足の計算が時刻的に不正確になる可能性がある。
- [OK] interval=5でSMAが315行生成された（生成自体は成功）

**詳細データ:**
```
resampling_method: iloc[::interval] (行インデックスベース)
first_5_times: ['2026-04-06 09:00:00', '2026-04-06 09:05:00', '2026-04-06 09:10:00', '2026-04-06 09:15:00', '2026-04-06 09:20:00']
lunch_break_gap: 2026-04-06 11:29:00 → 2026-04-06 12:30:00 (行上では連続)
```

## 残存する懸念事項（設計上の意図的な挙動）

### 1. `interval` リサンプリングが時刻ベースではなく行インデックスベース

```python
# indicator.py 内部（各メソッド共通）
df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
```
`iloc[::interval]` は行番号ベースで等間隔抽出するため、
前場(9:00-11:30, 150本)と後場(12:30-15:25, 175本)の間の昼休み(60分)を考慮しない。
例: interval=5 の場合、前場149行目(11:29)と後場150行目(12:30)が
「連続した5分間」として計算される。本来は91分離れている。

**設計上の意図:** 国内証券会社のチャートが採用している方式と整合するため、意図的に維持。
`interval=1`（1分足）が主な用途であれば影響ゼロ。詳細は `supplement_indicator_design_notes.md` を参照。

### 2. RSI・RCI・PSY の先頭行 NaN（設計上の正常な挙動）

window本ぶんのデータが揃うまで指標が計算できないため、先頭の window行はNaNになる。
これは数学的に正しい挙動であり、修正は不要。

| 指標 | window | 先頭NaN行数 |
|---|---|---|
| RSI | 9 | 9行（ファントムゼロ修正により window-1→window に変化） |
| RCI | 9 | 8行（元々正確） |
| PSY | 10 | 10行（ファントムゼロ修正により window-1→window に変化） |

CatBoostはNaN対応済みのためML学習上の問題はない。

---
*このレポートは自動生成されたものです。第4回をもって事前確認フェーズは完了。issue #47 の実装フェーズに移行可能。*