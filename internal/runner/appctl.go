package runner

import (
	"fmt"
	"strings"

	"tpops_deployment/internal/deploypaths"
	"tpops_deployment/internal/sshutil"
)

// BuildRemoteCommand 返回在部署根下执行的 shell 片段（不含外层 cd/pipe）。
// useAppctlWrap：对已知 action 调用远端 **appctl.sh**（或兼容 appctl）`<子命令> <组件>`；否则执行 rawCmd。
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
	// 本服务不会上传脚本：远端须在部署根或 PATH 中已有 appctl.sh（主入口）或 appctl（兼容）。
	// 顺序：**appctl.sh 优先**，再回退 appctl。
	return fmt.Sprintf(`ROOT=%s; cd "$ROOT" || exit 1; run_appctl() {
  local a="$1" c="$2"
  if [ -f "$ROOT/appctl.sh" ]; then exec sh "$ROOT/appctl.sh" "$a" "$c"; fi
  if command -v appctl.sh >/dev/null 2>&1; then exec sh "$(command -v appctl.sh)" "$a" "$c"; fi
  if [ -x "$ROOT/appctl" ]; then exec "$ROOT/appctl" "$a" "$c"; fi
  if command -v appctl >/dev/null 2>&1; then exec appctl "$a" "$c"; fi
  echo "[TPOPS] 未找到 appctl.sh：请在部署根 %s 放置 appctl.sh（推荐），或将 appctl.sh 加入 PATH。Runner 不会随任务下发该脚本。" >&2
  exit 127
}; run_appctl %s %s`,
		qRoot, root, sub, qComp)
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
