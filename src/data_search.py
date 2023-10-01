import csv
import time
import traceback
from datetime import datetime
from db_base import Db_Base
from db_operate import Db_Operate
from kabusapi import KabusApi
from mold import Mold

# APIから返ってくる情報を調査するための処理
class DS(Db_Base):
    def __init__(self):
        super().__init__()
        self.error_stock_code = []
        self.api = KabusApi(api_password = 'production', production = True)
        self.mold = Mold()
        self.db = Db_Operate()
        self.today = datetime.now().strftime("%Y%m%d")

    def main(self, stock_code = None):
        if stock_code is not None:
            # 指定があったらそれのみ
            stock_code_list = [stock_code]
        else:
            # 指定がないなら全部
            stock_code_list = [stock_code for stock_code in range(8226, 10000)]

        # 一個ずつ見る
        for target_stock_code in stock_code_list:
            time.sleep(0.13)

            print(f'{time.time()}: API投げる前')
            # 板情報で返ってくるデータを見たい
            board_info = self.api.info.board(stock_code = target_stock_code, market_code = 1)
            print(f'{time.time()}: API投げた後')
            if board_info == False or board_info == 4002001:
                self.error_stock_code.append(target_stock_code)
                continue

            # 銘柄登録数上限対応
            if board_info == 4002006:
                # 銘柄登録全解除
                result = self.api.regist.unregist_all()
                if result == False:
                    stock_code_list.append(target_stock_code)
                    continue

                # 再度板情報取得
                board_info = self.api.info.board(stock_code = target_stock_code, market_code = 1)
                if board_info == False:
                    self.error_stock_code.append(target_stock_code)
                    continue

            print(f'{time.time()}: dict変換')
            # dict変換
            try:
                board_dict = self.byte_to_dict(board_info)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error(f'dict変換処理でエラー\n{e}\n{traceback.format_exc()}')
                continue

            print(f'{time.time()}: CSVに突っ込む')
            # CSVに突っ込む
            try:
                self.write_dict_to_csv(board_dict)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error(f'CSV出力処理でエラー\n{e}\n{traceback.format_exc()}')
                continue

            print(f'{time.time()}: 上場管理テーブルに突っ込む')
            # 上場情報テーブルにデータ追加
            result = self.db.insert_listed(target_stock_code)
            if result == False:
                self.error_stock_code.append(target_stock_code)

            print(f'{time.time()}: ordersに突っ込むために整形')
            # DBに突っ込めるように成型
            try:
                board_table_dict = self.mold.response_to_boards(board_dict)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error(f'変換処理でエラー\n{e}\n{traceback.format_exc()}')
                continue

            print(f'{time.time()}: ordersに突っ込む')
            # レコード追加
            result = self.db.insert_boards(board_table_dict)
            if result == False:
                self.error_stock_code.append(target_stock_code)

        if len(self.error_stock_code) > 0:
            self.logger.warning(self.error_stock_code)
        else:
            self.logger.info('success!!')

    def write_dict_to_csv(self, input_dict):
        '''dict型のデータをCSVへ出力する'''
        # CSVファイルを書き込みモードで開く
        with open(f'../csv/board_data_{self.today}.csv', mode = 'a', newline = '', encoding = 'UTF-8') as file:
            writer = csv.DictWriter(file, fieldnames = input_dict.keys())

            # ファイルが存在しない場合または空の場合、ヘッダー行を書き込む
            if file.tell() == 0:
                writer.writeheader()

            # 辞書の値をCSVファイルに書き込む
            writer.writerow(input_dict)


ds = DS()
ds.main()