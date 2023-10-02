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

    def main(self, listed_check = True, unlisted_check = True):
        '''
        DBに登録されている上場している証券コードの更新

        Args:
            unlisted_check(bool): DBに記録されていない証券コードが上場しているかのチェック
        '''

        # DBに上場中として登録されている銘柄コードを取ってくる
        if listed_check:
            listed_data = self.db.select_listed(listed_flg = 1)
            if listed_data == False:
                exit()

            # 一個ずつ見る
            for listed in listed_data:
                stock_code = listed['stock_code']
                time.sleep(0.2)

                # 一番軽い優先市場取得APIで銘柄コードが存在しているかチェックする
                response = self.api.info.primary_exchange(stock_code = stock_code,)
                if response == False:
                    continue

                # 銘柄未発見の(=その証券コードが存在しない)場合はステータスを変更する
                elif response == 4002001:
                    result = self.db.update_listed(stock_code = stock_code, listed_flg = 0)
                    if result == False:
                        continue

        # 上場企業に振られていない銘柄コード(新規上場銘柄)のチェックを行う
        if unlisted_check:
            unlisted_list = self.db.select_listed(listed_flg = 0)
            if unlisted_list != False:
                # 1コードずつチェック
                for unlisted in unlisted_list:
                    stock_code = unlisted['stock_code']
                    time.sleep(0.2)

                    # 優先市場APIから銘柄コードの存在チェック
                    response = self.api.info.primary_exchange(stock_code = stock_code)
                    if response == False:
                        continue

                    # エラーでも銘柄未発見でも無い場合は割り当てられた企業がするとみなしてDBを更新
                    elif response != 4002001:
                        result = self.db.update_listed(stock_code = stock_code, listed_flg = 1)
                        if result == False:
                            continue

if __name__ == '__main__':
    ls = Listed_Update()
    ls.main()