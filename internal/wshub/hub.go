package wshub

import (
	"encoding/json"
	"sync"

	"github.com/gorilla/websocket"
)

type Hub struct {
	mu    sync.Mutex
	tasks map[int64]map[*websocket.Conn]struct{}
}

func NewHub() *Hub {
	return &Hub{tasks: make(map[int64]map[*websocket.Conn]struct{})}
}

func (h *Hub) Register(taskID int64, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.tasks[taskID] == nil {
		h.tasks[taskID] = make(map[*websocket.Conn]struct{})
	}
	h.tasks[taskID][c] = struct{}{}
}

func (h *Hub) Unregister(taskID int64, c *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if m, ok := h.tasks[taskID]; ok {
		delete(m, c)
		if len(m) == 0 {
			delete(h.tasks, taskID)
		}
	}
}

func (h *Hub) Broadcast(taskID int64, payload interface{}) {
	b, err := json.Marshal(payload)
	if err != nil {
		return
	}
	h.mu.Lock()
	m := h.tasks[taskID]
	var list []*websocket.Conn
	for c := range m {
		list = append(list, c)
	}
	h.mu.Unlock()
	for _, c := range list {
		_ = c.WriteMessage(websocket.TextMessage, b)
	}
}
