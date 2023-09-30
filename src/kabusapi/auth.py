import requests
import traceback
from base import Base

class Auth(Base):
    '''トークン発行用API'''
    def __init__(self, api_url):
        super().__init__()
        self.token = ''
        self.api_url = api_url

    def issue_token(self, api_password):
        '''
        トークンを発行する

        Args:
            api_password(str): APIのパスワード

        Returns:
            bool: 処理結果
        '''
        url = f'{self.api_url}/token'
        data = {'APIPassword': api_password}

        try:
            response = requests.post(url, json = data)
        except Exception as e:
            self.error_output('トークン発行取得処理でエラー', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.error_output(f'トークン発行取得処理でエラー\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        self.token = response.json()['Token']
        return self.token