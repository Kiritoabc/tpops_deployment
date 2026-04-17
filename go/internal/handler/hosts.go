package handler

import (
	"net/http"

	"github.com/Kiritoabc/tpops_deployment/go/internal/middleware"
	"github.com/gin-gonic/gin"
)

func (h *Handler) listHosts(c *gin.Context) {
	uid, _ := c.Get(middleware.CtxUserID)
	id := uid.(int64)
	list, err := h.svc.ListHosts(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}
