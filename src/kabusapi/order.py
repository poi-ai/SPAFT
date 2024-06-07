import json
import traceback
import requests

class Order():
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers, api_url, log, trade_password):
        self.api_headers = api_headers
        self.api_url = api_url
        self.log = log
        self.trade_password = trade_password

    def stock(self, order_info):
        '''
        日本株の注文を発注する

        Args:
            order_info(dict): 注文情報

        Returns:
            result(bool): 実行結果
            response.content(dict): 注文結果情報 or エラーメッセージ
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号
        '''
        url = f'{self.api_url}/sendorder'

        try:
            response = requests.post(url, headers = self.api_headers, json = order_info)
        except Exception as e:
            return False, e

        if response.status_code != 200:
            return False, f'ステータスコード: {response.status_code}\n{json.loads(response.content)}'

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

        data = {
            'OrderId': order_id,
            'Password': password
        }

        try:
            response = requests.put(url, json = data)
        except Exception as e:
            self.log.error(f'注文キャンセル処理でエラー\n注文ID: {order_id}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'注文キャンセル処理でエラー\n注文ID: {order_id}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False