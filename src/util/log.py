import logging
import inspect
import os
import sys
import re
from datetime import datetime, timedelta

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
        self.logger = logging.getLogger()
        self.output = output
        self.filename = filename
        self.today = self.now().strftime("%Y%m%d")
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
        formatter = logging.Formatter(f'%(asctime)s ({os.getpid()})  [%(levelname)s] %(message)s')

        # 出力レベルの設定
        self.logger.setLevel(logging.INFO)

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
        self.logger.debug(f'{message} [{file_name} in {line}]')

    def info(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.info(f'{message} [{file_name} in {line}]')

    def warning(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.warning(f'{message} [{file_name} in {line}]')

    def error(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.error(f'{message} [{file_name} in {line}]')

    def critical(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.critical(f'{message} [{file_name} in {line}]')

    def call_info(self, stack):
        '''
        ログ呼び出し元のファイル名と行番号を取得する

        Args:
            stack(list): 呼び出し元のスタック

        Returns:
            os.path.basename(stack[1].filename)(str): 呼び出し元ファイル名
            stack[1].lineno(int): 呼び出し元行番号

        '''
        return os.path.basename(stack[1].filename), stack[1].lineno