import numpy as np
import pandas as pd
import traceback
import re

class Indicator():
    def __init__(self, log):
        self.log = log

    def get_sma(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        単純移動平均線(SMA)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定するカラム名が存在し、連続した時系列のデータであること
            column_name(str): SMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): SMAを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # SMAの計算・カラムを追加
            df_resampled[column_name] = df_resampled[price_column_name].rolling(window=window_size).mean().round(1)

            # window_size - 1番目までのデータでは計算ができずNaNになるので-1で埋める
            df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のSMAで埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'SMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ema(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        指数移動平均線(EMA)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定するカラム名が存在し、連続した時系列のデータであること
            column_name(str): EMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): EMAを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # EMAの計算・カラムを追加
            df_resampled[column_name] = df_resampled[price_column_name].ewm(span = window_size).mean().round(1)

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

    def get_wma(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        加重移動平均線(WMA)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定するカラム名が存在し、連続した時系列のデータであること
            column_name(str): WMAを設定するカラム名
            window_size(int): 移動平均線を計算する際のウィンドウ幅
            interval(int): SMAを計算する間隔(何分足として計算するか)
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): WMAを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # WMAの計算・カラムを追加
            weights = np.arange(1, window_size + 1)
            df_resampled[column_name] = df_resampled[price_column_name].rolling(window = window_size).apply(lambda x: np.dot(x, weights) / weights.sum(), raw = True).round(1)

            # window_size - 1番目までのデータでは計算ができずNaNになるので-1で埋める
            df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のWMAで埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'WMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ma_cross(self, df, interval):
        '''
        別期間軸の移動平均線のクロスや関連性を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
            interval(int): SMAを計算する間隔(何分足として計算するか)

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): SMAクロスを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # 既に計算済の移動平均線の値を持つカラムを取得
            sma_columns = [col for col in df_resampled.columns if re.compile(f'sma_{interval}min_\\d+piece').match(col)]
            ema_columns = [col for col in df_resampled.columns if re.compile(f'ema_{interval}min_\\d+piece').match(col)]
            wma_columns = [col for col in df_resampled.columns if re.compile(f'wma_{interval}min_\\d+piece').match(col)]

            if len(sma_columns) == 0 or len(ema_columns) == 0 or len(wma_columns) == 0:
                ##self.log.warning('移動平均線の値が存在しません')
                return True, pd.DataFrame()

            add_columns = []
            for columns in [sma_columns, ema_columns, wma_columns]:
                # 移動平均線の種別
                line_type = columns[0].split('_')[0]
                for column_short in columns:
                    for column_long in columns:
                        # 短期と長期の本数を取得
                        short_piece = int(re.search(rf'{interval}min_(\d+)piece', column_short).group(1))
                        long_piece = int(re.search(rf'{interval}min_(\d+)piece', column_long).group(1))

                        # column_shortが短期、column_longが長期でない場合はスキップ
                        if short_piece >= long_piece:
                            continue

                        # 変数定義
                        golden_cross = f'{line_type}_{interval}min_{short_piece}to{long_piece}piece_golden_cross'
                        golden_cross_after = f'{line_type}_{interval}min_{short_piece}to{long_piece}piece_golden_cross_after'
                        dead_cross = f'{line_type}_{interval}min_{short_piece}to{long_piece}piece_dead_cross'
                        dead_cross_after = f'{line_type}_{interval}min_{short_piece}to{long_piece}piece_dead_cross_after'
                        diff = f'{line_type}_{interval}min_{short_piece}to{long_piece}piece_diff'

                        # ゴールデンクロス・デッドクロスの判定
                        df_resampled[golden_cross] = ((df_resampled[column_short].shift(1) <= df_resampled[column_long].shift(1)) & (df_resampled[column_short] > df_resampled[column_long])).astype(int)
                        df_resampled[dead_cross] = ((df_resampled[column_short].shift(1) >= df_resampled[column_long].shift(1)) & (df_resampled[column_short] < df_resampled[column_long])).astype(int)

                        # 直近でフラグが立ってからの経過時間
                        df_resampled['gc_id'] = df_resampled[golden_cross].cumsum()
                        df_resampled[golden_cross_after] = df_resampled.groupby('gc_id').cumcount()
                        df_resampled['dc_id'] = df_resampled[dead_cross].cumsum()
                        df_resampled[dead_cross_after] = df_resampled.groupby('dc_id').cumcount()

                        # 短期と長期の差を計算
                        df_resampled[diff] = (df_resampled[column_short] - df_resampled[column_long]).round(2)
                        add_columns.extend([golden_cross, golden_cross_after, dead_cross, dead_cross_after, diff])

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

        except Exception as e:
            self.log.error(f'MAクロス計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_bollinger_bands(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        ボリンジャーバンドを計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定するカラム名が存在し、連続した時系列のデータであること
            column_name(str): WMAを設定するカラム名
            window_size(int): ボリンジャーバンドを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): ボリンジャーバンドを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # 移動平均線と移動標準偏差を計算
            df_resampled['sma_tmp'] = df_resampled[price_column_name].rolling(window = window_size).mean()
            df_resampled['sigma_tmp'] = df_resampled[price_column_name].rolling(window = window_size).std()

            # 追加対象のカラム名
            add_columns = []

            # +3α~-3αを計算してカラムに追加する
            for sigma in [1, 2, 3]:
                df_resampled[f'{column_name}_upper_{sigma}_alpha'] = (df_resampled['sma_tmp'] + (df_resampled['sigma_tmp'] * sigma)).round(1)
                df_resampled[f'{column_name}_lower_{sigma}_alpha'] = (df_resampled['sma_tmp'] - (df_resampled['sigma_tmp'] * sigma)).round(1)

                add_columns.extend([f'{column_name}_upper_{sigma}_alpha', f'{column_name}_lower_{sigma}_alpha'])

            # バンド(α)の幅を計算
            df_resampled[f'{column_name}_width'] = (df_resampled['sigma_tmp'] * 2).round(3)
            add_columns.append(f'{column_name}_width')

            # バンド幅の収縮・拡大度合いを計算
            df_resampled[f'{column_name}_width_diff'] = df_resampled[f'{column_name}_width'].diff().round(3)
            add_columns.append(f'{column_name}_width_diff')

            # 価格とバンドの差を計算
            df_resampled[f'{column_name}_upper_diff'] = (df_resampled[price_column_name] - df_resampled[f'{column_name}_upper_1_alpha']).round(3)
            df_resampled[f'{column_name}_lower_diff'] = (df_resampled[f'{column_name}_lower_1_alpha'] - df_resampled[price_column_name]).round(3)
            add_columns.extend([f'{column_name}_upper_diff', f'{column_name}_lower_diff'])

            # バンド内での位置を計算 αの場合は1、-αの場合は0になる
            df_resampled[f'{column_name}_position'] = ((df_resampled[price_column_name] - df_resampled[f'{column_name}_lower_1_alpha']) / df_resampled[f'{column_name}_width']).round(3)
            add_columns.append(f'{column_name}_position')

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            for column in add_columns:
                # リサンプリング対象外の行は、直近の値で埋める
                df[column].fillna(method='ffill', inplace=True)

                # window_size - 1番目までのデータでは計算ができずNaNになるので-999で埋める
                df[column].fillna(-999, inplace=True)

        except Exception as e:
            self.log.error(f'ボリンジャーバンド計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rsi(self, df, column_name,  window_size, interval):
        '''
        相対力指数(RSI)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): RSIを設定するカラム名
            window_size(int): RSIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): RSIを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

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

            # window_size - 1番目までのデータでは計算ができずNaNになるので-999で埋める かつ 間の要素は直近の要素で埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'RSI計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rci(self, df, column_name, window_size, interval):
        '''
        順位相関指数(RCI)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): RCIを設定するカラム名
            window_size(int): RCIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): RCIを追加したDataFrame
        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # RCIの計算・カラムを追加
            df_resampled[column_name] = df_resampled['current_price'].rolling(window=window_size).apply(self.calc_rci, raw=False)

            # 初めの方の要素はNaNになるので直前の値で埋める
            df_resampled[column_name].fillna(method='ffill', inplace=True)

            # 先頭の要素を-999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を前の値で埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'RCI計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def calc_rci(self, sub_df):
        '''
        RCIの計算を行う

        Args:
            sub_df(pandas.Series): 価格のリスト

        Returns:
            rci(float): RCIの値(%)
        '''
        n = len(sub_df)
        d = ((np.arange(1, n + 1) - np.array(pd.Series(sub_df).rank())) ** 2).sum()
        rci = ((1 - 6 * d / (n *(n ** 2 - 1))) * 100).round(2)
        return rci

    def get_macd(self, df, column_name, short_window_size, long_window_size, signal_window_size, interval):
        '''
        MACDを計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): MACDを設定するカラム名
            short_window_size(int): 短期EMAのウィンドウ幅
            long_window_size(int): 長期EMAのウィンドウ幅
            signal_window_size(int): シグナル線のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): MACDを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # カラム名の設定
            macd = column_name
            macd_signal = f'{macd}_signal'
            macd_histogram = f'{macd}_diff'
            add_columns = []

            # MACD(短期EMA - 長期EMA)の計算
            short_ema = df_resampled['current_price'].ewm(span = short_window_size).mean()
            long_ema = df_resampled['current_price'].ewm(span = long_window_size).mean()
            df_resampled[macd] = (short_ema - long_ema).round(2)
            add_columns.append(macd)

            # MACDシグナルの計算
            df_resampled[macd_signal] = df_resampled[macd].ewm(span = signal_window_size).mean().round(2)
            add_columns.append(macd_signal)

            # MACDとMACDシグナルの差(ヒストグラム)を計算
            df_resampled[macd_histogram] = df_resampled[macd] - df_resampled[macd_signal]
            df_resampled[f'{macd_histogram}_flag'] = df_resampled[macd_histogram].apply(lambda x: 1 if x > 0 else 0)
            add_columns.extend([macd_histogram, f'{macd_histogram}_flag'])

            # ゴールデンクロス・デッドクロスのフラグ
            df_resampled[f'{macd}_cross'] = 0
            df_resampled.loc[(df_resampled[macd] > df_resampled[macd_signal]) & (df_resampled[macd].shift() < df_resampled[macd_signal].shift()), f'{macd}_cross'] = 1
            df_resampled.loc[(df_resampled[macd] < df_resampled[macd_signal]) & (df_resampled[macd].shift() > df_resampled[macd_signal].shift()), f'{macd}_cross'] = -1
            add_columns.append(f'{macd}_cross')

            # TODO クロス後の転換シグナルなしフラグ

            # MACDとMACDシグナルの傾きを計算
            for count in [1, 3, 5, 10]:
                df_resampled[f'{macd}_{count}_slope'] = df_resampled[macd].diff(count)
                df_resampled[f'{macd_signal}_{count}_slope'] = df_resampled[macd_signal].diff(count)
                add_columns.extend([f'{macd}_{count}_slope', f'{macd_signal}_{count}_slope'])

            # MACDの傾きと価格の傾きの不一致(ダイバージェンス)フラグ
            df_resampled[f'{macd}_mismatch'] = (df_resampled[macd].diff() * df_resampled['current_price'].diff()).apply(lambda x: 1 if x < 0 else 0)
            add_columns.append(f'{macd}_mismatch')

            # MACDの傾きと価格の傾きの不一致(ダイバージェンス)フラグが続いている回数
            df_resampled[f'{macd}_mismatch_count'] = df_resampled[f'{macd}_mismatch'].rolling(window=50, min_periods=1).sum()
            add_columns.append(f'{macd}_mismatch_count')

            # 先頭の要素を-999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_indexer(add_columns)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'MACD計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_psy(self, df, column_name, window_size, interval):
        '''
        サイコロジカルライン(PSY)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): PSYを設定するカラム名
            window_size(int): PSYを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): PSYを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # 前日との差分を計算
            df_resampled['diff'] = df_resampled['current_price'].diff()

            # 前日との差分がプラスなら1、マイナスなら0を設定
            df_resampled['up'] = df_resampled['diff'].apply(lambda x: 1 if x > 0 else 0)

            # PSYを計算
            df_resampled[column_name] = (df_resampled['up'].rolling(window = window_size).sum() / window_size * 100).round(1)

            # 先頭の要素を-999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[column_name], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'PSY計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_parabolic(self, df, column_name, min_af, max_af, interval):
        '''
        パラボリック(SAR)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): SARを設定するカラム名
            min_af(float): 加速因数の初期値(最小値)
            max_af(float): 加速因数の最大値
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): SARを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # 初期値の設定 SARの初期値と前日のEPは初期値の終値になる
            sar_list = [df_resampled['current_price'].iloc[0]]
            ep = df_resampled['current_price'].iloc[0]
            af = min_af
            trend = ''

            # SARの計算
            for i in range(1, len(df_resampled)):
                current_price = df_resampled['current_price'].iloc[i]

                # 1つ目の要素の場合は前日との差分で上昇か下降トレンドかを判定
                if i == 1:
                    if sar_list[-1] < current_price:
                        trend = 'up'
                    else:
                        trend = 'down'

                # 上昇トレンドの場合
                if trend == 'up':
                    # トレンド内での高値を更新した場合
                    if ep < current_price:
                        ep = current_price
                        af = min(af + min_af, max_af)

                    # SARの計算
                    sar = sar_list[i - 1] + af * (ep - sar_list[i - 1])

                    # SARが現在の価格よりも高い場合はトレンドを反転
                    if sar > current_price:
                        trend = 'down'
                        sar = ep
                        ep = current_price
                        af = min_af

                # 下降トレンドの場合
                else:
                    # トレンド内での安値を更新した場合
                    if ep > current_price:
                        ep = current_price
                        af = min(af + min_af, max_af)

                    # SARの計算
                    sar = sar_list[i - 1] - af * (sar_list[i - 1] - ep)

                    # SARが現在の価格よりも低い場合はトレンドを反転
                    if sar < current_price:
                        trend = 'up'
                        sar = ep
                        ep = current_price
                        af = min_af

                sar_list.append(sar.round(4))

            df_resampled[column_name] = sar_list
            column_name_flag = f'{column_name}_flag'
            df_resampled[column_name_flag] = (df_resampled[column_name] >= 0).astype(int)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[column_name, column_name_flag], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name].fillna(method='ffill', inplace=True)
            df[column_name_flag].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'SAR計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ichimoku_cloud(self, df, column_name, short_window_size, long_window_size, interval):
        '''
        一目均衡表を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムかhigh&lowカラムが存在かつデータが時系列で連続していること
            column_name(str): 一目均衡表を設定するカラム名
            short_window_size(int): 短期のウィンドウ幅
            long_window_size(int): 長期のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): 一目均衡表を追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df.iloc[::interval, :].copy()
            else:
                df_resampled = df.copy()

            # カラム名の設定
            base_line = f'{column_name}_base_line'
            conversion_line = f'{column_name}_conversion_line'
            leading_span_a = f'{column_name}_leading_span_a'
            leading_span_b = f'{column_name}_leading_span_b'
            lagging_span = f'{column_name}_lagging_span'
            base_conversion_diff = f'{column_name}_bc_diff'
            base_conversion_position = f'{column_name}_bc_position'
            base_conversion_cross = f'{column_name}_bc_cross'
            base_conversion_gc_after = f'{column_name}_bc_gc_after'
            base_conversion_dc_after = f'{column_name}_bc_dc_after'
            price_lagging_diff = f'{column_name}_pl_diff'
            price_lagging_position = f'{column_name}_pl_position'
            price_lagging_cross = f'{column_name}_pl_cross'
            price_lagging_gc_after = f'{column_name}_pl_gc_after'
            price_lagging_dc_after = f'{column_name}_pl_dc_after'
            leading_span_diff = f'{column_name}_ls_diff'
            leading_span_position = f'{column_name}_ls_position'
            leading_span_cross = f'{column_name}_ls_cross'
            leading_span_gc_after = f'{column_name}_ls_gc_after'
            leading_span_dc_after = f'{column_name}_ls_dc_after'
            price_cloud_high_diff = f'{column_name}_cloud_high_diff'
            price_cloud_low_diff = f'{column_name}_cloud_low_diff'
            price_cloud_position = f'{column_name}_cloud_position'
            price_cloud_cross = f'{column_name}_cloud_cross'
            price_cloud_cross_gc_after1 = f'{column_name}_cloud_gc_after1'
            price_cloud_cross_gc_after2 = f'{column_name}_cloud_gc_after2'
            price_cloud_cross_dc_after1 = f'{column_name}_cloud_dc_after1'
            price_cloud_cross_dc_after2 = f'{column_name}_cloud_dc_after2'

            add_columns = [base_line, conversion_line, leading_span_a, leading_span_b, lagging_span,
                           base_conversion_diff, base_conversion_position, base_conversion_cross, base_conversion_gc_after, base_conversion_dc_after,
                           price_lagging_diff, price_lagging_position, price_lagging_cross, price_lagging_gc_after, price_lagging_dc_after,
                           leading_span_diff, leading_span_position, leading_span_cross, leading_span_gc_after, leading_span_dc_after,
                           price_cloud_high_diff, price_cloud_low_diff, price_cloud_position, price_cloud_cross,
                           price_cloud_cross_gc_after1, price_cloud_cross_gc_after2, price_cloud_cross_dc_after1, price_cloud_cross_dc_after2]

            # 高値/安値がない場合
            if 'high' not in df_resampled.columns:
                df_resampled['high'] = df_resampled['current_price']
                df_resampled['low'] = df_resampled['current_price']

            # 基準線の計算 long_window_size本の高値と安値の平均
            df_resampled[base_line] = (df_resampled['high'].rolling(window = long_window_size).max() + df_resampled['low'].rolling(window = long_window_size).min()) / 2

            # 転換線の計算 short_window_size本の高値と安値の平均
            df_resampled[conversion_line] = (df_resampled['high'].rolling(window = short_window_size).max() + df_resampled['low'].rolling(window = short_window_size).min()) / 2

            # 先行スパン1の計算 long_window_size本先の基準線と転換線の平均
            df_resampled[leading_span_a] = ((df_resampled[conversion_line] + df_resampled[base_line]) / 2).shift(long_window_size)

            # 先行スパン2の計算 long_window_size x 2本の高値と安値の平均をlong_window_size本先にずらす
            df_resampled[leading_span_b] = ((df_resampled['high'].rolling(window = long_window_size * 2).max() + df_resampled['low'].rolling(window = long_window_size * 2).min()) / 2).shift(long_window_size)

            # 遅行スパンの計算 現在の価格をlong_window_size本前にずらす
            df_resampled[lagging_span] = df_resampled['current_price'].shift(-long_window_size)

            # 基準線と転換線の差/位置関係
            df_resampled[base_conversion_diff] = df_resampled[conversion_line] - df_resampled[base_line]
            df_resampled[base_conversion_position] = (df_resampled[conversion_line] - df_resampled[base_line]).apply(lambda x: 1 if x > 0 else 0)

            # 基準線と転換線のクロスフラグ
            df_resampled[base_conversion_cross] = 0
            df_resampled.loc[(df_resampled[conversion_line] > df_resampled[base_line]) & (df_resampled[conversion_line].shift() < df_resampled[base_line].shift()), base_conversion_cross] = 1
            df_resampled.loc[(df_resampled[conversion_line] < df_resampled[base_line]) & (df_resampled[conversion_line].shift() > df_resampled[base_line].shift()), base_conversion_cross] = -1

            # ゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[base_conversion_gc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == 1, base_conversion_gc_after] = 0
            df_resampled[base_conversion_dc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == -1, base_conversion_dc_after] = 0

            # 終値と遅行スパンの差/位置関係
            df_resampled[price_lagging_diff] = df_resampled['current_price'] - df_resampled[lagging_span]
            df_resampled[price_lagging_position] = (df_resampled['current_price'] > df_resampled[lagging_span]).astype(int)

            # 終値と遅行スパンのクロスフラグ
            df_resampled[price_lagging_cross] = 0
            df_resampled.loc[(df_resampled['current_price'] > df_resampled[lagging_span]) & (df_resampled['current_price'].shift() < df_resampled[lagging_span].shift()), price_lagging_cross] = 1
            df_resampled.loc[(df_resampled['current_price'] < df_resampled[lagging_span]) & (df_resampled['current_price'].shift() > df_resampled[lagging_span].shift()), price_lagging_cross] = -1

            # ゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[price_lagging_gc_after] = df_resampled.groupby((df_resampled[price_lagging_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_lagging_cross] == 1, price_lagging_gc_after] = 0
            df_resampled[price_lagging_dc_after] = df_resampled.groupby((df_resampled[price_lagging_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_lagging_cross] == -1, price_lagging_dc_after] = 0

            # 先行スパン1と2の差/位置関係
            df_resampled[leading_span_diff] = df_resampled[leading_span_a] - df_resampled[leading_span_b]
            df_resampled[leading_span_position] = (df_resampled[leading_span_a] > df_resampled[leading_span_b]).astype(int)

            # 先行スパン1と2のクロスフラグ
            df_resampled[leading_span_cross] = 0
            df_resampled.loc[(df_resampled[leading_span_a] > df_resampled[leading_span_b]) & (df_resampled[leading_span_a].shift() < df_resampled[leading_span_b].shift()), leading_span_cross] = 1
            df_resampled.loc[(df_resampled[leading_span_a] < df_resampled[leading_span_b]) & (df_resampled[leading_span_a].shift() > df_resampled[leading_span_b].shift()), leading_span_cross] = -1

            # ゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[leading_span_gc_after] = df_resampled.groupby((df_resampled[leading_span_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[leading_span_cross] == 1, leading_span_gc_after] = 0
            df_resampled[leading_span_dc_after] = df_resampled.groupby((df_resampled[leading_span_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[leading_span_cross] == -1, leading_span_dc_after] = 0

            # 終値と雲(先行スパン1と2の間)の差/位置関係
            df_resampled[price_cloud_high_diff] = df_resampled['current_price'] - np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])
            df_resampled[price_cloud_low_diff] = df_resampled['current_price'] - np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])
            # 雲の上下位置フラグ(1: 上、 0: 中、-1: 下)
            df_resampled[price_cloud_position] = 0
            df_resampled.loc[(df_resampled['current_price'] > np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])), price_cloud_position] = 1
            df_resampled.loc[(df_resampled['current_price'] < np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])), price_cloud_position] = -1

            # 終値と雲(先行スパン1と2の間)からのクロスフラグ
            df_resampled[price_cloud_cross] = 0
            # 雲の上->中
            df_resampled.loc[(df_resampled['current_price'] > np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled['current_price'].shift() < np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b]).shift()), price_cloud_cross] = 1
            # 雲の中->上
            df_resampled.loc[(df_resampled['current_price'] < np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled['current_price'].shift() > np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b]).shift()), price_cloud_cross] = 2
            # 雲の中->下
            df_resampled.loc[(df_resampled['current_price'] > np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled['current_price'].shift() < np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b]).shift()), price_cloud_cross] = 3
            # 雲の下->中
            df_resampled.loc[(df_resampled['current_price'] < np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled['current_price'].shift() > np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b]).shift()), price_cloud_cross] = 4

            # ゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[price_cloud_cross_gc_after1] = df_resampled.groupby((df_resampled[price_cloud_cross] == 2).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_cross] == 2, price_cloud_cross_gc_after1] = 0
            df_resampled[price_cloud_cross_gc_after2] = df_resampled.groupby((df_resampled[price_cloud_cross] == 4).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_cross] == 4, price_cloud_cross_gc_after2] = 0
            df_resampled[price_cloud_cross_dc_after1] = df_resampled.groupby((df_resampled[price_cloud_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_cross] == 1, price_cloud_cross_dc_after1] = 0
            df_resampled[price_cloud_cross_dc_after2] = df_resampled.groupby((df_resampled[price_cloud_cross] == 3).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_cross] == 3, price_cloud_cross_dc_after2] = 0

            # 先頭の要素を-9999999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_indexer(add_columns)] = -9999999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'一目均衡表計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_change_price(self, df, column_name, interval):
        '''
        変動した価格・変動率・変動フラグを計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): 追加するカラム名
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): 前日比を追加したDataFrame

        '''
        try:
            # 必要なカラムだけコピー
            df_resampled = df[['current_price']].copy()

            # 変数名の定義
            change_price = f'{column_name}_price'
            change_rate = f'{column_name}_rate'
            change_flag = f'{column_name}_flag'
            add_columns = [change_price, change_rate, change_flag]

            # 変動価格・変動率・変動フラグ(0:変動なし, 1:上昇, -1:下落)の計算
            df_resampled[change_price] = df_resampled['current_price'].shift(-interval) - df_resampled['current_price']
            df_resampled[change_rate] = df_resampled[change_price] / df_resampled['current_price']
            df_resampled[change_flag] = df_resampled[change_rate].apply(lambda x: -999 if pd.isna(x) else (0 if x == 0 else (1 if x > 0 else -1)))

            # データの末尾周囲の計算できない要素は-999で埋める
            for column in add_columns:
                df_resampled[column].fillna(-999, inplace=True)

            # 元のデータに計算で追加したデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # 計算(リサンプリング)対象外の行は直前の値で埋める
            for column in add_columns:
                df[column].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df