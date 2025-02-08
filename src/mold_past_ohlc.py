import os
from base import Base

class MoldPastOhlc(Base):
    '''四本値データを持つCSVファイルを成形する'''
    def __init__(self):
        super().__init__(use_db = False, use_api = False)
        self.output_csv_dir = os.path.join(os.path.dirname(__file__), '..',  'csv', 'past_ohlc')
        self.logic = self.service.mold_past_record

    def main(self):
        '''メイン処理'''

        # ディレクトリ名の設定
        self.logic.set_csv_dir_name(self.output_csv_dir)

        self.log.info('成形対象のCSVファイル名の取得開始')
        csv_name_list, tmp_csv_name_list = self.logic.get_target_csv_name_list()
        self.log.info('成形対象のCSVファイル名を取得終了')

        self.log.info('四本値データからの正解フラグ/テクニカル指標追加処理開始')
        for csv_name in csv_name_list:
            self.log.info(f'対象CSVファイル名: {csv_name}')
            self.logic.main(csv_name, 0)
        self.log.info('四本値データからの正解フラグ/テクニカル指標追加処理終了')

        self.log.info('四本値データからのテクニカル指標追加処理開始')
        for csv_name in tmp_csv_name_list:
            self.log.info(f'対象CSVファイル名: {csv_name}')
            self.logic.main(csv_name, 1)
        self.log.info('四本値データからのテクニカル指標追加処理終了終了')

if __name__ == '__main__':
    mpo = MoldPastOhlc()
    mpo.main()
