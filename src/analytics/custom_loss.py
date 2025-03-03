import numpy as np
from catboost import CatBoostRegressor

class RMSESignPenalty:
    def calc_ders_range(self, approxes, targets, weights):
        '''
        回帰予測において、正を負/負を正と予測した場合に実際のズレの4倍のペナルティを与えるカスタム損失関数
        ベースはRMSEで、符号違いの場合のみカスタムのペナルティを適用
        ※ CatBoostRegressorライブラリから呼ばれるため、メソッド名を変えてはいけない

        Args:
            approxes(np.ndarray): 予測値のリスト（logit ではない）
            targets(np.ndarray): 実測値のリスト
            weights(np.ndarray): サンプルの重み（None の場合もあり）

        Returns
            list: [(勾配, ヘッセ行列)] のリスト
        '''
        result = []
        for approx, target in zip(approxes, targets):
            error = approx - target
            # 符号が異なる場合にのみペナルティを4倍にする(RMSEのデフォルトの勾配は2、1にすると学習打ち切りになる)
            penalty_factor = 20.0 if (approx * target < 0) else 2.0

            grad = penalty_factor * error  # 勾配（1次微分）
            hess = penalty_factor  # ヘッセ行列（2次微分）

            result.append((grad, hess))
        return result

def evaluation_rmse_sign_penalty(y_true, y_pred):
    '''
    RMSESignPenaltyで構築したモデルの評価関数
    ベースはRMSEで、符号が異なる場合にのみペナルティを4倍にする

    Args:
        y_true(np.ndarray): 実測値
        y_pred(np.ndarray): 予測値

    Returns:
        float: カスタムペナルティを適用したRMSE
    '''
    errors = y_pred - y_true
    penalty_factors = np.where(y_true * y_pred < 0, 10.0, 1.0)  # 符号が違う場合は4倍
    weighted_errors = penalty_factors * (errors ** 2)  # RMSE の二乗誤差を修正
    return np.sqrt(np.mean(weighted_errors))  # RMSE に変換
