import pymysql
import traceback
from db_base import Db_Base
from datetime import datetime, timedelta

class Db_Operate(Db_Base):
    '''DB操作関連の処理'''
    def __init__(self):
        super().__init__()

##### 以下テンプレ ######
    def select_tablename(self):
        '''
        SELECT

        Args:

        Returns:
        '''
        try:
            # cursorの引数をなくすとタプルで返る
            with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = ''''
                    SELECT
                        xx
                    FROM
                        xx
                    WHERE
                        xx
                '''

                cursor.execute(sql)

                # 1行だけ抜き出す
                #row = cursor.fetchone()
                # 引数なし,データなし -> None
                # 引数なし,データあり -> tuple
                # pymysql.cursors.DictCursor,データなし -> None
                # pymysql.cursors.DictCursor,データあり -> dict


                # 全行抜き出す
                rows = cursor.fetchall()
                # 引数なし,データなし -> 空tuple
                # 引数なし,データ1行 -> tuple
                # 引数なし,データ複数行 -> tuple(tuple,tuple,...)
                # pymysql.cursors.DictCursor,データなし -> 空tuple
                # pymysql.cursors.DictCursor,データ1行 -> list[dict]
                # pymysql.cursors.DictCursor,データ複数行 -> list[dict,dict,...]

                # 指定した行数抜き出す
                num = 100
                rows = cursor.fetchmany(num)
                # fetchallと同
        except Exception as e:
            self.error_output('xxでエラー', e, traceback.format_exc())
            return False

    def insert_tablename(self):
        '''
        INSERT

        Args:

        Returns:
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO xxx
                    (
                        aaa,
                        bbb,
                        num
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                '''

                    # プレースホルダーはintでもstrでも受け入れてくれるのでとりあえず%sにしとけば良い

                cursor.execute(sql, (
                    'huga',
                    '77',
                    100,
                ))

            return True
        except Exception as e:
            self.error_output('xxxへのINSERTでエラー', e, traceback.format_exc())
            return False

    def update_tablename(self):
        '''
        UPDATE

        Args:

        Returns:

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE
                        xx
                    SET
                        xx = %s,
                        xx = %s
                    WHERE
                        xx = %s
                '''

                cursor.execute(sql, (
                    'hoge',
                    77
                ))

            return True
        except Exception as e:
            self.error_output(f'xxのUPDATEでエラー', e, traceback.format_exc())
            return False

    def delete_tablename(self):
        '''
        DELETE

        Args:

        Returns:

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    DELETE FROM
                        xx
                    WHERE
                        xx = %s
                '''

                cursor.execute(sql, (
                    'hoge'
                ))

            return True
        except Exception as e:
            self.error_output(f'xxのDELETEでエラー', e, traceback.format_exc())
            return False


    def sample_transaction(self):
        '''
        Transaction

        Args:

        Returns:
        '''
        with self.conn.cursor() as cursor:

            # self.start_transaction()

            # INSERT 追加するデータとカーソルを引数で渡す
            # result = self.insert_test(data, cursor)

            # UPDATE 更新するデータとか条件とかカーソルを引数で渡す
            # result = self.update_test(data, conditions, cursor)

            # UPDATE 削除する条件とかカーソルを引数で渡す
            # result = self.delete_test(data, cursor)

            # それぞれの処理後に返り値で実行結果を受け取って コミットかロールバックか
            # if result:
            #     self.commit()
            # else:
            #     self.rollback()

            # SQL実行結果をself.transaction_flagに突っ込んだ後に
            # self.end_transaction()
            # でもよい
            pass

        return True

db = Db_Operate()
db.insert_tablename()