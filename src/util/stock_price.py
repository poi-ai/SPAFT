
class StockPrice():
    '''株価について計算するクラス'''

    def __init__(self, log):
        self.log = log

    def get_price_range(self, stock_type, price):
        '''
        指定した銘柄の呼値を取得する

        Args:
            stock_type(int): 銘柄の種類 ※エンドポイント /symbol/{証券コード} から取得可
            price(float): 判定したい株価

            price_range(float)or False: 呼値
        '''
        price_ranges = {
            10000: [
                (3000, 1), (5000, 5), (30000, 10), (50000, 50), (300000, 100),
                (500000, 500), (3000000, 1000), (5000000, 5000), (30000000, 10000),
                (50000000, 50000), (float('inf'), 100000)
            ],
            10003: [
                (1000, 0.1), (3000, 0.5), (10000, 1), (30000, 5), (100000, 10),
                (300000, 50), (1000000, 100), (3000000, 500), (10000000, 1000),
                (30000000, 5000), (float('inf'), 10000)
            ],
            10118: [(float('inf'), 10)],
            10119: [(float('inf'), 5)],
            10318: [
                (100, 1), (1000, 5), (float('inf'), 10)
            ],
            10706: [(float('inf'), 0.25)],
            10718: [(float('inf'), 0.5)],
            12122: [(float('inf'), 5)],
            14473: [(float('inf'), 1)],
            14515: [(float('inf'), 0.05)],
            15411: [(float('inf'), 1)],
            15569: [(float('inf'), 0.5)],
            17163: [(float('inf'), 0.5)],
        }

        # stock_typeが見つからない場合
        if stock_type not in price_ranges:
            return False

        for limit, range_value in price_ranges[stock_type]:
            if price <= limit:
                return range_value

        return False

    def get_empty_board(self, yobine_group, upper_price, lower_price):
        '''
        指定した価格間に板が何枚存在するか

        Args:
            yobine_group(int): 銘柄の種類 ※呼値算出に使用。エンドポイント /symbol/{証券コード} から取得可
            upper_price(float): 指定した最高価格 ※基本的には売り板の最低価格
            lower_price(float): 指定した最低価格 ※基本的には買い板の最高価格

        Returns:
            integrity(bool): 整合性が取れているか 呼値10円なのに価格差15円とかになってないか
            board_num(int): 最良[売値/買値]価格間の間の板の枚数
                ※指定価格の板はカウントしない

        '''
        # 間に挟まる板の数をカウント
        board_num = -1

        tmp_lower_price = lower_price

        while True:
            # 呼値の取得
            sell_yobine = self.get_price_range(yobine_group, tmp_lower_price)

            # 最低価格に呼値を足していく
            tmp_lower_price += sell_yobine
            board_num += 1

            # 最高価格と加算された最低価格が一致したら終了
            if upper_price == tmp_lower_price:
                return True, board_num

            # 加算された最低価格が最低価格を超えたら不整合
            if upper_price > tmp_lower_price:
                error_message = f'呼値チェック処理で不整合\n呼値グループ: {yobine_group}、最高価格: {upper_price}、最低価格: {lower_price}'
                return False, error_message

    def get_updown_price(self, yobine_group, stock_price, pips, updown):
        '''
        指定した価格のXpips上/下の価格を返す

        Args:
            yobine_group(int): 銘柄の種類 ※呼値算出に使用。エンドポイント /symbol/{証券コード} から取得可
            stock_price(float): 基準価格
            pips(int): 何pips上/下の価格を返すか
            updown(int): 上を返すか下を返すか
                1: 上、0: 下

        Returns:
            result(bool): 不整合がないか
            stock_price: Xpips上/下の価格

        MEMO:
            思ったけどこれトレード開始前のinitに入れて値幅内全株価リストに持たせとくのもありだな
        '''
        # 計算用変数
        culc_stock_price = stock_price

        # 1pipごと上げ下げして計算する
        for pip in range(pips):
            # 呼値の取得
            yobine = self.get_price_range(yobine_group, culc_stock_price)

            # 1pips上/下の価格に書き換え
            if updown == 1:
                culc_stock_price += yobine
            else:
                culc_stock_price -= yobine

        # 上の計算の場合はこのまま返せる
        if updown == 1:
            return culc_stock_price

        # 下の場合は再計算が必要 ここでの呼値は上に何円空くか で下に何円空くかは判定できない
        # 基本的には価格は高くなるほど呼値も広がるので、上の呼値のpips下げれば包含はできている
        # また、呼値の上がり方は整数倍なのでありえない株価になることもない
        price_list = [culc_stock_price]

        while True:
            # 呼値の取得
            yobine = self.get_price_range(yobine_group, culc_stock_price)

            # 呼値を足していき、リストに追加する
            culc_stock_price += yobine
            price_list.append(culc_stock_price)

            # 基準価格を超えたら終了
            if culc_stock_price > stock_price:
                break

        # 株価を列挙したリストから検索する
        # リストの中に基準価格が存在するかチェック 存在しないことはないはずだが一応
        if stock_price in price_list:
            index = price_list.index(stock_price)
            # リストの要素数が足りなくてpips個下の株価が取得できないかのチェック ここもありえないはず
            if index >= pips:
                return True, price_list[index - pips]
            else:
                return False, f'リストの要素数が足りません\n呼値グループ: {yobine_group}/基準価格: {stock_price}/pips {pips}/updown: {updown}'
        # リストに基準価格がない場合
        else:
            return False, f'リストに基準価額が存在しません\n呼値グループ: {yobine_group}/基準価格: {stock_price}/pips {pips}/updown: {updown}'