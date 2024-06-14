import json
import time
from service_base import ServiceBase

class Simulation(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

    def param_check(self, config):
        '''シミュレーション設定ファイルで設定したファイルのパラメータチェック'''
        self.config = config
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
            self.log.error(f'設定した期間内の板情報取得に失敗\n{board_info}')
            return False, None

        # 取得できたレコードが0件
        if len(board_info) == 0:
            self.log.info('対象のレコード数が0件のためシミュレートできません')
            return False, None

        self.log.info(f'シミュレートレコード件数: {len(board_info)}件')
        return True, board_info

    def buy_order(self, buy_power, now_price):
        '''
        新規買い注文を入れる

        Args:
            buy_power(int): 余力
            now_price(float): 現在株価

        Returns:
            order_info(dict): 注文情報
            buy_power(int): 注文後余力

        '''
        # n枚下の株価を計算
        order_price = now_price - (self.config.PRICE_RANGE * self.config.REORDER_LINE)

        # 購入額を計算
        buy_price = order_price * self.config.UNIT_NUM

        # 余力チェック
        if buy_power < buy_price:
            self.log.warning(f'余力が足りません。必要額: {buy_price}、余力: {buy_power}')
            return False, buy_power

        # 余力から購入額を引く
        buy_power = buy_power - buy_price

        order_info = {
            'order_type': 'buy',
            'order_price': order_price, # 注文株価
            'sum_price': buy_price, # 購入金額
            'status': 'order',
            'sum_num': self.config.UNIT_NUM, # 注文株数
            'cancel_price': order_price + self.config.PRICE_RANGE #注文取消価格(1枚上に行ったら注文も1枚上に差し替え)
        }
        return order_info, buy_power

    def sell_order(self, buy_price):
        '''
        決済売り注文を入れる

        Args:
            buy_price(float): 購入株価

        Returns:
            order_info(dict): 注文情報
        '''
        # 利確価格(注文価格)と損切り価格の計算
        order_price = buy_price + (self.config.SECURING_BENEFIT_BORDER * self.config.PRICE_RANGE)
        loss_cut_price = buy_price - (self.config.LOSS_CUT_BORDER * self.config.PRICE_RANGE)

        # 売却成立時の金額
        sell_price = order_price * self.config.UNIT_NUM

        order_info = {
            'order_type': 'sell',
            'order_price': order_price, # 注文株価
            'sum_price': sell_price, # 売却金額
            'status': 'order',
            'sum_num': self.config.UNIT_NUM, # 注文株数
            'cancel_price': loss_cut_price # 注文取消価格(損切価格)
        }

        return order_info

    def traded_check(self, order_list, now_price, buy_power, trade_list):
        '''
        注文中のものが約定したかのチェック

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            buy_power(int): 余力
            trade_list(dict): 取引回数情報

        Returns:
            order_list(list): 約定分削除後の注文一覧
            buy_power(int): 約定分反映後の余力
            trade_list(dict): 約定分反映後の取引回数情報

        '''
        for order in order_list:
            # 買い注文約定判定
            if order['order_type'] == 'buy':
                if now_price < order['order_price']:
                    # ステータス更新
                    order['status'] = 'complete'
                    # 売り注文を入れる
                    order_info = self.sell_order(order['order_price'])
                    order_list.append(order_info)
            # 売り注文約定判定
            else:
                if now_price > order['order_price']:
                    # ステータス更新
                    order['status'] = 'complete'
                    buy_power += order['sum_price']
                    trade_list['securing_benefit_num'] += 1


        # 完了したレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'complete'], buy_power, trade_list

    def loss_cut_check(self, order_list, now_price, buy_power, board, trade_list):
        '''
        損切りラインを割った注文について損切り注文を入れる

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            sell_possible_price(float): 売却可能価格
            buy_power(int): 余力
            trade_list(dict): 取引回数情報

        Return:
            order_list(list): 損切り後の注文一覧
            buy_power(int): 損切り後の余力
            trade_list(dict): 損切り情報反映後の取引回数情報
        '''
        for order in order_list:
            if order['order_type'] == 'sell' and now_price <= order['cancel_price']:
                order['status'] = 'cancel'
                # 買い注文のある中で最も高い価格で損切り 本当は板の枚数もチェックしなきゃいけないけど今はパス
                buy_power = buy_power + (board['buy1_price'] * self.config.UNIT_NUM)
                trade_list['loss_cut_num'] += 1


        # キャンセルしたレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'cancel'], buy_power, trade_list

    def reorder_buy_check(self, order_list, now_price, buy_power):
        '''
        買い注文が約定せずに株価が上がったものについて注文をし直す

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            buy_power(int): 余力

        Return:
            order_list(list): 再注文後の注文一覧
            buy_power(int): 再注文後の余力
        '''
        # 一時保存用のorder_list
        tmp_order_list = []

        for order in order_list:
            if order['order_type'] == 'buy':
                # 注文価格からのpip数を計算
                diff_price = now_price - order['order_price']
                # 買い注文が成立せず株価が上がっていたら注文しなおし
                if diff_price / self.config.PRICE_RANGE > self.config.REORDER_LINE:
                    # 今の注文は取り消し
                    order['status'] = 'cancel'
                    # 余力も戻す
                    buy_power += order['sum_price']
                    # 今の株価を基準に買い注文の入れ直し
                    order_info, buy_power = self.buy_order(buy_power, now_price)
                    tmp_order_list.append(order_info)

        # キャンセルしたレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'cancel'] + tmp_order_list, buy_power
