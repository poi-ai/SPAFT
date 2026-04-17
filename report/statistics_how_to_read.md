# 統計情報CSVの読み方ガイド

`src/indicator_statistics.py` を実行すると `csv/statistics/` 配下に6種類の統計情報CSVが出力される。
このドキュメントは各CSVの読み方と、RPAエントリー条件を設計する際の活用方法を解説する。

## 出力ファイル一覧

| ファイル名 | 対応する統計 | 目的 |
|---|---|---|
| `statistics_1_signal_accuracy.csv` | ①シグナル精度統計 | 既知シグナル（GC/DC/逆転）の精度検証 |
| `statistics_2_bucket.csv` | ②バケット別精度統計 | オシレーター値域ごとの精度分布 |
| `statistics_3_bars_after_cross.csv` | ③クロス後経過本数別 | クロスから何本後までエントリー有効か |
| `statistics_4_threshold.csv` | ④閾値以上/以下統計 | 未知シグナルの発掘（探索の主体） |
| `statistics_5_bb_sigma.csv` | ⑤BBσ位置別統計 | 逆張り（平均回帰）エントリー候補 |
| `statistics_6_price_ma_position.csv` | ⑥価格とMA位置関係 | トレンドフォロー条件の補助 |

## 共通カラムの意味

全CSVに含まれる基本的な指標カラムは以下の通り。

| カラム名 | 意味 | 読み方のポイント |
|---|---|---|
| `nbar` | 何本後の予測か（1, 3, 5, 10, 15, 30） | 分足なので `nbar=5` は5分後 |
| `sample_count` | 条件に該当したサンプル（行）数 | **30未満の行は参考値扱い** |
| `rise_count` | `nbar`本後に上昇（flag==1）した数 | |
| `flat_count` | `nbar`本後に変化なし（flag==0）の数 | 呼値単位で動かなかった分 |
| `fall_count` | `nbar`本後に下落（flag==-1）した数 | |
| `rise_rate` | 上昇率 = `rise_count / sample_count` | **0.55以上なら偏りあり** |
| `fall_rate` | 下落率 = `fall_count / sample_count` | |
| `amount_mean` | 変動額の平均（円） | 呼値のマイナス側も含む期待値 |
| `amount_std` | 変動額の標準偏差（円） | 大きいほど値動きが荒い |
| `amount_median` | 変動額の中央値（円） | 平均より外れ値に強い |
| `rate_mean` | 変動率（0〜1スケール）の平均 | 0.001 = 0.1% |
| `rate_std` | 変動率の標準偏差 | |

### 確率の目安

| `rise_rate` の値 | 解釈 |
|---|---|
| ~0.50 | ランダム相当。シグナルとしての価値は低い |
| 0.50〜0.55 | わずかに偏りあり。複数条件を重ねる素材 |
| 0.55〜0.60 | 単独でも有効性が見込める |
| 0.60以上 | 強いシグナル候補（ただしサンプル数を確認） |

`fall_rate` も同様に0.55以上なら「下落する」という信号として使える（=売りエントリー候補、または買いを避ける条件）。

`rise_rate + fall_rate + flat_rate = 1.0` の関係にある。値幅の小さい銘柄では `flat_rate` が大きくなる。

### サンプル数の注意

- `sample_count < 30`: 統計的信頼性が低い。採用判断には使わない
- `sample_count < 100`: 参考値。他のnbarの結果と整合しているか確認
- `sample_count >= 100`: 実用的な判断材料になる

---

## ①シグナル精度統計 (`statistics_1_signal_accuracy.csv`)

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `signal_col` | 発火判定したシグナルカラム名 |
| `signal_type` | `golden_cross` / `dead_cross` / `reverse` |

### 集計単位

シグナルカラム × シグナル種別 × nbar = 1行。
`rise_count + flat_count + fall_count == sample_count` で、`sample_count` はそのシグナルが発火した回数。

### 読み方の例

```
signal_col=sma_1min_5to25piece_golden_cross, signal_type=golden_cross, nbar=5, sample_count=120, rise_rate=0.62
```

→ SMA5とSMA25のゴールデンクロス発火後、5分後に上昇する確率は62%。120サンプルなら実用判断に使える。

### 活用方針

- **rise_rate が 0.55+ のシグナルをRPAのエントリー条件に採用する**
- 同じシグナルでも `nbar` によって精度が変わる。利確までの保有時間を決める参考にする
- GC系で `fall_rate > rise_rate` なら「教科書通りに動かないシグナル」として警戒

### 既知の落とし穴

- SAR の `signal_type=reverse` は GC/DC の区別がない（トレンド反転フラグのみ）。前後のトレンド方向は別途 `sar_1min_up_trend` で確認が必要
- 一目均衡表の `cloud_cross` は設計書上 `==1` を GC、`==2` を DC としているが、`indicator.py` の実装では「2=雲の中→上（=上抜けGC）」「3=雲の中→下（=下抜けDC）」という割当になっている。**解釈が逆転している可能性があるので採用時は要確認**

---

## ②バケット別精度統計 (`statistics_2_bucket.csv`)

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `oscillator_col` | オシレーターカラム名 |
| `bucket_label` | バケットラベル（例: `[30.0, 40.0)` or `Q1`〜`Q4`） |
| `bucket_left` | バケット下限値 |
| `bucket_right` | バケット上限値 |

### バケットの構造

| 指標 | 分割方式 | ラベル |
|---|---|---|
| `rsi_1min_{9,14}piece` | 0〜100を10刻み | `[0.0, 10.0)` 〜 `[90.0, 100.0]` |
| `rci_1min_{9,26}piece` | -100〜100を20刻み | `[-100.0, -80.0)` 〜 `[80.0, 100.0]` |
| `psy_1min_12piece` | 0〜100を10刻み | 同上 |
| `bb_1min_20piece_position` | 0〜1（clip）を0.1刻み | `[0.0, 0.1)` 〜 `[0.9, 1.0]` |
| `macd_1min_diff` | 四分位 | `Q1` 〜 `Q4` |
| `bb_1min_20piece_width` | 四分位 | `Q1` 〜 `Q4` |

**半開区間**: `[a, b)` は `a <= value < b`。最後のバケットだけ `[a, b]` の閉区間（100や1.0の値を取りこぼさないため）。

### 読み方の例

```
oscillator_col=rsi_1min_14piece, bucket_label=[20.0, 30.0), nbar=3, sample_count=450, rise_rate=0.58
```

→ RSI14が20-30の範囲にいるとき、3分後に上昇する確率は58%（売られすぎからの反発が観察されている）。

### 活用方針

- **どの値域で偏りが発生しているか** を可視化できる。既知のRSIオーバーソールド（20以下買い）/オーバーボート（80以上売り）のような境界を、**自分のデータで検証**できる
- 分布の両端でサンプル数が少なくなりがち。中央のバケット（RSI40-60等）は `flat_rate` が支配的で情報量が低いことが多い
- `macd_1min_diff` / `bb_1min_20piece_width` は値域が銘柄依存のため四分位で分割。**絶対値の閾値ではなく相対的な位置**で判断する

### 統計④との違い

- 統計②は「バケット内のサンプル」=「その値域 **のみ** の行」で集計
- 統計④は「閾値以上/以下」=「境界を含む **累積的** な範囲」で集計
- 個別値域での傾向を見るなら統計②、「RSI 30以上ならどうなるか」を見るなら統計④

---

## ③クロス後経過本数別精度統計 (`statistics_3_bars_after_cross.csv`)

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `after_col` | バーカウントカラム名（例: `sma_1min_5to10piece_golden_cross_after`） |
| `cross_type` | `golden_cross` / `dead_cross` |
| `bars_elapsed` | クロス発生からの経過バー数（0=クロス発生本そのもの） |

### bars_elapsed の意味

```
クロス発生バー → bars_elapsed=0
次の1本後      → bars_elapsed=1
次の2本後      → bars_elapsed=2
...
次のクロス発生でカウンターがリセット → bars_elapsed=0
```

各値は「そのクロスからN本経過した状態で、さらにnbar本後の価格がどう動いたか」を表す。

### 読み方の例

```
after_col=sma_1min_5to10piece_golden_cross_after, cross_type=golden_cross,
bars_elapsed=2, nbar=3, sample_count=85, rise_rate=0.55
```

→ SMA5とSMA10のGC発生から2本経過した時点でエントリーすると、3分後に55%の確率で上昇。

### 活用方針

- **エントリー猶予本数の決定に使う**: 「GC発生本にエントリーできなかったが、まだ間に合うか？」を判断
- `bars_elapsed=0`（発生本）が最も精度が高く、本数が経つにつれて精度が落ちる傾向が典型
- `bars_elapsed` が大きい行は `sample_count` が小さくなりやすい（次のクロスまでの期間が長いケースは少ない）ので、サンプル数を必ず確認
- 1本足にこだわらず、遅れて発火しても精度が落ちないシグナルを見つけられれば、実行コスト（発注タイミングの緩和）が下がる

---

## ④閾値以上/以下統計 (`statistics_4_threshold.csv`)

**未知シグナル発掘の主体となる統計。** 最も重点的に見るファイル。

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `indicator_col` | 指標カラム名 |
| `threshold` | 閾値 |
| `direction` | `above`（`value >= threshold`） / `below`（`value <= threshold`） |

### 閾値の体系

| 指標 | 閾値 | 備考 |
|---|---|---|
| `rsi_1min_*piece` | 10, 20, 30, 40, 50, 60, 70, 80, 90 | 固定 |
| `rci_1min_*piece` | -80, -60, -40, -20, 0, 20, 40, 60, 80 | 固定 |
| `psy_1min_12piece` | 10, 20, 30, 40, 50, 60, 70, 80, 90 | 固定 |
| `bb_1min_20piece_position` | 0.1〜0.9（0.1刻み） | 固定 |
| `macd_1min_diff` | Q25, 0, Q75 | **動的**（全データから算出） |
| `bb_1min_20piece_width` | Q25, Q50, Q75 | **動的** |
| `{sma,ema,wma}_1min_*piece_diff` | 0 | 正負判定 |
| `ichimoku_1min_bc_diff`<br>`ichimoku_1min_cloud_high_diff`<br>`ichimoku_1min_cloud_low_diff` | 0 | 正負判定 |

### above と below の性質

- `above`: `value >= threshold` を満たす行
- `below`: `value <= threshold` を満たす行
- 境界値（`value == threshold`）は両方に含まれる（重複ではなく、両条件で再集計している）

### 読み方の例

```
indicator_col=rci_1min_9piece, threshold=-80, direction=above, nbar=5, sample_count=1500, rise_rate=0.54
indicator_col=rci_1min_9piece, threshold=-80, direction=below, nbar=5, sample_count=200, rise_rate=0.63
```

→ 「RCI9が-80以下（深い売られすぎ）にあるとき、5分後に63%の確率で上昇」という強いシグナル候補。逆張り買いの根拠に使える。

### 活用方針

1. **`rise_rate` または `fall_rate` が 0.6+ の行をフィルタ**
2. `sample_count >= 100` を満たす行に絞る
3. 同じ `indicator_col` で `nbar` を変えたときに精度が持続するか確認
4. 複数の指標を組み合わせて条件を重ねる（例: RSI14 < 30 **かつ** BB_position < 0.1）

### 分析のコツ

- `above`/`below` の偏りを見る: 片方だけ精度が高ければ「その値域から先」で何かが起きている証拠
- `macd_diff` の `threshold=0` で `above`/`below` を比較すると、MACD の正負がバイアスを持つかが分かる
- MA の `_diff` 列は「短期MA > 長期MA」の状態判定と等価。GC後の持続時間よりこちらの方がサンプル数が多く信頼性が高い

---

## ⑤BBσ位置別統計 (`statistics_5_bb_sigma.csv`)

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `condition_name` | BBとcloseの位置関係条件 |

### 条件の意味

| `condition_name` | 判定式 | 含意 |
|---|---|---|
| `1sigma_above` | `close > upper_1sigma` | +1σ超え（やや上） |
| `2sigma_above` | `close > upper_2sigma` | +2σ超え（買われすぎ） |
| `3sigma_above` | `close > upper_3sigma` | +3σ超え（異常値） |
| `1sigma_below` | `close < lower_1sigma` | -1σ割れ（やや下） |
| `2sigma_below` | `close < lower_2sigma` | -2σ割れ（売られすぎ） |
| `3sigma_below` | `close < lower_3sigma` | -3σ割れ（異常値） |
| `within_1sigma` | `lower_1sigma <= close <= upper_1sigma` | ±1σ内（平穏） |

**重複に注意**: `3sigma_above` の行は `2sigma_above` にも `1sigma_above` にも含まれる（累積的な条件）。

### 読み方の例

```
condition_name=2sigma_below, nbar=3, sample_count=180, rise_rate=0.64
```

→ 価格が-2σを割り込んでいるとき、3分後に64%の確率で上昇（平均回帰）。逆張り買いのエントリー候補。

### 活用方針

- **逆張りエントリーの根拠**: `Nsigma_above` で `fall_rate` が高い、`Nsigma_below` で `rise_rate` が高い、という**平均回帰**が観察できるか確認
- **トレンド継続の証拠**: 逆に `2sigma_above` で `rise_rate` が高ければ「強いブレイクアウト継続中」というシグナルになる（順張り）
- `within_1sigma` はレンジ相場の指標。`flat_rate` が高く、どちらのシグナルも出にくい

### 統計④ `bb_position` との違い

- 統計④は `bb_position` の**値**（0〜1）で判定
- 統計⑤は `close` と**バンド上下限の直接比較**で判定（2σ、3σなど`bb_position`では表現できない範囲も扱える）

---

## ⑥価格と移動平均の位置関係統計 (`statistics_6_price_ma_position.csv`)

### 固有カラム

| カラム名 | 意味 |
|---|---|
| `ma_col` | 比較対象のMAカラム名 |
| `position` | `above`（`close > ma`） / `below`（`close < ma`） |

### 対象カラム

- `sma_1min_{5,10,20,25}piece`
- `ema_1min_{5,10,20,25}piece`
- `wma_1min_{5,10,20,25}piece`
- `ichimoku_1min_base_line`（基準線）
- `ichimoku_1min_conversion_line`（転換線）

### 読み方の例

```
ma_col=sma_1min_5piece, position=above, nbar=5, sample_count=3000, rise_rate=0.52
```

→ close > SMA5 の状態から5分後に上昇する確率は52%。サンプル数は十分だが、単独では優位性は弱い。

### 活用方針

- **トレンドフォローの基礎条件**として使う。単独では弱い条件だが、他のシグナルとANDで組み合わせる
- 短期MA（5）より長期MA（25）の方が「トレンド方向」の精度指標になる
- 基準線・転換線（一目均衡表）との位置関係は、雲（統計⑤の対象）より反応が速い

### 統計④ MA `_diff` との違い

- 統計④は `short_ma - long_ma` の正負（MA同士の位置関係）
- 統計⑥は `close - ma` の正負（**価格とMAの位置関係**）
- 統計⑥の方が「今エントリーすべきか」を直接的に表す

---

## 統計を組み合わせる発想

単独統計だけでは「ランダムよりわずかに有利」程度のシグナルしか得られないことが多い。
複数統計で共通する条件を重ねることで確率を底上げする。

### 例1: 逆張り買いの多重条件
- 統計④: `rci_1min_9piece <= -80` で `rise_rate >= 0.60`
- 統計⑤: `2sigma_below` で `rise_rate >= 0.60`
- 統計⑥: `close < sma_1min_5piece`（既に短期下落中）

→ この3条件がすべて満たされたときにエントリー、とすれば単独条件より精度が上がる可能性が高い。

### 例2: 順張り買いの多重条件
- 統計①: `sma_1min_5to10piece_golden_cross` で `rise_rate >= 0.55`
- 統計③: `bars_elapsed <= 2`（発生から2本以内）
- 統計⑥: `close > sma_1min_25piece`（中期トレンドも上向き）
- 統計④: `rsi_1min_14piece >= 50` かつ `<= 70`（過熱していない）

### 検証の進め方

1. 統計④ で最も `rise_rate` が高い条件を抽出
2. その条件が発火した行に対して、統計⑤/⑥の条件を組み合わせて精度がさらに上がるかを確認
3. 実装時は行単位のマスクで再集計する（この統計CSVからは読み取れないため、`csv/indicator/*_with_indicators.csv` を直接集計する必要あり）

## 各CSVの採用判断フロー

```
CSVを開く
  ↓
sample_count >= 100 でフィルタ
  ↓
rise_rate >= 0.55 または fall_rate >= 0.55 でソート
  ↓
上位の条件について nbar を変えても精度が維持されるか確認
  ↓
別の統計CSVで同じ局面を見たときに矛盾がないか確認
  ↓
バックテスト/フォワードテスト（別途実装）
```

## 参考

- 設計書: `report/statistics_design.md`
- 入力データの生成元: `csv/indicator/*_with_indicators.csv`
- 生成スクリプト: `src/indicator_statistics.py`
