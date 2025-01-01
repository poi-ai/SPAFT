import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .trade import Trade
from .record import Record
from .simulation import Simulation
from .board_mold import BoardMold

class Service():
    def __init__(self, api_headers, api_url, conn):
        '''
        初期設定処理

        Args:
            api_url(str): KabusAPIのリクエストで使用するエンドポイント
            api_headers(dict): KabusAPIのリクエストで使用する認証用ヘッダー
            conn(pymysql.Conn): MySQLへの接続情報

        '''
        # 情報取得/記録に関するクラス
        self.record = Record(api_headers, api_url, conn)

        # 取引/注文に関するクラス
        self.trade = Trade(api_headers, api_url, conn)

        # DBに保存された板情報から取引のシミュレーションを行うクラス
        self.simulation = Simulation(api_headers, api_url, conn)

        # 板情報CSVを成形するクラス
        self.board_mold = BoardMold()

