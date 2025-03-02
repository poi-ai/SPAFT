import traceback
from datetime import datetime, timedelta

class Errors():
    '''errorsテーブルを操作する'''

    def __init__(self, log, conn, dict_return):
        '''
        Args:
            log(Log): カスタムログクラスのインスタンス
            conn(): DB接続クラスのインスタンス
            dict_return(): SQLの結果をdict型で返すためのクラス名

        '''
        self.log = log
        self.conn = conn
        self.dict_return = dict_return

    def select(self, minute = 1):
        '''
        エラーテーブル(errors)からx分以内に追加されたレコード数を取得する

        Args:
            minute(int): 何分以内か

        Returns:
            count(int): x分以内のエラー発生数

        '''
        try:
            one_minute_ago = datetime.now() - timedelta(minutes = minute)

            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        COUNT(1)
                    FROM
                        errors
                    WHERE
                        created_at >= %s
                '''

                cursor.execute(sql, (one_minute_ago,))
                row = cursor.fetchone()

                if row:
                    return int(row[0])
                else:
                    return 0

        except Exception as e:
            self.log.error('エラー件数取得処理でエラー', e, traceback.format_exc())
            return False

    def insert(self, content):
        '''
        エラー情報テーブル(errors)へレコードを追加する

        Args:
            content(str): 処理名

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO error
                    (
                        name,
                        content
                    )
                    VALUES
                    (
                        %s,
                        %s
                    )
                '''

                cursor.execute(sql, (
                    'scalping', # いずれ引数に
                    content
                ))

            return True
        except Exception as e:
            self.log.error('エラー情報テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

