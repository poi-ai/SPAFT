import json
import traceback
import requests
from base import Base

class Order(Base):
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers, api_url):
        super().__init__()
        self.api_headers = api_headers
        self.api_url = api_url

    def stock(self, order_info):
        '''
        日本株の注文を発注する

        Args:
            order_info(dict): 注文情報

        Returns:
            response.content(dict): 注文結果情報
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号
        '''
        url = f'{self.api_url}/sendorder'

        try:
            response = requests.post(url, headers = self.api_headers, json = order_info)
        except Exception as e:
            self.error_output(f'注文発注処理でエラー\n証券コード: {order_info["Symbol"]}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.error_output(f'注文発注処理でエラー\n証券コード: {order_info["Symbol"]}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

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
            self.error_output(f'注文キャンセル処理でエラー\n注文ID: {order_id}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.error_output(f'注文キャンセル処理でエラー\n注文ID: {order_id}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False
