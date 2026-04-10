from typing import Any, Dict, List, Optional

import yaml

# 设计文档中的层级顺序（用于排序展示）
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


def _status_from_obj(obj: Any) -> str:
    if not isinstance(obj, dict):
        return "none"
    for key in ("status", "state", "phase", "install_status"):
        val = obj.get(key)
        if isinstance(val, str) and val:
            return val.lower()
    return "none"


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
        status = _status_from_obj(obj)
        meta = _meta_from_obj(obj)
        # 若像叶子节点（含 status 且无复杂嵌套），仍可能有子字典
        child_keys = [
            k
            for k, v in obj.items()
            if k not in meta
            and k not in ("status", "state", "phase", "install_status")
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
        for key in sorted(child_keys, key=lambda x: (LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 999, x)):
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


def manifest_to_tree(raw_yaml: str) -> Dict[str, Any]:
    """
    将 manifest.yaml 文本解析为前端树形结构。
    兼容多种 YAML 顶层结构：dict / list / 单键包装。
    """
    text = (raw_yaml or "").strip()
    if not text:
        return {"roots": [], "levels": LEVEL_ORDER}

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return {"roots": [], "levels": LEVEL_ORDER, "error": str(exc)}

    roots: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        # 常见：顶层即为各 level
        top_keys = list(data.keys())
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
