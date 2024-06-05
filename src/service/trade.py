class Trade():
    '''取引に関するServiceクラス'''
    def __init__(self, log, util, api, db):
        self.log = log
        self.util = util
        self.api = api
        self.db = db