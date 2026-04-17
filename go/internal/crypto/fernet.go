package crypto

import (
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"time"

	fernet "github.com/fernet/fernet-go"
)

// DecryptFernetCredential 使用应用主密钥：SHA256(appSecret) → urlsafe b64 → Fernet 解密（与既有 Fernet 封装约定一致）。
func DecryptFernetCredential(appSecret, token string) (string, error) {
	if token == "" {
		return "", nil
	}
	if appSecret == "" {
		return "", fmt.Errorf("TPOPS_GO_FERNET_SECRET 未配置，无法解密主机凭证")
	}
	sum := sha256.Sum256([]byte(appSecret))
	fkey := base64.URLEncoding.EncodeToString(sum[:])
	k, err := fernet.DecodeKey(fkey)
	if err != nil {
		return "", err
	}
	msg := fernet.VerifyAndDecrypt([]byte(token), 0, []*fernet.Key{k})
	if msg == nil {
		return "", fmt.Errorf("凭证解密失败（请确认 TPOPS_GO_FERNET_SECRET 与加密时使用的应用密钥一致）")
	}
	return string(msg), nil
}

// DecryptFernetCredentialTTL 带 TTL 校验（一般凭证不过期，传 0 与上面等价）。
func DecryptFernetCredentialTTL(appSecret, token string, ttl time.Duration) (string, error) {
	if token == "" {
		return "", nil
	}
	if appSecret == "" {
		return "", fmt.Errorf("TPOPS_GO_FERNET_SECRET 未配置")
	}
	sum := sha256.Sum256([]byte(appSecret))
	fkey := base64.URLEncoding.EncodeToString(sum[:])
	k, err := fernet.DecodeKey(fkey)
	if err != nil {
		return "", err
	}
	msg := fernet.VerifyAndDecrypt([]byte(token), ttl, []*fernet.Key{k})
	if msg == nil {
		return "", fmt.Errorf("凭证解密失败")
	}
	return string(msg), nil
}
