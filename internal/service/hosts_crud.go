package service

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"time"

	"tpops_deployment/internal/crypto"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/sshutil"
)

// HostUpsertIn 与前端 hostForm 对齐（POST 整表 / PATCH 整表）。
type HostUpsertIn struct {
	ID                *int64 `json:"id"`
	Name              string `json:"name"`
	Hostname          string `json:"hostname"`
	Port              int    `json:"port"`
	Username          string `json:"username"`
	AuthMethod        string `json:"auth_method"`
	Password          string `json:"password"`
	PrivateKey        string `json:"private_key"`
	DockerServiceRoot string `json:"docker_service_root"`
}

func (s *Service) CreateHost(ctx context.Context, userID int64, in HostUpsertIn) (*HostListItem, int, error) {
	if strings.TrimSpace(in.Name) == "" {
		return nil, http.StatusBadRequest, errors.New("请填写主机名称")
	}
	if strings.TrimSpace(in.Hostname) == "" {
		return nil, http.StatusBadRequest, errors.New("请填写主机地址")
	}
	if in.Port <= 0 {
		in.Port = 22
	}
	if strings.TrimSpace(in.Username) == "" {
		return nil, http.StatusBadRequest, errors.New("请填写 SSH 用户名")
	}
	method := strings.TrimSpace(in.AuthMethod)
	if method == "" {
		method = "password"
	}
	plain, err := pickCredentialPlaintext(method, in.Password, in.PrivateKey)
	if err != nil {
		return nil, http.StatusBadRequest, err
	}
	if plain == "" {
		return nil, http.StatusBadRequest, errors.New("请填写密码或私钥")
	}
	if s.cfg.FernetSecret == "" {
		return nil, http.StatusBadRequest, errors.New("未配置 TPOPS_GO_FERNET_SECRET，无法保存加密凭证")
	}
	enc, err := crypto.EncryptFernetCredential(s.cfg.FernetSecret, plain)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	root := strings.TrimSpace(in.DockerServiceRoot)
	if root == "" {
		root = "/data/docker-service"
	}
	uid := userID
	id, err := s.repos.InsertHost(ctx, strings.TrimSpace(in.Name), strings.TrimSpace(in.Hostname), in.Port,
		strings.TrimSpace(in.Username), method, enc, root, &uid)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	h, err := s.repos.GetHostByID(ctx, id)
	if err != nil || h == nil {
		return nil, http.StatusInternalServerError, errors.New("插入后读取失败")
	}
	owner := ""
	if u, _ := s.repos.GetUserByID(ctx, userID); u != nil {
		owner = u.Username
	}
	return hostToListItem(h, owner), http.StatusCreated, nil
}

func (s *Service) UpdateHost(ctx context.Context, userID, hostID int64, in HostUpsertIn) (*HostListItem, int, error) {
	prev, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if prev == nil {
		return nil, http.StatusNotFound, errors.New("未找到")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, prev.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权修改该主机")
	}
	if strings.TrimSpace(in.Name) == "" || strings.TrimSpace(in.Hostname) == "" {
		return nil, http.StatusBadRequest, errors.New("名称与地址不能为空")
	}
	if in.Port <= 0 {
		in.Port = 22
	}
	method := strings.TrimSpace(in.AuthMethod)
	if method == "" {
		method = "password"
	}
	root := strings.TrimSpace(in.DockerServiceRoot)
	if root == "" {
		root = "/data/docker-service"
	}

	var credPtr *string
	if pw := strings.TrimSpace(in.Password); pw != "" || strings.TrimSpace(in.PrivateKey) != "" {
		plain, err := pickCredentialPlaintext(method, in.Password, in.PrivateKey)
		if err != nil {
			return nil, http.StatusBadRequest, err
		}
		if s.cfg.FernetSecret == "" {
			return nil, http.StatusBadRequest, errors.New("未配置 TPOPS_GO_FERNET_SECRET，无法保存加密凭证")
		}
		enc, err := crypto.EncryptFernetCredential(s.cfg.FernetSecret, plain)
		if err != nil {
			return nil, http.StatusInternalServerError, err
		}
		credPtr = &enc
	}

	if err := s.repos.UpdateHost(ctx, hostID, strings.TrimSpace(in.Name), strings.TrimSpace(in.Hostname), in.Port,
		strings.TrimSpace(in.Username), method, root, credPtr); err != nil {
		return nil, http.StatusInternalServerError, err
	}
	h, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil || h == nil {
		return nil, http.StatusNotFound, errors.New("未找到")
	}
	owner := ""
	if h.CreatedByID != nil {
		if u, _ := s.repos.GetUserByID(ctx, *h.CreatedByID); u != nil {
			owner = u.Username
		}
	}
	return hostToListItem(h, owner), http.StatusOK, nil
}

func pickCredentialPlaintext(authMethod, password, privateKey string) (string, error) {
	if authMethod == "key" {
		p := strings.TrimSpace(privateKey)
		if p == "" {
			return "", errors.New("密钥认证需要填写私钥")
		}
		return p, nil
	}
	p := strings.TrimSpace(password)
	if p == "" {
		return "", errors.New("密码认证需要填写密码")
	}
	return p, nil
}

func hostToListItem(h *repository.Host, ownerUsername string) *HostListItem {
	if h == nil {
		return nil
	}
	return &HostListItem{
		ID:                h.ID,
		Name:              h.Name,
		Hostname:          h.Hostname,
		Port:              h.Port,
		Username:          h.Username,
		AuthMethod:        h.AuthMethod,
		HasCredential:     h.Credential != "",
		DockerServiceRoot: h.DockerServiceRoot,
		OwnerUsername:     ownerUsername,
	}
}

func (s *Service) DeleteHost(ctx context.Context, userID, hostID int64) (int, error) {
	prev, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if prev == nil {
		return http.StatusNotFound, errors.New("未找到")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, prev.CreatedByID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if !ok {
		return http.StatusForbidden, errors.New("无权删除")
	}
	n, err := s.repos.DeleteHost(ctx, hostID)
	if err != nil {
		return http.StatusInternalServerError, err
	}
	if n == 0 {
		return http.StatusNotFound, errors.New("未找到")
	}
	return http.StatusNoContent, nil
}

// TestHostConnectionResult 连通性检测结果。
type TestHostConnectionResult struct {
	OK      bool   `json:"ok"`
	Message string `json:"message"`
}

func (s *Service) TestHostConnection(ctx context.Context, userID, hostID int64) (*TestHostConnectionResult, int, error) {
	h, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if h == nil {
		return nil, http.StatusNotFound, errors.New("未找到")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, h.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权测试该主机")
	}
	if h.Credential == "" {
		return &TestHostConnectionResult{OK: false, Message: "未配置加密凭证"}, http.StatusOK, nil
	}
	secret, err := crypto.DecryptFernetCredential(s.cfg.FernetSecret, h.Credential)
	if err != nil {
		return &TestHostConnectionResult{OK: false, Message: "凭证解密失败: " + err.Error()}, http.StatusOK, nil
	}
	if secret == "" {
		return &TestHostConnectionResult{OK: false, Message: "解密后凭证为空"}, http.StatusOK, nil
	}
	if err := sshutil.TestConnection(h.Hostname, h.Port, h.Username, h.AuthMethod, secret, 10*time.Second, 15*time.Second); err != nil {
		return &TestHostConnectionResult{OK: false, Message: err.Error()}, http.StatusOK, nil
	}
	return &TestHostConnectionResult{OK: true, Message: "SSH 连接成功"}, http.StatusOK, nil
}
