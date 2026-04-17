package handler

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/Kiritoabc/tpops_deployment/go/internal/auth"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool { return true },
}

// WSDeploy 对齐 /ws/deploy/:id/?token=...
func (h *Handler) WSDeploy(c *gin.Context) {
	token := c.Query("token")
	if token == "" {
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}
	claims, err := auth.ParseToken(h.cfg.JWTSecret, token)
	if err != nil {
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}
	taskID, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil || taskID < 1 {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}
	t, err := h.svc.TaskForWS(c.Request.Context(), claims.UserID, taskID)
	if err != nil || t == nil {
		c.AbortWithStatus(http.StatusForbidden)
		return
	}
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		return
	}
	h.hub.Register(taskID, conn)
	defer h.hub.Unregister(taskID, conn)

	hello := map[string]interface{}{
		"type":          "hello",
		"task_id":       taskID,
		"status":        t.Status,
		"action":        t.Action,
		"exit_code":     t.ExitCode,
		"error_message": trim2000(t.ErrorMessage),
		"finished_at":   t.FinishedAt,
		"started_at":    t.StartedAt,
	}
	b, _ := json.Marshal(hello)
	_ = conn.WriteMessage(websocket.TextMessage, b)

	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			break
		}
	}
}

func trim2000(s string) string {
	s = strings.TrimSpace(s)
	if len(s) > 2000 {
		return s[:2000]
	}
	return s
}
