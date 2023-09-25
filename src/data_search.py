import json
import time
import traceback
from db_base import Db_Base
from db_operate import Db_Operate
from kabusapi import KabusApi

# APIから返ってくる情報を調査するための処理
class DS(Db_Base):
    def __init__(self):
        super().__init__()
        self.api = KabusApi(api_password = 'production', production = True)
        self.db = Db_Operate()
        self.error_stock_code = []

    def main(self, stock_code = None):

        if stock_code is not None:
            # 指定があったらそれのみ
            stock_code_list = list(stock_code)
        else:
            # 指定がないなら全部
            stock_code_list = [stock_code for stock_code in range(1000, 10000)]

        # 一個ずつ見る
        for target_stock_code in stock_code_list:
            time.sleep(1)

            # 板情報で返ってくるデータを見たい
            board_info = self.api.info.board(stock_code = stock_code)
            if board_info == False:
                self.error_stock_code.append(target_stock_code)

            # dict変換
            try:
                borad_dict = self.byte_to_dict(board_info)
            except Exception as e:
                self.error_output('dict変換でエラー', e, traceback.format_exc())
                self.error_stock_code.append(target_stock_code)

            # DBに突っ込めるように形を変える
            try:
                borads_table_dict = {
                    'stock_code': '',
                    'market_code': '',
                    'price': '',
                    'latest_transaction_date': '',
                    'change_status': '',
                    'present_status': '',
                    'market_buy_qty': '',
                    'buy1_sign': '',
                    'buy1_price': '',
                    'buy1_qty': '',
                    'buy2_price': '',
                    'buy2_qty': '',
                    'buy3_price': '',
                    'buy3_qty': '',
                    'buy4_price': '',
                    'buy4_qty': '',
                    'buy5_price': '',
                    'buy5_qty': '',
                    'buy6_price': '',
                    'buy6_qty': '',
                    'buy7_price': '',
                    'buy7_qty': '',
                    'buy8_price': '',
                    'buy8_qty': '',
                    'buy9_price': '',
                    'buy9_qty': '',
                    'buy10_price': '',
                    'buy10_qty': '',
                    'market_sell_qty': '',
                    'sell1_sign': '',
                    'sell1_price': '',
                    'sell1_qty': '',
                    'sell2_price': '',
                    'sell2_qty': '',
                    'sell3_price': '',
                    'sell3_qty': '',
                    'sell4_price': '',
                    'sell4_qty': '',
                    'sell5_price': '',
                    'sell5_qty': '',
                    'sell6_price': '',
                    'sell6_qty': '',
                    'sell7_price': '',
                    'sell7_qty': '',
                    'sell8_price': '',
                    'sell8_qty': '',
                    'sell9_price': '',
                    'sell9_qty': '',
                    'sell10_price': '',
                    'sell10_qty': '',
                    'over_qty': '',
                    'under_qty': ''
                }
            except Exception as e:
                self.error_output('dict代入でエラー', e, traceback.format_exc())
                self.error_stock_code.append(target_stock_code)

            # レコード追加
            result = self.db.insert_boards()
            if result == False:
                self.error_stock_code.append(target_stock_code)

    def byte_to_dict(self, response_json):
        '''受け取ったレスポンスをdict型に変換する'''
        return json.loads(response_json)

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = self.byte_to_dict(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response

ds = DS()
ds.main(1570)