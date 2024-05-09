import json
import traceback
import requests

class Order():
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers, api_url, log):
        self.api_headers = api_headers
        self.api_url = api_url
        self.log = log

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
            self.log.error(f'注文発注処理でエラー\n証券コード: {order_info["Symbol"]}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'注文発注処理でエラー\n証券コード: {order_info["Symbol"]}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
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
            self.log.error(f'注文キャンセル処理でエラー\n注文ID: {order_id}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'注文キャンセル処理でエラー\n注文ID: {order_id}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

    def yutai_settlement(self, stock_code, num = 100, order_type = 2):
        '''
        優待銘柄売却用に信用空売りの成行決済注文を行う

        Args:
            stock_code(str): 決済対象の証券コード
            num(int): 決済株数
            order_type(int): 信用の種類
                1: 制度、2: 一般長期
        '''
        url = f'{self.api_url}/sendorder'

        order_info = {
            'Password': 'production',      # TODO ここはKabuStationではなくカブコムの取引パスワード
            'Symbol': str(stock_code),     # 証券コード
            'Exchange': 1,                 # 証券所   1: 東証、3: 名証、5: 福証、6: 札証
            'SecurityType': 1,             # 商品種別 1: 株式 のみ指定可
            'Side': 2,                     # 売買区分 1: 売、2: 買
            'CashMargin': 3,               # 取引区分 1: 現物、2: 新規信用、3: 返済
            'MarginTradeType': order_type, # 信用区分 1: 制度、2: 一般長期、3: デイトレ
            'DelivType': 2,                # 受渡区分 0: 現物売or信用新規、2: お預かり金、3: auマネーコネクト
            'FundType': '11',              # 資産区分 '  ': 現物売り、 '02': 保護、'AA': 信用代用、'11': 信用買・売
            'AccountType': 4,              # 口座区分 2: 一般、4: 特定、12: 法人
            'Qty': num,                    # 注文数量
            'ClosePositionOrder': 0,       # 決済順序 0: 古く利益が高いのから決済
            'FrontOrderType': 10,          # 執行条件 10: 成行
            'Price': 0,                    # 注文価格 0: 成行
            'ExpireDay': 0,                # 注文期限 0: ザラ場中は当日、引け後は翌営業日
        }

        try:
            response = requests.post(url, headers = self.api_headers, json = order_info)
        except Exception as e:
            print(f'優待用信用空売り決済処理でエラー\n証券コード: {stock_code}\n{e}\n{traceback.format_exc()}')
            self.log.error(f'優待用信用空売り決済処理でエラー\n証券コード: {stock_code}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            print(f'優待用信用空売り決済処理でエラー\n証券コード: {stock_code}\nステータスコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            self.log.error(f'優待用信用空売り決済処理でエラー\n証券コード: {stock_code}\nステータスコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False