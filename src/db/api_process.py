import traceback

class Api_Process():
    '''api_processテーブルを操作する'''

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

    def select(self, api_name = None, latest = False):
        '''
        APIプロセス管理テーブル(api_process)からデータを取得する

        Args:
            絞り込みを行う場合のみ指定
            api_name(str): API／プロセス名[任意]
            latest(bool): 実行時間の最新順にデータを取得する[任意]

        Returns:
            rows(dict): APIプロセス管理テーブルに格納されているデータ

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        name,
                        status,
                        api_exec_time,
                        created_at,
                        updated_at
                    FROM
                        api_process
                '''

                # API名を指定しているか
                if api_name is not None:
                    sql += ' WHERE name = %s'
                    # 最新のみ取得か
                    if latest:
                        sql += ' order by api_exec_time desc'
                    cursor.execute(sql, (api_name))
                else:
                    cursor.execute(sql)

                rows = cursor.fetchall()

                if rows:
                    return rows
                else:
                    return []

        except Exception as e:
            self.log.error('APIプロセス管理テーブル取得処理でエラー', e, traceback.format_exc())
            return False

