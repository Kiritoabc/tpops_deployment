package runner

import (
	"context"
	"fmt"
	"strings"
	"time"

	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/sshutil"
)

// PushUserEditToRemote 将任务中的 user_edit 文本写入远端（SFTP），供 appctl 读取。
func PushUserEditToRemote(
	ctx context.Context,
	host *repository.Host,
	sshSecret string,
	task *repository.DeploymentTask,
	emit func(map[string]interface{}),
) error {
	body := strings.TrimSpace(task.UserEditContent)
	if body == "" {
		emit(map[string]interface{}{"type": "log", "line": "[local] user_edit 为空，跳过下发", "data": ""})
		return nil
	}
	if !strings.HasSuffix(body, "\n") {
		body += "\n"
	}
	remote := deploypaths.ResolveUserEditRemotePath(host.DockerServiceRoot, task.RemoteUserEditPath)
	emit(map[string]interface{}{"type": "phase", "phase": "user_edit_push", "message": "下发 user_edit"})
	emit(map[string]interface{}{"type": "log", "line": fmt.Sprintf("[local] SFTP user_edit → %s", remote), "data": ""})
	r := strings.NewReader(body)
	if err := sshutil.UploadReaderSFTP(host.Hostname, host.Port, host.Username, host.AuthMethod, sshSecret, remote, r, 5*time.Minute); err != nil {
		return fmt.Errorf("下发 user_edit: %w", err)
	}
	emit(map[string]interface{}{"type": "log", "line": "[local] user_edit 已写入远端", "data": ""})
	return nil
}
