import simulation_config as config
import json
import time
from base import Base

class Simulation(Base):
    '''DBに保存されている板情報からトレードのシミュレーションを行う'''
    def __init__(self):
        # 初期設定
        super().__init__(use_api = False)

        self.logic = self.service.simulation

        # 設定ファイルのパラメータチェック
        result = self.logic.param_check(config)
        if result == False:
            exit()

    def main(self):
        self.log.info('スキャルピングシミュレーション処理開始')

        for target_date in config.TARGET_DATE:
            # 取引情報を管理
            self.trade_list = {
                'securing_benefit_num': 0, # 利確回数
                'loss_cut_num': 0 # ロスカット回数
            }
            # 注文情報を管理
            self.order_list = []
            # 余力
            self.buy_power = config.BUY_POWER

            # DBから対象のレコードを取得
            result, board_info = self.logic.select_boards(config.STOCK_CODE, target_date, config.START_TIME, config.END_TIME)
            if result == False:
                continue

            # 1レコードずつ進めながらシミュレーションを行う
            for board in board_info:
                now_price = board['price']
                # 注文がない場合
                if len(self.order_list) == 0:
                    # n枚下に買い注文
                    order_info, self.buy_power = self.logic.buy_order(self.buy_power, now_price)
                    if order_info == False:
                        continue
                    # 注文リストに追加
                    self.order_list.append(order_info)

                else:
                    # 約定チェック
                    self.order_list, self.buy_power, self.trade_list = self.logic.traded_check(self.order_list, now_price, self.buy_power, self.trade_list)

                    # 損切りチェック
                    self.order_list, self.buy_power, self.trade_list = self.logic.loss_cut_check(self.order_list, now_price, self.buy_power, board, self.trade_list)

                    # 買い注文しなおしチェック
                    self.order_list, self.buy_power = self.logic.reorder_buy_check(self.order_list, now_price, self.buy_power)

            ##### 評価額
            valuation = 0
            for order in self.order_list:
                valuation += order['sum_num'] * now_price

            print(self.buy_power + valuation)
            # 取引回数
            print(self.trade_list)
            #print(self.order_list)

        self.log.info('スキャルピングシミュレーション処理終了')



if __name__ == '__main__':
    s = Simulation()
    s.main()