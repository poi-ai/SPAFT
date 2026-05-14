from .scalping import Scalping
from .simulation import Simulation
from .stat_daytrade import StatDaytrade


class Trade():
    def __init__(self, api_headers, api_url, ws_url, conn):
        # 取引/注文に関するクラス
        self.scalping = Scalping(api_headers, api_url, ws_url, conn)

        # DBに保存された板情報から取引のシミュレーションを行うクラス
        self.simulation = Simulation(api_headers, api_url, ws_url, conn)

        # 統計ベースのエントリー条件を用いたデイトレードRPA(Phase 3)
        self.stat_daytrade = StatDaytrade(api_headers, api_url, ws_url, conn)
