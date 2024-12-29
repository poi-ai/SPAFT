import json
import os
from service_base import ServiceBase

class Record(ServiceBase):
    '''データ取得に関するServiceクラス'''
    def __init__(self, api_headers, api_url, conn):
        super().__init__(api_headers, api_url, conn)

    def record_init(self, target_code_list, debug = False):
        '''
        データ取得系処理を行うときの初期処理

        Args:
            target_code_list(list): 取得対象の銘柄リスト
            debug(bool): デバッグモードか

        Return:
            bool: 判定結果(T: 営業日、F: 非営業日)
            target_code_list(list): 取得不可能な銘柄を除いた取得対象の銘柄リスト

        '''
        if debug == True:
            self.log.info('デバッグモードのため営業日判定処理をスキップします')
        else:
            self.log.info('営業日判定処理開始')
            result = self.util.culc_time.exchange_time()
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

        # 取得対象の銘柄の初回データ取得は時間がかかるので先に板情報の空取得を行う
        self.log.info('初回板情報空取得処理開始')
        for stock_code in target_code_list[:]:
            result, error_code = self.info_board(stock_code, market_code = 1, add_info = False)
            if result == False and error_code == 402001:
                target_code_list.remove(stock_code)
        self.log.info('初回板情報空取得処理終了')

        return True, target_code_list

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
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'csv', f'{board_info["Symbol"]}.csv')
        result, error_message = self.util.file_manager.write_csv(csv_path, board_info, add_mode = True)
        if result != True:
            self.log.error(f'板情報CSV出力処理でエラー\n{error_message}')
            return False
        self.log.info('板情報CSV出力処理終了')
        return True