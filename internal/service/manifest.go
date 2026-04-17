package service

import (
	"context"
	"strings"
	"time"

	"tpops_deployment/internal/crypto"
	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/manifest"
	"tpops_deployment/internal/sshutil"
)

// ManifestSnapshot 单次 SSH 读取 manifest 并解析。
func (s *Service) ManifestSnapshot(ctx context.Context, userID, taskID int64) (map[string]interface{}, error) {
	t, err := s.repos.GetTaskByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	ok, err := s.repos.CanUserAccessTask(ctx, userID, t.CreatedByID)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, ErrForbidden
	}
	action := t.Action
	if action != "install" && action != "upgrade" {
		return nil, &ManifestNotSupported{Action: action}
	}
	host, err := s.repos.GetHostByID(ctx, t.HostID)
	if err != nil {
		return nil, err
	}
	secret, err := crypto.DecryptFernetCredential(s.cfg.FernetSecret, host.Credential)
	if err != nil {
		return nil, err
	}
	if secret == "" {
		return nil, ErrNoCredential
	}
	kv := deploypaths.ParseUserEditKV(t.UserEditContent)
	paths := deploypaths.RemoteManifestPaths(host.DockerServiceRoot, t.DeployMode, kv)
	var dicts []map[string]interface{}
	for _, rel := range paths {
		abs := deploypaths.AbsolutePath(host.DockerServiceRoot, rel)
		raw, code, err := sshutil.CatRemoteFile(host.Hostname, host.Port, host.Username, host.AuthMethod, secret, abs, 90*time.Second)
		if err != nil {
			continue
		}
		if code != 0 || strings.TrimSpace(raw) == "" {
			continue
		}
		d, err := manifest.ParseYAMLToMap(raw)
		if err != nil {
			continue
		}
		dicts = append(dicts, d)
	}
	if len(dicts) == 0 {
		return nil, ErrNoManifestYAML
	}
	tree, err := manifest.ManifestFromYAML(dicts, paths, deploypaths.Node1IP(kv))
	if err != nil {
		return nil, err
	}
	tree["deploy_mode"] = t.DeployMode
	return tree, nil
}

// EmitDeploymentEvent 供 runner 向任务 WebSocket 客户端广播 JSON（含 type 字段）。
func (s *Service) EmitDeploymentEvent(taskID int64, payload map[string]interface{}) {
	if s.hub == nil {
		return
	}
	s.hub.Broadcast(taskID, payload)
}
