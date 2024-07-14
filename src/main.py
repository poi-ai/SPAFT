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
            result, order_flag = self.logic.enforce_settlement(trade_password = config.TRADE_PASSWORD)
            # 実行に失敗した注文が存在するか、注文/注文キャンセルを行った場合
            if result == False or order_flag == True:
                # 10秒待ってもう一度同じ関数の呼び出し,完了していることの確認
                time.sleep(10)
                result, order_flag = self.logic.enforce_settlement(trade_password = config.TRADE_PASSWORD)
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

if __name__ == '__main__':
    m = Main()
    m.main()