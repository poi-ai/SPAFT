import custom_loss as cl
import os
import pandas as pd
import re
import sys
import time
from catboost import CatBoostRegressor, Pool
from plyer import notification
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from util.log import Log

log = Log()

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

csv_counter = 0

# 最後のデータはテストデータとして使用するので分割
train_csv_names = csv_files[:-1]
test_csv_name = csv_files[-1]

for minute in [1, 2, 3, 5, 10, 15, 30, 60, 90]:

    # x分後の数値予測を行う

    #### 目的変数 ####
    target_column = f'change_{minute}min_rate'

    log.info(f'目的変数: {target_column}')

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

    # 学習済みのモデルがあるか
    model = CatBoostRegressor(iterations = 60, learning_rate = 0.07, depth = 4, loss_function = cl.RMSESignPenalty(), eval_metric = 'RMSE', verbose = 0, l2_leaf_reg = 1.2)
    model_flag = False

    for index, train_csv_name in enumerate(train_csv_names):
        # メモリ開放
        train_df = None

        # 訓練用データの読み込み
        while True:
            try:
                train_df = pd.read_csv(os.path.join(data_dir, train_csv_name))
                break
            except Exception as e:
                log.error(e)
                log.error('Retry reading csv file')
                time.sleep(10)

        # 9:30以前と15:00以降のデータを削除
        train_df = train_df[30:-25]

        # NaN値を含む行を削除
        train_df = train_df.dropna(subset=[target_column])

        # 特徴量と目的変数に分割
        X_train = train_df.drop(cant_use_columns, axis=1)
        y_train = train_df[target_column]

        # stock_codeをカテゴリ型に変換
        X_train['stock_code'] = X_train['stock_code'].astype('category')

        # CatBoost用のデータセットを作成
        train_pool = Pool(X_train, y_train, cat_features=['stock_code'])

        # モデルの作成
        if model_flag:
            model.fit(train_pool, init_model = model)
        else:
            model.fit(train_pool)
            model_flag = True

        # 訓練データで予測
        y_train_pred = model.predict(train_pool)

        # 訓練データの評価
        train_rmse = round(root_mean_squared_error(y_train, y_train_pred), 2)
        log.info(f'学習データ: {train_csv_name} 残りファイル数: {len(train_csv_names) - index - 1} Train RMSE: {train_rmse} Train RMSE(Sign diff Pena): {round(cl.evaluation_rmse_sign_penalty(y_train.values, y_train_pred), 2)}')

        # 予測結果と実際の値を出力
        csv_counter += 1
        result_df = pd.DataFrame({'y_train': y_train, 'y_train_pred': y_train_pred})
        result_df.to_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', f'error_catboost_{minute}min_{csv_counter}.csv'), index=False)

        if train_rmse > 5000:
            log.info('精度が悪すぎるので強制終了します')
            break

        #log.info('Train MAE:', round(mean_absolute_error(y_train, y_train_pred), 2))
        #log.info('Train R2:', round(r2_score(y_train, y_train_pred), 2))

    #### テストデータでの予測

    # テスト用データの読み込み
    log.info(f'テストデータ: {test_csv_name}')

    while True:
        try:
            test_df = pd.read_csv(os.path.join(data_dir, test_csv_name))
            break
        except Exception as e:
            log.error(e)
            log.error('Retry reading csv file')
            time.sleep(10)

    # 9:30以前と15:00以降のデータを削除
    test_df = test_df[30:-25]

    # NaN値を含む行を削除
    test_df = test_df.dropna(subset=[target_column])

    # 特徴量と目的変数に分割
    X_test = test_df.drop(cant_use_columns, axis=1)
    y_test = test_df[target_column]

    # stock_codeをカテゴリ型に変換
    X_test['stock_code'] = X_test['stock_code'].astype('category')

    # CatBoost用のデータセットを作成
    test_pool = Pool(X_test, y_test, cat_features=['stock_code'])

    # テストデータで予測
    y_pred = model.predict(test_pool)

    # テストデータの評価
    custom_rmse = cl.evaluation_rmse_sign_penalty(y_test.values, y_pred)
    log.info(f'テストデータ: {test_csv_name} Test RMSE: {round(root_mean_squared_error(y_test, y_pred), 2)} Test RMSE(Sign diff Pena): {round(custom_rmse, 2)}')
    #log.info('Test MAE:', round(mean_absolute_error(y_test, y_pred), 2))
    #log.info('Test R2:', round(r2_score(y_test, y_pred), 2))

    # 特徴量の重要度
    feature_importance = model.get_feature_importance(train_pool)
    feature_name = X_train.columns
    importance_list = []
    for score, name in sorted(zip(feature_importance, feature_name), reverse=True):
        importance_list.append({'name': name, 'score': round(score, 2)})

    # 重要度を出力
    #for importance in importance_list:
    #    self.log(importance)

    # 予測結果と実際の値を出力
    #result_df = pd.DataFrame({'y_test': y_test, 'y_pred': y_pred})
    #result_df.to_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', f'catboost_{minute}min.csv'), index=False)

    # 構築したモデルの出力
    model.save_model(os.path.join(os.path.dirname(__file__), '..', '..', 'model', f'catboost_{minute}min.cbm'))

## 重要度を降順にソートして上位10件を表示
#importance_list = sorted(importance_list, key=lambda x: x['score'], reverse=True)
#for i in range(10):
#    self.log(importance_list[i])

# 特徴量の重要度を可視化
#import matplotlib.pyplot as plt
#import seaborn as sns
#sns.barplot(x=feature_importance, y=feature_name)
#plt.show()

notification.notify(title='実行完了', message='スクリプトの実行が終了しました。', timeout=50)