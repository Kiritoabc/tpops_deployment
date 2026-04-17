package handler

import (
	"net/http"

	"github.com/Kiritoabc/tpops_deployment/go/internal/config"
	"github.com/Kiritoabc/tpops_deployment/go/internal/middleware"
	"github.com/Kiritoabc/tpops_deployment/go/internal/service"
	"github.com/Kiritoabc/tpops_deployment/go/internal/wshub"
	"github.com/gin-gonic/gin"
)

type Handler struct {
	svc *service.Service
	cfg config.Config
	hub *wshub.Hub
}

func New(svc *service.Service, cfg config.Config, hub *wshub.Hub) *Handler {
	return &Handler{svc: svc, cfg: cfg, hub: hub}
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
		protected.GET("/deployment/tasks/:id/", h.getTask)
		protected.GET("/deployment/tasks/:id/manifest_snapshot/", h.manifestSnapshot)
	}

	r.GET("/ws/deploy/:id/", h.WSDeploy)
}
