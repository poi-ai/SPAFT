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

        self.config = config

        # インスタンス変数に証券コードを設定 TODO パラメータチェックに入れるかも
        self.stock_code = config.STOCK_CODE

        # 営業日チェック
        if self.util.culc_time.is_exchange_workday() == False:
            self.log.info('本日は取引所の営業日でないため取引を行いません')
            return False

        # 営業時間チェック
        if self.util.culc_time.exchange_date() == 5:
            self.log.info('本日の取引時間を過ぎているため処理を行いません')
            return False

        # 設定時間と現在の時間のチェック
        now = self.util.culc_time.get_now()
        end = config.END_TIME
        if now > now.replace(hour = end[:2], minute = end[3:]):
            self.log.info('設定した終了時刻を過ぎているため処理を行いません')
            return False

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
                self.log.error(f'優先市場情報取得処理で証券コード不正エラー\n証券コード: {self.stock_code}')
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

        # 売買単位・値幅上限・下限・呼値グループ
        self.stock_info['unit_num'] = stock_info['TradingUnit']
        self.stock_info['upper_limit'] = stock_info['UpperLimit']
        self.stock_info['lower_limit'] = stock_info['LowerLimit']
        self.stock_info['yobine_group'] = stock_info['PriceRangeGroup']

        # 余力 < ストップ高での1単元必要額
        if self.buy_power < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            # 余力 < 前日終値の1単元必要額
            if self.buy_power < (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2:
                self.log.error(f'余力が前営業日終値の1単元購入に必要な金額を下回っているため取引を行いません\n余力: {self.buy_power}\n1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}')
                return False
            else:
                self.log.warning(f'余力がストップ高の1単元購入に必要な金額を下回っているため途中から取引が行われなくなる可能性があります\n余力: {self.buy_power}\nストップ高1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}')

        time.sleep(1)

        # 取引規制チェック
        result, regulations_info = self.api.info.regulations(stock_code = self.stock_code,
                                                             market_code = self.market_code)
        if result == False:
            self.log.error(regulations_info)

        # TODO 規制情報チェック
        # 単純に規制があるケース、増担、注意銘柄などがあるため全て網羅しなければいけない

        ### # プレミアム料の取得/チェック 現時点では空売りはやらないので一旦保留
        ### premium_info = self.get_premium_price(stock_code)

        # ソフトリミットの値をチェック
        result, response =  self.api.info.soft_limit()
        if result == False:
            self.log.error(response)
            return False

        # 信用のソフトリミットを取得
        self.soft_limit = response['Margin']

        # ソフトリミット < ストップ高での1単元必要額
        if self.soft_limit < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            # ソフトリミット < 前日終値の1単元必要額
            if self.soft_limit < (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2:
                self.log.error(f'ソフトリミットが前営業日終値の1単元購入に必要な金額を下回っているため取引を行いません\n余力: {self.soft_limit}\n1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}')
                return False
            else:
                self.log.warning(f'ソフトリミットがストップ高の1単元購入に必要な金額を下回っているため途中から取引が行われなくなる可能性があります\n余力: {self.soft_limit}\nストップ高1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}')

        return True

    def scalping(self):
        '''スキャルピングを行う'''
        # 時間チェック
        

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

    def enforce_settlement(self):
        '''
        保有中のデイトレ信用株の強制成行決済を行う

        Returns:
            result(bool): 実行結果
            order_flag(bool): 注文/注文キャンセルをしたか
        '''
        # 何かしらの注文/注文キャンセルを行ったか
        order_flag = False

        # まず注文に出しているものを全てキャンセルする
        # とりあえず注文発注しているのものを取得
        search_filter = {
            'product': '2', # 信用
            'uptime': self.util.culc_time.get_now().strftime('%Y%m%d085959') # 今日の08:59:59(=今日の取引)のみ抽出
        }
        result, response = self.api.info.orders(search_filter)
        if result == False:
            self.log.error(response)
            return False, order_flag

        time.sleep(0.2)

        # 1注文ずつチェック
        for order in response:
            # 未約定チェック
            if order['State'] < 5:
                # 新規/決済に関わらず注文キャンセル
                result, response = self.api.order.cancel(order_id = order['ID'],
                                                         password = self.config.TRADE_PASSWORD)
                order_flag = True
                if result == False:
                    self.log.error(response)
                    continue # ここ要検討、このままだと少なくともこの後自動ではリカバリできない

                time.sleep(0.2)

                # キャンセルした注文が返済の場合は成行で再度返済処理を入れる
                if order['CashMargin'] == 3:
                    result, response = self.util.mold.create_order_request(
                        password = self.config.TRADE_PASSWORD,     # 取引パスワード
                        stock_code = order['Symbol'],              # 証券コード
                        exchange = order['Exchange'],              # 市場コード
                        side = 1,                                  # 売買区分 1: 売り注文
                        cash_margin = 3,                           # 信用区分 3: 返済
                        deliv_type = 0,                            # 受渡区分 0: 指定なし(2: お預かり金でもいいかも)
                        account_type = 4,                          # 口座種別 4: 特定口座
                        qty = order['OrderQty'] - order['CumQty'], # 注文株数 (返済注文での注文株数-約定済株数)
                        front_order_type = 10,                     # 執行条件 10: 成行
                        price = 0,                                 # 執行価格 0: 成行
                        expire_day = 0,                            # 注文有効期限 0: 当日中
                        close_position_order = 0,                  # 決済順序 0: 古く利益の高い順(ぶっちゃけなんでもいい)
                    )

                    time.sleep(0.2)

                    if result == False:
                        self.log.error(response)

        # 保有株から成売するものを決める
        # 絞り込みのためのフィルター
        search_filter = {
            'product': '2', # 信用区分 - 信用
            'side': '2'     # 売買区分 - 買い
        }

        # 信用の保有株を取得
        result, response = self.api.info.positions(search_filter)
        if result == False:
            self.log.error(response)
            return False, order_flag

        time.sleep(0.2)

        # 保有中の株を1つずつチェック
        for stock in response:
            # デイトレ信用の場合のみ対象とする
            if stock['MarginTradeType'] != 3:
                order_flag = True

                # 保有株数 - 注文中株数
                qty = order['LeavesQty'] - order['HoldQty']

                # 注文できる株数が0の場合はスキップ
                if qty == 0: continue

                # 成売の決済注文を入れる
                result, response = self.util.mold.create_order_request(
                    password = self.config.TRADE_PASSWORD, # 取引パスワード
                    stock_code = stock['Symbol'],          # 証券コード
                    exchange = order['Exchange'],          # 市場コード
                    side = 1,                              # 売買区分 1: 売り注文
                    cash_margin = 3,                       # 信用区分 3: 返済
                    deliv_type = 0,                        # 受渡区分 0: 指定なし(2: お預かり金でもいいかも)
                    account_type = 4,                      # 口座種別 4: 特定口座
                    qty = qty,                             # 注文株数
                    front_order_type = 10,                 # 執行条件 10: 成行
                    price = 0,                             # 執行価格 0: 成行
                    expire_day = 0,                        # 注文有効期限 0: 当日中
                    close_position_order = 0,              # 決済順序 0: 古く利益の高い順(ぶっちゃけなんでもいい)
                )

                time.sleep(0.2)

                if result == False:
                    self.log.error(response)

        return True, order_flag

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