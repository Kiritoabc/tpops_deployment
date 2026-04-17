package service

import (
	"context"
	"encoding/json"
	"strings"

	"tpops_deployment/internal/repository"
)

// TaskDetailJSON 与前端任务详情 / 列表扩展字段对齐。
type TaskDetailJSON struct {
	ID                 int64   `json:"id"`
	Host               int64   `json:"host"`
	DeployMode         string  `json:"deploy_mode"`
	UserEditContent    string  `json:"user_edit_content"`
	RemoteUserEditPath string  `json:"remote_user_edit_path"`
	RemoteLogPath      string  `json:"remote_log_path"`
	Action             string  `json:"action"`
	Target             string  `json:"target"`
	SkipPackageSync    bool    `json:"skip_package_sync"`
	Status             string  `json:"status"`
	ExitCode           *int    `json:"exit_code"`
	ErrorMessage       string  `json:"error_message"`
	CreatedAt          string  `json:"created_at"`
	UpdatedAt          string  `json:"updated_at,omitempty"`
	StartedAt          *string `json:"started_at"`
	FinishedAt         *string `json:"finished_at"`
	HostNode2ID        *int64  `json:"host_node2,omitempty"`
	HostNode3ID        *int64  `json:"host_node3,omitempty"`
	HostName           string  `json:"host_name,omitempty"`
	HostNode2Name      string  `json:"host_node2_name,omitempty"`
	HostNode3Name      string  `json:"host_node3_name,omitempty"`
	CreatedByUsername  string  `json:"created_by_username,omitempty"`
	PackageRelease     *int64  `json:"package_release"`
	PackageArtifactIDs []int64 `json:"package_artifact_ids"`
}

func (s *Service) TaskDetailForAPI(ctx context.Context, userID, taskID int64) (*TaskDetailJSON, error) {
	t, err := s.repos.GetTaskByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	ok, err := s.repos.CanUserAccessTask(ctx, userID, t.CreatedByID)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, nil
	}
	return s.buildTaskDetailJSON(ctx, t), nil
}

func (s *Service) buildTaskDetailJSON(ctx context.Context, t *repository.DeploymentTask) *TaskDetailJSON {
	out := &TaskDetailJSON{
		ID:                 t.ID,
		Host:               t.HostID,
		DeployMode:         t.DeployMode,
		UserEditContent:    t.UserEditContent,
		RemoteUserEditPath: t.RemoteUserEditPath,
		RemoteLogPath:      t.RemoteLogPath,
		Action:             t.Action,
		Target:             t.Target,
		SkipPackageSync:    t.SkipPackageSync != 0,
		Status:             t.Status,
		ExitCode:           t.ExitCode,
		ErrorMessage:       t.ErrorMessage,
		CreatedAt:          t.CreatedAt,
		UpdatedAt:          t.UpdatedAt,
		StartedAt:          t.StartedAt,
		FinishedAt:         t.FinishedAt,
		HostNode2ID:        t.HostNode2ID,
		HostNode3ID:        t.HostNode3ID,
		PackageRelease:     nil,
		PackageArtifactIDs: parseArtifactIDs(t.PackageArtifactIDs),
	}
	if h, _ := s.repos.GetHostByID(ctx, t.HostID); h != nil {
		out.HostName = h.Name
	}
	if t.HostNode2ID != nil {
		if h, _ := s.repos.GetHostByID(ctx, *t.HostNode2ID); h != nil {
			out.HostNode2Name = h.Name
		}
	}
	if t.HostNode3ID != nil {
		if h, _ := s.repos.GetHostByID(ctx, *t.HostNode3ID); h != nil {
			out.HostNode3Name = h.Name
		}
	}
	if t.CreatedByID != nil {
		if u, _ := s.repos.GetUserByID(ctx, *t.CreatedByID); u != nil {
			out.CreatedByUsername = u.Username
		}
	}
	return out
}

func parseArtifactIDs(raw string) []int64 {
	raw = strings.TrimSpace(raw)
	if raw == "" || raw == "[]" {
		return []int64{}
	}
	var arr []int64
	if err := json.Unmarshal([]byte(raw), &arr); err != nil {
		return []int64{}
	}
	return arr
}
