import io
import select
import shlex
import socket

import paramiko

from .models import Host


def _load_pkey(secret: str):
    """Try common key types for Paramiko."""
    buf = io.StringIO(secret)
    for loader in (
        paramiko.RSAKey.from_private_key,
        paramiko.Ed25519Key.from_private_key,
        paramiko.ECDSAKey.from_private_key,
    ):
        try:
            buf.seek(0)
            return loader(buf)
        except Exception:
            continue
    raise ValueError("无法解析私钥（支持 RSA / Ed25519 / ECDSA）")


def test_ssh_connection(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    timeout: int = 15,
):
    """
    Returns (ok: bool, message: str)
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = {
            "hostname": hostname,
            "port": port,
            "username": username,
            "timeout": timeout,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if auth_method == Host.AUTH_KEY:
            connect_kwargs["pkey"] = _load_pkey(secret)
        else:
            connect_kwargs["password"] = secret
        client.connect(**connect_kwargs)
        return True, "连接成功"
    except (paramiko.SSHException, socket.error, ValueError) as exc:
        return False, str(exc)
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_remote_command(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    command: str,
    timeout: int = 3600,
):
    """
    Yields decoded stdout/stderr chunks from remote command (streaming).
    Appends a final line __EXIT_CODE__:N for the caller to parse.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": hostname,
        "port": port,
        "username": username,
        "timeout": 30,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if auth_method == Host.AUTH_KEY:
        connect_kwargs["pkey"] = _load_pkey(secret)
    else:
        connect_kwargs["password"] = secret

    client.connect(**connect_kwargs)
    try:
        stdin, stdout, stderr = client.exec_command(
            command, get_pty=True, timeout=timeout
        )
        stdin.close()
        channel = stdout.channel

        while True:
            if channel.exit_status_ready() and not channel.recv_ready():
                if not channel.recv_stderr_ready():
                    break
            rlist, _, _ = select.select([channel], [], [], 1.0)
            if channel in rlist:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        yield data.decode("utf-8", errors="replace")
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096)
                    if data:
                        yield data.decode("utf-8", errors="replace")

        while channel.recv_ready():
            data = channel.recv(4096)
            if data:
                yield data.decode("utf-8", errors="replace")
        while channel.recv_stderr_ready():
            data = channel.recv_stderr(4096)
            if data:
                yield data.decode("utf-8", errors="replace")

        exit_code = channel.recv_exit_status()
        yield "\n__EXIT_CODE__:%s\n" % exit_code
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_remote_command_output(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    command: str,
    timeout: int = 120,
):
    """Run remote command and return (stdout+stderr text without marker, exit_code)."""
    buf = []
    exit_code = -1
    for chunk in run_remote_command(
        hostname, port, username, auth_method, secret, command, timeout=timeout
    ):
        if "__EXIT_CODE__:" in chunk:
            parts = chunk.split("__EXIT_CODE__:")
            buf.append(parts[0])
            tail = parts[-1].strip()
            try:
                exit_code = int(tail)
            except ValueError:
                exit_code = -1
        else:
            buf.append(chunk)
    text = "".join(buf)
    text = text.replace("\n__EXIT_CODE__:%s\n" % exit_code, "")
    return text, exit_code


def remote_cat_file(hostname, port, username, auth_method, secret, remote_path, timeout=60):
    """Best-effort read remote file via shell."""
    inner = "if [ -f %s ]; then cat %s; fi" % (
        shlex.quote(remote_path),
        shlex.quote(remote_path),
    )
    cmd = "bash -lc %s" % shlex.quote(inner)
    return run_remote_command_output(
        hostname, port, username, auth_method, secret, cmd, timeout=timeout
    )
