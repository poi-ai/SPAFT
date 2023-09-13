import config
import json
import math
from kabusapi import KabusApi
from db_operate import Db_Operate
from base import Base

class Main(Base):
    def __init__(self):
        self.api = KabusApi(api_password = 'production', production = True)
        self.db = Db_Operate()
        result = self.init_main()
        if not result: exit()

    def init_main(self):
        '''主処理の前に動かしておくべき処理'''

        # APIから余力取得(TODO 動かん)
        #response = self.api.wallet.cash()
        #if response == False:
        #    return False

        # TODO テスト用処理
        response = {
            'StockAccountWallet': 300000.0,
            'AuKCStockAccountWallet': 300000.0,
            'AuJbnStockAccountWallet': 0
        }
        # テスト用処理ここまで

        # 余力データから抽出し、DBのフォーマットに成形
        buying_power = int(response['StockAccountWallet'])
        bp_data = {
            'total_assets': buying_power,
            'total_marin': 0,
            'api_flag': '1'
        }

        # 余力情報をテーブルに追加
        result = self.db.insert_buying_power(bp_data)
        if not result:
            return False

        # 保証金が30万を下回っていたら取引できないので終了
        if buying_power <= 300000:
            self.logger.info('保証金額が30万円未満のため取引を行いません')
            return False

    def main(self):
        '''スキャルピングを行うためのメイン処理'''
        while True:
            # 1分以内のエラー発生回数を取得
            result = self.db.select_errors_minite()
            if result == False:
                exit() # TODO 強制成決済処理を呼び出す
            if result >= 5:
                self.error_output('スキャルピング処理で1分以内に5回以上のエラーが発生したため強制成行決済を行います')
                exit() # TODO 強制成決済処理を呼び出す

            # DBから未約定データ取得
            yet_data_list = self.db.select_orders(yet = True)
            if yet_data_list == False:
                self.db.insert_errors('未約定データDB取得処理')
                continue

            # 未約定データがあればAPIで情報を取得
            for yet_data in yet_data_list:
                # APIから約定情報取得
                order_data = self.api.info.orders(id = yet_data['order_id'])
                if order_data == False:
                    self.db.insert_errors('未約定データAPI取得処理')
                    continue

                # 注文ステータスが完了になっている場合
                if order_data['State'] == 5:
                    pass # TODO



            # 板情報取得
            board_info = self.api.info.board(1570, 1)
            board_info = json.loads(board_info)

            # 現在値と最低価格売り注文・最高価格買い注文を取得する
            over_price = board_info["Sell1"]["Price"]
            now_price = board_info["CurrentPrice"]
            under_price = board_info["Buy1"]["Price"]

            '''
            # 1570をunder_priceで買い注文
            result = self.api.order.stock(
                stock_code = 1570,
                password = 'p@ssword',
                exchange = 1,
                side = 2,
                cash_margin = 2,
                deliv_type = 0,
                account_type = 4,
                qty = 1,
                front_order_type = 20,
                price = under_price,
                margin_trade_type = 3,
                expire_day = 0,
                fund_type = '11'
            )
            '''
            # 保有中証券のIDを取得
            #now_position = self.api.info.orders()

            #print(now_position)

            #exit()
            # 1570を売り注文 (動作確認済)
            result = self.api.order.stock(
                stock_code = config.STOCK_CODE,
                password = 'p@ssword',
                exchange = 1,
                side = 1,
                cash_margin = 3,
                deliv_type = 2,
                account_type = 4,
                qty = 1,
                close_position_order = 6,
                front_order_type = 20,
                price = 19585,
                margin_trade_type = 3,
                expire_day = 0,
                fund_type = '11'
            )

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = json.loads(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response

    def get_interest(self, price):
        '''
        1約定の代金からカブコムのデイトレ金利を計算する

        Args:
            price(int): 約定代金

        Returns:
            interest(int): 金利

        '''
        # ワンショット100万以上は金利0%
        if price >= 1000000: return 0

        # 代金(円) x (年率)1.8% ÷ 365(日)、1円以下は切り捨て
        return math.floor(price * 0.018 / 365)


if __name__ == '__main__':
    m = Main()
    print(m.get_interest(999999))