import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .board_mold import BoardMold
from .mold_past_record import MoldPastRecord
from .past_record import PastRecord
from .record import Record
from .simulation import Simulation
from .trade import Trade


class Service():
    def __init__(self, api_headers, api_url, ws_url, conn):
        '''
        初期設定処理

        Args:
            api_url(str): KabusAPIのリクエストで使用するエンドポイント
            ws_url(str): WebSocketのエンドポイント
            api_headers(dict): KabusAPIのリクエストで使用する認証用ヘッダー
            conn(pymysql.Conn): MySQLへの接続情報

        '''
        # 情報取得/記録に関するクラス
        self.record = Record(api_headers, api_url, ws_url, conn)

        # 過去の四本値の情報取得/記録に関するクラス
        self.past_record = PastRecord()

        # 過去の四本値の情報を成形するクラス
        self.mold_past_record = MoldPastRecord()

        # 取引/注文に関するクラス
        self.trade = Trade(api_headers, api_url, ws_url, conn)

        # DBに保存された板情報から取引のシミュレーションを行うクラス
        self.simulation = Simulation(api_headers, api_url, ws_url, conn)

        # 板情報CSVを成形するクラス
        self.board_mold = BoardMold()
