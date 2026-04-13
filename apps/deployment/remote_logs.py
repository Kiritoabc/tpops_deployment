"""
远程 deploy 目录下日志增量读取（precheck.log / install.log）。
"""
import shlex


def log_kind_for_action(action: str) -> str:
    if not action:
        return "precheck"
    if str(action).startswith("precheck"):
        return "precheck"
    if action == "installl" or action == "upgrade":
        return "install"
    return "precheck"


def remote_log_path(log_path: str, kind: str) -> str:
    base = (log_path or "").strip().rstrip("/")
    if not base:
        return ""
    return "%s/deploy/%s.log" % (base, kind)


def tail_remote_log_chunk(
    hostname: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    remote_log: str,
    offset: int,
    max_bytes: int = 65536,
    timeout: int = 30,
):
    """
    从 offset（字节）起读取远程文件。stdout 为纯文本增量；最后一行固定为 __META__ new_offset has_more
    """
    if not remote_log:
        return "", offset, True

    one = (
        "import os,sys\n"
        "p=os.environ['LOGF']\n"
        "off=int(os.environ['OFF'])\n"
        "mx=int(os.environ['MX'])\n"
        "if not os.path.isfile(p):\n"
        " print('__META__ %d 0 0'%(off)); sys.exit(3)\n"
        "sz=os.path.getsize(p)\n"
        "if off>sz: off=sz\n"
        "with open(p,'rb') as f:\n"
        " f.seek(off)\n"
        " data=f.read(mx)\n"
        "sys.stdout.buffer.write(data)\n"
        "new=off+len(data)\n"
        "more=1 if new<sz else 0\n"
        "print('\\n__META__ %d %d'%(new,more))\n"
    )
    inner = "export LOGF=%s OFF=%s MX=%s; python3 -c %s" % (
        shlex.quote(remote_log),
        int(offset),
        int(max_bytes),
        shlex.quote(one),
    )
    cmd = "sh -c %s" % shlex.quote(inner)
    from apps.hosts.ssh_client import run_remote_command_output

    raw, code = run_remote_command_output(
        hostname, port, username, auth_method, secret, cmd, timeout=timeout
    )
    if code == 3:
        return "", offset, True
    text = raw.replace("\r\n", "\n")
    idx = text.rfind("\n__META__ ")
    if idx < 0:
        return raw, offset, False
    body = text[:idx]
    tail = text[idx + 1 :].strip()
    new_off = offset
    try:
        parts = tail.split()
        if len(parts) >= 3:
            new_off = int(parts[1])
    except (ValueError, IndexError):
        pass
    return body, new_off, False
