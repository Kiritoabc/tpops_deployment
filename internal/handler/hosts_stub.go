package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func (h *Handler) hostCRUDNotImplemented(c *gin.Context) {
	c.JSON(http.StatusNotImplemented, gin.H{"detail": "主机增删改尚未在 Go 版实现，请先用数据库或后续 API 录入"})
}
