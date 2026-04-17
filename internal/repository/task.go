package repository

import (
	"context"
)

type DeploymentTask struct {
	ID                 int64   `db:"id"`
	HostID             int64   `db:"host_id"`
	Action             string  `db:"action"`
	Target             string  `db:"target"`
	DeployMode         string  `db:"deploy_mode"`
	HostNode2ID        *int64  `db:"host_node2_id"`
	HostNode3ID        *int64  `db:"host_node3_id"`
	UserEditContent    string  `db:"user_edit_content"`
	RemoteUserEditPath string  `db:"remote_user_edit_path"`
	RemoteLogPath      string  `db:"remote_log_path"`
	PackageArtifactIDs string  `db:"package_artifact_ids"`
	SkipPackageSync    int     `db:"skip_package_sync"` // SQLite 0/1
	Status             string  `db:"status"`
	ExitCode           *int    `db:"exit_code"`
	ErrorMessage       string  `db:"error_message"`
	CreatedByID        *int64  `db:"created_by_id"`
	CreatedAt          string  `db:"created_at"`
	UpdatedAt          string  `db:"updated_at"`
	StartedAt          *string `db:"started_at"`
	FinishedAt         *string `db:"finished_at"`
}

func (r *Repos) ListTasks(ctx context.Context) ([]DeploymentTask, error) {
	var rows []DeploymentTask
	err := r.db.SelectContext(ctx, &rows, `
		SELECT id, host_id, action, target, deploy_mode, host_node2_id, host_node3_id,
		       user_edit_content, remote_user_edit_path, remote_log_path, package_artifact_ids, skip_package_sync,
		       status, exit_code, error_message, created_by_id, created_at, updated_at, started_at, finished_at
		FROM deployment_deploymenttask
		ORDER BY created_at DESC`)
	return rows, err
}
