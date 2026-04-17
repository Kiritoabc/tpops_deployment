-- +goose Up
-- +goose StatementBegin
-- 轻量 SQLite 表结构；默认使用独立 DB 文件（data/tpops_go.db）。
-- 若改为复用已有数据库文件，请自行评估迁移与冲突风险。

CREATE TABLE IF NOT EXISTS auth_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME NULL,
    is_superuser INTEGER NOT NULL DEFAULT 0,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    date_joined DATETIME NOT NULL DEFAULT (datetime('now')),
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    last_login_ip VARCHAR(45) NULL
);

CREATE TABLE IF NOT EXISTS hosts_host (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 22,
    username VARCHAR(64) NOT NULL,
    auth_method VARCHAR(16) NOT NULL DEFAULT 'password',
    credential TEXT NOT NULL DEFAULT '',
    docker_service_root VARCHAR(512) NOT NULL DEFAULT '',
    created_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS hosts_host_created_by_id ON hosts_host(created_by_id);

CREATE TABLE IF NOT EXISTS deployment_deploymenttask (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host_id INTEGER NOT NULL REFERENCES hosts_host(id) ON DELETE CASCADE,
    action VARCHAR(32) NOT NULL,
    target VARCHAR(64) NOT NULL DEFAULT '',
    deploy_mode VARCHAR(16) NOT NULL DEFAULT 'single',
    host_node2_id INTEGER NULL REFERENCES hosts_host(id) ON DELETE SET NULL,
    host_node3_id INTEGER NULL REFERENCES hosts_host(id) ON DELETE SET NULL,
    user_edit_content TEXT NOT NULL DEFAULT '',
    remote_user_edit_path VARCHAR(512) NOT NULL DEFAULT '',
    package_release_id INTEGER NULL,
    package_artifact_ids TEXT NOT NULL DEFAULT '[]',
    skip_package_sync INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    exit_code INTEGER NULL,
    error_message TEXT NOT NULL DEFAULT '',
    created_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    started_at DATETIME NULL,
    finished_at DATETIME NULL
);

CREATE INDEX IF NOT EXISTS deployment_task_host ON deployment_deploymenttask(host_id);
CREATE INDEX IF NOT EXISTS deployment_task_status ON deployment_deploymenttask(status);
CREATE INDEX IF NOT EXISTS deployment_task_created ON deployment_deploymenttask(created_at DESC);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS deployment_deploymenttask;
DROP TABLE IF EXISTS hosts_host;
DROP TABLE IF EXISTS auth_user;
-- +goose StatementEnd
