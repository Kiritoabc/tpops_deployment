import logging
import os
import re
import threading

import yaml

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.hosts.serializers import host_ssh_secret
from apps.hosts.ssh_client import (
    remote_mkdir_p,
    resolve_user_edit_conf_path,
    remote_cat_file,
    run_remote_command,
    run_remote_command_output,
    sftp_put_file,
    write_remote_file_utf8,
)

from apps.manifest.parser import manifest_to_tree, merge_tpops_manifest_dicts

from .models import DeploymentTask
from .package_patterns import (
    ROLE_OS_KERNEL,
    ROLE_OM_KERNEL,
    ROLE_TPOPS_SERVER,
    artifact_basename_for_classify,
    classify_package_basename,
)
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


def _remote_manifest_paths_for_task(host, deploy_mode: str, user_edit_kv: dict) -> list:
    """
    在执行机（SSH 目标）上 cat 的 manifest 路径列表（相对部署根 config/gaussdb）。

    - **单节点**：只读 ``manifest.yaml``。
    - **三节点**（与 user_edit 约定一致）：
      - 节点 1（当前配置中的 node1_ip 对应现场主文件）：``manifest.yaml``
      - 节点 2：``manifest_<node2_ip>.yaml``（来自 user_edit 的 node2_ip）
      - 节点 3：``manifest_<node3_ip>.yaml``（来自 user_edit 的 node3_ip）
      仅追加已填写的 node2_ip / node3_ip；空则不读对应文件。
    """
    root = _deploy_root(host)
    base = "%s/config/gaussdb" % root
    paths = []
    seen = set()

    def _add(p):
        if p not in seen:
            seen.add(p)
            paths.append(p)

    if deploy_mode != DeploymentTask.MODE_TRIPLE:
        _add("%s/manifest.yaml" % base)
        return paths

    kv = user_edit_kv or {}
    n2 = (kv.get("node2_ip") or "").strip()
    n3 = (kv.get("node3_ip") or "").strip()

    _add("%s/manifest.yaml" % base)
    if n2:
        _add("%s/manifest_%s.yaml" % (base, n2))
    if n3:
        _add("%s/manifest_%s.yaml" % (base, n3))
    return paths


def _should_poll_manifest(action: str) -> bool:
    return action in (DeploymentTask.INSTALL, DeploymentTask.UPGRADE)


def fetch_manifest_tree_for_task(host, task, secret, manifest_paths=None):
    """
    SSH 到执行机读取 manifest YAML 并解析为与 WebSocket ``manifest`` 消息同结构的 tree。
    不经过 Channels 推送；供任务结束后单次拉取或内部轮询复用。

    Returns:
        (tree_or_none, paths, poll_details)
        tree_or_none: dict 含 roots / summary / pipeline 等；读不到有效 YAML 时为 None
        paths: 实际尝试读取的相对路径列表
        poll_details: 每轮诊断字符串列表
    """
    if not host or not task:
        return None, [], ["缺少 host 或 task"]
    kv, parse_err = parse_user_edit_block((task.user_edit_content or "") or "")
    if parse_err:
        return None, [], ["user_edit: %s" % parse_err]
    dm = (task.deploy_mode if task else "") or DeploymentTask.MODE_SINGLE
    paths = (
        list(manifest_paths)
        if manifest_paths
        else _remote_manifest_paths_for_task(host, dm, kv)
    )
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
    if not dicts:
        return None, paths, poll_details
    if len(dicts) == 1:
        tree = manifest_to_tree(yaml.safe_dump(dicts[0], allow_unicode=True))
        if tree.get("summary") is not None:
            tree["summary"]["multi_node"] = False
    else:
        n1 = (kv.get("node1_ip") or "").strip()
        tree = merge_tpops_manifest_dicts(dicts, paths, node1_ip=n1 or None)
    tree["manifest_paths"] = paths
    tree["deploy_mode"] = dm
    return tree, paths, poll_details


def _poll_manifest_once(task_id: int, host_id: int, secret: str, manifest_paths: list) -> list:
    """Return list of remote paths that were polled (for logging)."""
    from apps.hosts.models import Host

    # 轮询在独立 daemon 线程中跑，须刷新/建立 ORM 连接（否则易 SQLite locked 或无效连接）
    close_old_connections()
    host = Host.objects.get(pk=host_id)
    task = DeploymentTask.objects.filter(pk=task_id).only(
        "user_edit_content", "deploy_mode"
    ).first()
    if not task:
        return []
    tree, paths, poll_details = fetch_manifest_tree_for_task(
        host, task, secret, manifest_paths if manifest_paths else None
    )
    if tree:
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
    close_old_connections()
    while not stop_event.is_set():
        try:
            _poll_manifest_once(task_id, host_id, secret, manifest_paths)
        except Exception as exc:
            _emit(task_id, {"type": "manifest_error", "message": str(exc)})
        if stop_event.wait(5.0):
            break


def _default_user_edit_path(host) -> str:
    return "%s/config/gaussdb/user_edit_file.conf" % _deploy_root(host)


def _remote_pkgs_dir(host) -> str:
    return "%s/pkgs" % _deploy_root(host)


def _should_tpops_gaussdb_media_prep(task) -> bool:
    """
    install/upgrade 且勾选了 TPOPS-GaussDB-Server 主包时，走 /data 解压与 pkgs 汇聚。
    未选主包则不走该流程（仅扁平同步其它已选包到 pkgs/）。
    """
    if getattr(task, "skip_package_sync", False):
        return False
    if task.action not in (DeploymentTask.INSTALL, DeploymentTask.UPGRADE):
        return False
    ids = getattr(task, "package_artifact_ids", None) or []
    rel_id = getattr(task, "package_release_id", None)
    if not ids or not rel_id:
        return False
    from apps.packages.models import PackageArtifact

    for art in PackageArtifact.objects.filter(
        release_id=rel_id, pk__in=ids
    ).only("remote_basename", "original_name"):
        if classify_package_basename(artifact_basename_for_classify(art))[
            "role"
        ] == ROLE_TPOPS_SERVER:
            return True
    return False


def _shell_quote(path: str) -> str:
    return "'%s'" % (path or "").replace("'", "'\"'\"'")


def _sync_tpops_gaussdb_media(task_id: int, task, secret: str) -> tuple:
    """
    TPOPS GaussDB：在节点 1 上准备 /data 下介质并汇入 <部署根>/pkgs/。
    返回 (ok: bool, error_message: str)
    """
    from apps.packages.models import PackageArtifact

    h = task.host
    rel = task.package_release
    ids = [int(x) for x in (task.package_artifact_ids or [])]
    qs = list(
        PackageArtifact.objects.filter(release=rel, pk__in=ids).order_by("pk")
    )
    if len(qs) != len(set(ids)):
        return False, "安装包列表与版本不一致或存在无效 ID"

    tpops_art = None
    om_art = None
    os_art = None
    for art in qs:
        info = classify_package_basename(artifact_basename_for_classify(art))
        role = info["role"]
        if role == ROLE_TPOPS_SERVER:
            tpops_art = art
        elif role == ROLE_OM_KERNEL:
            om_art = art
        elif role == ROLE_OS_KERNEL:
            os_art = art

    if tpops_art is None:
        return False, "缺少 TPOPS-GaussDB-Server 主包"

    pkgs = _remote_pkgs_dir(h)
    data_dir = "/data"

    _emit(
        task_id,
        {
            "type": "phase",
            "phase": "tpops_media_prep",
            "message": "TPOPS GaussDB 介质准备（/data 与 pkgs）",
        },
    )

    if not remote_mkdir_p(
        h.hostname, h.port, h.username, h.auth_method, secret, data_dir
    ):
        return False, "无法创建远程目录 %s" % data_dir

    if not remote_mkdir_p(
        h.hostname, h.port, h.username, h.auth_method, secret, pkgs
    ):
        return False, "无法创建远程目录 %s" % pkgs

    for art in qs:
        local_path = art.file.path if art.file else ""
        if not local_path or not os.path.isfile(local_path):
            return False, "本地找不到安装包文件 id=%s" % art.id
        remote_path = "%s/%s" % (data_dir, art.remote_basename)
        ok, msg = sftp_put_file(
            h.hostname,
            h.port,
            h.username,
            h.auth_method,
            secret,
            local_path,
            remote_path,
        )
        if not ok:
            return False, "上传至 %s 失败: %s" % (remote_path, msg)
        _emit(
            task_id,
            {"type": "log", "data": "[tpops-media] 已上传 /data/%s\n" % art.remote_basename},
        )

    tpops_archive = "%s/%s" % (data_dir, tpops_art.remote_basename)
    q_arch = _shell_quote(tpops_archive)
    q_data = _shell_quote(data_dir)

    tar_cmd = (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "set -e; cd %s && tar -xzf %s -C %s" % (q_data, q_arch, q_data)
    )
    out, code = run_remote_command_output(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        tar_cmd,
        timeout=7200,
        get_pty=False,
    )
    if out:
        _emit(task_id, {"type": "log", "data": out})
    if code != 0:
        return False, "解压 TPOPS 主包失败（退出码 %s）" % code

    find_dir_cmd = (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "set -e; cd %s && for d in TPOPS-GaussDB-Server_*; do "
        'if [ -d "$d" ]; then printf %%s "$d"; exit 0; fi; done; exit 1' % q_data
    )
    tpops_subdir, dcode = run_remote_command_output(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        find_dir_cmd,
        timeout=60,
        get_pty=False,
    )
    tpops_subdir = (tpops_subdir or "").strip().splitlines()[0].strip()
    if dcode != 0 or not tpops_subdir or "/" in tpops_subdir or tpops_subdir.startswith("."):
        return False, "解压后未找到 TPOPS-GaussDB-Server_* 目录（请确认压缩包内容）"

    q_sub = _shell_quote("%s/%s" % (data_dir, tpops_subdir))

    ds_glob_cmd = (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "set -e; cd %s && "
        'for f in DBS-*docker-service*.tar.gz DBS-*docker-service*.tgz; do '
        'if [ -f "$f" ]; then printf %%s\\n "$f"; exit 0; fi; done; exit 0' % q_sub
    )
    ds_path, _ = run_remote_command_output(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        ds_glob_cmd,
        timeout=60,
        get_pty=False,
    )
    ds_path = (ds_path or "").strip().splitlines()[0].strip()
    if ds_path and not ds_path.startswith("/"):
        ds_path = "%s/%s/%s" % (data_dir, tpops_subdir, ds_path)

    if ds_path:
        q_ds = _shell_quote(ds_path)
        ds_tar_cmd = (
            "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
            "set -e; tar -xzf %s -C %s" % (q_ds, q_data)
        )
        out_ds, code_ds = run_remote_command_output(
            h.hostname,
            h.port,
            h.username,
            h.auth_method,
            secret,
            ds_tar_cmd,
            timeout=7200,
            get_pty=False,
        )
        if out_ds:
            _emit(task_id, {"type": "log", "data": out_ds})
        if code_ds != 0:
            return False, "解压 docker-service 包失败（退出码 %s）" % code_ds
        _emit(
            task_id,
            {"type": "log", "data": "[tpops-media] 已解压 docker-service 包\n"},
        )
    else:
        _emit(
            task_id,
            {
                "type": "log",
                "data": "[tpops-media] 未找到 DBS-*docker-service*.tar.gz，跳过解压\n",
            },
        )

    q_pkgs = _shell_quote(pkgs)
    mv_cmd = (
        "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
        "set -e; cd %s && "
        "for f in DBS-*; do "
        'if [ -f "$f" ] || [ -d "$f" ]; then mv -f "$f" %s/; fi; done && '
        "for f in GaussDB_*; do "
        'if [ -f "$f" ] || [ -d "$f" ]; then mv -f "$f" %s/; fi; done'
        % (q_sub, q_pkgs, q_pkgs)
    )
    out_mv, code_mv = run_remote_command_output(
        h.hostname,
        h.port,
        h.username,
        h.auth_method,
        secret,
        mv_cmd,
        timeout=600,
        get_pty=False,
    )
    if out_mv:
        _emit(task_id, {"type": "log", "data": out_mv})
    if code_mv != 0:
        return False, "移动 TPOPS 目录内介质到 pkgs 失败（退出码 %s）" % code_mv
    _emit(
        task_id,
        {"type": "log", "data": "[tpops-media] 已将 DBS-* / GaussDB_* 移至 %s\n" % pkgs},
    )

    for label, art in (("om-agent", om_art), ("OS 内核", os_art)):
        if not art:
            continue
        src = "%s/%s" % (data_dir, art.remote_basename)
        dst = "%s/%s" % (pkgs, art.remote_basename)
        mv_one = (
            "export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8; "
            "set -e; if [ -f %s ]; then mv -f %s %s; fi"
            % (_shell_quote(src), _shell_quote(src), _shell_quote(dst))
        )
        out_m, code_m = run_remote_command_output(
            h.hostname,
            h.port,
            h.username,
            h.auth_method,
            secret,
            mv_one,
            timeout=120,
            get_pty=False,
        )
        if code_m != 0:
            return False, "移动 %s 包到 pkgs 失败" % label
        _emit(
            task_id,
            {"type": "log", "data": "[tpops-media] 已移入 pkgs: %s\n" % art.remote_basename},
        )

    _emit(
        task_id,
        {"type": "log", "data": "[tpops-media] 介质准备完成，pkgs: %s\n" % pkgs},
    )
    return True, ""


def _sync_pkgs_to_remote(task_id: int, task, secret: str) -> tuple:
    """
    将任务勾选的安装包同步到执行机 <部署根>/pkgs/（扁平文件名）。
    返回 (ok: bool, error_message: str)
    """
    from apps.packages.models import PackageArtifact

    if getattr(task, "skip_package_sync", False):
        _emit(task_id, {"type": "log", "data": "[pkgs] 已跳过安装包同步（使用环境已有包）\n"})
        return True, ""

    if _should_tpops_gaussdb_media_prep(task):
        return _sync_tpops_gaussdb_media(task_id, task, secret)

    ids = getattr(task, "package_artifact_ids", None) or []
    if not ids:
        return True, ""

    rel = getattr(task, "package_release", None)
    if rel is None:
        return False, "已填写安装包 ID 但未关联版本"

    pkgs = _remote_pkgs_dir(task.host)
    if not remote_mkdir_p(
        task.host.hostname,
        task.host.port,
        task.host.username,
        task.host.auth_method,
        secret,
        pkgs,
    ):
        return False, "无法创建远程目录 %s" % pkgs

    qs = PackageArtifact.objects.filter(release=rel, pk__in=ids)
    if qs.count() != len(set(int(x) for x in ids)):
        return False, "安装包列表与版本不一致或存在无效 ID"

    uploaded = []
    for art in qs:
        local_path = art.file.path if art.file else ""
        if not local_path or not os.path.isfile(local_path):
            return False, "本地找不到安装包文件 id=%s" % art.id
        remote_path = "%s/%s" % (pkgs, art.remote_basename)
        ok, msg = sftp_put_file(
            task.host.hostname,
            task.host.port,
            task.host.username,
            task.host.auth_method,
            secret,
            local_path,
            remote_path,
        )
        if not ok:
            return False, "上传 %s 失败: %s" % (art.remote_basename, msg)
        uploaded.append(art.remote_basename)

    _emit(
        task_id,
        {
            "type": "log",
            "data": "[pkgs] 已同步到 %s: %s\n"
            % (pkgs, ", ".join(uploaded) if uploaded else "(无)"),
        },
    )
    return True, ""


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
    """
    在 HTTP 请求结束后再启动的后台线程中执行 ORM/SSH。
    必须 close_old_connections()，否则复用主线程已关闭的 DB 连接或触发 SQLite 锁，表现为任务未执行（一直 pending）。
    """
    close_old_connections()
    try:
        _run_task_body(task_id)
    except Exception as exc:
        logger.exception("deployment task %s runner crashed", task_id)
        try:
            close_old_connections()
            task = DeploymentTask.objects.filter(pk=task_id).first()
            if task and task.status in (
                DeploymentTask.STATUS_PENDING,
                DeploymentTask.STATUS_RUNNING,
            ):
                task.status = DeploymentTask.STATUS_FAILED
                task.error_message = (
                    "后台执行线程异常（请查看服务端日志）: %s" % str(exc)[:500]
                )
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
                _emit(
                    task_id,
                    {
                        "type": "log",
                        "data": "\n[平台错误] 任务执行线程异常: %s\n" % str(exc)[:800],
                    },
                )
                _emit(task_id, {"type": "status", "data": task.status})
                _emit(
                    task_id,
                    {
                        "type": "done",
                        "exit_code": task.exit_code,
                        "status": task.status,
                        "finished_at": task.finished_at.isoformat()
                        if task.finished_at
                        else None,
                    },
                )
        except Exception:
            logger.exception(
                "failed to persist crash state for deployment task %s", task_id
            )
    finally:
        close_old_connections()


def _run_task_body(task_id: int):
    task = (
        DeploymentTask.objects.select_related(
            "host", "host_node2", "host_node3", "package_release"
        )
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

    manifest_paths = _remote_manifest_paths_for_task(h, task.deploy_mode, kv)

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

    ok_pkg, perr = _sync_pkgs_to_remote(task_id, task, secret)
    if not ok_pkg:
        task.status = DeploymentTask.STATUS_FAILED
        task.error_message = perr or "安装包同步失败"
        task.finished_at = timezone.now()
        task.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        _emit(task_id, {"type": "log", "data": (perr or "安装包同步失败") + "\n"})
        return

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
    # 按行尽快推送日志（原先每 256 字节才 emit，无换行时 stdout 易整块缓冲，界面几乎不动）
    _LOG_LINE_FLUSH_MAX = 120

    def _flush_log_lines(buf: str, emit_partial_tail: bool) -> str:
        """Emit complete lines; optionally emit tail without trailing \\n if long enough."""
        if not buf:
            return ""
        if "__EXIT_CODE__:" in buf:
            return buf
        parts = buf.split("\n")
        if len(parts) == 1:
            if emit_partial_tail and len(parts[0]) >= _LOG_LINE_FLUSH_MAX:
                _emit(task_id, {"type": "log", "data": parts[0]})
                return ""
            return buf
        for line in parts[:-1]:
            _emit(task_id, {"type": "log", "data": line + "\n"})
        tail = parts[-1]
        if emit_partial_tail and len(tail) >= _LOG_LINE_FLUSH_MAX:
            _emit(task_id, {"type": "log", "data": tail})
            return ""
        return tail

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
                    buffer = _flush_log_lines(out, emit_partial_tail=True)
                    if buffer:
                        _emit(task_id, {"type": "log", "data": buffer})
                buffer = ""
                break
            buffer = _flush_log_lines(buffer, emit_partial_tail=True)
        if buffer:
            buffer = _flush_log_lines(buffer, emit_partial_tail=True)
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
