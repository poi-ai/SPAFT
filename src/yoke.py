import requests

class KabusApi():
    TOP_URL = 'http://localhost:18080'

    def __init__(self):
        self.token = ''

    def set_token(self, api_password):
        '''
        トークンを発行する

        Args:
            api_password(str): APIのパスワード

        Returns:
            bool: 処理結果
        '''
        url = f'{KabusApi.TOP_URL}/token'
        data = {'APIPassword': api_password}

        try:
            response = requests.post(url, json = data)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        self.token = response.json()['Token']
        return True

    def get_token_header(self):
        '''トークンをヘッダーに埋め込む場合のフォーマットを取得する'''
        return {'X-API-KEY', self.token}

    def get_yoryoku(self):
        '''
        信用の新規取引可能額を取得

        Return:
            yoryoku(int or bool): 取引可能額(エラー時はFalse)
        '''
        url = f'{KabusApi.TOP_URL}/wallet/cash'

        try:
            response = requests.get(url, headers = self.get_token_header)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        return response.json()['MarginAccountWallet']

    def get_board(self, stock_code, market_code):
        '''
        指定した銘柄の板情報を取得

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間

        Return:
            response.content(dict or bool): 板情報(エラー時はFalse)
        '''
        url = f'{KabusApi.TOP_URL}/board/{stock_code}@{market_code}'

        try:
            response = requests.get(url, headers = self.get_token_header)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        return response.content()

    def get_stock_data(self, stock_code, market_code, add_info = True):
        '''
        指定した銘柄の情報を取得

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値

        Return:
            response.content(dict or bool): 指定した銘柄の情報(エラー時はFalse)
        '''
        add_info_str = 'true' if add_info else 'false'
        url = f'{KabusApi.TOP_URL}/board/{stock_code}@{market_code}?add_info={add_info_str}'

        try:
            response = requests.get(url, headers = self.get_token_header)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        return response.content