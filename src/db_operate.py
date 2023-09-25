
import traceback
from db_base import Db_Base
from datetime import datetime, timedelta

class Db_Operate(Db_Base):
    '''DB操作関連の処理'''
    def __init__(self):
        super().__init__()

    def select_buying_power(self, latest = False):
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
                row = cursor.fetchall()

                # データが存在しない場合
                if len(row) == 0:
                    return {}

                return row
        except Exception as e:
            self.error_output('余力テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def select_orders(self, yet = False):
        '''
        注文テーブル(orders)から注文情報を取得する

        Args:
            yet(bool): 未約定注文のみ取得するか

        Returns:
            list[dict{}, dict{}...]: 注文情報
                order_id(str): 注文ID
                reverse_order_id(str): 反対注文ID
                stock_code(float): 証券コード
                order_price(int): 注文価格
                    成行は-1.0
                order_volume(int): 注文株数
                transaction_price(float): 平均約定価格
                buy_sell(str): 売買区分
                    1: 売、2: 買
                cash_margin(str): 信用区分
                    1: 現物、2: 信用新規、3:信用返済
                margin_type(str): 信用取引区分
                    0: 現物、1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ)
                profit(float): 損益額
                    決済注文のみ、新規注文は0.0
                status(str): 注文ステータス
                    1: 未約定、2: 約定済、3:取消済
                order_date(datetime): 注文日時
                transaction_date(datetime): 約定日時
                update_date(datetime): 更新日時

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = ''''
                    SELECT
                        order_id,
                        reverse_order_id,
                        stock_code,
                        order_price,
                        order_volume,
                        transaction_price,
                        buy_sell,
                        cash_margin,
                        margin_type,
                        profit,
                        status,
                        order_date,
                        transaction_date,
                        update_date
                    FROM
                        orders
                '''

                # 未約定のみ抽出するの条件を追加
                if yet: sql += 'WHERE status = 1'

                cursor.execute(sql)
                rows = cursor.fetchall()

                # データが存在しない場合
                if len(rows) == 0:
                    return [{}]

                return rows
        except Exception as e:
            self.error_output('注文テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def select_errors_minite(self):
        '''
        エラーテーブル(errors)から1分以内に追加されたレコード数を取得する

        Returns:
            count(int): 1分以内のエラー発生数

        '''
        try:
            one_minute_ago = datetime.now() - timedelta(minutes = 1)

            with self.conn.cursor(self.dict_return) as cursor:
                sql = ''''
                    SELECT
                        CONUT(1)
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
            self.error_output('エラー件数取得処理でエラー', e, traceback.format_exc())
            return False

    def insert_buying_power(self, data):
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
            self.error_output('余力テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def insert_orders(self, data):
        '''
        注文テーブル(orders)へレコードを追加する

        Args:
            data(dict): 追加するデータ
                order_id(str): 注文ID[必須]
                reverse_order_id(str): 反対注文ID[任意]
                stock_code(float): 証券コード[必須]
                order_price(int): 注文価格[必須]
                    成行は-1.0
                order_volume(int): 注文株数[必須]
                buy_sell(str): 売買区分[必須]
                    1: 売、2: 買
                cash_margin(str): 信用区分[必須]
                    1: 現物、2: 信用新規、3:信用返済
                margin_type(str): 信用取引区分[必須]
                    0: 現物、1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ)
                status(str): 注文ステータス[必須]
                    1: 未約定、2: 約定済、3:取消済
                order_date(datetime): 注文日時[必須]

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO orders
                    (
                        order_id,
                        reverse_order_id,
                        stock_code,
                        order_price,
                        order_volume,
                        buy_sell,
                        cash_margin,
                        margin_type,
                        status,
                        order_date
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
                        %s
                    )
                '''

                cursor.execute(sql, (
                    data['order_id'],
                    data['reverse_order_id'],
                    data['stock_code'],
                    data['order_price'],
                    data['order_volume'],
                    data['buy_sell'],
                    data['cash_margin'],
                    data['margin_type'],
                    '1', # ステータス: 未約定
                    data['order_date']
                ))

            return True
        except Exception as e:
            self.error_output('注文テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def insert_boards(self, board_info):
        '''
        板情報(学習用)テーブル(boards)へレコードを追加する

        Args:
            borad_info(dict): 追加するデータ
                stock_code(str or int):  証券コード[]
                market_code(str or int): 市場コード[]
                price(float): 現在株価[]
                latest_transaction_date(datetime): 直近約定時刻[]
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
                        latest_transaction_date,
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
                    board_info['latest_transaction_date'],
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
            self.error_output('エラー情報テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def insert_errors(self, content):
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
            self.error_output('エラー情報テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def update_orders_status(self, order_id, status):
        '''
        注文テーブル(orders)のステータスを更新する

        Args:
            order_id(str): 注文ID
            status(str or int): 更新後のステータス
                1: 未約定、2: 約定済、3:取消済

        Returns:
            result(bool): SQL実行結果

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE
                        orders
                    SET
                        status = %s
                    WHERE
                        order_id = %s
                '''

                cursor.execute(sql, (
                    status,
                    order_id
                ))

            return True
        except Exception as e:
            self.error_output(f'注文テーブルのステータス更新処理でエラー', e, traceback.format_exc())
            return False

##### 以下テンプレ ######
    def select_tablename(self):
        '''
        SELECT

        Args:

        Returns:
        '''
        try:
            # cursorの引数をなくすとタプルで返る
            with self.conn.cursor(self.dict_return) as cursor:
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
