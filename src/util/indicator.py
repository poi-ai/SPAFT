import numpy as np
import pandas as pd
import traceback

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
            bool: 実行結果
            df(pandas.DataFrame): SMAを追加したDataFrame

        '''
        try:
            # インターバルに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # SMAの計算・カラムを追加
            df_resampled[column_name] = df_resampled['current_price'].rolling(window=window_size).mean().round(1)

            # window_size - 1番目のデータでは計算ができずNaNになるので-1で埋める
            df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のSMAで埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'SMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

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
            bool: 実行結果
            df(pandas.DataFrame): EMAを追加したDataFrame

        '''
        try:
            # インターバルに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # EMAの計算・カラムを追加
            df_resampled[column_name] = df['current_price'].ewm(span = window_size).mean().round(1)

            # window_size - 1番目のデータでは計算ができずNaNになるので-1で埋める
            df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のEMAで埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'EMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

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
            bool: 実行結果
            df(pandas.DataFrame): WMAを追加したDataFrame

        '''
        try:
            # インターバルに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # WMAの計算・カラムを追加
            weights = np.arange(1, window_size + 1)
            df_resampled[column_name] = df_resampled['current_price'].rolling(window = window_size).apply(lambda x: np.dot(x, weights) / weights.sum(), raw = True).round(1)

            # window_size - 1番目のデータでは計算ができずNaNになるので-1で埋める
            df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のWMAで埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'WMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_bollinger_bands(self, df, column_name, window_size, interval):
        '''
        ボリンジャーバンドを取得する

        Args:
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): WMAを設定するカラム名
            window_size(int): ボリンジャーバンドを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): ボリンジャーバンドを追加したDataFrame

        '''
        try:
            # インターバルに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # 移動平均線と移動標準偏差を計算
            df_resampled['sma_tmp'] = df_resampled['current_price'].rolling(window = window_size).mean()
            df_resampled['sigma_tmp'] = df_resampled['current_price'].rolling(window = window_size).std()

            # +3α~-3αを計算してカラムに追加する
            for sigma in [1, 2, 3]:
                df_resampled[f'{column_name}_upper_{sigma}_alpha'] = (df_resampled['sma_tmp'] + (df_resampled['sigma_tmp'] * sigma)).round(1)
                df_resampled[f'{column_name}_lower_{sigma}_alpha'] = (df_resampled['sma_tmp'] - (df_resampled['sigma_tmp'] * sigma)).round(1)

                # 元のデータフレームにリサンプリングされたデータをマージ
                df = df.merge(df_resampled[[f'{column_name}_upper_{sigma}_alpha', f'{column_name}_lower_{sigma}_alpha']], left_index=True, right_index=True, how='left')

            for sigma in [1, 2, 3]:
                # リサンプリング対象外の行は、直近の値で埋める
                df[f'{column_name}_upper_{sigma}_alpha'].fillna(method='ffill', inplace=True)
                df[f'{column_name}_lower_{sigma}_alpha'].fillna(method='ffill', inplace=True)

                # window_size - 1番目のデータでは計算ができずNaNになるので-1で埋める
                df[f'{column_name}_upper_{sigma}_alpha'].fillna(-1, inplace=True)
                df[f'{column_name}_lower_{sigma}_alpha'].fillna(-1, inplace=True)

        except Exception as e:
            self.log.error(f'ボリンジャーバンド計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rsi(self, df, column_name,  window_size, interval):
        '''
        相対力指数(RSI)を取得する

        Args:
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): RSIを設定するカラム名
            window_size(int): RSIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): RSIを追加したDataFrame

        '''
        try:
            # インターバルに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # 前日との差分を計算
            df_resampled['diff'] = df_resampled['current_price'].diff()

            # 前日との差分がプラスならその値、マイナスなら0を設定
            df_resampled['up'] = df_resampled['diff'].apply(lambda x: x if x > 0 else 0)

            # 前日との差分がマイナスならその値、プラスなら0を設定
            df_resampled['down'] = df_resampled['diff'].apply(lambda x: abs(x) if x < 0 else 0)

            # 平均上昇幅と平均下降幅を計算
            df_resampled['up_mean'] = df_resampled['up'].rolling(window = window_size).mean()
            df_resampled['down_mean'] = df_resampled['down'].rolling(window = window_size).mean()

            # RSIを計算
            if df_resampled['down_mean'].isna().all() or df_resampled['up_mean'].isna().all():
                df_resampled[column_name] = -999
            elif df_resampled['down_mean'].sum() == 0:
                if df_resampled['up_mean'].sum() == 0:
                    df_resampled[column_name] = 50
                else:
                    df_resampled[column_name] = 100
            else:
                df_resampled[column_name] = (100 - 100 / (1 + df_resampled['up_mean'] / df_resampled['down_mean'])).round(2)

            # 先頭の要素を-999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[column_name], left_index=True, right_index=True, how='left')

            # window_size - 1番目のデータでは計算ができずNaNになるので-999で埋める かつ 間の要素は直近の要素で埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'RSI計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df
