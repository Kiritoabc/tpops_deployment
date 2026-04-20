package crypto

import (
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"time"

	fernet "github.com/fernet/fernet-go"
)

func fernetKeyFromAppSecret(appSecret string) (*fernet.Key, error) {
	if appSecret == "" {
		return nil, fmt.Errorf("应用主密钥未配置，无法加解密主机凭证")
	}
	sum := sha256.Sum256([]byte(appSecret))
	fkey := base64.URLEncoding.EncodeToString(sum[:])
	return fernet.DecodeKey(fkey)
}

// DecryptFernetCredential 使用应用主密钥：SHA256(appSecret) → urlsafe b64 → Fernet 解密。
func DecryptFernetCredential(appSecret, token string) (string, error) {
	if token == "" {
		return "", nil
	}
	k, err := fernetKeyFromAppSecret(appSecret)
	if err != nil {
		return "", fmt.Errorf("TPOPS_GO_FERNET_SECRET 未配置，无法解密主机凭证")
	}
	msg := fernet.VerifyAndDecrypt([]byte(token), 0, []*fernet.Key{k})
	if msg == nil {
		return "", fmt.Errorf("凭证解密失败（请确认 TPOPS_GO_FERNET_SECRET 与加密时使用的应用密钥一致）")
	}
	return string(msg), nil
}

// EncryptFernetCredential 与 DecryptFernetCredential 使用相同密钥派生，加密明文凭证写入库。
func EncryptFernetCredential(appSecret, plaintext string) (string, error) {
	if plaintext == "" {
		return "", nil
	}
	k, err := fernetKeyFromAppSecret(appSecret)
	if err != nil {
		return "", err
	}
	tok, err := fernet.EncryptAndSign([]byte(plaintext), k)
	if err != nil {
		return "", err
	}
	return string(tok), nil
}

// DecryptFernetCredentialTTL 带 TTL 校验。
func DecryptFernetCredentialTTL(appSecret, token string, ttl time.Duration) (string, error) {
	if token == "" {
		return "", nil
	}
	k, err := fernetKeyFromAppSecret(appSecret)
	if err != nil {
		return "", fmt.Errorf("TPOPS_GO_FERNET_SECRET 未配置")
	}
	msg := fernet.VerifyAndDecrypt([]byte(token), ttl, []*fernet.Key{k})
	if msg == nil {
		return "", fmt.Errorf("凭证解密失败")
	}
	return string(msg), nil
}
