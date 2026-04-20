package runner

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"tpops_deployment/internal/crypto"
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

type syncHostTarget struct {
	label  string
	host   *repository.Host
	secret string
}

// collectPackageSyncTargets 三节点时向各不重复主机并行同步；单节点仅主执行机。
func collectPackageSyncTargets(ctx context.Context, repos *repository.Repos, fernetSecret string, main *repository.Host, mainSecret string, task *repository.DeploymentTask) ([]syncHostTarget, error) {
	if task.DeployMode != deploypaths.ModeTriple {
		return []syncHostTarget{{label: "节点1", host: main, secret: mainSecret}}, nil
	}
	var out []syncHostTarget
	seen := map[int64]struct{}{}
	add := func(label string, h *repository.Host, sec string) {
		if h == nil || sec == "" {
			return
		}
		if _, ok := seen[h.ID]; ok {
			return
		}
		seen[h.ID] = struct{}{}
		out = append(out, syncHostTarget{label: label, host: h, secret: sec})
	}
	add("节点1", main, mainSecret)

	dec := func(hid int64) (*repository.Host, string, error) {
		h, err := repos.GetHostByID(ctx, hid)
		if err != nil {
			return nil, "", err
		}
		if h == nil {
			return nil, "", fmt.Errorf("主机 #%d 不存在", hid)
		}
		s, err := crypto.DecryptFernetCredential(fernetSecret, h.Credential)
		if err != nil || s == "" {
			return nil, "", fmt.Errorf("主机 #%d 凭证解密失败", hid)
		}
		return h, s, nil
	}

	if task.HostNode2ID != nil && *task.HostNode2ID != main.ID {
		h2, s2, err := dec(*task.HostNode2ID)
		if err != nil {
			return nil, err
		}
		add("节点2", h2, s2)
	}
	if task.HostNode3ID != nil && *task.HostNode3ID != main.ID {
		h3, s3, err := dec(*task.HostNode3ID)
		if err != nil {
			return nil, err
		}
		add("节点3", h3, s3)
	}
	return out, nil
}

func syncArtifactsToOneHost(
	ctx context.Context,
	packagesDir string,
	tgt syncHostTarget,
	arts []repository.PackageArtifact,
	emit func(map[string]interface{}),
) error {
	for _, a := range arts {
		local := a.StoragePath
		if !strings.HasPrefix(local, "/") && packagesDir != "" {
			local = strings.TrimSuffix(packagesDir, "/") + "/" + strings.TrimPrefix(local, "/")
		}
		remote := deploypaths.RemotePkgsFile(tgt.host.DockerServiceRoot, a.RemoteBasename)
		emit(map[string]interface{}{"type": "log", "line": fmt.Sprintf("[local] %s SFTP → %s@%s:%s", tgt.label, tgt.host.Username, tgt.host.Hostname, remote), "data": ""})
		if err := sshutil.UploadFileSFTP(tgt.host.Hostname, tgt.host.Port, tgt.host.Username, tgt.host.AuthMethod, tgt.secret, local, remote, 30*time.Minute); err != nil {
			return fmt.Errorf("%s 上传 %s: %w", tgt.label, a.RemoteBasename, err)
		}
	}
	return nil
}

// SyncPackagesToRemote 将任务选中的安装包 SFTP 到各节点 deployRoot/pkgs/（三节点并行）。
func SyncPackagesToRemote(
	ctx context.Context,
	repos *repository.Repos,
	fernetSecret string,
	packagesDir string,
	mainHost *repository.Host,
	mainSecret string,
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
	for _, a := range arts {
		if a.ReleaseID != relID {
			return fmt.Errorf("安装包 #%d 不属于所选版本", a.ID)
		}
	}

	targets, err := collectPackageSyncTargets(ctx, repos, fernetSecret, mainHost, mainSecret, task)
	if err != nil {
		return err
	}
	emit(map[string]interface{}{"type": "phase", "phase": "package_sync", "message": fmt.Sprintf("向 %d 台主机同步 %d 个文件到 pkgs/", len(targets), len(arts))})

	var wg sync.WaitGroup
	errMu := sync.Mutex{}
	var firstErr error
	for _, tgt := range targets {
		tgt := tgt
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := syncArtifactsToOneHost(ctx, packagesDir, tgt, arts, emit); err != nil {
				errMu.Lock()
				if firstErr == nil {
					firstErr = err
				}
				errMu.Unlock()
			}
		}()
	}
	wg.Wait()
	if firstErr != nil {
		return firstErr
	}
	emit(map[string]interface{}{"type": "log", "line": "[local] 安装包同步完成（全部节点）", "data": ""})
	return nil
}
