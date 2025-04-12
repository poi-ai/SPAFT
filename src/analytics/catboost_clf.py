import columns_manage as cm
import os
import pandas as pd
import re
import sys
import time
from catboost import CatBoostClassifier, Pool
from plyer import notification
from sklearn.metrics import log_loss, accuracy_score

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from util.log import Log

log = Log()

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_202502\d{2}.csv', csv_file)]

csv_counter = 0

# 最後のデータはテストデータとして使用するので分割
train_csv_names = csv_files[:-1]
test_csv_name = csv_files[-1]

for minute in [1, 2, 3, 5, 10, 15, 30, 60, 90]:

    # x分後の数値予測を行う

    #### 目的変数 ####
    target_column = f'change_{minute}min_flag'

    log.info(f'目的変数: {target_column}')

    # 学習済みのモデルがあるか
    model = CatBoostClassifier(iterations = 60, learning_rate = 0.07, depth = 4, loss_function = 'Logloss', verbose = 0, l2_leaf_reg = 1.2)
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
        X_train = train_df.drop(cm.cant_use_columns, axis=1)
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
        y_train_pred_proba = model.predict_proba(train_pool)[:, 1]  # クラス1の確率を取得
        y_train_pred = (y_train_pred_proba > 0.5).astype(int)  # 確率を閾値0.5でクラスに変換

        # 訓練データの評価
        train_logloss = round(log_loss(y_train, y_train_pred_proba), 4)  # Loglossを計算
        train_accuracy = round(accuracy_score(y_train, y_train_pred), 4)
        log.info(f'学習データ: {train_csv_name} 残りファイル数: {len(train_csv_names) - index - 1} Train Logloss: {train_logloss} Train Accuracy: {train_accuracy}')

        # 予測結果と実際の値を出力
        #csv_counter += 1
        #result_df = pd.DataFrame({'y_train': y_train, 'y_train_pred': y_train_pred})
        #result_df.to_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', f'error_catboost_{minute}min_{csv_counter}.csv'), index=False)

        if train_accuracy < 0.45:
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
    X_test = test_df.drop(cm.cant_use_columns, axis=1)
    y_test = test_df[target_column]

    # stock_codeをカテゴリ型に変換
    X_test['stock_code'] = X_test['stock_code'].astype('category')

    # CatBoost用のデータセットを作成
    test_pool = Pool(X_test, y_test, cat_features=['stock_code'])

    # テストデータで予測
    y_test_pred_proba = model.predict_proba(test_pool)[:, 1]  # クラス1の確率を取得
    y_test_pred = (y_test_pred_proba > 0.5).astype(int)  # 確率を閾値0.5でクラスに変換

    # テストデータの評価
    test_logloss = round(log_loss(y_test, y_test_pred_proba), 4)  # Loglossを計算
    test_accuracy = round(accuracy_score(y_test, y_test_pred), 4)
    log.info(f'学習データ: {test_csv_name} 残りファイル数: {len(test_csv_name) - index - 1} Test Logloss: {test_logloss} Test Accuracy: {test_accuracy}')

    # 特徴量の重要度
    feature_importance = model.get_feature_importance(train_pool)
    feature_name = X_train.columns
    importance_list = []
    for score, name in sorted(zip(feature_importance, feature_name), reverse=True):
        importance_list.append({'name': name, 'score': round(score, 2)})

    # 重要度を出力
    for importance in importance_list:
        log.info(importance)

    # 予測結果と実際の値を出力
    #result_df = pd.DataFrame({'y_test': y_test, 'y_pred': y_pred})
    #result_df.to_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'result', f'catboost_{minute}min.csv'), index=False)

    # 構築したモデルの出力
    #model.save_model(os.path.join(os.path.dirname(__file__), '..', '..', 'model', f'catboost_{minute}min.cbm'))

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