package repository

import (
	"context"
	"database/sql"
)

// InsertTask 创建 pending 任务，返回新 id。
func (r *Repos) InsertTask(ctx context.Context, hostID int64, hostNode2, hostNode3 *int64, action, target, deployMode, userEdit, remotePath, remoteLogPath string, packageReleaseID *int64, skipSync, useRawShell int, createdBy *int64) (int64, error) {
	if deployMode == "" {
		deployMode = "single"
	}
	res, err := r.db.ExecContext(ctx, `
		INSERT INTO deployment_deploymenttask (
			host_id, host_node2_id, host_node3_id, action, target, deploy_mode, user_edit_content, remote_user_edit_path, remote_log_path,
			package_release_id, package_artifact_ids, skip_package_sync, use_raw_shell, status, created_by_id
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, 'pending', ?)`,
		hostID, hostNode2, hostNode3, action, target, deployMode, userEdit, remotePath, remoteLogPath, packageReleaseID, skipSync, useRawShell, createdBy)
	if err != nil {
		return 0, err
	}
	id, err := res.LastInsertId()
	return id, err
}

// UpdateTaskRunning 将 pending 置为 running 并写入 started_at。
func (r *Repos) UpdateTaskRunning(ctx context.Context, id int64) (bool, error) {
	res, err := r.db.ExecContext(ctx, `
		UPDATE deployment_deploymenttask
		SET status = 'running', started_at = datetime('now'), updated_at = datetime('now')
		WHERE id = ? AND status = 'pending'`, id)
	if err != nil {
		return false, err
	}
	n, err := res.RowsAffected()
	return n > 0, err
}

// UpdateTaskFinished 写入终态与 finished_at。
func (r *Repos) UpdateTaskFinished(ctx context.Context, id int64, status string, exitCode *int, errMsg string) error {
	if exitCode != nil {
		_, err := r.db.ExecContext(ctx, `
			UPDATE deployment_deploymenttask
			SET status = ?, exit_code = ?, error_message = ?, finished_at = datetime('now'), updated_at = datetime('now')
			WHERE id = ?`, status, *exitCode, errMsg, id)
		return err
	}
	_, err := r.db.ExecContext(ctx, `
		UPDATE deployment_deploymenttask
		SET status = ?, exit_code = NULL, error_message = ?, finished_at = datetime('now'), updated_at = datetime('now')
		WHERE id = ?`, status, errMsg, id)
	return err
}

// UpdateTaskStatusMessage 运行中更新状态文案（不结束任务）。
func (r *Repos) UpdateTaskStatusMessage(ctx context.Context, id int64, status, errMsg string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE deployment_deploymenttask
		SET status = ?, error_message = ?, updated_at = datetime('now')
		WHERE id = ?`, status, errMsg, id)
	return err
}

// TaskIsTerminal 若任务已是终态则返回 true。
// UpdateTaskPackageFields 写入安装包关联字段（package_release_id 可为 NULL）。
func (r *Repos) UpdateTaskPackageFields(ctx context.Context, id int64, packageReleaseID *int64, artifactIDsJSON string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE deployment_deploymenttask
		SET package_release_id = ?, package_artifact_ids = ?, updated_at = datetime('now')
		WHERE id = ?`, packageReleaseID, artifactIDsJSON, id)
	return err
}

func (r *Repos) TaskIsTerminal(ctx context.Context, id int64) (bool, error) {
	var st string
	err := r.db.GetContext(ctx, &st, `SELECT status FROM deployment_deploymenttask WHERE id = ?`, id)
	if err == sql.ErrNoRows {
		return false, err
	}
	if err != nil {
		return false, err
	}
	switch st {
	case "success", "failed", "cancelled":
		return true, nil
	default:
		return false, nil
	}
}
