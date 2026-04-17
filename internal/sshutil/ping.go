package sshutil

import (
	"fmt"
	"net"
	"time"

	"golang.org/x/crypto/ssh"
)

// TestConnection 尝试建立 SSH 会话并立即关闭，用于连通性检测。
func TestConnection(hostname string, port int, username, authMethod, secret string, dialTimeout, handshakeTimeout time.Duration) error {
	if port <= 0 {
		port = 22
	}
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return err
	}
	cfg.Timeout = handshakeTimeout
	addr := fmt.Sprintf("%s:%d", hostname, port)
	d := net.Dialer{Timeout: dialTimeout}
	conn, err := d.Dial("tcp", addr)
	if err != nil {
		return fmt.Errorf("TCP 连接失败: %w", err)
	}
	defer conn.Close()

	clientConn, chans, reqs, err := ssh.NewClientConn(conn, hostname, cfg)
	if err != nil {
		return fmt.Errorf("SSH 握手失败: %w", err)
	}
	client := ssh.NewClient(clientConn, chans, reqs)
	defer client.Close()

	sess, err := client.NewSession()
	if err != nil {
		return fmt.Errorf("无法创建会话: %w", err)
	}
	defer sess.Close()
	return nil
}
