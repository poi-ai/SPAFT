import traceback
from datetime import datetime

class Mold():
    '''DBやAPIに使うためのデータ整形を行う'''
    def __init__(self, log):
        self.log = log

    def response_to_boards(self, board_info):
        '''
        板情報取得APIで受け取ったレスポンスをboardsテーブルに挿入できる形に変換する

        Args:
            board_info(dict): 板情報

        Returns:
            board_table_info(dict): 変換後の板情報
            ※エラー時はFalseを返す
        '''

        try:
            board_table_info = {
                'stock_code': board_info['Symbol'],
                'market_code': board_info['Exchange'],
                'price': board_info['CurrentPrice'],
                'change_status': board_info['CurrentPriceChangeStatus'][2:],
                'present_status': board_info['CurrentPriceStatus'],
                'market_buy_qty': board_info['MarketOrderBuyQty'],
                'buy1_sign': board_info['Buy1']['Sign'][1:],
                'buy1_price': board_info['Buy1']['Price'],
                'buy1_qty': board_info['Buy1']['Qty'],
                'buy2_price': board_info['Buy2']['Price'],
                'buy2_qty': board_info['Buy2']['Qty'],
                'buy3_price': board_info['Buy3']['Price'],
                'buy3_qty': board_info['Buy3']['Qty'],
                'buy4_price': board_info['Buy4']['Price'],
                'buy4_qty': board_info['Buy4']['Qty'],
                'buy5_price': board_info['Buy5']['Price'],
                'buy5_qty': board_info['Buy5']['Qty'],
                'buy6_price': board_info['Buy6']['Price'],
                'buy6_qty': board_info['Buy6']['Qty'],
                'buy7_price': board_info['Buy7']['Price'],
                'buy7_qty': board_info['Buy7']['Qty'],
                'buy8_price': board_info['Buy8']['Price'],
                'buy8_qty': board_info['Buy8']['Qty'],
                'buy9_price': board_info['Buy9']['Price'],
                'buy9_qty': board_info['Buy9']['Qty'],
                'buy10_price': board_info['Buy10']['Price'],
                'buy10_qty': board_info['Buy10']['Qty'],
                'market_sell_qty': board_info['MarketOrderSellQty'],
                'sell1_sign': board_info['Sell1']['Sign'][1:],
                'sell1_price': board_info['Sell1']['Price'],
                'sell1_qty': board_info['Sell1']['Qty'],
                'sell2_price': board_info['Sell2']['Price'],
                'sell2_qty': board_info['Sell2']['Qty'],
                'sell3_price': board_info['Sell3']['Price'],
                'sell3_qty': board_info['Sell3']['Qty'],
                'sell4_price': board_info['Sell4']['Price'],
                'sell4_qty': board_info['Sell4']['Qty'],
                'sell5_price': board_info['Sell5']['Price'],
                'sell5_qty': board_info['Sell5']['Qty'],
                'sell6_price': board_info['Sell6']['Price'],
                'sell6_qty': board_info['Sell6']['Qty'],
                'sell7_price': board_info['Sell7']['Price'],
                'sell7_qty': board_info['Sell7']['Qty'],
                'sell8_price': board_info['Sell8']['Price'],
                'sell8_qty': board_info['Sell8']['Qty'],
                'sell9_price': board_info['Sell9']['Price'],
                'sell9_qty': board_info['Sell9']['Qty'],
                'sell10_price': board_info['Sell10']['Price'],
                'sell10_qty': board_info['Sell10']['Qty'],
                'over_qty': board_info['OverSellQty'],
                'under_qty': board_info['UnderBuyQty']
            }
            # まだ取引未成立の場合は直近約定日時の置換ができないので別対応
            current_price_time = board_info['CurrentPriceTime']
            if current_price_time == None:
                board_table_info['latest_transaction_time'] = None
            else:
                board_table_info['latest_transaction_time'] = current_price_time.replace('+09:00', '')
        except Exception as e:
            self.log.error(f'板情報取得APIから板情報テーブルへのフォーマット変換処理でエラー', e, traceback.format_exc())
            self.log.error(board_info)
            return False
        return board_table_info

    def response_to_csv(self, board_info):
        '''
        板情報取得APIで受け取ったレスポンスをCSVに記録する形に変換する

        Args:
            board_info(dict): 板情報

        Returns:
            board_info_dict(dict): 変換後の板情報
            ※エラー時はFalseを返す
        '''

        try:
            board_info_dict = {
                'stock_code': board_info['Symbol'], # 証券コード
                'current_price': board_info['CurrentPrice'], # 現在株価
                'current_price_change_status': board_info['CurrentPriceChangeStatus'], # 前の歩み値からの変化
                'current_price_status': board_info['CurrentPriceStatus'], # 現在株価のステータス
                'previous_close': board_info['PreviousClose'], # 前日終値
                'change_previous_close': board_info['ChangePreviousClose'], # 前日比
                'change_previous_close_per': board_info['ChangePreviousClosePer'], # 前日比(%)
                'opening_price': board_info['OpeningPrice'], # 始値
                'high_price': board_info['HighPrice'], # 高値
                'high_price_time': self.format_datetime(board_info['HighPriceTime']), # 高値時刻
                'low_price': board_info['LowPrice'], # 安値
                'low_price_time': self.format_datetime(board_info['LowPriceTime']), # 安値時刻
                'trading_volume': board_info['TradingVolume'], # 出来高
                'VWAP': board_info['VWAP'], # VWAP(売買高加重平均価格)
                'bid_sign': board_info['Sell1']['Sign'], # 売気配フラグ
                'market_order_sell_qty': board_info['MarketOrderSellQty'], # 売成行数量
                'bid_price_1': board_info['Sell1']['Price'], # 売気配価格1(最良気配)
                'bid_qty_1': board_info['Sell1']['Qty'], # 売気配数量1(最良気配)
                'bid_price_2': board_info['Sell2']['Price'], # 売気配価格2(2番目に安い価格)
                'bid_qty_2': board_info['Sell2']['Qty'], # 売気配数量2(2番目に安い価格)
                'bid_price_3': board_info['Sell3']['Price'], # 売気配価格3(3番目に安い価格)
                'bid_qty_3': board_info['Sell3']['Qty'], # 売気配数量3(3番目に安い価格)
                'bid_price_4': board_info['Sell4']['Price'], # 売気配価格4(4番目に安い価格)
                'bid_qty_4': board_info['Sell4']['Qty'], # 売気配数量4(4番目に安い価格)
                'bid_price_5': board_info['Sell5']['Price'], # 売気配価格5(5番目に安い価格)
                'bid_qty_5': board_info['Sell5']['Qty'], # 売気配数量5(5番目に安い価格)
                'bid_price_6': board_info['Sell6']['Price'], # 売気配価格6(6番目に安い価格)
                'bid_qty_6': board_info['Sell6']['Qty'], # 売気配数量6(6番目に安い価格)
                'bid_price_7': board_info['Sell7']['Price'], # 売気配価格7(7番目に安い価格)
                'bid_qty_7': board_info['Sell7']['Qty'], # 売気配数量7(7番目に安い価格)
                'bid_price_8': board_info['Sell8']['Price'], # 売気配価格8(8番目に安い価格)
                'bid_qty_8': board_info['Sell8']['Qty'], # 売気配数量8(8番目に安い価格)
                'bid_price_9': board_info['Sell9']['Price'], # 売気配価格9(9番目に安い価格)
                'bid_qty_9': board_info['Sell9']['Qty'], # 売気配数量9(9番目に安い価格)
                'bid_price_10': board_info['Sell10']['Price'], # 売気配価格10(10番目に安い価格)
                'bid_qty_10': board_info['Sell10']['Qty'], # 売気配数量10(10番目に安い価格)
                'over_sell_qty': board_info['OverSellQty'], # OVER売気配数量
                'ask_sign': board_info['Buy1']['Sign'], # 買気配フラグ
                'market_order_buy_qty': board_info['MarketOrderBuyQty'], # 買成行数量
                'ask_price_1': board_info['Buy1']['Price'], # 買気配価格1(最良気配)
                'ask_qty_1': board_info['Buy1']['Qty'], # 買気配数量1(最良気配)
                'ask_price_2': board_info['Buy2']['Price'], # 買気配価格2(2番目に安い価格)
                'ask_qty_2': board_info['Buy2']['Qty'], # 買気配数量2(2番目に安い価格)
                'ask_price_3': board_info['Buy3']['Price'], # 買気配価格3(3番目に安い価格)
                'ask_qty_3': board_info['Buy3']['Qty'], # 買気配数量3(3番目に安い価格)
                'ask_price_4': board_info['Buy4']['Price'], # 買気配価格4(4番目に安い価格)
                'ask_qty_4': board_info['Buy4']['Qty'], # 買気配数量4(4番目に安い価格)
                'ask_price_5': board_info['Buy5']['Price'], # 買気配価格5(5番目に安い価格)
                'ask_qty_5': board_info['Buy5']['Qty'], # 買気配数量5(5番目に安い価格)
                'ask_price_6': board_info['Buy6']['Price'], # 買気配価格6(6番目に安い価格)
                'ask_qty_6': board_info['Buy6']['Qty'], # 買気配数量6(6番目に安い価格)
                'ask_price_7': board_info['Buy7']['Price'], # 買気配価格7(7番目に安い価格)
                'ask_qty_7': board_info['Buy7']['Qty'], # 買気配数量7(7番目に安い価格)
                'ask_price_8': board_info['Buy8']['Price'], # 買気配価格8(8番目に安い価格)
                'ask_qty_8': board_info['Buy8']['Qty'], # 買気配数量8(8番目に安い価格)
                'ask_price_9': board_info['Buy9']['Price'], # 買気配価格9(9番目に安い価格)
                'ask_qty_9': board_info['Buy9']['Qty'], # 買気配数量9(9番目に安い価格)
                'ask_price_10': board_info['Buy10']['Price'], # 買気配価格10(10番目に安い価格)
                'ask_qty_10': board_info['Buy10']['Qty'], # 買気配数量10(10番目に安い価格)
                'under_buy_qty': board_info['UnderBuyQty'], # UNDER売気配数量
                'get_year': board_info['get_time'].year, # 取得年
                'get_month': board_info['get_time'].month, # 取得月
                'get_day': board_info['get_time'].day, # 取得日
                'get_hour': board_info['get_time'].hour, # 取得時
                'get_minute': board_info['get_time'].minute # 取得分
            }
        except Exception as e:
            self.log.error(f'板情報取得APIからCSV記録用フォーマット変換処理でエラー', e, traceback.format_exc())
            self.log.error(board_info)
            return False
        return board_info_dict

    def create_order_request(self, password, stock_code, exchange, side, cash_margin,
            deliv_type, account_type, qty, front_order_type, price,
            expire_day, margin_trade_type = None, margin_premium_unit = None,
            fund_type = None, close_position_order = None,
            close_positions = None, reverse_limit_order = None):
        '''
        注文APIで使用するリクエストのPOSTデータを作成する

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
            close_position_order(int): 決済順序 [任意] ※信用返済の場合close_positionsとどっちかが必須
                0: 日付(古い順)、損益(高い順)、1: 日付(古い順)、損益(低い順)、2: 日付(新しい順)、損益(高い順)、
                3: 日付(新しい順)、損益(低い順)、4: 損益(高い順)、日付(古い順)、5: 損益(高い順)、日付(新しい順)、
                6: 損益(低い順)、日付(古い順)、7: 損益(低い順)、日付(新しい順)
            close_positions(array[dict, dict] or dict): 信用返済 [任意] ※信用返済の場合close_position_orderとどっちか必須
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
            result(bool): 実行結果
            data(dict): 加工注文データ 直接これを注文API(/orders)のPOSTパラメータとして設定できる
        '''
        # TODO お金にダイレクトに関わるところだから厳密なバリデーションチェック入れたい

        try:
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

            if margin_trade_type != None: data['MarginTradeType'] = margin_trade_type
            if margin_premium_unit != None: data['MarginPremiumUnit'] = margin_premium_unit
            if fund_type != None: data['FundType'] = fund_type
            if close_position_order != None: data['ClosePositionOrder'] = close_position_order
            if close_positions != None: data['ClosePositions'] = close_positions
            if reverse_limit_order != None: data['ReverseLimitOrder'] = reverse_limit_order

            return True, data
        except Exception as e:
            return False, f'注文APIリクエスト作成処理でエラー\n証券コード: {stock_code}\n{e}'

    def format_datetime(self, datetime_str):
        '''
        日時文字列を整形する

        Args:
            datetime_str(str): 日時文字列

        Returns:
            str: 整形後の日時文字列
        '''
        dt = datetime.fromisoformat(datetime_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')