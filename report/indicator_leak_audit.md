# テクニカル指標リーク監査レポート

`src/util/indicator.py` を全面確認した結果、**遅行スパン（lagging_span）の算出に未来データ参照（look-ahead bias）が発生している**ことが判明した。本レポートはリーク箇所と影響範囲を記録する。

## 1. リーク本体

[`src/util/indicator.py:828`](../src/util/indicator.py:828):

```python
df_resampled[lagging_span] = df_resampled[close_column_name].shift(-long_window_size)
```

`shift(-26)` は **負方向シフト** であり、行 `t` の値は `close[t+26]` を参照する。
時刻 `t` の演算で 26分後の終値を参照しているため、**学習・バックテスト・実運用すべてで使用不可** の未来値である。

### 一目均衡表における「遅行スパン」の本来の意味

一目均衡表における遅行スパン（Chikou Span）は **「現在の終値を 26 本前にプロットしたもの」** であり、可視化上の表現でしかない。シグナル検出として使う場合は「現在の終値が **26本前の終値** を上抜け／下抜けしたか」を見るのが筋であり、その場合の式は:

```python
lagging_span[t] = close[t - 26]   # 正方向シフト = .shift(26)
```

となる。現在のコード `shift(-26)` は正反対の挙動になっている。

## 2. リークしているカラム一覧（合計 6 カラム）

`lagging_span` を直接または間接的に参照しているカラム。
[`src/util/indicator.py:828, 845-858`](../src/util/indicator.py:828) より列挙。

| # | カラム名 | 算出式 | 該当行 |
|---|---|---|---|
| 1 | `ichimoku_1min_lagging_span` | `close.shift(-26)` （リーク本体） | 828 |
| 2 | `ichimoku_1min_pl_diff` | `close - lagging_span` | 846 |
| 3 | `ichimoku_1min_pl_position` | `(close > lagging_span).astype(int)` | 847 |
| 4 | `ichimoku_1min_pl_cross` | `close` と `lagging_span` のクロス判定（±1） | 850-852 |
| 5 | `ichimoku_1min_pl_gc_after` | `pl_cross == 1` 発火からの経過バー数 | 855-856 |
| 6 | `ichimoku_1min_pl_dc_after` | `pl_cross == -1` 発火からの経過バー数 | 857-858 |

`pl_*` プレフィックスの全カラムが該当する。

## 3. 統計集計への波及

`csv/statistics/` 配下の以下の行は **未来情報を含むため信頼できない**:

| ファイル | 該当行の条件 |
|---|---|
| `statistics_1_signal_accuracy_*.csv` | `signal_col == 'ichimoku_1min_pl_cross'` |
| `statistics_3_bars_after_cross_*.csv` | `after_col == 'ichimoku_1min_pl_gc_after'` または `'ichimoku_1min_pl_dc_after'` |

該当統計の極端な勝率（DC nbar=30 で 69.0%、GC nbar=30 で 70.6% 下落）はリークの直接帰結であり、実運用シグナルとしての価値はない。

### リーク仮説の検証

`pl_cross == -1`（DC）の発火条件を展開すると:

```
close[t] < lagging_span[t]  AND  close[t-1] > lagging_span[t-1]
↓
close[t] < close[t+26]      AND  close[t-1] > close[t+25]
```

つまり DC 発火は「**26分後の終値が現在より高い**」が発火条件に直接含まれる。
nbar=30 における 69% 勝率はこの未来情報の直接観測。一方 nbar=1〜5 では勝率 0.49 と無相関で、26分以内のレンジには予測力がないことが裏付けられ、リーク仮説と完全に整合する。

## 4. リークしていない一目カラム（安全、参考）

`leading_span_a/b` は `shift(long_window_size)`（**正方向シフト**）で算出されており、行 `t` の値は `t-26` の過去データを参照する。

[`src/util/indicator.py:822, 825`](../src/util/indicator.py:822):

```python
df_resampled[leading_span_a] = (((conversion_line + base_line) / 2).shift(long_window_size)).round(3)
df_resampled[leading_span_b] = ((rolling_max + rolling_min) / 2).shift(long_window_size).round(3)
```

依存して算出される以下のカラムはすべて安全（過去データのみ使用）:

- `ichimoku_1min_base_line`, `ichimoku_1min_conversion_line`
- `ichimoku_1min_leading_span_a`, `ichimoku_1min_leading_span_b`
- `ichimoku_1min_bc_diff`, `bc_position`, `bc_cross`, `bc_gc_after`, `bc_dc_after`
- `ichimoku_1min_ls_diff`, `ls_position`, `ls_cross`, `ls_gc_after`, `ls_dc_after`
- `ichimoku_1min_cloud_high_diff`, `cloud_low_diff`, `cloud_position`, `cloud_cross`
- `ichimoku_1min_cloud_breakout_up_after`, `cloud_breakout_down_after`
- `ichimoku_1min_cloud_entry_up_after`, `cloud_entry_down_after`

## 5. 他の指標における負方向シフトの確認

`indicator.py` 全体の `.shift(-` を grep で検索した結果、負方向シフトは 2 箇所のみ:

| 行 | 用途 | リーク？ |
|---|---|---|
| 828 | `lagging_span` 算出 | **YES（本件）** |
| 947 | `change_amount = close.shift(-interval) - close`（変動価格 = 教師ラベル） | NO（正解ラベルなので意図通り） |

→ **テクニカル指標側で未来参照しているのは `lagging_span` 系統のみ**。他の SMA/EMA/WMA/RSI/RCI/MACD/BB/SAR/PSY およびクロス検出はすべて過去データのみで安全。

## 6. 推奨対応

1. **コード修正**: `indicator.py:828` を `shift(long_window_size)` に変更し、`lagging_span[t] = close[t-26]` の正規式に修正する
2. **再集計**: 修正後に `indicator_statistics.py` を再実行し、`csv/statistics/` を上書き更新する
3. **戦略策定の前提から `pl_*` を除外**（本レポートの兄弟ファイル `trading_strategy_recommendations.md` を再生成）
4. リーク修正後の `pl_*` 系は実質「現在の終値 vs 26本前の終値」になるため、独立指標としての価値は薄い。SMA・MACD と冗長になりやすいため、必ずしも統計①〜⑥に組み込む必要はない

## 7. まとめ

- **リークカラム数**: 6（全て `ichimoku_1min_pl_*` および `lagging_span`）
- **影響統計ファイル**: `statistics_1_*` の `pl_cross` 行、`statistics_3_*` の `pl_gc/dc_after` 行
- **本件起因の偽勝率**: nbar=30 で 69-71%（実運用では再現不能）
- **修正コスト**: 1行（`shift(-26)` → `shift(26)`）+ 統計再集計
