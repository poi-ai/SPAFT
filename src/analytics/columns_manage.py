# 目的変数や説明変数(特徴量)の設定を行う

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
                'change_90min_price', 'change_90min_rate', 'change_90min_flag',
                'ichimoku_1min_lagging_span', 'ichimoku_1min_pl_diff', 'ichimoku_1min_pl_position',
                'ichimoku_1min_pl_cross', 'ichimoku_1min_pl_gc_after', 'ichimoku_1min_pl_dc_after',
                'ichimoku_3min_lagging_span', 'ichimoku_3min_pl_diff', 'ichimoku_3min_pl_position',
                'ichimoku_3min_pl_cross', 'ichimoku_3min_pl_gc_after', 'ichimoku_3min_pl_dc_after',
                'ichimoku_5min_lagging_span', 'ichimoku_5min_pl_diff', 'ichimoku_5min_pl_position',
                'ichimoku_5min_pl_cross', 'ichimoku_5min_pl_gc_after', 'ichimoku_5min_pl_dc_after'
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
#cant_use_columns = not_related_columns + leak_columns + low_related_columns
cant_use_columns = not_related_columns + leak_columns

