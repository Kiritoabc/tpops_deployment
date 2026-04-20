package repository

import (
	"context"
	"database/sql"
)

// HostListRow 主机列表行（含创建人用户名）。
type HostListRow struct {
	ID                int64          `db:"id"`
	Name              string         `db:"name"`
	Hostname          string         `db:"hostname"`
	Port              int            `db:"port"`
	Username          string         `db:"username"`
	AuthMethod        string         `db:"auth_method"`
	Credential        string         `db:"credential"`
	DockerServiceRoot string         `db:"docker_service_root"`
	CreatedByID       sql.NullInt64  `db:"created_by_id"`
	CreatedAt         string         `db:"created_at"`
	UpdatedAt         string         `db:"updated_at"`
	OwnerUsername     sql.NullString `db:"owner_username"`
}

func (r *Repos) ListHostsForUser(ctx context.Context, userID int64) ([]HostListRow, error) {
	var rows []HostListRow
	err := r.db.SelectContext(ctx, &rows, `
		SELECT h.id, h.name, h.hostname, h.port, h.username, h.auth_method, h.credential,
		       h.docker_service_root, h.created_by_id, h.created_at, h.updated_at,
		       u.username AS owner_username
		FROM hosts_host h
		LEFT JOIN auth_user u ON u.id = h.created_by_id
		WHERE h.created_by_id IS NULL OR h.created_by_id = ?
		ORDER BY h.created_at DESC`, userID)
	return rows, err
}
