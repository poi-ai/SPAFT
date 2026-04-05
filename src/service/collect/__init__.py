from .record import Record
from .past_record import PastRecord


class Collect():
    def __init__(self, api_headers, api_url, ws_url, conn):
        # 情報取得/記録に関するクラス
        self.record = Record(api_headers, api_url, ws_url, conn)

        # 過去の四本値の情報取得/記録に関するクラス
        self.past_record = PastRecord()
