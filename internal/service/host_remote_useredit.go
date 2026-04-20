package service

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"time"

	"tpops_deployment/internal/crypto"
	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/sshutil"
)

// RemoteUserEditOut 从节点 1（指定 host）拉取远端 user_edit 文本。
type RemoteUserEditOut struct {
	Content            string `json:"content"`
	ResolvedRemotePath string `json:"resolved_remote_path"`
}

// FetchRemoteUserEdit 通过 SSH 读取主执行机上 user_edit 配置文件内容。
func (s *Service) FetchRemoteUserEdit(ctx context.Context, userID, hostID int64) (*RemoteUserEditOut, int, error) {
	h, err := s.repos.GetHostByID(ctx, hostID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if h == nil {
		return nil, http.StatusNotFound, errors.New("主机不存在")
	}
	ok, err := s.repos.CanUserAccessHost(ctx, userID, h.CreatedByID)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if !ok {
		return nil, http.StatusForbidden, errors.New("无权访问该主机")
	}
	secret, err := crypto.DecryptFernetCredential(s.cfg.FernetSecret, h.Credential)
	if err != nil || secret == "" {
		return nil, http.StatusBadRequest, errors.New("无法解密 SSH 凭证")
	}

	inner := deploypaths.ResolveRemoteUserEditConfPathScript(h.DockerServiceRoot)
	out, code, err := sshutil.RunShOutput(h.Hostname, h.Port, h.Username, h.AuthMethod, secret, inner, 60*time.Second)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	path := strings.TrimSpace(out)
	if code != 0 || path == "" || path == "NOTFOUND" {
		fallback := deploypaths.ResolveUserEditRemotePath(h.DockerServiceRoot, "")
		raw, c2, err2 := sshutil.CatRemoteFile(h.Hostname, h.Port, h.Username, h.AuthMethod, secret, fallback, 90*time.Second)
		if err2 != nil || c2 != 0 || strings.TrimSpace(raw) == "" {
			return nil, http.StatusNotFound, errors.New("未找到远端 user_edit（已检查 config/gaussdb/user_edit_file.conf、config/user_edit_file.conf 及 config/user_edit.conf）")
		}
		return &RemoteUserEditOut{Content: raw, ResolvedRemotePath: fallback}, http.StatusOK, nil
	}

	raw, c3, err3 := sshutil.CatRemoteFile(h.Hostname, h.Port, h.Username, h.AuthMethod, secret, path, 90*time.Second)
	if err3 != nil {
		return nil, http.StatusInternalServerError, err3
	}
	if c3 != 0 {
		return nil, http.StatusNotFound, errors.New("无法读取远端配置文件")
	}
	return &RemoteUserEditOut{Content: raw, ResolvedRemotePath: path}, http.StatusOK, nil
}
