import json
import traceback
import requests

class Wallet():
    '''余力・保証金情報に関するAPI'''
    def __init__(self, api_headers, api_url):
        self.api_headers = api_headers
        self.api_url = api_url

    def cash(self):
        '''
        現物の余力を取得する

        Returns:
            response.content(dict): 現物余力情報
                StockAccountWallet(float): 現物買付可能額
                AuKCStockAccountWallet(float): auカブコム証券可能額
                AuJbnStockAccountWallet(float): auじぶん銀行残高

        '''
        url = f'{self.api_url}/wallet/cash/'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            pass # TODO ここにエラー処理

            print(e)
            print(traceback.format_exc())
            return False

        if response.status_code != 200:
            pass # TODO ここにエラー処理
            print(self.api_headers)
            print(json.loads(response.content.decode('utf-8')))

            print(response.status_code)
            return False

        return response.content

    def margin(self, stock_code = None, market_code = None):
        '''
        信用の余力を取得する

        Args:
            stock_code(int or str): 証券コード [任意]
            market_code(int or str): 市場コード [任意]
                1: 東証、3: 名証

        Returns:
            response.content(dict): 信用余力情報
                MarginAccountWallet(float): 信用新規可能額
                DepositkeepRate(float): 保証金維持率 ※銘柄指定時のみ
                ConsignmentDepositRate(float): 委託保証金率 ※銘柄指定時のみ
                CashOfConsignmentDepositRate(float): 現金委託保証金率 ※銘柄指定時のみ
        '''
        url = f'{self.api_url}/wallet/margin/'

        if stock_code != None and market_code != None:
            url += f'{stock_code}@{market_code}'

        self.api_headers['Content-Type'] = 'application/json'
        print(self.api_headers)

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            pass # TODO ここにエラー処理

            print(e)
            print(traceback.format_exc())

            return False

        if response.status_code != 200:
            pass # TODO ここにエラー処理

            print(self.api_headers)
            print(json.loads(response.content.decode('utf-8')))

            print(response.status_code)

            return False

        return response.content

    def future(self):
        '''先物の余力を取得する'''
        pass

    def option(self):
        '''オプションの余力を取得する'''
        pass