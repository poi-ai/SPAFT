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
            self.log = Log(logger_filename)
        else:
            self.log = Log(Path(inspect.stack()[1].filename).stem)

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

class Log():
    '''
    loggerの設定を簡略化
        ログファイル名は呼び出し元のファイル名
        出力はINFO以上のメッセージのみ

    Args:
        output(int):出力タイプを指定
                    0:ログのみ出力、1:コンソールのみ出力、空:両方出力

    '''
    def __init__(self, filename = '', output = None):
        self.log = logging.getLogger()
        self.output = output
        self.filename = filename
        self.today = self.now().strftime("%Y%m%d")
        self.set()

    def set(self):
        # 重複出力防止処理 / より深いファイルをログファイル名にする
        for h in self.log.handlers[:]:
            # 起動中ログファイル名を取得
            log_path = re.search(r'<FileHandler (.+) \(INFO\)>', str(h))
            # 出力対象/占有ロックから外す
            self.log.removeHandler(h)
            h.close()
            # ログファイルの中身が空なら削除
            if log_path != None:
                if os.stat(log_path.group(1)).st_size == 0:
                    os.remove(log_path.group(1))

        # フォーマットの設定
        formatter = logging.Formatter(f'%(asctime)s ({os.getpid()})  [%(levelname)s] %(message)s')

        # 出力レベルの設定
        self.log.setLevel(logging.INFO)

        # ログ出力設定
        if self.output != 1:
            # リポジトリのルートフォルダを指定
            log_folder = os.path.join(os.path.dirname(__file__), '..', 'log')
            # ログフォルダチェック。無ければ作成
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
            # 出力先を設定
            handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.now().strftime("%Y%m%d")}.log'), encoding = 'utf-8')
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.log.addHandler(handler)

        # コンソール出力設定
        if self.output != 0:
            # ハンドラの設定
            handler = logging.StreamHandler(sys.stdout)
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.log.addHandler(handler)

    def date_check(self):
        '''日付変更チェック'''
        date = self.now().strftime("%Y%m%d")
        if self.today != date:
            self.today = date
            # PG起動中に日付を超えた場合はログ名を設定しなおす
            self.set()

    def now(self):
        '''現在のJSTを取得'''
        return datetime.utcnow() + timedelta(hours = 9)

    def debug(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.log.debug(f'{message} [{file_name} in {line}]')

    def info(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.log.info(f'{message} [{file_name} in {line}]')

    def warning(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.log.warning(f'{message} [{file_name} in {line}]')

    def error(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.log.error(f'{message} [{file_name} in {line}]')

    def error(self, message, error_content = '', stack_trace = ''):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        error_message = f'{message} [{file_name} in {line}]'

        if error_content != '':
            error_message += f'\n{error_content}'

        if stack_trace != '':
            error_message += f'\n{stack_trace}'

        self.log.error(error_message)

    def critical(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.log.critical(f'{message} [{file_name} in {line}]')

    def call_info(self, stack):
        '''
        ログ呼び出し元のファイル名と行番号を取得する

        Args:
            stack(list): 呼び出し元のスタック

        Returns:
            os.path.basename(stack[1].filename)(str): 呼び出し元ファイル名
            stack[1].lineno(int): 呼び出し元行番号

        '''
        if os.path.basename(stack[1].filename) == 'base.py':
            return os.path.basename(stack[2].filename), stack[2].lineno
        else:
            return os.path.basename(stack[1].filename), stack[1].lineno