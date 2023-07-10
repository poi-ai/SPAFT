import requests

class Order():
    '''投資商品の注文に関するAPI'''
    def __init__(self, api_headers):
        self.api_headers = api_headers

    def stock(self):
        '''日本株の注文を発注する'''
        pass

    def future(self):
        '''先物の注文を発注する'''
        pass

    def option(self):
        '''オプション銘柄の注文を発注する'''
        pass

    def cancel(self):
        '''注文をキャンセルする'''
        pass