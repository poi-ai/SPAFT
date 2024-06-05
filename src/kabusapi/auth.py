import json
import requests
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
            result(bool): 処理結果
            token(str): APIトークン or エラーメッセージ
        '''
        url = f'{self.api_url}/token'
        data = {'APIPassword': api_password}

        try:
            response = requests.post(url, json = data)
        except RequestException:
            return False, -1
        except Exception as e:
            return False, e

        if response.status_code != 200:
            return False, f'{response.status_code}\n{json.loads(response.content)}'

        self.token = response.json()['Token']
        return True, self.token