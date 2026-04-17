package service

import (
	"github.com/Kiritoabc/tpops_deployment/go/internal/config"
	"github.com/Kiritoabc/tpops_deployment/go/internal/repository"
	"github.com/Kiritoabc/tpops_deployment/go/internal/wshub"
)

type Service struct {
	repos *repository.Repos
	cfg   config.Config
	hub   *wshub.Hub
}

func New(repos *repository.Repos, cfg config.Config, hub *wshub.Hub) *Service {
	return &Service{repos: repos, cfg: cfg, hub: hub}
}
