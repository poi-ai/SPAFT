import csv
import json
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
            stock_code_list = [stock_code for stock_code in range(1000, 10000)]

        # 一個ずつ見る
        for target_stock_code in stock_code_list:
            time.sleep(1)

            # 板情報で返ってくるデータを見たい
            board_info = self.api.info.board(stock_code = stock_code, market_code = 1)
            if board_info == False:
                self.error_stock_code.append(target_stock_code)
                print(f'板情報取得処理でエラー stock_code: {target_stock_code}')
                continue

            # dict変換
            try:
                board_dict = self.byte_to_dict(board_info)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error('dict変換処理でエラー', e, traceback.format_exc())
                print(f'dict変換処理でエラー\n{e}\n{traceback.format_exc()}')
                continue

            # CSVに突っ込む
            try:
                self.write_dict_to_csv(board_dict)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error('CSV出力処理でエラー', e, traceback.format_exc())
                print(f'CSV出力処理でエラー\n{e}\n{traceback.format_exc()}')
                continue

            # DBに突っ込めるように成型
            try:
                board_table_dict = self.mold.response_to_boards(board_dict)
            except Exception as e:
                self.error_stock_code.append(target_stock_code)
                self.logger.error('変換処理でエラー', e, traceback.format_exc())
                print(f'変換処理でエラー\n{e}\n{traceback.format_exc()}')

            # レコード追加
            result = self.db.insert_boards(board_table_dict)
            if result == False:
                self.error_stock_code.append(target_stock_code)

        if len(self.error_stock_code) > 0:
            self.logger.warning(self.error_stock_code)
        else:
            self.logger.info('success!!')

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = self.byte_to_dict(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response

    def write_dict_to_csv(self, input_dict):
        '''dict型のデータをCSVへ出力する'''
        # CSVファイルを書き込みモードで開く
        with open(f'board_data_{self.today}.csv', mode = 'a', newline = '') as file:
            writer = csv.DictWriter(file, fieldnames = input_dict.keys())

            # ファイルが存在しない場合または空の場合、ヘッダー行を書き込む
            if file.tell() == 0:
                writer.writeheader()

            # 辞書の値をCSVファイルに書き込む
            writer.writerow(input_dict)


ds = DS()
ds.main()