import os
import pandas as pd
import re
from service_base import ServiceBase

class BoardMold(ServiceBase):
    '''板情報CSVを成形する'''
    def __init__(self):
        # 親クラスのinitを実行
        super().__init__(api_headers = False, api_url = False, conn = False)

        self.target_csv = []

    def main(self):
        '''主処理'''
        # 取得対象となるCSVを取得する
        result = self.get_target_csv()
        if result == False:
            return

        # CSVのデータからパラメータを生成する
        for csv_path in self.target_csv:
            # 板情報を持つCSVファイルをDataFrame型として読み込む
            result, board_df = self.read_csv(csv_path)
            if result == False:
                continue

            # 板情報からパラメータを生成する
            result, new_board_df = self.create_param(board_df)
            if result == False:
                continue

            # CSV出力を行う
            self.write_csv(csv_path, new_board_df)

            # TODO カラムを追加したCSVをformattedディレクトリに移す

            # TODO 元のCSVファイルをbakディレクトリに移す

        # TODO 先月以前のCSVファイルを7zへ圧縮する

        return True

    def get_target_csv(self):
        '''
        取得対象のCSVを取得する

        Returns:
            bool: 処理結果
        '''
        try:
            # 一つ上の階層のcsvディレクトリのパスを取得
            csv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv')

            # csvディレクトリが存在するか確認
            if not os.path.exists(csv_dir):
                self.log.info(f'CSVディレクトリが存在しません: {csv_dir}')
                return False

            # ディレクトリ内の.csvファイルを取得
            pattern = re.compile(r'^\w+_\w+\.csv$')
            self.target_csv = [os.path.join(csv_dir, f) for f in os.listdir(csv_dir) if f.endswith('.csv') and pattern.match(f)]

            # 取得したCSVファイルのリストをログに出力
            self.log.info(f'取得対象のCSVファイル: {self.target_csv}')

            return True
        except Exception as e:
            self.log.error(f'CSVファイルの取得でエラー: {str(e)}')
            return False

    def read_csv(self, csv_path):
        '''
        CSVを読み込んでDataFrame型にする

        Args:
            csv_path(str): CSVファイルのパス

        Returns:
            result(bool): 実行結果
            board_df(pandas.DataFrame) or False: 読み込んだCSVのデータ
        '''
        try:
            board_df = pd.read_csv(csv_path)
        except Exception as e:
            self.log.error(f'CSV読み込みでエラー パス: {csv_path}\n{str(e)}')
            return None, False

        return True, board_df

    def write_csv(self, csv_path, board_df):
        '''
        DataFrame型のデータをCSVに書き込む

        Args:
            csv_path(str): データ元のCSVファイルのパス
            board_df(pandas.DataFrame): 書き込むデータ

        Returns:
            bool: 処理結果
        '''
        new_csv_path = csv_path.replace('.csv', '_new.csv')

        try:
            board_df.to_csv(new_csv_path, index = False)
        except Exception as e:
            self.log.error(f'CSV書き込みでエラー パス: {new_csv_path}\n{str(e)}')
            return False

        return True

    def create_param(self, board_df):
        '''
        板情報のリストからパラメータを生成する

        Args:
            board_df(pandas.DataFrame): 板情報のリスト

        Returns:
            result(bool): 処理結果
            new_board_list(pandas.DataFrame): パラメータを追加した板情報のリスト
        '''
        # 何分足で計算するか
        minute_list = [1, 3, 5, 10, 15, 30]

        # 直近何個のデータから算出するか
        window_size_list = [3, 5, 10, 15]
        window_size_list2 = [9, 14, 22, 26, 52]
        window_size_list3 = [10, 12, 15]
        af_list = [0.01, 0.02, 0.05, 0.1]

        # 移動平均線を研鑽してカラムとして追加する
        for minute in minute_list:
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

            for af in af_list:
                # パラボリックSARを計算・追加する
                result, board_df = self.util.indicator.get_parabolic(df = board_df,
                                                                     column_name = f'sar_{minute}min_{af}af',
                                                                     af = af,
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

if __name__ == '__main__':
    bm = BoardMold()
    bm.main()