package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// 安装包 API 尚未实现：列表返回空数组，写操作返回 501，避免前端控制台大量报错。

func (h *Handler) listPackageReleases(c *gin.Context) {
	c.JSON(http.StatusOK, []gin.H{})
}

func (h *Handler) listPackageArtifacts(c *gin.Context) {
	c.JSON(http.StatusOK, []gin.H{})
}

func (h *Handler) packageNotImplemented(c *gin.Context) {
	c.JSON(http.StatusNotImplemented, gin.H{"detail": "安装包管理尚未在 Go 版实现"})
}
