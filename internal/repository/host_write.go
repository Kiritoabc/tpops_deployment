package repository

import (
	"context"
)

// InsertHost 插入主机，返回新 id。
func (r *Repos) InsertHost(ctx context.Context, name, hostname string, port int, username, authMethod, credential, dockerRoot string, createdBy *int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `
		INSERT INTO hosts_host (name, hostname, port, username, auth_method, credential, docker_service_root, created_by_id, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))`,
		name, hostname, port, username, authMethod, credential, dockerRoot, createdBy)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

// UpdateHost 更新主机元数据；credential 传 nil 表示不更新凭证列。
func (r *Repos) UpdateHost(ctx context.Context, id int64, name, hostname string, port int, username, authMethod, dockerRoot string, credential *string) error {
	if credential != nil {
		_, err := r.db.ExecContext(ctx, `
			UPDATE hosts_host SET name=?, hostname=?, port=?, username=?, auth_method=?, credential=?, docker_service_root=?, updated_at=datetime('now')
			WHERE id=?`,
			name, hostname, port, username, authMethod, *credential, dockerRoot, id)
		return err
	}
	_, err := r.db.ExecContext(ctx, `
		UPDATE hosts_host SET name=?, hostname=?, port=?, username=?, auth_method=?, docker_service_root=?, updated_at=datetime('now')
		WHERE id=?`,
		name, hostname, port, username, authMethod, dockerRoot, id)
	return err
}

func (r *Repos) DeleteHost(ctx context.Context, id int64) (int64, error) {
	res, err := r.db.ExecContext(ctx, `DELETE FROM hosts_host WHERE id = ?`, id)
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}
