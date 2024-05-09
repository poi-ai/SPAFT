import requests
import traceback
from requests.exceptions import RequestException

class Auth():
    '''トークン発行用API'''
    def __init__(self, api_url, log):
        self.token = ''
        self.api_url = api_url
        self.log = log

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
        except RequestException:
            self.log.error('KabuStaionが起動していません')
            return False
        except Exception as e:
            self.log.error('トークン発行取得処理でエラー', e, traceback.format_exc())
            return False

        if response.status_code != 200:
            self.log.error(f'トークン発行取得処理でエラー\nエラーコード: {response.status_code}\n{self.byte_to_dict(response.content)}')
            return False

        self.token = response.json()['Token']
        return self.token