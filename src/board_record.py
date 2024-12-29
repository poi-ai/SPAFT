import config
import json
import time
from base import Base

class Main(Base):
    '''板情報をDBに保存するための処理のテストコード'''
    def __init__(self):
        # 初期設定(親クラスのinit実行と、記録先に応じてDB接続を行う)
        if config.BOARD_RECORD_DB == 1:
            super().__init__(use_db = True)
        else:
            super().__init__(use_db = False)

        # 板情報取得対象の銘柄リスト
        self.target_code_list = config.RECORD_STOCK_CODE_LIST
        # デバッグモードか
        self.debug = config.BOARD_RECORD_DEBUG

        # 営業日判定/登録済銘柄の解除/取得対象銘柄の登録
        result, self.target_code_list = self.service.record.record_init(self.target_code_list, self.debug)
        # 非営業日の場合
        if result == False:
            return True

    def main(self):
        '''板情報取得のメイン処理'''

        # 大引けフラグ
        finish_flag = False

        while True:
            # 時刻チェック
            if self.debug == True:
                # 設定ファイルの終了時刻になったら処理終了
                debug_end_hour, debug_end_minute = config.BOARD_RECORD_DEBUG_END_TIME.split(':')
                now = self.util.culc_time.get_now(accurate = False)
                if now.hour > int(debug_end_hour) or (now.hour == int(debug_end_hour) and now.minute >= int(debug_end_minute)):
                    finish_flag = True
            else:
                time_type = self.util.culc_time.exchange_time()

                # 時刻の種別に応じて待機時間を決定
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
                    # 大引け後は大引けの板を一回だけ記録するため処理自体は終了させないでフラグだけ建てておく
                    finish_flag = True

            # 1銘柄ごとにチェック
            for stock_code in self.target_code_list:
                # 板情報をAPI経由で取得する
                result, board_info = self.service.record.info_board(stock_code = stock_code, market_code = 1, add_info = True)
                if result == False:
                    continue

                # DB記録モードの場合
                if config.BOARD_RECORD_DB == 1:
                    # 板情報テーブルに合わせたフォーマットに変換
                    board_table_dict = self.util.mold.response_to_boards(board_info)
                    if board_table_dict != False:
                        # 板情報を学習用テーブルに追加
                        result = self.service.record.insert_board(board_table_dict)
                        if result == False:
                            continue
                # CSV記録モードの場合
                else:
                    # 板情報をCSVに記録
                    result = self.service.record.record_board_csv(board_info)
                    if result == False:
                        continue

                # レート制限回避のため0.05秒待機 MEMO レート制限は最大10件/秒 API接続で0.05秒はかかるのでこれ以上の間隔を空ける必要はない
                time.sleep(0.05)

            # 大引け後やデバッグモード終了時刻を過ぎていたら処理終了
            if finish_flag: break

            # 取得モードによって待機時間を変える
            if config.BOARD_RECORD_MODE == 1:
                # 1秒ごと取得モードの場合は次の秒まで待機
                self.util.culc_time.wait_time_next_second(False)
            elif config.BOARD_RECORD_MODE == 2:
                # 1分ごと取得モードの場合は次の分まで待機
                self.util.culc_time.wait_time_next_minute(False)
            else:
                # 1回のみ取得モードの場合は処理終了
                return True

if __name__ == '__main__':
    m = Main()
    m.main()