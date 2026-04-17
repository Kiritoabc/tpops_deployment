package handler

import (
	"html/template"
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
	// 安装包上传：放宽 multipart 内存阈值（大文件仍落盘）
	r.MaxMultipartMemory = 512 << 20 // 512 MiB

	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "tpops-go"})
	})

	tpl, err := template.ParseFS(web.Dir, "templates/index.html")
	if err != nil {
		panic("web/templates/index.html: " + err.Error())
	}
	r.SetHTMLTemplate(tpl)
	r.GET("/", func(c *gin.Context) {
		c.HTML(http.StatusOK, "index.html", nil)
	})
	if sub, err := fs.Sub(web.Dir, "static"); err == nil {
		r.StaticFS("/static", http.FS(sub))
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
		protected.POST("/hosts/", h.createHost)
		protected.PATCH("/hosts/:id/", h.updateHost)
		protected.DELETE("/hosts/:id/", h.deleteHost)
		protected.POST("/hosts/:id/test_connection/", h.testHostConnection)
		protected.GET("/deployment/tasks/", h.listTasks)
		protected.POST("/deployment/tasks/", h.createTask)
		protected.GET("/deployment/tasks/:id/", h.getTask)
		protected.POST("/deployment/tasks/:id/start/", h.startTask)
		protected.GET("/deployment/tasks/:id/manifest_snapshot/", h.manifestSnapshot)

		pkg := protected.Group("/packages")
		{
			pkg.GET("/releases/", h.listPackageReleases)
			pkg.POST("/releases/", h.createPackageRelease)
			pkg.DELETE("/releases/:id/", h.deletePackageRelease)
			pkg.GET("/artifacts/", h.listPackageArtifacts)
			pkg.POST("/artifacts/", h.uploadPackageArtifact)
			pkg.DELETE("/artifacts/:id/", h.deletePackageArtifact)
		}
	}

	r.GET("/ws/deploy/:id/", h.WSDeploy)
	r.GET("/ws/deploy/:id/log/", h.WSDeployLog)
}
