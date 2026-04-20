package repository

import (
	"context"
)

// TaskListRow 任务列表行（含创建人、节点名称）。
type TaskListRow struct {
	DeploymentTask
	CreatedByUsername *string `db:"created_by_username"`
	HostName          *string `db:"host_name"`
	HostNode2Name     *string `db:"host_node2_name"`
	HostNode3Name     *string `db:"host_node3_name"`
}

func (r *Repos) ListTasksJoined(ctx context.Context) ([]TaskListRow, error) {
	var rows []TaskListRow
	err := r.db.SelectContext(ctx, &rows, `
		SELECT
			t.id, t.host_id, t.action, t.target, t.deploy_mode, t.host_node2_id, t.host_node3_id,
			t.user_edit_content, t.remote_user_edit_path, t.remote_log_path, t.package_release_id, t.package_artifact_ids, t.skip_package_sync, t.use_raw_shell,
			t.status, t.exit_code, t.error_message, t.created_by_id, t.created_at, t.updated_at, t.started_at, t.finished_at,
			u.username AS created_by_username,
			h1.name AS host_name,
			h2.name AS host_node2_name,
			h3.name AS host_node3_name
		FROM deployment_deploymenttask t
		LEFT JOIN auth_user u ON u.id = t.created_by_id
		LEFT JOIN hosts_host h1 ON h1.id = t.host_id
		LEFT JOIN hosts_host h2 ON h2.id = t.host_node2_id
		LEFT JOIN hosts_host h3 ON h3.id = t.host_node3_id
		ORDER BY t.created_at DESC`)
	return rows, err
}
