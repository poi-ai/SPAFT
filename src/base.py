import config
import json
import requests
import traceback

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from util import Util
from util.log import Log
from db import Db
from kabusapi import KabusApi
from service import Service

class Base():
    '''
    共通の初期処理とエラー通知メソッドを記載

    Memo:
        呼び出し可能なクラス
        ・起動ファイル->Service
        ・起動ファイル->Util
        ・Service->Util
        ・Service->Api
        ・Service->Db

        ・起動ファイル->Api x
        ・起動ファイル->Db x
        ・Db->Util x 必要そうなら入れる
        ・Api->Util x 必要なら入れる

    '''

    def __init__(self, use_db = True, use_api = True):
        '''
        UtilクラスとServiceクラスのインスタンスを生成する
        また、DBとAPIを使う場合は設定を行う
        Controller(起動ファイル)から呼び出す初期処理

        Args:
            use_db(bool): DBクラスを呼び出す/使用するか
                ※DBに接続されていないとエラーとなるので必要な場合のみTrueに

            use_api(bool): KabuStationAPIクラスを呼び出す/使用するか
                ※KabuStationが起動/API利用設定が完了していないとエラーとなるので必要な場合のみTrueに
        '''
        self.log = Log()

        # Utilityクラス
        self.util = Util(log = self.log)

        # KabuStation APIの操作に関連するクラス
        if use_api:
            api = KabusApi()
            api_url, ws_api, api_headers = api.controller_init(log = self.log,
                                                               api_password = config.API_PASSWORD,
                                                               production = config.API_PRODUCTION)
        else:
            api_url, ws_api, api_headers = False, False, False

        # データベースの操作に関連するクラス
        if use_db:
            try:
                db_info = {
                    'host': config.DB_HOST,
                    'user': config.DB_USER,
                    'password': config.DB_PASSWORD,
                    'db': config.DB_NAME
                }
            except Exception as e:
                self.log.error(f'MySQLの接続情報取得処理でエラー\n{e}\n{traceback.format_exc()}')
                exit()

            db = Db()
            conn = db.controller_init(self.log, db_info)
        else:
            conn = False

        # Serviceクラス
        self.service = Service(api_headers = api_headers,
                               api_url = api_url,
                               ws_url = ws_api,
                               conn = conn)


    def error_output(self, message, e = None, stacktrace = None, line_flg = True):
        '''エラー時のログ出力/LINE通知を行う

        Args:
            message(str) : エラーメッセージ
            e(str) : エラー名
            stacktrace(str) : スタックトレース(traceback.format_exc())
            line_flg(bool) : LINE通知を行うか
        '''
        other_message = message
        self.log.error(message)

        if e != None:
            self.log.error(e)
            other_message += f'\n{e}'

        if stacktrace != None:
            self.log.error(stacktrace)
            other_message += f'\n{stacktrace}'

        if line_flg:
            self.line_send(other_message)

    def line_send(self, message):
        '''LINE Messaging APIのブロードキャストでメッセージを送信する
            送信にはconfig.py.LINE_MESSAGING_API_TOKENにLINE Messaging APIの
            チャネルアクセストークンが記載されている必要がある(必須ではない)

        Args:
            message(str) : LINE送信するメッセージ内容
        '''
        # 設定ファイルからトークン取得
        try:
            token = config.LINE_MESSAGING_API_TOKEN
        except AttributeError:
            return

        # 空なら何もしない
        if token == '':
            return

        # 5000文字ずつ最大5件に分割（Messaging API上限）
        chunks = []
        while message and len(chunks) < 5:
            chunks.append(message[:5000])
            message = message[5000:]

        # ヘッダー設定
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        # メッセージ設定
        data = {
            'messages': [{'type': 'text', 'text': chunk} for chunk in chunks]
        }

        # メッセージ送信
        try:
            r = requests.post('https://api.line.me/v2/bot/message/broadcast', headers = headers, json = data)
        except Exception as e:
            self.log.error(f'LINE Messaging APIでのメッセージ送信に失敗しました\n{e}\n{traceback.format_exc()}')
            return

        if r.status_code != 200:
            self.log.error('LINE Messaging APIでエラーが発生しました')
            try:
                self.log.error(f'ステータスコード: {r.status_code}\nエラー内容: {json.dumps(json.loads(r.content), indent=2)}')
            except Exception as e:
                self.log.error(f'{e}\n{traceback.format_exc()}')

    #def byte_to_dict(self, response_json):
    #    '''受け取ったレスポンスをdict型に変換する'''
    #    return json.loads(response_json)

    #def tidy_response(self, response_json):
    #    '''受け取ったレスポンスをインデントをそろえた形にする'''
    #    parsed_response = self.byte_to_dict(response_json)
    #    formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
    #    return formatted_response
