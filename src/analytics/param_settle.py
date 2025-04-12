import os
import pandas as pd

# 入力CSVファイルのパス
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

# CSVに出力
pivot_df.to_csv(output_csv_path, index=False)