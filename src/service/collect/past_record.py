import csv
import os
import pandas as pd
import pytz
import py7zr
import re
import requests
import time
import traceback
from service_base import ServiceBase
from datetime import datetime, timedelta

class PastRecord(ServiceBase):
    '''過去の四本値取得に関するServiceクラス'''
    def __init__(self):
        super().__init__(api_headers = False, api_url = False, ws_url = False, conn = False)

    def main(self, target_stock_code_list, target_days, output_csv_dir):
        '''
        メイン処理

        Args:
            target_stock_code_list(list): 対象銘柄コード一覧
            target_days(int): 遡る日数
            output_csv_dir(str): CSV出力ディレクトリ

        '''
        # CSV保存ディレクトリ
        self.output_csv_dir = output_csv_dir

        # 1銘柄ずつ処理
        for stock_code in target_stock_code_list:
            time.sleep(5)

            self.log.info(f'銘柄コード: {stock_code} の四本値取得処理開始')
            result, ohlc = self.get_ohlc(stock_code, target_days)
            if result == False:
                # TODO エラーリストをCSVに出力
                continue
            self.log.info(f'銘柄コード: {stock_code} の四本値取得処理終了')

            # 記録済みの日付チェック
            recorded_date_list = self.check_recorded_csv(stock_code)

            # 取得データの成形
            result, formatted_ohlc, record_list = self.format_ohlc(ohlc, recorded_date_list)
            if result == False:
                # TODO エラーリストをCSVに出力
                continue

            self.log.info(f'銘柄コード: {stock_code} の四本値データのCSV出力開始')
            csv_path = os.path.join(self.output_csv_dir, f'ohlc_{datetime.now().strftime("%Y%m")}.csv')
            header = ['stock_code', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            result = self.write_csv(formatted_ohlc, header, csv_path)
            if result == False:
                # TODO エラーリストをCSVに出力
                continue
            self.log.info(f'銘柄コード: {stock_code} の四本値データのCSV出力終了')

            self.log.info(f'銘柄コード: {stock_code} の記録済み日付のCSV出力開始')
            check_csv_path = os.path.join(self.output_csv_dir, f'check_past_ohlc.csv')
            header = ['stock_code', 'date']
            result = self.write_csv(record_list, header, check_csv_path)
            if result == False:
                # TODO エラーリストをCSVに出力
                continue
            self.log.info(f'銘柄コード: {stock_code} の記録済み日付のCSV出力終了')

        return True

    def get_ohlc(self, stock_code, days):
        '''
        過去の四本値取得

        Args:
            stock_code(int or str): 銘柄コード
            days(int): 遡る日数

        Returns:
            result(bool): 実行結果
            ohlc(dict): 過去の四本値
        '''
        try:
            # User-Agentを指定しないと弾かれる
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }

            # 過去の四本値取得
            r = requests.get(f'https://query1.finance.yahoo.com/v7/finance/chart/{str(stock_code)}.T?range={days}d&interval=1m&indicators=quote&includeTimestamps=true', headers = headers)

            # レスポンスコードチェック
            if r.status_code != 200:
                self.log.error(f'米Yahoo!Financeからの四本値取得でエラー\n{r.status_code}\n{r._content}')
                return False, None

            # レスポンスデータを成形して返す
            ohlc = r.json()

            # 取得データのエラーチェック
            if ohlc['chart']['error'] != None:
                self.log.error(f'米Yahoo!Financeからの四本値取得でエラー\n{ohlc["chart"]["error"]}')
                return False, None

            return True, ohlc
        except Exception as e:
            self.log.error(f'米Yahoo!Financeからの四本値取得でエラー\n{e}\n{traceback.format_exc()}')
            return False, None

    def format_ohlc(self, ohlc, recorded_date_list):
        '''
        四本値データの成形

        Args:
            ohlc(dict): 過去の四本値
            recorded_date_list(list): 記録済の日付一覧

        Returns:
            result(bool): 実行結果
            formatted_ohlc(dict): 成形後の四本値
            record_date(list): 記録する日付一覧
        '''
        try:
            # データの中から四本値にあたる部分のみ修正
            ohlc_data = ohlc['chart']['result'][0]

            # 証券コード
            stock_code = ohlc_data['meta']['symbol'].split('.')[0]

            # 日付データ取得/成形
            timestamp = ohlc_data['timestamp']
            formatted_timestamp = [datetime.fromtimestamp(ts, pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M') for ts in timestamp]

            # 四本値データ取得
            ohlc_data = ohlc_data['indicators']['quote'][0]

            # 四本値データは丸め誤差があるため、小数点以下2桁を四捨五入する
            ohlc_data['open'] = [self.convert_to_int_if_possible(data) for data in ohlc_data['open']]
            ohlc_data['high'] = [self.convert_to_int_if_possible(data) for data in ohlc_data['high']]
            ohlc_data['low'] = [self.convert_to_int_if_possible(data) for data in ohlc_data['low']]
            ohlc_data['close'] = [self.convert_to_int_if_possible(data) for data in ohlc_data['close']]

            # データ数不整合チェック
            if not (len(formatted_timestamp) == len(ohlc_data['open']) == len(ohlc_data['high']) == len(ohlc_data['low']) == len(ohlc_data['close']) == len(ohlc_data['volume'])):
                self.log.error(f'四本値データの数が一致しません')
                self.log.error(f'len(timestamp, open, high, low, close, volume): ')
                self.log.error(f'{len(formatted_timestamp)}, {len(ohlc_data["open"])}, {len(ohlc_data["high"])}, {len(ohlc_data["low"])}, {len(ohlc_data["close"])}, {len(ohlc_data["volume"])}')
                return False, None, None

            # 四本値データを成形
            formatted_ohlc = []

            # 今回記録する日付
            record_date = [[stock_code, formatted_timestamp[0][:10]]]

            # 出来高がなかった場合にで埋めるための株価を保持しておく変数
            # 基本的には直近の終値
            # 寄り前で直近の終値がない場合は、寄った時の株価を設定
            last_close = ohlc_data['open'][0]

            # 別の日付のデータと区別するために現在の処理しているデータの日付を保持
            current_date = formatted_timestamp[0][:10]

            # 分ごとにデータを設定していく
            for index in range(len(formatted_timestamp)):
                # 昼休みのデータのチェック/除外する
                hour, minute = int(formatted_timestamp[index][11:13]), int(formatted_timestamp[index][14:16])
                if (hour == 11 and minute >= 30) or (hour == 12 and minute < 30):
                    continue

                # 記録済の日付チェック
                if formatted_timestamp[index][:10] in recorded_date_list:
                    continue

                # 当日のデータをザラ場中に処理すると中途半端な状態で記録されるため、除外
                now = datetime.now()
                if now.hour < 16:
                    if now.strftime('%Y-%m-%d') == formatted_timestamp[index][:10]:
                        continue

                # 特別気配の場合や大元のデータ欠損があるため補完を行う
                # 1本目のデータか日付が変わった場合のみ
                if (index == 0 and formatted_timestamp[index][11:16] != '09:00') or (formatted_timestamp[index][:10] != current_date):
                    # 日付変更の場合のみ管理用のデータ追加/変更
                    if formatted_timestamp[index][:10] != current_date:
                        # 記録済みの日付を追加
                        record_date.append([stock_code, formatted_timestamp[index][:10]])

                        # 処理中の日付を更新
                        current_date = formatted_timestamp[index][:10]

                    # 同日のOHLCデータのみ切り出し
                    diff_index = len(formatted_timestamp) - 1
                    for i in range(index, len(formatted_timestamp)):
                        if formatted_timestamp[i][:10] != formatted_timestamp[index][:10] :
                            diff_index = i
                            break
                    sliced_ohlc_data = {key: ohlc_data[key][index:diff_index] for key in ohlc_data.keys()}
                    sliced_ohlc_data['timestamp'] = formatted_timestamp[index:diff_index]

                    # 始値データの設定、同日データの中で欠損しているレコードの補完を行う
                    last_close, add_data = self.correcting_loss_ohlc(stock_code, sliced_ohlc_data)

                    # 終値があればそっちを穴埋めの値に設定
                    if ohlc_data['close'][index] is not None and formatted_timestamp[index][11:16] == '09:00':
                        last_close = ohlc_data['close'][index]

                    # 補完データを追加
                    formatted_ohlc.extend(add_data)

                # ザラ場中に実行すると中途半端なデータが入るのでそれも除外
                # MEMO: 秒を切り捨てたのでチェック処理が行えない
                #second = int(formatted_timestamp[index][17:19])
                #if second != 0:
                #    continue

                # データの追加
                # Noneの場合は補完値で穴埋め
                formatted_ohlc.append([stock_code,
                                        formatted_timestamp[index],
                                        ohlc_data['open'][index] if ohlc_data['open'][index] is not None else last_close,
                                        ohlc_data['high'][index] if ohlc_data['high'][index] is not None else last_close,
                                        ohlc_data['low'][index] if ohlc_data['low'][index] is not None else last_close,
                                        ohlc_data['close'][index] if ohlc_data['close'][index] is not None else last_close,
                                        ohlc_data['volume'][index] if ohlc_data['volume'][index] is not None else 0
                ])
                if ohlc_data['close'][index] is not None:
                    last_close = ohlc_data['close'][index]

            return True, formatted_ohlc, record_date
        except Exception as e:
            self.log.error(f'取得データの成形でエラー\n{e}\n{traceback.format_exc()}')
            return False, None, None

    def correcting_loss_ohlc(self, stock_code, today_ohlc):
        '''
        欠損している四本値データを埋める

        Args:
            stock_code(int or str): 銘柄コード
            today_ohlc(dict): 当日の四本値データ

        Returns:
            start_price(float): 当日の始値
            add_data(list): 補完が必要なデータ
        '''
        # 当日の始値を取得
        start_price = -1
        for i in range(len(today_ohlc['open'])):
            if today_ohlc['open'][i] is not None:
                start_price = today_ohlc['open'][i]
                break

        # 欠損レコードの補完
        # 9:00から数分間レコードが欠損している場合があるため、その場合は欠損しているレコードを埋める
        add_data = []
        # 1本目が9:00のデータでない場合
        if today_ohlc['timestamp'][0][11:16] != '09:00':
            # 時間計算できるようにdatetime型に変換
            # 当日の9:00のデータを作成
            current_time = datetime.strptime(f'{today_ohlc["timestamp"][0][:10]} 09:00', '%Y-%m-%d %H:%M')

            # バグ対策
            count = 0

            # 1本目の時刻までのレコードを補完
            while current_time.strftime('%H:%M') != today_ohlc['timestamp'][0][11:16]:
                add_data.append([stock_code,
                                current_time.strftime('%Y-%m-%d %H:%M'),
                                start_price,
                                start_price,
                                start_price,
                                start_price,
                                0
                ])
                current_time += timedelta(minutes = 1)

                # 元データの時刻部分の表記が狂っていた場合無限ループに陥るので、念のため対策
                count += 1
                if count > 1000:
                    break

        return start_price, add_data

    def check_recorded_csv(self, stock_code):
        '''
        記録済みCSVのチェック

        Args:
            stock_code(int or str): 銘柄コード

        Returns:
            date_list(list): 記録済みの日付一覧
        '''
        check_csv_path = os.path.join(self.output_csv_dir, f'check_past_ohlc.csv')
        # CSV存在チェック
        if not os.path.exists(check_csv_path):
            return []

        # CSVの読み込み
        check_csv = pd.read_csv(check_csv_path)

        # 銘柄コードが一致する行の日付を取得
        filtered_data = check_csv[check_csv['stock_code'] == stock_code]
        date_list = filtered_data['date'].tolist()

        return date_list

    def convert_to_int_if_possible(self, value):
        '''
        丸め誤差のある株価を正しい値に戻す

        Args:
            value(float): 変換する値

        Returns:
            value(float or int): 変換後の値
        '''
        # 値の存在チェック
        if value is not None:
            # 小数点以下2桁を四捨五入
            rounded_value = round(value, 2)
            # 整数変換可能なら変換
            if rounded_value.is_integer():
                return int(rounded_value)
            return rounded_value
        return None

    def write_csv(self, formatted_ohlc, header, file_path):
        '''
        CSVに出力

        Args:
            formatted_ohlc(list): 成形後の四本値
            header(list): ヘッダー
            file_path(str): 出力先のファイルパス

        Returns:
            result(bool): 実行結果
        '''
        try:
            with open(file_path, 'a', newline = '', encoding = 'utf-8') as f:
                writer = csv.writer(f)

                # ファイルが空の場合、ヘッダーを書き込む
                if f.tell() == 0:
                    writer.writerow(header)

                # ボディを書き込む
                for row in formatted_ohlc:
                    writer.writerow(row)

        except Exception as e:
            self.log.error(f'CSVファイル書き込みでエラー\nファイルパス: {file_path}\n{e}\n{traceback.format_exc()}')
            return False

        return True

    def delete_old_data(self):
        '''30日以上前の記録済みデータはいらないので削除する'''

        # CSVの存在チェック/読み込み
        csv_path = os.path.join(self.output_csv_dir, f'check_past_ohlc.csv')
        if not os.path.exists(csv_path):
            return True
        check_csv = pd.read_csv(csv_path)

        # 30日以上前のデータを削除
        check_csv['date'] = pd.to_datetime(check_csv['date'])
        check_csv = check_csv[check_csv['date'] >= datetime.now() - timedelta(days = 30)]

        # 削除後のデータを上書き
        check_csv.to_csv(csv_path, index = False)

        return True

    def compress_old_data(self,a):
        '''古い四本値データを圧縮する'''

        self.output_csv_dir = a

        # CSV保存ディレクトリからCSVファイル一覧の名前の取得
        csv_files = os.listdir(self.output_csv_dir)

        # 今月の記録用ファイル名
        current_month = f'ohlc_{datetime.now().strftime("%Y%m")}.csv'

        # 1ファイルずつチェックする
        for csv_file in csv_files:
            # OHLCデータのCSVファイル以外はスキップ
            if not re.match(r'ohlc_\d{6}.csv', csv_file):
                continue

            # 今月のファイルはスキップ
            if csv_file == current_month:
                continue

            # CSVファイルを7z形式で圧縮
            csv_path = os.path.join(self.output_csv_dir, csv_file)
            compressed_path = csv_path.replace('.csv', '.7z')
            try:
                with py7zr.SevenZipFile(compressed_path, 'w') as archive:
                    archive.write(csv_path, arcname=csv_file)

                # 圧縮に成功したら元のファイルを削除
                if os.path.exists(compressed_path):
                    os.remove(csv_path)
                else:
                    self.log.error(f'CSVファイルの圧縮が見つかりません\nファイルパス: {csv_path}')
            except Exception as e:
                self.log.error(f'CSVファイルの圧縮に失敗\nファイルパス: {csv_path}\n{e}')

        return True