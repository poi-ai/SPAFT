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

    def main(self):
        '''メイン処理'''
        result = self.service.past_record.main(self.target_stock_code_list, self.target_days, self.output_csv_dir)

        # 記録管理用CSVから古いデータを削除する
        result = self.service.past_record.delete_old_data()

if __name__ == '__main__':
    oo = PastOhlc()
    oo.main()
