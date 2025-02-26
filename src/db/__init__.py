import pymysql
import traceback
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .api_process import Api_Process
from .board import Board
from .buying_power import Buying_Power
from .errors import Errors
from .holds import Holds
from .listed import Listed
from .ohlc import Ohlc
from .orders import Orders

class Db():
    def controller_init(self, log, db_info):
        '''起動ファイルから呼び出す場合'''
        self.log = log

        # MySQLへ接続
        self.conn = self.connect(db_info)

        # 接続失敗したら処理終了
        if self.conn == False: exit()

        # SQL実行時に自動的にcommitになるように
        self.conn.autocommit(True)

        return self.conn

    def service_init(self, log, conn, db_info):
        self.log = log

        self.db_info = db_info

        # SELECT文の返しをdict型にする
        dict_return = pymysql.cursors.DictCursor

        self.api_process = Api_Process(log, conn, dict_return)
        self.board = Board(log, conn, dict_return)
        self.buying_power = Buying_Power(log, conn, dict_return)
        self.errors = Errors(log, conn, dict_return)
        self.holds = Holds(log, conn, dict_return)
        self.listed = Listed(log, conn, dict_return)
        self.ohlc = Ohlc(log, conn, dict_return)
        self.orders = Orders(log, conn, dict_return)

    def connect(self, db_info):
        '''データベースへの接続

        Args:
            db_info(dict): DB接続情報
        '''
        try:
            conn = pymysql.connect(
                host = db_info['host'],
                user = db_info['user'],
                password = db_info['password'],
                db = db_info['db']
            )
        except Exception as e:
            self.log.error(f'データベースに接続できません\n{e}')
            return False

        return conn

    def start_transaction(self):
        '''トランザクション開始'''
        self.log.info('トランザクション開始')
        self.conn.autocommit(False)
        self.transaction = True

    def end_transaction(self):
        '''トランザクション終了'''
        self.log.info('トランザクション終了')
        if self.transaction:
            self.commit()
        else:
            self.rollback()
        self.conn.autocommit(True)

    def commit(self):
        '''コミット'''
        try:
            self.log.info('コミット開始')
            self.conn.commit()
            self.log.info('コミット完了!')
        except Exception as e:
            self.log.error('コミットでエラー', e, traceback.format_exc())
            self.rollback()
            return

    def rollback(self):
        '''ロールバック'''
        try:
            self.log.info('ロールバック開始')
            self.conn.rollback()
            self.log.info('ロールバック完了!')
        except Exception as e:
            self.log.error('ロールバックでエラー', e, traceback.format_exc())
            return