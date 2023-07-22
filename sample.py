from src.kabusapi import KabusApi

# インスタンス生成&トークン発行(開発環境)
api = KabusApi('password')

# インスタンス生成&トークン発行(本番環境)
#api = KabusApi('password', production = True)

# トークン出力
#print(api.token)

# トークン再取得
#api.auth.issue_token('password')

# 板情報取得 [NTT<9432>]
#board_info = api.info.board(9432, 1)

# 銘柄情報取得 [ソフトバンクG<9984>]
#stock_info = api.info.symbol(9984, 1)

# プレミアム料(空売り上乗せ手数料)情報取得 [野村日経225ブル<1321>]
#premium_price_info = api.info.premium_price(1321)

# 新規注文 [トヨタ自動車<7203>、現物成行注文]
'''
result = api.order.stock(password = 'p@ssword',
                         stock_code = 7203,
                         exchange = 1,
                         side = 1,
                         cash_margin = 1,
                         deliv_type = 2,
                         account_type = 4,
                         qty = 100,
                         front_order_type = 10,
                         price = 0,
                         expire_day = 0,
                         fund_type = '02',
                         )
'''

# 注文のキャンセル
#result = api.order.cancel('20200529A01N06848002','p@ssword')

# 現物の余力情報取得
#cash_yoryoku = api.wallet.cash()

# 信用の余力情報取得 [ファーストリテイリング<9983>]
#margin_yoryoku = api.wallet.margin(9983, 1)