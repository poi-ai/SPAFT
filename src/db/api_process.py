class Api_Process():
    '''api_process�ơ��֥������'''

    def __init__(self, log, conn, dict_return):
        '''

        Args:
            log(Log): ������������饹�Υ��󥹥���
            conn(): DB��³���饹�Υ��󥹥���
            dict_return(): SQL�η�̤�dict�����֤�����Υ��饹̾

        '''
        self.log = log
        self.conn = conn
        self.dict_return = dict_return