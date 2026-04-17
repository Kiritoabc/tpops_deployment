package deploypaths

import (
	"fmt"
	"strings"

	"github.com/Kiritoabc/tpops_deployment/go/internal/useredit"
)

const ModeTriple = "triple"

func DeployRoot(dockerRoot string) string {
	r := strings.TrimSpace(strings.TrimSuffix(dockerRoot, "/"))
	if r == "" {
		return "/data/docker-service"
	}
	return r
}

// RemoteManifestPaths 与 Python _remote_manifest_paths_for_task 一致（相对路径，SSH 时拼 ROOT）。
func RemoteManifestPaths(deployRoot, deployMode string, kv map[string]string) []string {
	root := DeployRoot(deployRoot)
	base := fmt.Sprintf("%s/config/gaussdb", root)
	var paths []string
	seen := map[string]struct{}{}
	add := func(p string) {
		if _, ok := seen[p]; !ok {
			seen[p] = struct{}{}
			paths = append(paths, p)
		}
	}
	if deployMode != ModeTriple {
		add(base + "/manifest.yaml")
		return paths
	}
	n2 := strings.TrimSpace(kv["node2_ip"])
	n3 := strings.TrimSpace(kv["node3_ip"])
	add(base + "/manifest.yaml")
	if n2 != "" {
		add(fmt.Sprintf("%s/manifest_%s.yaml", base, n2))
	}
	if n3 != "" {
		add(fmt.Sprintf("%s/manifest_%s.yaml", base, n3))
	}
	return paths
}

// AbsolutePath 将相对路径拼到部署根下（远端 cat 用）。
func AbsolutePath(deployRoot, rel string) string {
	root := DeployRoot(deployRoot)
	rel = strings.TrimPrefix(rel, "/")
	return root + "/" + rel
}

// Node1IP 从 user_edit kv 取 node1_ip。
func Node1IP(kv map[string]string) string {
	return strings.TrimSpace(kv["node1_ip"])
}

// ParseUserEditKV 从任务文本解析 [user_edit]。
func ParseUserEditKV(userEdit string) map[string]string {
	return useredit.ParseBlock(userEdit)
}
