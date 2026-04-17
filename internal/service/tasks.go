package service

import (
	"context"
)

type TaskListItem struct {
	ID              int64   `json:"id"`
	HostID          int64   `json:"host"`
	Action          string  `json:"action"`
	Target          string  `json:"target"`
	DeployMode      string  `json:"deploy_mode"`
	Status          string  `json:"status"`
	ExitCode        *int    `json:"exit_code"`
	SkipPackageSync bool    `json:"skip_package_sync"`
	CreatedAt       string  `json:"created_at"`
}

func (s *Service) ListTasks(ctx context.Context) ([]TaskListItem, error) {
	rows, err := s.repos.ListTasks(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]TaskListItem, 0, len(rows))
	for _, t := range rows {
		out = append(out, TaskListItem{
			ID:              t.ID,
			HostID:          t.HostID,
			Action:          t.Action,
			Target:          t.Target,
			DeployMode:      t.DeployMode,
			Status:          t.Status,
			ExitCode:        t.ExitCode,
			SkipPackageSync: t.SkipPackageSync != 0,
			CreatedAt:       t.CreatedAt,
		})
	}
	return out, nil
}
