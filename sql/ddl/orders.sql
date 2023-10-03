-- 注文情報を管理するテーブル
CREATE TABLE orders (
    order_id VARCHAR(30) NOT NULL COMMENT '注文ID',
    reverse_order_id VARCHAR(30) DEFAULT NULL COMMENT '反対注文ID',
    stock_code VARCHAR(4) NOT NULL COMMENT '証券コード',
    order_price FLOAT(7,1) NOT NULL COMMENT '注文価格(成行は-1.0)',
    order_volume INT NOT NULL COMMENT '注文株数',
    transaction_price FLOAT(7,1) DEFAULT NULL COMMENT '平均約定価格',
    buy_sell VARCHAR(1) NOT NULL COMMENT '売買区分(1: 売、2: 買)',
    cash_margin VARCHAR(1) NOT NULL COMMENT '信用区分(1: 現物買、2: 現物売、3: 信用新規、4:信用返済)',
    margin_type VARCHAR(1) NOT NULL COMMENT '信用取引区分(0: 現物、1: 制度信用、2: 一般信用(長期)、3: 一般信用(デイトレ))',
    profit FLOAT(8, 1) DEFAULT NULL COMMENT '損益額(決済注文のみ、新規注文は0)',
    status VARCHAR(1) NOT NULL COMMENT '注文ステータス(0: 未約定(=注文中)、1: 約定済、2: 取消中、3: 取消済)',
    order_date DATETIME NOT NULL COMMENT '注文日時',
    transaction_date DATETIME DEFAULT NULL COMMENT '約定日時',
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新日時',
    PRIMARY KEY (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;