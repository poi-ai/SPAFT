'''
チャート描画スクリプト

config.py で設定した銘柄・日付・分足・テクニカル指標を組み合わせて
ローソク足チャートと出来高を描画する。

'''
import matplotlib.pyplot as plt
import mplfinance as mpf
import os
import sys
import traceback
import numpy as np
import pandas as pd
import config
import japanize_matplotlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import Base


class ChartViewer(Base):
    '''分足OHLCデータのチャート描画クラス'''

    # テクニカル指標の番号と名称
    INDICATOR_NAMES = {
        0: 'チャートのみ',
        1: 'SMA (単純移動平均)',
        2: 'EMA (指数移動平均)',
        3: 'WMA (加重移動平均)',
        4: 'ボリンジャーバンド',
        5: 'RSI',
        6: 'RCI',
        7: 'MACD',
    }

    # サブパネルに描画する指標番号と軸ラベル
    _PANEL_LABELS = {5: 'RSI', 6: 'RCI', 7: 'MACD'}

    def __init__(self):
        super().__init__(use_db=False, use_api=False)
        self._indicator = self.util.indicator
        self._stock_code = str(config.CHART_STOCK_CODE)
        self._date = str(config.CHART_DATE)
        self._interval = int(config.CHART_INTERVAL)
        self._indicator_type = int(config.CHART_INDICATOR)
        # リポジトリルート（src/ の一つ上）
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def main(self):
        '''メイン処理'''
        indicator_name = self.INDICATOR_NAMES.get(self._indicator_type, '不明')
        print(f'チャート描画処理開始')
        print(f'銘柄コード: {self._stock_code}  日付: {self._date}  {self._interval}分足  指標: {indicator_name}')

        # CSVの取得
        result, df = self._load_csv()
        if not result:
            return

        # テクニカル指標の計算
        result, df = self._calc_indicator(df)
        if not result:
            return

        # チャートの描画
        self._draw(df)

    # ------------------------------------------------------------------
    # CSV取得
    # ------------------------------------------------------------------

    def _load_csv(self):
        '''
        CSVファイルを取得する。
        対象の日付ディレクトリが存在しない場合は 7z アーカイブから展開する。

        ファイルパス:
            CSV : csv/ohlc/{date}/{date}_{code}_{interval}min.csv
            7z  : csv/ohlc/bak/{date}.7z

        Returns:
            result(bool): 処理結果
            df(pd.DataFrame or None): 読み込んだデータ
        '''
        csv_dir = os.path.join(self._repo_root, 'csv', 'ohlc', self._date)
        csv_path = os.path.join(
            csv_dir,
            f'{self._date}_{self._stock_code}_{self._interval}min.csv'
        )
        archive_path = os.path.join(
            self._repo_root, 'csv', 'ohlc', 'bak', f'{self._date}.7z'
        )

        # 日付ディレクトリが存在しない場合は 7z から展開
        if not os.path.isdir(csv_dir):
            if not os.path.isfile(archive_path):
                print(f'[ERROR] CSVファイルも 7z アーカイブも見つかりません')
                print(f'  対象CSV : {csv_path}')
                print(f'  対象7z  : {archive_path}')
                return False, None

            print(f'7z アーカイブを展開します: {archive_path}')
            extract_base = os.path.join(self._repo_root, 'csv', 'ohlc')
            result, error = self.util.file_manager.extract_7z_file(archive_path, extract_base)
            if not result:
                print(f'[ERROR] 7z 展開に失敗しました: {error}')
                return False, None

            # 日付ディレクトリが存在しない場合は作成して、CSVファイルを移動
            if not os.path.isdir(csv_dir):
                os.makedirs(csv_dir, exist_ok=True)
                # extract_base 直下のCSVファイルで、日付を含むものを date_dir に移動
                for filename in os.listdir(extract_base):
                    if filename.startswith(self._date) and filename.endswith('.csv'):
                        src = os.path.join(extract_base, filename)
                        dst = os.path.join(csv_dir, filename)
                        os.rename(src, dst)

            print(f'展開完了: {csv_dir}')

        # CSVの存在チェック
        if not os.path.isfile(csv_path):
            print(f'[ERROR] CSVファイルが見つかりません: {csv_path}')
            print(f'  銘柄コード・日付・分足の設定が正しいか確認してください')
            return False, None

        # CSV読み込み
        try:
            df = pd.read_csv(csv_path, parse_dates=['trade_time'])
        except Exception as e:
            print(f'[ERROR] CSV 読み込みでエラーが発生しました: {e}')
            print(traceback.format_exc())
            return False, None

        if df.empty:
            print(f'[ERROR] CSVファイルにデータがありません: {csv_path}')
            return False, None

        df = df.reset_index(drop=True)
        print(f'CSV 読み込み完了: {len(df)} 件')
        return True, df

    # ------------------------------------------------------------------
    # テクニカル指標の計算
    # ------------------------------------------------------------------

    def _calc_indicator(self, df):
        '''
        設定したテクニカル指標を計算し、df にカラムを追加する。
        CSVは既に目的の時間足で保存済みのため interval=1 で計算する。

        Args:
            df(pd.DataFrame): 読み込んだ OHLCデータ

        Returns:
            result(bool): 処理結果
            df(pd.DataFrame): 指標カラムを追加した DataFrame
        '''
        if self._indicator_type == 0:
            return True, df

        price_col = 'close_price'
        interval = 1

        try:
            if self._indicator_type == 1:
                # SMA (window=25)
                result, df = self._indicator.get_sma(df, 'sma', 25, interval, price_col)
                if not result:
                    print('[ERROR] SMA 計算に失敗しました')
                    return False, None
                # window 不足期間のセンチネル値(-1)を NaN に変換
                df['sma'] = df['sma'].replace(-1, np.nan)

            elif self._indicator_type == 2:
                # EMA (window=25)
                result, df = self._indicator.get_ema(df, 'ema', 25, interval, price_col)
                if not result:
                    print('[ERROR] EMA 計算に失敗しました')
                    return False, None
                df['ema'] = df['ema'].replace(-1, np.nan)

            elif self._indicator_type == 3:
                # WMA (window=25)
                result, df = self._indicator.get_wma(df, 'wma', 25, interval, price_col)
                if not result:
                    print('[ERROR] WMA 計算に失敗しました')
                    return False, None
                df['wma'] = df['wma'].replace(-1, np.nan)

            elif self._indicator_type == 4:
                # ボリンジャーバンド (window=20)
                result, df = self._indicator.get_bollinger_bands(
                    df, 'bb', 20, interval, price_col
                )
                if not result:
                    print('[ERROR] ボリンジャーバンド計算に失敗しました')
                    return False, None

            elif self._indicator_type == 5:
                # RSI (window=14)
                result, df = self._indicator.get_rsi(df, 'rsi', 14, interval, price_col)
                if not result:
                    print('[ERROR] RSI 計算に失敗しました')
                    return False, None

            elif self._indicator_type == 6:
                # RCI (window=9)
                result, df = self._indicator.get_rci(df, 'rci', 9, interval, price_col)
                if not result:
                    print('[ERROR] RCI 計算に失敗しました')
                    return False, None

            elif self._indicator_type == 7:
                # MACD (short=12, long=26, signal=9)
                result, df = self._indicator.get_macd(
                    df, 'macd', 12, 26, 9, interval, price_col
                )
                if not result:
                    print('[ERROR] MACD 計算に失敗しました')
                    return False, None

        except Exception as e:
            print(f'[ERROR] テクニカル指標の計算でエラーが発生しました: {e}')
            print(traceback.format_exc())
            return False, None

        return True, df

    # ------------------------------------------------------------------
    # チャート描画
    # ------------------------------------------------------------------

    def _draw(self, df):
        '''
        mplfinance でローソク足チャートを描画する。
        ・チャート・出来高は常に表示
        ・オーバーレイ系 (SMA/EMA/WMA/BB): メインチャートに重ねて描画
        ・サブパネル系 (RSI/RCI/MACD)    : 出来高の下にサブパネルを追加

        Args:
            df(pd.DataFrame): OHLCデータ（指標カラム含む）
        '''
        # mplfinance 用に整形（インデックスを DatetimeIndex に設定）
        df_plot = df.rename(columns={
            'open_price':  'Open',
            'high_price':  'High',
            'low_price':   'Low',
            'close_price': 'Close',
            'volume':      'Volume',
        }).copy()
        df_plot = df_plot.set_index('trade_time')
        df_plot.index = pd.DatetimeIndex(df_plot.index)

        # addplot の構築（df_plot のカラムを参照することで DatetimeIndex が一致）
        addplots = self._build_addplots(df_plot)

        # タイトル
        indicator_name = self.INDICATOR_NAMES.get(self._indicator_type, '')
        title = f'{self._stock_code}  {self._date}  {self._interval}min'
        if self._indicator_type != 0:
            title += f'  [{indicator_name}]'

        # フォントファイルを直接ロードして make_mpf_style の rc に組み込む
        # （plt.rcParams への直接設定は mpf スタイルに上書きされるため）
        import matplotlib.font_manager as fm
        jp_font_name = None
        for fp in fm.findSystemFonts():
            if any(fp.lower().endswith(c) for c in [
                'meiryo.ttc', 'meiryob.ttc',
                'yugothr.ttc', 'yugothm.ttc', 'yugothb.ttc',
                'msgothic.ttc', 'mspgothic.ttf',
            ]):
                fm.fontManager.addfont(fp)
                jp_font_name = fm.FontProperties(fname=fp).get_name()
                break

        style_rc = {'font.family': jp_font_name} if jp_font_name else {}
        style = mpf.make_mpf_style(base_mpf_style='yahoo', rc=style_rc)

        # OHLCV カラムのみに絞った DataFrame を渡す
        ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df_main = df_plot[[c for c in ohlcv_cols if c in df_plot.columns]]

        # 800x480px（dpi=100 基準）
        plot_kwargs = dict(
            type='candle',
            style=style,
            title=title,
            volume=True,
            figsize=(8, 4.8),
            datetime_format='%H:%M',
            show_nontrading=False,   # 昼休みを連続表示に
            # x軸左右のデータ余白を均等化（右寄り防止）
            scale_padding={'left': 0.02, 'top': 1.3, 'right': 0.02, 'bottom': 0.75},
            returnfig=True,
        )
        if addplots:
            plot_kwargs['addplot'] = addplots

        try:
            fig, axes = mpf.plot(df_main, **plot_kwargs)

            # サブパネル指標のy軸ラベルを設定
            # axes[0]: メインチャート, axes[1]: 出来高, axes[2]: サブパネル
            if self._indicator_type in self._PANEL_LABELS and len(axes) > 2:
                axes[2].set_ylabel(self._PANEL_LABELS[self._indicator_type])

            # subplots_adjust は mplfinance の GridSpec に無視されるため
            # 各 axes の Bbox を直接縮めて右側に y 軸ラベル用の余白を確保
            for ax in axes:
                bb = ax.get_position()
                ax.set_position([bb.x0, bb.y0, bb.width * 0.88, bb.height])

            plt.show()

        except Exception as e:
            print(f'[ERROR] チャート描画でエラーが発生しました: {e}')
            print(traceback.format_exc())

    def _build_addplots(self, df_plot):
        '''
        mplfinance の addplot リストを構築する。
        df_plot は DatetimeIndex 済みのため、返す Series も同じ Index を持つ。

        Args:
            df_plot(pd.DataFrame): DatetimeIndex 付きの OHLCデータ（指標カラム含む）

        Returns:
            addplots(list): mpf.make_addplot のリスト
        '''
        addplots = []
        t = self._indicator_type

        if t == 1 and 'sma' in df_plot.columns:
            addplots.append(
                mpf.make_addplot(df_plot['sma'], color='royalblue', width=1.2)
            )

        elif t == 2 and 'ema' in df_plot.columns:
            addplots.append(
                mpf.make_addplot(df_plot['ema'], color='darkorange', width=1.2)
            )

        elif t == 3 and 'wma' in df_plot.columns:
            addplots.append(
                mpf.make_addplot(df_plot['wma'], color='forestgreen', width=1.2)
            )

        elif t == 4:
            # ボリンジャーバンド ±1σ (青実線) / ±2σ (赤実線)
            for col, color in [
                ('bb_upper_2sigma', 'tomato'),
                ('bb_lower_2sigma', 'tomato'),
                ('bb_upper_1sigma', 'royalblue'),
                ('bb_lower_1sigma', 'royalblue'),
            ]:
                if col in df_plot.columns:
                    addplots.append(
                        mpf.make_addplot(
                            df_plot[col], color=color, width=0.8, linestyle='-'
                        )
                    )

        elif t == 5 and 'rsi' in df_plot.columns:
            # RSI サブパネル + 過買い(70) / 過売り(30) 水平線
            overbought = pd.Series(70.0, index=df_plot.index)
            oversold   = pd.Series(30.0, index=df_plot.index)
            addplots.extend([
                mpf.make_addplot(df_plot['rsi'], panel=2, color='purple',  width=1.2),
                mpf.make_addplot(overbought,     panel=2, color='tomato',  width=0.8, linestyle='--'),
                mpf.make_addplot(oversold,       panel=2, color='limegreen', width=0.8, linestyle='--'),
            ])

        elif t == 6 and 'rci' in df_plot.columns:
            # RCI サブパネル + +80 / -80 水平線
            upper = pd.Series( 80.0, index=df_plot.index)
            lower = pd.Series(-80.0, index=df_plot.index)
            addplots.extend([
                mpf.make_addplot(df_plot['rci'], panel=2, color='darkorange', width=1.2),
                mpf.make_addplot(upper,          panel=2, color='tomato',    width=0.8, linestyle='--'),
                mpf.make_addplot(lower,          panel=2, color='limegreen', width=0.8, linestyle='--'),
            ])

        elif t == 7:
            # MACD サブパネル: MACD 線・シグナル線・ヒストグラム (正=青/負=赤)
            if 'macd' in df_plot.columns and 'macd_signal' in df_plot.columns:
                hist = df_plot['macd_diff'].fillna(0) if 'macd_diff' in df_plot.columns \
                       else pd.Series(0.0, index=df_plot.index)
                hist_colors = [
                    'cornflowerblue' if v >= 0 else 'salmon' for v in hist
                ]
                addplots.extend([
                    mpf.make_addplot(df_plot['macd'],        panel=2, color='royalblue',  width=1.2),
                    mpf.make_addplot(df_plot['macd_signal'], panel=2, color='darkorange', width=1.0),
                    mpf.make_addplot(hist, panel=2, type='bar', color=hist_colors, alpha=0.5),
                ])

        return addplots

if __name__ == '__main__':
    viewer = ChartViewer()
    viewer.main()
