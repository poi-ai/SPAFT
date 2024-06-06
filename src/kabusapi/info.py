import json
import requests
import traceback
import urllib.parse

class Info():
    '''市場の情報を取得するAPI'''
    def __init__(self, api_headers, api_url, log):
        self.api_headers = api_headers
        self.api_url = api_url
        self.log = log

    def board(self, stock_code, market_code = 1, add_info = True):
        '''
        指定した銘柄の板・取引情報を取得する

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」

        Returns:
            result(bool): 実行結果
            response.content(dict): 指定した銘柄の板情報
                Symbol(str): 証券コード
                SymbolName(str): 銘柄名
                Exchange(int): 市場コード
                    1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
                ExchangeName(str): 市場名称
                CurrentPrice(float): 現在株価
                CurrentPriceTime(str): 直近約定時刻
                CurrentPriceChangeStatus(str): 一取引前からの変動情報
                    0000: 存在しない、0056: 変動なし、0057: 上昇、0058: 下落、0059: 中断板寄り(連続気配など)後の初値、
                    0060: ザラ場引け、0061: 板寄せ引け(板寄せで決定した株価以降取引なく引け)、
                    0062: 中断引け(連続気配などを保ったまま引け)、
                    0063: ダウン引け(?TODO)、0064: 逆転終値(条件付き引け注文により気配と逆の価格で引け、現在は存在しない)、
                    0066: 特別気配引け、0067: 一時留保(誤発注時に取引所が一時的売買停止したまま)引け
                    0068: 売買停止引け、0069: サーキットブレーカ引け
                CurrentPriceStatus(int): 現在状況
                    1: 現在値で取引成立、2:不連続歩み(?TODO)、3: 板寄せ(?TODO)、4: システム障害、5: 中断(?TODO)、
                    6: 売買停止、7: 売買停止解除・システム停止解除、8: 終値で取引成立、9: システム停止、
                    10: 概算値(?TODO)、11: 参考値(?TODO)、12: サーキットブレイク発動中、13:システム障害解除、
                    14: サーキットブレイク解除、15: 中断解除、16: 一時保留中、17: 一時保留解除、18: ファイル障害、
                    19: ファイル障害解除、20: Spread/Strategy(?)、21: ダイナミックサーキットブレーク発動中、
                    22: ダイナミックサーキットブレーク解除、23: 板寄せ約定
                CalcPrice(float): 計算用現在値(?TODO)
                PreviousClose(float): 前日終値
                PreviousCloseTime(str): 前日終値日付
                ChangePreviousClose(float): 前日比株価
                ChangePreviousClosePer(float): 騰落率
                OpeningPrice(float): 始値
                OpeningPriceTime(str): 始値時刻
                HighPrice(float): 高値
                HighPriceTime(str): 高値時刻
                LowPrice(float): 安値
                LowPriceTime(str): 安値時刻
                TradingVolume(float): 売買高 (1約定？1営業日？ TODO)
                TradingVolumeTime(str): 売買高時刻 (直近約定時間? TODO)
                VWAP(double): 売買高加重平均価格(VWAP)
                TradingValue(double): 売買代金 (1約定？1営業日？ TODO)
                BidQty(float): 最良売気配数量
                BidPrice(float): 最良売気配値段
                BidTime(str): 最良売気配時刻 ※株式のみ
                BidSign(str): 最良売気配フラグ
                    0000: 事象なし、0101: 一般気配、0102: 特別気配、0103: 注意気配、0107: 寄前気配、
                    0108: 停止前特別気配、0109: 引け後気配、0116: 寄前気配約定成立ポイントなし、
                    0117: 寄前気配約定成立ポイントあり、0118: 連続約定気配、0119: 停止前の連続約定気配、
                    0120: 買い上がり売り下がり中
                MarketOrderSellQty(float): 売成行数量 ※株式のみ
                Sell1(object): 売気配データ
                    Time(str): 時刻 TODO
                    Sign(str): 気配フラグ
                        0000: 事象なし、0101: 一般気配、0102: 特別気配、0103: 注意気配、0107: 寄前気配、
                        0108: 停止前特別気配、0109: 引け後気配、0116: 寄前気配約定成立ポイントなし、
                        0117: 寄前気配約定成立ポイントあり、0118: 連続約定気配、0119: 停止前の連続約定気配、
                        0120: 買い上がり売り下がり中
                    Price(double): 値段
                    Qty(double): 数量
                Sell2 ~ sell10(object): 売気配データ
                    Price(double): 値段
                    Qty(double): 数量
                AskQty(float): 最良買気配数量
                AskPrice(float): 最良買気配値段
                AskTime(str): 最良買気配時刻 ※株式のみ
                AskSign(str): 最良買気配フラグ
                    0000: 事象なし、0101: 一般気配、0102: 特別気配、0103: 注意気配、0107: 寄前気配、
                    0108: 停止前特別気配、0109: 引け後気配、0116: 寄前気配約定成立ポイントなし、
                    0117: 寄前気配約定成立ポイントあり、0118: 連続約定気配、0119: 停止前の連続約定気配、
                    0120: 買い上がり売り下がり中
                MarketOrderBuyQty(float): 買成行数量 ※株式のみ
                Buy1(object): 買気配データ
                    Time(str): 時刻 TODO
                    Sign(str): 気配フラグ TODO
                        0000: 事象なし、0101: 一般気配、0102: 特別気配、0103: 注意気配、0107: 寄前気配、
                        0108: 停止前特別気配、0109: 引け後気配、0116: 寄前気配約定成立ポイントなし、
                        0117: 寄前気配約定成立ポイントあり、0118: 連続約定気配、0119: 停止前の連続約定気配、
                        0120: 買い上がり売り下がり中
                    Price(double): 値段
                    Qty(double): 数量
                Buy2 ~ Buy10(object): 買気配データ
                    Price(double): 値段
                    Qty(double): 数量
                OverSellQty(float): OVER気配数量 ※株式のみ
                UnderBuyQty(float): UNDER気配数量 ※株式のみ
                TotalMarketValue(float): 時価総額 ※株式のみ
                ClearingPrice(float): 清算値 ※先物のみ
                IV(float): インプライド・ボラティリティ ※オプション日通しのみ
                Gamma(float): ガンマ ※オプション日通しのみ
                Theta(float): セータ ※オプション日通しのみ
                Vega(float): ベガ ※オプション日通しのみ
                Delta(float): デルタ ※オプション日通しのみ
                SecurityType(int): 銘柄種別
                    0: 指数、1: 現物、101: 日経225先物、103: 日経225OP、107: TOPIX先物、121: JPX400先物、
                    144: NYダウ、145: 日経平均VI、154: 東証マザーズ指数先物、155: TOPIX_REIT、
                    171: TOPIX CORE30、901: 日経平均225ミニ先物、907: TOPIXミニ先物
        '''
        url = f'{self.api_url}/board/{stock_code}@{market_code}'

        if not add_info: url += '?add_info=false'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            return False, e

        if response.status_code != 200:
            if response.status_code == 400:
                error_code = json.loads(response.content)['Code']

                # 板情報を取得した際に勝手に銘柄登録され、
                # 登録数が50銘柄超えて新たに新規銘柄の板情報を指定しようとするとエラーが出るクソ仕様
                # そのためこのエラーの場合はFalseではなくエラーコードの4002006を返す
                if error_code == 4002006:
                    return False, 4002006

                # 銘柄が見つからない場合は見つからない場合はエラーコード4002001を返す
                if error_code == 4002001:
                    return False, 4002001

                # 未知のエラーコードの場合エラーコードのみ返す
                else:
                    return False, f'エラーコード: {error_code}'

            # 400以外のエラーコードの場合
            else:
                return False, f'ステータスコード: {response.status_code}\n{json.loads(response.content)}'

        return True, response.content

    def symbol(self, stock_code, market_code, add_info = True):
        '''
        指定した銘柄の情報を取得する

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」

        Returns:
            response_content: 指定した銘柄の情報
                Symbol(str): 証券コード
                SymbolName(str): 銘柄名
                DisplayName(str): 銘柄略称
                Exchange(int): 市場コード
                    1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
                BisCategory(str): 業種コード
                    0050: 水産・農林業、1050: 鉱業、2050: 建設業、3050: 食料品、3100: 繊維製品、3150: パルプ・紙、
                    3200: 化学、3250: 医薬品、3300: 石油・石炭製品、3350: ゴム製品、3400: ガラス・土石製品、
                    450: 鉄鋼、3500: 非鉄金属、3550: 金属製品、3600: 機械、3650: 電気機器、3700: 輸送用機器、
                    3750: 精密機器、3800: その他製品、4050: 電気・ガス業、5050: 陸運業、5100: 海運業、5150: 空運業、
                    5200: 倉庫・運輸関連業、5250: 情報・通信業、6050: 卸売業、6100: 小売業、7050: 銀行業、7100: 証券・商品先物取引業、
                    7150: 保険業、7200: その他金融業、8050: 不動産業、9050: サービス業、9999: その他
                TotalMarketValue(float): 時価総額 ※株式のみ
                TotalStocks(float): 発行済み株式数(千株) ※株式のみ
                TradingUnit(float): 売買単位
                FiscalYearEndBasic(int): 決算期日
                PriceRangeGroup(str): 呼値(=1pips)グループ
                    10000: 株式(TOPIX100採用銘柄以外)、10003: 株式(TOPIX100採用銘柄)、10118: 日経平均先物、
                    10119: 日経225mini10318: 日経平均オプション、10706: ﾐﾆTOPIX先物、10718: TOPIX先物、
                    12122: JPX日経400指数先物、14473: NYダウ先物、14515: 日経平均VI先物、15411: 東証マザーズ指数先物、
                    15569: 東証REIT指数先物、17163: TOPIXCore30指数先物
                KCMarginBuy(bool): 一般信用(長期・デイトレ)買建可能フラグ ※株式のみ
                KCMarginSell(bool): 一般信用(長期・デイトレ)売建可能フラグ ※株式のみ
                MarginBuy(bool): 制度信用買建可能フラグ ※株式のみ
                MarginSell(bool): 制度信用売建可能フラグ ※株式のみ
                UpperLimit(float): 値幅上限
                LowerLimit(float): 値幅下限
                Underlyer(str): 原資産コード ※先物・オプションのみ
                    NK225: 日経225、NK300: 日経300、MOTHERS: 東証マザーズ、JPX400: JPX日経400、TOPIX: TOPIX、
                    NKVI: 日経平均VI、DJIA: NYダウ、TSEREITINDEX: 東証REIT指数、TOPIXCORE30: TOPIX Core30
                DerivMonth(str): 限月-年月 ※先物・オプションのみ
                TradeStart(int): 取引開始日 ※先物・オプションのみ
                TradeEnd(int): 取引終了日 ※先物・オプションのみ
                StrikePrice(double): 権利行使価格 ※オプションのみ
                PutOrCall(int): プット/コール区分 ※オプションのみ
                    1: プット、2: コール
                ClearingPrice(float): 清算値 ※先物のみ
            ※取得失敗時はFalseを返す
        '''
        url = f'{self.api_url}/symbol/{stock_code}@{market_code}'

        if not add_info: url += '?add_info=false'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'銘柄情報取得処理でエラー\n証券コード: {stock_code}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            if response.status_code == 400:
                # 板情報を取得した際に勝手に銘柄登録され、
                # 登録数が50銘柄超えて新たに新規銘柄の板情報を指定しようとするとエラーが出るクソ仕様
                # そのためこのエラーの場合はFalseではなく999を返す
                if self.byte_to_dict(response.content)['Code'] == 4002006:
                    self.logger.warning(f'銘柄情報取得処理で登録数上限エラー\n証券コード: {stock_code}')
                    return 4002006

                # 銘柄が見つからない場合は見つからない場合はそのエラーコードを返す
                if self.byte_to_dict(response.content)['Code'] == 4002001:
                    self.logger.warning(f'銘柄情報取得処理で銘柄未発見エラー\n証券コード: {stock_code}')
                    return 4002001

            self.log.error(f'銘柄情報取得処理でエラー\n証券コード: {stock_code}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        return response.content

    def orders(self, search_filter = None):
        '''
        約定状況を取得する
        引数指定なしで全ての状況を取得、引数指定で絞り込み可
        Args:
            search_filter(dict): 絞り込む検索条件[任意]
                product(str): 商品区分
                    0: すべて、1: 現物、2: 信用、3: 先物、4: オプション
                id(str): 注文番号
                uptime(string、yyyyMMddHHss): 更新日時 この日時以降の注文を取得
                details(str): 注文詳細取得
                    True: 取得する、False: 取得しない
                symbol(str): 銘柄コード
                state(str): 取引状態
                    1: 待機（発注待機）、2: 処理中（発注送信中）、3: 処理済（発注済・訂正済）
                    4: 訂正・取消送信中、5: 終了（発注エラー・取消済・全約定・失効・期限切れ）
                side(str): 売買区分
                    1: 売、2: 買
                cashmargin(str): 取引区分
                    2: 新規、3: 返済

        Returns:
            response.content (list[dict{},dict{},...])
                ID(str): 注文番号
                State(int): 状態 ※Order Stateと同値
                OrderState(int): 注文状態 ※Stateと同値
                    1: 待機（発注待機）、2: 処理中（発注送信中）、3: 処理済（発注済・訂正済）、
                    4: 訂正取消送信中、5: 終了（発注エラー・取消済・全約定・失効・期限切れ）
                OrdType(int): 執行条件
                    1: ザラバ、2: 寄り、3: 引け、4: 不成、5: 対当指値、6: IOC
                RecvTime(str): 受注日時
                Symbol(str): 証券コード
                SymbolName(str): 銘柄名
                Exchange(int): 市場コード
                    1: 東証、3: 名証、5: 福証、6: 札証、9: SOR、2: 日通し、23: 日中、24: 夜間
                ExchangeName(str): 市場名称
                TimeInForce(int): 有効期間条件 ※オプションのみ
                    1: FAS、2: FAK、3: FOK、
                Price(float): 注文価格
                OrderQty(float): 失効分を除く発注数量
                CumQty(float): 約定数量
                Side(str): 売買区分
                    1: 売、2: 買
                CashMargin(int): 取引区分
                    2: 新規、3: 返済
                AccountType(int): 口座種別
                    2: 一般、4: 特定、12: 法人
                DelivType(int): 受渡区分
                    1: 自動振替、2: お預り金、3: auマネーコネクト
                ExpireDay(int、yyyyMMdd): 注文有効期限
                MarginTradeType(int): 信用取引区分 ※信用のみ
                    1: 制度信用、2: 一般信用（長期）、3: 一般信用（デイトレ）
                MarginPremium(float): 発注分含むプレミアム料 ※信用買はNone、信用売の手数料なしは0を返す
                Details(list[dict{}, dict{},...] or dict{}): 注文詳細
                    SeqNum(int): 注文シーケンス番号
                    ID(str): 注文詳細番号
                    RecType(int): 明細種別
                        1: 受付、2: 繰越、3: 期限切れ、4: 発注、5: 訂正、6: 取消、7: 失効、8: 約定
                    ExchangeID(int): 取引所番号
                    State(int): 状態
                        1: 待機（発注待機）、2: 処理中（発注送信中・訂正送信中・取消送信中）、
                        3: 処理済（発注済・訂正済・取消済・全約定・期限切れ）、4: エラー、5: 削除済み
                    TransactTime(str): 処理時刻
                    OrdType(int): 執行条件
                        Null: 注文取消の場合、0: 注文期限切れ、失効、約定 の場合、1: ザラバ、2: 寄り、
                        3: 引け、4: 不成、5: 対当指値、6: IOC
                    Price (float): 注文価格
                    Qty(number): 数量
                    ExecutionID(str): 約定番号
                    ExecutionDay(str): 約定日時
                    DelivDay(int): 受渡日
                    Commission(float): 手数料
                    CommissionTax(float): 手数料消費税
        '''
        url = f'{self.api_url}/orders/'

        if search_filter != None:
            url = f'{url}?{urllib.parse.urlencode(search_filter)}'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'約定情報取得処理でエラー', e, traceback.format_exc())

        if response.status_code != 200:
            self.log.error(f'約定情報取得処理でエラー\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False
        return response.content

    def positions(self):
        '''残高・評価額を取得する'''
        pass

    def future_code(self):
        '''指定した先物の銘柄コードを取得する'''
        pass

    def option_code(self):
        '''指定したオプションの銘柄コードを取得する'''
        pass

    def ranking(self):
        '''各銘柄のランキングを取得する'''
        pass

    def exchange(self):
        '''為替情報を取得する'''
        pass

    def regurations(self, stock_code, market_code = 1):
        '''
        指定した銘柄の取引規制情報を取得する

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証

        Returns:
            response.content(dict): 指定した銘柄の優先市場情報
                Symbol(str): 証券コード
                RegulationsInfo(list[dict{}, dict{}...]): 取引規制情報
                    Exchange(int): 規制がかかっている市場
                        0: 全市場、1: 東証、3: 名証、5: 福証、6: 札証、9: SOR、10: CXJ、21: JNX
                    Product(int): 規制がかかっている取引
                        0: 全、1: 現物、2: 信用新規(制度)、3: 信用新規(一般)、4: 新規／空売り、5: 信用返済(制度)、
                        6: 信用返済(一般)、7: 返済、8: 品受、9: 品渡
                    Side(str): 規制がかかっている売買
                        0: 全、1: 売、2: 買
                    Reason(str): 規制理由
                    LimitStartDay(str, yyyy/MM/dd HH:mm): 規制開始日
                        ※空売り規制の場合はNULL
                    LimitEndDay(str, yyyy/MM/dd HH:mm): 規制終了日
                        ※空売り規制の場合はNULL
                    Level(int): コンプライアンスレベル
                        0: 規制なし、1: ワーニング、2: エラー
            ※エラー時はFalse
        '''
        url = f'{self.api_url}/regulations/{stock_code}@{market_code}'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'取引規制情報取得処理でエラー\n証券コード: {stock_code}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            if response.status_code == 400:
                # 銘柄が見つからない場合は見つからない場合はそのエラーコードを返す
                if self.byte_to_dict(response.content)['Code'] == 4002001:
                    self.logger.warning(f'取引規制情報取得処理で銘柄未発見エラー\n証券コード: {stock_code}')
                    return 4002001

            self.log.error(f'取引規制情報取得処理でエラー\n証券コード: {stock_code}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        return response.content

    def primary_exchange(self, stock_code):
        '''
        指定した銘柄の優先市場情報を取得する

        Args:
            stock_code(int or string): 証券コード

        Returns:
            response.content(dict): 指定した銘柄の優先市場情報
                Symbol(str): 証券コード
                PrimaryExchange(int): 優先市場
                    1: 東証、3: 名証、5: 福証、6: 札証
            ※エラー時はFalse
        '''
        url = f'{self.api_url}/primaryexchange/{stock_code}'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'優先市場情報取得処理でエラー\n証券コード: {stock_code}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            if response.status_code == 400:
                # 銘柄が見つからない場合は見つからない場合はそのエラーコードを返す
                if self.byte_to_dict(response.content)['Code'] == 4002001:
                    self.logger.warning(f'優先市場情報取得処理で銘柄未発見エラー\n証券コード: {stock_code}')
                    return 4002001

            self.log.error(f'優先市場情報取得処理でエラー\n証券コード: {stock_code}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        return response.content

    def soft_limit(self):
        '''
        kabuステーションで利用者が設定した一注文上限額を取得する

        Returns:
            response.content(dict): 設定した一注文(ワンショット)上限額
                Stock(float): 現物のワンショット上限金額
                Margin(float): 信用のワンショット上限金額
                Future(float): 先物のワンショット上限金額
                FutureMini(float): 先物ミニのワンショット上限金額
                Option(float): オプションのワンショット上限金額
                KabuSVersion(str): kabuステーションのバージョン
        '''
        url = f'{self.api_url}/apisoftlimit'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'設定上限金額情報取得処理でエラー', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'設定上限金額取得処理でエラー\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        return response.content

    def premium_price(self, stock_code):
        '''
        指定した銘柄のプレミアム(空売り)手数料を取得する

        Args:
            stock_code(int or string): 証券コード

        Returns:
            response.content(dict): 指定した銘柄のプレミアム(空売り)手数料データ
                Symbol(str): 証券コード
                GeneralMargin(dict): 一般信用(長期)のデータ
                    MarginPremiumType(int): プレミアム料区分
                        Null: 空売り非対応銘柄、0: プレミアム料がない銘柄、
                        1: プレミアム料が固定の銘柄、2: プレミアム料が入札で決定する銘柄
                    MarginPremium(float): プレミアム料
                    UpperMarginPremium(float): 上限プレミアム料
                    LowerMarginPremium(float): 下限プレミアム料
                    TickMarginPremium(float): プレミアム料刻値
                DayTrade(dict): 一般信用(デイトレ)のデータ
                    MarginPremiumType(int): プレミアム料区分
                        Null: 空売り非対応銘柄、0: プレミアム料がない銘柄、
                        1: プレミアム料が固定の銘柄、2: プレミアム料が入札で決定する銘柄
                    MarginPremium(float): プレミアム料
                    UpperMarginPremium(float): 上限プレミアム料
                    LowerMarginPremium(float): 下限プレミアム料
                    TickMarginPremium(float): プレミアム料刻値
        '''
        url = f'{self.api_url}/margin/marginpremium/{stock_code}'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            self.log.error(f'プレミアム手数料取得処理でエラー\n証券コード: {stock_code}', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'プレミアム手数料取得処理でエラー\n証券コード: {stock_code}\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        return response.content