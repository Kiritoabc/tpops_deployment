package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"io"

	"golang.org/x/crypto/pbkdf2"
)

const djangoPBKDF2Iterations = 260000 // Django 3.2 PBKDF2PasswordHasher 默认量级

// EncodePBKDF2Password 生成 Django 兼容的 pbkdf2_sha256$ 密文（新用户注册用）。
func EncodePBKDF2Password(password string) (string, error) {
	saltBytes := make([]byte, 11)
	if _, err := io.ReadFull(rand.Reader, saltBytes); err != nil {
		return "", err
	}
	salt := hex.EncodeToString(saltBytes)
	dk := pbkdf2.Key([]byte(password), []byte(salt), djangoPBKDF2Iterations, 32, sha256.New)
	hash := base64.StdEncoding.EncodeToString(dk)
	return fmt.Sprintf("pbkdf2_sha256$%d$%s$%s", djangoPBKDF2Iterations, salt, hash), nil
}
