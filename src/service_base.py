import config
import json

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from util import Util
from util.log import Log
from db import Db
from kabusapi import KabusApi

class ServiceBase():
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

    def __init__(self, api_headers = False, api_url = False, ws_url = False, conn = False):
        '''
        Utilクラス、Dbクラス、Apiクラスのインスタンスを生成する
        Serviceクラスから呼び出す初期処理

        Args:
            api_headers(dict) or False: APIのヘッダー情報 ※APIを使わない場合はFalse
            api_url(str) or False: APIのURL ※APIを使わない場合はFalse
            ws_url(str) or False: WebSocketのURL ※APIを使わない場合はFalse
            conn(pymysql.connections.Connection) or False: DB接続情報 ※DBを使わない場合はFalse

        '''
        self.log = Log()
        self.config = config

        # Utilityクラス
        self.util = Util(log = self.log)

        # KabuStation APIの操作に関連するクラス
        if api_url == False:
            self.api = False
        else:
            try:
                trade_password = config.TRADE_PASSWORD
            except:
                trade_password = False
            self.api = KabusApi()
            self.api.service_init(log = self.log,
                                  api_headers = api_headers,
                                  api_url = api_url,
                                  ws_url = ws_url,
                                  trade_password = trade_password)

        # データベースの操作に関連するクラス
        if conn == False:
            self.db = False
            self.db_info = False
        else:
            self.db_info = {
                'host': config.DB_HOST,
                'user': config.DB_USER,
                'password': config.DB_PASSWORD,
                'db': config.DB_NAME
            }
            self.db = Db()
            self.db.service_init(self.log, conn, self.db_info)


    def error_output(self, message, e = None, stacktrace = None):
        '''エラー時のログ出力を行う

        Args:
            message(str) : エラーメッセージ
            e(str) : エラー名
            stacktrace(str) : スタックトレース(traceback.format_exc())
        '''
        self.log.error(message)

        if e != None:
            self.log.error(e)

        if stacktrace != None:
            self.log.error(stacktrace)

    def byte_to_dict(self, response_json):
        '''受け取ったレスポンスをdict型に変換する'''
        return json.loads(response_json)

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = self.byte_to_dict(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response
