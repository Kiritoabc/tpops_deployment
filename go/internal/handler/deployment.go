package handler

import (
	"errors"
	"net/http"
	"strconv"

	"github.com/Kiritoabc/tpops_deployment/go/internal/middleware"
	"github.com/Kiritoabc/tpops_deployment/go/internal/service"
	"github.com/gin-gonic/gin"
)

func (h *Handler) getTask(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效任务 ID"})
		return
	}
	t, err := h.svc.GetTaskByIDForHandler(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	if t == nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": "未找到"})
		return
	}
	c.JSON(http.StatusOK, t)
}

func (h *Handler) manifestSnapshot(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效任务 ID"})
		return
	}
	tree, err := h.svc.ManifestSnapshot(c.Request.Context(), userID, id)
	if err != nil {
		var mn *service.ManifestNotSupported
		switch {
		case errors.Is(err, service.ErrForbidden):
			c.JSON(http.StatusForbidden, gin.H{"detail": "无权访问"})
		case errors.As(err, &mn):
			c.JSON(http.StatusBadRequest, gin.H{"detail": "当前任务类型不轮询 manifest", "action": mn.Action})
		case errors.Is(err, service.ErrNoCredential):
			c.JSON(http.StatusBadRequest, gin.H{"detail": "执行机未配置 SSH 凭证"})
		case errors.Is(err, service.ErrNoManifestYAML):
			c.JSON(http.StatusNotFound, gin.H{"detail": "未读取到有效 manifest YAML"})
		default:
			c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		}
		return
	}
	c.JSON(http.StatusOK, tree)
}
