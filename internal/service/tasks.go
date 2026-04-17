package service

import (
	"context"
)

type TaskListItem struct {
	ID                 int64   `json:"id"`
	Host               int64   `json:"host"`
	Action             string  `json:"action"`
	Target             string  `json:"target"`
	DeployMode         string  `json:"deploy_mode"`
	Status             string  `json:"status"`
	ExitCode           *int    `json:"exit_code"`
	SkipPackageSync    bool    `json:"skip_package_sync"`
	CreatedAt          string  `json:"created_at"`
	HostName           string  `json:"host_name,omitempty"`
	HostNode2Name      string  `json:"host_node2_name,omitempty"`
	HostNode3Name      string  `json:"host_node3_name,omitempty"`
	CreatedByUsername  string  `json:"created_by_username,omitempty"`
	PackageReleaseName *string `json:"package_release_name,omitempty"`
	PackageArtifactIDs []int64 `json:"package_artifact_ids,omitempty"`
}

func (s *Service) ListTasks(ctx context.Context) ([]TaskListItem, error) {
	rows, err := s.repos.ListTasksJoined(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]TaskListItem, 0, len(rows))
	for _, t := range rows {
		item := TaskListItem{
			ID:              t.ID,
			Host:            t.HostID,
			Action:          t.Action,
			Target:          t.Target,
			DeployMode:      t.DeployMode,
			Status:          t.Status,
			ExitCode:        t.ExitCode,
			SkipPackageSync: t.SkipPackageSync != 0,
			CreatedAt:       t.CreatedAt,
		}
		if t.HostName != nil {
			item.HostName = *t.HostName
		}
		if t.HostNode2Name != nil {
			item.HostNode2Name = *t.HostNode2Name
		}
		if t.HostNode3Name != nil {
			item.HostNode3Name = *t.HostNode3Name
		}
		if t.CreatedByUsername != nil {
			item.CreatedByUsername = *t.CreatedByUsername
		}
		out = append(out, item)
	}
	return out, nil
}
