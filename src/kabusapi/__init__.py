import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .auth import Auth
from .info import Info
from .order import Order
from .register import Register
from .wallet import Wallet

class KabusApi():
    def controller_init(self, log, api_password, production = False):
        '''
        起動ファイルから呼び出す場合

        Args:
            log(Log): カスタムログクラスのインスタンス
            api_password(str): kabuステーションで設定したパスワード
            production(bool): 実行環境
                True: 本番環境、False: 検証環境

        '''
        # ポート番号の設定
        if production:
            api_url = 'http://localhost:18080/kabusapi'
        else:
            api_url = 'http://localhost:18081/kabusapi'

        # APIトークンを発行
        self.auth = Auth(api_url, log)
        result, token = self.auth.issue_token(api_password)

        # トークン発行処理でエラー
        if result == False:
            if token == -1:
                log.error('KabuStationが起動していません')
            else:
                if 'ログイン認証エラー' in token:
                    log.error(f'トークン発行処理に失敗\n{token}\nKabuStaionの再起動が必要です')
                elif 'トークン取得失敗' in token:
                    log.error(f'トークン発行処理に失敗\n{token}\nIDかパスワードが間違っています')
                else:
                    log.error(f'トークン発行処理に失敗\n{token}')
            exit()

        # 認証ヘッダー
        api_headers = {'X-API-KEY': token}

        return api_url, api_headers

    def service_init(self, log, api_headers, api_url, trade_password):
        '''Serviceクラスから呼び出す場合'''
        # 認証情報発行APIクラス
        self.auth = Auth(api_url, log)
        # 情報取得関連APIクラス
        self.info = Info(api_headers, api_url, log)
        # 注文関連APIクラス
        self.order = Order(api_headers, api_url, log, trade_password)
        # 登録関連APIクラス
        self.register = Register(api_headers, api_url, log)
        # 余力関連APIクラス
        self.wallet = Wallet(api_headers, api_url, log)