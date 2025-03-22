import os
import pandas as pd
import numpy as np
import re
import sys
from plyer import notification

# CSVファイルから丸め誤差が発生しているカラムを修正する

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

for file in csv_files:
    df = pd.read_csv(os.path.join(data_dir, file))

    if sys.argv[1] == 'check':
        for column in df.columns:
            if df[column].dtype == 'float64':
                # Nanの値を99999に置換
                df[column] = df[column].fillna(99999)
                # 小数点以下5桁以下まで値が存在した場合は丸め誤差が発生していると判断
                if not df[column].apply(lambda x: x == np.round(x, 5)).all():
                    # 丸め誤差が発生している場合はファイル名とカラム名と値を出力
                    marume_values = df[column][df[column].apply(lambda x: x != np.round(x, 5))]
                    print(f'{file} の {column} に丸め誤差が発生しています。')
    elif sys.argv[1] == 'correct':
        for column in df.columns:
            if df[column].dtype == 'float64':
                # Nanの値を99999に置換
                df[column] = df[column].fillna(99999)
                # カラムのすべての値を小数点以下4桁を四捨五入して小数点以下3桁にする
                df[column] = df[column].round(3)
                # 99999をNanに戻す
                df[column].replace(99999, np.nan)

        df.to_csv(os.path.join(data_dir, file.replace('formatted', 'formatted2')), index=False)
    else:
        print('引数が不正です。')


notification.notify(title='実行完了', message='スクリプトの実行が終了しました。', timeout=50)