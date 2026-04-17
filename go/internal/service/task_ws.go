package service

import (
	"context"

	"github.com/Kiritoabc/tpops_deployment/go/internal/repository"
)

// TaskWSOut 供 WebSocket hello 使用（时间字段为 RFC3339 或 nil 字符串）。
type TaskWSOut struct {
	Status         string
	Action         string
	ExitCode       *int
	ErrorMessage   string
	StartedAt      *string
	FinishedAt     *string
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

// GetTaskByIDForHandler 返回完整行（供 REST detail）。
func (s *Service) GetTaskByIDForHandler(ctx context.Context, userID, taskID int64) (*repository.DeploymentTask, error) {
	t, err := s.repos.GetTaskByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	ok, err := s.repos.CanUserAccessTask(ctx, userID, t.CreatedByID)
	if err != nil || !ok {
		return nil, nil
	}
	return t, nil
}
