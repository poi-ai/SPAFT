import json
import traceback
import websockets

class Websocket():
    '''Websocket通信を行うクラス'''

    def __init__(self, ws_url, log):
        self.ws_url = ws_url
        self.log = log

    async def connect(self, on_message):
        '''
        Websocket接続を確立する

        Args:
            on_message(function): メッセージ受信時のコールバック関数

        Returns:
            bool: Websocket接続の成否
        '''
        url = f'{self.ws_url}/websocket'

        async with websockets.connect(url, ping_timeout = None) as websocket:
            while True:
                try:
                    # PUSHメッセージを待つ
                    message = await websocket.recv()

                    # メッセージを受信したらコールバック関数を実行
                    await on_message(json.loads(message))

                except Exception as e:
                    return f'{e}\n{traceback.format_exc()}'
        return True