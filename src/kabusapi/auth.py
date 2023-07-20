import requests

class Auth():
    '''トークン発行用API'''
    def __init__(self, api_url):
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
            pass # ここにエラー処理
            #print(e)
            return False

        if response.status_code != 200:
            #print(response.status_code)
            #print(response.content.decode('utf-8'))
            pass # ここにエラー処理
            return False

        print(response.content['Token'])

        self.token = response.json()['Token']
        return True