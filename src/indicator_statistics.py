# テクニカル指標の統計情報算出スクリプト
#
# 目的: #46で生成した四本値CSVを用いて、各テクニカル指標の統計情報を算出する
#
# 処理フロー:
#   ①保存済みCSVを取得する (本スクリプトで実装)
#     - csv/ohlc/bak/YYYYMMDD.7z を解凍し、csv/ohlc/YYYYMMDD/ のCSVを読み込む
#     - 作業前にcsv/ohlc/YYYYMMDD/が存在する場合はcsv/tmp/YYYYMMDD/に退避し、処理後に復元する
#   ②CSVから各テクニカル指標毎の統計情報を取る (未実装)
#
# 実行方法: src/ ディレクトリ内で実行
#   cd src && python analytics/indicator_statistics.py

import os
import re
import shutil
import traceback
import time
import numpy as np
import pandas as pd

from base import Base

# =========================================================
# パス設定
# =========================================================
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'csv')
OHLC_DIR = os.path.join(BASE_DIR, 'ohlc')
BAK_DIR = os.path.join(OHLC_DIR, 'bak')
TMP_DIR = os.path.join(BASE_DIR, 'tmp')
STATISTICS_DIR = os.path.join(BASE_DIR, 'statistics')

# =========================================================
# 統計用定数
# =========================================================
# 正解ラベルの対象Nバー
NBAR_LIST = [1, 3, 5, 10, 15, 30]

# MAクロスの (短期, 長期) 組み合わせ
MA_CROSS_PAIRS = [(5, 10), (5, 20), (5, 25), (10, 20), (10, 25), (20, 25)]

# MA単体のウィンドウ
MA_WINDOWS = [5, 10, 20, 25]

# 統計② バケット別精度統計 - 等幅分割設定 (col, lo, hi, n_buckets)
BUCKET_EVEN = [
    ('rsi_1min_9piece', 0, 100, 10),
    ('rsi_1min_14piece', 0, 100, 10),
    ('rci_1min_9piece', -100, 100, 10),
    ('rci_1min_26piece', -100, 100, 10),
    ('psy_1min_12piece', 0, 100, 10),
    ('bb_1min_20piece_position', 0, 1, 10),  # clip(0,1)前処理あり
]
# 統計② 四分位分割対象
BUCKET_QUARTILE = ['macd_1min_diff', 'bb_1min_20piece_width']

# 統計④ 閾値以上/以下統計 - 固定閾値
THRESHOLD_FIXED = {
    'rsi_1min_9piece': [10, 20, 30, 40, 50, 60, 70, 80, 90],
    'rsi_1min_14piece': [10, 20, 30, 40, 50, 60, 70, 80, 90],
    'rci_1min_9piece': [-80, -60, -40, -20, 0, 20, 40, 60, 80],
    'rci_1min_26piece': [-80, -60, -40, -20, 0, 20, 40, 60, 80],
    'psy_1min_12piece': [10, 20, 30, 40, 50, 60, 70, 80, 90],
    'bb_1min_20piece_position': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
}
# 統計④ 0基準(正/負)で判定する列
THRESHOLD_ZERO_COLS_BASE = [
    'ichimoku_1min_bc_diff',
    'ichimoku_1min_cloud_high_diff',
    'ichimoku_1min_cloud_low_diff',
]

# 統計⑥ 価格とMAの位置関係の対象カラム
STAT6_MA_COLS_BASE = [f'{t}_1min_{w}piece' for t in ['sma', 'ema', 'wma'] for w in MA_WINDOWS]
STAT6_MA_COLS_BASE += ['ichimoku_1min_base_line', 'ichimoku_1min_conversion_line']

# 価格スケール指標(close_priceで除して相対化する対象)
# 円スケールでボラ大の銘柄に閾値を引きずられないように、蓄積時点で相対値(乖離率)へ変換する
_PRICE_SCALE_COLS_LIST = [
    'macd_1min_diff', 'bb_1min_20piece_width',
    'ichimoku_1min_bc_diff', 'ichimoku_1min_cloud_high_diff', 'ichimoku_1min_cloud_low_diff',
]
for _t in ['sma', 'ema', 'wma']:
    for _s, _l in MA_CROSS_PAIRS:
        _PRICE_SCALE_COLS_LIST.append(f'{_t}_1min_{_s}to{_l}piece_diff')
PRICE_SCALE_COLS = set(_PRICE_SCALE_COLS_LIST)

# 出力スコープ定義
SCOPE_ALL = 'all'
SCOPE_BY_STOCK = 'by_stock'
SCOPE_BY_DATE = 'by_date'
SCOPES = [SCOPE_ALL, SCOPE_BY_STOCK, SCOPE_BY_DATE]

# 出力カラム
STAT_COMMON_COLUMNS = [
    'sample_count', 'rise_count', 'flat_count', 'fall_count',
    'rise_rate', 'fall_rate',
    'amount_mean', 'amount_std', 'amount_median',
    'rate_mean', 'rate_std',
]
STAT1_COLUMNS = ['signal_col', 'signal_type', 'nbar'] + STAT_COMMON_COLUMNS
STAT2_COLUMNS = ['oscillator_col', 'bucket_label', 'bucket_left', 'bucket_right', 'nbar'] + STAT_COMMON_COLUMNS
STAT3_COLUMNS = ['after_col', 'cross_type', 'bars_elapsed', 'nbar'] + STAT_COMMON_COLUMNS
STAT4_COLUMNS = ['indicator_col', 'threshold', 'direction', 'nbar'] + STAT_COMMON_COLUMNS
STAT5_COLUMNS = ['condition_name', 'nbar'] + STAT_COMMON_COLUMNS
STAT6_COLUMNS = ['ma_col', 'position', 'nbar'] + STAT_COMMON_COLUMNS

# スコープ別の先頭カラム
SCOPE_PREFIX_COLUMNS = {
    SCOPE_ALL: [],
    SCOPE_BY_STOCK: ['stock_code'],
    SCOPE_BY_DATE: ['date'],
}

class IndicatorStatistics(Base):
    '''テクニカル指標の統計情報算出クラス'''

    def __init__(self):
        super().__init__(use_db=False, use_api=False)
        self.csv_dict = []
        # 統計情報を格納する辞書（統計算出実装時に追記）
        # キー: "YYYYMMDD_STOCKCODE_N"（csv_dictの要素と同形式）、値: 統計情報
        self.statistics_data = {}

        # 統計用データアキュムレータ（CSV1件ずつ処理する際に生データを蓄積）
        # キーに stock_code と date を含めることで、_save_statistics 時点で
        # 全体／銘柄別／日付別の3スコープに group-by 集計可能とする
        # 構造: dict[group_key] = {'flag': [...], 'amount': [...], 'rate': [...]}
        # 価格スケール指標(PRICE_SCALE_COLS)は蓄積時に value/close_price で相対化済み
        self.stat1_data = {}  # key=(signal_col, signal_type, nbar, stock_code, date)
        self.stat2_raw = {}   # key=(oscillator_col, nbar, stock_code, date) -> value込み
        self.stat3_data = {}  # key=(after_col, cross_type, bars_elapsed, nbar, stock_code, date)
        self.stat4_raw = {}   # key=(indicator_col, nbar, stock_code, date) -> value込み
        self.stat5_data = {}  # key=(condition_name, nbar, stock_code, date)
        self.stat6_data = {}  # key=(ma_col, position, nbar, stock_code, date)

        # NaN埋め用の銘柄・日付集合(処理対象として現れたものを記録)
        self.all_stocks = set()
        self.all_dates = set()

    def get_target_dates(self):
        '''
        csv/ohlc/bak/ 内の7zファイルを走査し、処理対象の日付リストを返す

        Returns:
            list[str]: 日付文字列(YYYYMMDD)のリスト（昇順ソート済み）
        '''
        if not os.path.exists(BAK_DIR):
            return []

        dates = []
        for filename in os.listdir(BAK_DIR):
            if re.fullmatch(r'\d{8}\.7z', filename):
                dates.append(filename.replace('.7z', ''))

        return sorted(dates)

    def collect_ohlc_csv(self, date):
        '''
        指定日付の四本値CSVファイル名を収集して返す

        処理フロー:
          1. csv/ohlc/YYYYMMDD/ が存在する場合 → csv/tmp/YYYYMMDD/ に退避
          2. csv/ohlc/bak/YYYYMMDD.7z を csv/ohlc/YYYYMMDD/ に解凍
          3. YYYYMMDD_*_*min.csv のファイルパスのみを収集（CSVの読み込みは行わない）
          ※ 解凍ディレクトリの削除・退避の復元は呼び出し元が行う
          ※ エラー発生時は退避を復元してから終了する

        Args:
            date(str): 処理対象の日付 (YYYYMMDD形式)

        Returns:
            bool: 実行結果
            bool: 退避フラグ（True=退避済み）
                  失敗時は退避の復元が完了しているためFalse
        '''
        ohlc_date_dir = os.path.join(OHLC_DIR, date)
        tmp_date_dir = os.path.join(TMP_DIR, date)
        archive_path = os.path.join(BAK_DIR, f'{date}.7z')

        # 退避フラグ
        evacuated = False

        try:
            # csv/ohlc/YYYYMMDD/ が存在する場合は一時退避
            if os.path.exists(ohlc_date_dir):
                self.log.info(f'{date}: csv/ohlc/{date}/ が存在するため csv/tmp/{date}/ に退避します')
                os.makedirs(TMP_DIR, exist_ok=True)
                shutil.move(ohlc_date_dir, tmp_date_dir)
                evacuated = True

            # 7zファイルの存在チェック
            if not os.path.exists(archive_path):
                self.log.error(f'{date}: csv/ohlc/bak/{date}.7z が見つかりません')
                self._restore_evacuated(date, ohlc_date_dir, tmp_date_dir)
                return False, False

            # 7zファイルを一括で解凍
            self.log.info(f'{date}: csv/ohlc/bak/{date}.7z を解凍します')
            result, _ = self.util.file_manager.extract_7z_file(archive_path, ohlc_date_dir)
            if not result:
                self.log.error(f'{date}: 解凍に失敗しました')
                self._cleanup_extracted(date, ohlc_date_dir)
                self._restore_evacuated(date, ohlc_date_dir, tmp_date_dir)
                return False, False

            # 解凍後のCSVファイルパスを収集（読み込みは行わない）
            self.log.info(f'{date}: CSVファイル名を収集します')

            # 日付ディレクトリ内のファイルを走査
            for filename in os.listdir(ohlc_date_dir):
                # YYYYMMDD_STOCKCODE_Nmin.csv 形式のファイルのみ対象
                if not re.fullmatch(r'\d{8}_\d{4}_\d{1,2}min\.csv', filename):
                    continue

                # ファイル名: 20260406_1570_1min.csv → 20260406_1570_1 で配列に保持
                self.csv_dict.append(filename.replace('min.csv', ''))

            self.log.info(f'{date}: {len(self.csv_dict)}件のCSVファイルを収集しました')
            return True, evacuated

        except Exception as e:
            self.log.error(f'{date}: 予期しないエラーが発生しました\n{e}\n{traceback.format_exc()}')
            self._cleanup_extracted(date, ohlc_date_dir)
            self._restore_evacuated(date, ohlc_date_dir, tmp_date_dir)
            return False, False

    def calc_indicators(self):
        '''
        self.csv_dict に格納されたCSVファイル名から1件ずつデータを読み込み、
        テクニカル指標の計算・統計情報の取得を行う。
        メモリ使用量を抑えるため、1件分の処理が完了したら都度DataFrameを破棄して次へ進む。

        処理フロー（1件ごと）:
          1. CSVを読み込む
          2. テクニカル指標を計算する
          3. 統計情報を取得する（未実装）
          4. DataFrameを破棄して次のCSVへ

        self.csv_dict の要素形式: "YYYYMMDD_STOCKCODE_N"
        （例: "20260406_1570_1" → csv/ohlc/20260406/20260406_1570_1min.csv）

        Returns:
            bool: 実行結果（1件以上成功した場合True）
        '''
        success_count = 0

        for csv_name in self.csv_dict:
            # ファイルパスを復元: "YYYYMMDD_STOCKCODE_N" → csv/ohlc/YYYYMMDD/YYYYMMDD_STOCKCODE_Nmin.csv
            parts = csv_name.split('_')
            date = parts[0]
            stock_code = parts[1]
            csv_file_name = f'{csv_name}min.csv'
            csv_path = os.path.join(OHLC_DIR, date, csv_file_name)
            # 銘柄・日付を記録(NaN埋め用)
            self.all_stocks.add(stock_code)
            self.all_dates.add(date)

            # CSVを読み込む
            self.log.info(f'{csv_file_name}を読み込みます')
            try:
                df = pd.read_csv(csv_path)
                df['trade_time'] = pd.to_datetime(df['trade_time'])
            except Exception as e:
                self.log.error(f'{csv_name}: CSVの読み込みでエラー\n{e}\n{traceback.format_exc()}')
                continue

            # テクニカル指標を計算する
            result, df = self._apply_indicators(df)
            if not result:
                self.log.error('テクニカル指標の計算でエラーが発生したためスキップします')
                del df
                continue

            self.log.info(f'テクニカル指標計算完了 行数={len(df)} カラム数={len(df.columns)}')

            # 株価の変動を表すカラム(正解ラベル)を追加する
            result, df = self._add_price_change_labels(df)
            if not result:
                self.log.error('価格変動カラムの追加でエラーが発生したためスキップします')
                del df
                continue

            self.log.info(f'価格変動カラム追加完了 カラム数={len(df.columns)}')

            ################## テスト用ここまで ##################
            # 計算したテクニカル指標を含めた状態でCSVへ出力する 例) csv/indicator/20260406_1570_1min_with_indicators.csv
            output_dir = os.path.join(BASE_DIR, 'indicator')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'{csv_name}min_with_indicators.csv')
            try:
                df.to_csv(output_path, index=False)
                self.log.info(f'{csv_name}: テクニカル指標を含むCSVを出力しました → {output_path}')
            except Exception as e:
                self.log.error(f'{csv_name}: テクニカル指標を含むCSVの出力でエラー\n{e}\n{traceback.format_exc()}')
                # 出力に失敗しても統計情報の取得は行うため、ここではスキップせずに続行する
            ################### テスト用ここまで ##################


            # 統計情報を取得する（生データを蓄積）
            result = self._get_statistics(df, csv_name, stock_code, date)
            if not result:
                self.log.error(f'{csv_name}: 統計情報の蓄積でエラーが発生しました')

            # DataFrameを破棄して次のCSVへ
            del df
            success_count += 1

        self.log.info(f'テクニカル指標計算完了 成功={success_count}/{len(self.csv_dict)}件')
        return success_count > 0

    def _apply_indicators(self, df):
        '''
        各テクニカル指標を計算してDataFrameに追加する
        ※CSVは既にリサンプリング済みのため、全指標を interval=1 で計算する

        計算する指標:
          - SMA (単純移動平均線)     : 5・10・20・25本
          - EMA (指数移動平均線)     : 5・10・20・25本
          - WMA (加重移動平均線)     : 5・10・20・25本
          - MAクロス                 : SMA/EMA/WMA のゴールデン・デッドクロス
          - ボリンジャーバンド        : 20本
          - RSI (相対力指数)         : 9・14本
          - RCI (順位相関指数)       : 9・26本
          - MACD                    : 短期12・長期26・シグナル9本
          - サイコロジカルライン      : 12本
          - パラボリック(終値)        : AF初期0.02・最大0.2
          - パラボリック(三本値)      : AF初期0.02・最大0.2
          - 一目均衡表               : 転換線9・基準線26本
          - 変動価格                 : 1本後・3本後・5本後

        Args:
            df(pandas.DataFrame): OHLCデータ
                                  (close_price, high_price, low_price カラムを含む)

        Returns:
            bool: 実行結果
            pandas.DataFrame: テクニカル指標を追加したDataFrame。失敗時はNone
        '''
        indicator = self.util.indicator
        close_col = 'close_price'
        high_col  = 'high_price'
        low_col   = 'low_price'

        # SMA (単純移動平均線): 5・10・20・25本
        for window in [5, 10, 20, 25]:
            result, df = indicator.get_sma(df, f'sma_1min_{window}piece', window, 1, close_col)
            if not result:
                return False, None

        # EMA (指数移動平均線): 5・10・20・25本
        for window in [5, 10, 20, 25]:
            result, df = indicator.get_ema(df, f'ema_1min_{window}piece', window, 1, close_col)
            if not result:
                return False, None

        # WMA (加重移動平均線): 5・10・20・25本
        for window in [5, 10, 20, 25]:
            result, df = indicator.get_wma(df, f'wma_1min_{window}piece', window, 1, close_col)
            if not result:
                return False, None

        # MAクロス (SMA・EMA・WMAが計算済みであることが前提)
        # MA列が存在しない場合は空DataFrameが返るため、その場合はスキップ
        result, df_cross = indicator.get_ma_cross(df, 1)
        if not result:
            return False, None
        if not df_cross.empty:
            df = df_cross

        # ボリンジャーバンド: 20本
        result, df = indicator.get_bollinger_bands(df, 'bb_1min_20piece', 20, 1, close_col)
        if not result:
            return False, None

        # RSI (相対力指数): 9・14本
        for window in [9, 14]:
            result, df = indicator.get_rsi(df, f'rsi_1min_{window}piece', window, 1, close_col)
            if not result:
                return False, None

        # RCI (順位相関指数): 9・26本
        for window in [9, 26]:
            result, df = indicator.get_rci(df, f'rci_1min_{window}piece', window, 1, close_col)
            if not result:
                return False, None

        # MACD: 短期12・長期26・シグナル9本
        result, df = indicator.get_macd(df, 'macd_1min', 12, 26, 9, 1, close_col)
        if not result:
            return False, None

        # サイコロジカルライン: 12本
        result, df = indicator.get_psy(df, 'psy_1min_12piece', 12, 1, close_col)
        if not result:
            return False, None

        # パラボリック (終値ベース): AF初期値0.02・最大値0.2
        result, df = indicator.get_parabolic(df, 'sar_1min', 0.02, 0.2, 1, close_col)
        if not result:
            return False, None

        # パラボリック (三本値ベース): AF初期値0.02・最大値0.2
        result, df = indicator.get_parabolic_hlc(df, 'sar_hlc_1min', 0.02, 0.2, 1, high_col, low_col, close_col)
        if not result:
            return False, None

        # 一目均衡表: 転換線9本・基準線26本
        result, df = indicator.get_ichimoku_cloud(df, 'ichimoku_1min', 9, 26, 1, close_col, high_col, low_col)
        if not result:
            return False, None

        # 変動価格: 1本後・3本後・5本後
        for bars in [1, 3, 5]:
            result, df = indicator.get_change_price(df, f'change_{bars}bar', bars, close_col)
            if not result:
                return False, None

        return True, df

    def _add_price_change_labels(self, df):
        '''
        株価の変動を表すカラムをDataFrameに追加する。
        現在の行から X行後の終値と比較して、上昇フラグ・変動額・変動率を計算する。

        比較対象行: 1, 3, 5, 10, 15, 30, 60, 120行後
        X行後のデータが存在しない場合はそのカラムの値は NaN となる。

        追加するカラム:
          - price_change_flag_Nbar_after   : 上昇フラグ（1:上昇、0:変化なし、-1:下落、NaN:データ不足）
          - price_change_amount_Nbar_after : 株価変動額
          - price_change_rate_Nbar_after   : 株価変動率（小数点以下5桁に四捨五入）

        Args:
            df(pd.DataFrame): テクニカル指標計算済みのDataFrame

        Returns:
            bool: 実行結果
            pd.DataFrame: 価格変動カラムを追加したDataFrame。失敗時は(False, None)
        '''
        try:
            close_col = 'close_price'
            # 比較対象行
            bars_list = [1, 3, 5, 10, 15, 30, 60, 120]

            for bars in bars_list:
                # X行後の終値を取得
                future_close = df[close_col].shift(-bars)

                # 上昇フラグ (1:上昇、0:変化なし、-1:下落)
                flag_col = f'price_change_flag_{bars}bar_after'
                change = future_close - df[close_col]
                df[flag_col] = change.apply(
                    lambda x: None if pd.isna(x) else (1 if x > 0 else (0 if x == 0 else -1))
                )

                # 株価変動額
                amount_col = f'price_change_amount_{bars}bar_after'
                df[amount_col] = change

                # 株価変動率（小数点以下5桁に四捨五入）
                rate_col = f'price_change_rate_{bars}bar_after'
                df[rate_col] = (change / df[close_col]).round(5)

            return True, df

        except Exception as e:
            self.log.error(f'価格変動カラムの追加でエラー\n{e}\n{traceback.format_exc()}')
            return False, None

    # =========================================================
    # 統計情報の算出
    # =========================================================
    def _get_statistics(self, df, csv_name, stock_code, date):
        '''
        DataFrame1件分から各統計用の生データを蓄積する。
        集計は全CSV処理完了後に _save_statistics() で行う。

        統計の内容:
          ① シグナル精度統計 (クロス・逆転シグナル発火時の上昇/下落精度)
          ② バケット別精度統計 (オシレーター値を等幅/四分位で分割)
          ③ クロス後経過本数別精度統計 (クロスから経過したバー数ごと)
          ④ 閾値以上/以下統計 (連続値指標の閾値ベース)
          ⑤ BBσ位置別統計 (価格がバンドの何σを超えているか)
          ⑥ 価格と移動平均の位置関係統計

        Args:
            df(pd.DataFrame): テクニカル指標+正解ラベル付与済みDataFrame
            csv_name(str): ログ用のCSV識別名
            stock_code(str): 銘柄コード
            date(str): 日付(YYYYMMDD)

        Returns:
            bool: 実行結果
        '''
        try:
            # 事前にnbarごとの正解ラベルSeriesを取得
            flags = {}
            amounts = {}
            rates = {}
            for n in NBAR_LIST:
                flag_col = f'price_change_flag_{n}bar_after'
                amount_col = f'price_change_amount_{n}bar_after'
                rate_col = f'price_change_rate_{n}bar_after'
                if flag_col not in df.columns or amount_col not in df.columns or rate_col not in df.columns:
                    self.log.error(f'{csv_name}: 正解ラベルカラム {flag_col}/{amount_col}/{rate_col} が存在しません')
                    return False
                flags[n] = df[flag_col]
                amounts[n] = df[amount_col]
                rates[n] = df[rate_col]

            # 各統計収集の実行時間を計測
            time_start = time.perf_counter()
            collect_times = {}

            t1 = time.perf_counter()
            self._collect_stat1(df, flags, amounts, rates, stock_code, date)
            collect_times['stat1'] = time.perf_counter() - t1

            t2 = time.perf_counter()
            self._collect_stat2(df, flags, amounts, rates, stock_code, date)
            collect_times['stat2'] = time.perf_counter() - t2

            t3 = time.perf_counter()
            self._collect_stat3(df, flags, amounts, rates, stock_code, date)
            collect_times['stat3'] = time.perf_counter() - t3

            t4 = time.perf_counter()
            self._collect_stat4(df, flags, amounts, rates, stock_code, date)
            collect_times['stat4'] = time.perf_counter() - t4

            t5 = time.perf_counter()
            self._collect_stat5(df, flags, amounts, rates, stock_code, date)
            collect_times['stat5'] = time.perf_counter() - t5

            t6 = time.perf_counter()
            self._collect_stat6(df, flags, amounts, rates, stock_code, date)
            collect_times['stat6'] = time.perf_counter() - t6

            total_time = time.perf_counter() - time_start

            # 実行時間をログ出力
            self.log.info(f'{csv_name}: 統計蓄積完了 (合計 {total_time:.3f}秒)')
            self.log.info(f'  stat①: {collect_times["stat1"]:.3f}秒')
            self.log.info(f'  stat②: {collect_times["stat2"]:.3f}秒')
            self.log.info(f'  stat③: {collect_times["stat3"]:.3f}秒')
            self.log.info(f'  stat④: {collect_times["stat4"]:.3f}秒')
            self.log.info(f'  stat⑤: {collect_times["stat5"]:.3f}秒')
            self.log.info(f'  stat⑥: {collect_times["stat6"]:.3f}秒')

            return True
        except Exception as e:
            self.log.error(f'{csv_name}: 統計情報の蓄積でエラー\n{e}\n{traceback.format_exc()}')
            return False

    def _append_triplets(self, bucket, flag_ser, amount_ser, rate_ser):
        '''flag/amount/rateの3系列をbucketに追加する (NaN行は除外)'''
        mask = flag_ser.notna() & amount_ser.notna() & rate_ser.notna()
        if not mask.any():
            return
        bucket['flag'].extend(flag_ser[mask].astype(float).astype(int).tolist())
        bucket['amount'].extend(amount_ser[mask].astype(float).tolist())
        bucket['rate'].extend(rate_ser[mask].astype(float).tolist())

    def _append_quartets(self, bucket, value_ser, flag_ser, amount_ser, rate_ser):
        '''value込みで4系列をbucketに追加する (NaN行は除外)'''
        mask = value_ser.notna() & flag_ser.notna() & amount_ser.notna() & rate_ser.notna()
        if not mask.any():
            return
        bucket['value'].extend(value_ser[mask].astype(float).tolist())
        bucket['flag'].extend(flag_ser[mask].astype(float).astype(int).tolist())
        bucket['amount'].extend(amount_ser[mask].astype(float).tolist())
        bucket['rate'].extend(rate_ser[mask].astype(float).tolist())

    # ---------- ① シグナル精度 ----------
    def _collect_stat1(self, df, flags, amounts, rates, stock_code, date):
        '''統計①: クロス・逆転シグナル発火時の生データを蓄積'''
        signals = []  # list of (signal_col, signal_type, mask)

        # SMA/EMA/WMA クロス
        for t in ['sma', 'ema', 'wma']:
            for s, l in MA_CROSS_PAIRS:
                gc_col = f'{t}_1min_{s}to{l}piece_golden_cross'
                dc_col = f'{t}_1min_{s}to{l}piece_dead_cross'
                if gc_col in df.columns:
                    signals.append((gc_col, 'golden_cross', (df[gc_col] == 1).fillna(False)))
                if dc_col in df.columns:
                    signals.append((dc_col, 'dead_cross', (df[dc_col] == 1).fillna(False)))

        # MACD
        if 'macd_1min_cross' in df.columns:
            signals.append(('macd_1min_cross', 'golden_cross', (df['macd_1min_cross'] == 1).fillna(False)))
            signals.append(('macd_1min_cross', 'dead_cross', (df['macd_1min_cross'] == -1).fillna(False)))

        # SAR (逆転フラグ: GC相当のみ集計)
        for col in ['sar_1min_reverse_flag', 'sar_hlc_1min_reverse_flag']:
            if col in df.columns:
                signals.append((col, 'reverse', (df[col] == 1).fillna(False)))

        # 一目均衡表 bc/ls (値が1:GC, -1:DC)
        for key in ['bc', 'ls']:
            col = f'ichimoku_1min_{key}_cross'
            if col in df.columns:
                signals.append((col, 'golden_cross', (df[col] == 1).fillna(False)))
                signals.append((col, 'dead_cross', (df[col] == -1).fillna(False)))

        # 一目均衡表 cloud_cross (設計書: GC==1, DC==2)
        if 'ichimoku_1min_cloud_cross' in df.columns:
            signals.append(('ichimoku_1min_cloud_cross', 'golden_cross', (df['ichimoku_1min_cloud_cross'] == 1).fillna(False)))
            signals.append(('ichimoku_1min_cloud_cross', 'dead_cross', (df['ichimoku_1min_cloud_cross'] == 2).fillna(False)))

        # 各シグナル・各nbarについて生データを蓄積
        for col, stype, mask in signals:
            mask_arr = mask.astype(bool).values
            for nbar in NBAR_LIST:
                key = (col, stype, nbar, stock_code, date)
                bucket = self.stat1_data.setdefault(key, {'flag': [], 'amount': [], 'rate': []})
                self._append_triplets(bucket, flags[nbar][mask_arr], amounts[nbar][mask_arr], rates[nbar][mask_arr])

    # ---------- ② バケット別精度 ----------
    def _collect_stat2(self, df, flags, amounts, rates, stock_code, date):
        '''統計②: オシレーター値と正解ラベルの組を蓄積。分割は _save_statistics で行う
        価格スケール指標(PRICE_SCALE_COLS)はここで close_price で除して相対化する'''
        cols = [c for (c, _, _, _) in BUCKET_EVEN] + BUCKET_QUARTILE
        for col in cols:
            if col not in df.columns:
                continue
            value_ser = self._relativize_if_needed(df, col)
            if value_ser is None:
                continue
            for nbar in NBAR_LIST:
                key = (col, nbar, stock_code, date)
                bucket = self.stat2_raw.setdefault(key, {'value': [], 'flag': [], 'amount': [], 'rate': []})
                self._append_quartets(bucket, value_ser, flags[nbar], amounts[nbar], rates[nbar])

    def _relativize_if_needed(self, df, col):
        '''
        価格スケール指標(PRICE_SCALE_COLS)に該当する場合、value/close_price で相対化したSeriesを返す。
        対象外の場合はそのままのSeriesを返す。

        close_price が 0 / NaN の行は NaN とすることで、後段の NaN除外マスクで除外される。
        '''
        if col not in PRICE_SCALE_COLS:
            return df[col]
        if 'close_price' not in df.columns:
            return df[col]
        close = df['close_price']
        # close_price が 0 や NaN の行は NaN にする(0除算回避)
        safe_close = close.where((close != 0) & close.notna())
        return df[col] / safe_close

    # ---------- ③ クロス後経過本数別 ----------
    def _collect_stat3(self, df, flags, amounts, rates, stock_code, date):
        '''統計③: 各_afterカラムのバーカウント値ごとに生データを蓄積'''
        after_cols = []  # list of (col, cross_type)

        # SMA/EMA/WMA _after
        for t in ['sma', 'ema', 'wma']:
            for s, l in MA_CROSS_PAIRS:
                after_cols.append((f'{t}_1min_{s}to{l}piece_golden_cross_after', 'golden_cross'))
                after_cols.append((f'{t}_1min_{s}to{l}piece_dead_cross_after', 'dead_cross'))

        # 一目 bc/ls
        for k in ['bc', 'ls']:
            after_cols.append((f'ichimoku_1min_{k}_gc_after', 'golden_cross'))
            after_cols.append((f'ichimoku_1min_{k}_dc_after', 'dead_cross'))

        # 一目 雲ブレイクアウト/エントリー
        after_cols.append(('ichimoku_1min_cloud_breakout_up_after', 'golden_cross'))
        after_cols.append(('ichimoku_1min_cloud_breakout_down_after', 'dead_cross'))
        after_cols.append(('ichimoku_1min_cloud_entry_up_after', 'golden_cross'))
        after_cols.append(('ichimoku_1min_cloud_entry_down_after', 'dead_cross'))

        for col, ctype in after_cols:
            if col not in df.columns:
                continue
            vals_notna = df[col].dropna()
            if len(vals_notna) == 0:
                continue
            # floatが混ざる可能性があるのでintに丸める
            unique_vals = sorted({int(v) for v in vals_notna.unique()})
            for val in unique_vals:
                mask = (df[col] == val).fillna(False).values
                for nbar in NBAR_LIST:
                    key = (col, ctype, val, nbar, stock_code, date)
                    bucket = self.stat3_data.setdefault(key, {'flag': [], 'amount': [], 'rate': []})
                    self._append_triplets(bucket, flags[nbar][mask], amounts[nbar][mask], rates[nbar][mask])

    # ---------- ④ 閾値以上/以下 ----------
    def _collect_stat4(self, df, flags, amounts, rates, stock_code, date):
        '''統計④: 指標値と正解ラベルの組を蓄積。閾値判定は _save_statistics で行う
        価格スケール指標(PRICE_SCALE_COLS)はここで close_price で除して相対化する'''
        cols = list(THRESHOLD_FIXED.keys()) + ['macd_1min_diff', 'bb_1min_20piece_width']
        # MA diff 列（SMA/EMA/WMA × 6ペア）
        for t in ['sma', 'ema', 'wma']:
            for s, l in MA_CROSS_PAIRS:
                cols.append(f'{t}_1min_{s}to{l}piece_diff')
        # 一目 diff 列
        cols.extend(THRESHOLD_ZERO_COLS_BASE)

        # 重複削除（順序は保持）
        seen = set()
        uniq_cols = []
        for c in cols:
            if c not in seen:
                seen.add(c)
                uniq_cols.append(c)

        for col in uniq_cols:
            if col not in df.columns:
                continue
            value_ser = self._relativize_if_needed(df, col)
            if value_ser is None:
                continue
            for nbar in NBAR_LIST:
                key = (col, nbar, stock_code, date)
                bucket = self.stat4_raw.setdefault(key, {'value': [], 'flag': [], 'amount': [], 'rate': []})
                self._append_quartets(bucket, value_ser, flags[nbar], amounts[nbar], rates[nbar])

    # ---------- ⑤ BBσ位置 ----------
    def _collect_stat5(self, df, flags, amounts, rates, stock_code, date):
        '''統計⑤: close_price と BBの上下限の直接比較結果ごとに生データを蓄積'''
        required = [
            'close_price',
            'bb_1min_20piece_upper_1sigma', 'bb_1min_20piece_upper_2sigma', 'bb_1min_20piece_upper_3sigma',
            'bb_1min_20piece_lower_1sigma', 'bb_1min_20piece_lower_2sigma', 'bb_1min_20piece_lower_3sigma',
        ]
        if not all(c in df.columns for c in required):
            return

        close = df['close_price']
        u1 = df['bb_1min_20piece_upper_1sigma']
        u2 = df['bb_1min_20piece_upper_2sigma']
        u3 = df['bb_1min_20piece_upper_3sigma']
        l1 = df['bb_1min_20piece_lower_1sigma']
        l2 = df['bb_1min_20piece_lower_2sigma']
        l3 = df['bb_1min_20piece_lower_3sigma']

        conditions = [
            ('1sigma_above', (close > u1).fillna(False)),
            ('2sigma_above', (close > u2).fillna(False)),
            ('3sigma_above', (close > u3).fillna(False)),
            ('1sigma_below', (close < l1).fillna(False)),
            ('2sigma_below', (close < l2).fillna(False)),
            ('3sigma_below', (close < l3).fillna(False)),
            ('within_1sigma', ((close >= l1) & (close <= u1)).fillna(False)),
        ]
        for name, mask in conditions:
            mask_arr = mask.astype(bool).values
            for nbar in NBAR_LIST:
                key = (name, nbar, stock_code, date)
                bucket = self.stat5_data.setdefault(key, {'flag': [], 'amount': [], 'rate': []})
                self._append_triplets(bucket, flags[nbar][mask_arr], amounts[nbar][mask_arr], rates[nbar][mask_arr])

    # ---------- ⑥ 価格とMAの位置関係 ----------
    def _collect_stat6(self, df, flags, amounts, rates, stock_code, date):
        '''統計⑥: close_price と MA値の直接比較結果ごとに生データを蓄積'''
        if 'close_price' not in df.columns:
            return

        close = df['close_price']
        for col in STAT6_MA_COLS_BASE:
            if col not in df.columns:
                continue
            above_mask = (close > df[col]).fillna(False).values
            below_mask = (close < df[col]).fillna(False).values
            for position, mask in [('above', above_mask), ('below', below_mask)]:
                for nbar in NBAR_LIST:
                    key = (col, position, nbar, stock_code, date)
                    bucket = self.stat6_data.setdefault(key, {'flag': [], 'amount': [], 'rate': []})
                    self._append_triplets(bucket, flags[nbar][mask], amounts[nbar][mask], rates[nbar][mask])

    # =========================================================
    # 統計情報の集計・CSV出力
    # =========================================================
    def _compute_stats(self, flag_list, amount_list, rate_list):
        '''生データ(list)から統計辞書を返す'''
        n = len(flag_list)
        if n == 0:
            return {
                'sample_count': 0, 'rise_count': 0, 'flat_count': 0, 'fall_count': 0,
                'rise_rate': np.nan, 'fall_rate': np.nan,
                'amount_mean': np.nan, 'amount_std': np.nan, 'amount_median': np.nan,
                'rate_mean': np.nan, 'rate_std': np.nan,
            }
        flags_arr = np.asarray(flag_list)
        amounts_arr = np.asarray(amount_list, dtype=float)
        rates_arr = np.asarray(rate_list, dtype=float)
        rise = int((flags_arr == 1).sum())
        flat = int((flags_arr == 0).sum())
        fall = int((flags_arr == -1).sum())
        return {
            'sample_count': n,
            'rise_count': rise,
            'flat_count': flat,
            'fall_count': fall,
            'rise_rate': round(rise / n, 5),
            'fall_rate': round(fall / n, 5),
            'amount_mean': round(float(np.mean(amounts_arr)), 4),
            'amount_std': round(float(np.std(amounts_arr, ddof=1)), 4) if n > 1 else 0.0,
            'amount_median': round(float(np.median(amounts_arr)), 4),
            'rate_mean': round(float(np.mean(rates_arr)), 7),
            'rate_std': round(float(np.std(rates_arr, ddof=1)), 7) if n > 1 else 0.0,
        }

    def _save_statistics(self):
        '''
        蓄積した生データから各統計を集計し、CSVに出力する。
        全体／銘柄別／日付別の3スコープでそれぞれCSV出力するため、
        合計18ファイル(6統計 × 3スコープ)が出力される。
        '''
        try:
            os.makedirs(STATISTICS_DIR, exist_ok=True)
            time_start = time.perf_counter()

            stat_filenames = {
                1: 'statistics_1_signal_accuracy',
                2: 'statistics_2_bucket',
                3: 'statistics_3_bars_after_cross',
                4: 'statistics_4_threshold',
                5: 'statistics_5_bb_sigma',
                6: 'statistics_6_price_ma_position',
            }
            stat_columns = {
                1: STAT1_COLUMNS, 2: STAT2_COLUMNS, 3: STAT3_COLUMNS,
                4: STAT4_COLUMNS, 5: STAT5_COLUMNS, 6: STAT6_COLUMNS,
            }
            build_funcs = {
                1: self._build_stat1_rows, 2: self._build_stat2_rows,
                3: self._build_stat3_rows, 4: self._build_stat4_rows,
                5: self._build_stat5_rows, 6: self._build_stat6_rows,
            }

            # 各スコープ × 各統計を build → write
            for scope in SCOPES:
                for stat_no in range(1, 7):
                    t = time.perf_counter()
                    rows = build_funcs[stat_no](scope)
                    build_sec = time.perf_counter() - t
                    columns = SCOPE_PREFIX_COLUMNS[scope] + stat_columns[stat_no]
                    filename = f'{stat_filenames[stat_no]}_{scope}.csv'
                    tw = time.perf_counter()
                    self._write_csv(filename, rows, columns)
                    write_sec = time.perf_counter() - tw
                    self.log.info(f'  scope={scope} stat{stat_no}: build={build_sec:.3f}秒 write={write_sec:.3f}秒')

            self.log.info(f'統計集計・出力完了 (合計 {time.perf_counter() - time_start:.3f}秒)')
            return True
        except Exception as e:
            self.log.error(f'統計情報の保存でエラー\n{e}\n{traceback.format_exc()}')
            return False

    def _write_csv(self, filename, rows, columns):
        path = os.path.join(STATISTICS_DIR, filename)
        out_df = pd.DataFrame(rows, columns=columns)
        out_df.to_csv(path, index=False)
        self.log.info(f'統計CSV出力: {path} ({len(rows)}行)')

    # =========================================================
    # スコープ別集計のヘルパー
    # =========================================================
    def _aggregate_by_scope(self, raw_data, scope, key_tuple_size):
        '''
        raw_data: dict[(other_keys..., stock_code, date)] = bucket
        scope: SCOPE_ALL / SCOPE_BY_STOCK / SCOPE_BY_DATE
        key_tuple_size: stock_code/date を除いた先頭キーの個数

        Returns:
            dict[grouped_key] = merged_bucket
            - SCOPE_ALL: grouped_key = (other_keys...)
            - SCOPE_BY_STOCK: grouped_key = (other_keys..., stock_code)
            - SCOPE_BY_DATE: grouped_key = (other_keys..., date)
        '''
        out = {}
        for full_key, bucket in raw_data.items():
            other = full_key[:key_tuple_size]
            sc = full_key[key_tuple_size]
            dt = full_key[key_tuple_size + 1]
            if scope == SCOPE_ALL:
                new_key = other
            elif scope == SCOPE_BY_STOCK:
                new_key = other + (sc,)
            else:  # SCOPE_BY_DATE
                new_key = other + (dt,)
            merged = out.get(new_key)
            if merged is None:
                merged = {k: [] for k in bucket.keys()}
                out[new_key] = merged
            for k, vals in bucket.items():
                merged[k].extend(vals)
        return out

    def _scope_ids(self, scope):
        '''スコープに対応する識別子のリストを返す。SCOPE_ALL のときは [None]'''
        if scope == SCOPE_ALL:
            return [None]
        if scope == SCOPE_BY_STOCK:
            return sorted(self.all_stocks)
        return sorted(self.all_dates)

    def _scope_prefix(self, scope, scope_id):
        '''スコープに対応する先頭カラムの dict を返す'''
        if scope == SCOPE_ALL:
            return {}
        if scope == SCOPE_BY_STOCK:
            return {'stock_code': scope_id}
        return {'date': scope_id}

    def _empty_stats(self):
        '''サンプル無しの空統計値(NaN埋め用)'''
        return self._compute_stats([], [], [])

    # =========================================================
    # 各統計の行生成 (スコープ別)
    # =========================================================
    def _build_stat1_rows(self, scope):
        '''統計①(シグナル精度)の行を生成。NaN埋めポリシーに従い該当データなしの組も sample_count=0 行として出力'''
        agg = self._aggregate_by_scope(self.stat1_data, scope, 3)  # (col, stype, nbar)
        unique_triples = sorted({full_key[:3] for full_key in self.stat1_data.keys()})
        scope_ids = self._scope_ids(scope)

        rows = []
        for (col, stype, nbar) in unique_triples:
            for sid in scope_ids:
                key = (col, stype, nbar) if scope == SCOPE_ALL else (col, stype, nbar, sid)
                data = agg.get(key)
                stats = self._compute_stats(data['flag'], data['amount'], data['rate']) if data else self._empty_stats()
                rows.append({
                    **self._scope_prefix(scope, sid),
                    'signal_col': col, 'signal_type': stype, 'nbar': nbar,
                    **stats,
                })
        return rows

    def _build_stat2_rows(self, scope):
        '''統計②(バケット別)の行を生成。スコープ内で四分位閾値を独立に算出'''
        agg = self._aggregate_by_scope(self.stat2_raw, scope, 2)  # (col, nbar)
        # スコープ識別子ごとに整理: per_col_sid[(col, sid)] = {nbar: data}
        per_col_sid = {}
        for key, data in agg.items():
            if scope == SCOPE_ALL:
                col, nbar = key
                sid = None
            else:
                col, nbar, sid = key
            per_col_sid.setdefault((col, sid), {})[nbar] = data

        even_map = {c: (lo, hi, nb) for (c, lo, hi, nb) in BUCKET_EVEN}
        scope_ids = self._scope_ids(scope)
        unique_cols = sorted({k[0] for k in self.stat2_raw.keys()})

        rows = []
        for col in unique_cols:
            for sid in scope_ids:
                by_nbar = per_col_sid.get((col, sid), {})
                if col in even_map:
                    lo, hi, n_buckets = even_map[col]
                    edges = np.linspace(lo, hi, n_buckets + 1)
                    for nbar in NBAR_LIST:
                        data = by_nbar.get(nbar)
                        for i in range(n_buckets):
                            left = float(edges[i])
                            right = float(edges[i + 1])
                            label = f'[{left}, {right}]' if i == n_buckets - 1 else f'[{left}, {right})'
                            if data is None:
                                stats = self._empty_stats()
                            else:
                                values = np.asarray(data['value'], dtype=float)
                                if col == 'bb_1min_20piece_position':
                                    values = np.clip(values, 0.0, 1.0)
                                flags_arr = np.asarray(data['flag'])
                                amounts_arr = np.asarray(data['amount'], dtype=float)
                                rates_arr = np.asarray(data['rate'], dtype=float)
                                if i == n_buckets - 1:
                                    mask = (values >= left) & (values <= right)
                                else:
                                    mask = (values >= left) & (values < right)
                                stats = self._compute_stats(
                                    flags_arr[mask].tolist(),
                                    amounts_arr[mask].tolist(),
                                    rates_arr[mask].tolist(),
                                )
                            rows.append({
                                **self._scope_prefix(scope, sid),
                                'oscillator_col': col, 'bucket_label': label,
                                'bucket_left': round(left, 4), 'bucket_right': round(right, 4),
                                'nbar': nbar, **stats,
                            })
                else:
                    # 四分位分割: スコープ内で全nbar共通の閾値を決定
                    all_values = []
                    for d in by_nbar.values():
                        all_values.extend(d['value'])
                    labels = ['Q1', 'Q2', 'Q3', 'Q4']
                    if not all_values:
                        # データが無いスコープ識別子も NaN行で埋める
                        for nbar in NBAR_LIST:
                            for label in labels:
                                rows.append({
                                    **self._scope_prefix(scope, sid),
                                    'oscillator_col': col, 'bucket_label': label,
                                    'bucket_left': np.nan, 'bucket_right': np.nan,
                                    'nbar': nbar, **self._empty_stats(),
                                })
                        continue
                    all_arr = np.asarray(all_values, dtype=float)
                    boundaries = [
                        float(all_arr.min()),
                        float(np.quantile(all_arr, 0.25)),
                        float(np.quantile(all_arr, 0.50)),
                        float(np.quantile(all_arr, 0.75)),
                        float(all_arr.max()),
                    ]
                    for nbar in NBAR_LIST:
                        data = by_nbar.get(nbar)
                        for i in range(4):
                            left = boundaries[i]
                            right = boundaries[i + 1]
                            if data is None:
                                stats = self._empty_stats()
                            else:
                                values = np.asarray(data['value'], dtype=float)
                                flags_arr = np.asarray(data['flag'])
                                amounts_arr = np.asarray(data['amount'], dtype=float)
                                rates_arr = np.asarray(data['rate'], dtype=float)
                                if i == 3:
                                    mask = (values >= left) & (values <= right)
                                else:
                                    mask = (values >= left) & (values < right)
                                stats = self._compute_stats(
                                    flags_arr[mask].tolist(),
                                    amounts_arr[mask].tolist(),
                                    rates_arr[mask].tolist(),
                                )
                            rows.append({
                                **self._scope_prefix(scope, sid),
                                'oscillator_col': col, 'bucket_label': labels[i],
                                'bucket_left': round(left, 6), 'bucket_right': round(right, 6),
                                'nbar': nbar, **stats,
                            })
        return rows

    def _build_stat3_rows(self, scope):
        '''統計③(クロス後経過バー数別)の行を生成'''
        agg = self._aggregate_by_scope(self.stat3_data, scope, 4)  # (col, ctype, bars, nbar)
        unique_keys = sorted({full_key[:4] for full_key in self.stat3_data.keys()})
        scope_ids = self._scope_ids(scope)
        rows = []
        for (col, ctype, bars, nbar) in unique_keys:
            for sid in scope_ids:
                key = (col, ctype, bars, nbar) if scope == SCOPE_ALL else (col, ctype, bars, nbar, sid)
                data = agg.get(key)
                stats = self._compute_stats(data['flag'], data['amount'], data['rate']) if data else self._empty_stats()
                rows.append({
                    **self._scope_prefix(scope, sid),
                    'after_col': col, 'cross_type': ctype,
                    'bars_elapsed': bars, 'nbar': nbar, **stats,
                })
        return rows

    def _build_stat4_rows(self, scope):
        '''統計④(閾値以上/以下)の行を生成。動的閾値はスコープごとに独立に算出'''
        agg = self._aggregate_by_scope(self.stat4_raw, scope, 2)  # (col, nbar)
        per_col_sid = {}
        for key, data in agg.items():
            if scope == SCOPE_ALL:
                col, nbar = key
                sid = None
            else:
                col, nbar, sid = key
            per_col_sid.setdefault((col, sid), {})[nbar] = data

        scope_ids = self._scope_ids(scope)
        unique_cols = sorted({k[0] for k in self.stat4_raw.keys()})

        rows = []
        for col in unique_cols:
            for sid in scope_ids:
                by_nbar = per_col_sid.get((col, sid), {})
                # スコープ内でのデータをプールして閾値を決定
                if col in THRESHOLD_FIXED:
                    thresholds = list(THRESHOLD_FIXED[col])
                else:
                    all_values = []
                    for d in by_nbar.values():
                        all_values.extend(d['value'])
                    if col == 'macd_1min_diff':
                        if all_values:
                            arr = np.asarray(all_values, dtype=float)
                            q25 = round(float(np.quantile(arr, 0.25)), 6)
                            q75 = round(float(np.quantile(arr, 0.75)), 6)
                            thresholds = [q25, 0.0, q75]
                        else:
                            thresholds = []
                    elif col == 'bb_1min_20piece_width':
                        if all_values:
                            arr = np.asarray(all_values, dtype=float)
                            q25 = round(float(np.quantile(arr, 0.25)), 6)
                            q50 = round(float(np.quantile(arr, 0.50)), 6)
                            q75 = round(float(np.quantile(arr, 0.75)), 6)
                            thresholds = [q25, q50, q75]
                        else:
                            thresholds = []
                    else:
                        # MA diff / 一目 diff 系 (0基準。相対化済みでも0基準は変わらない)
                        thresholds = [0.0]

                if not thresholds:
                    # スコープ識別子にデータが無く動的閾値が決められない場合のNaN行
                    for nbar in NBAR_LIST:
                        for direction in ['above', 'below']:
                            rows.append({
                                **self._scope_prefix(scope, sid),
                                'indicator_col': col, 'threshold': np.nan,
                                'direction': direction, 'nbar': nbar, **self._empty_stats(),
                            })
                    continue

                for threshold in thresholds:
                    for direction in ['above', 'below']:
                        for nbar in NBAR_LIST:
                            data = by_nbar.get(nbar)
                            if data is None:
                                stats = self._empty_stats()
                            else:
                                values = np.asarray(data['value'], dtype=float)
                                flags_arr = np.asarray(data['flag'])
                                amounts_arr = np.asarray(data['amount'], dtype=float)
                                rates_arr = np.asarray(data['rate'], dtype=float)
                                if direction == 'above':
                                    mask = values >= threshold
                                else:
                                    mask = values <= threshold
                                stats = self._compute_stats(
                                    flags_arr[mask].tolist(),
                                    amounts_arr[mask].tolist(),
                                    rates_arr[mask].tolist(),
                                )
                            rows.append({
                                **self._scope_prefix(scope, sid),
                                'indicator_col': col, 'threshold': threshold,
                                'direction': direction, 'nbar': nbar, **stats,
                            })
        return rows

    def _build_stat5_rows(self, scope):
        '''統計⑤(BBσ位置別)の行を生成'''
        agg = self._aggregate_by_scope(self.stat5_data, scope, 2)  # (name, nbar)
        unique_keys = sorted({full_key[:2] for full_key in self.stat5_data.keys()})
        scope_ids = self._scope_ids(scope)
        rows = []
        for (name, nbar) in unique_keys:
            for sid in scope_ids:
                key = (name, nbar) if scope == SCOPE_ALL else (name, nbar, sid)
                data = agg.get(key)
                stats = self._compute_stats(data['flag'], data['amount'], data['rate']) if data else self._empty_stats()
                rows.append({
                    **self._scope_prefix(scope, sid),
                    'condition_name': name, 'nbar': nbar, **stats,
                })
        return rows

    def _build_stat6_rows(self, scope):
        '''統計⑥(価格とMAの位置関係)の行を生成'''
        agg = self._aggregate_by_scope(self.stat6_data, scope, 3)  # (col, position, nbar)
        unique_keys = sorted({full_key[:3] for full_key in self.stat6_data.keys()})
        scope_ids = self._scope_ids(scope)
        rows = []
        for (col, position, nbar) in unique_keys:
            for sid in scope_ids:
                key = (col, position, nbar) if scope == SCOPE_ALL else (col, position, nbar, sid)
                data = agg.get(key)
                stats = self._compute_stats(data['flag'], data['amount'], data['rate']) if data else self._empty_stats()
                rows.append({
                    **self._scope_prefix(scope, sid),
                    'ma_col': col, 'position': position, 'nbar': nbar, **stats,
                })
        return rows

    def _cleanup_extracted(self, date, ohlc_date_dir):
        '''解凍したディレクトリを削除する（存在しない場合は何もしない）'''
        if os.path.exists(ohlc_date_dir):
            try:
                shutil.rmtree(ohlc_date_dir)
                self.log.info(f'{date}: 解凍ディレクトリを削除しました')
            except Exception as e:
                self.log.error(f'{date}: 解凍ディレクトリの削除でエラー\n{e}\n{traceback.format_exc()}')

    def _restore_evacuated(self, date, ohlc_date_dir, tmp_date_dir):
        '''退避していたディレクトリが存在する場合は元の場所に復元する'''
        if os.path.exists(tmp_date_dir):
            try:
                shutil.move(tmp_date_dir, ohlc_date_dir)
                self.log.info(f'{date}: 退避ディレクトリを csv/ohlc/{date}/ に復元しました')
            except Exception as e:
                self.log.error(f'{date}: 退避ディレクトリの復元でエラー\n{e}\n{traceback.format_exc()}')

    def run(self):
        '''メイン処理'''
        # 処理対象の日付リストを取得
        dates = self.get_target_dates()

        if not dates:
            self.log.info('処理対象の7zファイルが csv/ohlc/bak/ に見つかりません')
            return

        self.log.info(f'処理対象日付: {dates}')

        # 7z解凍・CSVファイル名取得
        for date in dates:
            self.log.info(f'[解凍] {date}')
            result, _ = self.collect_ohlc_csv(date)
            if not result:
                self.log.error(f'{date}: CSVファイル名の収集に失敗しました。スキップします')
                continue
            self.log.info(f'{date}: 収集完了')

        if not self.csv_dict:
            self.log.info('収集できたCSVファイルがありません')
            return

        self.log.info(f'全date解凍完了 CSVファイル数={len(self.csv_dict)}')

        # テクニカル指標計算・統計情報の蓄積
        self.calc_indicators()

        # 蓄積した生データから統計情報を集計してCSV出力
        self._save_statistics()

        # 解凍ディレクトリの全削除・退避したディレクトリも戻す
        for date in dates:
            ohlc_date_dir = os.path.join(OHLC_DIR, date)
            tmp_date_dir = os.path.join(TMP_DIR, date)
            self._cleanup_extracted(date, ohlc_date_dir)
            self._restore_evacuated(date, ohlc_date_dir, tmp_date_dir)


if __name__ == '__main__':
    IndicatorStatistics().run()
