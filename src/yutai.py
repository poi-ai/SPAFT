import json
import sys
from main import Main

class Yutai(Main):
    '''信用の成行決済買い注文を行う'''
    def __init__(self):
        super().__init__()

    def main(self):
        # 株数・信用種別を指定する場合
        if len(sys.argv) == 5:
            self.api.order.yutai_settlement(sys.argv[2], sys.argv[3], sys.argv[4])
        # 株数のみ指定
        elif len(sys.argv) == 4:
            self.api.order.yutai_settlement(sys.argv[2], sys.argv[3])
        # どちらも指定しない(一般信用&100株)
        elif len(sys.argv) == 3:
            self.api.order.yutai_settlement(sys.argv[2])
        else:
            self.ap

        exit()

if __name__ == '__main__':
    y = Yutai()
    y.main()