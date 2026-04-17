package handler

import (
	"context"
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
	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/service"
	"tpops_deployment/internal/sshutil"
)

// WSDeployLog 仅日志：远端 tail -F 任务 remote_log_path，消息 type=log。
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
	if errors.Is(err, service.ErrForbidden) {
		c.AbortWithStatus(http.StatusForbidden)
		return
	}
	if err != nil || host == nil {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}
	secret, err := crypto.DecryptFernetCredential(h.cfg.FernetSecret, host.Credential)
	if err != nil || secret == "" {
		c.AbortWithStatus(http.StatusBadRequest)
		return
	}

	logRel := strings.TrimSpace(t.RemoteLogPath)
	if logRel == "" {
		logRel = "logs/deploy_" + strconv.FormatInt(taskID, 10) + ".log"
	}
	absLog := deploypaths.AbsolutePath(host.DockerServiceRoot, logRel)

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		return
	}
	h.hub.RegisterLog(taskID, conn)
	defer h.hub.UnregisterLog(taskID, conn)

	hello := map[string]interface{}{
		"type": "hello", "channel": "log",
		"task_id": taskID, "remote_log": absLog,
	}
	b, _ := json.Marshal(hello)
	_ = conn.WriteMessage(websocket.TextMessage, b)

	ctx, cancel := context.WithCancel(c.Request.Context())
	defer cancel()
	go func() {
		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				cancel()
				return
			}
		}
	}()

	_ = sshutil.TailRemoteFile(ctx, host.Hostname, host.Port, host.Username, host.AuthMethod, secret, absLog,
		func(line string) {
			payload := map[string]interface{}{"type": "log", "line": line}
			bb, _ := json.Marshal(payload)
			_ = conn.SetWriteDeadline(time.Now().Add(30 * time.Second))
			_ = conn.WriteMessage(websocket.TextMessage, bb)
		})
}
