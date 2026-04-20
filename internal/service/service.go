package service

import (
	"tpops_deployment/internal/config"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/wshub"
)

type Service struct {
	repos *repository.Repos
	cfg   config.Config
	hub   *wshub.Hub
}

func New(repos *repository.Repos, cfg config.Config, hub *wshub.Hub) *Service {
	return &Service{repos: repos, cfg: cfg, hub: hub}
}
