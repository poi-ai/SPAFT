import requests

class Auth():
    def __init__(self):
        self.token = ''

    def issue_token(self, api_password):
        '''
        トークンを発行する

        Args:
            api_password(str): APIのパスワード

        Returns:
            bool: 処理結果
        '''
        url = 'http://localhost:18080/token'
        data = {'APIPassword': api_password}

        try:
            response = requests.post(url, json = data)
        except Exception as e:
            pass # ここにエラー処理
            return False

        if response.status_code != 200:
            pass # ここにエラー処理
            return False

        self.token = response.json()['Token']
        return True