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
            self.logic.enforce_management(trade_type = '単一',
                                          trade_password = config.TRADE_PASSWORD,
                                          stock_code = config.STOCK_CODE)
            return True

        # トレード開始前の事前準備/チェック
        result = self.logic.scalping_init(config)
        if result == False:
            self.log.info('トレード前の初期処理でエラーが発生したため処理を終了します')
            return False

        # トレードを行う
        self.logic.scalping()

        self.log.info('SPAFT終了')

if __name__ == '__main__':
    m = Main()
    m.main()