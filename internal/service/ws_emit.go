package service

// broadcastTask 同时推送到部署 feed 与日志 feed WebSocket。
func (s *Service) broadcastTask(taskID int64, payload map[string]interface{}) {
	if s.hub == nil {
		return
	}
	s.hub.BroadcastDeploy(taskID, payload)
	s.hub.BroadcastLog(taskID, payload)
}

// EmitDeploymentEvent 保留：与 broadcastTask 等价。
func (s *Service) EmitDeploymentEvent(taskID int64, payload map[string]interface{}) {
	s.broadcastTask(taskID, payload)
}
