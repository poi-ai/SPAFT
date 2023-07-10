from auth import Auth
from info import Info
from order import Order
from regist import Regist
from wallet import Wallet

class KabusApi():
    def __init__(self, api_password):
        # APIトークンを発行
        self.auth = Auth()
        self.token = self.auth.issue_token(api_password)

        # 認証ヘッダー
        self.api_headers = {'X-API-KEY', self.token}

        # 情報取得関連APIクラス
        self.info = Info(self.api_headers)
        # 注文関連APIクラス
        self.order = Order(self.api_headers)
        # 登録関連APIクラス
        self.regist = Regist(self.api_headers)
        # 余力関連APIクラス
        self.wallet = Wallet(self.api_headers)