package service

import (
	"context"
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
