
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

                if latest:
                    rows = cursor.fetchone()
                else:
                    rows = cursor.fetchall()

                # データが存在しない場合
                if len(rows) == 0:
                    return []

                return rows
        except Exception as e:
            self.error_output('余力テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def select_orders(self, yet = False, order_price = None,
                      new_order = None, reverse_order = None):
        '''
        注文テーブル(orders)から注文情報を取得する

        Args:
            絞り込み条件を指定できる。全て任意
            yet(bool): 未約定注文のみ取得するか
            order_price(int): 指定した価格の注文のみ取得
            new_order(bool): 新規注文のみ取得
            reverse_order(bool): 決済注文のみ取得

        Returns:
            list[dict{}, dict{}...]: 注文情報
                order_id(str): 注文ID
                reverse_order_id(str): 反対注文ID
                stock_code(float): 証券コード
                order_price(float): 注文価格
                    成行は-1.0
                order_qty(int): 注文株数
                transaction_price(float): 平均約定価格
                buy_sell(str): 売買区分
                    1: 売、2: 買
                cash_margin(str): 信用区分
                    1: 現物買、2: 現物売、3: 信用新規、4:信用返済
                margin_type(str): 信用取引区分
                    0: 現物、1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ)
                fee(float): 取引手数料
                interest(float): 金利
                profit(float): 損益額
                    決済注文のみ、新規注文は0.0
                status(str): 注文ステータス
                    0: 未約定、1: 約定済、2: 取消中、3: 取消済
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
                        order_qty,
                        transaction_price,
                        buy_sell,
                        cash_margin,
                        margin_type,
                        fee,
                        interest,
                        profit,
                        status,
                        order_date,
                        transaction_date,
                        update_date
                    FROM
                        orders
                '''

                # WHERE文の生成
                condition = []
                if yet: condition.append(' status = 0 ')
                if order_price: condition.append(f' order_price = {order_price} ')
                if new_order: condition.append(' cash_margin like (1, 3) ')
                if reverse_order: condition.append(' cash_margin like (2, 4) ')

                if len(condition) != 0:
                    sql += ' WHERE ' + ' AND '.join(condition)

                cursor.execute(sql)
                rows = cursor.fetchall()

                # データが存在しない場合
                if len(rows) == 0:
                    return [{}]

                return rows
        except Exception as e:
            self.error_output('注文テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def select_errors_minite(self, minute = 1):
        '''
        エラーテーブル(errors)からx分以内に追加されたレコード数を取得する

        Args:
            minite(int): 何分以内か

        Returns:
            count(int): x分以内のエラー発生数

        '''
        try:
            one_minute_ago = datetime.now() - timedelta(minutes = minute)

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

    def select_listed(self, listed_flg = None):
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
                    sql += ' AND listed_flg = %s'
                    cursor.execute(sql, (listed_flg))
                else:
                    cursor.execute(sql)

                rows = cursor.fetchall()

                if rows:
                    return rows
                else:
                    return []

        except Exception as e:
            self.error_output('上場コードテーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def select_api_process(self, api_name = None, latest = False):
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
            self.error_output('APIプロセス管理テーブル取得処理でエラー', e, traceback.format_exc())
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
                order_qty(int): 注文株数[必須]
                buy_sell(str): 売買区分[必須]
                    1: 売、2: 買
                cash_margin(str): 信用区分[必須]
                    1: 現物買、2: 現物売、3: 信用新規、4:信用返済
                margin_type(str): 信用取引区分[必須]
                    0: 現物、1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ)
                fee(float): 取引手数料[必須]
                interest(float): 金利[任意]
                status(str): 注文ステータス[必須]
                    0: 未約定、1: 約定済、2: 取消中、3: 取消済
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
                        order_qty,
                        buy_sell,
                        cash_margin,
                        margin_type,
                        fee,
                        interest,
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
                    data['order_qty'],
                    data['buy_sell'],
                    data['cash_margin'],
                    data['margin_type'],
                    data['fee'],
                    data['interest'],
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
                stock_code(str):  証券コード[]
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

    def insert_listed(self, stock_code, listed_flg):
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
            self.error_output('上場情報テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def update_orders_status(self, order_id, status):
        '''
        注文テーブル(orders)のステータスを更新する

        Args:
            order_id(str): 注文ID
            status(str or int): 更新後のステータス
                0: 未約定、1: 約定済、2: 取消中、3: 取消済

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

    def update_listed(self, stock_code, listed_flg):
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
            self.error_output(f'上場情報テーブルのステータス更新処理でエラー', e, traceback.format_exc())
            return False

    def delete_listed(self, stock_code):
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
            self.error_output(f'上場コードテーブルの削除処理でエラー', e, traceback.format_exc())
            return False
