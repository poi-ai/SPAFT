import os
import traceback
import pandas as pd
from service_base import ServiceBase


class OhlcExport(ServiceBase):
    '''大引け後にohlcテーブルのデータをCSVに出力し、リサンプリング・7z圧縮・DB削除を行うクラス'''

    def __init__(self, api_headers, api_url, ws_url, conn):
        super().__init__(api_headers, api_url, ws_url, conn)

    def export(self, symbol_list, target_date):
        '''
        大引け後バッチ処理のメイン処理
        ohlcテーブルから1分足を取得し、CSVに出力した後3分・5分足にリサンプリングする。
        全銘柄の出力が完了したら7z圧縮し、圧縮成功時にDBのレコードを削除する。

        Args:
            symbol_list(list): 処理対象の銘柄コードリスト
            target_date(str): 処理対象日 'YYYYMMDD'

        Returns:
            result(bool): 実行結果
        '''
        self.log.info(f'大引け後OHLCエクスポート処理開始 対象日: {target_date} 銘柄数: {len(symbol_list)}')

        output_dir = os.path.join('..', 'csv', 'ohlc')

        # 銘柄ごとにCSV出力（1分足・3分足・5分足）
        for symbol in symbol_list:
            result = self._export_symbol(symbol, target_date, output_dir)
            if result == False:
                self.log.error(f'銘柄のCSV出力処理でエラーが発生したため処理を中断します 銘柄コード: {symbol}')
                return False

        # 全銘柄のCSVを7z圧縮
        bak_dir = os.path.join(output_dir, 'bak')
        output_7z = os.path.join(bak_dir, f'{target_date}.7z')
        self.log.info(f'7z圧縮処理開始 出力先: {output_7z}')
        result, error = self.util.file_manager.compress_csv_files(output_dir, output_7z)
        if result == False:
            self.log.error(f'7z圧縮処理でエラーが発生したためDB削除をスキップします\n{error}')
            return False
        self.log.info('7z圧縮処理終了')

        # 圧縮成功後にohlcテーブルの当日レコードを削除
        self.log.info(f'ohlcテーブル削除処理開始 対象日: {target_date}')
        result, row_count = self.db.ohlc.delete_by_date(target_date)
        if result == False:
            self.log.error('ohlcテーブル削除処理でエラーが発生しました')
            return False
        self.log.info(f'ohlcテーブル削除処理終了 削除件数: {row_count}')

        self.log.info(f'大引け後OHLCエクスポート処理終了 対象日: {target_date}')
        return True

    def _export_symbol(self, symbol, target_date, output_dir):
        '''
        指定銘柄のohlcレコードをDBから取得し、1分・3分・5分足のCSVを出力する

        Args:
            symbol(str): 銘柄コード
            target_date(str): 処理対象日 'YYYYMMDD'
            output_dir(str): CSV出力先ディレクトリ

        Returns:
            result(bool): 実行結果
        '''
        self.log.info(f'銘柄OHLCエクスポート処理開始 銘柄コード: {symbol}')

        # DBから1分足レコードを取得
        result, rows = self.db.ohlc.select_by_date(symbol, target_date)
        if result == False:
            self.log.error(f'ohlcレコード取得処理でエラー 銘柄コード: {symbol}')
            return False
        if len(rows) == 0:
            self.log.warning(f'ohlcレコードが存在しません 銘柄コード: {symbol} 対象日: {target_date}')
            return True

        # DataFrameに変換
        df = pd.DataFrame(rows)
        df['trade_time'] = pd.to_datetime(df['trade_time'])
        df = df.sort_values('trade_time').reset_index(drop=True)

        # 1分足CSVを出力
        path_1min = os.path.join(output_dir, f'{target_date}_{symbol}_1min.csv')
        result = self._write_csv(df, path_1min)
        if result == False:
            return False

        # 3分足CSVを出力
        df_3min = self._resample(df, '3min')
        if df_3min is None:
            return False
        path_3min = os.path.join(output_dir, f'{target_date}_{symbol}_3min.csv')
        result = self._write_csv(df_3min, path_3min)
        if result == False:
            return False

        # 5分足CSVを出力
        df_5min = self._resample(df, '5min')
        if df_5min is None:
            return False
        path_5min = os.path.join(output_dir, f'{target_date}_{symbol}_5min.csv')
        result = self._write_csv(df_5min, path_5min)
        if result == False:
            return False

        self.log.info(f'銘柄OHLCエクスポート処理終了 銘柄コード: {symbol} レコード数: {len(df)}')
        return True

    def _resample(self, df, freq):
        '''
        DataFrameを指定した時間足にリサンプリングする

        Args:
            df(pd.DataFrame): 1分足データ（trade_timeカラムがdatetime型）
            freq(str): リサンプリング間隔（例: '3min', '5min'）

        Returns:
            resampled(pd.DataFrame) or None: リサンプリング後のDataFrame
        '''
        try:
            df_indexed = df.set_index('trade_time')
            resampled = df_indexed.resample(freq).agg({
                'open_price':   'first',
                'high_price':   'max',
                'low_price':    'min',
                'close_price':  'last',
                'volume':       'sum',
                'total_volume': 'last',
                'status':       'last'
            }).dropna(subset=['open_price'])
            resampled = resampled.reset_index()
            return resampled
        except Exception as e:
            self.log.error(f'OHLCリサンプリング処理でエラー freq: {freq}\n{e}\n{traceback.format_exc()}')
            return None

    def _write_csv(self, df, file_path):
        '''
        DataFrameをCSVに出力する

        Args:
            df(pd.DataFrame): 出力対象のDataFrame
            file_path(str): 出力先のファイルパス

        Returns:
            result(bool): 実行結果
        '''
        try:
            df.to_csv(file_path, index=False, encoding='utf-8')
            self.log.info(f'CSV出力処理完了 ファイルパス: {file_path} 件数: {len(df)}')
            return True
        except Exception as e:
            self.log.error(f'CSV出力処理でエラー ファイルパス: {file_path}\n{e}\n{traceback.format_exc()}')
            return False
