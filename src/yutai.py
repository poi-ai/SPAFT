import sys
from base import Base

class Yutai(Base):
    '''信用の成行決済買い注文を行う'''
    def __init__(self):
        super().__init__(use_db = False)

    def main(self):
        # メイン処理
        self.service.trade.yutai_settlement()

        return

if __name__ == '__main__':
    y = Yutai()
    y.main()