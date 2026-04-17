package service

import (
	"context"
	"errors"
	"net/http"
	"strings"

	"tpops_deployment/internal/runner"
)

// CreateTaskIn 创建并启动任务请求体（与既有 JSON 字段名对齐）。
type CreateTaskIn struct {
	Host            int64  `json:"host"`
	Action          string `json:"action"`
	Target          string `json:"target"`
	DeployMode      string `json:"deploy_mode"`
	UserEditContent string `json:"user_edit_content"`
	RemoteUserEdit  string `json:"remote_user_edit_path"`
	RemoteLogPath   string `json:"remote_log_path"`
	SkipPackageSync bool   `json:"skip_package_sync"`
	Start           bool   `json:"start"`
}

// CreateTaskOut 返回新任务 id。
type CreateTaskOut struct {
	ID int64 `json:"id"`
}

// CreateTask 插入 pending 任务；若 start=true 则启动 runner。
func (s *Service) CreateTask(ctx context.Context, userID int64, in CreateTaskIn) (*CreateTaskOut, int, error) {
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
	uid := userID
	skip := 0
	if in.SkipPackageSync {
		skip = 1
	}
	id, err := s.repos.InsertTask(ctx, in.Host, action, strings.TrimSpace(in.Target), deployMode,
		in.UserEditContent, strings.TrimSpace(in.RemoteUserEdit), strings.TrimSpace(in.RemoteLogPath), skip, &uid)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if in.Start {
		s.StartRunner(id, userID)
	}
	return &CreateTaskOut{ID: id}, http.StatusCreated, nil
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
	cfg := runner.ConfigSubset{FernetSecret: s.cfg.FernetSecret}
	runner.RunSSHDeployment(context.Background(), taskID, userID, s.repos, cfg, s.RunnerBroadcaster(),
		func(c context.Context, uid, tid int64) (map[string]interface{}, error) {
			return s.ManifestSnapshot(c, uid, tid)
		})
}
