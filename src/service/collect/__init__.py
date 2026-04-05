from .collect_service import CollectService
from .past_record import PastRecord


class Collect():
    def __init__(self, api_headers, api_url, ws_url, conn):
        # 情報取得/記録に関するクラス
        self.collect_service = CollectService(api_headers, api_url, ws_url, conn)

        # 過去の四本値の情報取得/記録に関するクラス
        self.past_record = PastRecord()
