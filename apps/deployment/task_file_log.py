# -*- coding: utf-8 -*-
"""部署任务本地文件日志（与 WebSocket 并行，便于事后排查）。"""

import os
import threading
import time
from typing import Optional, TextIO

from django.conf import settings

_lock = threading.RLock()
_handles = {}  # task_id -> TextIO


def _log_dir() -> str:
    root = getattr(settings, "DEPLOYMENT_TASK_LOG_DIR", None)
    if root:
        return str(root)
    return os.path.join(settings.BASE_DIR, "logs", "deployment_tasks")


def open_task_log(task_id: int) -> Optional[TextIO]:
    """为任务打开追加日志文件；同一 task_id 只打开一次。"""
    d = _log_dir()
    with _lock:
        if task_id in _handles:
            return _handles[task_id]
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            return None
        path = os.path.join(d, "task_%s.log" % task_id)
        try:
            fp = open(path, "a", encoding="utf-8", buffering=1)
        except OSError:
            return None
        fp.write(
            "\n===== task %s opened %s =====\n"
            % (task_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        )
        fp.flush()
        _handles[task_id] = fp
        return fp


def write_task_log(task_id: int, line: str) -> None:
    if not line:
        return
    with _lock:
        fp = _handles.get(task_id)
    if not fp:
        return
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        fp.write("%s %s" % (ts, line if line.endswith("\n") else line + "\n"))
        fp.flush()
    except OSError:
        pass


def close_task_log(task_id: int) -> None:
    with _lock:
        fp = _handles.pop(task_id, None)
    if fp:
        try:
            fp.write(
                "===== task %s closed %s =====\n"
                % (task_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            )
            fp.close()
        except OSError:
            pass
