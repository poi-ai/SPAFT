import traceback
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common import Common
from mold import Mold

class Util():
    def __init__(self, log):
        '''
        初期設定処理

        Args:
            log(Log): カスタムログクラスのインスタンス

        '''
        self.log = log

        # 共通クラス
        self.common = Common(self.log)

        # API<->DBのデータ変換を行うクラス
        self.mold = Mold(self.log)

