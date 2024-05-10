import traceback

class Orders():
    '''ordersテーブルを操作する'''

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

    def select(self, yet = False, order_price = None,
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
            self.log.error('注文テーブル取得処理でエラー', e, traceback.format_exc())
            return False

    def insert(self, data):
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
            self.log.error('注文テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def update_status(self, order_id, status):
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
            self.log.error(f'注文テーブルのステータス更新処理でエラー', e, traceback.format_exc())
            return False
