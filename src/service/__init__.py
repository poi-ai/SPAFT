import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .collect import Collect
from .preprocess import Preprocess
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

        # データ前処理に関するクラス群
        self.preprocess = Preprocess()

        # 取引に関するクラス群（凍結中）
        self.trade = Trade(api_headers, api_url, ws_url, conn)
