import asyncio
import datetime
import json
import os
import time
import websockets
import pytz
from service_base import ServiceBase
from datetime import datetime, timedelta

class Record(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, ws_url, conn):
        super().__init__(api_headers, api_url, ws_url, conn)

        # 今日の年月をyyyymm形式で取得
        self.today = self.util.culc_time.get_now(accurate = False).strftime('%Y%m%d')

        # 記録対象の銘柄リスト
        self.target_code_list = []

        # 四本値データの一時記録用メモリ
        self.ohlc_list = []

        # タイムゾーン設定用
        self.jst = pytz.timezone('Asia/Tokyo')

    def record_init(self, target_code_list, debug = False, push_mode = False):
        '''
        データ取得系処理を行うときの初期処理

        Args:
            target_code_list(list): 取得対象の銘柄リスト
            debug(bool): デバッグモードか
            push_mode(bool): PUSH配信を受けるモードか

        Return:
            bool: 判定結果(T: 営業日、F: 非営業日)
            target_code_list(list): 取得不可能な銘柄を除いた取得対象の銘柄リスト

        '''
        if debug == True:
            self.log.info('デバッグモードのため営業日判定処理をスキップします')
        else:
            self.log.info('営業日判定処理開始')
            result = self.util.culc_time.exchange_date()
            if result == False:
                self.log.warning('非営業日のため取得処理を行いません')
                return False, None
            self.log.info('営業日判定処理終了')

        # 51銘柄以上取得処理を行うとエラーが出るのを回避するために、取得系のロジックでは最初に全銘柄登録解除しておく
        # 参考: https://github.com/kabucom/kabusapi/issues/135
        # 失敗してもあまり影響なく(そもそも51銘柄以上登録されていることがなく)、後の処理でリカバリーできるため
        # ここでの実行結果で処理は分けない
        self.log.info('登録済銘柄解約処理開始')
        self.unregister_all()
        self.log.info('登録済銘柄解約処理終了')

        self.target_code_list = target_code_list

        # PUSH配信を受けるモードの場合は銘柄登録処理を行う
        if push_mode == True:
            for target_code in target_code_list:
                time.sleep(0.3)
                self.log.info(f'銘柄登録処理開始 証券コード: {target_code}')
                result = self.api.register.register(target_code)
                if result != True: ## TODO ここで失敗したコードをインスタンス変数から除く
                    self.log.error(f'銘柄登録処理でエラー\n{result}')
                    continue
                self.log.info(f'銘柄登録処理終了 証券コード: {target_code}')
        # 板情報のAPIを叩きに行くモードの場合 初回データ取得は時間がかかるので先に板情報の空取得を行う
        else:
            self.log.info('初回板情報空取得処理開始')
            for stock_code in target_code_list[:]:
                result, error_code = self.info_board(stock_code, market_code = 1, add_info = False)
                if result == False and error_code == 402001:
                    target_code_list.remove(stock_code)
            self.log.info('初回板情報空取得処理終了')

        return True, target_code_list

    async def websocket_main(self):
        '''
        WebSocket接続/受信とDBへの登録処理を行う

        Returns:
            bool: 処理結果
        '''
        self.log.info('WebSocket接続処理開始')

        # デバッグモードチェック
        if self.config.BOARD_RECORD_DEBUG == False:
            # 日付チェック
            if self.util.culc_time.exchange_date() == False:
                self.log.info('非営業日のためPUSH配信受信を行いません')
                return True

            # 時間チェック
            time_type = self.util.culc_time.exchange_time(datetime.now())
            # 寄り前
            if time_type == 3:
                # 寄り1秒前まで待機
                _ = self.util.culc_time.wait_time(hour = 8, minute = 59, second = 59)
            # お昼休み
            elif time_type == 4:
                # 後場開始1秒前まで待機
                _ = self.util.culc_time.wait_time(hour = 12, minute = 29, second = 59)
            # クロージング・オークション / 大引け後
            elif time_type in [5, 6]:
                self.log.info('クロージング・オークション/大引け後のためPUSH配信受信を行いません')
                return True

        error_counter = 0

        # WebSocket接続/PUSH配信の受信
        ws_handler = await self.api.websocket.connect()
        async with ws_handler as ws:
            while True:
                try:
                    # デバッグモードでない場合のみ時間チェック
                    if self.config.BOARD_RECORD_DEBUG == False:
                        time_type = self.util.culc_time.exchange_time(datetime.now())
                        # お昼休み
                        if time_type == 4:
                            # 後場開始1秒前まで待機
                            _ = self.util.culc_time.wait_time(hour = 12, minute = 29, second = 59)
                        elif time_type in [5, 6]:
                            self.log.info('クロージング・オークション/大引け後のためPUSH配信受信を終了します')
                            break

                    # タイムアウト(=PUSH配信が来なくなるまで)の時間を計算
                    time_out = self.util.culc_time.get_trade_end_time_seconds(accurate = False)

                    self.log.info('PUSHメッセージ配信の待機')
                    # PUSHメッセージ配信の待機
                    message = await asyncio.wait_for(ws.recv(), timeout = time_out)
                    self.log.info('PUSHメッセージ配信を受信')

                    # メッセージを受信したらレコードを設定する処理をコールバック関数として実行
                    asyncio.create_task(self.operate_ohlc(json.loads(message)))

                except Exception as e:
                    self.log.error(f'PUSH配信の受信処理でエラー\n{e}')
                    error_counter += 1
                    if error_counter >= 15:
                        self.log.error('エラーが続いたためWebSocket接続を終了します')
                        return False
                    continue

        self.log.info('WebSocket接続処理終了')
        return True

    async def operate_ohlc(self, reception_data):
        '''
        WebSocketで受信した板情報をDBに登録する

        Args:
            reception_data(dict): 受信したデータ
        '''
        self.log.info('四本値テーブルへの記録処理開始')
        # 既に記録済の同一分のデータを詰めるために使用
        recorded_ohlc_data = {}

        # 直近の取引時間のdatetime型に変換
        reception_data['CurrentPriceTime'] = datetime.strptime(reception_data['CurrentPriceTime'], '%Y-%m-%dT%H:%M:%S%z')
        # 直近の取引の秒を切り捨て
        reception_data['CurrentPriceMinute'] = reception_data['CurrentPriceTime'].replace(second = 0, microsecond = 0)

        # 受信データと同一分のデータが既に存在するか
        # 一時保存用のメモリをチェック
        if len(self.ohlc_list) > 0:
            for ohlc in self.ohlc_list:
                # メモリに存在する場合
                try:
                    if ohlc['symbol'] == reception_data['Symbol'] and ohlc['trade_time'] == reception_data['CurrentPriceMinute']:
                        recorded_ohlc_data = ohlc
                        break
                except Exception as e:
                    self.log.error(f'メモリのチェック処理でエラー\n{e}')
                    self.log.error(f'ohlc[trade_time]: {ohlc["trade_time"]}')
                    self.log.error(f'reception_data[CurrentPriceMinute]: {reception_data["CurrentPriceMinute"]}')
                    continue

        # メモリに存在しない場合はDBをチェック
        if recorded_ohlc_data == {}:
            recorded_ohlc_data = self.db.ohlc.select_time(reception_data['Symbol'], reception_data['CurrentPriceMinute'])
            if recorded_ohlc_data == False:
                self.log.error('四本値テーブルの記録済みデータ取得処理でエラー')
                recorded_ohlc_data == {}
                # TODO エラーカウント追加

        # 記録済のデータがない場合は直近の累計出来高を取得
        total_volume = -999
        if recorded_ohlc_data == {}:
            # まずはメモリからチェック
            total_volume = self.get_latest_total_volume(reception_data)
            # メモリに存在しない場合はDBをチェック
            if total_volume == -999:
                total_volume = self.db.ohlc.select_latest_total_volume(reception_data['Symbol'], reception_data['CurrentPriceMinute'].date())
                if total_volume == False:
                    self.log.error('四本値テーブルの累計出来高取得処理でエラー')
                    total_volume = -999

        # レコード未存在/エラーで-999としていたデータを0に変更
        if total_volume == -999:
            total_volume = 0

        # 受信したデータと記録済みのOHLCデータをもとに、DBテーブル用のフォーマットに成形
        result, new_ohlc_data = self.util.mold.response_to_ohlc(reception_data, recorded_ohlc_data, total_volume)
        if result == False:
            self.log.error(new_ohlc_data)
            self.log.error(f'記録に失敗したデータ: {reception_data}')
            return False

        # 先にメモリを更新
        for ohlc in self.ohlc_list[:]:
            try:
                if ohlc['symbol'] == new_ohlc_data['symbol'] and ohlc['trade_time'] == new_ohlc_data['trade_time']:
                    self.ohlc_list.remove(ohlc)
                    break
            except Exception as e:
                self.log.error(f'メモリの更新処理でエラー\n{e}')
                self.log.error(f'ohlc[trade_time]: {ohlc["trade_time"]}')
                self.log.error(f'new_ohlc_data[trade_time]: {new_ohlc_data["trade_time"]}')
                continue
        self.ohlc_list.append(new_ohlc_data)

        # 既に記録済み/使用しないためメモリにいらないデータは削除する
        result = self.memory_cleaning()

        # DBを更新 TODO 3,4回/秒x銘柄数分upsertするので、頻度を減らしたい
        result = self.db.ohlc.upsert(new_ohlc_data)
        if result != True:
            return False

        self.log.info('四本値テーブルへの記録終了')
        return True

    def insert_board(self, board_info):
        '''
        boardテーブルにレコードを追加する

        Args:
            board_info(dict): 板情報データ

        Returns:
            result(bool): SQL実行結果
        '''
        result = self.db.board.insert(board_info)
        if result != True:
            self.log.error(f'板情報追加処理でエラー\n{result}')

    def info_board(self, stock_code, market_code = 1, add_info = True, retry_count = 0):
        '''
        APIを使用し板情報を取得する

        Args:
            stock_code(int or str): 証券コード
            market_code(int or str): 市場コード
                1: 東証、3: 名証、5: 福証、6: 札証、2: 日通し、23: 日中、24: 夜間
            add_info(bool): 下記4項目の情報を併せて取得するか
                「時価総額」、「発行済み株式数」、「決算期日」、「清算値」
            retry_count(int): リトライ回数

        Returns:
            bool: 処理結果
            board_info(dict) or error_code(int): APIから取得した板情報 or エラーコード
        '''
        self.log.info(f'板情報取得APIリクエスト送信処理開始 証券コード: {stock_code}')
        # APIでリクエスト送信
        result, board_info = self.api.info.board(stock_code, market_code, add_info)

        # 処理に失敗
        if result == False:
            # 登録数上限エラー
            if board_info == 4002006:
                self.log.error('板情報取得APIで銘柄登録数上限エラーが発生しました')

                # 登録銘柄全解除処理
                result = self.unregister_all()

                # 登録解除成功
                if result == True:
                    # 回帰で二度同じところに来るのはおかしいのでFalseとして返す(無限ループ回避)
                    if retry_count == 1:
                        self.log.error('無限ループに陥る可能性のあるエラーが発生しています')
                        return False, -1

                    # 成功したら回帰で再度リクエスト送信
                    result, board_info = self.info_board(self, stock_code, market_code = market_code, add_info = add_info, retry_count = 1)
                    if board_info == False:
                        return False, board_info
                else:
                    return False

            # 指定コードの銘柄が存在しないエラー
            elif board_info == 402001:
                self.log.error(f'指定した証券コードの板情報が存在しません 証券コード: {stock_code}')
                return False, 402001
            # その他のエラー
            else:
                self.log.error(f'板情報取得APIでエラーが発生しました 証券コード: {stock_code}\n{board_info}')
                return False, board_info

        self.log.info(f'板情報取得APIリクエスト送信処理終了 証券コード: {stock_code}')
        return True, board_info

    def unregister_all(self):
        '''
        APIを使用し登録済みの銘柄をすべて解除する

        Return
            bool: 処理実行結果
        '''
        self.log.info('全銘柄登録解除APIへのリクエスト送信処理開始')

        result = self.api.register.unregister_all()
        if result != True:
            self.log.error(f'全銘柄登録解除APIへのリクエスト処理でエラー\n{result}')
            return False

        self.log.info('全銘柄登録解除APIへのリクエスト送信処理終了')
        return True

    def record_board_csv(self, board_info):
        '''
        板情報をCSVに記録する

        Args:
            board_info(dict): 板情報データ

        Returns:
            bool: 処理結果
        '''
        # 板情報をCSVに記録
        self.log.info('板情報CSV出力処理開始')
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv', f'{self.today}_{board_info["stock_code"]}.csv')
        result, error_message = self.util.file_manager.write_csv(csv_path, board_info, add_mode = True)
        if result != True:
            self.log.error(f'板情報CSV出力処理でエラー\n{error_message}')
            return False
        self.log.info('板情報CSV出力処理終了')
        return True

    def get_latest_total_volume(self, reception_data):
        '''
        最新の累計出来高を取得する基準日時に最も近い時間の累計出来高を取得

        Args:
            reception_data(dict): 受信したデータ

        Returns:
            int: 最新の累計出来高
        '''
        latest_date, latest_total_volume = self.jst.localize(self.util.culc_time.get_now(accurate = False).replace(hour = 23, minute = 59)), -999
        for ohlc in self.ohlc_list:
            if ohlc['symbol'] == reception_data['Symbol']:
                if latest_date <= ohlc['trade_time']:
                    latest_date, latest_total_volume = ohlc['trade_time'], ohlc['total_volume']
        return latest_total_volume

    def memory_cleaning(self):
        '''
        メモリで保持しているデータの中からいらないものを取り除く

        Returns:
            bool: 処理結果
        '''
        # 管理用の連想配列
        memory_dict = {}
        # 削除する要素を一時的に保持するリスト
        to_remove = []

        # メモリの中から取引情報をチェック
        for index, ohlc in enumerate(self.ohlc_list):
            # 銘柄コードが管理用の連想配列に存在しない場合は追加
            if ohlc['symbol'] not in memory_dict:
                memory_dict[ohlc['symbol']] = (ohlc['trade_time'], index)
            else:
                # 同じ銘柄コードで取引時間が古いものはいらないので削除リストに追加
                if memory_dict[ohlc['symbol']][0] > ohlc['trade_time']:
                    to_remove.append(index)
                else:
                    to_remove.append(memory_dict[ohlc['symbol']][1])
                    memory_dict[ohlc['symbol']] = (ohlc['trade_time'], index)

        # 一括で削除 削除してインデックス番号がずれるのを防ぐために逆順で削除
        for index in sorted(to_remove, reverse = True):
            # TODO DBに登録されているかのチェック
            
            # 登録されていたら本当に削除
            del self.ohlc_list[index]

        return True