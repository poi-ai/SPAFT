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
        result, _ = self.param_check(config)
        if result == False:
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

        self.util.stock_price.set_yobine_group(self.stock_info['yobine_group'])
        result, error_message = self.util.stock_price.set_yobine_list(
            lower_price=self.stock_info['lower_limit'],
            upper_price=self.stock_info['upper_limit'],
            yobine_group=self.stock_info['yobine_group'])
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

        time.sleep(1)

        # 取引規制チェック
        self.log.info('取引規制情報取得処理開始')
        result, regulations_info = self.api.info.regulations(stock_code=self.stock_code,
                                                              market_code=self.market_code)
        if result == False:
            self.log.error(regulations_info)
            return False
        self.log.info('取引規制情報取得処理終了')

        time.sleep(1)

        # ソフトリミット
        self.log.info('ソフトリミット情報取得処理開始')
        result, response = self.api.info.soft_limit()
        if result == False:
            self.log.error(response)
            return False
        self.soft_limit = response['Margin'] * 10000
        self.log.info('ソフトリミット情報取得処理終了')

        if self.soft_limit < self.stock_info['upper_limit'] * self.stock_info['unit_num']:
            mid_need_soft = (self.stock_info['upper_limit'] + self.stock_info['lower_limit']) * self.stock_info['unit_num'] / 2
            if self.soft_limit < mid_need_soft:
                self.log.error(f'ソフトリミット不足のため取引不可 ソフトリミット:{self.soft_limit}円 1単元概算:{mid_need_soft}円')
                return False
            self.log.warning(f'ソフトリミットがストップ高分に届きません(途中で発注不可になる恐れ) ソフトリミット:{self.soft_limit}円')

        self.log.info('Phase3デイトレRPA初期処理終了')
        return True

    def param_check(self, config):
        '''
        統計デイトレ用のパラメータ読み込み
        親クラス Scalping.param_check と同じ戻り値 (bool, error_message) 形式とする

        config に必要な属性:
            STAT_TRADE_PASSWORD : 取引パスワード(なければ TRADE_PASSWORD を流用)
            STAT_STOCK_CODE     : 対象銘柄(なければ STOCK_CODE を流用)
            STAT_ORDER_LINE     : 注文時の現在価格からのオフセット(pips、デフォルト 0 = 基準価格そのまま)
            STAT_ENABLED_STRATEGIES : 有効化する戦略リスト(例: ['B'])
            STAT_BB_WIDTH_MIN_RATIO : BB幅/close 下限(デフォルト 0.0036)
            STAT_FILL_TIMEOUT_SECONDS : エントリー約定待機タイムアウト秒数(デフォルト 60)

        Returns:
            result(bool)
            error_message(str or None)
        '''
        try:
            self.trade_password = getattr(config, 'STAT_TRADE_PASSWORD', None) or config.TRADE_PASSWORD
            self.stock_code = getattr(config, 'STAT_STOCK_CODE', None) or config.STOCK_CODE

            # 親クラス Scalping が buy_order で参照する属性
            # ORDER_LINE = 0 で「基準価格そのままで指値」になる(stat_daytrade はクローズ価格基準のため通常 0)
            self.order_line = int(getattr(config, 'STAT_ORDER_LINE', 0))
            # securing_benefit/loss_cut/trail は stat_daytrade ロジック内では使わないが、
            # 親クラスのメソッドが内部参照する可能性があるため明示的に 0 で初期化する
            self.securing_benefit = 0
            self.loss_cut = 0
            self.trail = 0

            self.enabled_strategies = list(getattr(config, 'STAT_ENABLED_STRATEGIES', ['B']))
            self.bb_width_filter = float(getattr(config, 'STAT_BB_WIDTH_MIN_RATIO', 0.0036))
            self.fill_timeout_seconds = int(getattr(config, 'STAT_FILL_TIMEOUT_SECONDS', 60))

            # 有効戦略のうち未実装のものは除外
            unsupported = [s for s in self.enabled_strategies if s not in self.STRATEGY_PARAMS]
            if unsupported:
                self.log.warning(f'未実装の戦略のためスキップします: {unsupported}')
                self.enabled_strategies = [s for s in self.enabled_strategies if s in self.STRATEGY_PARAMS]

            if not self.enabled_strategies:
                self.log.error('有効な戦略が設定されていません')
                return False, '有効な戦略が設定されていません'

            self.log.info(f'有効戦略: {self.enabled_strategies} / BB幅下限比: {self.bb_width_filter} / 注文オフセット: {self.order_line}pips / 約定待機: {self.fill_timeout_seconds}秒')
            return True, None
        except Exception as e:
            self.error_output('統計デイトレパラメータ読み込みでエラー', e, traceback.format_exc())
            return False, str(e)

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

    # ---------------- 状態ログ ----------------

    def log_indicator_status(self, indicators, now):
        '''
        計算した指標値と、各エントリー/エグジット条件の充足状況をログ出力する
        self.log.info は標準出力(ターミナル) + ログファイル両方へ出るため共通呼び出し

        Args:
            indicators(dict): calc_realtime_indicators の戻り値
            now(datetime)
        '''
        def fmt(v, digits=2):
            if v is None:
                return 'N/A'
            return f'{v:.{digits}f}'

        close = indicators.get('close')
        rsi = indicators.get('rsi9')
        rci = indicators.get('rci26')
        bb_w = indicators.get('bb_width')
        bb_u2 = indicators.get('bb_upper_2')
        bb_l2 = indicators.get('bb_lower_2')
        bb_u3 = indicators.get('bb_upper_3')
        bb_l3 = indicators.get('bb_lower_3')
        bb_ratio = (bb_w / close) if (bb_w is not None and close) else None

        self.log.info(
            f'[指標] close={fmt(close)} rsi9={fmt(rsi)} rci26={fmt(rci)} '
            f'bb_width={fmt(bb_w)}({fmt((bb_ratio or 0) * 100, 3)}% / 下限{self.bb_width_filter*100:.2f}%) '
            f'BB[u3={fmt(bb_u3)} u2={fmt(bb_u2)} l2={fmt(bb_l2)} l3={fmt(bb_l3)}]'
        )

        if self.position is None:
            # ---- エントリー条件の充足状況 ----
            mark = lambda b: '○' if b else '✕'
            common_ok = self.check_common_filter(indicators)
            cb = not self.circuit_break_all

            lines = [
                f'CB全停止={mark(cb)}',
                f'BB幅フィルタ={mark(common_ok)}({fmt((bb_ratio or 0) * 100, 3)}% >= {self.bb_width_filter*100:.2f}%)',
            ]

            for sid in self.enabled_strategies:
                params = self.STRATEGY_PARAMS[sid]
                disabled = sid in self.disabled_strategies
                in_window = self.is_entry_window(now, params['hold_minutes'])

                if sid == 'B':
                    rsi_ok = (rsi is not None and rsi < params['rsi_threshold'])
                    overall = cb and common_ok and (not disabled) and in_window and rsi_ok
                    lines.append(
                        f'戦略B[時間帯={mark(in_window)} 停止={mark(not disabled)} '
                        f'RSI<{params["rsi_threshold"]}={mark(rsi_ok)}(rsi={fmt(rsi)})] => {mark(overall)}'
                    )

            self.log.info('[エントリー判定] ' + ' / '.join(lines))
        else:
            # ---- エグジット条件の充足状況 ----
            pos = self.position
            sid = pos['strategy']
            params = self.STRATEGY_PARAMS[sid]
            entry_price = pos['entry_price']
            pnl_ratio = (close - entry_price) / entry_price if (close is not None and entry_price) else 0.0
            held_min = (now - pos['entry_time']).total_seconds() / 60.0
            rsi_peak = pos.get('rsi_peak', 0)
            mark = lambda b: '○' if b else '✕'

            sl4 = (bb_l3 is not None and close is not None and close < bb_l3)
            sl_loss = (pnl_ratio <= params['sl_loss_pct'])
            sl6 = (held_min >= params['hold_minutes'] * 1.5)
            tp1 = (bb_u2 is not None and close is not None and close >= bb_u2)
            tp2 = (rsi is not None and rci is not None and rsi >= 80 and rci >= 80)
            tp4 = (held_min >= params['hold_minutes'] / 2 and pnl_ratio >= 0.001)
            ms1 = (rsi_peak >= 80 and rsi is not None and rsi < 50)
            time_stop = (held_min >= params['hold_minutes'])

            self.log.info(
                f'[ポジション] 戦略{sid} entry={fmt(entry_price)} '
                f'pnl={pnl_ratio*100:+.2f}% 保有={held_min:.1f}/{params["hold_minutes"]}分 '
                f'rsi_peak={fmt(rsi_peak)}'
            )
            self.log.info(
                f'[エグジット判定] '
                f'SL-4(close<BB下3σ)={mark(sl4)} / '
                f'SL含み損(<={params["sl_loss_pct"]*100:.1f}%)={mark(sl_loss)} / '
                f'SL-6(保有>={params["hold_minutes"]*1.5:.0f}分)={mark(sl6)} / '
                f'TP-1(close>=BB上2σ)={mark(tp1)} / '
                f'TP-2(RSI>=80&RCI>=80)={mark(tp2)} / '
                f'TP-4(半分時間+益>=0.1%)={mark(tp4)} / '
                f'MS-1(RSIピーク>=80→<50)={mark(ms1)} / '
                f'時間ストップ(>={params["hold_minutes"]}分)={mark(time_stop)}'
            )

    # ---------------- 約定確認 ----------------

    def confirm_fill(self, timeout_seconds=None, check_interval=5):
        '''
        エントリー注文の約定をポーリングで確認する
        タイムアウト時は未約定の信用デイトレ新規買注文をキャンセルする

        Args:
            timeout_seconds(int): 最大待機秒数。None ならインスタンス設定値を使用
            check_interval(int): ポーリング間隔(秒)

        Returns:
            filled(bool): 約定したか
            fill_price(float or None): 約定価格(API の Price フィールド)
        '''
        if timeout_seconds is None:
            timeout_seconds = self.fill_timeout_seconds

        start_time = self.util.culc_time.get_now()

        while True:
            # 信用デイトレ建玉の検出
            result, positions = self.get_today_position(symbol=str(self.stock_code), side='2')
            if result == True and positions:
                for pos in positions:
                    if pos.get('MarginTradeType') != 3:
                        continue
                    # 未決済数量が存在して0より大きければ約定済み
                    # HoldQty(拘束数量)は売り注文未発行時に欠落することがあるため判定に使わない
                    if pos.get('LeavesQty', 0) > 0:
                        try:
                            return True, float(pos.get('Price', 0))
                        except (TypeError, ValueError):
                            return True, None

            # タイムアウト判定
            elapsed = (self.util.culc_time.get_now() - start_time).total_seconds()
            if elapsed >= timeout_seconds:
                self.log.warning(f'エントリー注文未約定タイムアウト({timeout_seconds}秒) - 未約定注文をキャンセルします')
                self._cancel_open_buy_orders()
                return False, None

            time.sleep(check_interval)

    def _cancel_open_buy_orders(self):
        '''
        未約定の信用デイトレ新規買注文をキャンセルする(対象銘柄のみ)
        '''
        result, orders = self.get_today_order(symbol=str(self.stock_code))
        if result == False or not orders:
            return

        for order in orders:
            if order.get('MarginTradeType') != 3:
                continue
            if order.get('CashMargin') != 2:
                continue
            # SOR市場(手動注文)は操作不可
            if order.get('Exchange') == 9:
                continue
            # 既に約定/キャンセル済(State >= 5)はスキップ
            if order.get('State', 5) >= 5:
                continue
            self.log.info(f'未約定買注文キャンセル ID: {order.get("ID")}')
            try:
                self.api.order.cancel(order_id=order['ID'], password=self.trade_password)
            except Exception as e:
                self.log.error(f'未約定買注文キャンセルでエラー\n{e}\n{traceback.format_exc()}')
            time.sleep(0.3)

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
                # 09:00-09:30 は全戦略でエントリー禁止のため、寄り後30分まで一気に待機する
                if exch == 3:
                    self.log.info('寄り前のため 09:30(全戦略エントリー解禁時刻) まで待機')
                    self.util.culc_time.wait_time(hour=9, minute=30)
                    continue

                # 直近1分のクローズ(now の分の頭)時点までを使用する
                end_time = now.replace(second=0, microsecond=0) - timedelta(seconds=1)

                # 指標計算
                ok, indicators = self.calc_realtime_indicators(self.stock_code, end_time)
                if not ok:
                    self._sleep_until_next_minute()
                    continue

                # 指標値 + 条件充足状況をログ出力
                self.log_indicator_status(indicators, now)

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
                        # 注文基準価格は前分終値ではなく現在の最良買気配を使用する
                        # (close は判定用、注文用は board API のリアルタイム値が望ましい)
                        result, board_info = self.api.info.board(stock_code=self.stock_code,
                                                                  market_code=self.market_code)
                        if result == False:
                            self.log.error(f'板情報取得失敗のためエントリースキップ\n{board_info}')
                            self._sleep_until_next_minute()
                            continue

                        board_detail = self.board_analysis(board_info)
                        if board_detail is False:
                            self.log.error('板情報分析失敗のためエントリースキップ')
                            self._sleep_until_next_minute()
                            continue

                        entry_basis_price = board_detail['buy_price']
                        self.log.info(
                            f'エントリーシグナル: 戦略{sid} '
                            f'(rsi9={indicators.get("rsi9")}, close={indicators["close"]}, '
                            f'最良買気配={entry_basis_price})'
                        )

                        ok2, order_price = self.buy_order(stock_price=entry_basis_price)
                        if not ok2:
                            self.log.error('買い注文失敗')
                            self._sleep_until_next_minute()
                            continue

                        # 約定確認(タイムアウト時は注文キャンセル & ポジション設定スキップ)
                        filled, fill_price = self.confirm_fill()
                        if not filled:
                            self.log.warning('エントリー未約定のためポジション設定をスキップ')
                            self._sleep_until_next_minute()
                            continue

                        actual_entry_price = fill_price if (fill_price and fill_price > 0) else order_price
                        self.position = {
                            'strategy': sid,
                            'entry_price': actual_entry_price,
                            'entry_time': self.util.culc_time.get_now(),
                            'qty': self.stock_info['unit_num'],
                            'rsi_peak': indicators.get('rsi9') or 0,
                            'rci_at_entry': indicators.get('rci26'),
                        }
                        self.log.info(f'ポジション確定: 戦略{sid} エントリー価格={actual_entry_price}円')

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
