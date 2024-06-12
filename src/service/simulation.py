import json
import time
from service_base import ServiceBase

class Simulation(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

    def param_check(self, config):
        '''シミュレーション設定ファイルで設定したファイルのパラメータチェック'''
        # TODO あとで
        return True

    def select_boards(self, stock_code, target_date, start_time = '09:00', end_time = '15:00'):
        '''
        引数で指定した期間/証券コードの板情報を取得する

        Args:
            stock_code(str): 証券コード
            target_date(str, yyyy-mm-dd): シミュレーション対象日
            start_time(str, HH:MM): シミュレーション対象の開始時間
            end_time(str, HH:MM): シミュレーション対象の終了時間

        '''
        start = f'{target_date} {start_time}'
        end = f'{target_date} {end_time}'
        result, board_info = self.db.board.select_specify_of_time(stock_code, start, end)
        if result == False:
            self.log.error(f'設定した期間内の板情報取得に失敗\n{"\n".join(board_info)}')
            return False, None

        # 取得できたレコードが0件
        if len(board_info) == 0:
            self.log.info('シミュレート対象のレコード数が0件のため確認できません')
            return False

        self.log.info(f'シミュレートレコード件数: {len(board_info)}件')
        return True, board_info
