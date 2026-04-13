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
    get_pty: bool = True,
):
    """
    流式输出 stdout/stderr（小块及时 yield，便于 WebSocket 实时推送）。
    末尾追加 __EXIT_CODE__:N

    get_pty: 长时间跑脚本（如 appctl）建议 False，避免 PTY 下部分环境合并/延迟
    stderr，或与第二条并发 SSH 信道互相影响；短命令可 True。
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
            command, get_pty=get_pty, timeout=timeout
        )
        stdin.close()
        ch = stdout.channel

        while True:
            while ch.recv_ready():
                data = ch.recv(4096)
                if data:
                    yield data.decode("utf-8", errors="replace")
            while ch.recv_stderr_ready():
                data = ch.recv_stderr(4096)
                if data:
                    yield data.decode("utf-8", errors="replace")
            if ch.exit_status_ready():
                break
            select.select([ch], [], [], 0.05)

        while ch.recv_ready():
            data = ch.recv(4096)
            if data:
                yield data.decode("utf-8", errors="replace")
        while ch.recv_stderr_ready():
            data = ch.recv_stderr(4096)
            if data:
                yield data.decode("utf-8", errors="replace")

        exit_code = ch.recv_exit_status()
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
    get_pty: bool = False,
):
    """Run remote command and return (stdout+stderr text without marker, exit_code)."""
    buf = []
    exit_code = -1
    for chunk in run_remote_command(
        hostname,
        port,
        username,
        auth_method,
        secret,
        command,
        timeout=timeout,
        get_pty=get_pty,
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
    cmd = "sh -c %s" % shlex.quote(inner)
    return run_remote_command_output(
        hostname,
        port,
        username,
        auth_method,
        secret,
        cmd,
        timeout=timeout,
        get_pty=False,
    )


def remote_mkdir_p(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    remote_dir: str,
    timeout: int = 60,
):
    inner = "mkdir -p %s" % shlex.quote(remote_dir)
    cmd = "sh -c %s" % shlex.quote(inner)
    _out, code = run_remote_command_output(
        hostname, port, username, auth_method, secret, cmd, timeout=timeout
    )
    return code == 0


def resolve_user_edit_conf_path(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    deploy_root: str,
    timeout: int = 60,
):
    """
    在远程依次检测:
      <root>/config/gaussdb/user_edit_file.conf
      <root>/config/user_edit_file.conf
    返回存在的第一个绝对路径；均不存在则 (None, 错误信息)。
    """
    root = (deploy_root or "").strip().rstrip("/")
    if not root:
        return None, "部署根目录为空"

    inner = (
        "ROOT=%s; "
        'for p in "$ROOT/config/gaussdb/user_edit_file.conf" "$ROOT/config/user_edit_file.conf"; do '
        "if [ -f \"$p\" ]; then echo \"$p\"; exit 0; fi; "
        "done; echo NOTFOUND; exit 2"
    ) % shlex.quote(root)
    cmd = "sh -c %s" % shlex.quote(inner)
    out, code = run_remote_command_output(
        hostname, port, username, auth_method, secret, cmd, timeout=timeout
    )
    path = out.strip()
    if code == 0 and path and path != "NOTFOUND":
        return path, None
    return None, (
        "未找到 user_edit_file.conf（已检查 %s/config/gaussdb/ 与 %s/config/）"
        % (root, root)
    )


def write_remote_file_utf8(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    remote_path: str,
    content: str,
):
    """
    通过 SFTP 将 UTF-8 文本原子写入远程路径（先 .tmp 再 rename）。
    返回 (ok: bool, message: str)
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
    tmp = "%s.tmp.%d" % (remote_path, id(client))
    sftp = None
    try:
        sftp = client.open_sftp()
        data = content.encode("utf-8")
        with sftp.open(tmp, "wb") as remote_f:
            remote_f.write(data)
        try:
            sftp.remove(remote_path)
        except IOError:
            pass
        sftp.rename(tmp, remote_path)
        return True, "ok"
    except Exception as exc:
        if sftp is not None:
            try:
                sftp.remove(tmp)
            except Exception:
                pass
        return False, str(exc)
    finally:
        if sftp is not None:
            try:
                sftp.close()
            except Exception:
                pass
        try:
            client.close()
        except Exception:
            pass
