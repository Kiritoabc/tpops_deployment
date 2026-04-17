package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/service"
)

func (h *Handler) createHost(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	var in service.HostUpsertIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	out, code, err := h.svc.CreateHost(c.Request.Context(), userID, in)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) updateHost(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效主机 ID"})
		return
	}
	var in service.HostUpsertIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	out, code, err := h.svc.UpdateHost(c.Request.Context(), userID, id, in)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) deleteHost(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效主机 ID"})
		return
	}
	code, err := h.svc.DeleteHost(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.Status(code)
}

func (h *Handler) testHostConnection(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效主机 ID"})
		return
	}
	out, code, err := h.svc.TestHostConnection(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}
