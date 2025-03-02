import os
import pandas as pd
import re
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# データ格納フォルダからformatted_ohlc_{date}.csvに合致するCSVファイル名のみ取得する
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv', 'past_ohlc', 'formatted')
csv_files = [csv_file for csv_file in os.listdir(data_dir) if re.fullmatch(r'formatted_ohlc_\d{8}.csv', csv_file)]

# 最後のデータはテストデータとして使用するので分割
train_csv_names = csv_files[:-1]
test_csv_name = csv_files[-1]

# NaN値を含む行を削除
# df = df.dropna(subset=df.columns)

# 3分後の二値分類を行う

#### 目的変数 ####
target_column = 'change_3min_flag'

#### 関連のないカラム ####
not_related_columns = ['timestamp', 'date', 'minute', 'get_minute']

#### リークを起こすカラム ####
leak_columns = ['change_1min_price', 'change_1min_rate', 'change_1min_flag',
                'change_2min_price', 'change_2min_rate', 'change_2min_flag',
                'change_3min_price', 'change_3min_rate',
                'change_5min_price', 'change_5min_rate', 'change_5min_flag',
                'change_10min_price', 'change_10min_rate', 'change_10min_flag',
                'change_15min_price', 'change_15min_rate', 'change_15min_flag',
                'change_30min_price', 'change_30min_rate', 'change_30min_flag',
                'change_60min_price', 'change_60min_rate', 'change_60min_flag',
                'change_90min_price', 'change_90min_rate', 'change_90min_flag'
]

#### 説明変数として使えないカラム
cant_use_columns = not_related_columns + leak_columns + [target_column]


# 学習済みのモデルがあるか
model = CatBoostClassifier(iterations=30, learning_rate=0.1, depth=6, loss_function='Logloss', verbose=10)
model_flag = False

for index, train_csv_name in enumerate(train_csv_names):
    print(f'学習データ: {train_csv_name} 残りファイル数: {len(train_csv_names) - index - 1}')
    # メモリ開放
    train_df = None
    # 訓練用データの読み込み
    train_df = pd.read_csv(os.path.join(data_dir, train_csv_name))

    # 9:30以前と15:00以降のデータを削除
    train_df = train_df[30:-25]

    print('Under sampling')
    print(f'0 record count: {len(train_df[train_df[target_column] == 0])}')
    print(f'1 record count: {len(train_df[train_df[target_column] == 1])}')

    # データのバランスを取るためにアンダーサンプリングを行う
    df_0 = train_df[train_df[target_column] == 0]
    df_1 = train_df[train_df[target_column] == 1]

    # 0のデータを1のデータの数に合わせてサンプリング
    df_0_under = df_0.sample(len(df_1), random_state=42)

    # サンプリングしたデータを結合
    df_balanced = pd.concat([df_0_under, df_1])

    # 特徴量と目的変数に分割
    X_train = df_balanced.drop(cant_use_columns, axis=1)
    y_train = df_balanced[target_column]

    # stock_codeはカテゴリ変数なので、文字列型に変換
    X_train.loc[:, 'stock_code'] = X_train['stock_code'].astype(str)

    # 訓練データとテストデータに分割
    #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

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
    y_train_pred_proba = model.predict_proba(train_pool)[:, 1]

    # 確率がX%を超えた場合のみ予測結果を出力
    y_train_pred_filtered = (y_train_pred_proba >= 0.6).astype(int)

    # フィルターあり
    # 訓練データの評価
    print('Train Accuracy:', round(accuracy_score(y_train, y_train_pred_filtered), 2))
    print('Train Precision:', round(precision_score(y_train, y_train_pred_filtered), 2))
    print('Train Recall:', round(recall_score(y_train, y_train_pred_filtered), 2))
    print('Train F1:', round(f1_score(y_train, y_train_pred_filtered), 2))

    print()
    print()




#### テストデータでの予測

# テスト用データの読み込み
test_df = pd.read_csv(os.path.join(data_dir, test_csv_name))

# 9:30以前と15:00以降のデータを削除
test_df = test_df[30:-25]

# 特徴量と目的変数に分割
X_test = test_df.drop(cant_use_columns, axis=1)
y_test = test_df[target_column]

# stock_codeはカテゴリ変数なので、文字列型に変換
X_test.loc[:, 'stock_code'] = X_test['stock_code'].astype(str)

# 訓練データとテストデータに分割
#X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# CatBoost用のデータセットを作成
test_pool = Pool(X_test, y_test, cat_features=['stock_code'])

# テストデータで予測 フィルターなしはここまで
y_pred = model.predict(test_pool)
y_pred_proba = model.predict_proba(test_pool)[:, 1]

# 確率がX%を超えた場合のみ予測結果を出力 フィルターあり
y_pred_filtered = (y_pred_proba >= 0.6).astype(int)

# テストデータの評価
print('Test Accuracy:', round(accuracy_score(y_test, y_pred_filtered), 2))
print('Test Precision:', round(precision_score(y_test, y_pred_filtered), 2))
print('Test Recall:', round(recall_score(y_test, y_pred_filtered), 2))
print('Test F1:', round(f1_score(y_test, y_pred_filtered), 2))

print()
print()

# 特徴量の重要度
feature_importance = model.get_feature_importance(train_pool)
feature_name = X_train.columns
importance_list = []
for score, name in sorted(zip(feature_importance, feature_name), reverse=True):
    importance_list.append({'name': name, 'score': score})

# 重要度を降順にソートして上位10件を表示
importance_list = sorted(importance_list, key=lambda x: x['score'], reverse=True)
for i in range(10):
    print(importance_list[i])


# 特徴量の重要度を可視化
#import matplotlib.pyplot as plt
#import seaborn as sns
#sns.barplot(x=feature_importance, y=feature_name)
#plt.show()
