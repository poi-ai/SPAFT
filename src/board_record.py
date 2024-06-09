import config
import json
import time
from base import Base

class Main(Base):
    '''板情報をDBに保存するための処理のテストコード'''
    def __init__(self):
        # 初期設定
        super().__init__()

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
            # 前場前
            if time_type == 3:
                # 前場開始1秒前まで待機
                self.util.culc_time.wait_time(hour = 8, minute = 59, second = 59)
            # お昼休み
            elif time_type == 4:
                # 後場開始1秒前まで待機
                self.util.culc_time.wait_time(hour = 12, minute = 29, second = 59)
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
                    result = self.service.record.insert_board(board_table_dict)
                    if result == False:
                        continue

                # レート制限回避のため0.05秒待機
                time.sleep(0.05)

            # 除外した銘柄コードをリストから除去
            self.target_code_list = copy_code_list

            # 大引け後に記録を取ったら処理終了
            if finish_flag: break

            # 次の秒まで待機
            self.util.culc_time.wait_time_next_second()

if __name__ == '__main__':
    m = Main()
    m.main()