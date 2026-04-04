from .board_mold import BoardMold
from .past_record_mold import MoldPastRecord


class Preprocess():
    def __init__(self):
        # 板情報CSVを成形するクラス
        self.board_mold = BoardMold()

        # 過去の四本値の情報を成形するクラス
        self.past_record_mold = MoldPastRecord()
