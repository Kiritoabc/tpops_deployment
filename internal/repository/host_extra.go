package repository

import "context"

func (r *Repos) GetHostByID(ctx context.Context, id int64) (*Host, error) {
	var h Host
	err := r.db.GetContext(ctx, &h, `
		SELECT id, name, hostname, port, username, auth_method,
		       credential, docker_service_root, created_by_id, created_at, updated_at
		FROM hosts_host WHERE id = ?`, id)
	if err != nil {
		return nil, err
	}
	return &h, nil
}
