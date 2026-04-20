package remotelog

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"tpops_deployment/internal/sshutil"
	"tpops_deployment/internal/useredit"
)

var reSafeBasename = regexp.MustCompile(`^[a-zA-Z0-9._-]+$`)

// LogKindForAction 与 Python remote_logs.log_kind_for_action 对齐。
func LogKindForAction(action string) string {
	a := strings.TrimSpace(action)
	if a == "" {
		return "precheck"
	}
	if strings.HasPrefix(strings.ToLower(a), "precheck") {
		return "precheck"
	}
	if a == "install" || a == "upgrade" {
		return "install"
	}
	if a == "uninstall_all" {
		return "uninstall"
	}
	return "precheck"
}

// RemoteLogPath 返回 log_path/deploy/<kind>.log 绝对风格路径片段（相对 log_path 根）。
func RemoteLogPath(logPath, kind string) string {
	base := strings.TrimSpace(strings.TrimSuffix(logPath, "/"))
	if base == "" {
		return ""
	}
	k := strings.TrimSpace(kind)
	if k == "" {
		k = "precheck"
	}
	return fmt.Sprintf("%s/deploy/%s.log", base, k)
}

// RemoteDeployLogFile 返回 log_path/deploy/<basename>；basename 须安全。
func RemoteDeployLogFile(logPath, basename string) string {
	base := strings.TrimSpace(strings.TrimSuffix(logPath, "/"))
	b := strings.TrimSpace(basename)
	if base == "" || b == "" || !reSafeBasename.MatchString(b) {
		return ""
	}
	return fmt.Sprintf("%s/deploy/%s", base, b)
}

const tailPy = `import os,sys
p=os.environ["LOGF"]
off=int(os.environ["OFF"])
mx=int(os.environ["MX"])
if not os.path.isfile(p):
 print("__META__ %d 0 0"%(off)); sys.exit(3)
sz=os.path.getsize(p)
if off>sz: off=sz
with open(p,"rb") as f:
 f.seek(off)
 data=f.read(mx)
sys.stdout.buffer.write(data)
new=off+len(data)
more=1 if new<sz else 0
print("\n__META__ %d %d"%(new,more))
`

// TailRemoteLogChunk 与 Python tail_remote_log_chunk 一致：stdout 正文 + 末行 __META__ new more。
func TailRemoteLogChunk(hostname string, port int, username, authMethod, secret, remoteLog string, offset int64, maxBytes int, timeout time.Duration) (body string, newOffset int64, missing bool, err error) {
	if maxBytes <= 0 {
		maxBytes = 65536
	}
	if remoteLog == "" {
		return "", offset, true, nil
	}
	inner := fmt.Sprintf("export LOGF=%s OFF=%d MX=%d; python3 -c %s",
		sshutil.ShellQuote(remoteLog), offset, maxBytes, sshutil.ShellQuote(tailPy))
	raw, code, err := sshutil.RunShOutput(hostname, port, username, authMethod, secret, inner, timeout)
	if err != nil {
		return "", offset, false, err
	}
	if code == 3 {
		return "", offset, true, nil
	}
	text := strings.ReplaceAll(raw, "\r\n", "\n")
	idx := strings.LastIndex(text, "\n__META__ ")
	if idx < 0 {
		return raw, offset, false, nil
	}
	body = text[:idx]
	tail := strings.TrimSpace(text[idx+1:])
	newOffset = offset
	parts := strings.Fields(tail)
	if len(parts) >= 3 {
		if v, e := strconv.ParseInt(parts[1], 10, 64); e == nil {
			newOffset = v
		}
	}
	return body, newOffset, false, nil
}

// ResolveRemoteLogPath 从任务 user_edit 与 query 参数得到远端日志绝对路径。
func ResolveRemoteLogPath(userEdit, kind, relFile string) (rpath string, err error) {
	kv := useredit.ParseBlock(userEdit)
	lp := strings.TrimSpace(kv["log_path"])
	if lp == "" {
		return "", fmt.Errorf("无法解析 log_path：请在 user_edit 中配置 log_path")
	}
	if strings.TrimSpace(relFile) != "" {
		r := RemoteDeployLogFile(lp, relFile)
		if r == "" {
			return "", fmt.Errorf("非法 rel 文件名")
		}
		return r, nil
	}
	k := strings.TrimSpace(kind)
	if k != "precheck" && k != "install" && k != "uninstall" {
		k = "precheck"
	}
	r := RemoteLogPath(lp, k)
	if r == "" {
		return "", fmt.Errorf("log_path 为空")
	}
	return r, nil
}
