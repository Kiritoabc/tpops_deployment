"""
解析 / 改写 user_edit_file.conf 风格的 [user_edit] 段落（key = value）。
"""
import re
from typing import Dict, List, Optional, Tuple


def parse_user_edit_block(content: str) -> Tuple[Dict[str, str], Optional[str]]:
    if not content or not content.strip():
        return {}, "配置内容为空"

    lines = content.replace("\r\n", "\n").split("\n")
    in_section = False
    kv = {}
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].strip().lower()
            if sec == "user_edit":
                in_section = True
                continue
            if in_section:
                break
            continue
        if not in_section:
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip()
        val = v.strip()
        if key:
            kv[key] = val

    if not kv and "[user_edit]" not in content.lower():
        return {}, "未找到 [user_edit] 段落，请按模板以 [user_edit] 开头填写"

    return kv, None


def _extract_user_edit_block(content: str) -> Tuple[str, str, str]:
    """
    拆成 (prefix, body_lines_only, suffix)。
    body 为 [user_edit] 之后到下一个 [xxx] 之前（不含下一节标题行）。
    """
    text = content.replace("\r\n", "\n")
    m = re.search(r"(?is)(\n*\[user_edit\]\s*\n)(.*?)(?=\n\s*\[[^\]]+\]\s*\n|\Z)", text)
    if not m:
        return text, "", ""
    prefix = text[: m.end(1)]
    body = m.group(2)
    suffix = text[m.end(0) :]
    return prefix, body, suffix


def _body_set_keys(body: str, updates: Dict[str, str]) -> str:
    """在 body 内按行替换或追加 key = value。"""
    lines = body.split("\n") if body else []
    keys_lower = {k.lower(): k for k in updates}
    seen = {k.lower(): False for k in updates}
    out = []
    for line in lines:
        if "=" not in line:
            out.append(line)
            continue
        k, sep, v = line.partition("=")
        key = k.strip()
        lk = key.lower()
        if lk in keys_lower:
            canon = keys_lower[lk]
            out.append("%s = %s" % (canon, updates[canon]))
            seen[lk] = True
        else:
            out.append(line)
    tail = []
    for lk, done in seen.items():
        if not done:
            canon = keys_lower[lk]
            tail.append("%s = %s" % (canon, updates[canon]))
    if tail:
        if out and out[-1].strip():
            out.append("")
        out.extend(tail)
    return "\n".join(out)


def apply_host_ips_to_config(
    content: str,
    deploy_mode: str,
    host_ips: List[str],
) -> str:
    """
    可选：用 SSH 登记的主机名覆盖配置中的 node IP（当前产品逻辑已不使用，保留供脚本/扩展调用）。
    """
    prefix, body, suffix = _extract_user_edit_block(content)
    if "[user_edit]" not in content.lower():
        return content

    if deploy_mode == "single":
        ip = host_ips[0] if host_ips else ""
        updates = {"node1_ip": ip, "node1_ip2": ip}
    else:
        hips = list(host_ips)
        while len(hips) < 3:
            hips.append(hips[-1] if hips else "")
        n1, n2, n3 = hips[0], hips[1], hips[2]
        updates = {
            "node1_ip": n1,
            "node2_ip": n2,
            "node3_ip": n3,
            "node1_ip2": n1,
            "node2_ip2": n2,
            "node3_ip2": n3,
            "influxdb_install_ip1": n1,
            "influxdb_install_ip2": n2,
            "sftp_install_ip1": n1,
            "sftp_install_ip2": n2,
        }

    if not prefix:
        prefix = "[user_edit]\n"
    new_body = _body_set_keys(body, updates)
    return prefix + new_body + suffix
