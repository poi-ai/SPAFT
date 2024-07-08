import config
import time
from base import Base

class Main(Base):
    def __init__(self):
        # 初期設定
        super().__init__()

        # 取引関連の処理のサービスクラスをインスタンス変数に
        self.logic = self.service.trade

    def main(self):
        self.log.info('SPAFT起動')

        # 成行強制決済のみを行う場合
        if config.RECOVERY_SETTLEMENT:
            result, order_flag = self.logic.enforce_settlement()
            # 実行に失敗した注文が存在するか、注文/注文キャンセルを行った場合
            if result == False or order_flag == True:
                # 10秒待ってもう一度同じ関数の呼び出し,完了していることの確認
                time.sleep(10)
                result, order_flag = self.logic.enforce_settlement()
                if result == False or order_flag == True:
                    return False
            return True

        # トレード開始前の事前準備/チェック
        result = self.logic.scalping_init(config)
        if result == False:
            self.log.info('トレード前の初期処理でエラーが発生したため処理を終了します')
            return False

        # トレードを行う
        self.logic.scalping()

        self.log.info('SPAFT終了')

        '''
        # 板情報取得
        board_info = self.api.info.board(1570, 1)
        board_info = json.loads(board_info)

        # 現在値と最低価格売り注文・最高価格買い注文を取得する
        over_price = board_info["Sell1"]["Price"]
        now_price = board_info["CurrentPrice"]
        under_price = board_info["Buy1"]["Price"]

        # 1570をunder_priceで買い注文
        result = self.api.order.stock(
            stock_code = 1570,
            password = 'p@ssword',
            exchange = 1,
            side = 2,
            cash_margin = 2,
            deliv_type = 0,
            account_type = 4,
            qty = 1,
            front_order_type = 20,
            price = under_price,
            margin_trade_type = 3,
            expire_day = 0,
            fund_type = '11'
        )
        '''
        # 保有中証券のIDを取得
        #now_position = self.api.info.orders()

        #print(now_position)

        #exit()
        # 1570を売り注文 (動作確認済)
        '''
        result = self.api.order.stock(
            stock_code = 1570,
            password = 'p@ssword',
            exchange = 1,
            side = 1,
            cash_margin = 3,
            deliv_type = 2,
            account_type = 4,
            qty = 1,
            close_position_order = 6,
            front_order_type = 20,
            price = 19585,
            margin_trade_type = 3,
            expire_day = 0,
            fund_type = '11'
        )
        '''

if __name__ == '__main__':
    m = Main()
    m.main()