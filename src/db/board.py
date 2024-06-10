import traceback

class Board():
    '''boardテーブルを操作する'''

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

    def insert(self, board_info):
        '''
        板情報(学習用)テーブル(boards)へレコードを追加する

        Args:
            borad_info(dict): 追加するデータ
                stock_code(str):  証券コード[]
                market_code(str or int): 市場コード[]
                price(float): 現在株価[]
                latest_transaction_time(datetime): 直近約定時刻[]
                change_status(): []
                present_status(): []
                market_buy_qty(): []
                buy1_sign(): []
                buy1_price(): []
                buy1_qty(): []
                buy2_price(): []
                buy2_qty(): []
                buy3_price(): []
                buy3_qty(): []
                buy4_price(): []
                buy4_qty(): []
                buy5_price(): []
                buy5_qty(): []
                buy6_price(): []
                buy6_qty(): []
                buy7_price(): []
                buy7_qty(): []
                buy8_price(): []
                buy8_qty(): []
                buy9_price(): []
                buy9_qty(): []
                buy10_price(): []
                buy10_qty(): []
                market_sell_qty(): []
                sell1_sign(): []
                sell1_price(): []
                sell1_qty(): []
                sell2_price(): []
                sell2_qty(): []
                sell3_price(): []
                sell3_qty(): []
                sell4_price(): []
                sell4_qty(): []
                sell5_price(): []
                sell5_qty(): []
                sell6_price(): []
                sell6_qty(): []
                sell7_price(): []
                sell7_qty(): []
                sell8_price(): []
                sell8_qty(): []
                sell9_price(): []
                sell9_qty(): []
                sell10_price(): []
                sell10_qty(): []
                over_qty(): []
                under_qty(): []

        Returns:
            result(bool): SQL実行結果
        '''
        # TODO TODO TODO TODO TODO TODO
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO boards
                    (
                        stock_code,
                        market_code,
                        price,
                        latest_transaction_time,
                        change_status,
                        present_status,
                        market_buy_qty,
                        buy1_sign,
                        buy1_price,
                        buy1_qty,
                        buy2_price,
                        buy2_qty,
                        buy3_price,
                        buy3_qty,
                        buy4_price,
                        buy4_qty,
                        buy5_price,
                        buy5_qty,
                        buy6_price,
                        buy6_qty,
                        buy7_price,
                        buy7_qty,
                        buy8_price,
                        buy8_qty,
                        buy9_price,
                        buy9_qty,
                        buy10_price,
                        buy10_qty,
                        market_sell_qty,
                        sell1_sign,
                        sell1_price,
                        sell1_qty,
                        sell2_price,
                        sell2_qty,
                        sell3_price,
                        sell3_qty,
                        sell4_price,
                        sell4_qty,
                        sell5_price,
                        sell5_qty,
                        sell6_price,
                        sell6_qty,
                        sell7_price,
                        sell7_qty,
                        sell8_price,
                        sell8_qty,
                        sell9_price,
                        sell9_qty,
                        sell10_price,
                        sell10_qty,
                        over_qty,
                        under_qty
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                '''

                cursor.execute(sql, (
                    board_info['stock_code'],
                    board_info['market_code'],
                    board_info['price'],
                    board_info['latest_transaction_time'],
                    board_info['change_status'],
                    board_info['present_status'],
                    board_info['market_buy_qty'],
                    board_info['buy1_sign'],
                    board_info['buy1_price'],
                    board_info['buy1_qty'],
                    board_info['buy2_price'],
                    board_info['buy2_qty'],
                    board_info['buy3_price'],
                    board_info['buy3_qty'],
                    board_info['buy4_price'],
                    board_info['buy4_qty'],
                    board_info['buy5_price'],
                    board_info['buy5_qty'],
                    board_info['buy6_price'],
                    board_info['buy6_qty'],
                    board_info['buy7_price'],
                    board_info['buy7_qty'],
                    board_info['buy8_price'],
                    board_info['buy8_qty'],
                    board_info['buy9_price'],
                    board_info['buy9_qty'],
                    board_info['buy10_price'],
                    board_info['buy10_qty'],
                    board_info['market_sell_qty'],
                    board_info['sell1_sign'],
                    board_info['sell1_price'],
                    board_info['sell1_qty'],
                    board_info['sell2_price'],
                    board_info['sell2_qty'],
                    board_info['sell3_price'],
                    board_info['sell3_qty'],
                    board_info['sell4_price'],
                    board_info['sell4_qty'],
                    board_info['sell5_price'],
                    board_info['sell5_qty'],
                    board_info['sell6_price'],
                    board_info['sell6_qty'],
                    board_info['sell7_price'],
                    board_info['sell7_qty'],
                    board_info['sell8_price'],
                    board_info['sell8_qty'],
                    board_info['sell9_price'],
                    board_info['sell9_qty'],
                    board_info['sell10_price'],
                    board_info['sell10_qty'],
                    board_info['over_qty'],
                    board_info['under_qty']
                ))

            return True
        except Exception as e:
            return f'エラー情報テーブルへのレコード追加処理でエラー\n{e}\n{traceback.format_exc()}'

    def select_specify_of_time(self, stock_code, start_time, end_time):
        '''
        指定した期間内に作成されたレコードを取得する

        Args:
            stock_code(str): 証券コード
            start_time(str, YYYY-MM-DD HH:MM): 対象の最古の時間
            end_time(str, YYYY-MM-DD HH:MM): 対象の最新の時間

        Returns:
            result(bool): 実行結果
            records(list[dict,dict,...] or str): 取得したレコード or エラーメッセージ
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        *
                    FROM
                        boards
                    WHERE
                        stock_code = %s
                    AND
                        created_at BETWEEN %s AND %s
                    ORDER BY
                        created_at
                '''
                cursor.execute(sql, (stock_code, start_time, end_time))
                records = cursor.fetchall()
        except Exception as e:
            return False, f'boardテーブルから指定期間内のレコードを取得する処理でエラー\n{e}\n{traceback.format_exc()}'

        return True, records