package repository

import "context"

// CanUserAccessTask 与 Django filter_deployment_tasks_for_user：staff/superuser 全量；否则 created_by=user 或 created_by IS NULL。
func (r *Repos) CanUserAccessTask(ctx context.Context, userID int64, createdByID *int64) (bool, error) {
	var isSuper, isStaff int
	var role string
	err := r.db.QueryRowContext(ctx,
		`SELECT is_superuser, is_staff, role FROM auth_user WHERE id = ?`, userID,
	).Scan(&isSuper, &isStaff, &role)
	if err != nil {
		return false, err
	}
	if isSuper == 1 || isStaff == 1 {
		return true, nil
	}
	if createdByID == nil {
		return true, nil
	}
	return *createdByID == userID, nil
}
