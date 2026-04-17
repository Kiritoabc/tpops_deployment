package wshub

import (
	"encoding/json"
	"sync"

	"github.com/gorilla/websocket"
)

// Hub 按 taskID 管理两类连接：主部署 feed（deploy）与仅日志（log）。
type Hub struct {
	mu       sync.Mutex
	deploy   map[int64]map[*websocket.Conn]struct{}
	logConns map[int64]map[*websocket.Conn]struct{}
}

func NewHub() *Hub {
	return &Hub{
		deploy:   make(map[int64]map[*websocket.Conn]struct{}),
		logConns: make(map[int64]map[*websocket.Conn]struct{}),
	}
}

func (h *Hub) RegisterDeploy(taskID int64, c *websocket.Conn) {
	h.registerConn(&h.deploy, taskID, c)
}

func (h *Hub) UnregisterDeploy(taskID int64, c *websocket.Conn) {
	h.unregisterConn(&h.deploy, taskID, c)
}

func (h *Hub) RegisterLog(taskID int64, c *websocket.Conn) {
	h.registerConn(&h.logConns, taskID, c)
}

func (h *Hub) UnregisterLog(taskID int64, c *websocket.Conn) {
	h.unregisterConn(&h.logConns, taskID, c)
}

// Register / Unregister / Broadcast 兼容旧调用：等同 deploy feed。
func (h *Hub) Register(taskID int64, c *websocket.Conn) {
	h.RegisterDeploy(taskID, c)
}

func (h *Hub) Unregister(taskID int64, c *websocket.Conn) {
	h.UnregisterDeploy(taskID, c)
}

func (h *Hub) Broadcast(taskID int64, payload interface{}) {
	h.BroadcastDeploy(taskID, payload)
}

func (h *Hub) registerConn(m *map[int64]map[*websocket.Conn]struct{}, taskID int64, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if (*m)[taskID] == nil {
		(*m)[taskID] = make(map[*websocket.Conn]struct{})
	}
	(*m)[taskID][c] = struct{}{}
}

func (h *Hub) unregisterConn(m *map[int64]map[*websocket.Conn]struct{}, taskID int64, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if mm, ok := (*m)[taskID]; ok {
		delete(mm, c)
		if len(mm) == 0 {
			delete(*m, taskID)
		}
	}
}

func (h *Hub) BroadcastDeploy(taskID int64, payload interface{}) {
	h.broadcastToMap(&h.deploy, taskID, payload)
}

func (h *Hub) BroadcastLog(taskID int64, payload interface{}) {
	h.broadcastToMap(&h.logConns, taskID, payload)
}

func (h *Hub) broadcastToMap(m *map[int64]map[*websocket.Conn]struct{}, taskID int64, payload interface{}) {
	b, err := json.Marshal(payload)
	if err != nil {
		return
	}
	h.mu.Lock()
	mm := (*m)[taskID]
	var list []*websocket.Conn
	for c := range mm {
		list = append(list, c)
	}
	h.mu.Unlock()
	for _, c := range list {
		_ = c.WriteMessage(websocket.TextMessage, b)
	}
}
