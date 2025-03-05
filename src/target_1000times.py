import os
import pandas as pd
import numpy as np
import re
from plyer import notification

# 目的変数を1000倍にする(1以上と未満で二乗を取った時の差がおかしくなるため)

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

for file in csv_files:
    df = pd.read_csv(os.path.join(data_dir, file))
    for minute in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
        # 変動率を1000倍にしてint型に変換
        df[f'change_{minute}min_rate'] = df[f'change_{minute}min_rate'].fillna(-99999).apply(lambda x: int(x * 1000)).replace(-99999000, np.nan)
    df.to_csv(os.path.join(data_dir, file.replace('formatted', 'formatted2')), index=False)

notification.notify(title='実行完了', message='スクリプトの実行が終了しました。', timeout=50)