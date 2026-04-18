# indicator.py 出力カラム名 命名妥当性レビュー

**作成日:** 2026-04-06
**対象:** `src/util/indicator.py` 全メソッドの出力カラム名
**背景:** issue #47 実装前に、DataFrame に追加される各カラム名の妥当性・統一性を確認する

---

## 目次

1. [全カラム名の一覧](#1-全カラム名の一覧)
2. [明らかにおかしい](#2-明らかにおかしい)
3. [わかりづらい](#3-わかりづらい)
4. [統一性がない](#4-統一性がない)
5. [修正推奨まとめ](#5-修正推奨まとめ)

---

## 1. 全カラム名の一覧

`column_name` は呼び出し元から渡される基底名（例: `macd_1min`）。
`{col}` はその略記。

| メソッド | 出力カラム名パターン | 備考 |
|---|---|---|
| `get_sma()` | `{col}` | SMA値 |
| `get_ema()` | `{col}` | EMA値 |
| `get_wma()` | `{col}` | WMA値 |
| `get_ma_cross()` | `{type}_{n}min_{a}to{b}piece_golden_cross` | 0/1フラグ |
| | `{type}_{n}min_{a}to{b}piece_golden_cross_after` | GC後経過本数 |
| | `{type}_{n}min_{a}to{b}piece_dead_cross` | 0/1フラグ |
| | `{type}_{n}min_{a}to{b}piece_dead_cross_after` | DC後経過本数 |
| | `{type}_{n}min_{a}to{b}piece_diff` | 短期MA - 長期MAの差 |
| `get_bollinger_bands()` | `{col}_upper_1_alpha` / `_lower_1_alpha` | ±1σバンド |
| | `{col}_upper_2_alpha` / `_lower_2_alpha` | ±2σバンド |
| | `{col}_upper_3_alpha` / `_lower_3_alpha` | ±3σバンド |
| | `{col}_width` | ±1σバンド全幅(=2σ) |
| | `{col}_width_diff` | 前本からのバンド幅変化 |
| | `{col}_upper_diff` | 価格 - 上限(+1σ) |
| | `{col}_lower_diff` | 下限(-1σ) - 価格 |
| | `{col}_position` | ±1σバンド内の相対位置(0〜1) |
| `get_rsi()` | `{col}` | RSI値(0〜100) |
| `get_rci()` | `{col}` | RCI値(-100〜100) |
| `get_macd()` | `{col}` | MACD値 |
| | `{col}_signal` | MACDシグナル |
| | `{col}_diff` | MACD - signal（ヒストグラム） |
| | `{col}_diff_flag` | ヒストグラムが正なら1 |
| | `{col}_cross` | GC=1, DC=-1, なし=0 |
| | `{col}_1_slope` / `_3_slope` / `_5_slope` / `_10_slope` | MACDのN本前との差 |
| | `{col}_signal_1_slope` / ... | シグナルのN本前との差 |
| | `{col}_mismatch` | ダイバージェンスフラグ(0/1) |
| | `{col}_mismatch_count` | ダイバージェンス継続本数 |
| `get_psy()` | `{col}` | PSY値(0〜100) |
| `get_parabolic()` | `{col}` | SAR値 |
| | `{col}_flag` | SAR上昇なら1 |
| `get_parabolic_hlc()` | `{col}` | SAR値 |
| | `{col}_flag` | SAR上昇なら1 |
| | `{col}_reverse_flag` | トレンド反転なら1 |
| `get_ichimoku_cloud()` | `{col}_base_line` | 基準線 |
| | `{col}_conversion_line` | 転換線 |
| | `{col}_leading_span_a` | 先行スパン1 |
| | `{col}_leading_span_b` | 先行スパン2 |
| | `{col}_lagging_span` | 遅行スパン |
| | `{col}_bc_diff` | 転換線 - 基準線 |
| | `{col}_bc_position` | 転換線 > 基準線なら1 |
| | `{col}_bc_cross` | GC=1, DC=-1, なし=0 |
| | `{col}_bc_gc_after` | 転換線GC後の経過本数 |
| | `{col}_bc_dc_after` | 転換線DC後の経過本数 |
| | `{col}_pl_diff` | 終値 - 遅行スパン |
| | `{col}_pl_position` | 終値 > 遅行スパンなら1 |
| | `{col}_pl_cross` | GC=1, DC=-1, なし=0 |
| | `{col}_pl_gc_after` | 価格/遅行GC後の経過本数 |
| | `{col}_pl_dc_after` | 価格/遅行DC後の経過本数 |
| | `{col}_ls_diff` | 先行スパン1 - 先行スパン2 |
| | `{col}_ls_position` | 先行スパン1 > 先行スパン2なら1 |
| | `{col}_ls_cross` | GC=1, DC=-1, なし=0 |
| | `{col}_ls_gc_after` | スパン間GC後の経過本数 |
| | `{col}_ls_dc_after` | スパン間DC後の経過本数 |
| | `{col}_cloud_high_diff` | 終値 - 雲の上限 |
| | `{col}_cloud_low_diff` | 終値 - 雲の下限 |
| | `{col}_cloud_position` | 1:雲の上, 0:雲の中, -1:雲の下 |
| | `{col}_cloud_cross` | **1/2/3/4** の4段階（後述） |
| | `{col}_cloud_gc_after1` | cloud_cross==2 後の経過本数 |
| | `{col}_cloud_gc_after2` | cloud_cross==4 後の経過本数 |
| | `{col}_cloud_dc_after1` | cloud_cross==1 後の経過本数 |
| | `{col}_cloud_dc_after2` | cloud_cross==3 後の経過本数 |
| `get_change_price()` | `{col}_price` | 変化「額」 |
| | `{col}_rate` | 変化率 |
| | `{col}_flag` | 1:上昇, -1:下落, 0:変化なし |

---

## 2. 明らかにおかしい

### 2.1 ボリンジャーバンドの `_alpha` → `_sigma` であるべき

```
bb_1min_3piece_upper_1_alpha
bb_1min_3piece_lower_1_alpha
bb_1min_3piece_upper_2_alpha
...
```

**問題:** ボリンジャーバンドはσ（標準偏差）で計算されるにもかかわらず、カラム名に `alpha`（α）を使用している。

- α（アルファ）は金融分野では「超過リターン」「有意水準」「EWMのスムージング係数」などを指す別の概念
- ボリンジャーバンドの各バンドは標準偏差（σ / sigma / sd）で表現するのが業界標準
- 例: TradingView, Bloomberg, Yahoo Finance などはすべて `+1σ`, `+2σ`, `+3σ` と表記

**正しくあるべき名前:**
```
bb_1min_3piece_upper_1sigma  （または _1sd, _1std）
bb_1min_3piece_lower_1sigma
```

**影響範囲:** `get_bollinger_bands()` の出力 6カラム (`upper_N_alpha` / `lower_N_alpha` × 3段階)、および `upper_diff` / `lower_diff` / `position` が `upper_1_alpha` / `lower_1_alpha` を参照しているため、これらのカラム名も一緒に変更する必要がある。

---

### 2.2 `get_change_price()` の `_price` → 「価格変化額」ではなく「価格」に見える

```
change_1min_price   ← 1分間の価格変化「額」（例: +50円）
change_1min_rate    ← 1分間の変化率
change_1min_flag    ← 1/-1/0
```

**問題:** `change_1min_price` は「1分後の価格（終値）」と誤読しやすい。

- 実際の値は `close[i+1] - close[i]`（1分後との差額）
- 「価格」を表す列名に `price` を使っている既存コードと混同するリスクがある（例: `close_price`, `open_price`）

**正しくあるべき名前:**
```
change_1min_amount  または  change_1min_diff
```

`rate` と `flag` については問題ない（変化率・方向フラグとして明確）。

---

### 2.3 `cloud_cross` の値体系が孤立

```python
# bc_cross, pl_cross, ls_cross, macd_cross はすべて
GC = 1 / DC = -1 / なし = 0  （-1/0/1 の3値）

# cloud_cross だけ
1: 雲の上→中（下に入った） = 下方向
2: 雲の中→上（上に出た） = 上方向
3: 雲の中→下（下に出た） = 下方向
4: 雲の下→中（上に入った） = 上方向
```

**問題:** 他のすべてのクロスフラグが `-1/0/1` の3値体系なのに、`cloud_cross` だけ `1/2/3/4` の4値体系。

雲のクロスには4種類のイベントがある（上下 × 貫通か接触か）ことは事実だが、命名が不統一で値の意味も直感的でない（1が「下向きの動き」なのに `gc_after` と組み合わされている）。

さらに `cloud_gc_after1` / `cloud_gc_after2` の対応が不明確:
- `cloud_gc_after1` ← `cloud_cross == 2`（中→上）後の経過本数
- `cloud_gc_after2` ← `cloud_cross == 4`（下→中）後の経過本数
- `cloud_dc_after1` ← `cloud_cross == 1`（上→中）後の経過本数
- `cloud_dc_after2` ← `cloud_cross == 3`（中→下）後の経過本数

`gc_after1` と `gc_after2` の `1`/`2` が「何の1か」をカラム名だけでは判別不可能。

---

## 3. わかりづらい

### 3.1 `_diff` が複数の全く異なる意味で使われている

| カラム例 | `_diff` の意味 |
|---|---|
| `sma_1min_3to5piece_diff` | SMA(3) - SMA(5)（MA間の差） |
| `macd_1min_diff` | MACD - signal（ヒストグラム） |
| `bb_1min_3piece_width_diff` | バンド幅の前本からの変化量（diff(1)） |
| `ichimoku_1min_bc_diff` | 転換線 - 基準線の差 |
| `ichimoku_1min_pl_diff` | 終値 - 遅行スパンの差 |
| `ichimoku_1min_ls_diff` | 先行スパン1 - 先行スパン2の差 |
| `ichimoku_1min_cloud_high_diff` | 終値 - 雲の上限 |
| `ichimoku_1min_cloud_low_diff` | 終値 - 雲の下限 |

`_diff` は「差」全般に使われており意味が広すぎる。特に `macd_diff` と `width_diff` は:
- `macd_diff`: 2系列間の差（MACD - signal）
- `width_diff`: 1系列の時系列変化量（width[i] - width[i-1]）

同じ `_diff` だが計算の種類が根本的に異なる。

---

### 3.2 `_diff_flag` が何のフラグか読み取りにくい

```
macd_1min_diff_flag   ← MACDヒストグラム(diff)が正値(>0)なら1
```

「diff のフラグ」という命名だが、「ヒストグラムが正かどうか」という意味であることが一見わからない。

比較: 同じ「買いサイン的な正方向」を表す他のカラム:
```
sma_1min_3to5piece_golden_cross   ← ゴールデンクロスフラグ（明確）
macd_1min_diff_flag               ← ？（MACDがプラスのヒストグラムになったフラグ）
```

`macd_1min_hist_positive` や `macd_1min_above_signal` の方が意図が伝わりやすい。

---

### 3.3 `{count}_slope` の count 部分が曖昧

```
macd_1min_1_slope       ← 1本前との差
macd_1min_3_slope       ← 3本前との差
macd_1min_signal_1_slope
```

**問題点①:** カラム名に数字が単体で現れるため、何の数字か読み取りにくい。
- `macd_1min_1_slope` → 「1分足のMACDの1の傾き」= 1本前との差？ 1期間の傾き？
- `sma_1min_3piece` の `3piece` と異なり、`1_slope` の `1` の単位が不明確

**問題点②:** `signal` が入ると `macd_1min_signal_1_slope` となり、区切りの規則が変わって見える。

`_slope_1bar`, `_slope_3bar` のようにしてバー数を明示した方が読みやすい。

---

### 3.4 `upper_diff` と `lower_diff` の符号方向が逆

```python
upper_diff = price - upper_1_alpha    # 価格が上限より高いと正
lower_diff = lower_1_alpha - price    # 価格が下限より低いと正
```

**問題:** 両カラムとも「バンドを外れたときに正値」になる設計で意図は理解できるが、差の方向（引き算の向き）が逆。

- `upper_diff > 0` = 上限を超えている（買われすぎ方向）
- `lower_diff > 0` = 下限を割り込んでいる（売られすぎ方向）

直感的には「価格と上限の差 = upper_diff」は符号が逆（上限より低い = 負）の方が自然。
一貫性があれば良いが、「どちらが基準か」が列名から読み取れないため、利用時に混乱しやすい。

---

### 3.5 `get_parabolic()` の `_flag` が何の flag か

```
sar_1min_0.02_0.2af_flag   ← 「SARが前本のSARより高い」なら1
```

「フラグ」という名前だが、「SARの方向（上昇中か下降中か）」を表す。
`_trend_up` や `_up_trend` の方が意味が明確。

---

## 4. 統一性がない

### 4.1 フラグ系カラムの値体系が3種類存在する

| 値体系 | 使用箇所 |
|---|---|
| **0 / 1** | `parabolic_flag`, `parabolic_reverse_flag`, `bc_position`, `pl_position`, `ls_position`, `golden_cross`, `dead_cross`, `macd_diff_flag`, `macd_mismatch` |
| **-1 / 0 / 1** | `bc_cross`, `pl_cross`, `ls_cross`, `macd_cross`, `change_flag`, `cloud_position` |
| **1 / 2 / 3 / 4** | `cloud_cross` のみ |

同じ「クロス」系でも `ma_cross` は `golden_cross`(0/1) + `dead_cross`(0/1) の分離型、`macd_cross` は -1/0/1 の統合型と設計思想が違う。

---

### 4.2 `get_parabolic()` と `get_parabolic_hlc()` の出力カラムが非対称

| メソッド | 出力カラム |
|---|---|
| `get_parabolic()` | `{col}`, `{col}_flag` （2列） |
| `get_parabolic_hlc()` | `{col}`, `{col}_flag`, `{col}_reverse_flag` （3列） |

同じSARを計算する同系統のメソッドなのに出力が違う。
`reverse_flag`（トレンド反転したかどうか）は `get_parabolic()` にも有用なはずだが存在しない。

---

### 4.3 「GC後経過本数」の命名パターンが一致しない

| 場所 | カラム名 | 説明 |
|---|---|---|
| `get_ma_cross()` | `golden_cross_after` | GC後の経過本数 |
| `get_ma_cross()` | `dead_cross_after` | DC後の経過本数 |
| `get_ichimoku_cloud()` | `bc_gc_after` | GC後の経過本数（省略形） |
| `get_ichimoku_cloud()` | `bc_dc_after` | DC後の経過本数（省略形） |

同じ概念なのに:
- `get_ma_cross()`: `{full_name}_after`（`golden_cross_after`）
- `get_ichimoku_cloud()`: `{abbrev}_gc_after`（`bc_gc_after`）

パターンが異なる。一目均衡表側では `golden`/`dead` という言葉が消えて `gc`/`dc` に短縮されている。

---

### 4.4 カラム名に小数点（`.`）が含まれる

`get_parabolic()` の呼び出し側（`board_mold.py`）で生成されるカラム名:
```
sar_1min_0.02_0.2af
sar_1min_0.02_0.2af_flag
```

小数点 `.` はPandasのDataFrameの列名として使用は可能だが:
- `df.sar_1min_0.02_0.2af` という属性アクセス構文が使えない（`.` が区切り文字に見える）
- MySQLのカラム名として使用する場合、バッククォートが必要
- CSV出力後に他のツールで読み込む際に問題になる可能性がある

`0.02` → `002`（または `0p02`）のように小数点を別の文字に置換するか、`af=002_010` のような表記にした方が安全。

---

### 4.5 `_position` の定義が2種類ある

| カラム | 値の範囲 | 意味 |
|---|---|---|
| `bb_1min_3piece_position` | 連続値（実数、-∞〜+∞、通常0〜1） | ±1σバンド内の相対位置（0=下限, 1=上限） |
| `ichimoku_1min_bc_position` | 0 または 1 | 転換線 > 基準線なら1、そうでなければ0 |
| `ichimoku_1min_cloud_position` | -1, 0, 1 | 1=雲の上, 0=雲の中, -1=雲の下 |

同じ `_position` という接尾辞が連続実数・2値フラグ・3値フラグと3種類の異なる意味で使われている。

---

## 5. 修正推奨まとめ

### 優先度：高（意味の誤解を生む）

| # | 対象カラム | 問題 | 推奨変更 |
|---|---|---|---|
| 1 | `bb_*_upper_N_alpha` / `lower_N_alpha` | `alpha` は σ ではない | `upper_Nsigma` / `lower_Nsigma` |
| 2 | `change_1min_price` | 「価格変化額」なのに「price」 | `change_1min_amount` |
| 3 | `cloud_cross` の値 `1/2/3/4` | 他の cross 系と値体系が不統一 | 別途設計を再検討（後述） |

### 優先度：中（理解に手間がかかる）

| # | 対象カラム | 問題 | 推奨変更 |
|---|---|---|---|
| 4 | `macd_1min_1_slope` 等 | count の単位が不明 | `macd_1min_slope_1bar` 等 |
| 5 | `macd_1min_diff_flag` | 「histogramが正」とは読み取れない | `macd_1min_hist_positive` |
| 6 | `parabolic_flag` | 「上昇方向」とは読み取れない | `parabolic_up_trend` |
| 7 | `cloud_gc_after1` / `cloud_gc_after2` | `1`/`2` が何を指すか不明 | より具体的な名前（後述） |

### 優先度：低（統一できれば望ましい）

| # | 対象カラム | 問題 | 推奨変更 |
|---|---|---|---|
| 8 | `sar_*_0.02_0.2af` 等 | カラム名に小数点が含まれる | `sar_*_002_020af` 等 |
| 9 | `get_parabolic()` の `reverse_flag` 欠如 | `parabolic_hlc` との非対称 | `get_parabolic()` にも追加 |
| 10 | `upper_diff` / `lower_diff` の符号 | 引き算の向きが逆で直感に反する場合あり | コメントで明示する（変更は影響大） |
| 11 | `golden_cross_after` vs `bc_gc_after` | 同概念だが命名パターンが違う | どちらかに統一 |

---

### `cloud_cross` の再設計案（参考）

現状:
```
cloud_cross = 1: 上→中（上から雲に入った）
cloud_cross = 2: 中→上（雲から上に抜けた）
cloud_cross = 3: 中→下（雲から下に抜けた）
cloud_cross = 4: 下→中（下から雲に入った）
```

問題: `gc_after1` が `cloud_cross==2`（上抜け）に対応するが、これは確かに「強気＝ゴールデンクロス」相当だが、`cloud_cross==4`（下から雲に入る）が `gc_after2` というのは「ゴールデンクロス」ではなく「弱いシグナル」に近い。gc/dc という言葉自体が一目均衡表の雲に適切かは再検討の余地がある。

最低限の改善案（値体系を変えずに `_after` カラムを分かりやすく）:
```
cloud_gc_after1  →  cloud_breakout_up_after    （雲上抜け後 = cloud_cross==2）
cloud_gc_after2  →  cloud_entry_up_after       （下から雲に入った後 = cloud_cross==4）
cloud_dc_after1  →  cloud_entry_down_after     （上から雲に入った後 = cloud_cross==1）
cloud_dc_after2  →  cloud_breakout_down_after  （雲下抜け後 = cloud_cross==3）
```

---

*このドキュメントは issue #47 実装前調査の補足資料です。命名変更は学習データとの互換性に影響するため、変更する場合は `board_mold.py` / `past_record_mold.py` および既存の学習済みモデルとの整合性を確認すること。*
