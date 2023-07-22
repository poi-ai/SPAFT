import requests

class Order():
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers, api_url):
        self.api_headers = api_headers
        self.api_url = api_url

    def stock(self, password, stock_code, exchange, side, cash_margin,
              deliv_type, account_type, qty, front_order_type, price,
              expire_day, margin_trade_type = None, margin_premium_unit = None,
              fund_type = None, close_position_order = None,
              close_positions = None, reverse_limit_order = None):
        '''
        日本株の注文を発注する

        Args:
            TODO

        Returns:
            response.content(dict): 注文結果情報
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号
        '''
        url = f'{self.api_url}/sendorder'

        data = {'Password': password, 'Symbol': stock_code,
                'Exchange': exchange,
                'SecurityType': 1,
                'Side': side,
                'CashMargin': cash_margin,
                'DelivType': deliv_type,
                'AccountType': account_type,
                'Qty': qty,
                'FrontOrderType': front_order_type,
                'Price': price,
                'ExpireDay': expire_day}

        if margin_trade_type: data['MarginTradeType'] = margin_trade_type
        if margin_premium_unit: data['MarginPremiumUnit'] = margin_premium_unit
        if fund_type: data['FundType'] = fund_type
        if close_position_order: data['ClosePositionOrder'] = close_position_order
        if close_positions: data['ClosePositions'] = close_positions
        if reverse_limit_order: data['ReverseLimitOrder'] = reverse_limit_order

        try:
            response = requests.put(url, json = data)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理

        return response.content

    def future(self):
        '''先物の注文を発注する'''
        pass

    def option(self):
        '''オプション銘柄の注文を発注する'''
        pass

    def cancel(self, order_id, password):
        '''
        注文をキャンセルする

        Args:
            order_id(str): 受注時に発行された注文番号
            password(str): 注文パスワード

        Returns:
            response.content(dict): 注文結果情報
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号
        '''
        url = f'{self.api_url}/cancelorder'

        data = {'OrderId': order_id,
                'Password': password}

        try:
            response = requests.put(url, json = data)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理