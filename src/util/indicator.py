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
            # df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のSMAで埋める
            df[column_name] = df[column_name].ffill()

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
            df_resampled[column_name] = df_resampled[price_column_name].ewm(span = window_size, min_periods = window_size).mean().round(1)

            # window_size - 1番目のデータでは計算ができずNaNになるので-1で埋める
            # df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のEMAで埋める
            df[column_name] = df[column_name].ffill()

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
            # df_resampled[column_name].fillna(-1, inplace=True)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # 2分足以上の場合は間の数値を前のWMAで埋める
            df[column_name] = df[column_name].ffill()

        except Exception as e:
            self.log.error(f'WMA計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ma_cross(self, df, interval):
        '''
        別期間軸の移動平均線のクロスや関連性を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
            interval(int): MAを計算する間隔(何分足として計算するか)

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): MAクロスを追加したDataFrame

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
                        diff_rate = f'{diff}_rate'

                        # ゴールデンクロス・デッドクロスの判定
                        short_shifted = df_resampled[column_short].shift(1)
                        long_shifted = df_resampled[column_long].shift(1)

                        # Nan行のマスクを作成
                        nan_mask = pd.isna(short_shifted) | pd.isna(long_shifted)

                        # ゴールデンクロス・デッドクロスの計算
                        df_resampled[golden_cross] = np.where(
                            nan_mask, np.nan, ((short_shifted <= long_shifted) & (df_resampled[column_short] > df_resampled[column_long])).astype(int)
                        )

                        df_resampled[dead_cross] = np.where(
                            nan_mask, np.nan, ((short_shifted >= long_shifted) & (df_resampled[column_short] < df_resampled[column_long])).astype(int)
                        )

                        # 直近でフラグが立ってからの経過時間
                        df_resampled['gc_id'] = df_resampled[golden_cross].cumsum()
                        df_resampled[golden_cross_after] = df_resampled.groupby('gc_id').cumcount()
                        df_resampled['dc_id'] = df_resampled[dead_cross].cumsum()
                        df_resampled[dead_cross_after] = df_resampled.groupby('dc_id').cumcount()

                        # もともとNanのデータについては経過時間カラムもNanにする
                        df_resampled.loc[nan_mask, golden_cross_after] = np.nan
                        df_resampled.loc[nan_mask, dead_cross_after] = np.nan

                        # 最初にゴールデンクロス・デッドクロスとなった行以前の値を-1で埋める(ただしNanはNanのまま)
                        first_golden_cross_index = df_resampled[df_resampled[golden_cross] == 1].index.min()
                        first_dead_cross_index = df_resampled[df_resampled[dead_cross] == 1].index.min()
                        if pd.notna(first_golden_cross_index):
                            df_resampled.loc[:first_golden_cross_index - 1, golden_cross_after] = df_resampled.loc[:first_golden_cross_index - 1, golden_cross_after].where(nan_mask, -1)
                        if pd.notna(first_dead_cross_index):
                            df_resampled.loc[:first_dead_cross_index - 1, dead_cross_after] = df_resampled.loc[:first_dead_cross_index - 1, dead_cross_after].where(nan_mask, -1)

                        # 短期と長期の差の額と終値に対する比率を計算
                        short_long_diff = (df_resampled[column_short] - df_resampled[column_long]).round(5)
                        df_resampled[diff] = short_long_diff.round(2)
                        df_resampled[diff_rate] = ((short_long_diff * 1000) / df_resampled['close']).round(3)
                        add_columns.extend([golden_cross, golden_cross_after, dead_cross, dead_cross_after, diff, diff_rate])

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column] = df[column].ffill()

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

            # バンド(α)の幅の額と終値に対する率を計算
            band_width = (df_resampled['sigma_tmp'] * 2).round(6)
            df_resampled[f'{column_name}_width'] = band_width.round(3)
            df_resampled[f'{column_name}_width_rate'] = ((band_width * 1000) / df_resampled[price_column_name]).round(3)
            add_columns.extend([f'{column_name}_width', f'{column_name}_width_rate'])

            # バンド幅の収縮・拡大度合いの額と終値に対する率を計算
            band_width_diff = band_width.diff().round(6)
            df_resampled[f'{column_name}_width_diff'] = band_width_diff.round(3)
            df_resampled[f'{column_name}_width_diff_rate'] = ((band_width_diff * 1000) / df_resampled[price_column_name]).round(3)
            add_columns.extend([f'{column_name}_width_diff', f'{column_name}_width_diff_rate'])

            for sigma in [1, 2, 3]:
                band_upper_diff = (df_resampled[f'{column_name}_upper_{sigma}_alpha'] - df_resampled[price_column_name]).round(6)
                band_lower_diff = (df_resampled[f'{column_name}_lower_{sigma}_alpha'] - df_resampled[price_column_name]).round(6)

                # 終値とバンド(+3α~-3α)の差の額と終値に対する率を計算
                df_resampled[f'{column_name}_upper_{sigma}_diff'] = band_upper_diff.round(3)
                df_resampled[f'{column_name}_lower_{sigma}_diff'] = band_lower_diff.round(3)
                df_resampled[f'{column_name}_upper_{sigma}_diff_rate'] = ((band_upper_diff * 1000) / df_resampled[price_column_name]).round(3)
                df_resampled[f'{column_name}_lower_{sigma}_diff_rate'] = ((band_lower_diff * 1000) / df_resampled[price_column_name]).round(3)

                # 終値とバンドの位置を計算 +3α~-3αそれぞれの値を終値が超えていたら1、超えていなければ0
                df_resampled[f'{column_name}_upper_{sigma}_position'] = df_resampled[f'{column_name}_upper_{sigma}_diff'].apply(lambda x: np.nan if pd.isna(x) else (0 if x >= 0 else 1))
                df_resampled[f'{column_name}_lower_{sigma}_position'] = df_resampled[f'{column_name}_lower_{sigma}_diff'].apply(lambda x: np.nan if pd.isna(x) else (0 if x >= 0 else 1))

                add_columns.extend([f'{column_name}_upper_{sigma}_diff', f'{column_name}_lower_{sigma}_diff'])
                add_columns.extend([f'{column_name}_upper_{sigma}_diff_rate', f'{column_name}_lower_{sigma}_diff_rate'])
                add_columns.extend([f'{column_name}_upper_{sigma}_position', f'{column_name}_lower_{sigma}_position'])

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            for column in add_columns:
                # リサンプリング対象外の行は、直近の値で埋める
                df[column] = df[column].ffill()

                # window_size - 1番目までのデータでは計算ができずNaNになるので-999で埋める
                ##df[column].fillna(-999, inplace=True)

        except Exception as e:
            self.log.error(f'ボリンジャーバンド計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rsi(self, df, column_name,  window_size, interval, price_column_name = 'current_price'):
        '''
        相対力指数(RSI)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定したカラム名が存在かつデータが時系列で連続していること
            column_name(str): RSIを設定するカラム名
            window_size(int): RSIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): RSIを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # 前レコードとの差分を計算
            df_resampled['diff'] = df_resampled[price_column_name].diff()

            # 前レコードとの差分がプラスならその値、マイナスなら0を設定
            df_resampled['up'] = df_resampled['diff'].apply(lambda x: x if x > 0 else 0)

            # 前レコードとの差分がマイナスならその値、プラスなら0を設定
            df_resampled['down'] = df_resampled['diff'].apply(lambda x: abs(x) if x < 0 else 0)

            # 平均上昇幅と平均下降幅を計算
            df_resampled['up_mean'] = df_resampled['up'].rolling(window = window_size).mean()
            df_resampled['down_mean'] = df_resampled['down'].rolling(window = window_size).mean()

            # ついでなので終値に対しての平均上昇幅と平均下降幅のカラムを計算して追加する
            df_resampled[f'up_mean_rate_{interval}min_{window_size}piece'] = ((df_resampled['up_mean'] * 1000) / df_resampled[price_column_name]).round(3)
            df_resampled[f'down_mean_rate_{interval}min_{window_size}piece'] = ((df_resampled['down_mean'] * 1000) / df_resampled[price_column_name]).round(3)

            # RSIを計算
            if df_resampled['down_mean'].isna().all() or df_resampled['up_mean'].isna().all():
                ##df_resampled[column_name] = -999
                df_resampled[column_name] = None
            elif df_resampled['down_mean'].sum() == 0:
                if df_resampled['up_mean'].sum() == 0:
                    df_resampled[column_name] = 50
                else:
                    df_resampled[column_name] = 100
            else:
                df_resampled[column_name] = (100 - 100 / (1 + df_resampled['up_mean'] / df_resampled['down_mean'])).round(2)

            # 先頭の要素を-999で埋める
            ##df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name,f'up_mean_rate_{interval}min_{window_size}piece',f'down_mean_rate_{interval}min_{window_size}piece']], left_index=True, right_index=True, how='left')

            # 間の要素の値を直近の値で埋める
            df[column_name] = df[column_name].ffill()

        except Exception as e:
            self.log.error(f'RSI計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rci(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        順位相関指数(RCI)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定したカラム名が存在かつデータが時系列で連続していること
            column_name(str): RCIを設定するカラム名
            window_size(int): RCIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): RCIを追加したDataFrame
        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # RCIの計算・カラムを追加
            df_resampled[column_name] = df_resampled[price_column_name].rolling(window=window_size).apply(self.calc_rci, raw=False)

            # 初めの方の要素はNaNになるので直前の値で埋める
            df_resampled[column_name] = df_resampled[column_name].ffill()

            # 先頭の要素を-999で埋める
            ##df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name]], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を前の値で埋める
            df[column_name] = df[column_name].ffill()

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

    def get_macd(self, df, column_name, short_window_size, long_window_size, signal_window_size, interval, price_column_name = 'current_price'):
        '''
        MACDを計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定したカラム名が存在かつデータが時系列で連続していること
            column_name(str): MACDを設定するカラム名
            short_window_size(int): 短期EMAのウィンドウ幅
            long_window_size(int): 長期EMAのウィンドウ幅
            signal_window_size(int): シグナル線のウィンドウ幅
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): MACDを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # カラム名の設定
            macd = column_name
            macd_rate = f'{macd}_rate'
            macd_position = f'{macd}_position'
            macd_signal = f'{macd}_signal'
            macd_signal_rate = f'{macd_signal}_rate'
            macd_histogram = f'{macd}_diff'
            macd_histogram_rate = f'{macd_histogram}_rate'
            macd_histogram_flag = f'{macd_histogram}_flag'
            macd_golden_cross = f'{macd}_golden_cross'
            macd_dead_cross = f'{macd}_dead_cross'
            macd_golden_cross_after = f'{macd}_golden_cross_after'
            macd_dead_cross_after = f'{macd}_dead_cross_after'
            macd_cross_trend = f'{macd}_cross_trend'
            add_columns = []

            # MACD(短期EMA - 長期EMA)の計算 額と終値に対する率を計算
            short_ema = df_resampled[price_column_name].ewm(span = short_window_size, min_periods = short_window_size).mean()
            long_ema = df_resampled[price_column_name].ewm(span = long_window_size, min_periods = long_window_size).mean()
            macd_value = (short_ema - long_ema).round(6)
            df_resampled[macd] = macd_value.round(2)
            df_resampled[macd_rate] = ((macd_value * 1000) / df_resampled[price_column_name]).round(3)
            df_resampled[macd_position] = macd_value.apply(lambda x: np.nan if pd.isna(x) else (0 if x >= 0 else 1))
            add_columns.extend([macd, macd_rate, macd_position])

            # MACDシグナルの計算 額と終値に対する率を計算
            macd_signal_value = macd_value.ewm(span = signal_window_size).mean().round(6)
            df_resampled[macd_signal] = macd_signal_value.round(2)
            df_resampled[macd_signal_rate] = ((macd_signal_value * 1000) / df_resampled[price_column_name]).round(3)
            add_columns.extend([macd_signal, macd_signal_rate])

            # MACDとMACDシグナルの差(ヒストグラム)を計算 額と終値に対する率を計算
            macd_histogram_value = (macd_value - macd_signal_value).round(6)
            df_resampled[macd_histogram] = macd_histogram_value.round(3)
            df_resampled[macd_histogram_rate] = ((macd_histogram_value * 1000) / df_resampled[price_column_name]).round(3)
            df_resampled[macd_histogram_flag] = macd_histogram_value.apply(lambda x: np.nan if pd.isna(x) else (0 if x >= 0 else 1))
            add_columns.extend([macd_histogram, macd_histogram_rate, macd_histogram_flag])

            # MACDとMACDシグナルのゴールデンクロス・デッドクロスを計算する (MACDがシグナルを上抜けたらゴールデンクロス)
            macd_shifted = df_resampled[macd].shift(1)
            macd_signal_shifted = df_resampled[macd_signal].shift(1)

            # NaN行のマスクを作成
            nan_mask = pd.isna(macd_shifted) | pd.isna(macd_signal_shifted) | pd.isna(df_resampled[macd]) | pd.isna(df_resampled[macd_signal])

            # MACDとMACDシグナルのゴールデンクロス・デッドクロスの計算
            df_resampled[macd_golden_cross] = np.where(
                nan_mask, np.nan, ((df_resampled[macd_signal] > 0) & (df_resampled[macd] > df_resampled[macd_signal]) & (macd_shifted < macd_signal_shifted)).astype(int)
            )
            df_resampled[macd_dead_cross] = np.where(
                nan_mask, np.nan, ((df_resampled[macd_signal] < 0) & (df_resampled[macd] < df_resampled[macd_signal]) & (macd_shifted > macd_signal_shifted)).astype(int)
            )

            add_columns.extend([macd_golden_cross, macd_dead_cross])

            # 直近でゴールデンクロス・デッドクロスをしてからの経過時間
            df_resampled['gc_id'] = df_resampled[macd_golden_cross].cumsum()
            df_resampled[macd_golden_cross_after] = df_resampled.groupby('gc_id').cumcount()
            df_resampled['dc_id'] = df_resampled[macd_dead_cross].cumsum()
            df_resampled[macd_dead_cross_after] = df_resampled.groupby('dc_id').cumcount()

            # 最初にクロスした以前の行を値を-1で埋める(ただしNanはNanのまま)
            first_macd_golden_cross_index = df_resampled[df_resampled[macd_golden_cross] == 1].index.min()
            first_macd_dead_cross_index = df_resampled[df_resampled[macd_dead_cross] == 1].index.min()
            if pd.notna(first_macd_golden_cross_index):
                df_resampled.loc[:first_macd_golden_cross_index - 1, macd_golden_cross_after] = df_resampled.loc[:first_macd_golden_cross_index - 1, macd_golden_cross_after].where(nan_mask, -1)
            if pd.notna(first_macd_dead_cross_index):
                df_resampled.loc[:first_macd_dead_cross_index - 1, macd_dead_cross_after] = df_resampled.loc[:first_macd_dead_cross_index - 1, macd_dead_cross_after].where(nan_mask, -1)

            add_columns.extend([macd_golden_cross_after, macd_dead_cross_after])

            # MACDとMACDシグナルのゴールデンクロス・デッドクロスから現在のトレンドを計算
            df_resampled[macd_cross_trend] = (df_resampled[macd_golden_cross_after] - df_resampled[macd_dead_cross_after]).apply(lambda x: np.nan if pd.isna(x) else (-1 if x == 0 else (0 if x > 0 else 1)))
            add_columns.append(macd_cross_trend)

            # MACDとMACDシグナルの傾きと終値に対する率を計算 直近何本の差分から傾きを計算するか
            for count in [1, 3, 5, 10, 15]:
                # 幅が長すぎるとデータが取れないのでスキップ
                if interval * count >= 300:
                    continue

                macd_x_slope = f'{macd}_{count}_slope'
                macd_x_slope_rate = f'{macd_x_slope}_rate'
                macd_signal_x_slope = f'{macd_signal}_{count}_slope'
                macd_signal_x_slope_rate = f'{macd_signal_x_slope}_rate'
                macd_x_mismatch = f'{macd}_{count}_mismatch'
                macd_x_mismatch_count = f'{macd}_{count}_mismatch_count'

                # MACDとMACDシグナルの傾きの計算
                macd_x_slope_value = (df_resampled[macd].diff(count) / count).round(6)
                macd_signal_x_slope_value = (df_resampled[macd_signal].diff(count) / count).round(6)
                df_resampled[macd_x_slope] = macd_x_slope_value.round(3)
                df_resampled[macd_signal_x_slope] = macd_signal_x_slope_value.round(3)
                df_resampled[macd_x_slope_rate] = ((macd_x_slope_value * 1000) / df_resampled[price_column_name]).round(3)
                df_resampled[macd_signal_x_slope_rate] = ((macd_signal_x_slope_value * 1000) / df_resampled[price_column_name]).round(3)
                add_columns.extend([macd_x_slope, macd_x_slope_rate, macd_signal_x_slope, macd_signal_x_slope_rate])

                # MACDの傾きと価格の傾きの不一致(ダイバージェンス)フラグ
                df_resampled[macd_x_mismatch] = (df_resampled[macd_x_slope] * df_resampled[macd_signal_x_slope]).apply(lambda x: np.nan if pd.isna(x) else (0 if x >= 0 else 1))
                add_columns.append(macd_x_mismatch)

                # NaN行のマスクを作成
                nan_mask = pd.isna(df_resampled[macd_x_mismatch]) | pd.isna(df_resampled[macd_x_mismatch].shift(1))

                # MACDの傾きと価格の傾きの不一致(ダイバージェンス)フラグが続いている回数を計算
                df_resampled[macd_x_mismatch_count] = df_resampled[macd_x_mismatch].groupby((df_resampled[macd_x_mismatch] != df_resampled[macd_x_mismatch].shift(1)).cumsum()).cumcount() + 1
                # 不一致フラグが0の行の回数を0に設定
                df_resampled.loc[df_resampled[macd_x_mismatch] == 0, macd_x_mismatch_count] = 0
                # NaNの行はNaNに設定
                df_resampled.loc[nan_mask, macd_x_mismatch_count] = np.nan
                add_columns.append(macd_x_mismatch_count)

            # 先頭の要素を-999で埋める
            ##df_resampled.iloc[0, df_resampled.columns.get_indexer(add_columns)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column] = df[column].ffill()

        except Exception as e:
            self.log.error(f'MACD計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_psy(self, df, column_name, window_size, interval, price_column_name = 'current_price'):
        '''
        サイコロジカルライン(PSY)を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定したカラム名が存在し、データが時系列で連続していること
            column_name(str): PSYを設定するカラム名
            window_size(int): PSYを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): PSYを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # 前日との差分を計算
            df_resampled['diff'] = df_resampled[price_column_name].diff()

            # 前日との差分がプラスなら1、マイナスなら0を設定
            df_resampled['up'] = df_resampled['diff'].apply(lambda x: 1 if x > 0 else 0)

            # PSYを計算
            df_resampled[column_name] = (df_resampled['up'].rolling(window = window_size).sum() / window_size * 100).round(1)

            # 先頭の要素を-999で埋める
            ##df_resampled.iloc[0, df_resampled.columns.get_loc(column_name)] = -999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[column_name], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name] = df[column_name].ffill()

        except Exception as e:
            self.log.error(f'PSY計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_parabolic(self, df, column_name, min_af, max_af, interval, price_column_name = 'current_price'):
        '''
        パラボリック(SAR)を計算してカラムに追加する(終値のみから算出)

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※price_column_nameで指定したカラム名が存在し、データが時系列で連続していること
            column_name(str): SARを設定するカラム名
            min_af(float): 加速因数の初期値(最小値)
            max_af(float): 加速因数の最大値
            interval(int): 何分足として計算するか
            price_column_name(str): 終値のカラム名

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): SARを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[[price_column_name]].iloc[::interval, :].copy()
            else:
                df_resampled = df[[price_column_name]].copy()

            # 初期値の設定 SARの初期値と前日のEPは初期値の終値になる
            sar_list = [df_resampled[price_column_name].iloc[0]]
            ep = df_resampled[price_column_name].iloc[0]
            af = min_af
            trend = ''

            # SARの計算
            for i in range(1, len(df_resampled)):
                current_price = df_resampled[price_column_name].iloc[i]

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
            # SARが一つ前のSARよりも高い場合は1、低い場合は0
            df_resampled[column_name_flag] = (df_resampled[column_name] > df_resampled[column_name].shift(1)).astype(int)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name, column_name_flag]], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name] = df[column_name].ffill()

            df[column_name_flag] = df[column_name_flag].ffill()

        except Exception as e:
            self.log.error(f'SAR計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_parabolic_hlc(self, df, column_name, min_af, max_af, interval):
        '''
        パラボリック(SAR)を計算してカラムに追加する(三本値から算出)

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※high, low, closeカラムが存在し、データが時系列で連続していること
            column_name(str): SARを設定するカラム名
            min_af(float): 加速因数の初期値(最小値)
            max_af(float): 加速因数の最大値
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(pandas.DataFrame): SARを追加したDataFrame

        '''
        try:
            # 計算に必要なカラム名のリスト
            columns = ['high', 'low', 'close']

            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[columns].iloc[::interval, :].copy()
            else:
                df_resampled = df[columns].copy()

            # カラム名の設定
            column_name_diff = f'{column_name}_diff'
            column_name_diff_rate = f'{column_name_diff}_rate'

            # 初期値の設定 SARの初期値と前日のEPは初期値の終値になる
            sar_list = [df_resampled['close'].iloc[0]]
            sar_diff_list = [0]
            ep = df_resampled['close'].iloc[0]
            af = min_af
            trend = ''

            # SARの計算
            for i in range(1, len(df_resampled)):
                close = df_resampled['close'].iloc[i]
                high = df_resampled['high'].iloc[i]
                low = df_resampled['low'].iloc[i]
                sar_diff = 0

                # 1つ目の要素の場合は前日との差分で上昇か下降トレンドかを判定
                if i == 1:
                    if sar_list[0] < close:
                        trend = 'up'
                    else:
                        trend = 'down'

                # 上昇トレンドの場合
                if trend == 'up':
                    # トレンド内での高値を更新した場合
                    if ep < high:
                        ep, af = high, min(af + min_af, max_af)

                    # SARの計算
                    sar = sar_list[i - 1] + af * (ep - sar_list[i - 1])
                    # SARと安値の差分を計算
                    sar_diff = sar - low

                    # SARが現在の安値と同じか高くなった場合はトレンドを反転
                    if sar >= low:
                        trend, af = 'down', min_af
                        sar = ep
                        ep = high
                        sar_diff = 0

                # 下降トレンドの場合
                else:
                    # トレンド内での安値を更新した場合
                    if ep > low:
                        ep, af = low, min(af + min_af, max_af)

                    # SARの計算
                    sar = sar_list[i - 1] - af * (sar_list[i - 1] - ep)
                    # SARと高値の差分を計算
                    sar_diff = sar - high

                    # SARが現在の高値と同じか高くなった場合はトレンドを反転
                    if sar <= high:
                        trend, af = 'up', min_af
                        sar = ep
                        ep = low
                        sar_diff = 0


                sar_list.append(round(sar, 3))
                sar_diff_list.append(round(sar_diff, 3))

            df_resampled[column_name] = sar_list
            df_resampled[column_name_diff] = sar_diff_list
            column_name_flag = f'{column_name}_flag'
            column_name_reverse_flag = f'{column_name}_reverse_flag'

            # SARが一つ前のSARよりも高い場合は1、低い場合は0
            df_resampled[column_name_flag] = (df_resampled[column_name] > df_resampled[column_name].shift(1)).astype(int)

            # NaN行のマスクを作成
            nan_mask = pd.isna(df_resampled[column_name_flag]) | pd.isna(df_resampled[column_name_flag].shift(1))

            # トレンドが反転した場合は1、そうでない場合は0
            df_resampled[column_name_reverse_flag] = np.where(nan_mask, 0, (df_resampled[column_name_flag] != df_resampled[column_name_flag].shift(1)).astype(int))

            # SARとローソク足の差分について終値に対する率を計算
            df_resampled[column_name_diff_rate] = ((df_resampled[column_name_diff] * 1000) / df_resampled['close']).round(3)

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[[column_name, column_name_diff, column_name_diff_rate, column_name_flag, column_name_reverse_flag]], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name] = df[column_name].ffill()
            df[column_name_diff] = df[column_name_diff].ffill()
            df[column_name_diff_rate] = df[column_name_diff_rate].ffill()
            df[column_name_flag] = df[column_name_flag].ffill()
            df[column_name_reverse_flag] = df[column_name_reverse_flag].ffill()

        except Exception as e:
            self.log.error(f'SAR計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ichimoku_cloud(self, df, column_name, short_window_size, long_window_size, interval, close_column_name = 'current_price'):
        '''
        一目均衡表を計算してカラムに追加する

        Args:
            df(pandas.DataFrame): 板情報のデータ
                ※close_column_nameで指定したカラム(+high(高値)+row(終値))が存在かつデータが時系列で連続していること
            column_name(str): 一目均衡表を設定するカラム名
            short_window_size(int): 短期のウィンドウ幅
            long_window_size(int): 長期のウィンドウ幅
            interval(int): 何分足として計算するか
            close_column_name(str): 終値のカラム名

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
            base_conversion_diff_rate = f'{column_name}_bc_diff_rate'
            base_conversion_position = f'{column_name}_bc_position'
            base_conversion_cross = f'{column_name}_bc_cross'
            base_conversion_gc_after = f'{column_name}_bc_gc_after'
            base_conversion_dc_after = f'{column_name}_bc_dc_after'
            price_lagging_diff = f'{column_name}_pl_diff'
            price_lagging_diff_rate = f'{column_name}_pl_diff_rate'
            price_lagging_position = f'{column_name}_pl_position'
            price_lagging_cross = f'{column_name}_pl_cross'
            price_lagging_gc_after = f'{column_name}_pl_gc_after'
            price_lagging_dc_after = f'{column_name}_pl_dc_after'
            leading_span_diff = f'{column_name}_ls_diff'
            leading_span_diff_rate = f'{column_name}_ls_diff_rate'
            leading_span_position = f'{column_name}_ls_position'
            leading_span_cross = f'{column_name}_ls_cross'
            leading_span_gc_after = f'{column_name}_ls_gc_after'
            leading_span_dc_after = f'{column_name}_ls_dc_after'
            price_cloud_high_diff = f'{column_name}_cloud_high_diff'
            price_cloud_high_diff_rate = f'{column_name}_cloud_high_diff_rate'
            price_cloud_low_diff = f'{column_name}_cloud_low_diff'
            price_cloud_low_diff_rate = f'{column_name}_cloud_low_diff_rate'
            price_cloud_position = f'{column_name}_cloud_position'
            price_cloud_lower_gc = f'{column_name}_cloud_lower_gc'
            price_cloud_upper_gc = f'{column_name}_cloud_upper_gc'
            price_cloud_lower_dc = f'{column_name}_cloud_lower_dc'
            price_cloud_upper_dc = f'{column_name}_cloud_upper_dc'
            price_cloud_lower_gc_after = f'{column_name}_cloud_lower_gc_after'
            price_cloud_upper_gc_after = f'{column_name}_cloud_upper_gc_after'
            price_cloud_lower_dc_after = f'{column_name}_cloud_lower_dc_after'
            price_cloud_upper_dc_after = f'{column_name}_cloud_upper_dc_after'

            add_columns = [base_line, conversion_line, leading_span_a, leading_span_b, lagging_span,
                           base_conversion_diff, base_conversion_diff_rate, base_conversion_position, base_conversion_cross, base_conversion_gc_after, base_conversion_dc_after,
                           price_lagging_diff, price_lagging_diff_rate, price_lagging_position, price_lagging_cross, price_lagging_gc_after, price_lagging_dc_after,
                           leading_span_diff, leading_span_diff_rate, leading_span_position, leading_span_cross, leading_span_gc_after, leading_span_dc_after,
                           price_cloud_high_diff, price_cloud_high_diff_rate, price_cloud_low_diff, price_cloud_low_diff_rate, price_cloud_position,
                            price_cloud_lower_gc, price_cloud_upper_gc, price_cloud_lower_dc, price_cloud_upper_dc,
                            price_cloud_lower_gc_after, price_cloud_upper_gc_after, price_cloud_lower_dc_after, price_cloud_upper_dc_after]

            # 高値/安値がない場合
            if 'high' not in df_resampled.columns:
                df_resampled['high'] = df_resampled[close_column_name]

            if 'low' not in df_resampled.columns:
                df_resampled['low'] = df_resampled[close_column_name]

            # 基準線の計算 long_window_size本の高値と安値の平均
            df_resampled[base_line] = ((df_resampled['high'].rolling(window = long_window_size).max() + df_resampled['low'].rolling(window = long_window_size).min()) / 2).round(3)

            # 転換線の計算 short_window_size本の高値と安値の平均
            df_resampled[conversion_line] = ((df_resampled['high'].rolling(window = short_window_size).max() + df_resampled['low'].rolling(window = short_window_size).min()) / 2).round(3)

            # 先行スパン1の計算 long_window_size本先の基準線と転換線の平均
            df_resampled[leading_span_a] = (((df_resampled[conversion_line] + df_resampled[base_line]) / 2).shift(long_window_size)).round(3)

            # 先行スパン2の計算 long_window_size x 2本の高値と安値の平均をlong_window_size本先にずらす
            df_resampled[leading_span_b] = (((df_resampled['high'].rolling(window = long_window_size * 2).max() + df_resampled['low'].rolling(window = long_window_size * 2).min()) / 2).shift(long_window_size)).round(3)

            # 遅行スパンの計算 現在の価格をlong_window_size本前にずらす
            df_resampled[lagging_span] = df_resampled[close_column_name].shift(-long_window_size)

            # 基準線と転換線の差の額/終値に対する差の比率/位置関係
            base_conversion_diff_value = (df_resampled[conversion_line] - df_resampled[base_line]).round(6)
            df_resampled[base_conversion_diff] = base_conversion_diff_value.round(3)
            df_resampled[base_conversion_diff_rate] = ((base_conversion_diff_value * 1000) / df_resampled[close_column_name]).round(3)
            df_resampled[base_conversion_position] = (df_resampled[conversion_line] - df_resampled[base_line]).apply(lambda x: np.nan if pd.isna(x) else (1 if x > 0 else 0))

            # 基準線と転換線のクロスフラグ
            nan_mask = pd.isna(df_resampled[conversion_line]) | pd.isna(df_resampled[base_line]) | pd.isna(df_resampled[conversion_line].shift(1)) | pd.isna(df_resampled[base_line].shift(1))
            df_resampled[base_conversion_cross] = 0
            df_resampled.loc[~nan_mask & (df_resampled[conversion_line] > df_resampled[base_line]) & (df_resampled[conversion_line].shift(1) < df_resampled[base_line].shift(1)), base_conversion_cross] = 1
            df_resampled.loc[~nan_mask & (df_resampled[conversion_line] < df_resampled[base_line]) & (df_resampled[conversion_line].shift(1) > df_resampled[base_line].shift(1)), base_conversion_cross] = -1
            df_resampled.loc[nan_mask, base_conversion_cross] = np.nan

            # 基準線と転換線のゴールデンクロス/デッドクロスからの経過データ数を計算
            nan_mask = pd.isna(df_resampled[base_conversion_cross])
            df_resampled[base_conversion_gc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == 1, base_conversion_gc_after] = 0
            df_resampled[base_conversion_dc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == -1, base_conversion_dc_after] = 0
            df_resampled.loc[nan_mask, base_conversion_gc_after] = np.nan
            df_resampled.loc[nan_mask, base_conversion_dc_after] = np.nan

            # 基準線と転換線のゴールデンクロス/デッドクロスからの経過データ数を計算
            nan_mask = pd.isna(df_resampled[base_conversion_cross])
            df_resampled[base_conversion_gc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == 1, base_conversion_gc_after] = 0
            df_resampled[base_conversion_dc_after] = df_resampled.groupby((df_resampled[base_conversion_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[base_conversion_cross] == -1, base_conversion_dc_after] = 0
            df_resampled.loc[nan_mask, base_conversion_gc_after] = np.nan
            df_resampled.loc[nan_mask, base_conversion_dc_after] = np.nan

            # 最初にゴールデンクロス/デッドクロスが発生した行以前の値を-1で埋める(ただしNanはNanのまま)
            first_base_conversion_gc_index = df_resampled[df_resampled[base_conversion_cross] == 1].index.min()
            first_base_conversion_dc_index = df_resampled[df_resampled[base_conversion_cross] == -1].index.min()
            if pd.notna(first_base_conversion_gc_index):
                df_resampled.loc[:first_base_conversion_gc_index - 1, base_conversion_gc_after] = df_resampled.loc[:first_base_conversion_gc_index - 1, base_conversion_gc_after].where(nan_mask, -1)
            if pd.notna(first_base_conversion_dc_index):
                df_resampled.loc[:first_base_conversion_dc_index - 1, base_conversion_dc_after] = df_resampled.loc[:first_base_conversion_dc_index - 1, base_conversion_dc_after].where(nan_mask, -1)

            # 終値と遅行スパンの差の額/終値に対する差の比率/位置関係
            price_lagging_diff_value = (df_resampled[close_column_name] - df_resampled[lagging_span]).round(6)
            df_resampled[price_lagging_diff] = price_lagging_diff_value.round(3)
            df_resampled[price_lagging_diff_rate] = ((price_lagging_diff_value * 1000) / df_resampled[close_column_name]).round(3)
            df_resampled[price_lagging_position] = (df_resampled[close_column_name] > df_resampled[lagging_span]).astype(int)

            # 終値と遅行スパンのクロスフラグ
            df_resampled[price_lagging_cross] = 0
            df_resampled.loc[(df_resampled[close_column_name] > df_resampled[lagging_span]) & (df_resampled[close_column_name].shift(1) < df_resampled[lagging_span].shift(1)), price_lagging_cross] = 1
            df_resampled.loc[(df_resampled[close_column_name] < df_resampled[lagging_span]) & (df_resampled[close_column_name].shift(1) > df_resampled[lagging_span].shift(1)), price_lagging_cross] = -1

            # 終値と遅行スパンのゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[price_lagging_gc_after] = df_resampled.groupby((df_resampled[price_lagging_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_lagging_cross] == 1, price_lagging_gc_after] = 0
            df_resampled[price_lagging_dc_after] = df_resampled.groupby((df_resampled[price_lagging_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_lagging_cross] == -1, price_lagging_dc_after] = 0

            # 最初にゴールデンクロス/デッドクロスが発生した行以前の値を-1で埋める(ただしNanはNanのまま)
            first_price_lagging_gc_index = df_resampled[df_resampled[price_lagging_cross] == 1].index.min()
            first_price_lagging_dc_index = df_resampled[df_resampled[price_lagging_cross] == -1].index.min()
            if pd.notna(first_price_lagging_gc_index):
                df_resampled.loc[:first_price_lagging_gc_index - 1, price_lagging_gc_after] = -1
            if pd.notna(first_price_lagging_dc_index):
                df_resampled.loc[:first_price_lagging_dc_index - 1, price_lagging_dc_after] = -1

            # 先行スパン1と2の差の額/終値に対する差の比率/位置関係
            leading_span_diff_value = (df_resampled[leading_span_a] - df_resampled[leading_span_b]).round(6)
            df_resampled[leading_span_diff] = leading_span_diff_value.round(3)
            df_resampled[leading_span_diff_rate] = ((leading_span_diff_value * 1000) / df_resampled[close_column_name]).round(3)
            nan_mask = pd.isna(df_resampled[leading_span_a]) | pd.isna(df_resampled[leading_span_b])
            df_resampled[leading_span_position] = np.where(nan_mask, np.nan, (df_resampled[leading_span_a] > df_resampled[leading_span_b]).astype(int))

            # 先行スパン1と2のクロスフラグ
            nan_mask = pd.isna(df_resampled[leading_span_a]) | pd.isna(df_resampled[leading_span_b]) | pd.isna(df_resampled[leading_span_a].shift(1)) | pd.isna(df_resampled[leading_span_b].shift(1))
            df_resampled[leading_span_cross] = 0
            df_resampled.loc[~nan_mask & (df_resampled[leading_span_a] > df_resampled[leading_span_b]) & (df_resampled[leading_span_a].shift(1) < df_resampled[leading_span_b].shift(1)), leading_span_cross] = 1
            df_resampled.loc[~nan_mask & (df_resampled[leading_span_a] < df_resampled[leading_span_b]) & (df_resampled[leading_span_a].shift(1) > df_resampled[leading_span_b].shift(1)), leading_span_cross] = -1
            df_resampled.loc[nan_mask, leading_span_cross] = np.nan

            # 先行スパン1と2のゴールデンクロス/デッドクロスからの経過データ数を計算
            nan_mask = pd.isna(df_resampled[leading_span_cross])
            df_resampled[leading_span_gc_after] = df_resampled.groupby((df_resampled[leading_span_cross] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[leading_span_cross] == 1, leading_span_gc_after] = 0
            df_resampled[leading_span_dc_after] = df_resampled.groupby((df_resampled[leading_span_cross] == -1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[leading_span_cross] == -1, leading_span_dc_after] = 0
            df_resampled.loc[nan_mask, leading_span_gc_after] = np.nan
            df_resampled.loc[nan_mask, leading_span_dc_after] = np.nan

            # 最初にゴールデンクロス/デッドクロスが発生した行以前の値を-1で埋める(ただしNanはNanのまま)
            first_leading_span_gc_index = df_resampled[df_resampled[leading_span_cross] == 1].index.min()
            first_leading_span_dc_index = df_resampled[df_resampled[leading_span_cross] == -1].index.min()
            if pd.notna(first_leading_span_gc_index):
                df_resampled.loc[:first_leading_span_gc_index - 1, leading_span_gc_after] = df_resampled.loc[:first_leading_span_gc_index - 1, leading_span_gc_after].where(nan_mask, -1)
            if pd.notna(first_leading_span_dc_index):
                df_resampled.loc[:first_leading_span_dc_index - 1, leading_span_dc_after] = df_resampled.loc[:first_leading_span_dc_index - 1, leading_span_dc_after].where(nan_mask, -1)

            # 終値と雲(先行スパン1と2の間)の上限・下限との差の額/終値に対する差の比率/位置関係
            price_cloud_high_diff_value = (df_resampled[close_column_name] - np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])).round(6)
            price_cloud_low_diff_value = (df_resampled[close_column_name] - np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])).round(6)
            df_resampled[price_cloud_high_diff] = price_cloud_high_diff_value.round(3)
            df_resampled[price_cloud_low_diff] = price_cloud_low_diff_value.round(3)
            df_resampled[price_cloud_high_diff_rate] = ((price_cloud_high_diff_value * 1000) / df_resampled[close_column_name]).round(3)
            df_resampled[price_cloud_low_diff_rate] = ((price_cloud_low_diff_value * 1000) / df_resampled[close_column_name]).round(3)
            # 雲の上下位置フラグ(1: 上、 0: 中、-1: 下)
            nan_mask = pd.isna(df_resampled[leading_span_a]) | pd.isna(df_resampled[leading_span_b])
            df_resampled[price_cloud_position] = 0
            df_resampled.loc[(df_resampled[close_column_name] > np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])), price_cloud_position] = 1
            df_resampled.loc[(df_resampled[close_column_name] < np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])), price_cloud_position] = -1
            df_resampled.loc[nan_mask, price_cloud_position] = np.nan

            # 終値と雲(先行スパン1と2の間)の上限・下限のクロスフラグ
            nan_mask = pd.isna(df_resampled[leading_span_a]) | pd.isna(df_resampled[leading_span_b]) | pd.isna(df_resampled[close_column_name]) | pd.isna(df_resampled[close_column_name].shift(1))
            df_resampled[price_cloud_upper_dc] = 0
            df_resampled[price_cloud_upper_gc] = 0
            df_resampled[price_cloud_lower_dc] = 0
            df_resampled[price_cloud_lower_gc] = 0
            df_resampled.loc[(df_resampled[close_column_name] >= np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled[close_column_name].shift(1) < np.maximum(df_resampled[leading_span_a].shift(1), df_resampled[leading_span_b].shift(1))), price_cloud_upper_dc] = 1
            df_resampled.loc[(df_resampled[close_column_name] <= np.maximum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled[close_column_name].shift(1) > np.maximum(df_resampled[leading_span_a].shift(1), df_resampled[leading_span_b].shift(1))), price_cloud_upper_gc] = 1
            df_resampled.loc[(df_resampled[close_column_name] >= np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled[close_column_name].shift(1) < np.minimum(df_resampled[leading_span_a].shift(1), df_resampled[leading_span_b].shift(1))), price_cloud_lower_dc] = 1
            df_resampled.loc[(df_resampled[close_column_name] <= np.minimum(df_resampled[leading_span_a], df_resampled[leading_span_b])) & (df_resampled[close_column_name].shift(1) > np.minimum(df_resampled[leading_span_a].shift(1), df_resampled[leading_span_b].shift(1))), price_cloud_lower_gc] = 1
            df_resampled.loc[nan_mask, price_cloud_upper_dc] = np.nan
            df_resampled.loc[nan_mask, price_cloud_upper_gc] = np.nan
            df_resampled.loc[nan_mask, price_cloud_lower_dc] = np.nan
            df_resampled.loc[nan_mask, price_cloud_lower_gc] = np.nan

            # ゴールデンクロス/デッドクロスからの経過データ数を計算
            df_resampled[price_cloud_upper_dc_after] = df_resampled.groupby((df_resampled[price_cloud_upper_dc] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_upper_dc] == 1, price_cloud_upper_dc_after] = 0
            df_resampled[price_cloud_upper_gc_after] = df_resampled.groupby((df_resampled[price_cloud_upper_gc] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_upper_gc] == 1, price_cloud_upper_gc_after] = 0
            df_resampled[price_cloud_lower_dc_after] = df_resampled.groupby((df_resampled[price_cloud_lower_dc] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_lower_dc] == 1, price_cloud_lower_dc_after] = 0
            df_resampled[price_cloud_lower_gc_after] = df_resampled.groupby((df_resampled[price_cloud_lower_gc] == 1).cumsum()).cumcount()
            df_resampled.loc[df_resampled[price_cloud_lower_gc] == 1, price_cloud_lower_gc_after] = 0
            df_resampled.loc[nan_mask, price_cloud_upper_dc_after] = np.nan
            df_resampled.loc[nan_mask, price_cloud_upper_gc_after] = np.nan
            df_resampled.loc[nan_mask, price_cloud_lower_dc_after] = np.nan
            df_resampled.loc[nan_mask, price_cloud_lower_gc_after] = np.nan

            # 最初にゴールデンクロス/デッドクロスが発生した行以前の値を-1で埋める(ただしNanはNanのまま)
            first_price_cloud_upper_dc_index = df_resampled[df_resampled[price_cloud_upper_dc] == 1].index.min()
            first_price_cloud_upper_gc_index = df_resampled[df_resampled[price_cloud_upper_gc] == 1].index.min()
            first_price_cloud_lower_dc_index = df_resampled[df_resampled[price_cloud_lower_dc] == 1].index.min()
            first_price_cloud_lower_gc_index = df_resampled[df_resampled[price_cloud_lower_gc] == 1].index.min()

            if pd.notna(first_price_cloud_upper_dc_index):
                df_resampled.loc[:first_price_cloud_upper_dc_index - 1, price_cloud_upper_dc_after] = df_resampled.loc[:first_price_cloud_upper_dc_index - 1, price_cloud_upper_dc_after].where(nan_mask, -1)
            if pd.notna(first_price_cloud_upper_gc_index):
                df_resampled.loc[:first_price_cloud_upper_gc_index - 1, price_cloud_upper_gc_after] = df_resampled.loc[:first_price_cloud_upper_gc_index - 1, price_cloud_upper_gc_after].where(nan_mask, -1)
            if pd.notna(first_price_cloud_lower_dc_index):
                df_resampled.loc[:first_price_cloud_lower_dc_index - 1, price_cloud_lower_dc_after] = df_resampled.loc[:first_price_cloud_lower_dc_index - 1, price_cloud_lower_dc_after].where(nan_mask, -1)
            if pd.notna(first_price_cloud_lower_gc_index):
                df_resampled.loc[:first_price_cloud_lower_gc_index - 1, price_cloud_lower_gc_after] = df_resampled.loc[:first_price_cloud_lower_gc_index - 1, price_cloud_lower_gc_after].where(nan_mask, -1)

            # 先頭の要素を-9999999で埋める
            ##df_resampled.iloc[0, df_resampled.columns.get_indexer(add_columns)] = -9999999

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column] = df[column].ffill()

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
            ##df_resampled[change_flag] = df_resampled[change_rate].apply(lambda x: -999 if pd.isna(x) else (0 if x == 0 else (1 if x > 0 else -1)))
            df_resampled[change_flag] = df_resampled[change_rate].apply(lambda x: None if pd.isna(x) else (0 if x == 0 else (1 if x > 0 else -1)))

            # データの末尾周囲の計算できない要素は-999で埋める
            ##for column in add_columns:
            ##    df_resampled[column].fillna(-999, inplace=True)

            # 元のデータに計算で追加したデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # 計算(リサンプリング)対象外の行は直前の値で埋める
            for column in add_columns:
                df[column] = df[column].ffill()

        except Exception as e:
            self.log.error(f'計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df