package runner

import (
	"fmt"
	"strings"

	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/sshutil"
)

// BuildRemoteCommand 返回在部署根下执行的 shell 片段（不含外层 cd/pipe）。
// useAppctlWrap：对已知 action 调用 appctl <subcommand> <component>；否则执行 rawCmd。
func BuildRemoteCommand(deployRoot, action, rawCmd string, useAppctlWrap bool) string {
	root := deploypaths.DeployRoot(deployRoot)
	action = strings.TrimSpace(action)
	rawCmd = strings.TrimSpace(rawCmd)
	if !useAppctlWrap {
		if rawCmd == "" {
			return `echo "[TPOPS] 未配置 target 远程命令，跳过"`
		}
		return rawCmd
	}
	component := rawCmd
	if component == "" {
		component = "gaussdb"
	}
	sub := appctlSubcommand(action)
	qRoot := sshutil.ShellQuote(root)
	qComp := sshutil.ShellQuote(component)
	// 优先 $ROOT/appctl，其次 PATH
	return fmt.Sprintf(`ROOT=%s; cd "$ROOT" || exit 1; if [ -x "$ROOT/appctl" ]; then exec "$ROOT/appctl" %s %s; elif command -v appctl >/dev/null 2>&1; then exec appctl %s %s; else echo "[TPOPS] 未找到 appctl" >&2; exit 127; fi`,
		qRoot, sub, qComp, sub, qComp)
}

func appctlSubcommand(action string) string {
	switch strings.TrimSpace(action) {
	case "install":
		return "install"
	case "upgrade":
		return "upgrade"
	case "uninstall_all":
		return "uninstall_all"
	case "precheck_install":
		return "precheck_install"
	case "precheck_upgrade":
		return "precheck_upgrade"
	default:
		return sshutil.ShellQuote(action)
	}
}
