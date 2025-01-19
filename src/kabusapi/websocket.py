import asyncio
import json
import time
import traceback
import websockets
from datetime import datetime, time

class Websocket():
    '''Websocket通信を行うクラス'''

    def __init__(self, ws_url, log):
        self.ws_url = ws_url
        self.log = log

    async def connect(self):
        '''
        Websocket接続を確立する

        Returns:
            handler(websockets.connect): Websocket接続ハンドラ
        '''
        url = f'{self.ws_url}/websocket'
        try:
            handler = await websockets.connect(url, ping_timeout = None)
        except Exception as e:
            self.log.error(f'Websocket接続確率処理でエラー\n{e}')
            return False
        return handler