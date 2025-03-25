import custom_loss as cl
import columns_manage as cm
import os
import pandas as pd
import re
import time
import sys
from catboost import CatBoostRegressor, Pool
from datetime import datetime
from plyer import notification
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score
from bayes_opt import BayesianOptimization

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from util.log import Log

log = Log()

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_20250\d{3}.csv', csv_file)]

# どの程度のデータサイズまでメモリが耐えられるかの確認
enable_file_num = 0
log.info('結合可能ファイル数チェック開始')
try:
    log.info(f'チェックCSVファイル {csv_files[0]} ファイル数: {enable_file_num + 1}')
    check_df = pd.read_csv(os.path.join(data_dir, csv_files[0]))
    enable_file_num += 1
except Exception as e:
    log.info(e)
    log.info('first csv file read error')
    exit()

for csv_name in csv_files[1:]:
    try:
        log.info(f'チェックCSVファイル {csv_name} ファイル数: {enable_file_num + 1}')
        check_df = pd.concat([check_df, pd.read_csv(os.path.join(data_dir, csv_name))], ignore_index=True)
        enable_file_num += 1
    except Exception as e:
        log.info(e)
        log.info(f'csv file read error. file count: {enable_file_num}')
        break

# 余裕をもって可能なファイル数-1にする
enable_file_num -= 1
log.info(f'結合可能ファイル数: {enable_file_num}')

# メモリ開放
check_df = None

# 最後のデータはテストデータとして使用するので分割 軽量化のためデータ量は5日分で
train_csv_names = csv_files[:-1]
test_csv_name = csv_files[-1]
output_count = 0

def catboost_cv(iterations, learning_rate, depth, l2_leaf_reg):
    log.info(datetime.now())
    log.info(f'パラメータ iterations: {int(iterations)}, learning_rate: {round(learning_rate, 3)}, depth: {int(depth)}, l2_leaf_reg: {round(l2_leaf_reg, 2)}')

    #### 目的変数 ####
    target_column = f'change_{minute_list[minute_index]}min_rate'

    log.info(f'目的変数: {target_column}')

    # 学習済みのモデルがあるか
    model = CatBoostRegressor(iterations = int(iterations),
                              learning_rate = learning_rate,
                              depth = int(depth),
                              loss_function = cl.RMSESignPenalty(),
                              eval_metric = 'RMSE',
                              verbose = 0,
                              l2_leaf_reg = l2_leaf_reg,
                              thread_count = -1, # CPUスレッドの最大利用
                              use_best_model = False, # 最良モデル記録の計算割愛
                              sampling_frequency = 'PerTree', # レベルごとのサンプリング→ツリーごとのサンプリング
                              border_count = 128 # カテゴリ変数なの分割数を行う デフォルト: 256
    )
    model_flag = False

    # 複数ファイルまとめて学習させる場合の管理用変数
    read_file_index = 0
    train_df = None

    for index, train_csv_name in enumerate(train_csv_names):

        read_error_count = 0

        # 訓練用データの読み込み
        while True:
            try:
                if read_file_index == 0:
                    train_df = pd.read_csv(os.path.join(data_dir, train_csv_name))
                else:
                    train_df = pd.concat([train_df, pd.read_csv(os.path.join(data_dir, train_csv_name))], ignore_index=True)
                read_file_index += 1
                break
            except Exception as e:
                log.info(e)
                log.info('Retry reading csv file')
                read_error_count += 1
                if read_error_count > 5:
                    log.info('Retry count over 5')
                    break
                time.sleep(3)

        # 9:30以前と15:00以降のデータを削除
        train_df = train_df[30:-25]

        # NaN値を含む行を削除
        train_df = train_df.dropna(subset=[target_column])

        # メモリギリギリのデータ数に達していないか、最後のデータでない場合は次のファイルへ
        if read_file_index < enable_file_num and index < len(train_csv_names) - 1:
            log.info(f'学習データ: {train_csv_name} 残りファイル数: {len(train_csv_names) - index - 1} 残り結合数: {enable_file_num - read_file_index}')
            continue

        # 特徴量と目的変数に分割
        X_train = train_df.drop(cm.cant_use_columns, axis=1)
        y_train = train_df[target_column]

        # stock_codeはカテゴリ変数なので、文字列型に変換
        X_train['stock_code'] = X_train['stock_code'].astype('category')

        # CatBoost用のデータセットを作成
        train_pool = Pool(X_train, y_train, cat_features=['stock_code'])

        log.info(f'モデル作成開始: {datetime.now()}')
        # モデルの作成
        if model_flag:
            model.fit(train_pool, init_model = model)
        else:
            model.fit(train_pool)
            model_flag = True
        log.info(f'モデル作成終了: {datetime.now()}')

        # 訓練データで予測
        y_train_pred = model.predict(train_pool)

        # 訓練データの評価
        train_rmse = round(root_mean_squared_error(y_train, y_train_pred), 2)
        log.info(f'学習データ: {train_csv_name} 残りファイル数: {len(train_csv_names) - index - 1} Train RMSE: {train_rmse} Train RMSE(Sign diff Pena): {round(cl.evaluation_rmse_sign_penalty(y_train.values, y_train_pred), 2)}')

        # RMSEが1万以上の場合は継続学習を行ってもよくならないと判断してこの時点で学習を打ち切る
        if train_rmse > 10000:
            break

        # メモリ開放
        train_df = None
        read_file_index = 0

        #print('Train MAE:', round(mean_absolute_error(y_train, y_train_pred), 2))
        #print('Train R2:', round(r2_score(y_train, y_train_pred), 2))

        #print()
        #print()

    #### テストデータでの予測

    while True:
        try:
            test_df = pd.read_csv(os.path.join(data_dir, test_csv_name))
            break
        except Exception as e:
            log.info(e)
            log.info('Retry reading csv file')
            time.sleep(10)

    # 9:30以前と15:00以降のデータを削除
    test_df = test_df[30:-25]

    # NaN値を含む行を削除
    test_df = test_df.dropna(subset=[target_column])

    # 特徴量と目的変数に分割
    X_test = test_df.drop(cm.cant_use_columns, axis=1)
    y_test = test_df[target_column]

    # stock_codeはカテゴリ変数なので、文字列型に変換
    X_test['stock_code'] = X_test['stock_code'].astype('category')

    # CatBoost用のデータセットを作成
    test_pool = Pool(X_test, y_test, cat_features=['stock_code'])

    # テストデータで予測
    y_pred = model.predict(test_pool)

    # テストデータの評価
    custom_rmse = cl.evaluation_rmse_sign_penalty(y_test.values, y_pred)
    log.info(f'テストデータ: {test_csv_name} Test RMSE: {round(root_mean_squared_error(y_test, y_pred), 2)} Test RMSE(Sign diff Pena): {round(custom_rmse, 2)}')
    #print('Test MAE:', round(mean_absolute_error(y_test, y_pred), 2))
    #print('Test R2:', round(r2_score(y_test, y_pred), 2))

    # 予測結果と実際の値を出力
    output_count += 1
    log.info(f'出力回数: {output_count}')
    result_df = pd.DataFrame({'y_test': y_test, 'y_pred': y_pred.round(3)})
    result_df.to_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', f'catboost_{output_count}.csv'), index=False)

    return -custom_rmse

    #print()
    #print()

    '''
    # 特徴量の重要度
    feature_importance = model.get_feature_importance(train_pool)
    feature_name = X_train.columns
    importance_list = []
    for score, name in sorted(zip(feature_importance, feature_name), reverse=True):
        importance_list.append({'name': name, 'score': round(score, 2)})

    # 重要度を出力
    for importance in importance_list:
        print(importance)

    # 重要度を降順にソートして上位10件を表示
    importance_list = sorted(importance_list, key=lambda x: x['score'], reverse=True)
    for i in range(10):
        print(importance_list[i])

    # 特徴量の重要度を可視化
    #import matplotlib.pyplot as plt
    #import seaborn as sns
    #sns.barplot(x=feature_importance, y=feature_name)
    #plt.show()
    '''

minute_list = [15, 5, 3, 60, 90, 1, 2, 30, 10]
minute_index = 0

for i in range(len(minute_list)):
    minute_index = i
    log.info(f'{minute_list[minute_index]}分足の予測')

    # ベイズ最適化で探索を行う範囲
    pbounds = {
        'iterations': (500, 2000),
        'learning_rate': (0.005, 0.07),
        'depth': (6, 12),
        'l2_leaf_reg': (1.0, 20.0)
    }

    # ベイズ最適化のパラメータ設定
    optimizer = BayesianOptimization(
        f=catboost_cv,
        pbounds=pbounds,
        random_state=42
    )

    # ベイズ最適化の実行
    while True:
        try:
            optimizer.maximize(init_points=10, n_iter=30)
            break
        except Exception as e:
            log.info(e)
            log.info('Retry BayesianOptimization')
            time.sleep(10)

notification.notify(title='実行完了', message='スクリプトの実行が終了しました。', timeout=50)