package service

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"tpops_deployment/internal/runner"
)

// CreateTaskIn 创建并启动任务请求体（与既有 JSON 字段名对齐）。
type CreateTaskIn struct {
	Host               int64   `json:"host"`
	HostNode2          *int64  `json:"host_node2"`
	HostNode3          *int64  `json:"host_node3"`
	Action             string  `json:"action"`
	Target             string  `json:"target"`
	DeployMode         string  `json:"deploy_mode"`
	UserEditContent    string  `json:"user_edit_content"`
	RemoteUserEdit     string  `json:"remote_user_edit_path"`
	RemoteLogPath      string  `json:"remote_log_path"`
	SkipPackageSync    bool    `json:"skip_package_sync"`
	PackageRelease     *int64  `json:"package_release"`
	PackageArtifactIDs []int64 `json:"package_artifact_ids"`
	// NoStart 为 true 时仅创建任务，不启动 Runner（默认会启动，与旧前端「创建即执行」一致）。
	NoStart bool `json:"no_start"`
}

// CreateTask 插入 pending 任务；默认立即启动 Runner（与前端一致）；`start: false` 可仅创建。
func (s *Service) CreateTask(ctx context.Context, userID int64, in CreateTaskIn) (*TaskDetailJSON, int, error) {
	if in.Host < 1 {
		return nil, http.StatusBadRequest, errors.New("host 无效")
	}
	action := strings.TrimSpace(in.Action)
	if action == "" {
		return nil, http.StatusBadRequest, errors.New("action 必填")
	}
	host, err := s.repos.GetHostByID(ctx, in.Host)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if host == nil {
		return nil, http.StatusBadRequest, errors.New("执行机不存在")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, host.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权使用该执行机")
	}

	deployMode := strings.TrimSpace(in.DeployMode)
	if deployMode == "" {
		deployMode = "single"
	}
	if deployMode == "triple" {
		if in.HostNode2 == nil || in.HostNode3 == nil {
			return nil, http.StatusBadRequest, errors.New("三节点模式需要 host_node2 与 host_node3")
		}
	}
	uid := userID
	skip := 0
	if in.SkipPackageSync {
		skip = 1
	}
	artifactJSON := "[]"
	if len(in.PackageArtifactIDs) > 0 {
		b, err := json.Marshal(in.PackageArtifactIDs)
		if err != nil {
			return nil, http.StatusBadRequest, errors.New("package_artifact_ids 无效")
		}
		artifactJSON = string(b)
	}
	id, err := s.repos.InsertTask(ctx, in.Host, in.HostNode2, in.HostNode3, action, strings.TrimSpace(in.Target), deployMode,
		in.UserEditContent, strings.TrimSpace(in.RemoteUserEdit), strings.TrimSpace(in.RemoteLogPath), in.PackageRelease, skip, &uid)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if artifactJSON != "[]" {
		if err := s.repos.UpdateTaskPackageFields(ctx, id, in.PackageRelease, artifactJSON); err != nil {
			return nil, http.StatusInternalServerError, err
		}
	}
	if !in.NoStart {
		s.StartRunner(id, userID)
	}
	t, err := s.repos.GetTaskByID(ctx, id)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	return s.buildTaskDetailJSON(ctx, t), http.StatusCreated, nil
}

// StartRunner 对 pending 任务启动后台 SSH runner（幂等：非 pending 则忽略）。
func (s *Service) StartRunner(taskID, userID int64) {
	t, err := s.repos.GetTaskByID(context.Background(), taskID)
	if err != nil || t == nil {
		return
	}
	if t.Status != "pending" {
		return
	}
	ok, err := s.repos.CanUserAccessTask(context.Background(), userID, t.CreatedByID)
	if err != nil || !ok {
		return
	}
	cfg := runner.ConfigSubset{FernetSecret: s.cfg.FernetSecret, PackagesDir: s.cfg.PackagesStorageDir}
	runner.RunSSHDeployment(context.Background(), taskID, userID, s.repos, cfg, s.RunnerBroadcaster(),
		func(c context.Context, uid, tid int64) (map[string]interface{}, error) {
			return s.ManifestSnapshot(c, uid, tid)
		})
}
