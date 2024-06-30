import sys
import time
from service_base import ServiceBase

class Trade(ServiceBase):
    '''取引に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

        # 余力
        self.buy_power = -1
        # 証券コード
        self.stock_code = -1
        # 市場コード
        self.market_code = -1
        # 銘柄情報
        self.stock_info = {}

    def scalping_init(self, config):
        '''
        スキャルピングトレードを行う場合の初期処理

        Args:
            config(config): 設定ファイル

        Returns:
            result(bool): 実行結果

        '''
        # 設定ファイルのパラメータチェック
        result = self.param_check(config)
        if result == False:
            return False

        # インスタンス変数に証券コードを設定 TODO パラメータチェックに入れるかも
        self.stock_code = config.STOCK_CODE

        # 信用余力の取得
        buy_power = self.get_margin_buy_power()
        if buy_power == False:
            return False

        # インスタンス変数へ設定
        self.buy_power = buy_power

        time.sleep(1)

        # 銘柄の市場情報を取得
        result, stock_info = self.api.info.primary_exchange(stock_code = self.stock_code)
        if result == False:
            if stock_info == 4002001:
                self.log.error(f'優先市場情報取得処理で条件コード不正エラー\n証券コード: {self.stock_code}')
            else:
                self.log.error(stock_info)
            return False

        # 市場IDを抜き出してインスタンス変数へセット
        self.market_code = stock_info['PrimaryExchange']

        time.sleep(1)

        # 銘柄情報を取得
        result, stock_info = self.get_symbol(stock_code = self.stock_code,
                                                  market_code = self.market_code,
                                                  add_info = False)
        if result == False:
            self.log.error(stock_info)
            return False

        # デイトレ信用が取引可能か
        if stock_info['KCMarginBuy'] != True:
            self.log.warning(f'デイトレ信用の取引が行えない銘柄です\n証券コード: {self.stock_code}')
            return False

        # 売買単位
        self.stock_info['unit_num'] = stock_info['TradingUnit']
        # 値幅上限・下限
        self.stock_info['upper_limit'] = stock_info['UpperLimit']
        self.stock_info['upper_limit'] = stock_info['UpperLimit']
        # 呼値グループ
        self.yobine_group = stock_info['PriceRangeGroup']

        time.sleep(1)

        # 取引規制チェック
        result, regulations_info = self.api.info.regulations(stock_code = self.stock_code,
                                                             market_code = self.market_code)
        if result == False:
            self.log.error(regulations_info)

        # TODO 規制情報チェック

        ### # プレミアム料の取得/チェック 現時点では空売りはやらないので一旦保留
        ### premium_info = self.get_premium_price(stock_code)

        # TODO 今日約定したデイトレ信用の注文から未決済のものを決済する リカバリ用
        # 要検討 決済しておかないと巻き込まれるが、initで処理するもの違う気が

        # ソフトリミットの値をチェック
        result, response =  self.api.info.soft_limit()
        if result == False:
            self.log.error(response)
            return False

        # 信用のソフトリミットを取得
        self.soft_limit = response['Margin']

        # TODO 上限価格で必要な購入金額とのチェック

        return True

    def scalping(self):
        '''スキャルピングを行う'''
        pass

    def param_check(self, config):
        '''設定ファイルで設定したパラメータのチェック'''
        # TODO あとで
        return True

    def get_margin_buy_power(self):
        '''
        現在の信用余力を取得する

        Returns:
            result(float or False): 信用余力 or エラーメッセージ
        '''

        # API実行
        response = self.api.wallet.margin()

        # 取得成功した場合はdict型で返ってくる
        if type(response) == type({}):
            try:
                return response['MarginAccountWallet']
            except Exception as e:
                self.log.error(f'信用余力情報の取り出しに失敗\n{e}')
                return False
        else:
            self.log.error(response)
            return False

    def get_premium_price(self, stock_code):
        '''
        指定した銘柄のデイトレプレミアム料を取得する

        Args:
            stock_code(str): 証券コード

        Returns:
            premium_info(dict) or False: プレミアム手数料データ or エラーメッセージ
                premium_type(bool): 空売り可不
                    True: 空売り可能、False: 空売り不可能
                premium(float): プレミアム料
        '''

        # API実行
        response = self.api.info.premium_price(stock_code)

        # 取得成功した場合はdict型で返ってくる
        if type(response) == 'dict':
            premium_info = {}
            try:
                # 銘柄の種別 Noneの場合のみ空売りできない
                if response['MarginPremiumType'] == None:
                    premium_info['premium_type'] == False
                else:
                    premium_info['premium_type'] == True

                # プレミアム料
                if response['MarginPremium'] == None:
                    premium_info['premium'] == 0.0
                else:
                    premium_info['premium'] == response['MarginPremium']

                return premium_info

            except Exception as e:
                self.log.error(f'信用余力情報の取り出しに失敗\n{e}')
                return False
        else:
            self.log.error(response)
            return False

    def get_symbol(self, stock_code, market_code, add_info = True, retry_count = 0):
        '''
        銘柄情報の取得を行う(銘柄登録上限のリカバリも)

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」

        Returns:
            result(bool): 実行結果
            response(dict): 指定した銘柄の情報 or エラーメッセージ(str) or エラーコード(int)

        '''
        result, response = self.api.info.symbol(stock_code = stock_code,
                                                market_code = market_code,
                                                add_info = add_info)
        if result == False:
            # 登録数上限エラー
            if response == 4002006:
                # 再帰で同じエラーが出たら無限ループに入るのでこれ以上は進めない
                if retry_count > 0:
                    return False, f'銘柄情報取得処理で登録数上限エラー(再帰)\n証券コード: {stock_code}'

                self.log.warning(f'銘柄情報取得処理で登録数上限エラー\n証券コード: {stock_code}')

                # 登録銘柄を全解除するAPI呼び出し
                result = self.api.register.unregister_all()
                if result != True:
                    return False, result

                # 登録銘柄の解除に成功したら再帰でもう一度銘柄情報の取得を行う
                return self.get_symbol(stock_code, market_code, add_info, retry_count = 1)
            # その他のエラー
            else:
                return False, response

        return True, response


    def yutai_settlement(self, trade_password):
        '''
        優待銘柄売却用に信用空売りの成行決済注文を行う

        コマンドライン引数:
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
            'Password': trade_password,      # TODO ここはKabuStationではなくカブコムの取引パスワード
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
                OrderId(str): 受付注文番号
        '''
        result, response = self.api.order.stock(order_info = order_info)
        # TODO