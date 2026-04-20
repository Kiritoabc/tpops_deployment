package deploypaths

import "strings"

// DefaultUserEditRelativePath 未指定 remote_user_edit_path 时的默认相对路径（相对部署根）。
const DefaultUserEditRelativePath = "config/user_edit.conf"

// ResolveUserEditRemotePath 返回远端绝对路径；rel 为空时使用默认相对路径。
func ResolveUserEditRemotePath(deployRoot, rel string) string {
	rel = strings.TrimSpace(rel)
	if rel == "" {
		rel = DefaultUserEditRelativePath
	}
	return AbsolutePath(deployRoot, rel)
}
