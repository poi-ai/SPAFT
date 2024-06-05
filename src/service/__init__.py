import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trade import Trade
from record import Record

class Service():
    def __init__(self, log, util, api, db):
        '''
        初期設定処理

        Args:
            log(Log): カスタムログクラスのインスタンス

        '''
        self.log = log
        self.util = util
        self.api = api
        self.db = db

        # 情報取得/記録に関するクラス
        self.record = Record(self.log, self.util, self.api, self.db)

        # 取引/注文に関するクラス
        self.trade = Trade(self.log, self.util, self.api, self.db)

