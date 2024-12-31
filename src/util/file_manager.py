import csv

class FileManager:
    '''ファイルの入力・出力を行うクラス'''
    def __init__(self, log):
        self.log = log

    def read_csv(self, file_path):
        '''
        CSVファイルを読み込む

        Args:
            file_path(str): ファイルパス

        Returns:
            result(bool): 実行結果
            data(list) or error_message(str): 読み込んだデータ or エラーメッセージ
        '''
        self.log.info(f'CSVファイル読み込み処理開始 ファイルパス: {file_path}')

        try:
            with open(file_path, 'r', encoding = 'utf-8') as f:
                data = f.readlines()
        except Exception as e:
            self.log.error(f'CSVファイル読み込みでエラー\nファイルパス: {file_path}\n{e}')
            return False, e

        self.log.info(f'CSVファイル読み込み処理終了 ファイルパス: {file_path}')
        return True, data

    def write_csv(self, file_path, data, add_mode = False):
        '''
        CSVファイルに書き込む

        Args:
            file_path(str): ファイルパス
            data(dict): 書き込むデータ
            add_mode(bool): 追記モードか (True: 追記、 False: 上書き)

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''
        self.log.info(f'CSVファイル書き込み処理開始')

        try:
            with open(file_path, 'a' if add_mode == True else 'w', newline = '', encoding = 'utf-8') as f:
                writer = csv.DictWriter(f, fieldnames = data.keys())

                # ファイルが空の場合、ヘッダーを書き込む
                if f.tell() == 0:
                    writer.writeheader()

                writer.writerow(data)
        except Exception as e:
            self.log.error(f'CSVファイル書き込みでエラー\nファイルパス: {file_path}\n{e}')
            return False, e

        self.log.info(f'CSVファイル書き込み処理終了')
        return True, None