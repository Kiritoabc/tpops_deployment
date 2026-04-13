import os
import re
import threading

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

from apps.manifest.parser import manifest_to_tree

from .models import DeploymentTask
from .user_edit import apply_host_ips_to_config, parse_user_edit_block


def _channel_group(task_id: int) -> str:
    return "deployment_%s" % task_id


def _emit(task_id: int, payload: dict):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        _channel_group(task_id),
        {"type": "deployment_event", "payload": payload},
    )


def _remote_manifest_path(host) -> str:
    root = (host.docker_service_root or "").strip().rstrip("/")
    if not root:
        root = "/data/docker-service"
    return "%s/config/gaussdb/manifest.yaml" % root


def _default_user_edit_path(host) -> str:
    root = (host.docker_service_root or "").strip().rstrip("/")
    if not root:
        root = "/data/docker-service"
    return "%s/config/gaussdb/user_edit_file.conf" % root


def _poll_manifest_loop(task_id: int, host_id: int, secret: str, stop_event: threading.Event):
    from apps.hosts.models import Host

    while not stop_event.wait(5.0):
        try:
            host = Host.objects.get(pk=host_id)
            path = _remote_manifest_path(host)
            raw, _code = remote_cat_file(
                host.hostname,
                host.port,
                host.username,
                host.auth_method,
                secret,
                path,
                timeout=60,
            )
            tree = manifest_to_tree(raw)
            _emit(task_id, {"type": "manifest", "data": tree})
        except Exception as exc:
            _emit(task_id, {"type": "manifest_error", "message": str(exc)})


def _build_appctl_command(host, action: str, target: str) -> str:
    root = (host.docker_service_root or "").strip().rstrip("/")
    if not root:
        raise ValueError("请先在服务器配置中填写部署根目录")
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
    else:
        raise ValueError("未知操作类型")

    return (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "cd %s && bash appctl.sh %s" % (root, sub)
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
    # 1) 合并节点 IP 到配置
    base_conf = task.user_edit_content or ""
    if task.deploy_mode == DeploymentTask.MODE_TRIPLE:
        ips = [h.hostname, task.host_node2.hostname, task.host_node3.hostname]
    else:
        ips = [h.hostname]
    final_conf = apply_host_ips_to_config(base_conf, task.deploy_mode, ips)
    _, parse_err = parse_user_edit_block(final_conf)
    if parse_err:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = parse_err
        task.finished_at = timezone.now()
        task.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        _emit(task_id, {"type": "log", "data": parse_err + "\n"})
        return

    # 2) 解析远程 user_edit 路径并写入
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
    _emit(task_id, {"type": "log", "data": "执行: %s\n" % cmd})

    stop_poll = threading.Event()
    poller = threading.Thread(
        target=_poll_manifest_loop,
        args=(task_id, task.host_id, secret, stop_poll),
        daemon=True,
    )
    poller.start()

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
            if len(buffer) > 2048:
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
