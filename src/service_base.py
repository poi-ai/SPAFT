import config
import json
import requests

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

    def __init__(self, api_headers, api_url, conn):
        '''
        Utilクラス、Dbクラス、Apiクラスのインスタンスを生成する
        Serviceクラスから呼び出す初期処理

        '''
        self.log = Log()

        # Utilityクラス
        self.util = Util(log = self.log)

        # KabuStation APIの操作に関連するクラス
        if api_url == False:
            self.api = False
        else:
            self.api = KabusApi()
            self.api.service_init(self.log, api_headers, api_url)

        # データベースの操作に関連するクラス
        if conn == False:
            self.db = False
        else:
            self.db = Db()
            self.db.service_init(self.log, conn)


    def error_output(self, message, e = None, stacktrace = None, line_flg = True):
        '''エラー時のログ出力/LINE通知を行う

        Args:
            message(str) : エラーメッセージ
            e(str) : エラー名
            stacktrace(str) : スタックトレース(traceback.format_exc())
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

    def line_send(self, message, separate_no = 1):
        ''' LINEにメッセージを送信する
            送信にはconfig.py.LINE_TOKENにLINE Notice APIの
            APIトークンコードが記載されている必要がある(必須ではない)

        Args:
            message(str) : LINE送信するメッセージ内容
        '''
        # 10000字以上送ったらもうそれ以上送らない
        if separate_no > 10:
            self.log.info('LINE Notifyでの送信メッセージが10000字を超えました')
            return

        # 設定ファイルからトークン取得
        try:
            token = config.LINE_TOKEN
        except AttributeError as e:
            return

        # 空なら何もしない
        if token == '':
            return

        # ヘッダー設定
        headers = {'Authorization': f'Bearer {token}'}

        # メッセージが1000文字(上限)を超えていたら分割して送る
        unsent_message = ''
        if len(message) > 999:
            unsent_message = message[1000:]
            message = message[:1000]

        # メッセージ設定
        data = {'message': f'{message}'}

        # メッセージ送信
        try:
            r = requests.post('https://notify-api.line.me/api/notify', headers = headers, data = data)
        except Exception as e:
            self.log.error('LINE Notify APIでのメッセージ送信に失敗しました')
            self.log.error(e)
            return

        if r.status_code != 200:
            self.log.error('LINE Notify APIでエラーが発生しました')
            self.log.error('ステータスコード：' + r.status_code)
            try:
                self.log.error('エラー内容：' + json.dumps(json.loads(r.content), indent=2))
            except Exception as e:
                self.log.error(e)
            return False

        # 未送信文字が残っていれば送信
        if unsent_message != '':
            self.line_send(unsent_message, separate_no + 1)

    def byte_to_dict(self, response_json):
        '''受け取ったレスポンスをdict型に変換する'''
        return json.loads(response_json)

    def tidy_response(self, response_json):
        '''受け取ったレスポンスをインデントをそろえた形にする'''
        parsed_response = self.byte_to_dict(response_json)
        formatted_response = json.dumps(parsed_response, indent = 4, ensure_ascii = False)
        return formatted_response
