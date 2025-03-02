import config
from base import Base

class Yutai(Base):
    '''
    信用の成行決済買い注文を行う

    MEMO GUI操作機能を作ったのでそちらを優先して使う。こちらはGUIで何かあった時のリカバリで使用
    '''
    def __init__(self):
        super().__init__(use_db = False)

    def main(self):
        # メイン処理 TODO 引数にパスワードを入れろ
        self.service.trade.yutai_settlement(config.TRADE_PASSWORD)

        return

if __name__ == '__main__':
    y = Yutai()
    y.main()