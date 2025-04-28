import json
import requests

class Register():
    '''PUSH配信に関連するAPI'''
    def __init__(self, api_headers, api_url, log):
        self.api_headers = api_headers
        self.api_url = api_url
        self.log = log

    def register(self, symbol, exchange = 1):
        '''
        PUSH配信する銘柄を登録する

        Args:
            symbol(str): 銘柄コード
            exchange(int): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証

        Returns:
            bool or str: 実行結果 or エラーメッセージ
        '''
        url = f'{self.api_url}/register'

        # リクエストボディ
        params = {
            'Symbols': [
                {
                    'Symbol': symbol,
                    'Exchange': exchange
                }
            ]
        }

        try:
           response = requests.put(url, headers = self.api_headers, json = params)
        except Exception as e:
            return f'PUSH配信登録APIでエラー\n{e}'

        if response.status_code != 200:
            return f'PUSH配信登録APIでエラー\nステータスコード: {response.status_code}\n{json.loads(response.content)}'

        return True

    def unregister(self):
        '''指定した銘柄のPUSH配信を解除する'''
        pass

    def unregister_all(self):
        '''
        全ての銘柄のPUSH配信を解除する

        Returns:
            bool or str: 実行結果 or エラーメッセージ
        '''
        url = f'{self.api_url}/unregister/all'

        try:
           response = requests.put(url, headers = self.api_headers)
        except Exception as e:
            return f'PUSH配信登録全解除APIでエラー\n{e}'

        if response.status_code != 200:
            return f'PUSH配信登録全解除APIでエラー\nステータスコード: {response.status_code}\n{json.loads(response.content)}'

        return True
