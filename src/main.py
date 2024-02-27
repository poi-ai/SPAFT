import json
import sys
from kabusapi import KabusApi

class Main():
    def __init__(self):
        self.api = KabusApi('production', production = True)

    def main(self):
        # 優待売却用に一時的に作成
        if len(sys.argv) == 3:
            self.api.order.yutai_settlement(sys.argv[1], sys.argv[2])
        elif len(sys.argv) == 2:
            self.api.order.yutai_settlement(sys.argv[1])

        exit()


        # 余力取得(動かん)
        #print(self.api.wallet.margin())

        # プレ料取得
        premium_price_info = self.api.info.premium_price(1570)
        print(self.tidy_response(premium_price_info))

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
            stock_code = 1570,
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

if __name__ == '__main__':
    m = Main()
    m.main()