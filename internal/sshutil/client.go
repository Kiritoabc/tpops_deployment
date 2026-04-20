package sshutil

import (
	"bytes"
	"fmt"
	"net"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
)

// CatRemoteFile 在远端执行 `sh -c 'if [ -f path ]; then cat path; fi'` 读取文件内容。
func CatRemoteFile(hostname string, port int, username, authMethod, secret, remotePath string, timeout time.Duration) (string, int, error) {
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return "", -1, err
	}
	addr := fmt.Sprintf("%s:%d", hostname, port)
	conn, err := net.DialTimeout("tcp", addr, 15*time.Second)
	if err != nil {
		return "", -1, err
	}
	defer conn.Close()
	clientConn, chans, reqs, err := ssh.NewClientConn(conn, hostname, cfg)
	if err != nil {
		return "", -1, err
	}
	client := ssh.NewClient(clientConn, chans, reqs)
	defer client.Close()

	sess, err := client.NewSession()
	if err != nil {
		return "", -1, err
	}
	defer sess.Close()
	inner := fmt.Sprintf("if [ -f %s ]; then cat %s; fi", shellQuote(remotePath), shellQuote(remotePath))
	cmd := "sh -c " + shellQuote(inner)
	var stdout, stderr bytes.Buffer
	sess.Stdout = &stdout
	sess.Stderr = &stderr
	_ = sess.Setenv("LANG", "C.UTF-8")
	done := make(chan error, 1)
	go func() {
		done <- sess.Run(cmd)
	}()
	select {
	case err := <-done:
		if err != nil {
			if x, ok := err.(*ssh.ExitError); ok {
				return strings.TrimSpace(stdout.String()), x.ExitStatus(), nil
			}
			return strings.TrimSpace(stdout.String()), -1, fmt.Errorf("%w: %s", err, stderr.String())
		}
		return strings.TrimSpace(stdout.String()), 0, nil
	case <-time.After(timeout):
		_ = sess.Close()
		return "", -1, fmt.Errorf("ssh cat 超时")
	}
}

// ShellQuote 单引号包裹，供 `sh -c` 拼接使用。
func ShellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", "'\"'\"'") + "'"
}

func shellQuote(s string) string { return ShellQuote(s) }

func clientConfig(username, authMethod, secret string) (*ssh.ClientConfig, error) {
	var auth []ssh.AuthMethod
	switch authMethod {
	case "key":
		signer, err := parsePrivateKey(secret)
		if err != nil {
			return nil, err
		}
		auth = append(auth, ssh.PublicKeys(signer))
	default:
		auth = append(auth, ssh.Password(secret))
	}
	return &ssh.ClientConfig{
		User:            username,
		Auth:            auth,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Timeout:         20 * time.Second,
	}, nil
}

func parsePrivateKey(pem string) (ssh.Signer, error) {
	s, err := ssh.ParsePrivateKey([]byte(pem))
	if err == nil {
		return s, nil
	}
	// try passphrase-less only
	return nil, fmt.Errorf("私钥解析失败: %w", err)
}
