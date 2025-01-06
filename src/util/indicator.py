import numpy as np
import pandas as pd
import traceback

class Indicator():
    def __init__(self, log):
        self.log = log

    def get_sma(self, df, column_name, window_size, interval):
        '''
        単純移動平均線(SMA)を計算してカラムに追加する

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
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # SMAの計算・カラムを追加
            df_resampled[column_name] = df_resampled['current_price'].rolling(window=window_size).mean().round(1)

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

    def get_ema(self, df, column_name, window_size, interval):
        '''
        指数移動平均線(EMA)を計算してカラムに追加する

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
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # EMAの計算・カラムを追加
            df_resampled[column_name] = df_resampled['current_price'].ewm(span = window_size).mean().round(1)

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
        加重移動平均線(WMA)を計算してカラムに追加する

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
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # WMAの計算・カラムを追加
            weights = np.arange(1, window_size + 1)
            df_resampled[column_name] = df_resampled['current_price'].rolling(window = window_size).apply(lambda x: np.dot(x, weights) / weights.sum(), raw = True).round(1)

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

    def get_bollinger_bands(self, df, column_name, window_size, interval):
        '''
        ボリンジャーバンドを計算してカラムに追加する

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
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

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

                # window_size - 1番目までのデータでは計算ができずNaNになるので-1で埋める
                df[f'{column_name}_upper_{sigma}_alpha'].fillna(-1, inplace=True)
                df[f'{column_name}_lower_{sigma}_alpha'].fillna(-1, inplace=True)

        except Exception as e:
            self.log.error(f'ボリンジャーバンド計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_rsi(self, df, column_name,  window_size, interval):
        '''
        相対力指数(RSI)を計算してカラムに追加する

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
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): RCIを設定するカラム名
            window_size(int): RCIを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): RCIを追加したDataFrame
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
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): MACDを設定するカラム名
            short_window_size(int): 短期EMAのウィンドウ幅
            long_window_size(int): 長期EMAのウィンドウ幅
            signal_window_size(int): シグナル線のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): MACDを追加したDataFrame

        '''
        try:
            # 何分足の設定かに応じてデータをリサンプリング
            if interval > 1:
                df_resampled = df[['current_price']].iloc[::interval, :].copy()
            else:
                df_resampled = df[['current_price']].copy()

            # カラム名の設定
            column_signal_name = f'{column_name}_signal'
            column_diff_name = f'{column_name}_diff'
            add_columns = [column_name, column_signal_name, column_diff_name]

            # MACD(短期EMA - 長期EMA)の計算
            short_ema = df_resampled['current_price'].ewm(span = short_window_size).mean()
            long_ema = df_resampled['current_price'].ewm(span = long_window_size).mean()
            df_resampled[column_name] = (short_ema - long_ema).round(2)

            # MACDシグナルの計算
            df_resampled[column_signal_name] = df_resampled[column_name].ewm(span = signal_window_size).mean().round(2)

            # MACDとMACDシグナルの差を計算
            df_resampled[column_diff_name] = df_resampled[column_name] - df_resampled[column_signal_name]

            # 先頭の要素を-999で埋める
            df_resampled.iloc[0, df_resampled.columns.get_indexer([column_name, column_signal_name, column_diff_name])] = -999

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
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): PSYを設定するカラム名
            window_size(int): PSYを計算する際のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): PSYを追加したDataFrame

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
            df(DataFrame): 板情報のデータ
                ※current_priceカラムが存在かつデータが時系列で連続していること
            column_name(str): SARを設定するカラム名
            min_af(float): 加速因数の初期値(最小値)
            max_af(float): 加速因数の最大値
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): SARを追加したDataFrame

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

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[column_name], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            df[column_name].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'SAR計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df

    def get_ichimoku_cloud(self, df, column_name, short_window_size, long_window_size, interval):
        '''
        一目均衡表を計算してカラムに追加する

        Args:
            df(DataFrame): 板情報のデータ
                ※current_priceカラムかhigh&lowカラムが存在かつデータが時系列で連続していること
            column_name(str): 一目均衡表を設定するカラム名
            short_window_size(int): 短期のウィンドウ幅
            long_window_size(int): 長期のウィンドウ幅
            interval(int): 何分足として計算するか

        Returns:
            bool: 実行結果
            df(DataFrame): 一目均衡表を追加したDataFrame

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
            add_columns = [base_line, conversion_line, leading_span_a, leading_span_b, lagging_span]

            # 終値ベースのデータしかない場合
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

            # 先頭の要素を-1で埋める
            df_resampled.iloc[0, df_resampled.columns.get_indexer(add_columns)] = -1

            # 元のデータフレームにリサンプリングされたデータをマージ
            df = df.merge(df_resampled[add_columns], left_index=True, right_index=True, how='left')

            # リサンプリングされていない行を直前の値で埋める
            for column in add_columns:
                df[column].fillna(method='ffill', inplace=True)

        except Exception as e:
            self.log.error(f'一目均衡表計算でエラー\n{str(e)}\n{traceback.format_exc()}')
            return False, None

        return True, df