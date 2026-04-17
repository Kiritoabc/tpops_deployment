package handler

import (
	"net/http"

	"github.com/Kiritoabc/tpops_deployment/go/internal/config"
	"github.com/Kiritoabc/tpops_deployment/go/internal/middleware"
	"github.com/Kiritoabc/tpops_deployment/go/internal/service"
	"github.com/gin-gonic/gin"
)

type Handler struct {
	svc *service.Service
	cfg config.Config
}

func New(svc *service.Service, cfg config.Config) *Handler {
	return &Handler{svc: svc, cfg: cfg}
}

func (h *Handler) Register(r *gin.Engine) {
	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "tpops-go"})
	})

	api := r.Group("/api")

	authG := api.Group("/auth")
	{
		authG.POST("/login/", h.login)
		authG.POST("/register/", h.register)
		authG.GET("/profile/", middleware.JWTAuth(h.cfg.JWTSecret), h.profile)
	}

	protected := api.Group("")
	protected.Use(middleware.JWTAuth(h.cfg.JWTSecret))
	{
		protected.GET("/hosts/", h.listHosts)
		protected.GET("/deployment/tasks/", h.listTasks)
	}
}
