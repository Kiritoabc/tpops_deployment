# -*- coding: utf-8 -*-
"""TPOPS GaussDB 安装介质文件名分类（与上传命名约定一致）。"""

import re

ROLE_TPOPS_SERVER = "tpops_server"
ROLE_OM_KERNEL = "om_kernel"
ROLE_OS_KERNEL = "os_kernel"
ROLE_UNKNOWN = "unknown"

# 远端 / 平台 basename 仅含安全字符（见 packages.models._safe_remote_basename）
_RE_TPOPS = re.compile(
    r"^TPOPS-GaussDB-Server_(?P<cpu>[A-Za-z0-9_]+)_.+\.tar\.gz$",
    re.IGNORECASE,
)
_RE_OM = re.compile(
    r"^DBS-GaussDB-Kernel_(?P<cpu>[A-Za-z0-9_]+)_.+\.tar\.gz$",
    re.IGNORECASE,
)
_RE_OS = re.compile(
    r"^DBS-GaussDB-(?P<os>[A-Za-z0-9]+)-Kernel_(?P<cpu>[A-Za-z0-9_]+)_.+\.tar\.gz$",
    re.IGNORECASE,
)


def classify_package_basename(basename):
    """
    Returns dict: role, cpu, os (os 仅 os_kernel 角色), pattern_name
    """
    name = (basename or "").strip()
    if not name:
        return {"role": ROLE_UNKNOWN, "cpu": None, "os": None, "pattern_name": ""}

    m = _RE_TPOPS.match(name)
    if m:
        return {
            "role": ROLE_TPOPS_SERVER,
            "cpu": m.group("cpu"),
            "os": None,
            "pattern_name": "TPOPS-GaussDB-Server_{CPU}_*.tar.gz",
        }
    m = _RE_OM.match(name)
    if m:
        return {
            "role": ROLE_OM_KERNEL,
            "cpu": m.group("cpu"),
            "os": None,
            "pattern_name": "DBS-GaussDB-Kernel_{CPU}_*.tar.gz",
        }
    m = _RE_OS.match(name)
    if m:
        return {
            "role": ROLE_OS_KERNEL,
            "cpu": m.group("cpu"),
            "os": m.group("os"),
            "pattern_name": "DBS-GaussDB-{OS}-Kernel_{CPU}_*.tar.gz",
        }
    return {"role": ROLE_UNKNOWN, "cpu": None, "os": None, "pattern_name": ""}
