import pymysql
import traceback
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_process import Api_Process
from board import Board
from buying_power import Buying_Power
from errors import Errors
from listed import Listed
from orders import Orders

class Db():
    def __init__(self, log):
        '''
        初期設定処理

        Args:
            log(Log): カスタムログクラスのインスタンス

        '''
        self.log = log
        self.conn = self.connect()
        self.conn.autocommit(True)
        self.dict_return = pymysql.cursors.DictCursor
        self.transaction = False

        self.api_process = Api_Process(log, self.conn, self.dict_return)
        self.board = Board(log, self.conn, self.dict_return)
        self.buying_power = Buying_Power(log, self.conn, self.dict_return)
        self.errors = Errors(log, self.conn, self.dict_return)
        self.listed = Listed(log, self.conn, self.dict_return)
        self.orders = Orders(log, self.conn, self.dict_return)

    def connect(self):
        '''データベースへの接続'''
        return pymysql.connect(
            host = 'localhost',
            user = 'root',
            password = 'root',
            db = 'spaft'
        )

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