import json
import traceback
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
            password(str): 注文パスワード(≠APIパスワード)[必須]
            stock_code(str): 証券コード [必須]
            exchange(int): 市場コード [必須]
                1: 東証、3: 名証、5: 福証、6: 札証
            side(str): 売買区分 [必須]
                1: 売、2: 買
            cash_margin(int): 信用区分 [必須]
                1: 現物、2: 新規、3: 返済
            deliv_type(int): 受渡区分 [必須]
                0: 指定なし、1: 自動振替、2: お預り金、3: auマネーコネクト
            account_type(int): 口座種別 [必須]
                2: 一般、4: 特定、12: 法人
            qty(int): 注文株数
            front_order_type(int): 執行条件 [必須]
                10: 成行、13: 寄成(前場)、14: 寄成(後場)、15: 引成(前場)、16: 引成(後場)、17: IOC成行、
                20: 指値、21: 寄指(前場)、22: 寄指(後場)、23: 引指(前場)、24: 引指(後場)、25: 不成(前場)、
                26: 不成(後場)、27: IOC指値、30: 逆指値
            price(int): 注文価格 [必須]
                ※指値でない場合は0を指定
            expire_day(int、yyyyMMdd): 注文有効期限 [必須]
                ※当日中は0
            margin_trade_type(int): 信用取引区分 [任意]
                1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ)
            margin_premium_unit(float): プレミアム料 [任意]
            fund_type(str): 資産区分 [任意] ※現物注文は必須
                '  '(半ｽﾍﾟｰｽ2文字): 現物売の場合、02: 保護、AA: 信用代用、11: 信用取引
            close_position_order(int): 決済順序 [任意] ※信用返済の場合必須
                0: 日付(古い順)、損益(高い順)、1: 日付(古い順)、損益(低い順)、2: 日付(新しい順)、損益(高い順)、
                3: 日付(新しい順)、損益(低い順)、4: 損益(高い順)、日付(古い順)、5: 損益(高い順)、日付(新しい順)、
                6: 損益(低い順)、日付(古い順)、7: 損益(低い順)、日付(新しい順)
            close_positions(array[dict, dict] or dict): 信用返済 [任意] ※信用返済の場合必須
                HoldID(str): 返済建玉ID [任意]
                Qty(int): 返済建玉数量 [任意]
            reverse_limit_order(dict): 逆指値条件 [任意]
                TriggerSec(int): トリガー銘柄種別 [必須]
                    1: 発注銘柄の株価、2: 日経平均株価、3: TOPIX指数
                TriggerPrice(float): トリガー価格 [必須]
                UnderOver(int): トリガー条件 [必須]
                    1: 以下、2: 以上
                AfterHitOrderType(int): トリガー発動時執行条件 [必須]
                    1: 成行、2: 指値、3: 不成
                AfterHitPrice(float): トリガー発動時注文価格 [必須]
                    ※成行の場合は0

        Returns:
            response.content(dict): 注文結果情報
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号
        '''
        url = f'{self.api_url}/sendorder'

        data = {
            'Password': password,
            'Symbol': str(stock_code),
            'Exchange': exchange,
            'SecurityType': 1,
            'Side': str(side),
            'CashMargin': cash_margin,
            'DelivType': deliv_type,
            'AccountType': account_type,
            'Qty': qty,
            'FrontOrderType': front_order_type,
            'Price': float(price),
            'ExpireDay': expire_day
        }

        if margin_trade_type: data['MarginTradeType'] = margin_trade_type
        if margin_premium_unit: data['MarginPremiumUnit'] = margin_premium_unit
        if fund_type: data['FundType'] = fund_type
        if close_position_order: data['ClosePositionOrder'] = close_position_order
        #if close_positions: data['ClosePositions'] = close_positions
        if reverse_limit_order: data['ReverseLimitOrder'] = reverse_limit_order

        print(json.dumps(data, indent = 4, ensure_ascii = False))

        try:
            response = requests.post(url, headers = self.api_headers, json = data)
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