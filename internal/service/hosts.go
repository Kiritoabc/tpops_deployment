package service

import (
	"context"

	"tpops_deployment/internal/repository"
)

type HostListItem struct {
	ID                int64  `json:"id"`
	Name              string `json:"name"`
	Hostname          string `json:"hostname"`
	Port              int    `json:"port"`
	Username          string `json:"username"`
	AuthMethod        string `json:"auth_method"`
	HasCredential     bool   `json:"has_credential"`
	DockerServiceRoot string `json:"docker_service_root"`
}

func (s *Service) ListHosts(ctx context.Context, userID int64) ([]HostListItem, error) {
	rows, err := s.repos.ListHostsForUser(ctx, userID)
	if err != nil {
		return nil, err
	}
	out := make([]HostListItem, 0, len(rows))
	for _, h := range rows {
		out = append(out, HostListItem{
			ID:                h.ID,
			Name:              h.Name,
			Hostname:          h.Hostname,
			Port:              h.Port,
			Username:          h.Username,
			AuthMethod:        h.AuthMethod,
			HasCredential:     h.Credential != "",
			DockerServiceRoot: h.DockerServiceRoot,
		})
	}
	return out, nil
}

// HostForTask 校验用户对执行机的访问后返回主机行。
func (s *Service) HostForTask(ctx context.Context, hostID, userID int64) (*repository.Host, error) {
	h, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil || h == nil {
		return nil, err
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, h.CreatedByID)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, ErrForbidden
	}
	return h, nil
}
