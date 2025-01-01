import numpy as np
import pandas as pd

class Indicator():
    def __init__(self, log):
        '''
        初期設定処理

        Args:
            log(Log): カスタムログクラスのインスタンス

        '''
        self.log = log

    def get_sma(self, df, column_name, window_size, interval):
        '''
        単純移動平均線(SMA)を取得する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): SMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)

        Returns:
            df(pandas.DataFrame): SMAを追加したDataFrame

        '''
        # インターバルに応じてデータをリサンプリング
        if interval > 1:
            df_resampled = df.iloc[::interval, :].copy()
        else:
            df_resampled = df.copy()

        # SMAの計算・カラムを追加
        df_resampled[column_name] = df_resampled['current_price'].rolling(window=window_size).mean().round(1)

        # 初めの方の要素はNaNになるので-1で埋める
        df_resampled[column_name].fillna(-1, inplace=True)

        # 元のデータフレームにリサンプリングされたデータをマージ
        df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

        # 2分足以上の場合は間の数値を前のSMAで埋める
        df[column_name].fillna(method='ffill', inplace=True)

        return df

    def get_ema(self, df, column_name, window_size, interval):
        '''
        指数移動平均線(EMA)を取得する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): EMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)

        Returns:
            df(pandas.DataFrame): EMAを追加したDataFrame

        '''
        # インターバルに応じてデータをリサンプリング
        if interval > 1:
            df_resampled = df.iloc[::interval, :].copy()
        else:
            df_resampled = df.copy()

        # EMAの計算・カラムを追加
        df_resampled[column_name] = df['current_price'].ewm(span = window_size).mean().round(1)

        # 初めの方の要素はNaNになるので-1で埋める
        df_resampled[column_name].fillna(-1, inplace=True)

        # 元のデータフレームにリサンプリングされたデータをマージ
        df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

        # 2分足以上の場合は間の数値を前のEMAで埋める
        df[column_name].fillna(method='ffill', inplace=True)

        return df

    def get_wma(self, df, column_name, window_size, interval):
        '''
        加重移動平均線(WMA)を取得する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): WMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)

        Returns:
            df(pandas.DataFrame): WMAを追加したDataFrame

        '''
        # インターバルに応じてデータをリサンプリング
        if interval > 1:
            df_resampled = df.iloc[::interval, :].copy()
        else:
            df_resampled = df.copy()

        # WMAの計算・カラムを追加
        weights = np.arange(1, window_size + 1)
        df_resampled[column_name] = df_resampled['current_price'].rolling(window = window_size).apply(lambda x: np.dot(x, weights) / weights.sum(), raw = True).round(1)

        # 初めの方の要素はNaNになるので-1で埋める
        df_resampled[column_name].fillna(-1, inplace=True)

        # 元のデータフレームにリサンプリングされたデータをマージ
        df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

        # 2分足以上の場合は間の数値を前のWMAで埋める
        df[column_name].fillna(method='ffill', inplace=True)

        return df
