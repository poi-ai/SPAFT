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
        self.buy_order_dict = {}
        self.sell_order_dict = {}
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
        # TODO テスト用処理ここまで

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
            yet_info_list = self.db.select_orders(yet = True)
            if yet_info_list == False:
                self.db.insert_errors('未約定データDB取得処理')
                continue

            # 未約定データがあればAPIで情報を取得
            for yet_info in yet_info_list:
                # APIから約定情報取得
                order_info = self.api.info.orders(id = yet_info['order_id'])
                if order_info == False:
                    self.db.insert_errors('未約定データAPI取得処理')
                    continue

                # 注文ステータスが完了になっている場合
                if order_info['State'] == 5:
                    order_id = order_info['ID']

                    if order_id in self.buy_order_dict:
                        del self.buy_order_dict[order_id]
                        if order_id in self.sell_order_dict:
                            del self.sell_order_dict[order_id]
                        else:
                            self.logger.warning(f'インスタンス変数に一致する注文IDが見つかりませんでした order_id {order_id}')

                    # DB更新
                    result = self.db.update_orders_status(order_id = order_info['ID'], status = 2)
                    if result == False:
                        self.db.insert_errors('注文ステータスDB更新処理')
                        continue

                    # 約定したのが新規注文なら1枚上に決済注文を入れる
                    if order_info['CashMargin'] == 2:
                        # TODO データ成形用処理
                        reverse_order_info = {
                        }
                        result = self.api.order.stock(reverse_order_info)
                        if not result:
                            self.db.insert_errors('反対注文発注API処理')
                            continue

                        # リカバリ用でインスタンス変数に注文をIDを持たせとく
                        self.sell_order_dict.append(result['OrderId'])

                        # TODO 注文情報をDBに追加する

            # 板情報を取得する
            board_info = self.api.info.board(stock_code = config.STOCK_CODE)
            if board_info == False:
                self.db.insert_errors('板情報取得処理')
                continue

            board_info = json.loads(board_info)

            # TODO 学習用データテーブル用のフォーマットに整形

            # 板情報を学習用テーブルに追加
            result = self.db.insert_boards()
            if result == False:
                self.db.insert_errors('板情報DB記録処理')

            # 買い対象の板5枚分の価格を取得する
            buy_target_price = self.culc_buy_target_price(result)


            # 現在値と最低売り注文価格・最高買い注文価格を取得する
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

    def culc_buy_target_price(self, board_info):
        '''
        注文を入れる対象の5枚分の価格を取得する

        Args:
            board_info(dict): APIから取得した板情報

        Returns:
            target_price_list(list): 買いの対象となる5枚分の価格

        '''
        # 買い板の注文価格が高い順に5枚分チェックをする
        buy_price_list = [board_info[f'Buy{index}']["Price"] for index in range(1, 6)]

        # 間の価格を抜けるのを防ぐため最小の価格差を取得する
        min_diff = min([buy_price_list[i] - buy_price_list[i + 1] for i in range(len(buy_price_list) - 1)])

        # 売り注文-1pipから注文を入れるか、買い注文のある最高値から注文を入れるか
        if config.AMONG_PRICE_ORDER == True:
            # 売り注文と買い注文間の注文のない価格を取得
            return [price for price in range()]
        else:
            return []


if __name__ == '__main__':
    m = Main()
    print(m.get_interest(999999))