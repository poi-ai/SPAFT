import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

