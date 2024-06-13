
class StockPrice():
    '''株価について計算するクラス'''

    def __init__(self, log):
        self.log = log

    def get_price_range(self, stock_type, price):
        '''
        指定した銘柄の呼値を取得する.

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

from log import Log
s = StockPrice(1)
print(s.get_price_range(10000, 7000))