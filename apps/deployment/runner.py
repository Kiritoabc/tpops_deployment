import re
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.hosts.serializers import host_ssh_secret
from apps.hosts.ssh_client import remote_cat_file, run_remote_command
from apps.manifest.parser import manifest_to_tree

from .models import DeploymentTask


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
    return "%s/autoChangeInterface/manifest.yaml" % root


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
        raise ValueError("请先在服务器配置中填写 docker-service 根目录")
    if action == DeploymentTask.PRECHECK:
        sub = "precheck install %s" % target
    elif action == DeploymentTask.INSTALL:
        sub = "install %s" % target
    else:
        raise ValueError("未知操作")
    return (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "cd %s && bash autoChangeInterface/appctl.sh %s" % (root, sub)
    )


def run_task_async(task_id: int):
    thread = threading.Thread(target=_run_task, args=(task_id,), daemon=True)
    thread.start()


def _run_task(task_id: int):
    task = DeploymentTask.objects.select_related("host").filter(pk=task_id).first()
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

    try:
        cmd = _build_appctl_command(task.host, task.action, task.target)
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
            task.host.hostname,
            task.host.port,
            task.host.username,
            task.host.auth_method,
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
