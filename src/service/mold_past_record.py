import os
import pandas as pd
import re
from service_base import ServiceBase
from tqdm import tqdm

# PerformanceWarningを無視
import warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

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
            target_list(list): CSVファイル名のリスト ※ディレクトリが空の場合は空リストを返す
        '''
        # ディレクトリ内のCSVファイル名を取得
        csv_name_list = os.listdir(self.csv_dir_name)

        # 四本値の元データのCSVファイル
        target_list = []

        # 途中まで保存したCSVファイル
        tmp_target_list = []

        for csv_name in csv_name_list:
            # 四本値データのCSV(ohlc_xxxxxx.csv)を抽出
            if re.fullmatch(r'ohlc_\d{6}.csv', csv_name):
                target_list.append(csv_name)

            # 途中まで保存したCSVファイル(tmp_ohlc_xxxxxx.csv)を抽出
            if re.fullmatch(r'tmp_ohlc_\d{6}.csv', csv_name):
                tmp_target_list.append(csv_name)

        # 途中まで保存したCSVがあるデータは対象から除く
        for target_csv in target_list:
            if f'tmp_{target_csv}' in tmp_target_list:
                target_list.remove(target_csv)

        return target_list, tmp_target_list

    def main(self, csv_name, file_type):
        '''
        成形のメイン処理

        Args:
            csv_name(str): 成形対象のCSVファイル名
            file_type(int): ファイルの種類(0: 四本値元データ, 1: 目的変数追加済データ)

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

        # 元データの場合
        if file_type == 0:

            # データの前処理
            # timestampをdatetime型に変換
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # 重要度の低い(クロージング・オークション)のレコードを削除
            df = self.delete_record(df)

            # 時間に関する特徴量を追加
            ## 処理量を減らすため、この中から必要なカラムだけを引数として送り、あとで結合させる
            df_tmp = self.add_time_feature(df[['timestamp']])

            ## 重複するカラムを削除してから結合
            df_tmp.drop(columns = 'timestamp', inplace = True)
            df = pd.concat([df, df_tmp], axis = 1)

            # 目的変数(株価変化額/率/フラグ)のカラムを追加
            ## 処理量を減らすため、この中から必要なカラムだけを引数として送り、あとで結合させる
            target_columns = ['timestamp', 'close', 'stock_code', 'date']
            df_tmp = self.add_change_feature(df[target_columns])

            ## 重複するカラムを削除してから結合
            df_tmp.drop(columns = target_columns, inplace = True)
            df = pd.concat([df, df_tmp], axis = 1)

            # timestampをstr型に戻して秒を削除
            df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')

            # 一時保存のCSVファイルの出力
            output_csv_path = os.path.join(self.csv_dir_name, f'tmp_{csv_name}')
            df.to_csv(output_csv_path, index = False)

        # 主要なテクニカル指標を追加
        ## 必要なカラムだけを引数として送り、あとで結合させる
        target_columns = ['date', 'stock_code', 'high', 'low', 'close']
        result, df_tmp = self.add_technical_indicators(df[target_columns])
        if result == False:
            return False

        ## 重複するカラムを削除してから結合
        df_tmp.drop(columns = target_columns, inplace = True)
        df = pd.concat([df, df_tmp], axis = 1)

        # CSVファイルの出力
        output_csv_path = os.path.join(self.csv_dir_name, f'formatted_{csv_name}')
        df.to_csv(output_csv_path, index = False)

    def delete_record(self, df):
        '''モデル作成の際に使わなさそうなレコードを削除する'''

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
        '''
        主要なテクニカル指標を追加する

        Args:
            df(padnas.DataFrame): 三本値+時刻を持つデータフレーム
                date, high, low, closeのカラムが必要

        Returns:
            bool: 実行結果
            add_df(pandas.DataFrame): テクニカル指標を追加したデータフレーム
                ※エラーが発生した場合はNoneを返す

        '''
        ############### board_model.pyの内容を移植だけなのでそのままでは動かない
        # 何分足で計算するか
        minute_list = [1, 3, 5, 10, 15, 30, 60, 90, 120, 240]

        # 直近何本のデータから計算するか
        window_size_list = [3, 5, 10, 15]
        window_size_list2 = [9, 14, 22, 26, 52]
        window_size_list3 = [10, 12, 15]
        af_list = [[0.01, 0.1], [0.02, 0.2], [0.05, 0.5], [0.1, 1]]

        # 参照に対して変更を加えないようコピーを作成
        df = df.copy()
        add_df = df.copy()

        # timestampとcloseのカラムを持ったdfを作成
        close_columns = ['date', 'stock_code', 'close']
        close_df = df[close_columns].copy()

        # timestampとhigh, low, closeのカラムを持ったdfを作成
        hlc_columns = ['date', 'stock_code', 'high', 'low', 'close']
        hlc_df = df[hlc_columns].copy()

        # 日付/証券コードのユニーク値を取得
        date_list = df['date'].unique()
        stock_code_list = df['stock_code'].unique()

        for date in tqdm(date_list):
            for stock_code in tqdm(stock_code_list):
                # 日付/証券コードごとにデータを取得
                unique_df = close_df[(close_df['date'] == date) & (close_df['stock_code'] == stock_code)].copy()
                hlc_unique_df = hlc_df[(hlc_df['date'] == date) & (hlc_df['stock_code'] == stock_code)].copy()

                if len(unique_df) == 0:
                    continue

                for minute in minute_list:
                    '''
                    for window_size in window_size_list:
                        # 間隔と本数が多すぎると説明変数として利用できるようになるまで時間がかかるためスキップ
                        if minute * window_size > 9: # TODO 元は150だったが、計算量を減らすため一時的に9に変更
                            continue

                        sma_column_name = f'sma_{minute}min_{window_size}piece'
                        ema_column_name = f'ema_{minute}min_{window_size}piece'
                        wma_column_name = f'wma_{minute}min_{window_size}piece'
                        bb_column_name = f'bb_{minute}min_{window_size}piece'

                        # 単純移動平均線(SMA)を計算・追加する
                        result, sma_df = self.util.indicator.get_sma(df = unique_df,
                                                                    column_name = sma_column_name,
                                                                    window_size = window_size,
                                                                    interval = minute,
                                                                    price_column_name = 'close')
                        if result == False:
                            return False, None

                        # 指数移動平均線(EMA)を計算・追加する
                        result, ema_df = self.util.indicator.get_ema(df = unique_df,
                                                                     column_name = ema_column_name,
                                                                     window_size = window_size,
                                                                     interval = minute,
                                                                     price_column_name = 'close')
                        if result == False:
                            return False, None

                        # 加重移動平均線(WMA)を計算・追加する
                        result, wma_df = self.util.indicator.get_wma(df = unique_df,
                                                                     column_name = wma_column_name,
                                                                     window_size = window_size,
                                                                     interval = minute,
                                                                     price_column_name = 'close')
                        if result == False:
                            return False, None

                        # ボリンジャーバンドを計算・追加する
                        result, bb_df = self.util.indicator.get_bollinger_bands(df = unique_df,
                                                                                column_name = bb_column_name,
                                                                                window_size = window_size,
                                                                                interval = minute,
                                                                                price_column_name = 'close')
                        if result == False:
                            return False, None

                        # 計算したデータをdfに追加する
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), sma_column_name] = sma_df[sma_column_name]
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), ema_column_name] = ema_df[ema_column_name]
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), wma_column_name] = wma_df[wma_column_name]
                        ## ボリンジャーバンドは複数のカラムがあるので一つずつ追加
                        for column_name in bb_df.columns:
                            if re.search(bb_column_name, column_name):
                                add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), column_name] = bb_df[column_name]

                    # 計算・カラム追加済みの各種移動平均線のカラム名を取得
                    ma_columns = []
                    for column in add_df.columns:
                        if re.compile(f'.ma_{minute}min_\\d+piece').match(column):
                            ma_columns.append(column)

                    # 日付と証券コードでフィルタリングし、必要なカラムだけをコピー
                    ma_unique_df = add_df.loc[(close_df['date'] == date) & (add_df['stock_code'] == stock_code), ma_columns].copy()

                    # 計算済みの移動平均線から短期と長期の関連性を計算・追加する
                    result, ma_cross_df = self.util.indicator.get_ma_cross(df = ma_unique_df, interval = minute)
                    if result == False:
                        return False, None

                    # 計算したデータをdfに追加する
                    for column_name in ma_cross_df.columns:
                        if column_name not in ma_columns:
                            add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), column_name] = ma_cross_df[column_name]

                    for window_size in window_size_list2:
                        # 間隔と本数が多すぎると実際の数値が出るまで時間がかかるためスキップ
                        if minute * window_size > 44: # TODO 元は150だったが、計算量を減らすため一時的に44に変更
                            continue

                        # カラム名定義
                        rsi_column_name = f'rsi_{minute}min_{window_size}piece'
                        rci_column_name = f'rci_{minute}min_{window_size}piece'

                        # RSIを計算・追加する
                        result, rsi_df = self.util.indicator.get_rsi(df = unique_df,
                                                                    column_name = rsi_column_name,
                                                                    window_size = window_size,
                                                                    interval = minute,
                                                                    price_column_name = 'close')
                        if result == False:
                            return False, None

                        # RCIを計算・追加する
                        result, rci_df = self.util.indicator.get_rci(df = unique_df,
                                                                    column_name = rci_column_name,
                                                                    window_size = window_size,
                                                                    interval = minute,
                                                                    price_column_name = 'close')

                        if result == False:
                            return False, None

                        # 計算したデータをdfに追加する
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), rsi_column_name] = rsi_df[rsi_column_name]
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), rci_column_name] = rci_df[rci_column_name]


                    for window_size in window_size_list3:
                        # 間隔と本数が多すぎると実際の数値が出るまで時間がかかるためスキップ
                        if minute * window_size > 59: # TODO 元は150だったが、計算量を減らすため一時的に59に変更
                            continue

                        # カラム名定義
                        psy_column_name = f'psy_{minute}min_{window_size}piece'

                        # サイコロジカルラインを計算・追加する
                        result, psy_df = self.util.indicator.get_psy(df = unique_df,
                                                                    column_name = psy_column_name,
                                                                    window_size = window_size,
                                                                    interval = minute,
                                                                    price_column_name = 'close')
                        if result == False:
                            return False, None

                        # 計算したデータをdfに追加する
                        add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), psy_column_name] = psy_df[psy_column_name]
                    '''

                    for min_af, max_af in af_list:
                        # カラム名定義
                        sar_column_name = f'sar_{minute}min_{min_af}_{max_af}af'

                        # パラボリックSARを計算・追加する
                        result, sar_df = self.util.indicator.get_parabolic_hlc(df = hlc_unique_df,
                                                                            column_name = sar_column_name,
                                                                            min_af = min_af,
                                                                            max_af = max_af,
                                                                            interval = minute)
                        if result == False:
                            return False, None

                        # 計算したデータをdfに追加する
                        for column_name in sar_df.columns:
                            if column_name not in add_df.columns:
                                add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), column_name] = sar_df[column_name]

                    '''
                    # MACDを計算・追加する
                    result, macd_df = self.util.indicator.get_macd(df = unique_df,
                                                                    column_name = f'macd_{minute}min',
                                                                    short_window_size = 12,
                                                                    long_window_size = 26,
                                                                    signal_window_size = 9,
                                                                    interval = minute,
                                                                    price_column_name = 'close')
                    if result == False:
                        return False, None

                    # 計算したデータをdfに追加する
                    for column_name in macd_df.columns:
                        if column_name not in add_df.columns:
                            add_df.loc[(df['date'] == date) & (df['stock_code'] == stock_code), column_name] = macd_df[column_name]

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
                    '''

        return True, add_df
