import csv
import os
import py7zr

class FileManager():
    '''ファイルの入力・出力を行うクラス'''
    def __init__(self, log):
        self.log = log

    def read_file(self, file_path):
        '''
        ファイルを読み込む

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

    def move_file(self, src_path, dst_path):
        '''
        ファイルを移動する

        Args:
            src_path(str): 移動元のファイルパス
            dst_path(str): 移動先のファイルパス

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''
        self.log.info(f'ファイル移動処理開始 {src_path} -> {dst_path}')

        try:
            os.rename(src_path, dst_path)
        except Exception as e:
            self.log.error(f'ファイル移動でエラー\n移動元: {src_path}\n移動先: {dst_path}\n{e}')
            return False, e

        self.log.info(f'ファイル移動処理終了')
        return True, None

    def compress_csv_files(self, directory, output_file):
        '''
        指定したディレクトリ内の.gitkeep以外のすべてのCSVファイルを一つの.7zファイルに圧縮する

        Args:
            directory(str): 対象ディレクトリのパス
            output_file(str): 出力する.7zファイルのパス

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''
        self.log.info(f'CSVファイル圧縮処理開始')
        csv_files = []

        try:
            # 圧縮対象のCSVファイルを取得
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.csv') and file != '.gitkeep':
                        file_path = os.path.join(root, file)
                        csv_files.append(file_path)

            self.log.info(f'圧縮対象のCSVファイル数: {len(csv_files)}')

            # CSVファイルを.7zファイルに圧縮
            with py7zr.SevenZipFile(output_file, 'w') as archive:
                for file_path in csv_files:
                    archive.write(file_path, arcname=os.path.basename(file_path))

        except Exception as e:
            self.log.error(f'CSVファイルの圧縮処理でエラー\nディレクトリ: {directory}\n出力ファイル: {output_file}\n{e}')
            return False, e

        # 圧縮成功後に元のCSVファイルを削除する
        try:
            for file_path in csv_files:
                os.remove(file_path)
        except Exception as e:
            self.log.error(f'元のCSVファイルの削除処理でエラー\n{e}')
            return False, e

        self.log.info(f'CSVファイル圧縮処理終了')
        return True, None