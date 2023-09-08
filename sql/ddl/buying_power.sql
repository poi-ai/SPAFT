-- 余力情報を管理するテーブル
CREATE TABLE buying_power (
    id INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    total_assets INT NOT NULL COMMENT '総資産(購入額ベース)',
    total_margin INT NOT NULL COMMENT '信用保有額合計(購入額ベース)',
    api_flag VARCHAR(1) NOT NULL DEFAULT '0' COMMENT 'API取得フラグ、(1: APIから取得、0: DBのデータから計算)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'データ作成日時',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;