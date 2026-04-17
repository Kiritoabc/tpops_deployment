package repository

import "context"

// CanUserAccessHost：staff/superuser 全量；否则 created_by=user 或 created_by IS NULL。
func (r *Repos) CanUserAccessHost(ctx context.Context, userID int64, createdByID *int64) (bool, error) {
	return r.CanUserAccessTask(ctx, userID, createdByID)
}
