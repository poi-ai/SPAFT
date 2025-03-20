import os
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score

# テストデータのCSVファイル名
test_csv_name = 'formatted_ohlc_20250228.csv'

# 学習済モデルと予測を行うファイルの保管ディレクトリのパス
model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'model')
pred_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prediction')
test_data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')

# 1分足~90分足での予測を行う
for minute in [1, 2, 3, 5, 10, 15, 30, 60, 90]:
    # 学習済モデルの読み込み
    model = CatBoostRegressor()
    model.load_model(os.path.join(model_dir, f'catboost_{minute}min.cbm'))

    #### 関連のないカラム ####
    not_related_columns = ['timestamp', 'date', 'minute', 'get_minute']

    #### リークを起こすカラム ####
    leak_columns = ['change_1min_price', 'change_1min_rate', 'change_1min_flag',
                    'change_2min_price', 'change_2min_rate', 'change_2min_flag',
                    'change_3min_price', 'change_3min_rate', 'change_3min_flag',
                    'change_5min_price', 'change_5min_rate', 'change_5min_flag',
                    'change_10min_price', 'change_10min_rate', 'change_10min_flag',
                    'change_15min_price', 'change_15min_rate', 'change_15min_flag',
                    'change_30min_price', 'change_30min_rate', 'change_30min_flag',
                    'change_60min_price', 'change_60min_rate', 'change_60min_flag',
                    'change_90min_price', 'change_90min_rate', 'change_90min_flag'
    ]

    ### 重要度の低かったカラム
    low_related_columns = [
        'ema_10min_10to15piece_dead_cross', 'ema_10min_3to10piece_dead_cross', 'ema_10min_3to10piece_golden_cross',
        'ema_10min_3to15piece_dead_cross', 'ema_10min_3to15piece_golden_cross', 'ema_10min_3to5piece_golden_cross',
        'ema_10min_5to10piece_dead_cross', 'ema_10min_5to15piece_dead_cross', 'ema_15min_3to10piece_dead_cross',
        'ema_15min_3to10piece_golden_cross', 'ema_15min_3to5piece_dead_cross', 'ema_15min_5to10piece_dead_cross',
        'ema_1min_10to15piece_dead_cross', 'ema_1min_10to15piece_golden_cross', 'ema_1min_3to10piece_dead_cross',
        'ema_1min_3to10piece_golden_cross', 'ema_1min_3to15piece_dead_cross', 'ema_1min_3to15piece_golden_cross',
        'ema_1min_3to5piece_dead_cross', 'ema_1min_3to5piece_golden_cross', 'ema_1min_5to10piece_dead_cross',
        'ema_1min_5to10piece_golden_cross', 'ema_1min_5to15piece_dead_cross', 'ema_1min_5to15piece_golden_cross',
        'ema_30min_3to5piece_golden_cross', 'ema_3min_10to15piece_dead_cross', 'ema_3min_3to10piece_golden_cross',
        'ema_3min_3to15piece_dead_cross', 'ema_3min_3to15piece_golden_cross', 'ema_3min_3to5piece_dead_cross',
        'ema_3min_3to5piece_golden_cross', 'ema_3min_5to10piece_dead_cross', 'ema_3min_5to10piece_golden_cross',
        'ema_3min_5to15piece_dead_cross', 'ema_3min_5to15piece_golden_cross', 'ema_5min_10to15piece_dead_cross',
        'ema_5min_3to10piece_golden_cross', 'ema_5min_3to15piece_dead_cross', 'ema_5min_3to15piece_golden_cross',
        'ema_5min_3to5piece_dead_cross', 'ema_5min_5to10piece_dead_cross', 'ema_5min_5to15piece_dead_cross',
        'ema_5min_5to15piece_golden_cross', 'ichimoku_1min_bc_cross', 'ichimoku_1min_ls_cross', 'ichimoku_1min_ls_position',
        'ichimoku_3min_bc_cross', 'ichimoku_5min_bc_cross', 'ichimoku_5min_bc_position', 'ichimoku_5min_cloud_cross',
        'ichimoku_5min_cloud_high_diff', 'ichimoku_5min_cloud_low_diff', 'ichimoku_5min_cloud_position',
        'ichimoku_5min_leading_span_b', 'ichimoku_5min_ls_cross', 'ichimoku_5min_ls_diff', 'ichimoku_5min_ls_position',
        'macd_10min_diff_flag', 'macd_10min_mismatch', 'macd_15min_diff_flag', 'macd_15min_mismatch', 'macd_1min_mismatch',
        'macd_30min_diff_flag', 'macd_3min_cross', 'macd_3min_mismatch', 'macd_5min_mismatch', 'macd_60min_diff_flag',
        'sar_10min_0.01_0.1af_flag', 'sar_10min_0.02_0.2af_flag', 'sar_10min_0.05_0.5af_flag', 'sar_10min_0.05_0.5af_reverse_flag',
        'sar_10min_0.1_1af_flag', 'sar_15min_0.01_0.1af_flag', 'sar_15min_0.01_0.1af_reverse_flag', 'sar_15min_0.02_0.2af_flag',
        'sar_15min_0.05_0.5af_flag', 'sar_15min_0.05_0.5af_reverse_flag', 'sar_1min_0.02_0.2af_flag',
        'sar_1min_0.02_0.2af_reverse_flag', 'sar_30min_0.01_0.1af_reverse_flag', 'sar_30min_0.02_0.2af_flag',
        'sar_30min_0.02_0.2af_reverse_flag', 'sar_30min_0.05_0.5af_flag', 'sar_5min_0.01_0.1af_flag', 'sar_5min_0.1_1af_flag',
        'sar_60min_0.01_0.1af_flag', 'sar_60min_0.01_0.1af_reverse_flag', 'sar_60min_0.02_0.2af_flag',
        'sar_60min_0.02_0.2af_reverse_flag', 'sar_60min_0.05_0.5af_flag', 'sar_60min_0.05_0.5af_reverse_flag',
        'sar_60min_0.1_1af_flag', 'sar_60min_0.1_1af_reverse_flag', 'sma_10min_3to15piece_dead_cross',
        'sma_10min_3to5piece_dead_cross', 'sma_10min_3to5piece_golden_cross', 'sma_10min_5to10piece_dead_cross',
        'sma_10min_5to15piece_dead_cross', 'sma_15min_3to5piece_dead_cross', 'sma_15min_3to5piece_golden_cross',
        'sma_1min_10to15piece_dead_cross', 'sma_1min_10to15piece_golden_cross', 'sma_1min_3to10piece_dead_cross',
        'sma_1min_3to10piece_golden_cross', 'sma_1min_3to15piece_dead_cross', 'sma_1min_3to15piece_golden_cross',
        'sma_1min_3to5piece_dead_cross', 'sma_1min_3to5piece_golden_cross', 'sma_1min_5to10piece_dead_cross',
        'sma_1min_5to15piece_dead_cross', 'sma_30min_3to5piece_dead_cross', 'sma_3min_10to15piece_dead_cross',
        'sma_3min_10to15piece_golden_cross', 'sma_3min_3to10piece_dead_cross', 'sma_3min_3to10piece_golden_cross',
        'sma_3min_3to15piece_dead_cross', 'sma_3min_3to15piece_golden_cross', 'sma_3min_3to5piece_golden_cross',
        'sma_3min_5to10piece_dead_cross', 'sma_3min_5to10piece_golden_cross', 'sma_3min_5to15piece_dead_cross',
        'sma_5min_10to15piece_dead_cross', 'sma_5min_3to10piece_dead_cross', 'sma_5min_3to10piece_golden_cross',
        'sma_5min_3to15piece_dead_cross', 'sma_5min_3to5piece_dead_cross', 'sma_5min_5to10piece_golden_cross',
        'sma_5min_5to15piece_dead_cross', 'wma_10min_3to10piece_dead_cross', 'wma_10min_3to5piece_dead_cross',
        'wma_10min_3to5piece_golden_cross', 'wma_10min_5to10piece_dead_cross', 'wma_10min_5to15piece_dead_cross',
        'wma_1min_10to15piece_dead_cross', 'wma_1min_10to15piece_golden_cross', 'wma_1min_3to10piece_dead_cross',
        'wma_1min_3to15piece_dead_cross', 'wma_1min_3to15piece_golden_cross', 'wma_1min_3to5piece_dead_cross',
        'wma_1min_3to5piece_golden_cross', 'wma_1min_5to10piece_dead_cross', 'wma_1min_5to15piece_dead_cross',
        'wma_30min_3to5piece_dead_cross', 'wma_3min_10to15piece_dead_cross', 'wma_3min_10to15piece_golden_cross',
        'wma_3min_3to10piece_dead_cross', 'wma_3min_3to10piece_golden_cross', 'wma_3min_3to15piece_dead_cross',
        'wma_3min_3to15piece_golden_cross', 'wma_3min_3to5piece_golden_cross', 'wma_3min_5to10piece_dead_cross',
        'wma_3min_5to10piece_golden_cross', 'wma_3min_5to15piece_golden_cross', 'wma_5min_10to15piece_dead_cross',
        'wma_5min_3to10piece_dead_cross', 'wma_5min_3to15piece_dead_cross', 'wma_5min_3to15piece_golden_cross',
        'wma_5min_3to5piece_dead_cross', 'wma_5min_3to5piece_golden_cross', 'wma_5min_5to10piece_dead_cross',
        'wma_5min_5to10piece_golden_cross', 'wma_5min_5to15piece_dead_cross', 'wma_5min_5to15piece_golden_cross'
    ]

    #### 説明変数として使えないカラム
    cant_use_columns = not_related_columns + leak_columns + low_related_columns

    # 目的変数のカラム名
    target_column = f'change_{minute}min_rate'

    # 予測を行うデータの読み込み
    test_df = pd.read_csv(os.path.join(test_data_dir, test_csv_name))

    # timestampカラムをdatetime型に変換して、9:30以前と15:00以降のデータを削除
    test_df['timestamp'] = pd.to_datetime(test_df['timestamp'])
    test_df = test_df[(test_df['timestamp'].dt.time >= pd.to_datetime('09:30').time()) & (test_df['timestamp'].dt.time <= pd.to_datetime('15:00').time())]

    # NaN値を含む行を削除
    test_df = test_df.dropna(subset=[target_column])

    # 特徴量と目的変数に分割
    X_test = test_df.drop(cant_use_columns, axis=1)
    y_test = test_df[target_column]

    # stock_codeをカテゴリ型に変更
    X_test['stock_code'] = X_test['stock_code'].astype('category')

    # CatBoost用のデータセットを作成
    test_pool = Pool(X_test, y_test, cat_features=['stock_code'])

    # テストデータで予測
    y_pred = model.predict(test_pool)

    # 一部カラムのみを切り出して、予測値を結合する
    keep_columns = ['stock_code', 'timestamp', 'open', 'high', 'low', 'close', 'volume', f'change_{minute}min_flag', f'change_{minute}min_price', f'change_{minute}min_rate']
    test_df_result = test_df[keep_columns].copy()
    test_df_result[f'pred_change_{minute}min_rate'] = y_pred

    # 予測結果をCSVファイルに保存
    test_df_result.to_csv(os.path.join(pred_dir, f'pred_{minute}min.csv'), index=False)

    print(f'{minute}分足の予測結果')
    print(f'テストデータ: {test_csv_name} Test RMSE: {round(root_mean_squared_error(y_test, y_pred), 2)}')

