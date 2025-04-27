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
trade_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'trade')
border_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'border_settle.csv')
performance_path = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', 'performance.csv')
ohlc_csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

# 出力先のCSVファイルが存在しない場合はファイル作成をしてヘッダーを追加
headers = ['date', 'column', 'updown', 'per', 'min', 'benefit', 'benefit_rate']
if not os.path.exists(performance_path):
    with open(performance_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

# 閾値データの呼び出し
border_df = pd.read_csv(os.path.join(data_dir, border_path))
# 閾値の存在しているカラム
border_unique = border_df['column'].unique()

# 四本値+テクニカル指標のCSVを読み込む
for csv_file in tqdm(ohlc_csv_files):
    # CSVファイルの読み込み
    df = pd.read_csv(os.path.join(data_dir, csv_file))

    # 遅行スパンを含む(リークを起こす)カラムは取り除く
    df = df.drop(columns=cm.leak_columns_ichimoku)

    # 必要のないカラムも取り除く
    df = df.drop(columns=['date', 'hour', 'minute', 'day_of_week', 'get_minute'])

    # 日付をファイル名から取得
    csv_file_date = csv_file.replace('formatted_ohlc_', '').replace('.csv', '')

    # カラムを順番に取り出す
    for column_name in border_unique:
        # 閾値データに該当のレコードが存在するかチェック
        if column_name not in border_unique:
            continue

        # 単一では明らかに変動に影響しないカラムの場合はスキップ
        if column_name in ['stock_code', 'hour', 'minute', 'get_minute', 'open', 'high', 'low', 'close', 'volume', 'day_of_week', 'date']:
            continue

        # 目的変数の場合もスキップ
        if column_name in cm.leak_columns:
            continue

        # パフォーマンス計算に必要なカラムのみ抜き出す
        mold_df = df[['stock_code', 'timestamp', column_name, 'close'] + cm.leak_columns_price + cm.leak_columns_rate].copy()

        # intかfloat型のカラムのみを対象にする
        if mold_df[column_name].dtype == 'int64' or mold_df[column_name].dtype == 'float64':
            # 分ごとにパフォーマンスの計算を行う
            for min in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
                # columnとminが合致する閾値データが存在するかチェック
                if border_df[(border_df['column'] == column_name) & (border_df['min'] == min)].empty:
                    continue

                # 必要なカラムのみ抽出
                min_df = mold_df[['stock_code', 'timestamp', column_name, 'close', f'change_{min}min_price', f'change_{min}min_rate']].copy()

                # 何%の閾値で計算するか
                for border_per in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
                    # 閾値データの取得
                    border_value = border_df[(border_df['column'] == column_name) & (border_df['min'] == min)]

                    # 閾値がNanならスキップ
                    if pd.isna(border_value[f'{border_per}per'].values[0]):
                        continue

                    # 取引記録CSVがないならヘッダーを付けて新規作成
                    headers = ['stock_code', 'timestamp', 'price', 'rate', 'feature_value']
                    if not os.path.exists(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_u.csv')):
                        with open(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_u.csv'), 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(headers)

                    if not os.path.exists(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_d.csv')):
                        with open(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_d.csv'), 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(headers)

                    # 管理用
                    up_skip_index = 0
                    down_skip_index = 0
                    before_stock_code = 0
                    up_benefit = 0
                    up_benefit_rate = 0
                    down_benefit = 0
                    down_benefit_rate = 0

                    # 1行ずつ処理
                    for index, row in min_df.iterrows():
                        # 別銘柄チェック
                        if before_stock_code != row['stock_code']:
                            up_skip_index = 0
                            down_skip_index = 0
                            before_stock_code = row['stock_code']

                        # レコードスキップのチェック
                        if up_skip_index > 0 and down_skip_index > 0:
                            up_skip_index -= 1
                            down_skip_index -= 1
                            continue

                        # カラムに値がない場合はスキップ
                        if pd.isna(row[column_name]) or pd.isna(row[f'change_{min}min_price']):
                            continue

                        # 閾値よりも上の場合のチェック
                        if up_skip_index > 0:
                            up_skip_index -= 1
                        elif row[column_name] >= border_value[f'{border_per}per'].values[0]:
                            up_benefit = round(up_benefit + row[f'change_{min}min_price'], 1)
                            up_benefit_rate = round(up_benefit_rate + 1 - (row['close'] + row[f'change_{min}min_price']) / row['close'], 5)
                            up_skip_index = min - 1

                            # 取引結果をCSVに出力
                            with open(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_u.csv'), 'a', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([row['stock_code'], row['timestamp'], row[f'change_{min}min_price'], row[f'change_{min}min_rate'], row[column_name]])

                        # 閾値よりも下の場合のチェック
                        if down_skip_index > 0:
                            down_skip_index -= 1
                        elif row[column_name] <= border_value[f'{border_per}per'].values[0]:
                            down_benefit = round(down_benefit + row[f'change_{min}min_price'], 1)
                            down_benefit_rate = round(down_benefit_rate + 1 - (row['close'] + row[f'change_{min}min_price']) / row['close'], 5)
                            down_skip_index = min - 1

                            # 取引結果をCSVに出力
                            with open(os.path.join(trade_dir, f'trade_{csv_file_date}_{column_name}_{min}_{border_per}_d.csv'), 'a', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([row['stock_code'], row['timestamp'], row[f'change_{min}min_price'], row[f'change_{min}min_rate'], row[column_name]])

                    # パフォーマンスの計算結果をCSVに出力
                    with open(performance_path, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([csv_file_date, column_name, 'u', border_per, min, up_benefit, up_benefit_rate])
                        writer.writerow([csv_file_date, column_name, 'd', border_per, min, down_benefit, down_benefit_rate])
