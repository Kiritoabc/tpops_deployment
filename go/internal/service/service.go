package service

import (
	"github.com/Kiritoabc/tpops_deployment/go/internal/config"
	"github.com/Kiritoabc/tpops_deployment/go/internal/repository"
)

type Service struct {
	repos *repository.Repos
	cfg   config.Config
}

func New(repos *repository.Repos, cfg config.Config) *Service {
	return &Service{repos: repos, cfg: cfg}
}
