import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .collect import Collect
from .mold import Mold
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
        # データ収集に関するクラス群
        self.collect = Collect(api_headers, api_url, ws_url, conn)

        # データ成形に関するクラス群
        self.mold = Mold()

        # 取引に関するクラス群（凍結中）
        self.trade = Trade(api_headers, api_url, ws_url, conn)
