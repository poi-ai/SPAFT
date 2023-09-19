import json
from base import Base
from kabusapi import KabusApi

# APIから返ってくる情報を調査するための処理
class DS(Base):
    def __init__(self):
        super().__init__()
        self.api = KabusApi(api_password = 'production', production = True)

    def main(self, stock_code):
        # 板情報で返ってくるデータを見たい
        board_info = self.api.info.board(stock_code = stock_code)

        print(self.tidy_response(board_info))

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = json.loads(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response


ds = DS()
ds.main(1570)