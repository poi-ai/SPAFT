CREATE TABLE ohlc (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
    symbol VARCHAR(20) NOT NULL COMMENT '証券コード',
    trade_time DATETIME NOT NULL COMMENT '取引日時',
    open_price FLOAT NOT NULL COMMENT '始値',
    high_price FLOAT NOT NULL COMMENT '高値',
    low_price FLOAT NOT NULL COMMENT '安値',
    close_price FLOAT NOT NULL COMMENT '終値',
    volume INT NOT NULL COMMENT '出来高',
    total_volume BIGINT NOT NULL COMMENT '累積出来高',
    status TINYINT NOT NULL DEFAULT 0 COMMENT 'ステータス',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'レコード更新日時',
    UNIQUE INDEX idx_symbol_datetime (symbol, trade_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
