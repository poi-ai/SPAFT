import config
import inspect
import pymysql
import traceback
from base import Base
from pathlib import Path

class Db_Base(Base):
    '''データベース接続/操作を簡略化するための共通クラス'''

    def __init__(self):
        super().__init__(Path(inspect.stack()[1].filename).stem)
        self.conn = self.connect()
        self.conn.autocommit(True)
        self.dict_return = pymysql.cursors.DictCursor
        self.transaction_flag = True

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
        self.logger.info('トランザクション開始')
        self.conn.autocommit(False)
        self.transaction_flag = True

    def end_transaction(self):
        '''トランザクション終了'''
        self.logger.info('トランザクション終了')
        if self.transaction_flag:
            self.commit()
        else:
            self.rollback()
        self.conn.autocommit(True)

    def commit(self):
        '''コミット'''
        try:
            self.conn.commit()
        except Exception as e:
            self.error_output('コミット処理でエラー', e, traceback.format_exc())
            self.rollback()
            return

    def rollback(self):
        '''ロールバック'''
        try:
            self.conn.rollback()
        except Exception as e:
            self.error_output('ロールバック処理でエラー', e, traceback.format_exc())
            return

    def execute(self, query):
        '''クエリ実行'''
        try:
            with self.conn.cursor() as cursor:
                self.logger.info(f'クエリ実行：{query}')
                cursor.execute(query)
        except Exception as e:
            self.error_output('クエリ実行でエラー', e, traceback.format_exc())
            return

