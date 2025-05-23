
class StockPrice():
    '''株価について計算するクラス'''

    def __init__(self, log):
        self.log = log
        self.yobine_group = 0
        self.yobine_list = []

    def set_yobine_group(self, yobine_group):
        '''
        KabusAPIで設定している独自の呼値グループIDをインスタンス変数に設定する

        Args:
            yobine_group(int or str): 銘柄の種類 ※エンドポイント /symbol/{証券コード} から取得可

        '''
        self.yobine_group = yobine_group

    def set_yobine_list(self, lower_price, upper_price, yobine_group = None):
        '''
        指定した銘柄の値幅上限から下限までの価格をlistにする

        Args:
            lower_price(float): 値幅下限(S安価格)
            upper_price(float): 値幅上限(S高価格)
            yobine_group(int or str): 呼値グループ

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''
        # 引数に指定がなければインスタンス変数から取得
        if yobine_group == None:
            yobine_group = self.yobine_group

        # 値幅下限をリストにセット
        yobine_list = [lower_price]
        tmp_price = lower_price

        while True:
            # 基準価格の呼値を取得
            yobine = self.get_price_range(yobine_group, tmp_price)
            # 基準価格 + 呼値を計算してリストに挿入
            next_price = tmp_price + yobine

            # 丸め誤差修正
            next_price = self.polish_price(next_price, yobine)

            if next_price == False:
                return False, f'呼値計算に失敗しました。呼値グループ: {yobine_group}、基準価格: {tmp_price}'

            if next_price < upper_price:
                yobine_list.append(next_price)
                tmp_price = next_price
            elif next_price == upper_price:
                yobine_list.append(next_price)
                break
            else:
                break

        self.yobine_list = yobine_list
        return True, None

    def get_price_range(self, yobine_group, price):
        '''
        指定した銘柄の呼値を取得する

        Args:
            yobine_group(int or str): 銘柄の種類 ※エンドポイント /symbol/{証券コード} から取得可
            price(float): 判定したい株価

            price_range(float) or False: 呼値
        '''
        # エンドポイントの返り値をそのまま引数に充てるとstrなのでintに変換する
        yobine_group = int(yobine_group)

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

        # yobine_groupが見つからない場合
        if yobine_group not in price_ranges:
            return False

        for limit, range_value in price_ranges[yobine_group]:
            if price + 0.1 <= limit:
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
                ※指定価格の板はカウントしない 同一価格が指定された場合は-1を返す

        '''
        # 同価格チェック
        if upper_price == lower_price:
            return True, -1

        # 間に挟まる板の数をカウント
        board_num = -1

        tmp_lower_price = lower_price

        while True:
            # 呼値の取得
            sell_yobine = self.get_price_range(yobine_group, tmp_lower_price)

            # 最低価格に呼値を足していく
            tmp_lower_price += sell_yobine

            # 丸め誤差修正
            tmp_lower_price = self.polish_price(tmp_lower_price, sell_yobine)

            board_num += 1

            # 最高価格と加算された最低価格が一致したら終了
            if upper_price == tmp_lower_price:
                return True, board_num

            # 加算された最低価格が最低価格を超えたら不整合
            if upper_price < tmp_lower_price:
                error_message = f'呼値チェック処理で不整合\n呼値グループ: {yobine_group}、呼値: {sell_yobine}円、最高価格: {upper_price}円、最低価格: {lower_price}円'
                return False, error_message

    def get_updown_price(self, stock_price, pips, updown, yobine_group = None):
        '''
        指定した価格のXpips上/下の価格を返す

        Args:
            stock_price(float): 基準価格
            pips(int): 何pips上/下の価格を返すか
            updown(int): 上を返すか下を返すか
                1: 上、0: 下
            yobine_group(int): 銘柄の種類 ※呼値算出に使用。エンドポイント /symbol/{証券コード} から取得可

        Returns:
            result(bool): 不整合がないか
            stock_price: Xpips上/下の価格
        '''
        # 引数に指定がなければインスタンス変数から取得
        if yobine_group == None:
            yobine_group = self.yobine_group

        # 注文可能価格のリストから一致する要素番号を取得
        try:
            index = yobine_group.index(stock_price)
        except ValueError:
            return False, f'基準価格が注文可能価格内に見つかりません。基準価格: {stock_price}、注文可能価格: {yobine_group}'

        if updown == 1:
            new_index = index + pips
        else:
            new_index = index - pips

        # 気配の上限を超える場合は上限を返す TODO 引数で制御できるように
        if new_index >= len(yobine_group):
            return True, yobine_group[-1]

        # 気配の下限を下回る場合は下限を返すように TODO 引数で制御できるように
        if new_index < 0:
            return True, yobine_group[0]

        return True, yobine_group[new_index]

    def polish_price(self, price, yobine):
        '''
        計算結果の丸め誤差などを修正する

        Args:
            price(int or float): 修正対象の株価
            yobine(int or float): 呼値

        Return:
            accurate_price(int or float): 正確な株価
        '''
        # 丸め誤差修正
        # 呼値が小数の場合は小数点下2桁で四捨五入
        if yobine < 1:
            accurate_price = round(price, 1)
        else:
            accurate_price = round(price, 0)

        # データ型修正
        # int変換可能な値の場合は変換する
        if isinstance(accurate_price, float) and accurate_price.is_integer():
            accurate_price = int(accurate_price)

        return accurate_price