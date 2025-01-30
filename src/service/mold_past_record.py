import os
import pandas as pd
import re
from service_base import ServiceBase
from tqdm import tqdm

class MoldPastRecord(ServiceBase):
    '''四本値データを持つCSVファイルを成形する'''
    def __init__(self):
        super().__init__()
        self.csv_dir_name = ''

    def set_csv_dir_name(self, csv_dir_name):
        '''CSVファイルが格納されているディレクトリ名を設定する'''
        self.csv_dir_name = csv_dir_name

    def get_target_csv_name_list(self):
        '''
        成形対象のCSVファイル名を取得する

        Returns:
            list: CSVファイル名のリスト ※ディレクトリが空の場合は空リストを返す
        '''
        # ディレクトリ内のCSVファイル名を取得
        csv_name_list = os.listdir(self.csv_dir_name)

        # 四本値データのCSV(ohlc_xxxxxx.csv)のみを抽出
        return re.findall(r'ohlc_\d{6}.csv', ' '.join(csv_name_list))

    def main(self, csv_name):
        '''
        成形のメイン処理

        Args:
            csv_name(str): 成形対象のCSVファイル名

        Returns:
            bool: 実行結果
        '''

        # CSVファイルの読み込み
        csv_path = os.path.join(self.csv_dir_name, csv_name)
        df = pd.read_csv(csv_path)

        # データのサンプル
        #stock_code,timestamp,open,high,low,close,volume
        #1332,2025-01-16 09:00,854.6,856.1,854.6,855.4,0
        #1332,2025-01-16 09:06,855.7,855.9,855.2,855.8,600
        #1332,2025-01-16 09:07,855.4,855.6,855.1,855.6,1500
        #1332,2025-01-16 09:08,855.7,855.7,854.1,854.1,3800
        #1332,2025-01-16 09:09,854.4,854.5,853.6,853.6,10400

        # 重要度の低いレコードを削除
        df = self.delete_record(df)

        # 時間に関する特徴量を追加
        ## 処理量を減らすため、この中から必要なカラムだけを引数として送り、あとで結合させる
        df_tmp = self.add_time_feature(df[['timestamp']])

        ## 重複するカラムを削除してから結合
        df.drop(columns = 'timestamp', inplace = True)
        df = pd.concat([df, df_tmp], axis = 1)

        # 目的変数(株価変化額/率/フラグ)のカラムを追加
        ## 処理量を減らすため、この中から必要なカラムだけを引数として送り、あとで結合させる
        target_columns = ['timestamp', 'close', 'stock_code', 'date']
        df_tmp = self.add_change_feature(df[target_columns])

        ## 重複するカラムを削除してから結合
        df.drop(columns = target_columns, inplace = True)
        df = pd.concat([df, df_tmp], axis = 1)

        # 主要なテクニカル指標を追加
        ## 必要なカラムだけを引数として送り、あとで結合させる
        target_columns = ['timestamp', 'open', 'high', 'low', 'close']
        df_tmp = self.add_technical_indicators(target_columns)

        ## 重複するカラムを削除してから結合
        df.drop(columns = target_columns, inplace = True)
        df = pd.concat([df, df_tmp], axis = 1)

         # timestampをstr型に戻して秒を削除
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')

        

        # CSVファイルの出力
        output_csv_path = os.path.join(self.csv_dir_name, f'formatted_{csv_name}')
        df.to_csv(output_csv_path, index = False)


    def delete_record(self, df):
        '''モデル作成に使えなさそうなレコードを削除する'''

        # データの前処理
        # 必要に応じてtimestampをdatetime型に変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 15:25以降(クロージング・オークション)のデータを削除
        df = df[df['timestamp'].dt.time < pd.to_datetime('15:25').time()]

        return df

    def add_time_feature(self, df):
        '''時間に関する特徴量を追加する'''
        # 参照に対して変更を加えないようコピーを作成
        df = df.copy()

        # 日付/時/分/曜日/9:00からの経過分数の特徴量を追加
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['get_minute'] = (df['hour'] - 9) * 60 + df['minute']

        return df

    def add_change_feature(self, df):
        '''目的変数(株価変化額/率/フラグ)のカラムを追加する'''
        # 参照に対して変更を加えないようコピーを作成
        df = df.copy()

        # 日付/証券コードのユニーク値を取得
        date_list = df['date'].unique()
        stock_code_list = df['stock_code'].unique()

        for date in tqdm(date_list):
            for stock_code in stock_code_list:
                # 日付/証券コードごとにデータを取得
                df_tmp = df[(df['date'] == date) & (df['stock_code'] == stock_code)].copy()

                # 1~90分後の株価変化額/率/フラグを追加
                for minute in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
                    # n分後のデータを追加
                    # n分後の株価変化フラグ(1:上昇, 0:同値・下落)
                    df_tmp[f'change_{minute}min_flag'] = (df_tmp['close'].shift(-minute) > df_tmp['close']).astype(int)
                    # n分後の株価変化額 単純引き算だと丸め誤差が出るため、小数点第2位で丸める
                    df_tmp[f'change_{minute}min_price'] = round(df_tmp['close'].shift(-minute) - df_tmp['close'], 2)
                    # n分後の株価変化率(%) 細かすぎると計算量が増えるため丸める 最小はTOPIX銘柄の1000円→999.9円(-0.01%)
                    df_tmp[f'change_{minute}min_rate'] = round(df_tmp[f'change_{minute}min_price'] / df_tmp['close'] * 100, 3)


                    # 計算したデータを元のdfに戻す
                    df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), f'change_{minute}min_flag'] = df_tmp[f'change_{minute}min_flag']
                    df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), f'change_{minute}min_price'] = df_tmp[f'change_{minute}min_price']
                    df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), f'change_{minute}min_rate'] = df_tmp[f'change_{minute}min_rate']

        # 日付変更フラグの追加(管理用)
        df['date_change_flag'] = (df['timestamp'].dt.day != df['timestamp'].shift(-1).dt.day).astype(int)
        # 処理の都合上、末尾は1になってしまうため0にする
        df.loc[df.index[-1], 'date_change_flag'] = 0

        return df

    def add_technical_indicators(self, df):
        '''主要なテクニカル指標を追加する'''
        ############### board_model.pyの内容を移植だけなのでそのままでは動かない

        # 参照に対して変更を加えないようコピーを作成
        df = df.copy()

        # 何分足で計算するか
        minute_list = [1, 3, 5, 10, 15, 30, 60, 90, 120, 240]

        # 直近何個のデータから算出するか
        window_size_list = [3, 5, 10, 15]
        window_size_list2 = [9, 14, 22, 26, 52]
        window_size_list3 = [10, 12, 15]
        af_list = [[0.01, 0.1], [0.02, 0.2], [0.05, 0.5], [0.1, 1]]

        for minute in minute_list:
            # minute分前からの増減率・増減幅・増減フラグを計算・追加する
            result, board_df = self.util.indicator.get_change_price(df = board_df,
                                                                    column_name = f'change_{minute}min',
                                                                    interval = minute)

            if result == False:
                return False, None

            # 説明変数に60分足以上の間隔ではデータ数が少なくなりすぎるのでスキップ
            if minute >= 60:
                continue

            for window_size in window_size_list:
                # 間隔と本数が多すぎると実際の数値が出るまで時間がかかるためスキップ
                if minute * window_size > 150:
                    continue

                # 単純移動平均線(SMA)を計算・追加する
                result, board_df = self.util.indicator.get_sma(df = board_df,
                                                               column_name = f'sma_{minute}min_{window_size}piece',
                                                               window_size = window_size,
                                                               interval = minute)
                if result == False:
                    return False, None

                # 指数移動平均線(EMA)を計算・追加する
                result, board_df = self.util.indicator.get_ema(df = board_df,
                                                               column_name = f'ema_{minute}min_{window_size}piece',
                                                               window_size = window_size,
                                                               interval = minute)
                if result == False:
                    return False, None

                # 加重移動平均線(WMA)を計算・追加する
                result, board_df = self.util.indicator.get_wma(df = board_df,
                                                               column_name = f'wma_{minute}min_{window_size}piece',
                                                               window_size = window_size,
                                                               interval = minute)
                if result == False:
                    return False, None

                # ボリンジャーバンドを計算・追加する
                result, board_df = self.util.indicator.get_bollinger_bands(df = board_df,
                                                                           column_name = f'bb_{minute}min_{window_size}piece',
                                                                           window_size = window_size,
                                                                           interval = minute)
                if result == False:
                    return False, None

            # 短期と長期の移動平均線の関連性を計算・追加する
            result, board_df = self.util.indicator.get_ma_cross(df = board_df, interval = minute)

            for window_size in window_size_list2:
                # 間隔と本数が多すぎると実際の数値が出るまで時間がかかるためスキップ
                if minute * window_size > 150:
                    continue

                # RSIを計算・追加する
                result, board_df = self.util.indicator.get_rsi(df = board_df,
                                                            column_name = f'rsi_{minute}min_{window_size}piece',
                                                            window_size = window_size,
                                                            interval = minute)
                if result == False:
                    return False, None

                # RCIを計算・追加する
                result, board_df = self.util.indicator.get_rci(df = board_df,
                                                               column_name = f'rci_{minute}min_{window_size}piece',
                                                               window_size = window_size,
                                                               interval = minute)
                if result == False:
                    return False, None

            for window_size in window_size_list3:
                # 間隔と本数が多すぎると実際の数値が出るまで時間がかかるためスキップ
                if minute * window_size > 150:
                    continue

                # サイコロジカルラインを計算・追加する
                result, board_df = self.util.indicator.get_psy(df = board_df,
                                                               column_name = f'psy_{minute}min_{window_size}piece',
                                                               window_size = window_size,
                                                               interval = minute)
                if result == False:
                    return False, None

            for min_af, max_af in af_list:
                # パラボリックSARを計算・追加する
                result, board_df = self.util.indicator.get_parabolic(df = board_df,
                                                                     column_name = f'sar_{minute}min_{min_af}_{max_af}af',
                                                                     min_af = min_af,
                                                                     max_af = max_af,
                                                                     interval = minute)
                if result == False:
                    return False, None

            # MACDを計算・追加する
            result, board_df = self.util.indicator.get_macd(df = board_df,
                                                            column_name = f'macd_{minute}min',
                                                            short_window_size = 12,
                                                            long_window_size = 26,
                                                            signal_window_size = 9,
                                                            interval = minute)
            if result == False:
                return False, None

            # 一目均衡表は計算に広いデータが必要になるため5分足までで制限
            if minute > 5:
                continue

            # 一目均衡表を計算・追加する
            result, board_df = self.util.indicator.get_ichimoku_cloud(df = board_df,
                                                                      column_name = f'ichimoku_{minute}min',
                                                                      short_window_size = 9,
                                                                      long_window_size = 26,
                                                                      interval = minute)
            if result == False:
                return False, None

        return True, board_df
