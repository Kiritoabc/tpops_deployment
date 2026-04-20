-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS packages_packagerelease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS packages_release_created_by ON packages_packagerelease(created_by_id);

CREATE TABLE IF NOT EXISTS packages_packageartifact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id INTEGER NOT NULL REFERENCES packages_packagerelease(id) ON DELETE CASCADE,
    original_name VARCHAR(512) NOT NULL DEFAULT '',
    remote_basename VARCHAR(512) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    size INTEGER NOT NULL DEFAULT 0,
    sha256 VARCHAR(64) NOT NULL DEFAULT '',
    created_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS packages_artifact_release ON packages_packageartifact(release_id);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS packages_packageartifact;
DROP TABLE IF EXISTS packages_packagerelease;
-- +goose StatementEnd
