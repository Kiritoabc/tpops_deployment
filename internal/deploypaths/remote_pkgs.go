package deploypaths

import "fmt"

// RemotePkgsDir 远端安装包目录（与部署根同级下的 pkgs/）。
func RemotePkgsDir(dockerRoot string) string {
	return AbsolutePath(dockerRoot, "pkgs")
}

// RemotePkgsFile 远端 pkgs 下某文件名（绝对路径）。
func RemotePkgsFile(dockerRoot, basename string) string {
	return fmt.Sprintf("%s/%s", RemotePkgsDir(dockerRoot), basename)
}
