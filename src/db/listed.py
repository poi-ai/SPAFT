import traceback

class Listed():
    '''listedテーブルを操作する'''

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

    def select(self, listed_flg = None):
        '''
        上場情報テーブル(listed)からデータを取得する

        Args:
            listed_flg(int or str): 上場企業に割り振られているか[任意]
                0: 上場企業に割り振られていないコードのみ取得
                1: 上場企業に割り振られているコードのみ取得

        Returns:
            rows(dict): 上場情報テーブルに格納されているデータ

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        stock_code,
                        market_code,
                        listed_flg
                    FROM
                        listed
                '''

                if listed_flg is not None:
                    sql += ' WHERE listed_flg = %s'
                    cursor.execute(sql, (listed_flg))
                else:
                    cursor.execute(sql)

                rows = cursor.fetchall()

                if rows:
                    return rows
                else:
                    return []

        except Exception as e:
            self.log.error('上場コードテーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def insert(self, stock_code, listed_flg):
        '''
        上場情報テーブル(errors)へレコードを追加する

        Args:
            stock_code(int or str): 銘柄コード
            listed_flg(int or str): 上場中フラグ

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    INSERT INTO listed
                    (
                        stock_code,
                        market_code,
                        listed_flg
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                '''

                cursor.execute(sql, (
                    stock_code,
                    1,
                    listed_flg
                ))

            return True
        except Exception as e:
            self.log.error('上場情報テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def update(self, stock_code, listed_flg):
        '''
        上場情報テーブル(listed)のステータスを更新する

        Args:
            stock_code(int or str): 銘柄コード
            listed_flg(int or str): 上場中フラグ

        Returns:
            result(bool): SQL実行結果

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE
                        listed
                    SET
                        listed_flg = %s
                    WHERE
                        stock_code = %s
                '''

                cursor.execute(sql, (
                    listed_flg,
                    stock_code
                ))

            return True
        except Exception as e:
            self.log.error(f'上場情報テーブルのステータス更新処理でエラー', e, traceback.format_exc())
            return False

    def delete(self, stock_code):
        '''
        上場情報テーブル(errors)のレコードを削除する

        Args:
            stock_code(str): 銘柄コード

        Returns:
            result(bool): SQL実行結果

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    DELETE FROM
                        listed
                    WHERE
                        stock_code = %s,
                        market_code = 1
                '''

                cursor.execute(sql, (
                    stock_code
                ))

            return True
        except Exception as e:
            self.log.error(f'上場コードテーブルの削除処理でエラー', e, traceback.format_exc())
            return False
