package runner

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/sshutil"
)

func parseArtifactIDList(raw string) []int64 {
	raw = strings.TrimSpace(raw)
	if raw == "" || raw == "[]" {
		return nil
	}
	var ids []int64
	if err := json.Unmarshal([]byte(raw), &ids); err != nil {
		return nil
	}
	return ids
}

// SyncPackagesToRemote 将任务选中的安装包 SFTP 到远端 deployRoot/pkgs/。
func SyncPackagesToRemote(
	ctx context.Context,
	repos *repository.Repos,
	packagesDir string,
	host *repository.Host,
	sshSecret string,
	task *repository.DeploymentTask,
	emit func(map[string]interface{}),
) error {
	if task.SkipPackageSync != 0 {
		return nil
	}
	ids := parseArtifactIDList(task.PackageArtifactIDs)
	if len(ids) == 0 {
		return nil
	}
	if task.PackageReleaseID == nil {
		emit(map[string]interface{}{"type": "log", "line": "[local] 已选择安装包但未设置 package_release_id，跳过同步", "data": ""})
		return nil
	}
	relID := *task.PackageReleaseID
	arts, err := repos.ListArtifactsByIDs(ctx, ids)
	if err != nil {
		return fmt.Errorf("读取安装包: %w", err)
	}
	if len(arts) == 0 {
		return fmt.Errorf("未找到安装包记录")
	}
	emit(map[string]interface{}{"type": "phase", "phase": "package_sync", "message": fmt.Sprintf("同步 %d 个文件到远端 pkgs/", len(arts))})
	for _, a := range arts {
		if a.ReleaseID != relID {
			return fmt.Errorf("安装包 #%d 不属于所选版本", a.ID)
		}
		local := a.StoragePath
		if !strings.HasPrefix(local, "/") && packagesDir != "" {
			local = strings.TrimSuffix(packagesDir, "/") + "/" + strings.TrimPrefix(local, "/")
		}
		remote := deploypaths.RemotePkgsFile(host.DockerServiceRoot, a.RemoteBasename)
		emit(map[string]interface{}{"type": "log", "line": fmt.Sprintf("[local] SFTP → %s", remote), "data": ""})
		if err := sshutil.UploadFileSFTP(host.Hostname, host.Port, host.Username, host.AuthMethod, sshSecret, local, remote, 30*time.Minute); err != nil {
			return fmt.Errorf("上传 %s: %w", a.RemoteBasename, err)
		}
	}
	emit(map[string]interface{}{"type": "log", "line": "[local] 安装包同步完成", "data": ""})
	return nil
}
