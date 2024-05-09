# スキャルピングを行う銘柄[必須]
STOCK_CODE = 1570 # 日経レバ
# STOCK_CODE = 9432 # NTT

# 板を記録する銘柄コードリスト
RECORD_STOCK_CODE_LIST = [

]

# 買い板と売り板の間の価格に注文を入れるか
AMONG_PRICE_ORDER = True

# DB情報[必須] kabusAPIはWindows上でしか動かせないので基本は固定
HOST = 'localhost',
USER = 'root',
PASSWORD = 'root',
DB = 'spaft'

# LINE通知メッセージトークン[任意]
LINE_TOKEN = ''
