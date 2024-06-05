import config
import json
import time
from base import Base

class Main(Base):
    '''板情報をDBに保存するための処理のテストコード'''
    def __init__(self):
        # ログインスタンスの設定
        super().__init__()

        # 各クラスの設定
        self.create_instance()

        # 板情報取得対象の銘柄リスト
        self.target_code_list = config.RECORD_STOCK_CODE_LIST

        # 営業日判定と登録済銘柄の解除
        result = self.service.record.record_init()
        if result == False:
            return True

    def main(self):
        '''板情報取得のメイン処理'''

        # 大引けフラグ
        finish_flag = False

        while True:
            # レート制限のための時間計測
            start_time = time.time()

            # 日付・時刻チェック
            time_type = self.util.culc_time.exchange_time()
            # 寄付き前
            if time_type == 3:
                pass
            # お昼休み
            elif time_type == 4:
                pass
            # 大引け後
            elif time_type == 5:
                finish_flag = True # 大引け後は板を一回だけ記録するため,それ用のフラグ

            # エラー銘柄除去のためにコピーを作っておく
            copy_code_list = self.target_code_list

            # 1銘柄ごとにチェック
            for stock_code in self.target_code_list:
                # 板情報をAPI経由で取得する
                board_info = self.service.record.info_board(stock_code = stock_code, market_code = 1, add_info = True)
                if board_info == False:
                    continue

                # 板情報テーブルに合わせたフォーマットに変換
                board_table_dict = self.util.mold.response_to_boards(board_info)
                if board_table_dict != False:
                    # 板情報を学習用テーブルに追加
                    self.db.board.insert(board_table_dict)

            # 除外した銘柄コードをリストから除去
            self.target_code_list = copy_code_list

            # 大引け後に記録を取ったら処理終了
            if finish_flag: break

            # 1周1秒未満の場合は1秒になるように時間調整
            end_time = time.time()
            if end_time - start_time < 1:
                time.sleep(1 - (end_time - start_time))


if __name__ == '__main__':
    m = Main()
    m.main()