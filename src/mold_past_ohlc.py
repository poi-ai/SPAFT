import os
from base import Base

class MoldPastOhlc(Base):
    '''四本値データを持つCSVファイルを成形する'''
    def __init__(self):
        super().__init__(use_db = False, use_api = False)
        self.output_csv_dir = os.path.join(os.path.dirname(__file__), '..',  'csv', 'past_ohlc')
        self.tmp_csv_dir = os.path.join(os.path.dirname(__file__), '..',  'csv', 'past_ohlc', 'tmp')
        self.logic = self.service.mold_past_record

    def main(self):
        '''メイン処理'''

        # ディレクトリ名の設定
        self.logic.set_dir_name(self.output_csv_dir, self.tmp_csv_dir)

        self.log.info('成形対象の四本値CSVファイル名の取得開始')
        result = self.logic.get_target_csv_name_list()
        if result == False:
            self.log.error('成形対象の四本値CSVファイル名の取得に失敗しました')
            return
        self.log.info('成形対象の四本値CSVファイル名の取得終了')

        self.log.info('目的変数追加処理開始')
        result = self.logic.create_dv()
        if result == False:
            self.log.error('目的変数追加処理に失敗しました')
            return
        self.log.info('目的変数追加処理終了')

        self.log.info('成形対象の目的変数追加済CSVファイル名の取得開始')
        result = self.logic.get_tmp_target_csv_name_list()
        if result == False:
            self.log.error('成形対象の目的変数追加済CSVファイル名の取得に失敗しました')
            return
        self.log.info('成形対象の目的変数追加済CSVファイル名の取得終了')

        self.log.info('説明変数追加処理開始')
        result = self.logic.create_iv()
        if result == False:
            self.log.error('説明変数追加処理に失敗しました')
            return
        self.log.info('説明変数追加処理終了')

if __name__ == '__main__':
    mpo = MoldPastOhlc()
    mpo.main()
