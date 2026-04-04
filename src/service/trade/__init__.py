from .trade import Trade as ScalpingTrade
from .simulation import Simulation


class Trade():
    def __init__(self, api_headers, api_url, ws_url, conn):
        # 取引/注文に関するクラス
        self.scalping = ScalpingTrade(api_headers, api_url, ws_url, conn)

        # DBに保存された板情報から取引のシミュレーションを行うクラス
        self.simulation = Simulation(api_headers, api_url, ws_url, conn)
