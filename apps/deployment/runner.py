import os
import re
import shlex
import threading
import time

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


def _init_marker_paths(host) -> list:
    r = _deploy_root(host)
    return [
        "%s/config/gaussdb/init_manifest_successful" % r,
        "%s/config/gaussdb/init_manifest_successful.txt" % r,
        "%s/config/init_manifest_successful" % r,
    ]


def _remote_manifest_paths_for_nodes(host, user_edit_kv: dict) -> list:
    """本地节点用 manifest.yaml，其它 IP 用 manifest_{ip}.yaml"""
    root = _deploy_root(host)
    base = "%s/config/gaussdb" % root
    local = (host.hostname or "").strip()
    ips = []
    for key in ("node1_ip", "node2_ip", "node3_ip"):
        v = (user_edit_kv or {}).get(key)
        if v and v.strip():
            ips.append(v.strip())
    if not ips:
        return ["%s/manifest.yaml" % base]
    paths = []
    seen = set()
    for ip in ips:
        if ip == local:
            p = "%s/manifest.yaml" % base
        else:
            p = "%s/manifest_%s.yaml" % (base, ip)
        if p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def _should_poll_manifest(action: str) -> bool:
    return action in (DeploymentTask.INSTALLL, DeploymentTask.UPGRADE)


def _wait_init_manifest(
    task_id: int,
    host,
    secret: str,
    stop_event: threading.Event,
    timeout_sec: int = 7200,
) -> bool:
    """等待 init manifest 标记文件出现；推送 phase 消息。"""
    paths = _init_marker_paths(host)
    _emit(
        task_id,
        {
            "type": "phase",
            "phase": "wait_init_manifest",
            "message": "等待初始化完成（init manifest successful）…",
            "paths_tried": paths,
        },
    )
    deadline = time.time() + timeout_sec
    inner_check = "for p in %s; do test -f \"$p\" && echo FOUND && exit 0; done; exit 1" % " ".join(
        shlex.quote(p) for p in paths
    )
    while not stop_event.is_set() and time.time() < deadline:
        from apps.hosts.ssh_client import run_remote_command_output

        cmd = "sh -c %s" % shlex.quote(inner_check)
        out, code = run_remote_command_output(
            host.hostname,
            host.port,
            host.username,
            host.auth_method,
            secret,
            cmd,
            timeout=30,
        )
        if code == 0 and "FOUND" in out:
            _emit(
                task_id,
                {
                    "type": "phase",
                    "phase": "init_manifest_ready",
                    "message": "初始化完成，开始轮询 manifest",
                },
            )
            return True
        time.sleep(2.0)
    _emit(
        task_id,
        {
            "type": "phase",
            "phase": "init_manifest_timeout",
            "message": "等待 init manifest 标记超时或未出现",
        },
    )
    return False


def _poll_manifest_loop(
    task_id: int,
    host_id: int,
    secret: str,
    stop_event: threading.Event,
    manifest_paths: list,
):
    from apps.hosts.models import Host

    while not stop_event.wait(5.0):
        try:
            host = Host.objects.get(pk=host_id)
            task = DeploymentTask.objects.filter(pk=task_id).only("user_edit_content").first()
            kv, _ = parse_user_edit_block((task.user_edit_content if task else "") or "")
            paths = list(manifest_paths) if manifest_paths else _remote_manifest_paths_for_nodes(
                host, kv
            )
            dicts = []
            for p in paths:
                raw, _code = remote_cat_file(
                    host.hostname,
                    host.port,
                    host.username,
                    host.auth_method,
                    secret,
                    p,
                    timeout=60,
                )
                if not (raw or "").strip():
                    continue
                try:
                    data = yaml.safe_load(raw)
                except Exception:
                    continue
                if isinstance(data, dict):
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
                        "message": "manifest 文件尚未就绪，继续等待…",
                        "paths": paths,
                    },
                )
        except Exception as exc:
            _emit(task_id, {"type": "manifest_error", "message": str(exc)})


def _default_user_edit_path(host) -> str:
    return "%s/config/gaussdb/user_edit_file.conf" % _deploy_root(host)


def _build_appctl_command(host, action: str, target: str) -> str:
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
    elif action == DeploymentTask.INSTALLL:
        sub = "installl%s" % (" %s" % tgt if tgt else "")
    elif action == DeploymentTask.UPGRADE:
        sub = "upgrade%s" % (" %s" % tgt if tgt else "")
    else:
        raise ValueError("未知操作类型")

    return (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "cd %s && sh appctl.sh %s" % (root, sub)
    )


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

    manifest_paths = _remote_manifest_paths_for_nodes(h, kv)

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
        cmd = _build_appctl_command(h, task.action, task.target)
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
    if _should_poll_manifest(task.action):
        if _wait_init_manifest(task_id, h, secret, stop_poll):
            poller = threading.Thread(
                target=_poll_manifest_loop,
                args=(task_id, task.host_id, secret, stop_poll, manifest_paths),
                daemon=True,
            )
            poller.start()
    else:
        _emit(
            task_id,
            {
                "type": "phase",
                "phase": "precheck_no_manifest",
                "message": "前置检查阶段不轮询 manifest；请点流程节点查看 deploy 日志",
            },
        )

    exit_code = None
    buffer = ""
    try:
        for chunk in run_remote_command(
            h.hostname,
            h.port,
            h.username,
            h.auth_method,
            secret,
            cmd,
            timeout=86400,
        ):
            buffer += chunk
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
    _emit(task_id, {"type": "done", "exit_code": task.exit_code})
