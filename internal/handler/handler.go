package handler

import (
	"io/fs"
	"net/http"

	"tpops_deployment/internal/config"
	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/service"
	"tpops_deployment/internal/wshub"
	"tpops_deployment/web"

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

	r.GET("/", func(c *gin.Context) {
		b, err := web.Dir.ReadFile("static/index.html")
		if err != nil {
			c.String(http.StatusNotFound, "not found")
			return
		}
		c.Data(http.StatusOK, "text/html; charset=utf-8", b)
	})
	if sub, err := fs.Sub(web.Dir, "static"); err == nil {
		r.StaticFS("/assets", http.FS(sub))
	}

	api := r.Group("/api")

	authG := api.Group("/auth")
	{
		authG.POST("/login/", h.login)
		authG.POST("/register/", h.register)
		authG.POST("/token/refresh/", h.tokenRefresh)
		authG.GET("/profile/", middleware.JWTAuth(h.cfg.JWTSecret), h.profile)
	}

	protected := api.Group("")
	protected.Use(middleware.JWTAuth(h.cfg.JWTSecret))
	{
		protected.GET("/hosts/", h.listHosts)
		protected.GET("/deployment/tasks/", h.listTasks)
		protected.POST("/deployment/tasks/", h.createTask)
		protected.GET("/deployment/tasks/:id/", h.getTask)
		protected.POST("/deployment/tasks/:id/start/", h.startTask)
		protected.GET("/deployment/tasks/:id/manifest_snapshot/", h.manifestSnapshot)
	}

	r.GET("/ws/deploy/:id/", h.WSDeploy)
	r.GET("/ws/deploy/:id/log/", h.WSDeployLog)
}
