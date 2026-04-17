package handler

import (
	"net/http"

	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/service"
	"github.com/gin-gonic/gin"
)

func (h *Handler) login(c *gin.Context) {
	var in service.LoginIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	ip := c.ClientIP()
	out, code, err := h.svc.Login(c.Request.Context(), in, ip)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) register(c *gin.Context) {
	var in service.RegisterIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	_, u, code, err := h.svc.Register(c.Request.Context(), in)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, gin.H{"message": "注册成功", "user": u})
}

func (h *Handler) profile(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	id := uid.(int64)
	u, err := h.svc.Profile(c.Request.Context(), id)
	if err != nil || u == nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": "用户不存在"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"user": u})
}
