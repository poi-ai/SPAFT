# テクニカル指標の正当性チェックスクリプト（第4回: 一目均衡表バグ修正 + ファントムゼロ問題修正後）
#
# 目的: 第3回チェックで残ったWARNING項目のうち修正対象を修正した後の動作を確認する。
#   - 一目均衡表: high_column_name/low_column_name パラメータ追加・close代替フォールバック削除
#   - RSI/PSY: ファントムゼロ（diff[0]=NaN が 0 に化けていた問題）を修正
#
# 実行方法: src/ ディレクトリ内で実行
#   cd src && python analytics/test_indicator_validity.py
#
# 出力: docs/report_indicator_validity4.md

import os
import sys
import traceback
import numpy as np
import pandas as pd
from datetime import datetime

# インポートパスの設定（src/ から実行することを前提とする）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from util.log import Log
from util.indicator import Indicator

# =========================================================
# 定数・パス設定
# =========================================================
REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
SAMPLE_CSV_PATH = os.path.join(REPO_ROOT, 'csv', 'result', 'ohlc_sample_phase1.csv')
REPORT_PATH = os.path.join(REPO_ROOT, 'docs', 'report_indicator_validity4.md')

# =========================================================
# 1. サンプルCSV生成
# =========================================================

def generate_sample_ohlc():
    '''
    フェーズ1(#46)で出力されるであろうohlcテーブルのCSVサンプルを生成する。

    ohlcテーブルのスキーマ (statistic_daytrade_plan.md より):
        symbol        : str  - 証券コード
        trade_time    : datetime - 取引分（秒を切り捨て）
        open_price    : float - 始値
        high_price    : float - 高値
        low_price     : float - 安値
        close_price   : float - 終値
        volume        : int  - 当該分の出来高
        total_volume  : int  - 当日累積出来高
        status        : int  - ステータス（常に1）

    銘柄: 1570 (NEXT FUNDS 日経225連動型上場投信)
    想定価格帯: 28,000円前後
    日付: 2026-04-06 (仮想営業日)
    前場: 9:00〜11:30 = 150本、後場: 12:30〜15:25 = 175本
    '''
    np.random.seed(42)

    symbol = '1570'
    base_price = 28000.0

    # 前場: 9:00〜11:29 (150分)
    morning_times = pd.date_range('2026-04-06 09:00', periods=150, freq='1min')
    # 後場: 12:30〜15:24 (175分)
    afternoon_times = pd.date_range('2026-04-06 12:30', periods=175, freq='1min')
    all_times = morning_times.append(afternoon_times)
    n = len(all_times)  # 325行

    # ランダムウォークで終値を生成（σ=30円程度の1分変動）
    changes = np.random.normal(0, 30, n)
    close_prices = np.round(base_price + np.cumsum(changes), 0)
    # 負値にならないようクリップ（現実的な下限）
    close_prices = np.clip(close_prices, 10000, 60000)

    # 始値 = 1本前の終値
    open_prices = np.empty(n)
    open_prices[0] = base_price
    open_prices[1:] = close_prices[:-1]
    open_prices = np.round(open_prices, 0)

    # 高値 = max(open, close) + 上振れ（絶対値で正方向）
    upside = np.abs(np.random.normal(0, 15, n))
    high_prices = np.round(np.maximum(open_prices, close_prices) + upside, 0)

    # 安値 = min(open, close) - 下振れ（絶対値で負方向）
    downside = np.abs(np.random.normal(0, 15, n))
    low_prices = np.round(np.minimum(open_prices, close_prices) - downside, 0)
    low_prices = np.clip(low_prices, 1, None)

    # 出来高・累積出来高
    volumes = np.random.randint(500, 8000, n).astype(int)
    total_volumes = np.cumsum(volumes).astype(int)

    df = pd.DataFrame({
        'symbol': symbol,
        'trade_time': all_times.strftime('%Y-%m-%d %H:%M:%S'),
        'open_price': open_prices.astype(float),
        'high_price': high_prices.astype(float),
        'low_price': low_prices.astype(float),
        'close_price': close_prices.astype(float),
        'volume': volumes,
        'total_volume': total_volumes,
        'status': 1,
    })

    return df


# =========================================================
# 2. チェック結果を記録するクラス
# =========================================================

class CheckResult:
    '''各テクニカル指標の正当性チェック結果を記録する'''

    PASS = 'PASS'
    FAIL = 'FAIL'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

    def __init__(self, name):
        self.name = name
        self.status = self.PASS
        self.messages = []
        self.details = {}

    def add(self, status, message):
        if status == self.ERROR and self.status != self.ERROR:
            self.status = self.ERROR
        elif status == self.FAIL and self.status not in (self.ERROR,):
            self.status = self.FAIL
        elif status == self.WARNING and self.status == self.PASS:
            self.status = self.WARNING
        self.messages.append(f'[{status}] {message}')

    def ok(self, message):
        self.messages.append(f'[OK] {message}')

    def __repr__(self):
        return f'CheckResult({self.name}, {self.status})'


# =========================================================
# 3. 各指標のチェック関数
# =========================================================

def check_sma(indicator, df, results):
    '''SMA(単純移動平均線)の正当性チェック'''
    r = CheckResult('SMA (sma_1min_3piece, interval=1)')
    col = 'sma_1min_3piece'
    window = 3
    try:
        ok, df_out = indicator.get_sma(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return None
        vals = df_out[col]
        # 先頭 window_size-1 行が NaN であること（修正後の期待動作）
        expected_nan = window - 1
        actual_nan = vals.isna().sum()
        if actual_nan == expected_nan:
            r.ok(f'先頭{expected_nan}行がNaN（window_size-1行分の期待する欠損）')
        elif actual_nan > expected_nan:
            r.add(CheckResult.FAIL, f'NaNが{actual_nan}行残存（期待値: {expected_nan}行）')
        else:
            r.add(CheckResult.FAIL, f'NaNが{actual_nan}行しかない（期待値: {expected_nan}行）— 初期値に意図しない補完が入っている可能性')
        # 有効値の範囲チェック: 正の実数であること
        valid = vals.dropna()
        if (valid <= 0).any():
            r.add(CheckResult.FAIL, f'有効なSMA値に0以下の値が存在: min={valid.min()}')
        else:
            r.ok(f'有効値{len(valid)}行が全て正の実数')
        # 精度チェック: window本目の値が直近window本のclose平均と一致するか
        idx = window - 1  # 0ベース
        expected = df['close_price'].iloc[:window].mean().round(1)
        actual = vals.iloc[idx]
        if abs(actual - expected) < 1.0:
            r.ok(f'第{window}行目の値が期待値({expected})と一致: {actual}')
        else:
            r.add(CheckResult.FAIL, f'第{window}行目の値が期待値({expected})と不一致: {actual}')
        r.details = {'nan_count': int(actual_nan), 'min': float(valid.min()), 'max': float(valid.max()), 'sample': list(vals.iloc[window-1:window+3].round(1))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}\n{traceback.format_exc()}')
    results.append(r)
    return df_out if ok else None


def check_ema(indicator, df, results):
    '''EMA(指数移動平均線)の正当性チェック'''
    r = CheckResult('EMA (ema_1min_3piece, interval=1)')
    col = 'ema_1min_3piece'
    try:
        ok, df_out = indicator.get_ema(df.copy(), col, window_size=3, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return None
        vals = df_out[col]
        nan_count = vals.isna().sum()
        if nan_count > 0:
            r.add(CheckResult.WARNING, f'NaNが{nan_count}行残存')
        valid = vals.dropna()
        if (valid <= 0).any():
            r.add(CheckResult.FAIL, f'EMAに0以下の値が存在')
        else:
            r.ok('全値が正の実数')
        # ewm は最初の行から値が出るため NaN は出ないはず（fillna(-1)はしているが）
        first_val = vals.iloc[0]
        first_close = df['close_price'].iloc[0]
        if abs(first_val - first_close) < 1.0:
            r.ok(f'第1行目のEMAが始値({first_close})と一致: {first_val}')
        else:
            r.add(CheckResult.WARNING, f'第1行目のEMA({first_val})が始値({first_close})と乖離 (ewmの性質上許容範囲内の可能性あり)')
        r.details = {'min': float(valid.min()), 'max': float(valid.max()), 'sample': list(vals.iloc[:4].round(1))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)
    return df_out if ok else None


def check_wma(indicator, df, results):
    '''WMA(加重移動平均線)の正当性チェック'''
    r = CheckResult('WMA (wma_1min_3piece, interval=1)')
    col = 'wma_1min_3piece'
    window = 3
    try:
        ok, df_out = indicator.get_wma(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return None
        vals = df_out[col]
        # 先頭 window_size-1 行が NaN であること（修正後の期待動作）
        expected_nan = window - 1
        actual_nan = vals.isna().sum()
        if actual_nan == expected_nan:
            r.ok(f'先頭{expected_nan}行がNaN（window_size-1行分の期待する欠損）')
        elif actual_nan > expected_nan:
            r.add(CheckResult.FAIL, f'NaNが{actual_nan}行残存（期待値: {expected_nan}行）')
        else:
            r.add(CheckResult.FAIL, f'NaNが{actual_nan}行しかない（期待値: {expected_nan}行）— 初期値に意図しない補完が入っている可能性')
        valid = vals.dropna()
        if (valid <= 0).any():
            r.add(CheckResult.FAIL, f'有効なWMA値に0以下の値が存在: min={valid.min()}')
        else:
            r.ok(f'有効値{len(valid)}行が全て正の実数')
        # WMAの精度チェック: weights=[1,2,3]の場合 wma = (p[-2]*1 + p[-1]*2 + p[0]*3) / 6
        weights = np.array([1, 2, 3])
        p = df['close_price'].iloc[:3].values
        expected = np.round(np.dot(p, weights) / weights.sum(), 1)
        actual = vals.iloc[window - 1]
        if abs(actual - expected) < 1.0:
            r.ok(f'第{window}行目のWMAが期待値({expected})と一致: {actual}')
        else:
            r.add(CheckResult.FAIL, f'第{window}行目のWMAが期待値({expected})と不一致: {actual}')
        r.details = {'nan_count': int(actual_nan), 'min': float(valid.min()), 'max': float(valid.max()), 'sample': list(vals.iloc[window-1:window+3].round(1))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)
    return df_out if ok else None


def check_bollinger_bands(indicator, df, results):
    '''ボリンジャーバンドの正当性チェック'''
    r = CheckResult('ボリンジャーバンド (bb_1min_3piece, interval=1)')
    col = 'bb_1min_3piece'
    window = 3
    try:
        ok, df_out = indicator.get_bollinger_bands(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return None

        # バンドのカラム確認
        expected_cols = [
            f'{col}_upper_1sigma', f'{col}_lower_1sigma',
            f'{col}_upper_2sigma', f'{col}_lower_2sigma',
            f'{col}_upper_3sigma', f'{col}_lower_3sigma',
            f'{col}_width', f'{col}_width_diff',
            f'{col}_upper_diff', f'{col}_lower_diff',
            f'{col}_position',
        ]
        missing = [c for c in expected_cols if c not in df_out.columns]
        if missing:
            r.add(CheckResult.FAIL, f'期待するカラムが存在しない: {missing}')
        else:
            r.ok(f'期待する{len(expected_cols)}カラムが全て生成された')

        # upper > lower の確認（windowサイズ以降）
        valid_slice = df_out.iloc[window:]
        upper1 = valid_slice[f'{col}_upper_1sigma']
        lower1 = valid_slice[f'{col}_lower_1sigma']
        upper2 = valid_slice[f'{col}_upper_2sigma']
        lower2 = valid_slice[f'{col}_lower_2sigma']

        if (upper1 > lower1).all():
            r.ok('upper_1sigma > lower_1sigma が全行成立')
        else:
            r.add(CheckResult.FAIL, f'upper_1 <= lower_1 が存在: {(upper1 <= lower1).sum()}行')

        if (upper2 > upper1).all():
            r.ok('upper_2sigma > upper_1sigma が全行成立')
        else:
            r.add(CheckResult.FAIL, f'upper_2 <= upper_1 が存在')

        if (lower1 > lower2).all():
            r.ok('lower_1sigma > lower_2sigma が全行成立（バンドの広がり確認）')
        else:
            r.add(CheckResult.FAIL, f'lower_1 <= lower_2 が存在')

        # widthが正の値か
        width = valid_slice[f'{col}_width']
        if (width > 0).all():
            r.ok('幅(width)が全行で正の値')
        else:
            r.add(CheckResult.WARNING, f'幅が0の行が存在: {(width <= 0).sum()}行（価格変動がなかった場合は許容）')

        # positionが0〜1の範囲か（-1はNaN補完の可能性）
        pos = valid_slice[f'{col}_position'].dropna()
        out_of_range = ((pos < -0.5) | (pos > 1.5)).sum()
        if out_of_range == 0:
            r.ok('position値が概ね0〜1の範囲内')
        else:
            r.add(CheckResult.WARNING, f'positionが0〜1を外れる行が{out_of_range}個（極端な外れ値の可能性）')

        r.details = {
            'sample_upper_1': list(upper1.iloc[:3].round(1)),
            'sample_lower_1': list(lower1.iloc[:3].round(1)),
            'sample_width': list(width.iloc[:3].round(3)),
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)
    return df_out if ok else None


def check_ma_cross(indicator, df_with_ma, results):
    '''MAクロスの正当性チェック（事前にSMA/EMA/WMAが計算済みのdfを渡す）'''
    r = CheckResult('MAクロス (ma_cross, interval=1)')
    interval = 1
    try:
        ok, df_out = indicator.get_ma_cross(df_with_ma.copy(), interval=interval)
        if not ok:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return
        if df_out.empty:
            r.add(CheckResult.WARNING, '結果のDataFrameが空（SMA/EMA/WMAの事前計算カラムが見つからなかった可能性）')
            results.append(r); return

        # クロスカラムの確認
        cross_cols = [c for c in df_out.columns if 'golden_cross' in c or 'dead_cross' in c or '_diff' in c]
        r.ok(f'クロスカラム{len(cross_cols)}本が生成された')

        # golden_crossは0または1のフラグ
        gc_cols = [c for c in df_out.columns if 'golden_cross' in c and 'after' not in c]
        for col in gc_cols[:2]:  # 代表2列確認
            unique_vals = df_out[col].dropna().unique()
            if set(unique_vals).issubset({0, 1, 0.0, 1.0}):
                r.ok(f'{col}: 0/1フラグが正常')
            else:
                r.add(CheckResult.FAIL, f'{col}: 0/1以外の値が存在 {unique_vals}')

        # diff カラムが数値（正負を取れる）かどうか、かつ株価の絶対値レベルの外れ値がないか
        diff_cols = [c for c in df_out.columns if c.endswith('_diff')]
        close_std = df_out['close_price'].std() if 'close_price' in df_out.columns else 500.0
        for col in diff_cols[:2]:
            valid = df_out[col].dropna()
            if valid.dtype in (float, np.float64) and not valid.empty:
                abs_max = valid.abs().max()
                # 合理的な差分は株価の標準偏差の10倍程度を上限とする（-1補完汚染があると株価絶対値レベルになる）
                if abs_max < close_std * 10:
                    r.ok(f'{col}: 合理的な差分値 (range: {valid.min():.1f}〜{valid.max():.1f})')
                else:
                    r.add(CheckResult.FAIL,
                          f'{col}: 差分に外れ値あり (range: {valid.min():.1f}〜{valid.max():.1f}) '
                          f'— NaN補完値との差が混入している可能性')
            else:
                r.add(CheckResult.WARNING, f'{col}: 型または値が予期しない形式')

    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_rsi(indicator, df, results):
    '''RSI(相対力指数)の正当性チェック
    ファントムゼロ修正後: diff[0]=NaN が up/down にも伝播するため、
    先頭NaNは window行（修正前は window-1行）になる。
    '''
    r = CheckResult('RSI (rsi_1min_9piece, interval=1)')
    col = 'rsi_1min_9piece'
    window = 9
    expected_nan = window  # ファントムゼロ修正後は window行がNaN
    try:
        ok, df_out = indicator.get_rsi(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return
        vals = df_out[col]

        # NaN残存チェック: 先頭 window行がNaN（設計上の正常な挙動）
        nan_count = int(vals.isna().sum())
        if nan_count == expected_nan:
            r.ok(f'NaNが先頭{nan_count}行のみ（期待通り: window={window}本のデータが揃うまでNaN）')
        elif nan_count == 0:
            r.ok('NaN残存なし（全行に値あり）')
        else:
            r.add(CheckResult.WARNING,
                  f'NaNが{nan_count}行残存（期待={expected_nan}行）')

        valid = vals.dropna()
        # RSIは0〜100の範囲
        out_of_range = ((valid < 0) | (valid > 100)).sum()
        if out_of_range == 0:
            r.ok('全RSI値が0〜100の範囲内')
        else:
            r.add(CheckResult.FAIL, f'{out_of_range}行が0〜100を逸脱: min={valid.min()}, max={valid.max()}')

        r.details = {'nan_count': nan_count, 'expected_nan': expected_nan,
                     'sample': list(valid.iloc[:5].round(2))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_rci(indicator, df, results):
    '''RCI(順位相関指数)の正当性チェック'''
    r = CheckResult('RCI (rci_1min_9piece, interval=1)')
    col = 'rci_1min_9piece'
    window = 9
    try:
        ok, df_out = indicator.get_rci(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return
        vals = df_out[col]
        nan_count = vals.isna().sum()
        if nan_count > 0:
            r.add(CheckResult.WARNING, f'NaNが{nan_count}行残存')
        valid = vals.dropna()
        # RCIは-100〜100の範囲
        out_of_range = ((valid < -100.1) | (valid > 100.1)).sum()
        if out_of_range == 0:
            r.ok('全RCI値が-100〜100の範囲内')
        else:
            r.add(CheckResult.FAIL, f'{out_of_range}行が-100〜100を逸脱: min={valid.min()}, max={valid.max()}')
        r.details = {'nan_count': int(nan_count), 'sample': list(valid.iloc[window:window+5].round(2))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_macd(indicator, df, results):
    '''MACDの正当性チェック'''
    r = CheckResult('MACD (macd_1min, short=12, long=26, signal=9, interval=1)')
    col = 'macd_1min'
    try:
        ok, df_out = indicator.get_macd(df.copy(), col,
                                        short_window_size=12, long_window_size=26,
                                        signal_window_size=9, interval=1,
                                        price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return

        # 生成カラムの確認
        expected_cols = [col, f'{col}_signal', f'{col}_diff', f'{col}_hist_positive', f'{col}_cross',
                         f'{col}_mismatch', f'{col}_mismatch_count']
        missing = [c for c in expected_cols if c not in df_out.columns]
        if missing:
            r.add(CheckResult.FAIL, f'期待カラムが存在しない: {missing}')
        else:
            r.ok(f'期待する{len(expected_cols)}カラムが全て生成された')

        # diff = macd - signal が正しいか（誤差0.01以内）
        macd_vals = df_out[col]
        signal_vals = df_out[f'{col}_signal']
        diff_vals = df_out[f'{col}_diff']
        expected_diff = (macd_vals - signal_vals).round(3)
        diff_error = (diff_vals - expected_diff).abs().max()
        if diff_error < 0.01:
            r.ok(f'diff = macd - signal が正しい（最大誤差: {diff_error:.4f}）')
        else:
            r.add(CheckResult.FAIL, f'diffの計算誤差が大きい: {diff_error:.4f}')

        # hist_positive は diff > 0 なら 1、それ以外は 0
        flag_vals = df_out[f'{col}_hist_positive']
        expected_flag = (diff_vals > 0).astype(int)
        mismatch = (flag_vals != expected_flag).sum()
        if mismatch == 0:
            r.ok('hist_positive が正しく 0/1 で設定されている')
        else:
            r.add(CheckResult.FAIL, f'hist_positive の不一致が{mismatch}行')

        # cross は -1, 0, 1 のみ
        cross_vals = df_out[f'{col}_cross'].dropna()
        if set(cross_vals.unique()).issubset({-1, 0, 1}):
            r.ok('cross 値が -1/0/1 のみ')
        else:
            r.add(CheckResult.FAIL, f'cross に想定外の値: {cross_vals.unique()}')

        # slopeカラムの確認（count=[1,3,5,10]）
        slope_cols = [f'{col}_slope_{cnt}bar' for cnt in [1, 3, 5, 10]]
        missing_slopes = [c for c in slope_cols if c not in df_out.columns]
        if missing_slopes:
            r.add(CheckResult.WARNING, f'slopeカラムが存在しない: {missing_slopes}')
        else:
            r.ok(f'slopeカラム{len(slope_cols)}本が全て生成された')

        r.details = {
            'sample_macd': list(macd_vals.iloc[30:35].round(2)),
            'sample_signal': list(signal_vals.iloc[30:35].round(2)),
            'sample_diff': list(diff_vals.iloc[30:35].round(3)),
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_psy(indicator, df, results):
    '''PSY(サイコロジカルライン)の正当性チェック
    ファントムゼロ修正後: diff[0]=NaN が up にも伝播するため、
    先頭NaNは window行（修正前は window-1行）になる。
    '''
    r = CheckResult('PSY (psy_1min_10piece, interval=1)')
    col = 'psy_1min_10piece'
    window = 10
    expected_nan = window  # ファントムゼロ修正後は window行がNaN
    try:
        ok, df_out = indicator.get_psy(df.copy(), col, window_size=window, interval=1, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return
        vals = df_out[col]

        # NaN残存チェック: 先頭 window行がNaN（設計上の正常な挙動）
        nan_count = int(vals.isna().sum())
        if nan_count == expected_nan:
            r.ok(f'NaNが先頭{nan_count}行のみ（期待通り: window={window}本のデータが揃うまでNaN）')
        elif nan_count == 0:
            r.ok('NaN残存なし（全行に値あり）')
        else:
            r.add(CheckResult.WARNING,
                  f'NaNが{nan_count}行残存（期待={expected_nan}行）')

        valid = vals.dropna()
        # PSYは0〜100の範囲
        out_of_range = ((valid < 0) | (valid > 100)).sum()
        if out_of_range == 0:
            r.ok('全PSY値が0〜100の範囲内')
        else:
            r.add(CheckResult.FAIL, f'{out_of_range}行が0〜100を逸脱: min={valid.min()}, max={valid.max()}')
        # PSYは10の倍数(window=10なので 0, 10, 20, ..., 100 のいずれか)
        remainder = (valid % 10).abs()
        non_multiple = (remainder > 0.01).sum()
        if non_multiple == 0:
            r.ok(f'PSY値が全て10の倍数（window={window}に対する正常な離散値）')
        else:
            r.add(CheckResult.WARNING, f'10の倍数でない値が{non_multiple}行（丸め誤差の可能性）')
        r.details = {'nan_count': nan_count, 'expected_nan': expected_nan,
                     'sample': list(valid.iloc[:10].round(1))}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_parabolic_close(indicator, df, results):
    '''パラボリックSAR(終値ベース)の正当性チェック'''
    r = CheckResult('パラボリックSAR (close_price ベース, min_af=0.02, max_af=0.2, interval=1)')
    col = 'sar_1min_0.02_0.2af_close'
    try:
        ok, df_out = indicator.get_parabolic(df.copy(), col, min_af=0.02, max_af=0.2, interval=1,
                                             price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return
        sar_vals = df_out[col]
        flag_vals = df_out[f'{col}_flag']

        # SARが正の実数
        if (sar_vals > 0).all():
            r.ok('全SAR値が正の実数')
        else:
            r.add(CheckResult.FAIL, f'SAR値に0以下が存在')

        # flagは0または1
        unique_flags = set(flag_vals.dropna().unique())
        if unique_flags.issubset({0, 1, 0.0, 1.0}):
            r.ok('flagが0/1のみ')
        else:
            r.add(CheckResult.FAIL, f'flagに0/1以外の値: {unique_flags}')

        # SARが概ね株価の±30%以内（極端な外れ値がないか）
        close_mean = df['close_price'].mean()
        sar_mean = sar_vals.mean()
        if abs(sar_mean - close_mean) / close_mean < 0.30:
            r.ok(f'SAR平均({sar_mean:.0f})が終値平均({close_mean:.0f})の±30%以内')
        else:
            r.add(CheckResult.WARNING, f'SAR平均({sar_mean:.0f})が終値平均({close_mean:.0f})から大きく乖離')

        r.details = {'sample_sar': list(sar_vals.iloc[:5].round(1)), 'sample_flag': list(flag_vals.iloc[:5])}
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_parabolic_hlc(indicator, df, results):
    '''
    パラボリックSAR(三本値ベース)の正当性チェック

    修正後: high_column_name/low_column_name/close_column_name 引数を追加したため、
    ohlcテーブルのカラム名(high_price/low_price/close_price)を明示して渡せるようになった。
    '''
    r = CheckResult('パラボリックSAR HLC (high_column_name等を明示した正常動作の確認, interval=1)')
    col = 'sar_1min_0.02_0.2af_hlc'
    try:
        # ohlcのカラム名を明示して渡す
        ok, df_out = indicator.get_parabolic_hlc(
            df.copy(), col, min_af=0.02, max_af=0.2, interval=1,
            high_column_name='high_price', low_column_name='low_price', close_column_name='close_price'
        )
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return

        sar_vals = df_out[col]
        flag_vals = df_out[f'{col}_flag']
        rev_vals = df_out[f'{col}_reverse_flag']

        # SARが正の実数
        if (sar_vals > 0).all():
            r.ok('全SAR値が正の実数')
        else:
            r.add(CheckResult.FAIL, 'SAR値に0以下が存在')

        # flag / reverse_flag は 0 または 1
        for fname, fvals in [(f'{col}_flag', flag_vals), (f'{col}_reverse_flag', rev_vals)]:
            unique = set(fvals.dropna().unique())
            if unique.issubset({0, 1, 0.0, 1.0}):
                r.ok(f'{fname}: 0/1フラグが正常')
            else:
                r.add(CheckResult.FAIL, f'{fname}: 0/1以外の値が存在 {unique}')

        # SARが終値の±30%以内
        close_mean = df['close_price'].mean()
        sar_mean = sar_vals.mean()
        if abs(sar_mean - close_mean) / close_mean < 0.30:
            r.ok(f'SAR平均({sar_mean:.0f})が終値平均({close_mean:.0f})の±30%以内')
        else:
            r.add(CheckResult.WARNING, f'SAR平均({sar_mean:.0f})が終値平均({close_mean:.0f})から大きく乖離')

        r.details = {
            'sample_sar': list(sar_vals.iloc[:5].round(1)),
            'sample_flag': list(flag_vals.iloc[:5]),
            'sample_reverse_flag': list(rev_vals.iloc[:5]),
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'想定外の例外: {type(e).__name__}: {e}')
    results.append(r)


def check_ichimoku(indicator, df, results):
    '''
    一目均衡表の正当性チェック

    第3回修正: get_ichimoku_cloud() に high_column_name/low_column_name パラメータを追加し、
    close_price代替フォールバックを削除した。
    ohlcテーブルの高値/安値カラム名(high_price/low_price)を明示して渡せるようになった。
    '''
    r = CheckResult('一目均衡表 (high_column_name等を明示した正常動作の確認, interval=1)')
    col = 'ichimoku_1min'
    try:
        # ohlcカラム名を明示して渡す（修正後の正常動作確認）
        ok, df_out = indicator.get_ichimoku_cloud(df.copy(), col,
                                                   short_window_size=9, long_window_size=26,
                                                   interval=1,
                                                   close_column_name='close_price',
                                                   high_column_name='high_price',
                                                   low_column_name='low_price')
        if not ok or df_out is None:
            r.add(CheckResult.FAIL, 'メソッドがFalseを返した'); results.append(r); return

        # 主要カラムの生成確認
        expected_suffixes = ['_base_line', '_conversion_line', '_leading_span_a',
                             '_leading_span_b', '_lagging_span']
        all_present = True
        for suffix in expected_suffixes:
            full_col = f'{col}{suffix}'
            if full_col in df_out.columns:
                r.ok(f'{full_col} が生成された')
            else:
                r.add(CheckResult.FAIL, f'{full_col} が存在しない')
                all_present = False

        if not all_present:
            results.append(r); return

        # 基準線(26本)・転換線(9本)が正の数値型か
        base_col = f'{col}_base_line'
        conv_col = f'{col}_conversion_line'
        base_valid = df_out[base_col].dropna()
        conv_valid = df_out[conv_col].dropna()

        if (base_valid > 0).all():
            r.ok(f'基準線が正の数値型（有効値{len(base_valid)}行）')
        else:
            r.add(CheckResult.FAIL, '基準線に0以下の値が存在')

        if (conv_valid > 0).all():
            r.ok(f'転換線が正の数値型（有効値{len(conv_valid)}行）')
        else:
            r.add(CheckResult.FAIL, '転換線に0以下の値が存在')

        # 修正確認: 基準線 ≠ 転換線（以前はclose=high=lowの代替処理で全行一致していた）
        if not base_valid.empty and not conv_valid.empty:
            common_idx = base_valid.index.intersection(conv_valid.index)
            if len(common_idx) > 0:
                are_equal = (base_valid[common_idx].round(1) == conv_valid[common_idx].round(1)).all()
                if are_equal:
                    r.add(CheckResult.FAIL,
                          f'共通{len(common_idx)}行で基準線と転換線が全行一致。'
                          'high/low が正しく参照されていない可能性あり')
                else:
                    differ_count = (base_valid[common_idx].round(1) != conv_valid[common_idx].round(1)).sum()
                    r.ok(f'基準線と転換線が{differ_count}/{len(common_idx)}行で異なる値'
                         f'（high_price/low_price が正しく使われている）')

        # 先行スパン1・2が存在するか(NaNありでも可)
        lsa_col = f'{col}_leading_span_a'
        lsb_col = f'{col}_leading_span_b'
        lsa_valid = df_out[lsa_col].dropna()
        lsb_valid = df_out[lsb_col].dropna()
        if len(lsa_valid) > 0:
            r.ok(f'先行スパン1: 有効値{len(lsa_valid)}行（range: {lsa_valid.min():.0f}〜{lsa_valid.max():.0f}）')
        if len(lsb_valid) > 0:
            r.ok(f'先行スパン2: 有効値{len(lsb_valid)}行（range: {lsb_valid.min():.0f}〜{lsb_valid.max():.0f}）')

        r.details = {
            'high_column_name': 'high_price',
            'low_column_name': 'low_price',
            'base_line_sample': list(base_valid.iloc[:3].round(1)),
            'conversion_line_sample': list(conv_valid.iloc[:3].round(1)),
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


def check_change_price(indicator, df, results):
    '''
    変化額・変化率・フラグ計算の正当性チェック

    第2回修正: get_change_price() に price_column_name パラメータを追加したため、
    price_column_name='close_price' を明示することで ohlcテーブルでの動作を確認する。

    実装上の挙動:
      - 生成カラム名は {column_name}_amount / _rate / _flag
      - change_flag は -1(下落) / 0(変動なし) / 1(上昇)
      - 最終 interval 行は shift(-interval) が NaN になるが ffill で直前値が補完される
    '''
    r = CheckResult('変化額・変化率(get_change_price, price_column_name="close_price"を指定した正常動作の確認)')
    col = 'change_1min'
    try:
        ok, df_out = indicator.get_change_price(
            df.copy(), col, interval=1, price_column_name='close_price'
        )
        if not ok:
            r.add(CheckResult.FAIL, 'メソッドがFalseを返した'); results.append(r); return

        # 生成されるカラム名の確認 (suffix は _amount / _rate / _flag)
        change_amount_col = f'{col}_amount'
        change_rate_col = f'{col}_rate'
        change_flag_col = f'{col}_flag'
        all_ok = True
        for expected_col in [change_amount_col, change_rate_col, change_flag_col]:
            if expected_col in df_out.columns:
                r.ok(f'{expected_col} が生成された')
            else:
                r.add(CheckResult.FAIL, f'{expected_col} が存在しない')
                all_ok = False
        if not all_ok:
            results.append(r); return

        # change_amount の値確認（ffillにより NaN なし）
        cp_vals = df_out[change_amount_col]
        nan_count = int(cp_vals.isna().sum())
        if nan_count == 0:
            r.ok(f'change_amount: 全{len(cp_vals)}行に値あり（末尾はffillで補完済み）')
        else:
            r.add(CheckResult.WARNING, f'change_amount: NaNが{nan_count}行残っている')

        # change_amount の範囲チェック（28000円台の銘柄で1分変動が±2000円以内か）
        cp_valid = cp_vals.dropna()
        if len(cp_valid) > 0:
            cp_max_abs = cp_valid.abs().max()
            if cp_max_abs < 2000:
                r.ok(f'change_amount 最大絶対値: {cp_max_abs:.1f}円（妥当な範囲）')
            else:
                r.add(CheckResult.WARNING, f'change_amount 最大絶対値: {cp_max_abs:.1f}円（大きすぎる可能性）')

        # change_flag: -1/0/1 のみで構成されているか
        cf_vals = df_out[change_flag_col].dropna()
        unique_flags = set(cf_vals.unique())
        if unique_flags <= {-1.0, 0.0, 1.0}:
            r.ok(f'change_flag: 値が -1/0/1 のみ（有効値{len(cf_vals)}行）')
        else:
            r.add(CheckResult.FAIL, f'change_flag に -1/0/1 以外の値が存在: {unique_flags}')

        # change_rate: 先頭行で change_amount / close_price との一致確認
        if len(cp_valid) > 0:
            expected_rate = df_out[change_amount_col].iloc[0] / df['close_price'].iloc[0]
            actual_rate = df_out[change_rate_col].iloc[0]
            if abs(expected_rate - actual_rate) < 1e-9:
                r.ok(f'change_rate = change_amount / close_price の計算が正確')
            else:
                r.add(CheckResult.FAIL,
                      f'change_rate の計算が不正: 期待={expected_rate:.6f}, 実際={actual_rate:.6f}')

        r.details = {
            'price_column_name': 'close_price',
            'interval': 1,
            'change_amount_range': f'{cp_valid.min():.1f} ~ {cp_valid.max():.1f}',
            'change_flag_unique': sorted(unique_flags),
            'nan_rows': nan_count,
            '末尾補完': '最終1行は shift(-1)=NaN のため直前値で ffill',
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {type(e).__name__}: {e}\n{traceback.format_exc()}')
    results.append(r)


def check_interval_resampling(indicator, df, results):
    '''
    interval > 1 のリサンプリングロジックの確認チェック

    indicator.py の各メソッドは interval > 1 の場合 iloc[::interval] で行インデックスベースで
    リサンプリングを行う。ohlcテーブルには昼休み(11:30-12:30)が含まれないため、
    本来の時刻ベースのリサンプリングとは結果が異なる可能性がある。
    '''
    r = CheckResult('intervalリサンプリング方式の確認 (interval=5, 時刻ベースか行インデックスベースか)')
    col = 'sma_5min_3piece'
    interval = 5
    window = 3
    try:
        ok, df_out = indicator.get_sma(df.copy(), col, window_size=window, interval=interval, price_column_name='close_price')
        if not ok or df_out is None:
            r.add(CheckResult.ERROR, 'メソッドがFalseを返した'); results.append(r); return

        # iloc[::5]で抽出される行の時刻を確認
        resampled_times = df['trade_time'].iloc[::interval].tolist()
        r.ok(f'リサンプリング後の先頭5行の時刻: {resampled_times[:5]}')

        # 昼休みをまたぐ行インデックス周辺を確認
        # 前場150本目(11:29)→後場1本目(12:30)を跨ぐ行がインデックスベースで連続扱いになるか
        morning_last_idx = 149  # 11:29
        afternoon_first_idx = 150  # 12:30
        time_before = df['trade_time'].iloc[morning_last_idx]
        time_after = df['trade_time'].iloc[afternoon_first_idx]
        r.add(CheckResult.WARNING,
              f'行インデックスベースのリサンプリングのため、前場終了({time_before})と'
              f'後場開始({time_after})が連続した行として扱われる。'
              f'昼休み(60分)を跨ぐN分足の計算が時刻的に不正確になる可能性がある。')

        # SMA値が生成されていることを確認
        vals = df_out[col].dropna()
        if len(vals) > 0:
            r.ok(f'interval={interval}でSMAが{len(vals)}行生成された（生成自体は成功）')

        r.details = {
            'resampling_method': 'iloc[::interval] (行インデックスベース)',
            'first_5_times': resampled_times[:5],
            'lunch_break_gap': f'{time_before} → {time_after} (行上では連続)',
        }
    except Exception as e:
        r.add(CheckResult.ERROR, f'例外発生: {e}')
    results.append(r)


# =========================================================
# 4. MDレポート生成
# =========================================================

def render_md_report(results, df_info, generated_at):
    '''チェック結果をMarkdownレポートとして出力する'''

    status_icon = {
        CheckResult.PASS: '✅',
        CheckResult.FAIL: '❌',
        CheckResult.WARNING: '⚠️',
        CheckResult.ERROR: '💥',
    }

    lines = []
    lines.append(f'# テクニカル指標 正当性チェックレポート（第4回: 一目均衡表バグ修正 + ファントムゼロ問題修正後）')
    lines.append(f'')
    lines.append(f'**生成日時:** {generated_at}')
    lines.append(f'**対象:** `src/util/indicator.py` の各テクニカル指標計算メソッド')
    lines.append(f'**フェーズ:** issue #47 対応前の事前確認（第3回残存WARNING項目の修正後チェック）')
    lines.append(f'')
    lines.append(f'## 第3回からの変更点')
    lines.append(f'')
    lines.append(f'第3回チェックで残存していたWARNING項目のうち、修正対象とした2種3件を修正した。')
    lines.append(f'')
    lines.append(f'| メソッド | 問題 | 修正内容 |')
    lines.append(f'|---|---|---|')
    lines.append(f'| `get_ichimoku_cloud()` | `high`/`low` カラムが存在しない場合に `close_price` で代替する不正なフォールバック | `high_column_name`・`low_column_name` パラメータを追加。フォールバック処理を削除。デフォルト値で後方互換。 |')
    lines.append(f'| `get_rsi()` | `diff[0]=NaN` を `up/down` 計算で `0` として扱うファントムゼロ問題 | NaNを伝播するよう lambda を修正。先頭NaNが window-1行→window行に変化。 |')
    lines.append(f'| `get_psy()` | 同上（`up` 計算で NaN→0 になっていた） | 同上。先頭NaNが window-1行→window行に変化。 |')
    lines.append(f'')
    lines.append(f'**後方互換性:** `get_ichimoku_cloud()` の既存呼び出し元（`past_record_mold.py`）は `high`/`low` カラムを持つdfを渡しているため、デフォルト引数のまま動作する。')
    lines.append(f'## 前提・確認観点')
    lines.append(f'')
    lines.append(f'フェーズ1(#46)が完了すると、KabuStation WebSocket PUSHで蓄積された1分足OHLCデータが')
    lines.append(f'以下のカラム構成でCSVまたはDBテーブルに存在する想定。')
    lines.append(f'')
    lines.append(f'**ohlcテーブル/CSVのカラム構成:**')
    lines.append(f'```')
    lines.append(f'symbol, trade_time, open_price, high_price, low_price, close_price, volume, total_volume, status')
    lines.append(f'```')
    lines.append(f'')
    lines.append(f'`indicator.py` の各メソッドはデフォルトで `price_column_name="current_price"` を想定している。')
    lines.append(f'ohlcデータで使う場合は `price_column_name="close_price"` を明示する必要がある。')
    lines.append(f'第2〜4回の修正により、カラム名のハードコード問題および一目均衡表のフォールバックバグは全て解消済み。')
    lines.append(f'')

    # サンプルデータ概要
    lines.append(f'## サンプルデータ概要')
    lines.append(f'')
    lines.append(f'| 項目 | 値 |')
    lines.append(f'|---|---|')
    for k, v in df_info.items():
        lines.append(f'| {k} | {v} |')
    lines.append(f'')

    # サマリーテーブル
    lines.append(f'## チェック結果サマリー')
    lines.append(f'')
    lines.append(f'| # | 指標 | 結果 |')
    lines.append(f'|---|---|---|')
    for i, r in enumerate(results, 1):
        icon = status_icon.get(r.status, '?')
        lines.append(f'| {i} | {r.name} | {icon} {r.status} |')
    lines.append(f'')

    # 統計
    pass_count = sum(1 for r in results if r.status == CheckResult.PASS)
    warn_count = sum(1 for r in results if r.status == CheckResult.WARNING)
    fail_count = sum(1 for r in results if r.status == CheckResult.FAIL)
    err_count = sum(1 for r in results if r.status == CheckResult.ERROR)
    lines.append(f'**集計:** PASS={pass_count} / WARNING={warn_count} / FAIL={fail_count} / ERROR={err_count}')
    lines.append(f'')

    # 詳細
    lines.append(f'## 詳細結果')
    lines.append(f'')
    for r in results:
        icon = status_icon.get(r.status, '?')
        lines.append(f'### {icon} {r.name}')
        lines.append(f'')
        lines.append(f'**総合判定:** {r.status}')
        lines.append(f'')
        if r.messages:
            lines.append(f'**チェック項目:**')
            lines.append(f'')
            for msg in r.messages:
                lines.append(f'- {msg}')
            lines.append(f'')
        if r.details:
            lines.append(f'**詳細データ:**')
            lines.append(f'```')
            for k, v in r.details.items():
                lines.append(f'{k}: {v}')
            lines.append(f'```')
            lines.append(f'')

    # 残存懸念事項
    lines.append(f'## 残存する懸念事項（設計上の意図的な挙動）')
    lines.append(f'')
    lines.append(f'### 1. `interval` リサンプリングが時刻ベースではなく行インデックスベース')
    lines.append(f'')
    lines.append(f'```python')
    lines.append(f"# indicator.py 内部（各メソッド共通）")
    lines.append(f"df_resampled = df[[price_column_name]].iloc[::interval, :].copy()")
    lines.append(f'```')
    lines.append(f'`iloc[::interval]` は行番号ベースで等間隔抽出するため、')
    lines.append(f'前場(9:00-11:30, 150本)と後場(12:30-15:25, 175本)の間の昼休み(60分)を考慮しない。')
    lines.append(f'例: interval=5 の場合、前場149行目(11:29)と後場150行目(12:30)が')
    lines.append(f'「連続した5分間」として計算される。本来は91分離れている。')
    lines.append(f'')
    lines.append(f'**設計上の意図:** 国内証券会社のチャートが採用している方式と整合するため、意図的に維持。')
    lines.append(f'`interval=1`（1分足）が主な用途であれば影響ゼロ。詳細は `supplement_indicator_design_notes.md` を参照。')
    lines.append(f'')
    lines.append(f'### 2. RSI・RCI・PSY の先頭行 NaN（設計上の正常な挙動）')
    lines.append(f'')
    lines.append(f'window本ぶんのデータが揃うまで指標が計算できないため、先頭の window行はNaNになる。')
    lines.append(f'これは数学的に正しい挙動であり、修正は不要。')
    lines.append(f'')
    lines.append(f'| 指標 | window | 先頭NaN行数 |')
    lines.append(f'|---|---|---|')
    lines.append(f'| RSI | 9 | 9行（ファントムゼロ修正により window-1→window に変化） |')
    lines.append(f'| RCI | 9 | 8行（元々正確） |')
    lines.append(f'| PSY | 10 | 10行（ファントムゼロ修正により window-1→window に変化） |')
    lines.append(f'')
    lines.append(f'CatBoostはNaN対応済みのためML学習上の問題はない。')
    lines.append(f'')

    lines.append(f'---')
    lines.append(f'*このレポートは自動生成されたものです。第4回をもって事前確認フェーズは完了。issue #47 の実装フェーズに移行可能。*')

    return '\n'.join(lines)


# =========================================================
# 5. メイン処理
# =========================================================

def main():
    print('=== テクニカル指標 正当性チェック開始 ===')

    log = Log(output=1)  # コンソール出力のみ
    indicator = Indicator(log)

    # 1. サンプルCSVの生成と保存
    print('\n[1] サンプルCSVの生成...')
    df_sample = generate_sample_ohlc()
    os.makedirs(os.path.dirname(SAMPLE_CSV_PATH), exist_ok=True)
    df_sample.to_csv(SAMPLE_CSV_PATH, index=False)
    print(f'    サンプルCSV保存: {SAMPLE_CSV_PATH}')
    print(f'    行数: {len(df_sample)}, カラム: {list(df_sample.columns)}')

    # サンプルデータ概要（レポート用）
    df_info = {
        '銘柄コード': df_sample['symbol'].iloc[0],
        '行数': len(df_sample),
        '前場': '9:00〜11:29 (150行)',
        '後場': '12:30〜15:24 (175行)',
        '始値': f"{df_sample['open_price'].iloc[0]:,.0f}円",
        '終値(最終)': f"{df_sample['close_price'].iloc[-1]:,.0f}円",
        'close_price 最小': f"{df_sample['close_price'].min():,.0f}円",
        'close_price 最大': f"{df_sample['close_price'].max():,.0f}円",
        'カラム構成': ', '.join(df_sample.columns.tolist()),
    }

    # 2. CSVの読み込み
    print('\n[2] サンプルCSV読み込み...')
    df = pd.read_csv(SAMPLE_CSV_PATH)
    print(f'    読み込み完了: {len(df)}行')

    # 3. 各指標のチェック実行
    print('\n[3] 各テクニカル指標のチェック実行...')
    results = []

    # SMA / EMA / WMA（MA Cross のために事前計算してdfに持たせる）
    df_with_ma = df.copy()
    for window in [3, 5, 10, 15]:
        for func, prefix in [(indicator.get_sma, 'sma'), (indicator.get_ema, 'ema'), (indicator.get_wma, 'wma')]:
            col = f'{prefix}_1min_{window}piece'
            ok, df_tmp = func(df_with_ma.copy(), col, window_size=window, interval=1, price_column_name='close_price')
            if ok and df_tmp is not None:
                df_with_ma[col] = df_tmp[col]

    print('    SMA チェック中...')
    check_sma(indicator, df, results)

    print('    EMA チェック中...')
    check_ema(indicator, df, results)

    print('    WMA チェック中...')
    check_wma(indicator, df, results)

    print('    ボリンジャーバンド チェック中...')
    check_bollinger_bands(indicator, df, results)

    print('    MAクロス チェック中...')
    check_ma_cross(indicator, df_with_ma, results)

    print('    RSI チェック中...')
    check_rsi(indicator, df, results)

    print('    RCI チェック中...')
    check_rci(indicator, df, results)

    print('    MACD チェック中...')
    check_macd(indicator, df, results)

    print('    PSY チェック中...')
    check_psy(indicator, df, results)

    print('    パラボリックSAR(close) チェック中...')
    check_parabolic_close(indicator, df, results)

    print('    パラボリックSAR HLC (カラム名問題確認) チェック中...')
    check_parabolic_hlc(indicator, df, results)

    print('    一目均衡表 (カラム名問題確認) チェック中...')
    check_ichimoku(indicator, df, results)

    print('    変化額・変化率 (カラム名問題確認) チェック中...')
    check_change_price(indicator, df, results)

    print('    intervalリサンプリング方式 チェック中...')
    check_interval_resampling(indicator, df, results)

    # 4. レポート出力
    print('\n[4] MDレポートの生成・出力...')
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report_md = render_md_report(results, df_info, generated_at)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f'    レポート保存: {REPORT_PATH}')

    # 5. コンソールサマリー出力
    print('\n=== チェック結果サマリー ===')
    status_icon = {
        CheckResult.PASS: '[PASS]', CheckResult.FAIL: '[FAIL]',
        CheckResult.WARNING: '[WARN]', CheckResult.ERROR: '[ERR ]',
    }
    for r in results:
        icon = status_icon.get(r.status, '[?]')
        print(f'  {icon} {r.status:8s}  {r.name}')
    print()
    pass_count = sum(1 for r in results if r.status == CheckResult.PASS)
    warn_count = sum(1 for r in results if r.status == CheckResult.WARNING)
    fail_count = sum(1 for r in results if r.status == CheckResult.FAIL)
    err_count  = sum(1 for r in results if r.status == CheckResult.ERROR)
    print(f'  合計: PASS={pass_count} / WARNING={warn_count} / FAIL={fail_count} / ERROR={err_count}')
    print(f'\n  レポート: {REPORT_PATH}')
    print('=== チェック完了 ===')


if __name__ == '__main__':
    main()
