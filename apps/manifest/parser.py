"""
解析 TPOPS docker-service 的 manifest.yaml。

结构要点（与 crontab/manifest 更新脚本一致）：
- 顶层：各层聚合状态，如 patch_status、base_enviornment_status、…
- 各层键（如 patch、base_enviornment）：值为服务项列表，每项含 name、script、status、retry_time 等
"""
import re
from typing import Any, Dict, List, Optional

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


def _parse_duration_seconds(val: Any) -> float:
    """Best-effort parse install_require_time / similar to seconds for ETA sum."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else 0.0
    s = str(val).strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        pass
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([hms])?$", s, re.I)
    if m:
        num = float(m.group(1))
        u = (m.group(2) or "s").lower()
        if u == "h":
            return num * 3600
        if u == "m":
            return num * 60
        return num
    digits = re.findall(r"\d+(?:\.\d+)?", s)
    if digits:
        try:
            return float(digits[0])
        except ValueError:
            pass
    return 0.0


def _estimated_install_seconds_from_data(data: Dict[str, Any]) -> float:
    total = 0.0
    if not isinstance(data, dict):
        return total
    for level in LEVEL_ORDER:
        block = data.get(level)
        if not isinstance(block, list):
            continue
        for item in block:
            if isinstance(item, dict):
                total += _parse_duration_seconds(item.get("install_require_time"))
    return total


def _first_running_service(roots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for root in roots or []:
        if not isinstance(root, dict):
            continue
        lid = root.get("id") or root.get("label")
        for ch in root.get("children") or []:
            if not isinstance(ch, dict):
                continue
            st = _norm_status(ch.get("status"))
            if st in ("running", "retrying"):
                meta = ch.get("meta") if isinstance(ch.get("meta"), dict) else {}
                return {
                    "level": lid,
                    "level_label": root.get("label") or lid,
                    "id": ch.get("id"),
                    "label": ch.get("label") or ch.get("id"),
                    "status": st,
                    "start_time": meta.get("start_time"),
                    "install_require_time": meta.get("install_require_time"),
                }
    return None


def enrich_manifest_summary(summary: Dict[str, Any], roots: List[Dict[str, Any]], data: Any) -> None:
    """
    Mutates summary with progress %, ETA sum, first running service (for UI).
    ``data`` is the raw manifest dict (single node) or None (caller fills estimate separately).
    """
    if not isinstance(summary, dict):
        return
    lt = int(summary.get("levels_total") or 0)
    ld = int(summary.get("levels_done") or 0)
    st = int(summary.get("services_total") or 0)
    sd = int(summary.get("services_done") or 0)
    summary["levels_progress_percent"] = int(round(100.0 * ld / lt)) if lt else 0
    summary["services_progress_percent"] = int(round(100.0 * sd / st)) if st else 0
    summary["progress_percent"] = (
        summary["services_progress_percent"] if st else summary["levels_progress_percent"]
    )
    if isinstance(data, dict):
        summary["estimated_total_seconds"] = round(
            _estimated_install_seconds_from_data(data), 1
        )
    running = _first_running_service(roots)
    summary["current_running_service"] = running
    summary["services_running"] = sum(
        1
        for r in roots or []
        if isinstance(r, dict)
        for ch in (r.get("children") or [])
        if isinstance(ch, dict) and _norm_status(ch.get("status")) in ("running", "retrying")
    )


def _is_tpops_manifest(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for level in LEVEL_ORDER:
        sk = "%s_status" % level
        if sk in data or level in data:
            return True
    return False


def _per_node_progress_from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """单份 manifest 字典上的层/服务完成度（用于三节点分列进度）。"""
    lv_done = sum(
        1
        for lv in LEVEL_ORDER
        if _norm_status(d.get("%s_status" % lv)) == "done"
    )
    st_done = 0
    st_total = 0
    for lv in LEVEL_ORDER:
        block = d.get(lv)
        if not isinstance(block, list):
            continue
        for item in block:
            if isinstance(item, dict):
                st_total += 1
                if _norm_status(item.get("status")) == "done":
                    st_done += 1
    pct = int(round(100.0 * st_done / st_total)) if st_total else 0
    return {
        "levels_done": lv_done,
        "levels_total": len(LEVEL_ORDER),
        "services_done": st_done,
        "services_total": st_total,
        "progress_percent": min(100, max(0, pct)),
    }


def enrich_pipeline_multi_nodes(
    pipeline: List[Dict[str, Any]],
    roots: List[Dict[str, Any]],
    nodes_meta: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """为 pipeline 子步骤附加各节点状态（三节点并行安装可视化）。"""
    if not pipeline or not nodes_meta or len(nodes_meta) < 2:
        return pipeline
    labels = [
        str(nm.get("label") or ("节点%s" % (nm.get("index", 0) + 1)))
        for nm in nodes_meta
    ]
    root_by_id = {r.get("id"): r for r in roots if isinstance(r, dict)}
    for row in pipeline:
        root = root_by_id.get(row.get("key"))
        if not root:
            continue
        by_child_id = {
            c.get("id"): c
            for c in (root.get("children") or [])
            if isinstance(c, dict)
        }
        if len(nodes_meta) > 1:
            row["parallel_note"] = "三节点并行安装（各节点 manifest 合并）"
        for sub in row.get("children") or []:
            ch = by_child_id.get(sub.get("id"))
            if not ch:
                continue
            meta = ch.get("meta") if isinstance(ch.get("meta"), dict) else {}
            nodes_part = meta.get("nodes")
            if not isinstance(nodes_part, list) or not nodes_part:
                continue
            node_details = []
            for nm_entry in nodes_part:
                if not isinstance(nm_entry, dict):
                    continue
                idx = int(nm_entry.get("node_index", 0))
                lab = labels[idx] if 0 <= idx < len(labels) else "节点%s" % (idx + 1)
                node_details.append(
                    {
                        "node_index": idx,
                        "node_label": lab,
                        "status": _norm_status(nm_entry.get("status")),
                    }
                )
            if node_details:
                sub["node_details"] = node_details
    return pipeline


def build_pipeline_from_roots(roots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    流水线：大层串行（顺序即 roots 顺序），每层内子服务并发（展示说明）。
    """
    cn = "一二三四五六七八九十"
    pipeline = []
    for i, root in enumerate(roots or []):
        if not isinstance(root, dict):
            continue
        idx = i + 1
        step_cn = cn[idx - 1] if idx <= 10 else str(idx)
        title = "步骤%s：%s" % (step_cn, root.get("label") or root.get("id") or "")
        subs = []
        for ch in root.get("children") or []:
            if not isinstance(ch, dict):
                continue
            lab = ch.get("label") or ch.get("id") or ""
            subs.append(
                {
                    "id": ch.get("id"),
                    "label": lab,
                    "status": ch.get("status") or "none",
                }
            )
        pipeline.append(
            {
                "index": idx,
                "key": root.get("id"),
                "title": title,
                "level_status": root.get("status") or "none",
                "parallel_note": "本层内子步骤并发执行",
                "children": subs,
            }
        )
    return pipeline


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
    enrich_manifest_summary(summary, roots, data)

    return {
        "roots": roots,
        "levels": LEVEL_ORDER,
        "summary": summary,
        "pipeline": build_pipeline_from_roots(roots),
    }


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

    return {
        "roots": roots,
        "levels": LEVEL_ORDER,
        "pipeline": build_pipeline_from_roots(roots),
    }


_STATUS_PRIORITY = {
    "error": 60,
    "null": 55,
    "retrying": 50,
    "running": 40,
    "none": 20,
    "done": 10,
}


def _agg_status(statuses: List[str]) -> str:
    best = "done"
    bp = _STATUS_PRIORITY.get(best, 0)
    for s in statuses:
        ss = _norm_status(s)
        p = _STATUS_PRIORITY.get(ss, 15)
        if p > bp:
            bp = p
            best = ss
    return best


def merge_tpops_manifest_dicts(
    dicts: List[Dict[str, Any]],
    manifest_paths: Optional[List[str]] = None,
    node1_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """多节点 manifest 字典合并为一棵树（聚合各层/各服务状态）。"""
    if not dicts:
        return {
            "roots": [],
            "levels": LEVEL_ORDER,
            "summary": {},
            "nodes": [],
            "pipeline": [],
        }

    nodes_meta = []
    paths = manifest_paths or []
    for i, d in enumerate(dicts):
        if not isinstance(d, dict):
            continue
        label = "node_%s" % (i + 1)
        if i < len(paths):
            p = paths[i]
            if "manifest_" in p and p.endswith(".yaml"):
                import re as _re

                m = _re.search(r"manifest_([0-9.]+)\.yaml", p)
                if m:
                    label = m.group(1)
            elif p.endswith("/manifest.yaml") or p.endswith("manifest.yaml"):
                label = "local"
        nodes_meta.append(
            {
                "index": i,
                "label": label,
                "path": p if i < len(paths) else "",
                "role": ("node1", "node2", "node3")[i] if i < 3 else "node_%s" % (i + 1),
            }
        )
    n1 = (node1_ip or "").strip()
    for nm in nodes_meta:
        if nm.get("role") == "node1" and n1:
            nm["label"] = n1
        elif nm.get("label") == "local" and not n1:
            nm["label"] = "节点1（manifest.yaml）"

    merged_levels = {}
    for level in LEVEL_ORDER:
        sk = "%s_status" % level
        aggs = [_norm_status(d.get(sk)) for d in dicts if isinstance(d, dict)]
        merged_levels[level] = _agg_status(aggs) if aggs else "none"

    roots: List[Dict[str, Any]] = []
    summary = {
        "levels_total": len(LEVEL_ORDER),
        "levels_done": sum(1 for lv in LEVEL_ORDER if merged_levels.get(lv) == "done"),
        "levels_running": sum(
            1 for lv in LEVEL_ORDER if merged_levels.get(lv) in ("running", "retrying")
        ),
        "levels_error": sum(1 for lv in LEVEL_ORDER if merged_levels.get(lv) == "error"),
        "levels_none": sum(1 for lv in LEVEL_ORDER if merged_levels.get(lv) == "none"),
        "by_level": dict(merged_levels),
        "services_total": 0,
        "services_done": 0,
    }

    for level in LEVEL_ORDER:
        sk = "%s_status" % level
        agg = merged_levels[level]
        children: List[Dict[str, Any]] = []

        # 按服务 name 对齐多节点（不按列表下标）
        per_node_by_name: List[Dict[str, Dict[str, Any]]] = []
        all_names = set()
        for d in dicts:
            if not isinstance(d, dict):
                per_node_by_name.append({})
                continue
            block = d.get(level)
            lst = block if isinstance(block, list) else ([] if block is None else [block])
            by_name = {}
            for item in lst:
                if isinstance(item, dict):
                    nm = str(item.get("name") or "").strip() or "_unnamed"
                    by_name[nm] = item
                    all_names.add(nm)
            per_node_by_name.append(by_name)

        for name in sorted(all_names):
            statuses = []
            metas = []
            script = ""
            for ni, by_name in enumerate(per_node_by_name):
                item = by_name.get(name)
                if isinstance(item, dict):
                    script = item.get("script") or script
                    stn = _norm_status(item.get("status"))
                    statuses.append(stn)
                    metas.append(
                        {
                            "node_index": ni,
                            "status": stn,
                            "finish_execute_time": item.get("finish_execute_time"),
                        }
                    )
            st = _agg_status(statuses) if statuses else "none"
            meta = {k: None for k in SERVICE_DETAIL_KEYS}
            if metas:
                meta["nodes"] = metas
            children.append(
                {
                    "id": "%s/%s" % (level, name),
                    "label": "%s · %s" % (name, script) if script else name,
                    "status": st,
                    "meta": meta,
                }
            )
            summary["services_total"] += 1
            if st == "done":
                summary["services_done"] += 1

        roots.append(
            {
                "id": level,
                "label": level,
                "status": agg,
                "meta": {"level_status_key": sk, "merged_nodes": len(dicts)},
                "children": children,
            }
        )

    est_sum = sum(
        _estimated_install_seconds_from_data(d) for d in dicts if isinstance(d, dict)
    )
    enrich_manifest_summary(summary, roots, None)
    summary["estimated_total_seconds"] = round(est_sum, 1)
    summary["multi_node"] = len(dicts) > 1
    summary["per_node_stats"] = [
        {
            "index": i,
            "label": (nodes_meta[i].get("label") if i < len(nodes_meta) else "node_%s" % (i + 1)),
            "role": (nodes_meta[i].get("role") if i < len(nodes_meta) else ""),
            "path": (nodes_meta[i].get("path") if i < len(nodes_meta) else ""),
            **_per_node_progress_from_dict(d),
        }
        for i, d in enumerate(dicts)
        if isinstance(d, dict)
    ]

    out = {
        "roots": roots,
        "levels": LEVEL_ORDER,
        "summary": summary,
        "nodes": nodes_meta,
    }
    pipe = build_pipeline_from_roots(roots)
    out["pipeline"] = enrich_pipeline_multi_nodes(pipe, roots, nodes_meta)
    return out


def manifest_to_tree(raw_yaml: str) -> Dict[str, Any]:
    text = (raw_yaml or "").strip()
    if not text:
        return {"roots": [], "levels": LEVEL_ORDER, "summary": {}, "pipeline": []}

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return {
            "roots": [],
            "levels": LEVEL_ORDER,
            "error": str(exc),
            "summary": {},
            "pipeline": [],
        }

    if _is_tpops_manifest(data):
        assert isinstance(data, dict)
        return _build_tpops_tree(data)

    return _legacy_manifest_to_tree(data)
