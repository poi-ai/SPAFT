import json
import time
import requests
import ntplib
from datetime import datetime, timedelta

class CulcTime():
    '''営業日や取引時間など時間に関して計算するクラス'''

    def __init__(self, log):
        self.log = log
        self.ntp_server = 1

    def exchange_date(self):
        '''
        現在の日付が取引所の営業日かの判定をする

        Returns:
            bool: 取引所営業日/非営業日の判定結果
                True: 取引所営業日、False: 取引所非営業日
        '''
        # NTPサーバーから現在の時刻を取得
        now = self.get_now(accurate = False)

        # 営業日判定
        if self.is_exchange_workday(now):
            return True

        return False

    def exchange_time(self, now = None):
        '''
        現在の時間か指定した時間から取引時間の種別を判定する

        Args:
            now(datetime): 判定対象の時間 省略可

        Returns:
            time_type(int): 時間種別
                1: 前場取引時間、2: 後場取引時間(クロージング・オークション除く)、
                3: 取引時間外(寄り付き前)、4: 取引時間外(お昼休み)、5: 取引時間外(大引け後)、6: クロージング・オークション
        '''
        # 時間が指定されていない場合はNTPサーバーから現在の時刻を取得
        if now == None:
            now = self.get_now()

        # 前場
        if 9 <= now.hour < 11 or (now.hour == 11 and now.minute < 30):
            return 1
        # クロージング・オークション
        elif 15 == now.hour and (25 <= now.minute < 30):
            return 6
        # 後場
        elif 12 < now.hour < 15 or (now.hour == 12 and now.minute >= 30) or (now.hour == 15 and now.minute < 25):
            return 2
        # 寄り前
        elif now.hour < 9:
            return 3
        # 引け後
        elif now.hour >= 15:
            return 5
        # お昼休み
        else:
            return 4

    def is_exchange_workday(self, date):
        '''
        指定した日が取引所の営業日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 営業日、False: 非営業日
        '''

        # 土日祝日かの判定を行う
        result = self.is_workday(date)

        # 土日・祝日の場合
        if result == False:
            return False

        # 取引所の営業日の判定を行う
        if self.is_exchange_holiday(date):
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

    def is_workday(self, date):
        '''
        指定した日が営業日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 営業日、False: 非営業日

        '''

        # 土日判定
        if date.weekday() in [5, 6]:
            return False

        # 祝日判定
        if self.is_holiday(date):
            return False

        return True

    def is_holiday(self, date):
        '''
        指定した日が祝日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 祝日、False: 非祝日

        '''
        # 祝日のリストの取得
        until_year, holiday_list = self.get_holiday_list()

        # 指定した年が対応しているか
        if int(date.strftime('%Y')) <= until_year:
            # 対応している場合 祝日リストに入っているか
            return date.strftime('%Y%m%d') in holiday_list
        else:
            # 対応していない場合
            holiday_list = self.holidays_jp_api()
            # TODO リストからチェックする処理 2030年までに対応

    def get_holiday_list(self):
        '''祝日を列挙したリスト

        Returns:
            until_year(int): 記載のある最後の年
            holiday_list(list): 祝日のリスト
        '''
        return 2030, {
            '20240101','元日',
            '20240108','成人の日',
            '20240211','建国記念の日',
            '20240212','振替休日',
            '20240223','天皇誕生日',
            '20240320','春分の日',
            '20240429','昭和の日',
            '20240503','憲法記念日',
            '20240504','みどりの日',
            '20240505','こどもの日',
            '20240506','振替休日',
            '20240715','海の日',
            '20240811','山の日',
            '20240812','振替休日',
            '20240916','敬老の日',
            '20240922','秋分の日',
            '20240923','振替休日',
            '20241014','スポーツの日',
            '20241103','文化の日',
            '20241104','振替休日',
            '20241123','勤労感謝の日',
            '20250101','元日',
            '20250113','成人の日',
            '20250211','建国記念の日',
            '20250223','天皇誕生日',
            '20250224','振替休日',
            '20250320','春分の日',
            '20250429','昭和の日',
            '20250503','憲法記念日',
            '20250504','みどりの日',
            '20250505','こどもの日',
            '20250506','振替休日',
            '20250721','海の日',
            '20250811','山の日',
            '20250915','敬老の日',
            '20250923','秋分の日',
            '20251013','スポーツの日',
            '20251103','文化の日',
            '20251123','勤労感謝の日',
            '20251124','振替休日',
            '20260101','元日',
            '20260112','成人の日',
            '20260211','建国記念の日',
            '20260223','天皇誕生日',
            '20260320','春分の日',
            '20260429','昭和の日',
            '20260503','憲法記念日',
            '20260504','みどりの日',
            '20260505','こどもの日',
            '20260506','振替休日',
            '20260720','海の日',
            '20260811','山の日',
            '20260921','敬老の日',
            '20260922','国民の休日',
            '20260923','秋分の日',
            '20261012','スポーツの日',
            '20261103','文化の日',
            '20261123','勤労感謝の日',
            '20270101','元日',
            '20270111','成人の日',
            '20270211','建国記念の日',
            '20270223','天皇誕生日',
            '20270321','春分の日',
            '20270322','振替休日',
            '20270429','昭和の日',
            '20270503','憲法記念日',
            '20270504','みどりの日',
            '20270505','こどもの日',
            '20270719','海の日',
            '20270811','山の日',
            '20270920','敬老の日',
            '20270923','秋分の日',
            '20271011','スポーツの日',
            '20271103','文化の日',
            '20271123','勤労感謝の日',
            '20280101','元日',
            '20280110','成人の日',
            '20280211','建国記念の日',
            '20280223','天皇誕生日',
            '20280320','春分の日',
            '20280429','昭和の日',
            '20280503','憲法記念日',
            '20280504','みどりの日',
            '20280505','こどもの日',
            '20280717','海の日',
            '20280811','山の日',
            '20280918','敬老の日',
            '20280922','秋分の日',
            '20281009','スポーツの日',
            '20281103','文化の日',
            '20281123','勤労感謝の日',
            '20290101','元日',
            '20290108','成人の日',
            '20290211','建国記念の日',
            '20290212','振替休日',
            '20290223','天皇誕生日',
            '20290320','春分の日',
            '20290429','昭和の日',
            '20290430','振替休日',
            '20290503','憲法記念日',
            '20290504','みどりの日',
            '20290505','こどもの日',
            '20290716','海の日',
            '20290811','山の日',
            '20290917','敬老の日',
            '20290923','秋分の日',
            '20290924','振替休日',
            '20291008','スポーツの日',
            '20291103','文化の日',
            '20291123','勤労感謝の日',
            '20300101','元日',
            '20300114','成人の日',
            '20300211','建国記念の日',
            '20300223','天皇誕生日',
            '20300320','春分の日',
            '20300429','昭和の日',
            '20300503','憲法記念日',
            '20300504','みどりの日',
            '20300505','こどもの日',
            '20300506','振替休日',
            '20300715','海の日',
            '20300811','山の日',
            '20300812','振替休日',
            '20300916','敬老の日',
            '20300923','秋分の日',
            '20301014','スポーツの日',
            '20301103','文化の日',
            '20301104','振替休日',
            '20301123','勤労感謝の日'
        }

    def holidays_jp_api(self):
        '''
        Holidays JP APIから祝日情報を取得する

        Returns:
            holidays(dict): 実行日の前年～翌年までの祝日一覧

        '''
        try:
            r = requests.get('https://holidays-jp.github.io/api/v1/date.json')
        except Exception as e:
            return False, e

        if r.status_code != 200:
            self.log.error(f'祝日情報取得APIエラー ステータスコード: {r.status_code}')
            return False, f'{r.status_code}\n{r.status_code}\n{json.loads(r.content)}'

        holidays = r.json()

        if len(holidays) == 0:
            self.log.error(f'祝日情報取得APIエラー レスポンス情報が空')
            return False

        return holidays

    def is_exchange_holiday(self, date):
        '''取引所が年末年始の休場日か'''

        # 1/1~1/3
        if date.month == 1 and date.day <= 3:
            return True

        # 12/31
        if date.month == 12 and date.day == 31:
            return True

        return False

    def get_now(self, accurate = True):
        '''
        現在の時刻を取得する

        Args:
            accurate(bool): 正確な時刻が欲しいか デフォルト: True
                True: NTPサーバーから取得、False: datetimeから取得

        Returns:
            now(datetime): 現在時刻
        '''

        # 正確な時刻が欲しい場合のみ
        if accurate:
            result, now = self.ntp(server_id = self.ntp_server)
            self.server_id_management()
            if result == True:
                return now
            self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました\n{now}')

            result, now = self.ntp(server_id = self.ntp_server)
            self.server_id_management()
            if result == True:
                return now
            self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました\n{now}')

            result, now = self.ntp(server_id = self.ntp_server)
            self.server_id_management()
            if result == True:
                return now
            self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました\n{now}')

        # どのNTPサーバーからも取れなかった場合か正確な時刻が要求されていない場合はdatetimeから取得
        return datetime.now()

    def server_id_management(self):
        '''インスタンス変数のサーバーIDの管理を行う'''
        if self.ntp_server == 1:
            self.ntp_server = 2
        elif self.ntp_server == 2:
            self.ntp_server = 3
        elif self.ntp_server == 3:
            self.ntp_server = 1
        return

    def wait_time(self, hour, minute, second = None, microsecond = None):
        '''
        指定した時間まで待機する(日付は跨がない)

        Args:
            hour(int): この時間(時)まで待機する[必須]
            minute(int): この時間(分)まで待機する[必須]
            second(int): この時間(秒)まで待機する[任意]
            microsecond(int): この時間(マイクロ秒)まで待機する[任意]
        '''
        # 現在の時刻を取得する
        now = self.get_now()

        # この時間まで待つ
        if second is not None and microsecond is not None:
            schedule_time = now.replace(hour = hour, minute = minute, second = second, microsecond = microsecond)
        elif second is not None:
            schedule_time = now.replace(hour = hour, minute = minute, second = second)
        else:
            schedule_time = now.replace(hour = hour, minute = minute)

        # もう対象の時間を過ぎていたら何もせず返す
        if now >= schedule_time:
            self.log.info(f'{hour}時{minute}分を過ぎているため待機しません')
            return True

        # 待機する時間(秒)を計る
        wait_seconds = (schedule_time - now).total_seconds()

        self.log.info(f'{hour}時{minute}分まで{wait_seconds}秒待機します')
        time.sleep(wait_seconds)
        self.log.info('待機終了')
        return True

    def wait_time_next_second(self, accurate = True):
        '''
        次の秒まで待機する

        Args:
            accurate(bool): 正確な時刻が欲しいか

        '''
        # 現在の時刻を取得する
        now = self.get_now(accurate)

        # 次の秒の00(≒1秒後)
        next_minute = (now + timedelta(seconds = 1)).replace(microsecond = 0)

        # 待機する時間(マイクロ秒単位)を計る
        wait_seconds = (next_minute - now).total_seconds()

        self.log.info(f'{wait_seconds}秒待機します')
        time.sleep(wait_seconds)
        self.log.info('待機終了')
        return True

    def wait_time_next_minute(self, accurate = True):
        '''
        次の分まで待機する

        Args:
            accurate(bool): 正確な時刻が欲しいか

        '''
        # 現在の時刻を取得する
        now = self.get_now(accurate)

        # 次の分の00秒(≒1分後)
        next_minute = (now + timedelta(minutes = 1)).replace(second = 0, microsecond = 0)

        # 待機する時間(マイクロ秒単位)を計る
        wait_seconds = (next_minute - now).total_seconds()

        self.log.info(f'{wait_seconds}秒待機します')
        time.sleep(wait_seconds)
        self.log.info('待機終了')
        return True

    def get_trade_end_time_seconds(self, accurate = False):
        '''
        引け(クロージング・オークション)の時間までの秒数を取得する

        Args:
            accurate(bool): 正確な時刻が欲しいか
                True: NTPサーバーから取得、False: datetimeから取得

        Returns:
            time_out(float): 引け(クロージング・オークション)の時間までの秒数
        '''
        # 現時刻を取得
        now = self.get_now(accurate)
        # 前場・前場前の場合
        if now.hour < 11 or (now.hour == 11 and now.minute < 30):
            # 昼休みになったらタイムアウトするように
            time_out = (now.replace(hour = 11, minute = 30, second = 0) - now).total_seconds()
        # 昼休み・後場(クロージング・オークション除く)の場合
        elif now.hour < 15 or (now.hour == 15 and now.minute < 25):
            # クロージング・オークション時間に突入したらタイムアウトするように
            time_out = (now.replace(hour = 15, minute = 25, second = 0) - now).total_seconds()
        # クロージング・オークションの場合
        elif now.hour == 15 and (25 <= now.minute < 30):
            # 大引けになったらタイムアウトするように
            time_out = (now.replace(hour = 15, minute = 30, second = 0) - now).total_seconds()
        # その他(デバッグモードなど)の場合
        else:
            # 処理の都合上なんかしらの数値を設定する必要がある場合のために99999をセット
            time_out = 99999

        return time_out

    def ntp(self, server_id = 1):
        '''NTPサーバーから現在の時刻を取得する'''
        if server_id == 1:
            server = 'ntp.jst.mfeed.ad.jp' # stratum2
        elif server_id == 2:
            server = 'time.cloudflare.com' # stratum3
        elif server_id == 3:
            server = 'time.aws.com' # stratum4
        else:
            return False, 'サーバーID不正'

        # リクエスト送信
        try:
            c = ntplib.NTPClient()
            server = 'ntp.jst.mfeed.ad.jp' # stratum2
            response = c.request(server, version = 3)
        except Exception as e:
            return False, e

        # Leap Indicatorチェック
        if response.leap < 2:
            return True, datetime.fromtimestamp(response.tx_time)
        else:
            return False, f'LI: {response.leap}'
