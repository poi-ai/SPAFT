
import asyncio
import config
import json
import time
from base import Base

class ReceptionWebsocket(Base):
    '''Websocketで取引情報を取得し、DBに登録する'''
    def __init__(self):
        if config.WEBSOCKET_MODE == 1:
            super().__init__()
        else:
            super().__init__(use_db = False)

    async def main(self):
        # 初期処理(営業日判定/登録済銘柄の解除/PUSH配信を受ける銘柄の登録)
        record_init = self.service.record.record_init(config.RECORD_STOCK_CODE_LIST, config.BOARD_RECORD_DEBUG, push_mode = True)
        if record_init == False:
            return False

        # PUSH配信のモードをconfigから取得する
        websocket_mode = config.WEBSOCKET_MODE

        # WebSocket接続/PUSH配信の受信/データのDB登録
        try:
            # 前場
            await self.service.record.websocket_main(1, websocket_mode)

            # 後場
            await self.service.record.websocket_main(2, websocket_mode)
        except Exception as e:
            self.log.error(f'WebSocket接続でエラー\n{e}')
            return False

if __name__ == "__main__":
    rw = ReceptionWebsocket()
    asyncio.run(rw.main())