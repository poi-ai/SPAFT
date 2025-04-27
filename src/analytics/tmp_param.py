import columns_manage as cm
import csv
import os
import pandas as pd
import re
import sys
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from util.log import Log

log = Log()

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
border_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'bak_border_value.csv')
output_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'border_value.csv')

# border_csv_pathを読み込む
df = pd.read_csv(border_csv_path)

# 新規カラムminを設定
min_values = [1, 2, 3, 5, 10, 15, 30, 60, 90]
df['min'] = [min_values[i % len(min_values)] for i in range(len(df))]

# minカラムの位置を左から3番目に移動
df = df[['date', 'column', 'min'] + [col for col in df.columns if col not in ['date', 'column', 'min']]]

# output_csv_pathに出力
df.to_csv(output_csv_path, index=False)