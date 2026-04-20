package sshutil

import (
	"bytes"
	"fmt"
	"net"
	"time"

	"golang.org/x/crypto/ssh"
)

// RunShOutput 执行远端 `sh -c <inner>`，返回合并后的 stdout+stderr 文本与退出码。
func RunShOutput(hostname string, port int, username, authMethod, secret, inner string, timeout time.Duration) (string, int, error) {
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return "", -1, err
	}
	if port <= 0 {
		port = 22
	}
	addr := fmt.Sprintf("%s:%d", hostname, port)
	d := net.Dialer{Timeout: 15 * time.Second}
	conn, err := d.Dial("tcp", addr)
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
	cmd := "sh -c " + ShellQuote(inner)
	var stdout, stderr bytes.Buffer
	sess.Stdout = &stdout
	sess.Stderr = &stderr
	done := make(chan error, 1)
	go func() { done <- sess.Run(cmd) }()
	select {
	case err := <-done:
		out := stdout.String() + stderr.String()
		if err != nil {
			if x, ok := err.(*ssh.ExitError); ok {
				return out, x.ExitStatus(), nil
			}
			return out, -1, err
		}
		return out, 0, nil
	case <-time.After(timeout):
		_ = sess.Close()
		return "", -1, fmt.Errorf("ssh 命令超时")
	}
}
