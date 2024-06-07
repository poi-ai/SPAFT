import sys
from service_base import ServiceBase

class Trade(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)


    def yutai_settlement(self):
        '''
        優待銘柄売却用に信用空売りの成行決済注文を行う

        argv:
            sys.argv[2]: 必須。決済対象の証券コード
            sys.argv[3]: 任意。決済株数 ※デフォルト 100
            sys.argv[4]: 任意。信用の種類 ※デフォルト 2(一般長期)
                1: 制度、2: 一般長期
        '''

        # 引数チェック
        if len(sys.argv) == 5:
            stock_code, num, order_type = sys.argv[2], sys.argv[3], sys.argv[4]
        elif len(sys.argv) == 4:
            stock_code, num, order_type = sys.argv[2], sys.argv[3], 2
        elif len(sys.argv) == 3:
            stock_code, num, order_type = sys.argv[2], 100, 2
        else:
            self.log.error('信用空売り決済処理に必要な引数が足りません')
            return

        self.log.info(f'信用空売り決済処理[優待用]のAPIリクエスト送信処理開始 証券コード: {stock_code}')

        order_info = {
            'Password': 'production',      # TODO ここはKabuStationではなくカブコムの取引パスワード
            'Symbol': str(stock_code),     # 証券コード
            'Exchange': 1,                 # 証券所   1: 東証 (3: 名証、5: 福証、6: 札証)
            'SecurityType': 1,             # 商品種別 1: 株式 のみ指定可
            'Side': 2,                     # 売買区分 2: 買 (1: 売)
            'CashMargin': 3,               # 取引区分 3: 返済 (1: 現物、2: 新規信用)
            'MarginTradeType': order_type, # 信用区分 1: 制度、2: 一般長期、3: デイトレ
            'DelivType': 2,                # 受渡区分 2: お預かり金 (3: auマネーコネクト、0: 現物売or信用新規)
            'FundType': '11',              # 資産区分 '11': 信用買・売 ('  ': 現物売り、 '02': 保護、'AA': 信用代用)
            'AccountType': 4,              # 口座区分 4: 特定 (2: 一般、12: 法人)
            'Qty': num,                    # 注文数量
            'ClosePositionOrder': 0,       # 決済順序 0: 古く利益が高いのから決済
            'FrontOrderType': 10,          # 執行条件 10: 成行
            'Price': 0,                    # 注文価格 0: 成行
            'ExpireDay': 0,                # 注文期限 0: 翌営業日 (ザラ場中は当日)
        }

        self.log.info(f'信用空売り決済処理[優待用]のAPIリクエスト送信処理開始 証券コード: {stock_code}')

        result, response = self.api.order.stock(order_info = order_info)

        if result == False:
            self.log.error(f'信用空売り決済処理[優待用]でエラー\n証券コード: {stock_code}\n{response}')
            return False

        self.log.info(f'信用空売り決済処理[優待用]のAPIリクエスト送信処理成功 証券コード: {stock_code}')
        return True

    def stock(self, order_info):
        '''
        日本株の注文を発注する

        Args:
            order_info(dict): 注文情報

        Returns:
            response.content(dict or bool): 注文結果情報 or False
                Result(int): 結果コード
                    0: 成功、それ以外: 失敗
                OrderId(str): 受付注文番号'''
        result, response = self.api.order.stock(order_info = order_info)
        # TODO