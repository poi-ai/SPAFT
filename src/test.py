import config
import math
import time
import traceback
from base import Base
from datetime import datetime, timedelta
from db_operate import Db_Operate
from kabusapi import KabusApi
from mold import Mold

class Main(Base):
    def __init__(self):
        self.api = KabusApi(api_password = 'production', production = True)
        self.db = Db_Operate()
        self.mold = Mold()
        self.order_list = []
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

        # 銘柄情報を取得 TODO 50銘柄ルールに引っ掛かるか確認
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
                # 1分待って再取得
                time.sleep(1)
                result = self.db.select_errors_minite(2)
                # それでもエラーなら強制決済
                if result == False:
                    self.enforce_liquidation()

            # 1分に5回以上のエラーで強制成行決済
            if result >= 5:
                self.error_output('スキャルピング処理で1分以内に5回以上のエラーが発生したため強制成行決済を行います')
                self.enforce_liquidation()

            # DBから未約定データ取得
            yet_order_list = self.db.select_orders(yet = True)
            if yet_order_list == False:
                self.db.insert_errors('未約定データDB取得処理')
                continue # TODO ここでcontinueしても意味ない

            # DBからAPIの最終呼び出し時間を取得
            api_process_info = self.db.select_api_process(name = 'order_info')
            if api_process_info:
                self.db.insert_errors('約定データAPI取得処理')
                continue # TODO ここでcontinueしても意味ない

            # 最終呼び出し時間のデータ存在チェック
            if len(api_process_info) == 0:
                # レコードがない場合は今日の8時59分に設定
                today = datetime.now()
                latest_exec_time = datetime(today.year, today.month, today.day, 8, 59).strftime("%Y%m%d%H%M%S")
            else:
                # 最新の実行時間を取り出し10秒前に設定
                latest_exec_time = api_process_info[0]['api_exex_time'] - timedelta(seconds = 10)
                latest_exec_time = latest_exec_time.strftime('%Y%m%d%H%M%S')

            # 検索用フォーマットに合わせる
            search_filter = {
                'uptime': latest_exec_time,
                'status': '5' # 決済状態: 終了（発注エラー・取消済・全約定・失効・期限切れ）
            }

            # APIから未取得の約定済み注文を取得
            api_order_list = self.api.info.orders(search_filter)
            if api_order_list == False:
                continue # TODO ここでcontinueしても意味ない

            # dict変換
            api_order_list = self.byte_to_dict(api_order_list)

            # APIとDBで同じ注文IDがあればDBを更新する
            for yet_order in yet_order_list:
                for api_order in api_order_list:
                    if yet_order['order_id'] == api_order['ID']:
                        order_id = yet_order['order_id']

                        # リカバリ変数から注文情報削除
                        self.delete_recovery(order_id)

                        # 注文テーブルのステータスを約定済みに更新
                        result = self.db.update_orders_status(order_id = order_info['ID'], status = 1)
                        if result == False:
                            self.db.insert_errors('注文テーブル約定ステータス更新処理')
                            continue

                        # 新規注文の場合は反対注文を入れる
                        if order_info['CashMargin'] == 2:
                            # 約定した1枚上に決済注文を入れる
                            # TODO データ成形用処理
                            reverse_order_info = {}

                            result = self.api.order.stock(reverse_order_info)
                            if not result:
                                self.db.insert_errors('反対注文発注API処理')
                                continue

                            # リカバリ変数に追加  # TODO 注文用のreverse_order_infoを組み立てたらそこから埋める
                            self.add_recovery(order_id = result['OrderId'], price = 'TODO', qty = 'TODO', order_type = 3)

                            # TODO 注文情報をDBに追加する

            # 板情報を取得する
            board_info = self.api.info.board(stock_code = config.STOCK_CODE)
            if board_info == False:
                self.db.insert_errors('板情報取得処理')
                continue

            # 銘柄登録数上限対応
            if board_info == 4002006:
                # 銘柄登録全解除
                result = self.api.regist.unregist_all()
                if result == False:
                    self.db.insert_errors('銘柄登録全解除')
                    continue

                # 再度板情報取得
                board_info = self.api.info.board(stock_code = config.STOCK_CODE, market_code = 1)
                if board_info == False:
                    self.db.insert_errors('再板情報取得処理')
                    continue

            # dict変換
            board_info = self.byte_to_dict(board_info)

            # 板情報テーブルに合わせたフォーマットに変換
            # ここの一連の処理は失敗しても注文には影響しないのでお咎めなし
            board_table_dict = self.mold.response_to_boards(board_info)
            if board_table_dict != False:
                # 板情報を学習用テーブルに追加
                self.db.insert_boards(board_table_dict)

            # S安で決済できなくなるのを防ぐため
            # 現在価格が値幅の8割を下回っていたら強制成行決済
            if board_info['CurrentPrice'] <= self.stop_price:
                self.enforce_liquidation()

            # 買い対象の板5枚分の価格を取得する
            buy_target_price = self.culc_buy_target_price(result)

            # 買い対象の5枚に未約定の注文を入れているかチェック
            for target_price in buy_target_price:
                order_info = self.db.select_orders(yet = True, order_price = target_price, new_order = True)
                if result == False:
                    self.db.insert_errors('価格指定の注文テーブル取得処理')
                    continue

                # 注文が入っていなければ入れる
                if len(order_info) == 0:
                    # 余力チェック
                    bp = self.db.select_buying_power()
                    if bp == False:
                        self.db.insert_errors('余力テーブル情報取得処理')
                        continue

                    # dict変換
                    bp = self.byte_to_dict(bp)

                    # 購入後が保証金の2.5倍に収まるなら買う
                    if bp['total_asset'] * 2.5 > bp['total_margin'] + target_price * self.one_unit:

                        # TODO 注文フォーマット作成

                        # APIで発注
                        result = self.api.order.stock()
                        if result == False:
                            self.db.insert_errors('買い注文API')
                            continue

                        # リカバリ用変数に突っ込む TODO 注文フォーマットから取得
                        self.add_recovery(order_id = result['OrderId'], order_price = 'TODO', order_qty = 'TODO', order_type = 2)

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
        # ワンショット100万以上は金利0%
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

    def add_recovery(self, order_id, order_price, order_qty, order_type):
        '''
        リカバリ変数に注文情報を追加する

        Args:
            order_id(str): 注文ID
            order_price(int): 注文価格
            order_qty(int): 注文株数
            order_type(str): 注文種別
                2: 新規、3: 返済

        Return:
            bool: 実行結果

        '''
        try:
            order_info = {
                'order_id': order_id,
                'price': order_price,
                'qty': order_qty,
                'type': order_type
            }
            self.order_list.append(order_info)
        except Exception as e:
            self.error_output(f'リカバリ変数への注文情報追加処理に失敗しました\norder_id {order_id}', e, traceback.format_exc())
            return False

        return True

    def delete_recovery(self, order_id):
        '''
        リカバリ変数から注文情報を削除する

        Args:
            order_id(str): 削除したい注文ID

        Returns:
            bool: 実行結果

        '''
        list_len = len(self.order_list)
        # リストから削除
        self.sell_order_list = list(filter(lambda sell_order: sell_order['order_id'] != order_id, self.sell_order_list))
        # リストの長さに変化がなかった(=消えていなかった)らエラーとする
        if list_len - 1 == len(self.sell_order_list):
            return True
        else:
            self.logger.error(f'リカバリ変数への注文情報削除処理に失敗しました\norder_id {order_id}')
            return False

if __name__ == '__main__':
    m = Main()
    print(m.get_interest(999999))