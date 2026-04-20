package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/service"
)

func (h *Handler) listPackageReleases(c *gin.Context) {
	list, err := h.svc.ListPackageReleases(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}

func (h *Handler) createPackageRelease(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	var in service.CreateReleaseIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	out, code, err := h.svc.CreatePackageRelease(c.Request.Context(), userID, in)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) deletePackageRelease(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效 ID"})
		return
	}
	code, err := h.svc.DeletePackageRelease(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.Status(code)
}

func (h *Handler) listPackageArtifacts(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	rid, err := strconv.ParseInt(c.Query("release"), 10, 64)
	if err != nil || rid < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "需要 query release"})
		return
	}
	list, code, err := h.svc.ListArtifacts(c.Request.Context(), userID, rid)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}

func (h *Handler) uploadPackageArtifact(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	ridStr := c.PostForm("release")
	if ridStr == "" {
		ridStr = c.Query("release")
	}
	rid, err := strconv.ParseInt(ridStr, 10, 64)
	if err != nil || rid < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "需要表单字段 release"})
		return
	}
	fh, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "需要上传文件 file"})
		return
	}
	f, err := fh.Open()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": err.Error()})
		return
	}
	defer f.Close()

	out, code, err := h.svc.UploadArtifact(c.Request.Context(), userID, rid, fh, f)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) deletePackageArtifact(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || id < 1 {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效 ID"})
		return
	}
	code, err := h.svc.DeleteArtifact(c.Request.Context(), userID, id)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.Status(code)
}
