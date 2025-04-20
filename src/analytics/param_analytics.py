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
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
output_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'param_rate.csv')
boerder_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'border_value.csv')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

# 出力先のCSVファイルが存在しない場合はファイル作成をしてヘッダーを追加
headers = ['date', 'column', 'updown', 'per', 'min', 'one_num', 'zero_num', 'one_rate']
if not os.path.exists(output_csv_path):
    with open(output_csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

headers = ['date', 'column', '1per', '5per', '10per', '25per', '50per', '75per', '90per', '95per', '99per']
if not os.path.exists(boerder_csv_path):
    with open(boerder_csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

for csv_file in tqdm(csv_files):
    # CSVファイルの読み込み
    df = pd.read_csv(os.path.join(data_dir, csv_file))

    # リークを起こすカラムは取り除く
    df = df.drop(columns = cm.leak_columns_ichimoku)

    # 出力時の日付を取得
    csv_file_date = csv_file.replace('formatted_ohlc_2025', '').replace('.csv', '')

    # n分ごとの変動フラグ
    for min in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
        # 変動がなかったレコードは削除
        mold_df = df[df[f'change_{min}min_rate'] != 0]

        # カラムがNanのレコードは削除
        mold_df = df[df[f'change_{min}min_rate'].notnull()]

        # 各カラムのデータ型の確認
        for column_name in df.columns:
            if column_name in cm.leak_columns:
                continue

            # 単一では明らかに変動に影響しないカラムの場合はスキップ
            if column_name in ['stock_code', 'hour', 'minute', 'get_minute', 'open', 'high', 'low', 'close', 'volume', 'day_of_week', 'date']:
                continue

            # intかfloat型のカラムのみを対象にする
            if mold_df[column_name].dtype == 'int64' or mold_df[column_name].dtype == 'float64':
                # 対象のカラムと変動フラグ、変動率をのみ切り出し
                uni_df = mold_df[[column_name, f'change_{min}min_rate', f'change_{min}min_flag']].copy()
                # 対象カラムがNaNのレコードを削除
                uni_df = uni_df[uni_df[column_name].notnull()]

                # 対象カラムのみ切り出し
                target_column_df = uni_df[column_name].copy()
                # 上位500レコードからユニークな値を取得
                col_unique = target_column_df[:500].unique()

                # ユニークな値の種類を取得が3種類以下なら0,1の二値とみなす
                nichi_flag = len(col_unique) <= 3

                # 二値の場合は1%と99%を閾値に設定
                if nichi_flag:
                    percents = [0.01, 0.99]
                # それ以外の場合は1%, 5%, 10%, 25%, 50%, 75%, 90%, 95%, 99%を閾値に設定
                else:
                    percents = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]

                # 各閾値の値を取得
                quantiles = target_column_df.quantile(percents).values

                # quantilesの値を小数点以下5桁に丸めてborder_value.csvに出力
                mold_quantiles = [round(q, 5) for q in quantiles]

                # 二値の場合は出力用に補正
                if nichi_flag:
                    mold_quantiles = [mold_quantiles[0], None, None, None, None, None, None, None, mold_quantiles[1]]

                # 閾値を出力
                with open(boerder_csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([csv_file_date, column_name] + mold_quantiles)

                continue

                for i, q in enumerate(quantiles):
                    try:
                        # ここでqには1%, 5%, 10%, 25%, 50%, 75%, 90%, 95%, 99%の値が入る
                        # qを閾値とした、q以上を1、q未満を0のカラムを追加
                        border_flag_name_up = f'{column_name}_{int((1 - percents[i]) * 100)}per_up'
                        border_flag_name_down = f'{column_name}_{int((1 - percents[i]) * 100)}per_down'
                        uni_df[border_flag_name_up] = (target_column_df >= round(q, 5)).astype(int)
                        uni_df[border_flag_name_down] = (target_column_df <= round(q, 5)).astype(int)

                        # qが1のレコードと0のレコードの切り出し
                        uni_df_1 = uni_df[uni_df[border_flag_name_up] == 1]
                        uni_df_0 = uni_df[uni_df[border_flag_name_down] == 1]
                        #change_min_flag = uni_df.loc[col >= q, f'change_{min}min_flag'].value_counts()

                        # uni_df_1と0のchange_min_flagの値をカウント
                        change_min_flag_1 = uni_df_1[f'change_{min}min_flag'].value_counts()
                        change_min_flag_0 = uni_df_0[f'change_{min}min_flag'].value_counts()

                        change_min_flag_1_1, change_min_flag_1_0 = change_min_flag_1.get(1, 0), change_min_flag_1.get(0, 0)
                        change_min_flag_0_1, change_min_flag_0_0 = change_min_flag_0.get(1, 0), change_min_flag_0.get(0, 0)

                        output_data = ''
                        output_data2 = ''

                        if (not nichi_flag or percents[i] != 0.99):
                            if change_min_flag_1_1 == 0:
                                output_data = f'{csv_file_date},{column_name},u,{int((1 - percents[i]) * 100)},{min},{change_min_flag_1_1},{change_min_flag_1_0},0'
                            else:
                                output_data = f'{csv_file_date},{column_name},u,{int((1 - percents[i]) * 100)},{min},{change_min_flag_1_1},{change_min_flag_1_0},{round(change_min_flag_1_1 / (change_min_flag_1_1 + change_min_flag_1_0), 2)}'

                        if (not nichi_flag or percents[i] != 0.01):
                            if change_min_flag_0_1 == 0:
                                output_data2 = f'{csv_file_date},{column_name},d,{int((1 - percents[i]) * 100)},{min},{change_min_flag_0_1},{change_min_flag_0_0},0'
                            else:
                                output_data2 = f'{csv_file_date},{column_name},d,{int((1 - percents[i]) * 100)},{min},{change_min_flag_0_1},{change_min_flag_0_0},{round(change_min_flag_0_1 / (change_min_flag_0_1 + change_min_flag_0_0), 2)}'

                        # 現在のファイルと同階層のparam_rate.csvに末尾追加の形で出力
                        with open(output_csv_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            if output_data != '':
                                writer.writerow(output_data.split(','))
                            if output_data2 != '':
                                writer.writerow(output_data2.split(','))

                        # カラム削除
                        del uni_df[border_flag_name_up]
                        del uni_df[border_flag_name_down]

                    except Exception as e:
                        # エラーが発生した行を出力
                        log.error(f'Error in {csv_file}, column: {column_name}, error: {e}')
                        continue