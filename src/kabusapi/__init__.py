import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import Auth
from info import Info
from order import Order
from regist import Regist
from wallet import Wallet

class KabusApi():
    def __init__(self, log, api_password, production = False):
        '''
        初期設定処理

        Args:
            log(Log): カスタムログクラスのインスタンス
            api_password(str): kabuステーションで設定したパスワード
            production(bool): 実行環境
                True: 本番環境、False: 検証環境
        '''
        self.log = log

        # ポート番号の設定
        if production:
            self.API_URL = 'http://localhost:18080/kabusapi'
        else:
            self.API_URL = 'http://localhost:18081/kabusapi'

        # APIトークンを発行
        self.auth = Auth(self.API_URL, log)
        token = self.auth.issue_token(api_password)

        # トークン発行処理でエラー
        if token == False:
            exit()

        # 認証ヘッダー
        self.api_headers = {'X-API-KEY': token}

        # 情報取得関連APIクラス
        self.info = Info(self.api_headers, self.API_URL, log)
        # 注文関連APIクラス
        self.order = Order(self.api_headers, self.API_URL, log)
        # 登録関連APIクラス
        self.regist = Regist(self.api_headers, self.API_URL, log)
        # 余力関連APIクラス
        self.wallet = Wallet(self.api_headers, self.API_URL, log)