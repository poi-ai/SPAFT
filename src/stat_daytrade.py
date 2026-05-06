import config
from base import Base


class StatDaytradeMain(Base):
    '''
    統計ベースのエントリー条件を用いたデイトレードRPA(Phase 3) エントリースクリプト
    実装の詳細は src/service/trade/stat_daytrade.py を参照
    '''

    def __init__(self):
        super().__init__()
        # 統計デイトレードのServiceクラス
        self.logic = self.service.trade.stat_daytrade

    def main(self):
        self.log.info('SPAFT(統計デイトレRPA Phase3) 起動')

        # 強制決済のみ行うモード(scalping と共通の運用フラグを流用)
        if getattr(config, 'RECOVERY_SETTLEMENT', False):
            stock_code = getattr(config, 'STAT_STOCK_CODE', None) or config.STOCK_CODE
            trade_password = getattr(config, 'STAT_TRADE_PASSWORD', None) or config.TRADE_PASSWORD
            self.logic.enforce_management(trade_type='単一', trade_password=trade_password, stock_code=stock_code)
            return True

        # 初期処理
        if not self.logic.stat_daytrade_init(config):
            self.log.info('Phase3 デイトレRPA 初期処理でエラーのため終了します')
            return False

        # メインループ
        self.logic.run()

        self.log.info('SPAFT(統計デイトレRPA Phase3) 終了')
        return True


if __name__ == '__main__':
    StatDaytradeMain().main()
