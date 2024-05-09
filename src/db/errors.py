class Errors():
    '''errorsテーブルを操作する'''

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