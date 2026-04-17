package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func (h *Handler) listTasks(c *gin.Context) {
	list, err := h.svc.ListTasks(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}
