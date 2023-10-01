import time
from db_base import Db_Base
from db_operate import Db_Operate
from kabusapi import KabusApi

# 上場している銘柄コードを管理する処理
class Listed_Update(Db_Base):
    def __init__(self):
        super().__init__()
        self.api = KabusApi(api_password = 'production', production = True)
        self.db = Db_Operate()

    def main(self, unlisted_check = True):
        '''
        DBに登録されている上場している証券コードの更新

        Args:
            unlisted_check(bool): DBに記録されていない証券コードが上場しているかのチェック
        '''

        # DBに登録されていない銘柄コード用のリスト
        unlisted_list = [code for code in range(1000, 10000)]

        # DBから上場している銘柄コードを取ってくる
        listed_data = self.db.select_listed()
        if listed_data == False:
            exit()

        # 一個ずつ見る
        for listed in listed_data:
            stock_code = listed['stock_code']
            time.sleep(0.2)

            # 板情報が存在するか取得
            board_info = self.api.info.board(stock_code = stock_code, market_code = 1)
            if board_info == False:
                continue

            # 銘柄登録数上限対応
            if board_info == 4002006:
                # 銘柄登録全解除
                result = self.api.regist.unregist_all()
                if result == False:
                    continue

                # 再度板情報取得
                board_info = self.api.info.board(stock_code = stock_code, market_code = 1)
                if board_info == False:
                    continue

            # 銘柄未発見の(=その証券コードが存在しない)場合はテーブルから削除する
            elif board_info == 4002001:
                result = self.db.delete_listed(stock_code = stock_code)
                if result == False:
                    continue

            # 違う場合は未登録リストから除去する
            else:
                if unlisted_check:
                    unlisted_list = [code for code in unlisted_list if code != stock_code]

            # DB未登録の銘柄が登録されているかのチェック
            if unlisted_check:
                print()  #TODO

ls = Listed_Update()
ls.main()