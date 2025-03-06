import os
import pandas as pd
import numpy as np
import re
from plyer import notification

# CSVファイルから丸め誤差が発生しているカラムを修正する

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

for file in csv_files:
    df = pd.read_csv(os.path.join(data_dir, file))

    for column in df.columns:
        if df[column].dtype == 'float64':
            # Nanの値を99999に置換
            df[column] = df[column].fillna(99999)
            # カラムのすべての値を小数点以下4桁を四捨五入して小数点以下3桁にする
            df[column] = df[column].round(3)
            # 99999をNanに戻す
            df[column].replace(99999, np.nan)

    df.to_csv(os.path.join(data_dir, file.replace('formatted', 'formatted2')), index=False)
    

notification.notify(title='実行完了', message='スクリプトの実行が終了しました。', timeout=50)