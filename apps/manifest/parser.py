"""
解析 TPOPS docker-service 的 manifest.yaml。

结构要点（与 crontab/manifest 更新脚本一致）：
- 顶层：各层聚合状态，如 patch_status、base_enviornment_status、…
- 各层键（如 patch、base_enviornment）：值为服务项列表，每项含 name、script、status、retry_time 等
"""
from typing import Any, Dict, List

import yaml

# 与 action/gaussdb/vars.sh 中 all_levels 顺序一致（展示顺序）
LEVEL_ORDER = [
    "patch",
    "base_enviornment",
    "PlatformData",
    "Zookeeper",
    "Kafka",
    "docker_service",
    "gaussdb_service",
    "post_service",
]

SERVICE_DETAIL_KEYS = (
    "script",
    "retry_time",
    "start_time_is_record",
    "start_time",
    "install_require_time",
    "repair_require_time",
    "upgrade_require_time",
    "rollback_require_time",
    "uninstall_require_time",
    "finish_flag",
    "finish_execute_time",
)


def _norm_status(val: Any) -> str:
    if val is None:
        return "none"
    if isinstance(val, str):
        s = val.strip().lower()
        return s if s else "none"
    return str(val).lower()


def _is_tpops_manifest(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for level in LEVEL_ORDER:
        sk = "%s_status" % level
        if sk in data or level in data:
            return True
    return False


def _service_node(level_key: str, idx: int, item: Any) -> Dict[str, Any]:
    """列表中的一项 -> 树节点。"""
    node_id = "%s/item_%s" % (level_key, idx)
    if not isinstance(item, dict):
        return {
            "id": node_id,
            "label": str(item),
            "status": "none",
        }
    name = item.get("name") or "item_%s" % idx
    script = item.get("script") or ""
    status = _norm_status(item.get("status"))
    label = "%s · %s" % (name, script) if script else str(name)
    meta = {k: item.get(k) for k in SERVICE_DETAIL_KEYS if k in item}
    return {
        "id": "%s/%s" % (level_key, name),
        "label": label,
        "status": status,
        "meta": meta,
    }


def _build_tpops_tree(data: Dict[str, Any]) -> Dict[str, Any]:
    roots: List[Dict[str, Any]] = []
    summary = {
        "levels_total": len(LEVEL_ORDER),
        "levels_done": 0,
        "levels_running": 0,
        "levels_error": 0,
        "levels_none": 0,
        "by_level": {},
    }

    for level in LEVEL_ORDER:
        sk = "%s_status" % level
        agg = _norm_status(data.get(sk, "none"))
        summary["by_level"][level] = agg
        if agg == "done":
            summary["levels_done"] += 1
        elif agg == "running":
            summary["levels_running"] += 1
        elif agg == "error":
            summary["levels_error"] += 1
        elif agg == "none":
            summary["levels_none"] += 1

        children: List[Dict[str, Any]] = []
        block = data.get(level)
        if isinstance(block, list):
            for idx, item in enumerate(block):
                children.append(_service_node(level, idx, item))
        elif isinstance(block, dict):
            # 少数场景可能是单对象
            children.append(_service_node(level, 0, block))

        roots.append(
            {
                "id": level,
                "label": level,
                "status": agg,
                "meta": {"level_status_key": sk},
                "children": children,
            }
        )

    # 服务级统计（所有层列表内）
    svc_total = 0
    svc_done = 0
    for level in LEVEL_ORDER:
        block = data.get(level)
        if not isinstance(block, list):
            continue
        for item in block:
            svc_total += 1
            if isinstance(item, dict) and _norm_status(item.get("status")) == "done":
                svc_done += 1
    summary["services_total"] = svc_total
    summary["services_done"] = svc_done

    return {"roots": roots, "levels": LEVEL_ORDER, "summary": summary}


def _meta_from_obj(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    keys = (
        "start_time",
        "finish_execute_time",
        "install_require_time",
        "retry_time",
        "message",
        "error",
    )
    return {k: obj.get(k) for k in keys if k in obj}


def _walk(name: str, obj: Any, path: str = "") -> Dict[str, Any]:
    node_id = "%s/%s" % (path, name) if path else name
    if isinstance(obj, list):
        children = []
        for idx, item in enumerate(obj):
            child_name = "%s[%s]" % (name, idx)
            children.append(_walk(child_name, item, node_id))
        return {
            "id": node_id,
            "label": name,
            "status": "none",
            "children": children,
        }

    if isinstance(obj, dict):
        status_keys = ("status", "state", "phase", "install_status")
        status = "none"
        for key in status_keys:
            val = obj.get(key)
            if isinstance(val, str) and val:
                status = val.lower()
                break
        meta = _meta_from_obj(obj)
        child_keys = [
            k
            for k, v in obj.items()
            if k not in meta
            and k not in status_keys
            and isinstance(v, (dict, list))
        ]
        if not child_keys:
            return {
                "id": node_id,
                "label": name,
                "status": status,
                "meta": meta,
            }

        children: List[Dict[str, Any]] = []
        for key in sorted(
            child_keys,
            key=lambda x: (LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 999, x),
        ):
            children.append(_walk(key, obj[key], node_id))
        return {
            "id": node_id,
            "label": name,
            "status": status,
            "meta": meta,
            "children": children,
        }

    return {
        "id": node_id,
        "label": "%s: %s" % (name, str(obj)),
        "status": "none",
    }


def _legacy_manifest_to_tree(data: Any) -> Dict[str, Any]:
    roots: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        # 跳过顶层 *_status 标量，避免重复根节点
        top_keys = [
            k
            for k in data.keys()
            if not (isinstance(k, str) and k.endswith("_status"))
        ]
        ordered = sorted(
            top_keys,
            key=lambda x: (LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 999, x),
        )
        for key in ordered:
            roots.append(_walk(key, data[key], ""))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            roots.append(_walk("item_%s" % idx, item, ""))
    else:
        roots.append(_walk("manifest", data, ""))

    return {"roots": roots, "levels": LEVEL_ORDER}


def manifest_to_tree(raw_yaml: str) -> Dict[str, Any]:
    text = (raw_yaml or "").strip()
    if not text:
        return {"roots": [], "levels": LEVEL_ORDER, "summary": {}}

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return {"roots": [], "levels": LEVEL_ORDER, "error": str(exc), "summary": {}}

    if _is_tpops_manifest(data):
        assert isinstance(data, dict)
        return _build_tpops_tree(data)

    return _legacy_manifest_to_tree(data)
