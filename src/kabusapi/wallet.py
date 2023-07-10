import requests

class Wallet():
    '''余力・保証金情報に関するAPI'''
    def __init__(self, api_headers):
        self.api_headers = api_headers

    def cash(self):
        '''現物の余力を取得する'''
        pass

    def margin(self):
        '''信用の余力を取得する'''
        pass

    def future(self):
        '''先物の余力を取得する'''
        pass

    def option(self):
        '''オプションの余力を取得する'''
        pass