package deploypaths

import (
	"fmt"

	"tpops_deployment/internal/sshutil"
)

// ResolveRemoteUserEditConfPath 在远端探测 user_edit 配置文件绝对路径（与 Python resolve_user_edit_conf_path 一致）。
// 依次：$ROOT/config/gaussdb/user_edit_file.conf、$ROOT/config/user_edit_file.conf
func ResolveRemoteUserEditConfPathScript(deployRoot string) string {
	root := DeployRoot(deployRoot)
	q := sshutil.ShellQuote(root)
	return fmt.Sprintf(`ROOT=%s; for p in "$ROOT/config/gaussdb/user_edit_file.conf" "$ROOT/config/user_edit_file.conf"; do if [ -f "$p" ]; then echo "$p"; exit 0; fi; done; echo NOTFOUND; exit 2`, q)
}
