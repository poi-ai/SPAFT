import sys
import time
from service_base import ServiceBase

class Trade(ServiceBase):
    '''取引に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

        # 取引パスワード
        self.trade_password = ''
        # 余力
        self.buy_power = -1
        # 証券コード
        self.stock_code = -1
        # 市場コード
        self.market_code = -1
        # 銘柄情報
        self.stock_info = {}
        # スキャルピングを行う時間
        self.start_time = None
        self.end_time = None
        # 買い注文時に現在値の何pip数下に注文を入れるか
        self.order_line = -1
        # 利確/損切りのpips数
        self.securing_benefit = -1
        self.loss_cut = -1
        # 直前の株価
        self.before_price = -1

    def scalping_init(self, config):
        '''
        スキャルピングトレードを行う場合の初期処理

        Args:
            config(module): 設定ファイル

        Returns:
            result(bool): 実行結果

        '''
        self.log.info('スキャルピング初期処理取得処理開始')
        # 設定ファイルのパラメータチェック
        result = self.param_check(config)
        if result == False:
            return False

        # インスタンス変数に証券コードを設定 TODO パラメータチェックに入れるかも
        self.stock_code = config.STOCK_CODE

        # 営業日チェック
        if self.util.culc_time.exchange_date() == False:
            self.log.info('本日は取引所の営業日でないため取引を行いません')
            return False
        self.log.info('営業日チェックOK')

        # 営業時間チェック
        if self.util.culc_time.exchange_time() == 5:
            self.log.info('本日の取引時間を過ぎているため処理を行いません')
            return False
        self.log.info('取引時間チェックOK')

        # 設定時間と現在の時間のチェック
        now = self.util.culc_time.get_now()
        end = config.END_TIME
        if now > now.replace(hour = int(end[:2]), minute = int(end[3:])):
            self.log.info('設定した終了時刻を過ぎているため処理を行いません')
            return False
        self.log.info('設定時間チェックOK')

        # 信用余力の取得
        buy_power = self.get_margin_buy_power()
        if buy_power is False:
            return False
        self.log.info('余力情報取得OK')

        # インスタンス変数へ設定
        self.buy_power = buy_power

        time.sleep(1)

        # 銘柄の市場情報を取得
        self.log.info('銘柄の優先市場情報取得処理開始')
        result, stock_info = self.api.info.primary_exchange(stock_code = self.stock_code)
        if result == False:
            if stock_info == 4002001:
                self.log.error(f'銘柄の優先市場情報取得処理で証券コード不正エラー\n証券コード: {self.stock_code}')
            else:
                self.log.error(stock_info)
            return False
        self.log.info('銘柄の優先市場情報取得処理終了')

        # 市場IDを抜き出してインスタンス変数へセット
        self.market_code = stock_info['PrimaryExchange']

        time.sleep(1)

        # 銘柄情報を取得
        self.log.info('銘柄情報取得処理開始')
        result, stock_info = self.get_symbol(stock_code = self.stock_code,
                                                  market_code = self.market_code,
                                                  addinfo = False)
        if result == False:
            self.log.error(stock_info)
            return False
        self.log.info('銘柄情報取得処理終了')

        # デイトレ信用が取引可能か
        if stock_info['KCMarginBuy'] != True:
            self.log.warning(f'デイトレ信用の取引が行えない銘柄です\n証券コード: {self.stock_code}')
            return False

        # 売買単位・値幅上限・下限・呼値グループ
        self.stock_info['unit_num'] = stock_info['TradingUnit']
        self.stock_info['upper_limit'] = stock_info['UpperLimit']
        self.stock_info['lower_limit'] = stock_info['LowerLimit']
        self.stock_info['yobine_group'] = stock_info['PriceRangeGroup']

        # 今日の制限値幅で呼値が変わるか
        upper_yobine = self.util.stock_price.get_price_range(self.stock_info['yobine_group'], self.stock_info['upper_limit'])
        lower_yobine = self.util.stock_price.get_price_range(self.stock_info['yobine_group'], self.stock_info['lower_limit'])

        # 変わらないなら取引ではそのまま呼値を使えるようにする
        if upper_yobine == lower_yobine:
            self.stock_info['yobine'] = upper_yobine
        else:
            self.stock_info['yobine'] = -1

        # 余力 < ストップ高での1単元必要額
        self.log.info('余力チェック開始')
        if self.buy_power < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            # 余力 < 前日終値の1単元必要額
            if self.buy_power < (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2:
                self.log.error(f'余力が前営業日終値の1単元購入に必要な金額を下回っているため取引を行いません\n余力: {self.buy_power}円 1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}円')
                return False
            else:
                self.log.warning(f'余力がストップ高の1単元購入に必要な金額を下回っているため途中から取引が行われなくなる可能性があります\n余力: {self.buy_power}円 ストップ高1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}円')
        self.log.info('余力チェックOK')

        time.sleep(1)

        # 取引規制チェック
        self.log.info('取引規制情報取得処理開始')
        result, regulations_info = self.api.info.regulations(stock_code = self.stock_code,
                                                             market_code = self.market_code)
        if result == False:
            self.log.error(regulations_info)
            return False
        self.log.info('取引規制情報取得処理終了')

        # TODO 規制情報チェック
        # 単純に規制があるケース、増担、注意銘柄などがあるため全て網羅しなければいけない

        # ソフトリミットの値をチェック
        self.log.info('ソフトリミット情報取得処理開始')
        result, response =  self.api.info.soft_limit()
        if result == False:
            self.log.error(response)
            return False
        self.log.info('ソフトリミット情報取得処理終了')

        # 信用のソフトリミットを取得
        self.soft_limit = response['Margin'] * 10000

        # ソフトリミット < ストップ高での1単元必要額
        self.log.info('ソフトリミットチェック処理開始')
        if self.soft_limit < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            # ソフトリミット < 前日終値の1単元必要額
            if self.soft_limit < (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2:
                self.log.error(f'ソフトリミットが前営業日終値の1単元購入に必要な金額を下回っているため取引を行いません\n余力: {self.soft_limit}円 1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}円')
                return False
            else:
                self.log.warning(f'ソフトリミットがストップ高の1単元購入に必要な金額を下回っているため途中から取引が行われなくなる可能性があります円 余力: {self.soft_limit}\nストップ高1単元必要金額: {(self.stock_info["upper_limit"] + self.stock_info["lower_limit"]) * self.stock_info["unit_num"] / 2}円')
        self.log.info('ソフトリミット情報取得処理終了')

        self.log.info('スキャルピング初期処理取得処理終了')

        return True

    def scalping(self):
        '''スキャルピングを行う'''
        self.log.info('スキャルピング主処理開始')

        # 開始時間チェック
        self.log.info('スキャルピング開始時間チェック')
        now = self.util.culc_time.get_now()
        diff_seconds = (now.replace(hour = int(self.start_time[:2]), minute = int(self.start_time[3:])) - now).total_seconds()

        # 開始まで時間がある場合待機する
        if diff_seconds > 0:
            self.log.info(f'スキャルピング開始まで{diff_seconds}秒待機')
            time.sleep(diff_seconds)
        else:
            self.log.info('スキャルピング開始時間超過のため待機なし')

        # 初期注文のみ処理を変えるのでフラグを立てておく
        init_order = True

        # 注文非検知の時用のカウンター
        none_operate = 0

        # 購入価格
        ordered_buy_price = -1

        # 利確/損切り判定用
        secure_flag = False

        self.log.info('トレードスタート')
        while True:
            # 時間チェック
            now = self.util.culc_time.get_now()

            # 前場の取引時間中かつ、設定した前場取引終了時間を過ぎている場合はお昼休みまで待機
            if self.util.culc_time.exchange_time() == 1:
                diff_seconds = (now.replace(hour = int(self.pm_end[:2]), minute = int(self.pm_end[3:])) - now).total_seconds()

                # 設定した時間を過ぎた場合(終了予定時刻 - 現在時刻)か11:28を超えたら強制成行決済
                if diff_seconds <= 0 or (now.hour == 11 and now.minute >= 28) or now.hour >= 12:
                    self.enforce_management(trade_type = '前場取引終了設定時間越え')

                    # お昼休み1分後まで待機
                    wait_seconds = (now.replace(hour = 11, minute = 3) - now).total_seconds()
                    if wait_seconds > 0:
                        self.log.info(f'前場取引終了~お昼休みまで{wait_seconds}秒待機')
                        time.sleep(wait_seconds)

                    # チェック対象の時間を取り直し
                    now = self.util.culc_time.get_now()

            # お昼休みなら後場開始まで待機
            if self.util.culc_time.exchange_time() == 4:
                diff_seconds = (now.replace(hour = 12, minute = 30) - now).total_seconds()

                if diff_seconds > 0:
                    self.log.info(f'お昼休み突入~スキャルピング再開まで{diff_seconds}秒待機')
                    time.sleep(diff_seconds)

            # 設定したスキャ終了時間 - 現在時間
            diff_seconds = (now.replace(hour = int(self.end_time[:2]), minute = int(self.end_time[3:])) - now).total_seconds()

            # 終了時間を過ぎているか14:55を過ぎたら強制成行決済を行って処理終了
            if diff_seconds < 0 or (now.hour == 14 and now.minute >= 55):
                self.enforce_management(trade_type = '取引全体終了設定時間越え')
                break

            # 板情報取得
            result, board_info = self.api.info.board(stock_code = self.stock_code, market_code = self.market_code)
            if result == False:
                self.log.error(board_info)
                time.sleep(3)
                continue

            time.sleep(0.2)

            # 取得した板情報を分類する
            board_detail_info = self.board_analysis(board_info)
            if board_detail_info == False:
                time.sleep(3)
                continue

            # 保有株一覧取得
            result, hold_stock_list = self.get_today_position(symbol = self.stock_code)
            if result == False:
                self.log.error(hold_stock_list)
                time.sleep(3)
                continue

            time.sleep(0.2)

            # 注文一覧取得
            result, order_list = self.get_today_order(symbol = self.stock_code)
            if result == False:
                self.log.error(order_list)
                time.sleep(3)
                continue

            time.sleep(0.2)

            # 保有中の株/注文中の株があるか
            hold_flag = False
            order_flag = False

            # 保有中銘柄を1つずつチェック
            for hold_stock in hold_stock_list:
                 # デイトレ信用の場合のみ対象とする
                if hold_stock['MarginTradeType'] == 3:
                    # 既に返済が済んでいるものも保有扱いされるので除外する
                    # 保有中株数も注文数株数も0のものは除外
                    if hold_stock['LeavesQty'] != 0 or hold_stock['HoldQty'] != 0:
                        hold_flag = True
                        # 保有株数 - 注文中株数
                        qty = hold_stock['LeavesQty'] - hold_stock['HoldQty']

                        # 売り注文が出されていない株がある場合は注文を出す
                        if qty > 0:
                            # 利確価格で注文
                            result = self.sell_secure_order(qty = qty, stock_price = hold_stock['Price'])
                            time.sleep(0.3)
                            if result == False:
                                continue
                            secure_flag = True

            # 板情報からいくら未満の買注文の場合訂正対象になるか
            result, decent_buy_price = self.util.stock_price.get_updown_price(yobine_group = self.stock_info['yobine_group'], # 呼値グループ
                                                                              stock_price = board_detail_info['buy_price'],
                                                                              pips = self.order_line,
                                                                              updown = 0)
            if result == False:
                self.log.error(decent_buy_price)
                continue

            # 板情報より購入価格がいくら以上だと損切りにするか TODO 呼値が変わると狂うのでそのうち直す
            result, decent_cut_price = self.util.stock_price.get_updown_price(yobine_group = self.stock_info['yobine_group'], # 呼値グループ
                                                                                 stock_price = board_detail_info['sell_price'],
                                                                                 pips = self.loss_cut,
                                                                                 updown = 1)
            if result == False:
                self.log.error(decent_cut_price)
                continue

            # 注文を1つずつチェック
            for order in order_list:
                # デイトレ信用の場合のみチェック対象
                if order['MarginTradeType'] != 3:
                    continue

                # ステータスチェック 現時点で約定/取消されていない注文のみチェック対象
                if order['State'] == 5:
                    continue

                order_flag = True

                # 注文種別(新規買/決済売)をチェック
                # 新規買の場合
                if order['CashMargin'] == 2:
                    # 注文価格よりさらに上に行っていたら指値を変更して再注文
                    if decent_buy_price > order['Price']:
                        self.log.info(f'新規買注文指しなおし処理開始 購入価格: {order["Price"]}円 → {decent_buy_price}円')

                        self.log.info(f'注文キャンセル処理開始 ID: {order["ID"]}')
                        result, response = self.api.order.cancel(order_id = order['ID'],
                                                               password = self.trade_password)
                        time.sleep(0.1)
                        if result == False:
                            self.log.error(response)
                            continue
                        self.log.info(f'注文キャンセル処理終了 ID: {order["ID"]}')

                        result, buy_price = self.buy_order(stock_price = board_detail_info['buy_price'])
                        time.sleep(0.2)
                        if result == False:
                            continue
                        ordered_buy_price = ordered_buy_price

                        self.log.info(f'新規買注文指しなおし処理終了')

                # 返済売の場合
                else:
                    # 利確売の場合
                    if secure_flag == True:
                        # 現在価格が購入した額の損切り価格を下回っているかチェック
                        # いくら以上の購入価格の場合損切りラインを割ったか <= 購入価格
                        if decent_cut_price <= ordered_buy_price:
                            self.log.info(f'利確から損切りに差し替え処理開始 {order["Price"]}円 → {board_detail_info["sell_price"]}円')

                            self.log.info(f'注文キャンセル処理開始 ID: {order["ID"]}')
                            result, response = self.api.order.cancel(order_id = order['ID'],
                                                                password = self.trade_password)
                            if result == False:
                                self.log.error(response)
                                continue
                            self.log.info(f'注文キャンセル処理終了 ID: {order["ID"]}')

                            time.sleep(0.5)

                            # 売り板の1枚目で損切りを注文
                            result = self.sell_cut_order(qty = order['OrderQty'], order_price = board_detail_info['sell_price'])
                            if result == False:
                                continue

                            # 利確フラグを折る
                            secure_flag = False

                            self.log.info(f'利確から損切りに差し替え処理終了')

                            time.sleep(0.3)

                    # 損切りの場合
                    else:
                        # 板の売りの1枚目が損切りの売り注文価格よりさらに下がっているか
                        if board_detail_info["sell_price"] < order['Price']:
                            self.log.info(f'損切り価格引き下げ処理開始 {order["Price"]}円 → {board_detail_info["sell_price"]}円')

                            self.log.info(f'注文キャンセル処理開始 ID: {order["ID"]}')
                            result, response = self.api.order.cancel(order_id = order['ID'],
                                                                password = self.trade_password)
                            if result == False:
                                self.log.error(response)
                                continue
                            self.log.info(f'注文キャンセル処理終了 ID: {order["ID"]}')

                            time.sleep(0.5)

                            # 売り板の1枚目で損切りを再注文
                            result = self.sell_cut_order(qty = order['OrderQty'], order_price = board_detail_info['sell_price'])
                            if result == False:
                                continue

                            # 利確フラグを折る
                            secure_flag = False

                            self.log.info(f'損切り価格引き下げ処理終了')

                            time.sleep(0.3)


            # 保有株も注文もなく,1周目の場合は新規買い注文を入れる
            if not hold_flag and not order_flag and init_order:
                # 現在価格でなく買い板の最高価格ベースを基準に買いを入れる
                result, buy_price = self.buy_order(stock_price = board_detail_info['buy_price'])
                time.sleep(0.3)
                if result == False:
                    continue
                ordered_buy_price = buy_price

            # 注文も保有株もない場合
            if not hold_flag and not order_flag:
                none_operate += 1
            else:
                none_operate = 0

            # 保有株情報取得と注文情報取得はコンマ秒リクエストにラグがあるため
            # 実際はあるもののすり抜ける可能性がある
            # 3周連続で存在しない場合はポジションなしとみなして新規注文を入れる
            if none_operate >= 3:
                result, buy_price = self.buy_order(stock_price = board_detail_info['buy_price'])
                time.sleep(0.3)
                if result == False:
                    continue
                # 成功したらカウントリセット
                none_operate = 0
                ordered_buy_price = buy_price

            # 1周目終了でしたら初回注文に使うためのフラグは折る
            init_order = False

        self.log.info('トレード終了')
        self.log.info('スキャルピング主処理終了')

    def param_check(self, config):
        '''
        設定ファイルで設定したパラメータのチェック

        Args:
            config(module): 設定ファイル

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ

        '''
        # TODO バリデーションチェックを追加

        # 取引パスワード
        self.trade_password = config.TRADE_PASSWORD

        # 証券コード
        self.stock_code = config.STOCK_CODE

        # スキャルピングを行う時間
        self.start_time = config.START_TIME
        self.pm_end = config.AM_END_TIME
        self.end_time = config.END_TIME

        # 買い注文時に現在値の何pip数下に注文を入れるか
        self.order_line = config.ORDER_LINE

        # 利確/損切りのpips数
        self.securing_benefit = config.SECURING_BENEFIT_BORDER
        self.loss_cut = config.LOSS_CUT_BORDER

        return True, None

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

    def get_symbol(self, stock_code, market_code, addinfo = True, retry_count = 0):
        '''
        銘柄情報の取得を行う(銘柄登録上限のリカバリも)

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            addinfo(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」

        Returns:
            result(bool): 実行結果
            response(dict): 指定した銘柄の情報 or エラーメッセージ(str) or エラーコード(int)

        '''
        result, response = self.api.info.symbol(stock_code = stock_code,
                                                market_code = market_code,
                                                addinfo = addinfo)
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
                return self.get_symbol(stock_code, market_code, addinfo, retry_count = 1)
            # その他のエラー
            else:
                return False, response

        return True, response

    def enforce_settlement(self, trade_password = None):
        '''
        保有中のデイトレ信用株の強制成行決済を行う

        Args:
            trade_password(str): 取引パスワード

        Returns:
            result(bool): 実行結果
            order_flag(bool): 注文/注文キャンセルをしたか
        '''
        self.log.info('強制成行決済処理開始')
        # 直接このメソッドを呼び出す場合は取引パスワードを持ってないのでインスタンス変数に設定する
        if trade_password:
            self.trade_password = trade_password

        # 何かしらの注文/注文キャンセルを行ったか
        order_flag = False

        # まず注文に出しているものを全てキャンセルする
        # とりあえず注文発注しているのものを取得
        self.log.info('注文情報取得処理開始')
        result, response = self.get_today_order(symbol = self.stock_code)
        time.sleep(0.3)
        if result == False:
            self.log.error(response)
            return False, order_flag
        self.log.info('注文情報取得処理終了')

        # 1注文ずつチェック
        self.log.info('注文情報取得チェック処理開始')
        for order in response:
            # デイトレ信用の場合のみ対象とする
            if 'MarginTradeType' in order:
                if order['MarginTradeType'] == 3:
                    # SOR市場(手動注文)は仕様上操作できないのでパスする
                    if order['Exchange'] != 9:
                        # 未約定チェック
                        if order['State'] < 5:

                            # 新規/決済に関わらず注文キャンセル
                            self.log.info(f'注文キャンセル処理開始 ID: {order["ID"]}')
                            result, response = self.api.order.cancel(order_id = order['ID'],
                                                                     password = self.trade_password)
                            self.log.info(f'注文キャンセル処理終了 ID: {order["ID"]}')
                            order_flag = True
                            if result == False:
                                self.log.error(response)
                                continue # ここ要検討、このままだと少なくともこの後自動ではリカバリできない

                            time.sleep(0.3)

                            # キャンセルした注文が返済の場合は成行で再度返済処理を入れる
                            if order['CashMargin'] == 3:
                                self.log.info('再返済注文処理開始')
                                result, order_info = self.util.mold.create_order_request(
                                    password = self.trade_password,            # 取引パスワード
                                    stock_code = order['Symbol'],              # 証券コード
                                    exchange = order['Exchange'],              # 市場コード
                                    side = 1,                                  # 売買区分 1: 売り注文
                                    cash_margin = 3,                           # 信用区分 3: 返済
                                    deliv_type = 2,                            # 資金受渡区分 2: お預かり金(0: 指定なし だとエラー)
                                    account_type = 4,                          # 口座種別 4: 特定口座
                                    qty = order['OrderQty'] - order['CumQty'], # 注文株数 (返済注文での注文株数-約定済株数)
                                    front_order_type = 10,                     # 執行条件 10: 成行
                                    price = 0,                                 # 執行価格 0: 成行
                                    expire_day = 0,                            # 注文有効期限 0: 当日中
                                    close_position_order = 0,                  # 決済順序 0: 古く利益の高い順(ぶっちゃけなんでもいい)
                                )

                                if result == False:
                                    self.log.error(order_info)
                                    continue

                                time.sleep(0.3)

                                # 返済注文リクエスト送信
                                result, response = self.api.order.stock(order_info = order_info)

                                if result == False:
                                    self.log.error(response)
                                    continue

                                time.sleep(0.3)

                                self.log.info('再返済注文処理終了')

        self.log.info('注文情報取得チェック処理終了')

        # 保有株から成売するものを決める
        # 信用の保有株を取得
        self.log.info('保有株情報取得処理開始')
        result, response = self.get_today_position(side = '2')
        if result == False:
            self.log.error(response)
            return False, order_flag
        self.log.info('保有株情報取得処理終了')

        time.sleep(0.2)

        # 保有中の株を1つずつチェック
        self.log.info('保有株情報チェック処理開始')
        for stock in response:
            # デイトレ信用の場合のみ対象とする
            if stock['MarginTradeType'] != 3:
                order_flag = True

                # 保有株数 - 注文中株数
                qty = order['LeavesQty'] - order['HoldQty']

                # 注文できる株数が0の場合はスキップ
                if qty == 0: continue

                # 成売の決済注文を入れる
                self.log.info('保有株成行注文処理開始')
                result, order_info = self.util.mold.create_order_request(
                    password = self.trade_password, # 取引パスワード
                    stock_code = stock['Symbol'],   # 証券コード
                    exchange = order['Exchange'],   # 市場コード
                    side = 1,                       # 売買区分 1: 売り注文
                    cash_margin = 3,                # 信用区分 3: 返済
                    deliv_type = 2,                 # 資金受渡区分 2: お預かり金(0: 指定なし だとエラー)
                    account_type = 4,               # 口座種別 4: 特定口座
                    qty = qty,                      # 注文株数
                    front_order_type = 10,          # 執行条件 10: 成行
                    price = 0,                      # 執行価格 0: 成行
                    expire_day = 0,                 # 注文有効期限 0: 当日中
                    close_position_order = 0,       # 決済順序 0: 古く利益の高い順(ぶっちゃけなんでもいい)
                )

                time.sleep(0.3)

                if result == False:
                    self.log.error(response)
                    continue

                # 返済注文リクエスト送信
                result, response = self.api.order.stock(order_info = order_info)

                if result == False:
                    self.log.error(response)
                    continue

                time.sleep(0.3)

                self.log.info('保有株成行注文処理終了')

        self.log.info('保有株情報チェック処理終了')
        self.log.info('強制成行決済処理終了')

        return True, order_flag

    def enforce_management(self, trade_type, trade_password = None):
        '''
        強制成行決済処理の呼び出しや結果に応じた再呼び出し/ログ出力を行う

        Args:
            trade_type(str): どこ経由の強制決済か ログ出力に使用
            trade_password(str): 取引パスワード

        '''
        # 強制決済
        self.log.info(f'{trade_type}強制成行決済処理開始')
        result, order_flag = self.enforce_settlement(trade_password)
        self.log.info(f'{trade_type}強制成行決済処理仮終了')

        # 処理にすべて成功し、追加で注文や注文キャンセルを行っていない(=もうない)場合は処理終了
        if result == True and order_flag == False:
            self.log.info(f'{trade_type}強制成行決済処理終了 対象なし')
            return
        else:
            # 5秒待機してから再チェック
            time.sleep(5)
            self.log.info(f'{trade_type}強制成行決済処理最終チェック開始')
            result, order_flag = self.enforce_settlement(trade_password)
            self.log.info(f'{trade_type}強制成行決済処理最終チェック開始')
            if result == True and order_flag == False:
                self.log.info(f'{trade_type}全強制決済処理正常終了')
                return
            else:
                self.log.error('一部決済処理がエラー/すり抜けで残ったままになっている可能性があります')
                return

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
            'Password': trade_password,    # TODO ここはKabuStationではなくカブコムの取引パスワード
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

    def get_today_order(self, symbol = None, side = None, cashmargin = None):
        '''
        今日の信用取引の一覧を取得する

        Args:
            symbol(str): 証券コードで絞り込み ※省略可
                ※証券コード@市場コード の形式で指定必要
            side(str): 売買区分で絞り込み ※省略可
                '1': 売注文、'2': 買注文
            cashmargin(str): 信用区分で絞り込み ※省略可
                '2': 新規注文、'3': 返済注文

        Returns:
            result(bool): 実行結果
            response.content(list[dict{},dict{},...]): 取得した注文情報 or エラーメッセージ(str)

        Memo:
            信用注文区分: デイトレ信用 での絞り込みはできない
            受け取ったレスポンスのパラメータから判断する必要がある

        '''
        # 絞り込みのためのフィルター
        search_filter = {
            #'detail': False, # 注文の詳細を表示しない
            'product': '2', # 信用
            'updtime': self.util.culc_time.get_now().strftime('%Y%m%d000000') # 今日の00:00:00以降(=今日の取引)のみ抽出
        }

        if symbol != None: search_filter['symbol'] = str(symbol)
        if side != None: search_filter['side'] = side
        if cashmargin != None: search_filter['cashmargin'] = cashmargin

        return self.api.info.orders(search_filter)

    def get_today_position(self, symbol = None, side = None):
        '''
        信用の保有株一覧を取得する

        Args:
            symbol(str): 証券コードで絞り込み ※省略可
            side(str): 売買区分で絞り込み ※省略可
                '1': 売注文、'2': 買注文

        Returns:
            result(bool): 実行結果
            response.content(list[dict{},dict{},...]): 取得した保有株情報 or エラーメッセージ(str)

        Memo:
            信用注文区分: デイトレ信用 での絞り込みはできない
            受け取ったレスポンスのパラメータから判断する必要がある

        '''
        # 絞り込みのためのフィルター
        search_filter = {
            'product': '2', # 信用区分 - 信用
        }

        if symbol != None: search_filter['symbol'] = symbol
        if side != None: search_filter['side'] = side

        return self.api.info.positions(search_filter)

    def board_analysis(self, board_info):
        '''
        板情報を分析する

        Args:
            board_info(dict): 板情報

        Returns:
            border_detail_info(dict): 分析した板情報
                now_price(float): 現在株価
                buy_price(float): 最良売値
                sell_price(float): 最良買値
                empty_board_num(float): 空いている板数
                TODO そのうち別の項目も追加

        '''
        board_detail_info = {}

        # 想定外の値が入ることも考えて念のためtry-except
        try:
            # 現在株価、最良[購入/売却]価格
            board_detail_info['now_price'] = board_info['CurrentPrice']
            board_detail_info['buy_price'] = board_info['Buy1']['Price']
            board_detail_info['sell_price'] = board_info['Sell1']['Price']

            # 買い板と売り板の間に何枚空板があるかチェック
            result, board_num = self.util.stock_price.get_empty_board(yobine_group = self.stock_info['yobine_group'],
                                                                      upper_price = board_detail_info['sell_price'],
                                                                      lower_price = board_detail_info['buy_price'])
            if result == True:
                board_detail_info['empty_board_num'] = board_num
            else:
                self.log.error(board_num)
                board_detail_info['empty_board_num'] = -1

            return board_detail_info
        except Exception as e:
            self.log.error(f'板情報分析処理でエラー\n{e}')
            return False

    def buy_order(self, stock_price):
        '''
        Xpips下に買い注文を入れる

        Args:
            stock_price(float): 基準価格

        Returns:
            bool: 実行結果
            order_price(float): 購入価格

        '''
        self.log.info(f'買い注文処理開始 基準価格: {stock_price}円')

        # Xpip下の価格を計算する
        result, order_price = self.util.stock_price.get_updown_price(yobine_group = self.stock_info['yobine_group'], # 呼値グループ
                                                                     stock_price = stock_price,
                                                                     pips = self.order_line,
                                                                     updown = 0)
        if result == False:
            self.log.error(order_price)
            return False, None

        self.log.info(f'注文価格: {order_price}')

        # 実際に投げる注文のフォーマット(POSTパラメータ)を作成する
        result, order_info = self.util.mold.create_order_request(
                password = self.trade_password,     # 取引パスワード
                stock_code = self.stock_code,       # 証券コード
                exchange = self.market_code,        # 市場コード
                side = 2,                           # 売買区分 2: 買い注文
                cash_margin = 2,                    # 信用区分 2: 新規
                margin_trade_type = 3,              # 信用取引区分 3: 一般信用(デイトレ)
                deliv_type = 0,                     # 受渡区分 0: 指定なし
                account_type = 4,                   # 口座種別 4: 特定口座
                qty = self.stock_info['unit_num'],  # 注文株数 1単元の株数
                front_order_type = 20,              # 執行条件 20: 指値
                price = order_price,                # 執行価格 買い板の最高価格-Xpips
                expire_day = 0,                     # 注文有効期限 0: 当日中
                fund_type = '11'                    # 資産区分 '11': 信用取引
        )

        if result == False:
            self.log.error(response)
            return False, None

        # 注文APIへリクエストを投げる
        result, response = self.api.order.stock(order_info = order_info)

        if result == False:
            self.log.error(f'買い注文処理でエラー\n{response}')
            return False, None

        self.log.info(f'買い注文処理成功 注文価格: {order_info["Price"]}円 株数: {self.stock_info["unit_num"]}株')
        return True, order_price

    def sell_secure_order(self, qty, stock_price):
        '''
        利確の売り注文を入れる

        Args:
            qty(int): 注文株数
            stock_price(float): 基準価格

        Returns:
            bool: 実行結果

        '''
        self.log.info(f'利確売り注文処理開始 基準価格: {stock_price}円')

        # 利確価格(Xpips上)を計算する
        result, order_price = self.util.stock_price.get_updown_price(yobine_group = self.stock_info['yobine_group'], # 呼値グループ
                                                                     stock_price = stock_price,
                                                                     pips = self.securing_benefit,
                                                                     updown = 1)

        if result == False:
            self.log.error(order_price)
            return False

        self.log.info(f'利確価格: {order_price}')

        # 売り注文のフォーマットを作る
        result, order_info = self.util.mold.create_order_request(
                            password = self.trade_password,
                            stock_code = self.stock_code,
                            exchange = self.market_code,
                            side = 1,                      # 売買区分 1: 売
                            cash_margin = 3,               # 信用区分 3: 信用返済
                            margin_trade_type = 3,         # 信用取引区分 3: 一般信用(デイトレ)
                            deliv_type = 2,                # 資金受渡区分 2: お預かり金(0: 指定なし だとエラー)
                            account_type = 4,              # 口座種別 4: 特定口座
                            qty = qty,                     # 注文株数
                            front_order_type = 20,         # 執行条件 20: 指値
                            price = order_price,           # 執行価格 利確価格
                            expire_day = 0,                # 注文有効期限 0: 当日中
                            close_position_order = 0      # 決済順序 何選んでも変わらない
        )

        if result == False:
            self.log.error(order_info)
            return False

        # 注文APIへリクエストを投げる
        result, response = self.api.order.stock(order_info = order_info)

        if result == False:
            self.log.error(f'利確売り注文処理でエラー\n{response}')
            return False

        self.log.info(f'利確売り注文処理成功 注文価格: {order_price}')
        return True

    def sell_cut_order(self, qty, order_price):
        '''
        損切りの売り注文を入れる

        Args:
            qty(int): 注文株数
            order_price(float): 損切り価格

        Returns:
            bool: 実行結果

        '''
        self.log.info(f'損切り売り注文処理開始 損切り価格: {order_price}')

        # 売り注文のフォーマットを作る
        result, order_info = self.util.mold.create_order_request(
                            password = self.trade_password,
                            stock_code = self.stock_code,
                            exchange = self.market_code,
                            side = 1,                      # 売買区分 1: 売
                            cash_margin = 3,               # 信用区分 3: 信用返済
                            margin_trade_type = 3,
                            deliv_type = 2,                # 資金受渡区分 2: お預かり金(0: 指定なし だとエラー)
                            account_type = 4,              # 口座種別 4: 特定口座
                            qty = qty,                     # 注文株数
                            front_order_type = 20,         # 執行条件 20: 指値
                            price = order_price,           # 執行価格 利確価格
                            expire_day = 0,                # 注文有効期限 0: 当日中
                            close_position_order = 0       # 決済順序 何選んでも変わらない
        )

        if result == False:
            self.log.error(order_info)
            return False

        # 注文APIへリクエストを投げる
        result, response = self.api.order.stock(order_info = order_info)

        if result == False:
            self.log.error(f'損切り売り注文処理でエラー\n{response}')
            return False

        self.log.info(f'損切り売り注文処理成功 注文価格: {order_price}')
        return True