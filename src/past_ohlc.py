import config
import os
from base import Base

class PastOhlc(Base):
    '''米Yahoo!Financeから過去の四本値を取得し、CSVに出力する'''
    def __init__(self):
        super().__init__(use_db = False, use_api = False)

        # 対象の銘柄コード一覧/遡る日数/CSV出力ディレクトリ
        self.target_stock_code_list = config.RECORD_OHLC_STOCK_CODE_LIST
        self.target_days = config.RECORD_OHLC_DAYS
        self.output_csv_dir = os.path.join(os.path.dirname(__file__), '..',  'csv', 'past_ohlc')
        self.logic = self.service.past_record

    def main(self):
        '''メイン処理'''

        self.log.info('米Yahoo!Financeからの四本値取得処理開始')
        _ = self.logic.main(self.target_stock_code_list, self.target_days, self.output_csv_dir)
        self.log.info('米Yahoo!Financeからの四本値取得処理終了')

        self.log.info('記録管理用CSVから古いデータの削除処理開始')
        _ = self.logic.delete_old_data()
        self.log.info('記録管理用CSVから古いデータの削除処理終了')

        self.log.info('古い四本値データの圧縮処理開始')
        _ = self.logic.compress_old_data(self.output_csv_dir)
        self.log.info('古い四本値データの圧縮処理終了')

if __name__ == '__main__':
    oo = PastOhlc()
    oo.main()
