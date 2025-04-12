import columns_manage as cm
import csv
import os
import pandas as pd
import re
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from util.log import Log

log = Log()

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
output_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'param_rate.csv')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_20250\d{3}.csv', csv_file)]


for csv_file in csv_files:

    # CSVファイルの読み込み
    df = pd.read_csv(os.path.join(data_dir, csv_file))

    # リークを起こすカラムは取り除く
    df = df.drop(columns = cm.leak_columns_ichimoku)

    percents = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]

    # 各カラムのデータ型の確認
    for column in df.columns:
        if column in cm.leak_columns:
            continue

        if column in ['stock_code', 'hour', 'minute', 'get_minute', 'open', 'high', 'low', 'close', 'volume', 'day_of_week', 'date']:
            continue

        train_df = df.copy()
        col = train_df[column]

        if col.dtype == 'int64' or col.dtype == 'float64':
            max_value, min_value = col.max(), col.min()
            # 1%, 5%, 10%, 25%, 50%, 75%, 90%, 95%, 99%の値を取得
            quantiles = col.quantile(percents).values
            for i, q in enumerate(quantiles):
                try:
                    # ここでqには1%, 5%, 10%, 25%, 50%, 75%, 90%, 95%, 99%の値が入る
                    # qを閾値とした、q以上を1、q未満を0のカラムを追加
                    col_name = f'{column}_{int(percents[i] * 100)}per'
                    train_df[col_name] = (col >= q).astype(int)

                    for min in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
                        uni_df = train_df[[col_name, f'change_{min}min_rate', f'change_{min}min_flag']].copy()

                        # 変動がなかったレコードは削除
                        uni_df = uni_df[uni_df[f'change_{min}min_rate'] != 0]
                        # カラムがNanのレコードは削除
                        uni_df = uni_df[uni_df[f'change_{min}min_rate'].notnull()]
                        uni_df = uni_df[uni_df[col_name].notnull()]

                        # qが1のレコードと0のレコードの切り出し
                        uni_df_1 = uni_df[uni_df[col_name] == 1]
                        uni_df_0 = uni_df[uni_df[col_name] == 0]
                        #change_min_flag = uni_df.loc[col >= q, f'change_{min}min_flag'].value_counts()

                        # uni_df_1と0のchange_min_flagの値をカウント
                        change_min_flag_1 = uni_df_1[f'change_{min}min_flag'].value_counts()
                        change_min_flag_0 = uni_df_0[f'change_{min}min_flag'].value_counts()

                        change_min_flag_1_1, change_min_flag_1_0 = change_min_flag_1.get(1, 0), change_min_flag_1.get(0, 0)
                        change_min_flag_0_1, change_min_flag_0_0 = change_min_flag_0.get(1, 0), change_min_flag_0.get(0, 0)

                        if change_min_flag_1_1 + change_min_flag_0_1 == 0:
                            continue

                        csv_file_date = csv_file.replace('formatted_ohlc_2025', '').replace('.csv', '')

                        if change_min_flag_1_1 == 0:
                            output_data = f'{csv_file_date},{column},u,{int(percents[i] * 100)},{min},{change_min_flag_1_1},{change_min_flag_1_0},0'
                        else:
                            output_data = f'{csv_file_date},{column},u,{int(percents[i] * 100)},{min},{change_min_flag_1_1},{change_min_flag_1_0},{round(change_min_flag_1_1 / (change_min_flag_1_1 + change_min_flag_1_0), 2)}'

                        if change_min_flag_0_1 == 0:
                            output_data2 = f'{csv_file_date},{column},d,{int(percents[i] * 100)},{min},{change_min_flag_0_1},{change_min_flag_0_0},0'
                        else:
                            output_data2 = f'{csv_file_date},{column},d,{int(percents[i] * 100)},{min},{change_min_flag_0_1},{change_min_flag_0_0},{round(change_min_flag_0_1 / (change_min_flag_0_1 + change_min_flag_0_0), 2)}'

                        # 現在のファイルと同階層のparam_rate.csvに末尾追加の形で出力
                        with open(output_csv_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(output_data.split(','))
                            writer.writerow(output_data2.split(','))

                    # カラム削除
                    del train_df[col_name]

                except Exception as e:
                    # エラーが発生した行を出力
                    log.error(f'Error in {csv_file}, column: {column}, error: {e}')
                    continue
