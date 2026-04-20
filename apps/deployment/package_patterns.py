# -*- coding: utf-8 -*-
"""TPOPS GaussDB 安装介质文件名分类（与上传命名约定一致）。"""

import re

ROLE_TPOPS_SERVER = "tpops_server"
ROLE_OM_KERNEL = "om_kernel"
ROLE_OS_KERNEL = "os_kernel"
ROLE_UNKNOWN = "unknown"

# 远端 / 平台 basename 仅含安全字符（见 packages.models._safe_remote_basename）
# CPU 段后允许「无下划后缀」直接 .tar.gz，如 Kernel_x86_64.tar.gz
_RE_TPOPS = re.compile(
    r"^TPOPS-GaussDB-Server_(?P<cpu>[A-Za-z0-9_]+)(?:_.+)?\.tar\.gz$",
    re.IGNORECASE,
)
_RE_OM = re.compile(
    r"^DBS-GaussDB-Kernel_(?P<cpu>[A-Za-z0-9_]+)(?:_.+)?\.tar\.gz$",
    re.IGNORECASE,
)
# OS 内核：只固定前缀 DBS-GaussDB-{OS}-Kernel，其后版本/CPU 等由现场命名，不再强解析
_RE_OS = re.compile(
    r"^DBS-GaussDB-(?P<os>[A-Za-z0-9]+)-Kernel.*\.tar\.gz$",
    re.IGNORECASE,
)
# 经 _safe_remote_basename 等处理后连字符可能变成下划线
_RE_OS_UNDERSCORE = re.compile(
    r"^DBS_GaussDB_(?P<os>[A-Za-z0-9]+)_Kernel.*\.tar\.gz$",
    re.IGNORECASE,
)


def artifact_basename_for_classify(artifact):
    """
    与前端一致：优先 remote_basename；为空则用 original_name 的末段（部分历史数据）。
    """
    if artifact is None:
        return ""
    rb = (getattr(artifact, "remote_basename", None) or "").strip()
    if rb:
        return rb
    orig = (getattr(artifact, "original_name", None) or "").strip().replace("\\", "/")
    if not orig:
        return ""
    parts = orig.split("/")
    return (parts[-1] or "").strip()


def classify_package_basename(basename):
    """
    Returns dict: role, cpu, os, pattern_name

    os_kernel：仅解析 OS 段；``Kernel`` 之后不再强匹配 CPU/版本格式。
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
            "cpu": None,
            "os": m.group("os"),
            "pattern_name": "DBS-GaussDB-{OS}-Kernel*.tar.gz",
        }
    m = _RE_OS_UNDERSCORE.match(name)
    if m:
        return {
            "role": ROLE_OS_KERNEL,
            "cpu": None,
            "os": m.group("os"),
            "pattern_name": "DBS_GaussDB_{OS}_Kernel*.tar.gz",
        }
    return {"role": ROLE_UNKNOWN, "cpu": None, "os": None, "pattern_name": ""}
