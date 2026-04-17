package service

import "tpops_deployment/internal/runner"

// runnerHubAdapter 将 Service 接到 runner.Broadcaster。
type runnerHubAdapter struct{ s *Service }

func (a runnerHubAdapter) Broadcast(taskID int64, payload map[string]interface{}) {
	a.s.broadcastTask(taskID, payload)
}

// RunnerBroadcaster 供 runner 包推送 WS 事件。
func (s *Service) RunnerBroadcaster() runner.Broadcaster {
	return runnerHubAdapter{s: s}
}
