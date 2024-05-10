import traceback

class Buying_Power():
    '''buying_powerテーブルを操作する'''

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

    def select(self, latest = False):
        '''
        余力テーブル(buying_power)から余力情報を取得する

        Args:
            latest(bool): 最新の余力のみ取得するか

        Returns:
            list[dict{}, dict{},..]: 余力情報
                id(int): ID
                total_assets(int): 総資産額
                total_margin(int): 信用株式保有合計額
                api_flag(str): APIから取得したか(1: APIから取得、0: DBから計算)
                created_at(datetime): レコード追加日時

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = ''''
                    SELECT
                        id,
                        total_assets,
                        total_margin,
                        api_flag,
                        created_at
                    FROM
                        buying_power
                '''

                if latest: sql += 'ORDER BY id desc limit 1'

                cursor.execute(sql)

                if latest:
                    rows = cursor.fetchone()
                else:
                    rows = cursor.fetchall()

                # データが存在しない場合
                if len(rows) == 0:
                    return []

                return rows
        except Exception as e:
            self.log.error('余力テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def insert(self, data):
        '''
        余力テーブル(buying_power)へレコードを追加する

        Args:
            data(dict): 追加するデータ
                total_assets(int or str): 総資産額[必須]
                total_margin(int or str): 信用株式保有額[必須]
                api_flag(int or str): APIから取得したか[必須]

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO buying_power
                    (
                        total_assets,
                        total_margin,
                        api_flag
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                '''

                cursor.execute(sql, (
                    data['total_assets'],
                    data['total_margin'],
                    data['api_flag']
                ))

            return True
        except Exception as e:
            self.log.error('余力テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False
