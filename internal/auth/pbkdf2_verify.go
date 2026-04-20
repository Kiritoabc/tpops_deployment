package auth

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"errors"
	"strconv"
	"strings"

	"golang.org/x/crypto/pbkdf2"
)

// CheckPassword 校验 pbkdf2_sha256$ 格式密码（与常见 PBKDF2PasswordHasher 兼容）。
// encoded 形如: pbkdf2_sha256$<iter>$<salt>$<base64hash>
func CheckPassword(password, encoded string) (bool, error) {
	if encoded == "" {
		return false, errors.New("empty hash")
	}
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[0] != "pbkdf2_sha256" {
		return false, errors.New("unsupported password hasher (need pbkdf2_sha256)")
	}
	iter, err := strconv.Atoi(parts[1])
	if err != nil || iter < 1 {
		return false, errors.New("invalid iterations")
	}
	salt := parts[2]
	wantB64 := parts[3]
	want, err := base64.StdEncoding.DecodeString(wantB64)
	if err != nil {
		return false, err
	}
	dk := pbkdf2.Key([]byte(password), []byte(salt), iter, len(want), sha256.New)
	if subtle.ConstantTimeCompare(dk, want) == 1 {
		return true, nil
	}
	return false, nil
}
