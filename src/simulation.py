import simulation_config as config
import json
import time
from base import Base

class Simulation(Base):
    '''DBに保存されている板情報からトレードのシミュレーションを行う'''
    def __init__(self):
        # 初期設定
        super().__init__(use_api = False)

        # 設定ファイルのパラメータチェック
        result = self.service.simulation.param_check(config)
        if result == False:
            exit()

    def main(self):
        # DBから対象のレコードを取得
        result, board_info = self.service.simulation.select_boards(config.STOCK_CODE, config.TARGET_DATE, config.START_TIME, config.END_TIME)
        if result == False:
            return

        # 1レコードずつ進めながらシミュレーションを行う
        for board in board_info:
            # TODO 今なにも持っていない判定チェック
            pass



if __name__ == '__main__':
    s = Simulation()
    s.main()