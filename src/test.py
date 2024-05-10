import config
import json
from base import Log
from common import Common
from mold import Mold
from db import Db
from kabusapi import KabusApi

class Main(Common, Mold):
    '''板情報をDBに保存するための処理のテストコード'''
    def __init__(self):
        self.log = Log()
        self.api = KabusApi(self.log, api_password = 'production', production = True)
        # DB操作のSQLを記載しているクラス
        self.db = Db(self.log)
        # レスポンス/リクエストフォーマット整形する処理をまとめたクラス
        self.mold = Mold(self.log)
        # 共通処理を記載したクラス
        self.common = Common(self.log)
        # 板情報取得対象の銘柄リスト
        self.target_code_list = config.RECORD_STOCK_CODE_LIST
        # 初期処理
        self.init_main()

    def init_main(self):
        '''主処理の前に動かしておくべき処理'''
        # 50銘柄ルールに引っ掛からないように登録銘柄をすべて解除しておく
        result = self.api.regist.unregist_all()
        if result == False:
            pass # 特にエラー出ても後の処理にそんな影響ないので特に何もしない

        return True

    def main(self):
        '''板情報取得のメイン処理'''
        # 大引けフラグ
        finish_flag = False

        while True:
            # 日付・時刻チェック
            time_type = self.common.exchange_time()
            # 非営業日
            if time_type == -1:
                self.log.info('非営業日のため実行されません')
                return True
            # 寄付き前
            elif time_type == 3:
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
            for code in self.target_code_list:
                # 板情報をAPI経由で取得する
                board_info = self.api.info.board(stock_code = code)

                if board_info == False:
                    self.db.errors.insert('板情報取得処理')
                    continue
                elif board_info == 4002006:
                    # 銘柄登録数上限の場合、銘柄登録全解除
                    result = self.api.regist.unregist_all()
                    if result == False:
                        self.db.errors.insert('銘柄登録全解除')
                        continue

                    # 再度板情報取得
                    board_info = self.api.info.board(stock_code = code, market_code = 1)
                    if board_info == False:
                        self.db.errors.insert('板情報再取得処理')
                        continue
                elif board_info == 4002001:
                    # 指定したコードの銘柄が存在しない場合、記録対象からコードを除外
                    copy_code_list = [item for item in copy_code_list if item != code]
                    continue

                # byte型のレスポンス(板情報)をdictに変換
                board_info = json.loads(board_info)

                # 板情報テーブルに合わせたフォーマットに変換
                board_table_dict = self.mold.response_to_boards(board_info)
                if board_table_dict != False:
                    # 板情報を学習用テーブルに追加
                    self.db.board.insert(board_table_dict)

            # 除外した銘柄コードをリストから除去
            self.target_code_list = copy_code_list

            # 大引け後に記録を取ったら処理終了
            if finish_flag: break


if __name__ == '__main__':
    m = Main()
    m.main()