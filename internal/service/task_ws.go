package service

import (
	"context"
)

// TaskWSOut 供 WebSocket hello 使用（时间字段为 RFC3339 或 nil 字符串）。
type TaskWSOut struct {
	Status       string
	Action       string
	ExitCode     *int
	ErrorMessage string
	StartedAt    *string
	FinishedAt   *string
}

func (s *Service) TaskForWS(ctx context.Context, userID, taskID int64) (*TaskWSOut, error) {
	t, err := s.repos.GetTaskByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	ok, err := s.repos.CanUserAccessTask(ctx, userID, t.CreatedByID)
	if err != nil || !ok {
		return nil, nil
	}
	return &TaskWSOut{
		Status:       t.Status,
		Action:       t.Action,
		ExitCode:     t.ExitCode,
		ErrorMessage: t.ErrorMessage,
		StartedAt:    t.StartedAt,
		FinishedAt:   t.FinishedAt,
	}, nil
}
