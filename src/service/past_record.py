import csv
import os
import pandas as pd
import pytz
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
            # 過去の四本値取得
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
            # 四本値データをCSVに出力
            csv_path = os.path.join(self.output_csv_dir, f'ohlc_{datetime.now().strftime("%Y%m")}.csv')
            header = ['stock_code', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            result = self.write_csv(formatted_ohlc, header, csv_path)
            if result == False:
                # TODO エラーリストをCSVに出力
                continue
            self.log.info(f'銘柄コード: {stock_code} の四本値データのCSV出力終了')

            self.log.info(f'銘柄コード: {stock_code} の記録済み日付のCSV出力開始')
            # 記録済みの日付をCSVに出力
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
            formatted_timestamp = [datetime.fromtimestamp(ts, pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S') for ts in timestamp]

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

                # 1本目のデータは寄った時分のデータなので埋めずに9:00の出来高0のデータを追加する
                if index == 0 and formatted_timestamp[index][11:16] != '09:00':
                    formatted_ohlc.append([stock_code,
                                            formatted_timestamp[index][:10] + ' 09:00:00',
                                            ohlc_data['open'][index],
                                            ohlc_data['high'][index],
                                            ohlc_data['low'][index],
                                            ohlc_data['close'][index],
                                            0]
                    )
                    continue

                # 日付変更チェック
                if formatted_timestamp[index][:10] != current_date:
                    record_date.append([stock_code, formatted_timestamp[index][:10]])
                    current_date = formatted_timestamp[index][:10]
                    # 始値の設定しなおし
                    last_close = ohlc_data['open'][0]
                    # 寄りのデータが9:00の出来高0かチェックのデータを追加する
                    if formatted_timestamp[index][11:16] != '09:00':
                        formatted_ohlc.append([stock_code,
                                                formatted_timestamp[index][:10] + ' 09:00:00',
                                                ohlc_data['open'][index],
                                                ohlc_data['high'][index],
                                                ohlc_data['low'][index],
                                                ohlc_data['close'][index],
                                                0]
                        )
                        continue

                # ザラ場中に実行すると中途半端なデータが入るのでそれも除外
                second = int(formatted_timestamp[index][17:19])
                if second != 0:
                    continue

                # 出来高チェック
                if ohlc_data['volume'][index] is not None:
                    formatted_ohlc.append([stock_code,
                                            formatted_timestamp[index],
                                            ohlc_data['open'][index],
                                            ohlc_data['high'][index],
                                            ohlc_data['low'][index],
                                            ohlc_data['close'][index],
                                            ohlc_data['volume'][index]]
                    )
                    last_close = ohlc_data['close'][index]
                else:
                    # 出来高がない(=None)の場合、前のデータの終値を設定
                    # 前のデータがない場合は、後のデータの始値を設定
                    formatted_ohlc.append([stock_code,
                                            formatted_timestamp[index],
                                            last_close,
                                            last_close,
                                            last_close,
                                            last_close,
                                            0]
                    )

            return True, formatted_ohlc, record_date
        except Exception as e:
            self.log.error(f'取得データの成形でエラー\n{e}\n{traceback.format_exc()}')
            return False, None, None

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