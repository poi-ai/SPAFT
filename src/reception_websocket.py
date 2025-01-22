
import asyncio
import config
import json
import time
from base import Base

class ReceptionWebsocket(Base):
    '''Websocketで取引情報を取得し、DBに登録する'''
    def __init__(self):
        super().__init__()

    async def main(self):
        # 初期処理(営業日判定/登録済銘柄の解除/PUSH配信を受ける銘柄の登録)
        record_init = self.service.record.record_init(config.RECORD_STOCK_CODE_LIST, config.BOARD_RECORD_DEBUG, push_mode = True)
        if record_init == False:
            return False

        # WebSocket接続/PUSH配信の受信/データのDB登録
        try:
            await self.service.record.websocket_main()
        except Exception as e:
            self.log.error(f'WebSocket接続でエラー\n{e}')
            return False

if __name__ == "__main__":
    rw = ReceptionWebsocket()
    asyncio.run(rw.main())