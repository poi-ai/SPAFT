import time
import traceback
import pandas as pd
from datetime import datetime, timedelta

from .scalping import Scalping


class StatDaytrade(Scalping):
    '''
    統計ベースのエントリー条件を用いたデイトレードRPA(Phase 3)
    プレイブック(report/trading_playbook.md)に準拠

    MVP は戦略B(RSI(9)<10 で買い、30分保有)のみを実装する
    A/C/D/E/X/W は段階追加とする
    '''

    # 戦略ごとのパラメータ定義
    STRATEGY_PARAMS = {
        'B': {
            'side': 'buy',
            'hold_minutes': 30,
            'sl_loss_pct': -0.007,    # 含み損 -0.7% で損切り(SL-1)
            'rsi_threshold': 10,
        },
    }

    # 戦略の優先順位(同時発火時)
    STRATEGY_PRIORITY = ['B', 'C', 'E', 'A', 'D']

    def __init__(self, api_headers, api_url, ws_url, conn):
        super().__init__(api_headers, api_url, ws_url, conn)

        # 設定値
        self.enabled_strategies = []
        self.bb_width_filter = 0.0036

        # 建玉管理(現在は単一銘柄MVP想定。複数銘柄化時はキー=証券コードのdictへ)
        self.position = None  # {'strategy': 'B', 'entry_price': X, 'entry_time': dt, 'qty': Y, 'rsi_peak': float, 'rci_at_entry': float}

        # サーキットブレーカー状態
        self.circuit_break_all = False
        self.disabled_strategies = set()

    # ---------------- 初期処理 ----------------

    def stat_daytrade_init(self, config):
        '''
        Phase 3 デイトレードRPAの初期処理
        scalping_init() の処理ベースを流用しつつ、本戦略専用のパラメータを読む

        Returns:
            result(bool): 実行結果
        '''
        self.log.info('Phase3デイトレRPA初期処理開始')

        # 戦略パラメータの読み込み
        if not self.param_check(config):
            return False

        # 営業日チェック
        if self.util.culc_time.exchange_date() == False:
            self.log.info('本日は取引所の営業日でないため取引を行いません')
            return False
        self.log.info('営業日チェックOK')

        # 営業時間チェック
        if self.util.culc_time.exchange_time() == 5:
            self.log.info('本日の取引時間を過ぎているため処理を行いません')
            return False

        # 信用余力の取得
        buy_power = self.get_margin_buy_power()
        if buy_power is False:
            return False
        self.buy_power = buy_power
        self.log.info(f'信用余力取得OK: {buy_power}円')
        time.sleep(1)

        # 銘柄の優先市場
        result, exch_info = self.api.info.primary_exchange(stock_code=self.stock_code)
        if result == False:
            self.log.error(f'優先市場取得失敗\n{exch_info}')
            return False
        self.market_code = exch_info['PrimaryExchange']
        time.sleep(1)

        # 銘柄情報
        result, stock_info = self.get_symbol(stock_code=self.stock_code,
                                             market_code=self.market_code,
                                             addinfo=False)
        if result == False:
            self.log.error(stock_info)
            return False

        if stock_info.get('KCMarginBuy') != True:
            self.log.warning(f'デイトレ信用が利用できない銘柄です: {self.stock_code}')
            return False

        self.stock_info['unit_num'] = stock_info['TradingUnit']
        self.stock_info['upper_limit'] = stock_info['UpperLimit']
        self.stock_info['lower_limit'] = stock_info['LowerLimit']
        self.stock_info['yobine_group'] = stock_info['PriceRangeGroup']

        self.util.stock_price.set_yobine_group(stock_info['PriceRangeGroup'])
        result, error_message = self.util.stock_price.set_yobine_list(
            stock_info['LowerLimit'] if 'LowerLimit' in stock_info else self.stock_info['lower_limit'],
            stock_info['UpperLimit'] if 'UpperLimit' in stock_info else self.stock_info['upper_limit'],
            stock_info['PriceRangeGroup'])
        if result == False:
            self.log.error(f'呼値リスト作成失敗: {error_message}')
            return False

        # 余力チェック
        if self.buy_power < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            mid_need = (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2
            if self.buy_power < mid_need:
                self.log.error(f'余力不足のため取引不可 余力:{self.buy_power}円 1単元概算:{mid_need}円')
                return False
            self.log.warning(f'ストップ高分の余力なし(途中で発注不可になる恐れ) 余力:{self.buy_power}円')

        self.log.info('Phase3デイトレRPA初期処理終了')
        return True

    def param_check(self, config):
        '''
        統計デイトレ用のパラメータ読み込み

        config に必要な属性:
            STAT_TRADE_PASSWORD : 取引パスワード(なければ TRADE_PASSWORD を流用)
            STAT_STOCK_CODE     : 対象銘柄(なければ STOCK_CODE を流用)
            STAT_ENABLED_STRATEGIES : 有効化する戦略リスト(例: ['B'])
            STAT_BB_WIDTH_MIN_RATIO : BB幅/close 下限(デフォルト 0.0036)
        '''
        try:
            self.trade_password = getattr(config, 'STAT_TRADE_PASSWORD', None) or config.TRADE_PASSWORD
            self.stock_code = getattr(config, 'STAT_STOCK_CODE', None) or config.STOCK_CODE
            self.enabled_strategies = list(getattr(config, 'STAT_ENABLED_STRATEGIES', ['B']))
            self.bb_width_filter = float(getattr(config, 'STAT_BB_WIDTH_MIN_RATIO', 0.0036))

            # 有効戦略のうち未実装のものは除外
            unsupported = [s for s in self.enabled_strategies if s not in self.STRATEGY_PARAMS]
            if unsupported:
                self.log.warning(f'未実装の戦略のためスキップします: {unsupported}')
                self.enabled_strategies = [s for s in self.enabled_strategies if s in self.STRATEGY_PARAMS]

            if not self.enabled_strategies:
                self.log.error('有効な戦略が設定されていません')
                return False

            self.log.info(f'有効戦略: {self.enabled_strategies} / BB幅下限比: {self.bb_width_filter}')
            return True
        except Exception as e:
            self.error_output('統計デイトレパラメータ読み込みでエラー', e, traceback.format_exc())
            return False

    # ---------------- リアルタイム指標計算 ----------------

    def calc_realtime_indicators(self, symbol, end_time):
        '''
        直近 N 本の OHLC を DB から取得し、戦略B 判定に必要な指標(最新値)を返す

        Args:
            symbol(str): 銘柄コード
            end_time(datetime): この時刻以前の直近データを使用

        Returns:
            result(bool)
            indicators(dict): 取得失敗時は None
                close(float)
                rsi9(float)
                rci26(float)
                bb_upper_2(float), bb_lower_2(float), bb_upper_3(float), bb_lower_3(float)
                bb_width(float)
        '''
        try:
            # RSI(9)/RCI(26)/BB(20) すべてを満たす窓幅。余裕を持って 60本取得する
            need_n = 60
            result, rows = self.db.ohlc.select_range(symbol=str(symbol), end_time=end_time, n=need_n)
            if result == False or rows is None or len(rows) < 21:
                self.log.warning(f'指標計算用 OHLC データが不足: {0 if rows is None else len(rows)}件')
                return False, None

            df = pd.DataFrame(rows)
            # close_price が必須
            if 'close_price' not in df.columns:
                self.log.error('close_price カラムが OHLC レコードに存在しません')
                return False, None

            # NaN 行の除去(出来高 0 で stub になっているケース対策)
            df = df.dropna(subset=['close_price']).reset_index(drop=True)
            if len(df) < 21:
                return False, None

            ind = self.util.indicator
            # RSI(9)
            ok, df = ind.get_rsi(df, 'rsi9', window_size=9, interval=1, price_column_name='close_price')
            if not ok:
                return False, None
            # RCI(26)
            if len(df) >= 26:
                ok, df = ind.get_rci(df, 'rci26', window_size=26, interval=1, price_column_name='close_price')
                if not ok:
                    return False, None
            else:
                df['rci26'] = float('nan')
            # BB(20)
            ok, df = ind.get_bollinger_bands(df, 'bb', window_size=20, interval=1, price_column_name='close_price')
            if not ok:
                return False, None

            last = df.iloc[-1]
            indicators = {
                'close': float(last['close_price']),
                'rsi9': None if pd.isna(last.get('rsi9')) else float(last['rsi9']),
                'rci26': None if pd.isna(last.get('rci26')) else float(last['rci26']),
                'bb_upper_2': None if pd.isna(last.get('bb_upper_2sigma')) else float(last['bb_upper_2sigma']),
                'bb_lower_2': None if pd.isna(last.get('bb_lower_2sigma')) else float(last['bb_lower_2sigma']),
                'bb_upper_3': None if pd.isna(last.get('bb_upper_3sigma')) else float(last['bb_upper_3sigma']),
                'bb_lower_3': None if pd.isna(last.get('bb_lower_3sigma')) else float(last['bb_lower_3sigma']),
                'bb_width': None if pd.isna(last.get('bb_width')) else float(last['bb_width']),
            }
            return True, indicators
        except Exception as e:
            self.error_output('リアルタイム指標計算でエラー', e, traceback.format_exc())
            return False, None

    # ---------------- エントリー判定 ----------------

    def is_entry_window(self, now, hold_minutes):
        '''
        プレイブック §6 の時間帯フィルタ。エントリー可能時間か判定する

        Args:
            now(datetime)
            hold_minutes(int): 戦略の保有時間

        Returns:
            bool: True ならエントリー可能
        '''
        h, m = now.hour, now.minute
        # 寄り直後 09:00〜09:30 は全戦略禁止
        if h < 9 or (h == 9 and m < 30):
            return False
        # 前場引け前 11:25〜11:30 禁止
        if h == 11 and m >= 25:
            return False
        # 昼休み 11:30〜12:30 禁止
        if h == 12 and m < 30:
            return False
        # 後場寄付き 12:30〜12:35 禁止
        if h == 12 and m < 35:
            return False
        # 15:25 以降禁止
        if h == 15 and m >= 25:
            return False
        if h >= 16:
            return False
        # 保有時間ごとのバックオフ
        # 大引け 15:25 から hold_minutes 引いた時刻以降は新規禁止
        cutoff = now.replace(hour=15, minute=25, second=0, microsecond=0) - timedelta(minutes=hold_minutes)
        if now >= cutoff:
            return False
        return True

    def check_common_filter(self, indicators):
        '''共通エントリーフィルタ(BB幅 Q3以上)'''
        if indicators.get('bb_width') is None or indicators.get('close') in (None, 0):
            return False
        ratio = indicators['bb_width'] / indicators['close']
        return ratio >= self.bb_width_filter

    def evaluate_entry(self, indicators, now):
        '''
        有効戦略のうちエントリー条件を満たすものを優先順位で1件返す

        Returns:
            strategy_id(str) or None
        '''
        if self.circuit_break_all:
            return None

        if not self.check_common_filter(indicators):
            return None

        candidates = []
        for sid in self.enabled_strategies:
            if sid in self.disabled_strategies:
                continue
            if not self.is_entry_window(now, self.STRATEGY_PARAMS[sid]['hold_minutes']):
                continue

            if sid == 'B':
                rsi = indicators.get('rsi9')
                if rsi is not None and rsi < self.STRATEGY_PARAMS['B']['rsi_threshold']:
                    candidates.append('B')
            # A/C/D/E/X/W は段階追加

        if not candidates:
            return None

        # 優先順位順に1件選択
        for sid in self.STRATEGY_PRIORITY:
            if sid in candidates:
                return sid
        return candidates[0]

    # ---------------- エグジット判定 ----------------

    def evaluate_exit(self, indicators, now):
        '''
        保有中の建玉に対し、TP/SL/MS/時間ストップを順番に判定する

        Returns:
            (should_exit(bool), reason(str) or None)
        '''
        if self.position is None:
            return False, None

        pos = self.position
        sid = pos['strategy']
        params = self.STRATEGY_PARAMS[sid]
        close = indicators.get('close')
        if close is None:
            return False, None

        entry_price = pos['entry_price']
        pnl_ratio = (close - entry_price) / entry_price if entry_price else 0.0
        held_minutes = (now - pos['entry_time']).total_seconds() / 60.0

        # RSI ピークを更新(MS-1 用)
        rsi = indicators.get('rsi9')
        if rsi is not None and rsi > pos.get('rsi_peak', -1):
            pos['rsi_peak'] = rsi

        # 買い側のみ実装(MVP)
        if params['side'] == 'buy':
            # SL-4: close < BB lower 3σ
            if indicators.get('bb_lower_3') is not None and close < indicators['bb_lower_3']:
                return True, 'SL-4: BB lower 3σ 割れ'
            # SL-1/SL-2: 含み損
            if pnl_ratio <= params['sl_loss_pct']:
                return True, f'SL: 含み損 {pnl_ratio*100:.2f}%'
            # SL-6: 1.5倍時間超過(保険)
            if held_minutes >= params['hold_minutes'] * 1.5:
                return True, 'SL-6: 保有時間超過'
            # TP-1: BB upper 2σ 抜け
            if indicators.get('bb_upper_2') is not None and close >= indicators['bb_upper_2']:
                return True, 'TP-1: BB upper 2σ 到達'
            # TP-2: RSI>=80 AND RCI>=80
            if rsi is not None and indicators.get('rci26') is not None:
                if rsi >= 80 and indicators['rci26'] >= 80:
                    return True, 'TP-2: RSI/RCI 共に高水準'
            # TP-4: 半分時間到達 AND 含み益>=+0.1%
            if held_minutes >= params['hold_minutes'] / 2 and pnl_ratio >= 0.001:
                return True, 'TP-4: 半分時間+含み益+0.1%'
            # MS-1: RSIが80超 → 50割れ
            if pos.get('rsi_peak', 0) >= 80 and rsi is not None and rsi < 50:
                return True, 'MS-1: RSIモメンタム反転'
            # 時間ストップ
            if held_minutes >= params['hold_minutes']:
                return True, '時間ストップ'

        return False, None

    # ---------------- 取引ループ ----------------

    def run(self):
        '''メインの取引ループ。毎分00〜02秒で判定を行う'''
        self.log.info('Phase3 デイトレRPA メインループ開始')

        try:
            while True:
                # 大引け後/休日終了
                now = self.util.culc_time.get_now()
                exch = self.util.culc_time.exchange_time(now)

                # お昼休みは保有も止め、後場開始まで待機
                if exch == 4:
                    self.log.info('お昼休みのため後場開始まで待機')
                    self.util.culc_time.wait_time(hour=12, minute=30)
                    continue

                # 大引け後は終了
                if exch == 5 or exch == 6:
                    if self.position is not None:
                        self.log.info('大引け後/CA時間: 強制成行決済を実行')
                        self.enforce_management(trade_type='大引け')
                        self.position = None
                    self.log.info('取引終了時刻に到達したためループを抜ける')
                    break

                # 15:25 強制決済(プレイブック §6)
                if now.hour == 15 and now.minute >= 25:
                    if self.position is not None:
                        self.log.info('15:25 到達: 全建玉強制成行決済')
                        self.enforce_management(trade_type='15:25強制決済')
                        self.position = None
                    break

                # 11:30 直前の前場引け対応
                if exch == 1 and now.hour == 11 and now.minute >= 28:
                    if self.position is not None:
                        self.log.info('前場引け前: 建玉を強制成行決済')
                        self.enforce_management(trade_type='前場引け')
                        self.position = None
                    self.log.info('お昼休みまで待機')
                    self.util.culc_time.wait_time(hour=12, minute=30)
                    continue

                # 寄り前は待機
                if exch == 3:
                    self.log.info('寄り前のため 09:00 まで待機')
                    self.util.culc_time.wait_time(hour=9, minute=0)
                    continue

                # 直近1分のクローズ(now の分の頭)時点までを使用する
                end_time = now.replace(second=0, microsecond=0) - timedelta(seconds=1)

                # 指標計算
                ok, indicators = self.calc_realtime_indicators(self.stock_code, end_time)
                if not ok:
                    self._sleep_until_next_minute()
                    continue

                # 保有中ならエグジット判定を最優先
                if self.position is not None:
                    should_exit, reason = self.evaluate_exit(indicators, now)
                    if should_exit:
                        self.log.info(f'エグジットシグナル: {reason}')
                        self.enforce_management(trade_type=f'戦略エグジット({reason})')
                        self.position = None
                else:
                    # エントリー判定
                    sid = self.evaluate_entry(indicators, now)
                    if sid is not None:
                        self.log.info(f'エントリーシグナル: 戦略{sid} (close={indicators["close"]}, rsi9={indicators.get("rsi9")})')
                        ok2, order_price = self.buy_order(stock_price=indicators['close'])
                        if ok2:
                            self.position = {
                                'strategy': sid,
                                'entry_price': order_price,
                                'entry_time': now,
                                'qty': self.stock_info['unit_num'],
                                'rsi_peak': indicators.get('rsi9') or 0,
                                'rci_at_entry': indicators.get('rci26'),
                            }
                        else:
                            self.log.error('買い注文失敗')

                self._sleep_until_next_minute()

        except Exception as e:
            self.error_output('Phase3デイトレRPA メインループでエラー', e, traceback.format_exc())
        finally:
            # 最終安全弁: 残建玉があれば強制決済
            try:
                self.enforce_management(trade_type='ループ終了時クリーンアップ')
            except Exception as e:
                self.log.error(f'クリーンアップ強制決済でエラー\n{e}')

        self.log.info('Phase3 デイトレRPA メインループ終了')

    def _sleep_until_next_minute(self):
        '''次の分の 00 秒+少しのバッファまで待機する'''
        try:
            self.util.culc_time.wait_time_next_minute(accurate=False)
        except Exception:
            time.sleep(5)
