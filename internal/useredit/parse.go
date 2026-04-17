package useredit

import (
	"regexp"
	"strings"
)

// ParseBlock 解析 [user_edit] 段 key=value（供 manifest 路径与校验使用）。
func ParseBlock(content string) map[string]string {
	kv := make(map[string]string)
	lines := strings.Split(strings.ReplaceAll(content, "\r\n", "\n"), "\n")
	in := false
	for _, line := range lines {
		s := strings.TrimSpace(line)
		if s == "" || strings.HasPrefix(s, "#") {
			continue
		}
		if strings.HasPrefix(s, "[") && strings.HasSuffix(s, "]") {
			sec := strings.ToLower(strings.TrimSpace(s[1 : len(s)-1]))
			if sec == "user_edit" {
				in = true
			} else if in {
				break
			}
			continue
		}
		if !in {
			continue
		}
		idx := strings.Index(line, "=")
		if idx < 0 {
			continue
		}
		k := strings.TrimSpace(line[:idx])
		v := strings.TrimSpace(line[idx+1:])
		if k != "" {
			kv[k] = v
		}
	}
	return kv
}

var reManifestIP = regexp.MustCompile(`manifest_([0-9.]+)\.yaml`)

// ManifestIPFromPath 从相对路径提取 manifest_<ip>.yaml 中的 IP。
func ManifestIPFromPath(p string) string {
	m := reManifestIP.FindStringSubmatch(p)
	if len(m) > 1 {
		return m[1]
	}
	return ""
}
