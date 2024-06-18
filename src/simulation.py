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

        # 日付
        for target_date in config.TARGET_DATE:
            # DBから対象日のレコードを取得
            result, board_info = self.logic.select_boards(config.STOCK_CODE, target_date, config.START_TIME, config.END_TIME)
            if result == False:
                continue

            # 現在価格の何pips下に買い注文を入れるか
            for order_line in config.REORDER_LINE:
                # 購入価格の何pips上で利確するか
                for securing_benefit_border in config.SECURING_BENEFIT_BORDER:
                    # 購入価格の何pip下で損切りするか
                    for loss_cut_border in config.LOSS_CUT_BORDER:

                        # 設定情報を管理
                        setting_info = {
                            'order_line': order_line,                  # 現在価格の何pips下に買い注文を入れるか
                            'benefit_border': securing_benefit_border, # 購入価格の何pips上で利確するか
                            'loss_cut_border': loss_cut_border,        # 購入価格の何pip下で損切りするか
                            'buy_power': config.BUY_POWER,             # 余力
                            'price_range': config.PRICE_RANGE,         # 呼値
                            'unit_num': config.UNIT_NUM                # 売買単位
                        }

                        # 取引情報を管理
                        trade_info = {
                            'securing_benefit_num': 0, # 利確回数
                            'loss_cut_num': 0 # ロスカット回数
                        }

                        # 注文情報を管理
                        order_list = []

                        # 1レコードずつ進めながらシミュレーションを行う
                        for board in board_info:
                            now_price = board['price']
                            # 注文がない場合
                            if len(order_list) == 0:
                                # 買い注文
                                order_info, setting_info['buy_power'] = self.logic.buy_order(setting_info, now_price)
                                if order_info == False:
                                    continue
                                # 注文リストに追加
                                order_list.append(order_info)

                            else:
                                # 約定チェック
                                order_list, setting_info['buy_power'], trade_info = self.logic.traded_check(order_list, now_price, setting_info, trade_info)

                                # 損切りチェック
                                order_list, setting_info['buy_power'], trade_info = self.logic.loss_cut_check(order_list, board, setting_info, trade_info)

                                # 買い注文しなおしチェック
                                order_list, setting_info['buy_power'] = self.logic.reorder_buy_check(order_list, now_price, setting_info)

                        # 大引けで利確/損切り
                        order_list, setting_info['buy_power'], trade_info = self.logic.last_settlement(order_list, setting_info, board_info[-1], trade_info)

                        ##### 結果出力 いずれちゃんと
                        print(f'銘柄コード: {config.STOCK_CODE}、シミュレーション日: {target_date} {config.START_TIME}~{config.END_TIME}、買い注文位置: {setting_info["order_line"]}pip↓、利確ライン: {setting_info["benefit_border"]}pip↑、損切りライン: {setting_info["loss_cut_border"]}pip↓、収支: {setting_info["buy_power"] - config.BUY_POWER}円、利確回数: {trade_info["securing_benefit_num"]}、損切り回数: {trade_info["loss_cut_num"]}')
                        #### Excel貼り付け用
                        #print(f'{setting_info["order_line"]}pip↓ {setting_info["benefit_border"]}pip↑ {setting_info["loss_cut_border"]}pip↓ {setting_info["buy_power"] + valuation - config.BUY_POWER} {trade_info["securing_benefit_num"]} {trade_info["loss_cut_num"]}')

        self.log.info('スキャルピングシミュレーション処理終了')



if __name__ == '__main__':
    s = Simulation()
    s.main()