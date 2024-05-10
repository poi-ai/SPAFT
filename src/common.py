import ntplib
from datetime import datetime, timedelta
from holiday import Holiday


class Common():
    '''共通処理を記載したクラス'''
    def __init__(self, log):
        self.log = log

        # 営業日関連の共通処理
        self.holiday = Holiday(self.log)

    def exchange_time(self):
        '''
        現在の時間から取引時間の種別を判定する

        Returns:
            time_type(int): 時間種別
                -1: 非営業日、1: 前場取引時間、2: 後場取引時間、
                3: 取引時間外(寄り付き前)、4: 取引時間外(お昼休み)、5: 取引時間外(大引後)
        '''
        # NTPサーバーから現在の時刻を取得
        now = self.ntp()

        # 土日祝日判定
        if not self.is_exchange_workday(now):
            return -1

        # 時間判定
        if 9 <= now.hour < 11 or (now.hour == 11 and now.minute < 30):
            return 1
        elif 12 < now.hour < 15 or (now.hour == 12 and now.minute >= 30):
            return 2
        elif now.hour < 9:
            return 3
        elif now.hour >= 15:
            return 5
        else:
            return 4

    def is_exchange_workday(self, date):
        '''
        指定した日が取引所の営業日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
        '''

        # 土日祝日かの判定を行う
        result = self.holiday.is_workday(date)

        # 土日・祝日の場合
        if result == False:
            return False

        # 取引所の営業日の判定を行う
        if self.holiday.is_exchange_holiday(date):
            return False

        return True

    def next_exchange_workday(self, date):
        '''
        指定した日の翌取引所営業日を返す

        Args:
            date(datetime): 指定日

        Returns:
            next_date(datetime): 指定日の翌取引所営業日
        '''
        while True:
            next_date = date + timedelta(days = 1)

            # 取引所営業日判定
            result = self.is_exchange_workday(next_date)

            # 取引営業日ならその日付を返す
            if result:
                return next_date

            date = next_date

    def ntp(self):
        '''NTPサーバーから現在の時刻を取得する'''
        try:
            c = ntplib.NTPClient()
            server = 'ntp.jst.mfeed.ad.jp' # stratum2
            response = c.request(server, version = 3)
            return datetime.fromtimestamp(response.tx_time)
        except Exception as e:
            self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました サーバー: {server}\n{e}')
            self.log.error(f'別のNTPサーバーから時刻取得を行います')

            try:
                c = ntplib.NTPClient()
                server = 'time.cloudflare.com' # stratum3
                response = c.request(server, version = 3)
                return datetime.fromtimestamp(response.tx_time)
            except Exception as e:
                self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました サーバー: {server}\n{e}')
                # サブのNTPサーバーもダメな場合はdatetimeライブラリから取得する
                return datetime.now()


from base import Log
c = Common(Log())
print(c.next_exchange_workday())