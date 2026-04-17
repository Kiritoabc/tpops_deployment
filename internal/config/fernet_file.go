package config

import (
	"crypto/rand"
	"encoding/base64"
	"os"
	"path/filepath"
)

// ensureFernetSecret 若环境变量未提供 Fernet 密钥，则从 data/.fernet_secret 读取或生成并写入（仅本地开发便利；生产务必设置 TPOPS_GO_FERNET_SECRET）。
func ensureFernetSecret(goRoot, current string) string {
	if current != "" {
		return current
	}
	p := filepath.Join(goRoot, "data", ".fernet_secret")
	b, err := os.ReadFile(p)
	if err == nil && len(b) > 0 {
		return string(b)
	}
	// 随机 32 字节 → urlsafe base64，作为应用密钥参与 SHA256 派生（与 Decrypt 路径一致）
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return ""
	}
	secret := base64.RawURLEncoding.EncodeToString(buf)
	_ = os.MkdirAll(filepath.Dir(p), 0o700)
	tmp := p + ".tmp"
	if err := os.WriteFile(tmp, []byte(secret), 0o600); err != nil {
		return ""
	}
	if err := os.Rename(tmp, p); err != nil {
		_ = os.Remove(tmp)
		return ""
	}
	return secret
}
