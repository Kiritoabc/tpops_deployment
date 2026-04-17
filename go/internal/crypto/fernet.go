package crypto

import (
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"time"

	fernet "github.com/fernet/fernet-go"
)

// DecryptFernetCredential 与 Django apps/hosts/crypto.py 一致：SHA256(SECRET_KEY) → urlsafe b64 → Fernet 解密。
func DecryptFernetCredential(djangoSecretKey, token string) (string, error) {
	if token == "" {
		return "", nil
	}
	if djangoSecretKey == "" {
		return "", fmt.Errorf("FERNET/SECRET 未配置，无法解密主机凭证")
	}
	sum := sha256.Sum256([]byte(djangoSecretKey))
	fkey := base64.URLEncoding.EncodeToString(sum[:])
	k, err := fernet.DecodeKey(fkey)
	if err != nil {
		return "", err
	}
	msg := fernet.VerifyAndDecrypt([]byte(token), 0, []*fernet.Key{k})
	if msg == nil {
		return "", fmt.Errorf("凭证解密失败（密钥是否与 Django SECRET_KEY 一致？）")
	}
	return string(msg), nil
}

// DecryptFernetCredentialTTL 带 TTL 校验（一般凭证不过期，传 0 与上面等价）。
func DecryptFernetCredentialTTL(djangoSecretKey, token string, ttl time.Duration) (string, error) {
	if token == "" {
		return "", nil
	}
	if djangoSecretKey == "" {
		return "", fmt.Errorf("FERNET/SECRET 未配置")
	}
	sum := sha256.Sum256([]byte(djangoSecretKey))
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
