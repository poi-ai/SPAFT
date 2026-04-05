
import asyncio
import config
import json
import time
import traceback
from base import Base

class OhlcPushCollector(Base):
    '''WebSocket PUSHで板情報を受信し、1分足OHLCに変換してDBに登録する'''
    def __init__(self):
        super().__init__()

    async def main(self):
        # 初期処理(営業日判定/登録済銘柄の解除/PUSH配信を受ける銘柄の登録)
        result, target_code_list = self.service.collect.record.record_init(config.RECORD_STOCK_CODE_LIST, config.BOARD_RECORD_DEBUG, push_mode = True)
        if result == False:
            return False

        # WebSocket接続/PUSH配信の受信/データのDB登録
        try:
            # 前場
            await self.service.collect.record.websocket_main(1)

            # 後場
            await self.service.collect.record.websocket_main(2)
        except Exception as e:
            self.log.error(f'WebSocket接続でエラー\n{e}\n{traceback.format_exc()}')
            return False

        # 大引け後バッチ: ohlcテーブル → CSV出力(1分/3分/5分足) → 7z圧縮 → DB削除
        result = self.service.collect.ohlc_export.export(
            target_code_list, self.service.collect.record.today
        )
        if result == False:
            return False

if __name__ == "__main__":
    rw = OhlcPushCollector()
    asyncio.run(rw.main())