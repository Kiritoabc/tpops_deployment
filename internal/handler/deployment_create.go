package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"tpops_deployment/internal/middleware"
	"tpops_deployment/internal/service"
)

func (h *Handler) createTask(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	userID := uid.(int64)
	var in service.CreateTaskIn
	if err := c.ShouldBindJSON(&in); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "无效请求体"})
		return
	}
	out, code, err := h.svc.CreateTask(c.Request.Context(), userID, in)
	if err != nil {
		c.JSON(code, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(code, out)
}

func (h *Handler) startTask(c *gin.Context) {
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
	if t.Status != "pending" {
		c.JSON(http.StatusConflict, gin.H{"detail": "任务不在 pending 状态", "status": t.Status})
		return
	}
	h.svc.StartRunner(id, userID)
	c.JSON(http.StatusAccepted, gin.H{"id": id, "message": "runner 已启动"})
}
