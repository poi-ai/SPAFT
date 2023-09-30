import requests
import traceback
import urllib.parse
from base import Base

class Regist(Base):
    '''PUSH配信に関連するAPI'''
    def __init__(self, api_headers, api_url):
        super().__init__()
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
        url = f'{self.api_url}/unregister/all'

        try:
           response = requests.put(url, headers = self.api_headers)
        except Exception as e:
            self.error_output(f'全銘柄登録解除取得処理でエラー', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.error_output(f'全銘柄登録解除処理でエラ\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False
