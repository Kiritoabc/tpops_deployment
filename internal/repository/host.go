package repository

import (
	"context"
)

type Host struct {
	ID                  int64   `db:"id"`
	Name                string  `db:"name"`
	Hostname            string  `db:"hostname"`
	Port                int     `db:"port"`
	Username            string  `db:"username"`
	AuthMethod          string  `db:"auth_method"`
	Credential          string  `db:"credential"`
	DockerServiceRoot   string  `db:"docker_service_root"`
	CreatedByID         *int64  `db:"created_by_id"`
	CreatedAt           string  `db:"created_at"`
	UpdatedAt           string  `db:"updated_at"`
}

func (r *Repos) ListHostsForUser(ctx context.Context, userID int64) ([]Host, error) {
	var rows []Host
	err := r.db.SelectContext(ctx, &rows, `
		SELECT id, name, hostname, port, username, auth_method,
		       credential, docker_service_root, created_by_id, created_at, updated_at
		FROM hosts_host
		WHERE created_by_id IS NULL OR created_by_id = ?
		ORDER BY created_at DESC`, userID)
	return rows, err
}
