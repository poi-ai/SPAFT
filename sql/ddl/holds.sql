-- 保有中の株の情報を管理するテーブル
CREATE TABLE holds (
    id VARCHAR(25) NOT NULL COMMENT '建玉ID',
    symbol VARCHAR(4) NOT NULL COMMENT '証券コード',
    exchange VARCHAR(1) NOT NULL COMMENT '市場コード 1: 東証、3: 名証、5: 福証、6: 札証',
    leaves_qty INT UNSIGNED NOT NULL COMMENT '保有株数(返済注文中株数含む)',
    free_qty INT UNSIGNED NOT NULL COMMENT '注文可能株数',
    price FLOAT(7,1) NOT NULL COMMENT '平均約定価格',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'レコード更新時間'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;