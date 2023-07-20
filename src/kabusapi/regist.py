import requests

class Regist():
    '''PUSH配信に関連するAPI'''
    def __init__(self, api_headers, api_url):
        self.api_headers = api_headers
        self.api_url = api_url

    def regist(self):
        '''PUSH配信する銘柄を登録する'''
        pass

    def unregist(self):
        '''指定した銘柄のPUSH配信を解除する'''
        pass

    def unregist_all(self):
        '''全ての銘柄のPUSH配信を解除する'''
        pass