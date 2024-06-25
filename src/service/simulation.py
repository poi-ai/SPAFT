import json
import time
from service_base import ServiceBase

class Simulation(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

    def param_check(self, config):
        '''シミュレーション設定ファイルで設定したパラメータのチェック'''
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

    def buy_order(self, setting_info, now_price):
        '''
        新規買い注文を入れる

        Args:
            setting_info(dict): シミュレーションの設定情報
                buy_power(int): 余力
                order_line(int): 買い注文を何pips下に入れるか
                price_range(float): 呼値
                unit_num(int): 売買単位
            now_price(float): 現在株価

        Returns:
            order_info(dict): 注文情報
            buy_power(int): 注文後余力

        '''
        # n枚下の株価を計算
        order_price = now_price - (setting_info['price_range'] * setting_info['order_line'])

        # 購入額を計算
        buy_price = order_price * setting_info['unit_num']

        # 余力チェック
        if setting_info['buy_power'] < buy_price:
            self.log.warning(f'余力が足りません。必要額: {buy_price}、余力: {setting_info["buy_power"]}')
            return False, setting_info['buy_power']

        # 余力から購入額を引く
        setting_info['buy_power'] -= buy_price

        order_info = {
            'order_type': 'buy',
            'order_price': order_price, # 注文株価
            'sum_price': buy_price, # 購入金額
            'status': 'order',
            'sum_num': setting_info['unit_num'], # 注文株数
            'cancel_price': order_price + setting_info['price_range'] #注文取消価格(1枚上に行ったら注文も1枚上に差し替え)
        }
        return order_info, setting_info['buy_power']

    def sell_order(self, buy_price, setting_info):
        '''
        決済売り注文を入れる

        Args:
            buy_price(float): 購入株価
            setting_info(dict): シミュレーションの設定情報
                price_range(float): 呼値
                unit_num(int): 売買単位
                benefit_border(int): 何pip上で利確するか
                loss_cut_border(int): 何pip下で損切りするか

        Returns:
            order_info(dict): 注文情報
        '''
        # 利確価格(注文価格)と損切り価格の計算
        order_price = buy_price + (setting_info['benefit_border'] * setting_info['price_range'])
        loss_cut_price = buy_price - (setting_info['loss_cut_border'] * setting_info['price_range'])

        # 売却成立時の金額
        sell_price = order_price * setting_info['unit_num']

        order_info = {
            'order_type': 'sell',
            'order_price': order_price, # 注文株価
            'sum_price': sell_price, # 売却金額
            'status': 'order',
            'sum_num': setting_info['unit_num'], # 注文株数
            'cancel_price': loss_cut_price # 注文取消価格(損切り価格)
        }

        return order_info

    def traded_check(self, order_list, now_price, setting_info, trade_list):
        '''
        注文中のものが約定したかのチェック

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            setting_info(dict): シミュレーションの設定情報
                price_range(float): 呼値
                unit_num(int): 売買単位
                benefit_border(int): 何pip上で利確するか
                loss_cut_border(int): 何pip下で損切りするか
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
                    order_info = self.sell_order(order['order_price'], setting_info)
                    order_list.append(order_info)
            # 売り注文約定判定
            else:
                if now_price > order['order_price']:
                    # ステータス更新
                    order['status'] = 'complete'
                    setting_info['buy_power'] += order['sum_price']
                    trade_list['securing_benefit_num'] += 1


        # 完了したレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'complete'], setting_info['buy_power'], trade_list

    def loss_cut_check(self, order_list, board, setting_info, trade_list):
        '''
        損切りラインを割った注文について損切り注文を入れる

        Args:
            order_list(list): 注文一覧
            board(dict): 板情報
            setting_info(dict): シミュレーションの設定情報
                buy_power(int): 余力
                unit_num(int): 売買単位
            trade_list(dict): 取引回数情報

        Return:
            order_list(list): 損切り後の注文一覧
            buy_power(int): 損切り後の余力
            trade_list(dict): 損切り情報反映後の取引回数情報
        '''
        for order in order_list:
            if order['order_type'] == 'sell' and board['price'] <= order['cancel_price']:
                order['status'] = 'cancel'
                # 買い板の中で最も高い価格で損切り 本当は板の枚数もチェックしなきゃいけないけど今はパス
                setting_info['buy_power'] += (board['buy1_price'] * setting_info['unit_num'])
                trade_list['loss_cut_num'] += 1

        # 損切りしたレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'cancel'], setting_info['buy_power'], trade_list

    def reorder_buy_check(self, order_list, now_price, setting_info):
        '''
        買い注文が約定せずに株価が上がったものについて注文をし直す

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            setting_info(dict): シミュレーションの設定情報
                buy_power(int): 余力
                order_line(int): 買い注文を何pips下に入れるか
                price_range(float): 呼値

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
                if diff_price / setting_info['price_range'] > setting_info['order_line']:
                    # 今の注文は取り消し
                    order['status'] = 'cancel'
                    # 余力も戻す
                    setting_info['buy_power'] += order['sum_price']
                    # 今の株価を基準に買い注文の入れ直し
                    order_info, setting_info['buy_power'] = self.buy_order(setting_info, now_price)
                    tmp_order_list.append(order_info)

        # キャンセルしたレコードは削除して返す
        return [order for order in order_list if order.get('status') != 'cancel'] + tmp_order_list, setting_info['buy_power']

    def last_settlement(self, order_list, setting_info, board, trade_list):
        '''
        保有中の株を一括で決済する

        Args:
            order_list(list): 注文一覧
            now_price(float): 現在株価
            sell_possible_price(float): 売却可能価格
            setting_info(dict): シミュレーションの設定情報
                buy_power(int): 余力
                price_range(float): 呼値
                unit_num(int): 売買単位
                benefit_border(int): 何pip上で利確するか
            trade_list(dict): 取引回数情報

        Return:
            order_list(list): 損切り後の注文一覧
            buy_power(int): 損切り後の余力
            trade_list(dict): 損切り情報反映後の取引回数情報
        '''
        for order in order_list:
            if order['order_type'] == 'sell':
                # 買い板の中で最も高い価格で損切り／利確
                setting_info['buy_power'] += (board['buy1_price'] * setting_info['unit_num'])

                # 利確か損切りか判定
                buy_price = order['order_price'] - (setting_info['price_range'] * setting_info['benefit_border'])
                if buy_price < board['buy1_price']:
                    trade_list['loss_cut_num'] += 1
                elif buy_price > board['buy1_price']:
                    trade_list['securing_benefit_num'] += 1
            else:
                # 買い注文はキャンセルして購入額をそのまま余力に戻す
                setting_info['buy_power'] += order['sum_price']

        # 損切りしたレコードは削除して返す、買い注文中のものも削除する
        return [], setting_info['buy_power'], trade_list