import os
import pandas as pd

# CSVファイルのパス
input_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'param_rate.csv')
output_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'param_rate_summary.csv')

# CSVを読み込み
df = pd.read_csv(input_csv_path)

# 1と0の数を削除
df = df.drop(columns=['one_num', 'zero_num'])

# column, updown, per, minでグループ化し、dateとone_rateをピボット形式に変換
pivot_df = df.pivot_table(
    index = ['column', 'updown', 'per', 'min'],
    columns = 'date',
    values = 'one_rate',
    aggfunc = 'first'
).reset_index()

# カラム名をフラット化
pivot_df.columns.name = None

# ピボット形式の値のみを抽出 最初の4列はグループ化キーなので除外
pivot_values = pivot_df.iloc[:, 4:]

# 最小値、最大値、平均、分散、2α、-2αを計算して新しいカラムとして追加
pivot_df['min_value'] = pivot_values.min(axis=1)
pivot_df['max_value'] = pivot_values.max(axis=1)
pivot_df['mean_value'] = pivot_values.mean(axis=1).round(2)
pivot_df['std_dev'] = (pivot_values.var(axis=1) ** 0.5).round(4)
pivot_df['plus_2alpha'] = (pivot_df['mean_value'] + 2 * pivot_df['std_dev']).round(2)
pivot_df['minus_2alpha'] = (pivot_df['mean_value'] - 2 * pivot_df['std_dev']).round(2)

# CSVに出力
pivot_df.to_csv(output_csv_path, index=False)