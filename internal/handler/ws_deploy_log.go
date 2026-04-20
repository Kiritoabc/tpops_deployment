package handler

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"tpops_deployment/internal/auth"
	"tpops_deployment/internal/crypto"
	"tpops_deployment/internal/remotelog"
	"tpops_deployment/internal/service"
)

// WSDeployLog 与 Python DeployLogTailConsumer 对齐：按字节 offset 轮询远程
// log_path/deploy/<kind>.log 或 log_path/deploy/<rel>，消息 type=chunk|meta|hello|wait|error。
func (h *Handler) WSDeployLog(c *gin.Context) {
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
	t, err := h.svc.TaskDetailForAPI(c.Request.Context(), claims.UserID, taskID)
	if err != nil || t == nil {
		c.AbortWithStatus(http.StatusForbidden)
		return
	}

	host, err := h.svc.HostForTask(c.Request.Context(), t.Host, claims.UserID)
	if err != nil {
		if errors.Is(err, service.ErrForbidden) {
			c.AbortWithStatus(http.StatusForbidden)
			return
		}
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}
	if host == nil {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}
	secret, err := crypto.DecryptFernetCredential(h.cfg.FernetSecret, host.Credential)
	if err != nil || secret == "" {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}

	kind := strings.TrimSpace(c.Query("kind"))
	if kind == "" {
		kind = "precheck"
	}
	if kind != "precheck" && kind != "install" && kind != "uninstall" {
		kind = "precheck"
	}
	rel := strings.TrimSpace(c.Query("rel"))

	rpath, err := remotelog.ResolveRemoteLogPath(t.UserEditContent, kind, rel)
	if err != nil {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		return
	}
	h.hub.RegisterLog(taskID, conn)
	defer h.hub.UnregisterLog(taskID, conn)

	hello := map[string]interface{}{
		"type": "hello", "task_id": taskID, "kind": kind, "rel": rel,
	}
	b, _ := json.Marshal(hello)
	_ = conn.WriteMessage(websocket.TextMessage, b)

	send := func(v interface{}) {
		bb, _ := json.Marshal(v)
		_ = conn.SetWriteDeadline(time.Now().Add(30 * time.Second))
		_ = conn.WriteMessage(websocket.TextMessage, bb)
	}

	send(map[string]interface{}{"type": "meta", "path": rpath, "kind": kind})

	stop := make(chan struct{})
	go func() {
		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				close(stop)
				return
			}
		}
	}()

	var off int64
	missingCount := 0
	ticker := time.NewTicker(400 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-stop:
			return
		case <-ticker.C:
			chunk, newOff, missing, err := remotelog.TailRemoteLogChunk(
				host.Hostname, host.Port, host.Username, host.AuthMethod, secret,
				rpath, off, 65536, 30*time.Second)
			if err != nil {
				send(map[string]interface{}{"type": "error", "message": err.Error()})
				return
			}
			off = newOff
			if chunk != "" {
				send(map[string]interface{}{"type": "chunk", "data": chunk})
			}
			if missing {
				missingCount++
				if missingCount > 30 {
					send(map[string]interface{}{"type": "wait", "message": "日志文件尚未创建…"})
					missingCount = 0
				}
			} else {
				missingCount = 0
			}
		}
	}
}
