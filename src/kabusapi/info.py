import requests

class Info():
    '''市場の情報を取得するAPI'''
    def __init__(self, api_headers):
        self.api_headers = api_headers

    def board(self, stock_code, market_code, add_info = True):
        '''
        指定した銘柄の板・取引情報を取得する

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」

        Returns:
            response.content(dict): 指定した銘柄の板情報
                Symbol(str): 証券コード
                SymbolName(str): 銘柄名
                Exchange(int): 市場コード
                    1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
                ExchangeName(str): 市場名称
                CurrentPrice(float): 現在株価
                CurrentPriceTime(str): 直近約定時刻
                CurrentPriceChangeStatus(str): 一取引前からの変動情報
                    0000: 存在しない、0056: 変動なし、0057: 上昇、0058: 下落、
                    0059: 中断板寄り(連続気配など)後の初値、0060: ザラ場引け、
                    0061: 板寄せ引け(板寄せで決定した株価以降取引なく引け)、
                    0062: 中断引け(連続気配などを保ったまま引け)、
                    0063: ダウン引け(?)、0064: 逆転終値(条件付き引け注文により気配と逆の価格で引け、現在は存在しない)、
                    0066: 特別気配引け、0067: 一時留保(誤発注時に取引所が一時的売買停止したまま)引け
                    0068: 売買停止引け、0069: サーキットブレーカ引け
                TODO 残りのパラメータ

                ※処理失敗時はFalseを返す

        '''
        url = f'http://localhost:18080/board/{stock_code}@{market_code}'

        if not add_info: url += '?add_info=false'

        try:
            response = requests.get(url, headers = self.api_headers)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        return response.content

    def symbol(self):
        '''指定した銘柄の情報を取得する'''
        pass

    def orders(self):
        '''指定した注文番号の約定状況を取得する'''
        pass

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

    def regurations(self):
        '''指定した銘柄の取引規制情報を取得する'''
        pass

    def primary_exchange(self):
        '''指定した銘柄の優先市場情報を取得する'''
        pass

    def soft_limit(self):
        '''kabuステーション®APIの一注文上限額を取得する'''
        pass

    def premium_price(self):
        '''指定した銘柄のプレミアム(空売り追加)手数料を取得する'''
        pass