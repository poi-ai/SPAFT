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
        self.buy_order_list = []
        self.sell_order_list = []
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
            self.logger.info('保証金が30万円未満のため取引を行いません')
            return False

        # 銘柄情報を取得
        stock_info = self.api.info.symbol(stock_code = config.STOCK_CODE, market_code = 1)
        if stock_info == False:
            return False

        # 銘柄情報から取引に使用するデータを変数に突っ込んどく
        # 1単元株数
        self.one_unit = stock_info['TradingUnit']
        # 値幅上限(S高株価)
        self.upper_price = stock_info['UpperLimit']
        # 値幅下限(S安株価)
        self.lower_price = stock_info['LowerLimit']
        # 基準から値幅の8割減株価(取引中止ライン)
        self.stop_price = self.lower_price + (self.upper_price - self.lower_price) / 10

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

                    before_len = len(self.buy_order_list) + len(self.sell_order_list)

                    self.buy_order_list = list(filter(lambda buy_order: buy_order['order_id'] != order_id, self.buy_order_list))
                    self.sell_order_list = list(filter(lambda sell_order: sell_order['order_id'] != order_id, self.sell_order_list))

                    if before_len == len(self.buy_order_list) + len(self.sell_order_list):
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
                        self.sell_order_list.append({
                            'order_id': result['OrderId'],
                            'price': yet_info['order_price'], # TODO 組み立てたら
                            'qty': yet_info['order_volume'] # TODO 組み立てたら
                        })

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

            # 現在価格が値幅の8割を下回っていたら強制取引終了
            if result['CurrentPrice'] <= self.stop_price:
                exit() # TODO 強制成決済処理を呼び出す

            # 買い対象の板5枚分の価格を取得する
            buy_target_price = self.culc_buy_target_price(result)

            # 未約定の買い注文があるか確認
            for target_price in buy_target_price:
                order_info = self.db.select_orders(yet = True, order_price = target_price)
                if result == False:
                    self.db.insert_errors('価格指定注文DB取得処理')
                    continue

                # 注文が入っていなければ入れる
                if len(order_info) == 0:
                    # 余力チェック
                    bp = self.db.select_buying_power()
                    if bp == False:
                        self.db.insert_errors('余力情報DB取得処理')
                        continue

                    # 購入後が保証金の2.5倍に収まるなら買う
                    if bp['total_asset'] * 2.5 > bp['total_margin'] + target_price * self.one_unit:

                        # TODO 注文フォーマット作成

                        # APIで発注
                        result = self.api.order.stock()
                        if result == False:
                            self.db.insert_errors('買い注文API')
                            continue

                        # リカバリ用変数に突っ込む
                        self.buy_order_list.append({
                            'order_id': result['OrderId'],
                            'price': 1, # TODO 組み立てたら
                            'qty': 1 # TODO 組み立てたら
                        })

                        # TODO 注文テーブルに突っ込む

                        # TODO 余力テーブルにレコード追加
                        latest_bp = {
                            'total_assets': bp['total_assets'],
                            'total_margin': bp['total_margin'] + target_price * self.one_unit,
                            'api_flag': '0'
                        }






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

    def get_interest(self, price):
        '''
        1約定の代金からカブコムのデイトレ金利を計算する

        Args:
            price(int): 約定代金

        Returns:
            interest(int): 1日にかかる金利額

        '''
        # ワンシト100万以上は金利0%
        if price >= 1000000: return 0

        # 代金(円) x (年率)1.8% ÷ 365(日)、1円以下は切り捨て
        return math.floor(price * 0.018 / 365)

    def culc_buy_target_price(self, board_info):
        '''
        注文を入れる対象の5枚分の価格を取得する
        1pipの値幅が変わる(TOPIX MID400構成銘柄が1000円をまたぐ)場合は不整合が起こるので注意

        Args:
            board_info(dict): APIから取得した板情報

        Returns:
            target_price_list(list): 買いの対象となる5枚分の価格

        '''
        # 買い板の注文価格が高い順に5枚分チェックをする
        buy_price_list = [board_info[f'Buy{index}']["Price"] for index in range(1, 6)]

        # 間の価格を抜けるのを防ぐため最小の価格差を取得する
        min_diff = min([buy_price_list[i] - buy_price_list[i + 1] for i in range(len(buy_price_list) - 1)])

        # 売り注文-1pipから注文を入れるか(T)、買い注文のある最高値から注文を入れるか(F)
        if config.AMONG_PRICE_ORDER == True:
            price_list = [board_info['Sell1']['Price'] - pip * min_diff for pip in range(1, 6)]
        else:
            price_list = [board_info['Buy1']['Price'] - pip * min_diff for pip in range(5)]

        # S安未満のものは弾いて返す
        return [price for price in price_list if price >= self.lower_price]


if __name__ == '__main__':
    m = Main()
    print(m.get_interest(999999))