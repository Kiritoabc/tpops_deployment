package sshutil

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"net"
	"strings"
	"sync"
	"time"

	"golang.org/x/crypto/ssh"
)

// RunRemoteStream 在远端执行 remoteScript（通常为 `sh -lc '...'`），按行回调 stdout/stderr。
// 在 ctx 取消时关闭 session；返回进程退出码（若无法取得则为 -1）。
func RunRemoteStream(ctx context.Context, hostname string, port int, username, authMethod, secret, remoteScript string, onStdout, onStderr func(string)) (int, error) {
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return -1, err
	}
	addr := fmt.Sprintf("%s:%d", hostname, port)
	d := net.Dialer{Timeout: 15 * time.Second}
	conn, err := d.DialContext(ctx, "tcp", addr)
	if err != nil {
		return -1, err
	}
	defer conn.Close()

	clientConn, chans, reqs, err := ssh.NewClientConn(conn, hostname, cfg)
	if err != nil {
		return -1, err
	}
	client := ssh.NewClient(clientConn, chans, reqs)
	defer client.Close()

	sess, err := client.NewSession()
	if err != nil {
		return -1, err
	}
	defer sess.Close()

	stdout, err := sess.StdoutPipe()
	if err != nil {
		return -1, err
	}
	stderr, err := sess.StderrPipe()
	if err != nil {
		return -1, err
	}

	if err := sess.Start(remoteScript); err != nil {
		return -1, err
	}

	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		scanLines(ctx, stdout, onStdout)
	}()
	go func() {
		defer wg.Done()
		scanLines(ctx, stderr, onStderr)
	}()

	wait := make(chan error, 1)
	go func() {
		wait <- sess.Wait()
	}()

	select {
	case <-ctx.Done():
		_ = sess.Close()
		wg.Wait()
		return -1, ctx.Err()
	case err := <-wait:
		wg.Wait()
		if err != nil {
			if x, ok := err.(*ssh.ExitError); ok {
				return x.ExitStatus(), nil
			}
			return -1, err
		}
		return 0, nil
	}
}

func scanLines(ctx context.Context, r io.Reader, fn func(string)) {
	if fn == nil {
		return
	}
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for sc.Scan() {
		select {
		case <-ctx.Done():
			return
		default:
		}
		line := strings.TrimRight(sc.Text(), "\r")
		fn(line)
	}
}

// TailRemoteFile 在远端 `tail -n 200 -F path` 流式输出，直到 ctx 取消或连接错误。
func TailRemoteFile(ctx context.Context, hostname string, port int, username, authMethod, secret, remotePath string, onLine func(string)) error {
	cfg, err := clientConfig(username, authMethod, secret)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", hostname, port)
	d := net.Dialer{Timeout: 15 * time.Second}
	conn, err := d.DialContext(ctx, "tcp", addr)
	if err != nil {
		return err
	}
	defer conn.Close()

	clientConn, chans, reqs, err := ssh.NewClientConn(conn, hostname, cfg)
	if err != nil {
		return err
	}
	client := ssh.NewClient(clientConn, chans, reqs)
	defer client.Close()

	sess, err := client.NewSession()
	if err != nil {
		return err
	}
	defer sess.Close()

	inner := "tail -n 200 -F " + ShellQuote(remotePath) + " 2>&1"
	cmd := "sh -c " + ShellQuote(inner)

	stdout, err := sess.StdoutPipe()
	if err != nil {
		return err
	}
	if err := sess.Start(cmd); err != nil {
		return err
	}

	errCh := make(chan error, 1)
	go func() {
		scanLines(ctx, stdout, onLine)
		errCh <- sess.Wait()
	}()
	select {
	case <-ctx.Done():
		_ = sess.Close()
		return ctx.Err()
	case err := <-errCh:
		return err
	}
}
