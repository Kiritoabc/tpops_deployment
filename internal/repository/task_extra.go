package repository

import "context"

func (r *Repos) GetTaskByID(ctx context.Context, id int64) (*DeploymentTask, error) {
	var t DeploymentTask
	err := r.db.GetContext(ctx, &t, `
		SELECT id, host_id, action, target, deploy_mode, host_node2_id, host_node3_id,
		       user_edit_content, remote_user_edit_path, remote_log_path, package_release_id, package_artifact_ids, skip_package_sync,
		       status, exit_code, error_message, created_by_id, created_at, updated_at, started_at, finished_at
		FROM deployment_deploymenttask WHERE id = ?`, id)
	if err != nil {
		return nil, err
	}
	return &t, nil
}
