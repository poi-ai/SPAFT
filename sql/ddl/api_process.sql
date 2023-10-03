-- APIのプロセス管理
CREATE TABLE api_process (
    name VARCHAR(255) NOT NULL COMMENT 'API／プロセス名',
    status VARCHAR(1) COMMENT 'ステータス',
    api_exec_time DATETIME COMMENT 'API最終実行時間',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード追加時間',
    update_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新日時',
    PRIMARY KEY (name, api_exec_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;