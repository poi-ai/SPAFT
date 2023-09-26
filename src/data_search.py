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

            # dict変換
            try:
                board_dict = self.byte_to_dict(board_info)
            except Exception as e:
                print(e)
                self.error_output('dict変換でエラー', e, traceback.format_exc())
                self.error_stock_code.append(target_stock_code)
            
            # 確認用
            print(board_dict)

            '''
            # DBに突っ込めるように形を変える
            try:
                borads_table_dict = {
                    'stock_code': board_info['Symbol'],
                    'market_code': board_info['Exchange'],
                    'price': board_info[''],
                    'latest_transaction_date': board_info[''],
                    'change_status': board_info[''],
                    'present_status': board_info[''],
                    'market_buy_qty': board_info[''],
                    'buy1_sign': board_info[''],
                    'buy1_price': board_info[''],
                    'buy1_qty': board_info[''],
                    'buy2_price': board_info[''],
                    'buy2_qty': board_info[''],
                    'buy3_price': board_info[''],
                    'buy3_qty': board_info[''],
                    'buy4_price': board_info[''],
                    'buy4_qty': board_info[''],
                    'buy5_price': board_info[''],
                    'buy5_qty': board_info[''],
                    'buy6_price': board_info[''],
                    'buy6_qty': board_info[''],
                    'buy7_price': board_info[''],
                    'buy7_qty': board_info[''],
                    'buy8_price': board_info[''],
                    'buy8_qty': board_info[''],
                    'buy9_price': board_info[''],
                    'buy9_qty': board_info[''],
                    'buy10_price': board_info[''],
                    'buy10_qty': board_info[''],
                    'market_sell_qty': board_info[''],
                    'sell1_sign': board_info[''],
                    'sell1_price': board_info[''],
                    'sell1_qty': board_info[''],
                    'sell2_price': board_info[''],
                    'sell2_qty': board_info[''],
                    'sell3_price': board_info[''],
                    'sell3_qty': board_info[''],
                    'sell4_price': board_info[''],
                    'sell4_qty': board_info[''],
                    'sell5_price': board_info[''],
                    'sell5_qty': board_info[''],
                    'sell6_price': board_info[''],
                    'sell6_qty': board_info[''],
                    'sell7_price': board_info[''],
                    'sell7_qty': board_info[''],
                    'sell8_price': board_info[''],
                    'sell8_qty': board_info[''],
                    'sell9_price': board_info[''],
                    'sell9_qty': board_info[''],
                    'sell10_price': board_info[''],
                    'sell10_qty': board_info[''],
                    'over_qty': board_info[''],
                    'under_qty': board_info['']
                }
            except Exception as e:
                self.error_output('dict代入でエラー', e, traceback.format_exc())
                self.error_stock_code.append(target_stock_code)

            # レコード追加
            result = self.db.insert_boards()
            if result == False:
                self.error_stock_code.append(target_stock_code)
            '''

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