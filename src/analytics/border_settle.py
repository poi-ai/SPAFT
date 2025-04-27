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

# 日ごと、特徴量ごとの閾値を記録しているCSVファイルのパス
result_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result')
border_path = os.path.join(result_dir, 'border_value.csv')
border_settle_path = os.path.join(result_dir, 'border_settle.csv')

# 出力先のCSVファイルが存在しない場合はファイル作成をしてヘッダーを追加
if not os.path.exists(border_settle_path):
    with open(border_settle_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['column', 'min', '1per', '5per', '10per', '25per', '50per', '75per', '90per', '95per', '99per'])

# 閾値を記録しているCSVファイルを読み込む
border_df = pd.read_csv(border_path)

# 特徴量の一覧を重複なしで取得
feature_list = border_df['column'].unique()

for feature in tqdm(feature_list):
    # 特徴量ごとにデータをフィルタリング
    feature_df = border_df[border_df['column'] == feature]

    for min in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
        # minごとにデータをフィルタリング
        min_df = feature_df[feature_df['min'] == min]

        # 各閾値ごとの平均値を計算する
        mean_values = min_df[['1per', '5per', '10per', '25per', '50per', '75per', '90per', '95per', '99per']].mean().round(3)

        # nanのデータを空文字に置き換える
        mean_values = mean_values.fillna('')

        # データをCSVの末尾に出力する
        with open(border_settle_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([feature, min] + mean_values.tolist())
