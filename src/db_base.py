import config
import pymysql
import traceback

class Db_Base():
    '''データベース接続/操作を簡略化するための共通クラス'''

    def __init__(self, log):
        self.log = log
        self.conn = self.connect()
        self.conn.autocommit(True)
        self.dict_return = pymysql.cursors.DictCursor
        self.transaction = True

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

