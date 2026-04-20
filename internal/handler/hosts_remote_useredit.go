package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/middleware"
)

// fetchHostRemoteUserEdit GET /api/hosts/:id/remote_user_edit/
func (h *Handler) fetchHostRemoteUserEdit(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效主机 ID"})
		return
	}
	out, code, err := h.svc.FetchRemoteUserEdit(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}
