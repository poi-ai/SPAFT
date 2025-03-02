import traceback
from datetime import datetime, timedelta

class Ohlc():
    '''ohlcテーブルを操作する'''

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

    def select(self):
        '''
        四本値テーブル(ohlc)からレコードを取得する

        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        *
                    FROM
                        ohlc
                '''

                cursor.execute(sql)
                row = cursor.fetchall()

                if not row:
                    return False
                return row
        except Exception as e:
            self.log.error('四本値レコード一括取得処理でエラー', e, traceback.format_exc())
            return False

    def select_time(self, symbol, target_time):
        '''
        四本値テーブル(ohlc)から指定時間のレコードを取得する

        Args:
            symbol(str): 銘柄コード
            target_time(datetime): 取得対象時間

        Returns:
            row(dict): 指定時間のレコード ※レコードが存在しない場合は{}
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        *
                    FROM
                        ohlc
                    WHERE
                        symbol = %s
                    AND
                        trade_time = %s
                '''

                cursor.execute(sql, (symbol, target_time))
                row = cursor.fetchone()

                if not row:
                    return {}
                return row
        except Exception as e:
            self.log.error('四本値レコード取得処理でエラー', e, traceback.format_exc())
            return False

    def select_total_volume(self, symbol, target_time):
        '''
        四本値テーブル(ohlc)から指定銘柄の指定時間のレコードの累計出来高取得する

        Args:
            symbol(str): 銘柄コード
            target_time(datetime.datetime): 取得対象時間

        Returns:
            row['total_volume'](int): 指定時間の累計出来高 ※レコードが存在しない場合はFalse
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        total_volume
                    FROM
                        ohlc
                    WHERE
                        symbol = %s
                    AND
                        trade_time = %s
                '''

                cursor.execute(sql, (symbol, target_time))
                row = cursor.fetchone()

                if not row:
                    return False
                return row['total_volume']
        except Exception as e:
            self.log.error('四本値レコードの指定時刻累計出来高取得処理でエラー', e, traceback.format_exc())
            return False

    def select_latest_total_volume(self, symbol, target_date):
        '''
        四本値テーブル(ohlc)から指定銘柄の指定日の最新レコードの累計出来高取得する

        Args:
            symbol(str): 銘柄コード
            target_date(datetime.date): 取得対象日

        Returns:
            row['total_volume'](int): 指定時間の累計出来高 ※レコードが存在しない場合は-999
        '''
        try:
            with self.conn.cursor(self.dict_return) as cursor:
                sql = '''
                    SELECT
                        total_volume
                    FROM
                        ohlc
                    WHERE
                        symbol = %s
                    AND
                        DATE(trade_time) = DATE(%s)
                    ORDER BY
                        trade_time DESC
                    LIMIT 1
                '''

                cursor.execute(sql, (symbol, target_date))
                row = cursor.fetchone()

                if not row:
                    return -999
                return row['total_volume']
        except Exception as e:
            self.log.error('四本値レコードの最新分累計出来高取得処理でエラー', e, traceback.format_exc())
            return False

    def insert(self, ohlc_data):
        '''
        四本値テーブル(ohlc)にレコードを追加する

        Args:
            ohlc_data(dict): 追加データ
                symbol(str): 銘柄コード
                trade_time(datetime): 取引時間
                open_price(float): 始値
                high_price(float): 高値
                low_price(float): 安値
                close_price(float): 終値
                volume(int): 出来高
                total_volume(int): 累積出来高
                status(int): ステータス

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO ohlc
                    (
                        symbol,
                        trade_time,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                        total_volume,
                        status

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
                        %s
                    )
                '''

                cursor.execute(sql, (
                    ohlc_data['symbol'],
                    ohlc_data['trade_time'],
                    ohlc_data['open_price'],
                    ohlc_data['high_price'],
                    ohlc_data['low_price'],
                    ohlc_data['close_price'],
                    ohlc_data['volume'],
                    ohlc_data['total_volume'],
                    ohlc_data['status']
                ))

            return True
        except Exception as e:
            self.log.error('四本値テーブルへのレコード追加処理でエラー', e, traceback.format_exc())
            return False

    def update(self, ohlc_data):
        '''
        四本値テーブル(ohlc)のレコードを更新する

        Args:
            ohlc_data(dict): 更新データ
                symbol(str): 銘柄コード
                trade_time(datetime): 取引時間
                open_price(float): 始値
                high_price(float): 高値
                low_price(float): 安値
                close_price(float): 終値
                volume(int): 出来高
                total_volume(int): 累積出来高
                status(int): ステータス

        Returns:
            result(bool): SQL実行結果
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE ohlc
                    SET
                        open_price = %s,
                        high_price = %s,
                        low_price = %s,
                        close_price = %s,
                        volume = %s,
                        total_volume = %s,
                        status = %s
                    WHERE
                        symbol = %s
                    AND
                        trade_time = %s
                '''

                cursor.execute(sql, (
                    ohlc_data['open_price'],
                    ohlc_data['high_price'],
                    ohlc_data['low_price'],
                    ohlc_data['close_price'],
                    ohlc_data['volume'],
                    ohlc_data['total_volume'],
                    ohlc_data['status'],
                    ohlc_data['symbol'],
                    ohlc_data['trade_time']
                ))

            return True
        except Exception as e:
            self.log.error('四本値テーブルのレコード更新処理でエラー', e, traceback.format_exc())
            return False

    def upsert(self, ohlc_data):
        '''
        四本値テーブル(ohlc)のレコードを追加または更新する

        Args:
            ohlc_data(dict): 追加または更新データ
                symbol(str): 銘柄コード
                trade_time(datetime): 取引時間
                open_price(float): 始値
                high_price(float): 高値
                low_price(float): 安値
                close_price(float): 終値
                volume(int): 出来高
                total_volume(int): 累積出来高
                status(int): ステータス

        Returns:
            result(bool): SQL実行結果
            row_count(int): 実行されたSQLの種別 ※追加の場合は1、更新の場合は2
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO ohlc
                    (
                        symbol,
                        trade_time,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                        total_volume,
                        status
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
                        %s
                    ) as new
                    ON DUPLICATE KEY UPDATE
                        high_price = new.high_price,
                        low_price = new.low_price,
                        close_price = new.close_price,
                        volume = new.volume,
                        total_volume = new.total_volume,
                        status = new.status
                '''

                cursor.execute(sql, (
                    ohlc_data['symbol'],
                    ohlc_data['trade_time'],
                    ohlc_data['open_price'],
                    ohlc_data['high_price'],
                    ohlc_data['low_price'],
                    ohlc_data['close_price'],
                    ohlc_data['volume'],
                    ohlc_data['total_volume'],
                    ohlc_data['status']
                ))

            return True, cursor.rowcount
        except Exception as e:
            self.log.error('四本値テーブルのレコード追加または更新処理でエラー', e, traceback.format_exc())
            return False, 0