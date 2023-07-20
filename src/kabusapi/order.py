import requests

class Order():
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers, api_url):
        self.api_headers = api_headers
        self.api_url = api_url

    def stock(self):
        '''日本株の注文を発注する'''
        pass

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
            orderId(string): 受注時に発行された注文番号
            password(string): 注文パスワード

        Returns:
            Result(int): 結果コード
                0: 成功、それ以外: 失敗
            OrderId(string): 受付注文番号
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