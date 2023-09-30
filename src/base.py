import config
import inspect
import json
import logging
import os
import sys
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

class Base():
    '''共通処理のloggerインスタンス生成とエラー通知メソッドを記載'''

    def __init__(self, logger_filename = None):
        if logger_filename != None:
            self.logger = Log(logger_filename)
        else:
            self.logger = Log(Path(inspect.stack()[1].filename).stem)

    def error_output(self, message, e = None, stacktrace = None, line_flg = True):
        '''エラー時のログ出力/LINE通知を行う

        Args:
            message(str) : エラーメッセージ
            e(str) : エラー名
            stacktrace(str) : スタックトレース(traceback.format_exc())
        '''
        other_message = message
        self.logger.error(message)

        if e != None:
            self.logger.error(e)
            other_message += f'\n{e}'

        if stacktrace != None:
            self.logger.error(stacktrace)
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
            self.logger.info('LINE Notifyでの送信メッセージが10000字を超えました')
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
            self.logger.error('LINE Notify APIでのメッセージ送信に失敗しました')
            self.logger.error(e)
            return

        if r.status_code != 200:
            self.logger.error('LINE Notify APIでエラーが発生しました')
            self.logger.error('ステータスコード：' + r.status_code)
            try:
                self.logger.error('エラー内容：' + json.dumps(json.loads(r.content), indent=2))
            except Exception as e:
                self.logger.error(e)
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

class Log():
    '''loggerの設定を簡略化
        ログファイル名は呼び出し元のファイル名
        出力はINFO以上のメッセージのみ

    Args:
        output(int):出力タイプを指定
                    0:ログのみ出力、1:コンソールのみ出力、空:両方出力

    '''
    def __init__(self, filename = '', output = None):
        self.logger = logging.getLogger()
        self.output = output
        self.filename = filename
        self.today = (datetime.utcnow() + timedelta(hours = 9)).strftime("%Y%m%d")
        self.set()

    def set(self):
        # 重複出力防止処理 / より深いファイルをログファイル名にする
        for h in self.logger.handlers[:]:
            # 起動中ログファイル名を取得
            log_path = re.search(r'<FileHandler (.+) \(INFO\)>', str(h))
            # 出力対象/占有ロックから外す
            self.logger.removeHandler(h)
            h.close()
            # ログファイルの中身が空なら削除
            if log_path != None:
                if os.stat(log_path.group(1)).st_size == 0:
                    os.remove(log_path.group(1))

        # フォーマットの設定
        formatter = logging.Formatter(f'%(asctime)s {self.filename.rjust(15, " ")} - [%(levelname)s] %(message)s')

        # 出力レベルの設定
        self.logger.setLevel(logging.INFO)

        # ログ出力設定
        if self.output != 1:
            # リポジトリのルートフォルダを指定
            repos_root = os.path.join(os.path.dirname(__file__), '..')
            log_folder = os.path.join(repos_root, 'log')
            # ログフォルダチェック。無ければ作成
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
            # 出力先を設定
            handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.today}.log'), encoding = 'utf-8')
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

        # コンソール出力設定
        if self.output != 0:
            # ハンドラの設定
            handler = logging.StreamHandler(sys.stdout)
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

    def date_check(self):
        '''日付変更チェック'''
        date = (datetime.utcnow() + timedelta(hours = 9)).strftime("%Y%m%d")
        if self.today != date:
            self.today = date
            # PG起動中に日付を超えた場合はログ名を設定しなおす
            self.set()

    def debug(self, message):
        self.date_check()
        self.logger.debug(message)

    def info(self, message):
        self.date_check()
        self.logger.info(message)

    def warning(self, message):
        self.date_check()
        self.logger.warning(message)

    def error(self, message):
        self.date_check()
        self.logger.error(message)

    def critical(self, message):
        self.date_check()
        self.logger.critical(message)

