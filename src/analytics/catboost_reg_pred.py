import os
import pandas as pd
import columns_manage as cm
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
    X_test = test_df.drop(cm.cant_use_columns, axis=1)
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

