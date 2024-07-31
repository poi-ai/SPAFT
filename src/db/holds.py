import traceback

class Holds():
    '''holdsテーブルを操作する'''

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

    def select(self, symbol = None, exchange = None, outstanding = True, today = True):
        '''
        保有株注文テーブル(orders)から注文情報を取得する

        Args:
            絞り込み条件を指定できる。全て任意
            symbol(str): 証券コード
            exchange(str): 市場コード
            outstanding(bool): 未決済のみ取得するか
            today(bool): 今日の注文のみ取得するか

        Returns:
            result(bool): 実行結果
            list[dict{}, dict{}...]: 保有株情報 or エラーメッセージ(str)
                id(str): 建玉ID
                symbol(str): 証券コード
                exchange(str): 市場コード
                leaves_qty(int): 保有株数(返済注文中株数含む)
                free_qty(int): 注文可能株数
                price(float): 平均約定単価
                created_at(datetime): レコード追加時間
                update_at(datetime): レコード更新時間

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = ''''
                    SELECT
                        id,
                        symbol,
                        exchange,
                        leaves_qty,
                        free_qty,
                        price,
                        created_at,
                        updated_at
                    FROM
                        holds
                '''

                # WHERE文の生成
                condition = []
                if symbol is not None: condition.append(f' symbol = {symbol} ')
                if exchange is not None: condition.append(f' exchange = {exchange} ')
                if outstanding is True: condition.append(' leaves_qty > 0 ')
                if today is True: condition.append(' DATE(created_at) = CURDATE() ')

                if len(condition) != 0:
                    sql += ' WHERE ' + ' AND '.join(condition)

                cursor.execute(sql)
                rows = cursor.fetchall()

                # データが存在しない場合
                if len(rows) == 0:
                    return True, [{}]

                return True, rows
        except Exception as e:
            self.log.error()
            return False, f'保有株テーブル取得処理でエラー\n{e}\n{traceback.format_exc()}'

    def insert(self, data):
        '''
        保有株テーブル(holds)へレコードを追加する

        Args:
            data(dict): 追加するデータ
                id(str): 建玉ID[必須]
                symbol(str): 証券コード[必須]
                exchange(str): 市場コード[必須]
                leaves_qty(int): 保有株数(返済注文中株数含む)[必須]
                free_qty(int): 注文可能株数[必須]
                price(float): 平均約定単価[必須]

        Returns:
            True(bool): SQL実行成功 or エラーメッセージ(str)
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO orders
                    (
                        id,
                        symbol,
                        exchange,
                        leaves_qty,
                        hold_qty,
                        price
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                    )
                '''

                cursor.execute(sql, (
                    data['id'],
                    data['symbol'],
                    data['exchange'],
                    data['leaves_qty'],
                    data['hold_qty'],
                    data['price']
                ))

            return True
        except Exception as e:
            return f'保有株テーブルへのレコード追加処理でエラー\n{e}\n{traceback.format_exc()}'

    def update_status(self, holds_id, leaves_qty, free_qty):
        '''
        保有株テーブル(holds)の株数を更新する

        Args:
            holds_id(str): 建玉ID
            leaves_qty(int): 更新後の保有株数 ※省略可
            free_qty(int): 更新後の注文可能株数 ※省略可

        Returns:
            True(bool): SQL実行成功 or エラーメッセージ(str)
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE
                        holds
                    SET
                        leaves_qty = %s,
                        free_qty = %s
                    WHERE
                        holds_id = %s
                '''

                cursor.execute(sql, (
                    leaves_qty,
                    free_qty,
                    holds_id
                ))

            return True
        except Exception as e:
            return f'保有株テーブルの更新処理でエラー\n{e}\n{traceback.format_exc()}'
