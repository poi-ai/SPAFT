-- 上場している企業のデータを管理するテーブル
CREATE TABLE listed (
    stock_code INT NOT NULL COMMENT '証券コード',
    market_code VARCHAR(1) NOT NULL COMMENT '市場コード (1: 東証、3: 名証、5: 福証、6: 札証)',
    listed_flg VARCHAR(1) NOT NULL DEFAULT '0' COMMENT '上場中フラグ',
    update_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新日時',
    PRIMARY KEY (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;