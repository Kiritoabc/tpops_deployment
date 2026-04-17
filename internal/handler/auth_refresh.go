package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/auth"
)

type refreshIn struct {
	Refresh string `json:"refresh"`
}

func (h *Handler) tokenRefresh(c *gin.Context) {
	var in refreshIn
	if err := c.ShouldBindJSON(&in); err != nil || in.Refresh == "" {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "需要提供 refresh"})
		return
	}
	claims, err := auth.ParseToken(h.cfg.JWTSecret, in.Refresh)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"detail": "refresh 无效或已过期"})
		return
	}
	access, err := auth.SignAccess(h.cfg.JWTSecret, claims.UserID, claims.Username, claims.Role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"access": access})
}
