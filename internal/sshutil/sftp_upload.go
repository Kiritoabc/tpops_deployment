package sshutil

import (
	"fmt"
	"io"
	"net"
	"os"
	"path"
	"strings"
	"time"

	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
)

// UploadFileSFTP 将本地文件上传到远端 remotePath（含目录创建）。
func UploadFileSFTP(hostname string, port int, username, authMethod, secret, localPath, remotePath string, timeout time.Duration) error {
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return err
	}
	if port <= 0 {
		port = 22
	}
	addr := fmt.Sprintf("%s:%d", hostname, port)
	d := net.Dialer{Timeout: 15 * time.Second}
	conn, err := d.Dial("tcp", addr)
	if err != nil {
		return fmt.Errorf("tcp: %w", err)
	}
	defer conn.Close()

	clientConn, chans, reqs, err := ssh.NewClientConn(conn, hostname, cfg)
	if err != nil {
		return fmt.Errorf("ssh: %w", err)
	}
	client := ssh.NewClient(clientConn, chans, reqs)
	defer client.Close()

	sftpClient, err := sftp.NewClient(client)
	if err != nil {
		return fmt.Errorf("sftp: %w", err)
	}
	defer sftpClient.Close()

	lf, err := os.Open(localPath)
	if err != nil {
		return err
	}
	defer lf.Close()

	remotePath = strings.TrimSpace(remotePath)
	remoteDir := path.Dir(remotePath)
	if remoteDir != "" && remoteDir != "." {
		if err := sftpClient.MkdirAll(remoteDir); err != nil {
			return fmt.Errorf("mkdir %s: %w", remoteDir, err)
		}
	}
	rf, err := sftpClient.Create(remotePath)
	if err != nil {
		return fmt.Errorf("create %s: %w", remotePath, err)
	}
	defer rf.Close()

	done := make(chan error, 1)
	go func() {
		_, err := io.Copy(rf, lf)
		done <- err
	}()
	select {
	case err := <-done:
		if err != nil {
			return err
		}
	case <-time.After(timeout):
		return fmt.Errorf("sftp 上传超时")
	}
	return nil
}
