import os
import re
import threading

import yaml

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.hosts.serializers import host_ssh_secret
from apps.hosts.ssh_client import (
    remote_mkdir_p,
    resolve_user_edit_conf_path,
    remote_cat_file,
    run_remote_command,
    write_remote_file_utf8,
)

from apps.manifest.parser import manifest_to_tree, merge_tpops_manifest_dicts

from .models import DeploymentTask
from .user_edit import parse_user_edit_block


def _channel_group(task_id: int) -> str:
    return "deployment_%s" % task_id


def _emit(task_id: int, payload: dict):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        _channel_group(task_id),
        {"type": "deployment_event", "payload": payload},
    )


def _deploy_root(host) -> str:
    root = (host.docker_service_root or "").strip().rstrip("/")
    return root or "/data/docker-service"


def _remote_manifest_paths(host) -> list:
    """
    仅在执行机（SSH 目标）上读取的 manifest 路径。

    固定为 ``<部署根目录>/config/gaussdb/manifest.yaml``，不解析 user_edit
    中的 node*_ip，也不使用 manifest_<ip>.yaml 命名。
    """
    root = _deploy_root(host)
    base = "%s/config/gaussdb" % root
    return ["%s/manifest.yaml" % base]


def _should_poll_manifest(action: str) -> bool:
    return action in (DeploymentTask.INSTALL, DeploymentTask.UPGRADE)


def _poll_manifest_once(task_id: int, host_id: int, secret: str, manifest_paths: list) -> list:
    """Return list of remote paths that were polled (for logging)."""
    from apps.hosts.models import Host

    host = Host.objects.get(pk=host_id)
    paths = list(manifest_paths) if manifest_paths else _remote_manifest_paths(host)
    dicts = []
    poll_details = []
    for p in paths:
        raw, cat_code = remote_cat_file(
            host.hostname,
            host.port,
            host.username,
            host.auth_method,
            secret,
            p,
            timeout=60,
        )
        if not (raw or "").strip():
            poll_details.append(
                "%s → 无内容或文件不存在（请确认路径与权限；sh 退出码 %s）"
                % (p, cat_code)
            )
            continue
        try:
            data = yaml.safe_load(raw)
        except Exception as yerr:
            poll_details.append("%s → YAML 解析失败: %s" % (p, str(yerr)[:200]))
            continue
        if not isinstance(data, dict):
            poll_details.append(
                "%s → 解析结果非字典（%s），跳过"
                % (p, type(data).__name__)
            )
            continue
        dicts.append(data)
    if dicts:
        if len(dicts) == 1:
            tree = manifest_to_tree(yaml.safe_dump(dicts[0], allow_unicode=True))
        else:
            tree = merge_tpops_manifest_dicts(dicts, paths)
        tree["manifest_paths"] = paths
        _emit(task_id, {"type": "manifest", "data": tree})
    else:
        _emit(
            task_id,
            {
                "type": "manifest_wait",
                "message": "本轮未读到有效 manifest YAML，5s 后重试…",
                "paths": paths,
                "details": poll_details,
            },
        )
    return paths


def _poll_manifest_loop(
    task_id: int,
    host_id: int,
    secret: str,
    stop_event: threading.Event,
    manifest_paths: list,
):
    """
    Poll remote manifest files until stop_event is set.

    Important: do NOT use ``while not stop_event.wait(5):`` — the first call
    waits up to 5s before any read; if appctl exits and the main thread sets
    ``stop_event`` within that window, the loop body never runs and manifest
    is never fetched.
    """
    while not stop_event.is_set():
        try:
            _poll_manifest_once(task_id, host_id, secret, manifest_paths)
        except Exception as exc:
            _emit(task_id, {"type": "manifest_error", "message": str(exc)})
        if stop_event.wait(5.0):
            break


def _default_user_edit_path(host) -> str:
    return "%s/config/gaussdb/user_edit_file.conf" % _deploy_root(host)


def _build_appctl_command(host, action: str, target: str, deploy_mode: str = None) -> str:
    root = _deploy_root(host)
    tgt = (target or "").strip()

    if action == DeploymentTask.PRECHECK_INSTALL:
        if not tgt:
            raise ValueError("安装前置检查需要填写目标组件（如 gaussdb）")
        sub = "precheck install %s" % tgt
    elif action == DeploymentTask.PRECHECK_UPGRADE:
        if not tgt:
            raise ValueError("升级前置检查需要填写目标组件（如 gaussdb）")
        sub = "precheck upgrade %s" % tgt
    elif action == DeploymentTask.INSTALL:
        sub = "install%s" % (" %s" % tgt if tgt else "")
    elif action == DeploymentTask.UPGRADE:
        sub = "upgrade%s" % (" %s" % tgt if tgt else "")
    elif action == DeploymentTask.UNINSTALL_ALL:
        sub = "uninstall_all%s" % (" %s" % tgt if tgt else "")
    else:
        raise ValueError("未知操作类型")

    # install/upgrade/uninstall_all 在无 TTY 时可能提示 (y/n)，自动应答 y
    inner = "cd %s && sh appctl.sh %s" % (root, sub)
    if action in (
        DeploymentTask.INSTALL,
        DeploymentTask.UPGRADE,
        DeploymentTask.UNINSTALL_ALL,
    ):
        inner = "cd %s && yes y 2>/dev/null | sh appctl.sh %s" % (root, sub)

    return "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; " + inner


def run_task_async(task_id: int):
    thread = threading.Thread(target=_run_task, args=(task_id,), daemon=True)
    thread.start()


def _run_task(task_id: int):
    task = (
        DeploymentTask.objects.select_related("host", "host_node2", "host_node3")
        .filter(pk=task_id)
        .first()
    )
    if not task:
        return

    secret = host_ssh_secret(task.host)
    if not secret:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = "未配置 SSH 凭证"
        task.finished_at = timezone.now()
        task.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        _emit(
            task_id,
            {"type": "log", "data": "错误: 未配置 SSH 密码或私钥\n"},
        )
        return

    h = task.host
    final_conf = task.user_edit_content or ""
    kv, parse_err = parse_user_edit_block(final_conf)
    if parse_err:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = parse_err
        task.finished_at = timezone.now()
        task.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        _emit(task_id, {"type": "log", "data": parse_err + "\n"})
        return

    manifest_paths = _remote_manifest_paths(h)

    path, perr = resolve_user_edit_conf_path(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        h.docker_service_root or "",
    )
    if not path:
        path = _default_user_edit_path(h)
        _emit(
            task_id,
            {"type": "log", "data": "提示: %s，将写入默认路径 %s\n" % (perr or "", path),
            },
        )
        ddir = os.path.dirname(path)
        if not remote_mkdir_p(
            h.hostname, h.port, h.username, h.auth_method, secret, ddir
        ):
            task.status = DeploymentTask.STATUS_FAILED
            task.error_message = "无法创建远程目录 %s" % ddir
            task.finished_at = timezone.now()
            task.save(
                update_fields=[
                    "status",
                    "error_message",
                    "finished_at",
                    "updated_at",
                ]
            )
            _emit(task_id, {"type": "log", "data": task.error_message + "\n"})
            return
    else:
        task.remote_user_edit_path = path
        task.save(update_fields=["remote_user_edit_path", "updated_at"])
        _emit(
            task_id,
            {"type": "log", "data": "已定位远程配置: %s，开始覆盖写入...\n" % path},
        )

    ok, werr = write_remote_file_utf8(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        path,
        final_conf,
    )
    if not ok:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = werr or "写入 user_edit_file.conf 失败"
        task.remote_user_edit_path = path
        task.finished_at = timezone.now()
        task.save(
            update_fields=[
                "status",
                "error_message",
                "remote_user_edit_path",
                "finished_at",
                "updated_at",
            ]
        )
        _emit(task_id, {"type": "log", "data": "写入失败: %s\n" % werr})
        return

    task.remote_user_edit_path = path
    task.save(update_fields=["remote_user_edit_path", "updated_at"])
    _emit(task_id, {"type": "log", "data": "配置文件已写入: %s\n" % path})

    try:
        cmd = _build_appctl_command(h, task.action, task.target, task.deploy_mode)
    except ValueError as exc:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = str(exc)
        task.finished_at = timezone.now()
        task.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        _emit(task_id, {"type": "log", "data": str(exc) + "\n"})
        return

    task.status = DeploymentTask.STATUS_RUNNING
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at", "updated_at"])

    _emit(task_id, {"type": "status", "data": task.status})
    _emit(
        task_id,
        {
            "type": "phase",
            "phase": "run_appctl",
            "message": "执行命令",
            "command": cmd,
        },
    )
    _emit(task_id, {"type": "log", "data": "执行: %s\n" % cmd})

    stop_poll = threading.Event()
    poller = None
    init_needle = "init manifest successful"

    if not _should_poll_manifest(task.action):
        _emit(
            task_id,
            {
                "type": "phase",
                "phase": "precheck_no_manifest",
                "message": (
                    "卸载流程不轮询 manifest"
                    if task.action == DeploymentTask.UNINSTALL_ALL
                    else "前置检查阶段不轮询 manifest"
                ),
            },
        )
    else:
        # install/upgrade：不依赖 stdout 里是否出现固定文案（现场脚本可能改文案、
        # 或 PTY/缓冲导致检测不到）；appctl 未结束时即开始轮询，文件就绪后 UI 即有 manifest。
        _emit(
            task_id,
            {
                "type": "phase",
                "phase": "manifest_polling",
                "message": "安装/升级流程：已开始轮询远程 manifest（就绪后即推送流水线）",
                "paths": manifest_paths,
            },
        )
        try:
            tried = _poll_manifest_once(task_id, task.host_id, secret, manifest_paths)
            _emit(
                task_id,
                {
                    "type": "log",
                    "data": "[manifest] 轮询路径: %s\n"
                    % (", ".join(tried) if tried else "(无路径)"),
                },
            )
        except Exception as exc:
            _emit(
                task_id,
                {
                    "type": "manifest_error",
                    "message": "首次拉取 manifest 失败: %s" % exc,
                },
            )
        poller = threading.Thread(
            target=_poll_manifest_loop,
            args=(task_id, task.host_id, secret, stop_poll, manifest_paths),
            daemon=True,
        )
        poller.start()

    exit_code = None
    buffer = ""
    stream_for_init_scan = ""
    init_stdout_hinted = False
    try:
        for chunk in run_remote_command(
            h.hostname,
            h.port,
            h.username,
            h.auth_method,
            secret,
            cmd,
            timeout=86400,
            get_pty=False,
        ):
            buffer += chunk
            stream_for_init_scan += chunk
            if len(stream_for_init_scan) > 8192:
                stream_for_init_scan = stream_for_init_scan[-4096:]
            if (
                _should_poll_manifest(task.action)
                and not init_stdout_hinted
                and init_needle in stream_for_init_scan.lower()
            ):
                init_stdout_hinted = True
                _emit(
                    task_id,
                    {
                        "type": "phase",
                        "phase": "init_manifest_ready",
                        "message": "appctl 输出中已出现 init manifest successful（manifest 轮询已在进行）",
                    },
                )
            m = re.search(r"__EXIT_CODE__:(-?\d+)", buffer)
            if m:
                exit_code = int(m.group(1))
                out = buffer[: m.start()]
                if out:
                    _emit(task_id, {"type": "log", "data": out})
                buffer = ""
                break
            if len(buffer) >= 256:
                _emit(task_id, {"type": "log", "data": buffer})
                buffer = ""
        if buffer:
            _emit(task_id, {"type": "log", "data": buffer})
    except Exception as exc:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = str(exc)
        task.exit_code = -1
        task.finished_at = timezone.now()
        task.save(
            update_fields=[
                "status",
                "error_message",
                "exit_code",
                "finished_at",
                "updated_at",
            ]
        )
        _emit(task_id, {"type": "log", "data": "\n异常: %s\n" % exc})
        _emit(task_id, {"type": "status", "data": task.status})
        stop_poll.set()
        return
    finally:
        stop_poll.set()

    task.exit_code = exit_code if exit_code is not None else -1
    if exit_code == 0:
        task.status = DeploymentTask.STATUS_SUCCESS
    else:
        task.status = DeploymentTask.STATUS_FAILED
        if not task.error_message:
            task.error_message = "命令退出码 %s" % exit_code
    task.finished_at = timezone.now()
    task.save(
        update_fields=[
            "status",
            "exit_code",
            "error_message",
            "finished_at",
            "updated_at",
        ]
    )
    _emit(task_id, {"type": "status", "data": task.status})
    _emit(
        task_id,
        {
            "type": "done",
            "exit_code": task.exit_code,
            "status": task.status,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        },
    )
