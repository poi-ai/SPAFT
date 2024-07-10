
class StockPrice():
    '''株価について計算するクラス'''

    def __init__(self, log):
        self.log = log

    def get_price_range(self, stock_type, price):
        '''
        指定した銘柄の呼値を取得する

        Args:
            stock_type(int): 銘柄の種類(/symbol/{証券コード}エンドポイントから取得可)
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
            stock_type(float): 銘柄の種類 ※呼値算出に使用
            upper_price(float): 指定した最高価格、売り注文
            lower_price(float): 指定した最低価格、買い注文

        Returns:
            board_num(int): 最良[売値/買値]価格間の間の板の枚数

        '''
        while True:
            # 呼値の取得
            sell_yobine = self.get_price_range(self.upper_price,) # TODO

            buy_price += sell_yobine
            board_num += 1

            # 買値と売値が一致したら終了
            if buy_price == sell_price:
                break

            # 買値が売値を超えたらエラー 無限ループ防止
            if buy_price > sell_price:
                self.log.error(f'呼値チェック処理で無限ループ 買値: {buy_price}、売値: {sell_price}')
                break

            # 呼値の更新
            sell_yobine = self.util.stock_price.get_price_range(self.stock_code, buy_price)