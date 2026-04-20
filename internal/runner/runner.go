package runner

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"tpops_deployment/internal/crypto"
	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/repository"
	"tpops_deployment/internal/sshutil"
)

// Broadcaster 向 WebSocket 客户端推送事件（实现方应同时推 deploy 与 log 通道）。
type Broadcaster interface {
	Broadcast(taskID int64, payload map[string]interface{})
}

// ConfigSubset runner 所需配置子集。
type ConfigSubset struct {
	FernetSecret string
	PackagesDir  string // 本地安装包根目录（与上传存储一致）
}

func useAppctlForAction(action string) bool {
	switch strings.TrimSpace(action) {
	case "install", "upgrade", "uninstall_all", "precheck_install", "precheck_upgrade":
		return true
	default:
		return false
	}
}

// RunSSHDeployment 在后台执行：认领 pending→running、SSH 流式命令、可选 manifest 轮询、写库终态。
func RunSSHDeployment(
	bg context.Context,
	taskID int64,
	starterUserID int64,
	repos *repository.Repos,
	cfg ConfigSubset,
	hub Broadcaster,
	manifestFn func(context.Context, int64, int64) (map[string]interface{}, error),
) {
	go func() {
		ctx, cancel := context.WithCancel(bg)
		defer cancel()

		t, err := repos.GetTaskByID(context.Background(), taskID)
		if err != nil || t == nil {
			return
		}

		emit := func(m map[string]interface{}) {
			if hub != nil {
				hub.Broadcast(taskID, m)
			}
		}

		emit(map[string]interface{}{"type": "phase", "phase": "preflight", "message": "准备执行"})

		claimed, err := repos.UpdateTaskRunning(context.Background(), taskID)
		if err != nil || !claimed {
			emit(map[string]interface{}{"type": "log", "line": "[local] 任务未处于 pending 或已被其他进程认领，跳过执行"})
			return
		}

		host, err := repos.GetHostByID(context.Background(), t.HostID)
		if err != nil || host == nil {
			_ = repos.UpdateTaskFinished(context.Background(), taskID, "failed", intPtr(1), "执行机不存在")
			emit(donePayload("failed", 1, "执行机不存在"))
			return
		}

		secret, err := crypto.DecryptFernetCredential(cfg.FernetSecret, host.Credential)
		if err != nil || secret == "" {
			msg := "无法解密 SSH 凭证"
			if err != nil {
				msg = err.Error()
			}
			_ = repos.UpdateTaskFinished(context.Background(), taskID, "failed", intPtr(1), msg)
			emit(donePayload("failed", 1, msg))
			return
		}

		deployRoot := deploypaths.DeployRoot(host.DockerServiceRoot)
		logRel := strings.TrimSpace(t.RemoteLogPath)
		if logRel == "" {
			logRel = fmt.Sprintf("logs/deploy_%d.log", taskID)
		}
		absLog := deploypaths.AbsolutePath(host.DockerServiceRoot, logRel)

		if err := SyncPackagesToRemote(ctx, repos, cfg.PackagesDir, host, secret, t, emit); err != nil {
			_ = repos.UpdateTaskFinished(context.Background(), taskID, "failed", intPtr(1), err.Error())
			emit(donePayload("failed", 1, err.Error()))
			return
		}

		if err := PushUserEditToRemote(ctx, host, secret, t, emit); err != nil {
			_ = repos.UpdateTaskFinished(context.Background(), taskID, "failed", intPtr(1), err.Error())
			emit(donePayload("failed", 1, err.Error()))
			return
		}

		cmdLine := BuildRemoteCommand(host.DockerServiceRoot, t.Action, t.Target, useAppctlForAction(t.Action))

		inner := fmt.Sprintf(
			`set -o pipefail; LOG=%s; mkdir -p "$(dirname "$LOG")"; cd %s; { %s; } 2>&1 | tee -a "$LOG"; exit ${PIPESTATUS[0]}`,
			sshutil.ShellQuote(absLog),
			sshutil.ShellQuote(deployRoot),
			cmdLine,
		)
		remoteScript := "bash -lc " + sshutil.ShellQuote(inner)

		emit(map[string]interface{}{"type": "phase", "phase": "run_appctl", "message": "SSH 执行中"})
		emit(map[string]interface{}{"type": "status", "data": "running", "message": ""})

		action := strings.TrimSpace(t.Action)
		needManifest := action == "install" || action == "upgrade"

		var wg sync.WaitGroup
		if needManifest && manifestFn != nil {
			emit(map[string]interface{}{"type": "phase", "phase": "manifest_polling", "message": "轮询 manifest"})
			wg.Add(1)
			go func() {
				defer wg.Done()
				tick := time.NewTicker(5 * time.Second)
				defer tick.Stop()
				for {
					select {
					case <-ctx.Done():
						return
					case <-tick.C:
						tree, err := manifestFn(context.Background(), starterUserID, taskID)
						if err != nil {
							reason := trimErr(err)
							emit(map[string]interface{}{"type": "manifest_wait", "reason": reason, "message": reason})
							continue
						}
						emit(map[string]interface{}{"type": "manifest", "data": tree, "manifest": tree})
					}
				}
			}()
		}

		logEmit := func(line string) {
			emit(map[string]interface{}{"type": "log", "line": line, "data": line + "\n"})
		}
		exitCode, runErr := sshutil.RunRemoteStream(ctx, host.Hostname, host.Port, host.Username, host.AuthMethod, secret, remoteScript,
			logEmit, logEmit,
		)

		cancel()
		wg.Wait()

		if needManifest && manifestFn != nil {
			if tree, err := manifestFn(context.Background(), starterUserID, taskID); err == nil && tree != nil {
				emit(map[string]interface{}{"type": "manifest", "data": tree, "manifest": tree})
			}
		}

		if runErr != nil {
			if runErr == context.Canceled {
				_ = repos.UpdateTaskFinished(context.Background(), taskID, "cancelled", intPtr(-1), "已取消")
				emit(donePayload("cancelled", -1, ""))
				return
			}
			msg := runErr.Error()
			_ = repos.UpdateTaskFinished(context.Background(), taskID, "failed", intPtr(exitCode), msg)
			emit(donePayload("failed", exitCode, msg))
			return
		}

		st := "success"
		if exitCode != 0 {
			st = "failed"
		}
		_ = repos.UpdateTaskFinished(context.Background(), taskID, st, intPtr(exitCode), "")
		emit(donePayload(st, exitCode, ""))
	}()
}

func donePayload(status string, exitCode int, msg string) map[string]interface{} {
	finished := time.Now().UTC().Format(time.RFC3339Nano)
	return map[string]interface{}{
		"type": "done", "status": status,
		"exit_code": exitCode, "error_message": msg,
		"finished_at": finished,
	}
}

func intPtr(v int) *int { return &v }

func trimErr(err error) string {
	s := err.Error()
	if len(s) > 200 {
		return s[:200]
	}
	return s
}
