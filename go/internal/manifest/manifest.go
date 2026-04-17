package manifest

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

// LevelOrder 与 apps/manifest/parser.py 一致
var LevelOrder = []string{
	"patch", "base_enviornment", "PlatformData", "Zookeeper", "Kafka",
	"docker_service", "gaussdb_service", "post_service",
}

var serviceDetailKeys = []string{
	"script", "retry_time", "start_time_is_record", "start_time",
	"install_require_time", "repair_require_time", "upgrade_require_time",
	"rollback_require_time", "uninstall_require_time", "finish_flag", "finish_execute_time",
}

var statusPriority = map[string]int{
	"error": 60, "null": 55, "retrying": 50, "running": 40, "none": 20, "done": 10,
}

func NormStatus(v interface{}) string {
	if v == nil {
		return "none"
	}
	switch t := v.(type) {
	case string:
		s := strings.ToLower(strings.TrimSpace(t))
		if s == "" {
			return "none"
		}
		return s
	default:
		return strings.ToLower(fmt.Sprint(t))
	}
}

func aggStatus(statuses []string) string {
	best := "done"
	bp := statusPriority[best]
	for _, s := range statuses {
		ss := NormStatus(s)
		p := statusPriority[ss]
		if p == 0 {
			p = 15
		}
		if p > bp {
			bp = p
			best = ss
		}
	}
	return best
}

func isTPOPSManifest(data map[string]interface{}) bool {
	for _, level := range LevelOrder {
		if _, ok := data[level+"_status"]; ok {
			return true
		}
		if _, ok := data[level]; ok {
			return true
		}
	}
	return false
}

func metaFromItem(item map[string]interface{}) map[string]interface{} {
	out := make(map[string]interface{})
	for _, k := range serviceDetailKeys {
		if v, ok := item[k]; ok {
			out[k] = v
		}
	}
	return out
}

func serviceNode(levelKey string, idx int, item interface{}) map[string]interface{} {
	nodeID := fmt.Sprintf("%s/item_%d", levelKey, idx)
	m, ok := item.(map[string]interface{})
	if !ok {
		return map[string]interface{}{
			"id": nodeID, "label": fmt.Sprint(item), "status": "none",
		}
	}
	name := fmt.Sprint(m["name"])
	if strings.TrimSpace(name) == "" {
		name = fmt.Sprintf("item_%d", idx)
	}
	script := fmt.Sprint(m["script"])
	status := NormStatus(m["status"])
	label := name
	if script != "" {
		label = name + " · " + script
	}
	id := fmt.Sprintf("%s/%s", levelKey, name)
	return map[string]interface{}{
		"id": id, "label": label, "status": status, "meta": metaFromItem(m),
	}
}

func enrichManifestSummary(summary map[string]interface{}, roots []interface{}, data map[string]interface{}) {
	lt := intFrom(summary["levels_total"])
	ld := intFrom(summary["levels_done"])
	st := intFrom(summary["services_total"])
	sd := intFrom(summary["services_done"])
	if lt > 0 {
		summary["levels_progress_percent"] = int(math.Round(100 * float64(ld) / float64(lt)))
	} else {
		summary["levels_progress_percent"] = 0
	}
	if st > 0 {
		summary["services_progress_percent"] = int(math.Round(100 * float64(sd) / float64(st)))
	} else {
		summary["services_progress_percent"] = 0
	}
	if st > 0 {
		summary["progress_percent"] = summary["services_progress_percent"]
	} else {
		summary["progress_percent"] = summary["levels_progress_percent"]
	}
	if data != nil {
		summary["estimated_total_seconds"] = round1(estimatedInstallSeconds(data))
	}
	summary["current_running_service"] = firstRunningService(roots)
	summary["services_running"] = countRunningServices(roots)
}

func intFrom(v interface{}) int {
	switch t := v.(type) {
	case int:
		return t
	case int64:
		return int(t)
	case float64:
		return int(t)
	default:
		n, _ := strconv.Atoi(fmt.Sprint(t))
		return n
	}
}

func round1(f float64) float64 {
	return math.Round(f*10) / 10
}

func estimatedInstallSeconds(data map[string]interface{}) float64 {
	var total float64
	for _, level := range LevelOrder {
		block, _ := data[level]
		lst, ok := block.([]interface{})
		if !ok {
			continue
		}
		for _, item := range lst {
			if m, ok := item.(map[string]interface{}); ok {
				total += parseDurationSeconds(m["install_require_time"])
			}
		}
	}
	return total
}

var durRe = regexp.MustCompile(`^(\d+(?:\.\d+)?)\s*([hms])?$`)

func parseDurationSeconds(v interface{}) float64 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok && f >= 0 {
		return f
	}
	s := strings.TrimSpace(fmt.Sprint(v))
	if s == "" {
		return 0
	}
	if x, err := strconv.ParseFloat(s, 64); err == nil && x >= 0 {
		return x
	}
	m := durRe.FindStringSubmatch(strings.ToLower(s))
	if len(m) == 3 {
		num, _ := strconv.ParseFloat(m[1], 64)
		u := m[2]
		if u == "h" {
			return num * 3600
		}
		if u == "m" {
			return num * 60
		}
		return num
	}
	return 0
}

func firstRunningService(roots []interface{}) interface{} {
	for _, r := range roots {
		root, ok := r.(map[string]interface{})
		if !ok {
			continue
		}
		lid := root["id"]
		lbl := root["label"]
		ch, _ := root["children"].([]interface{})
		for _, c := range ch {
			cm, ok := c.(map[string]interface{})
			if !ok {
				continue
			}
			st := NormStatus(cm["status"])
			if st == "running" || st == "retrying" {
				meta, _ := cm["meta"].(map[string]interface{})
				mt := map[string]interface{}{}
				if meta != nil {
					if v, ok := meta["start_time"]; ok {
						mt["start_time"] = v
					}
					if v, ok := meta["install_require_time"]; ok {
						mt["install_require_time"] = v
					}
				}
				return map[string]interface{}{
					"level": lid, "level_label": lbl, "id": cm["id"],
					"label": cm["label"], "status": st,
					"start_time": mt["start_time"], "install_require_time": mt["install_require_time"],
				}
			}
		}
	}
	return nil
}

func countRunningServices(roots []interface{}) int {
	n := 0
	for _, r := range roots {
		root, ok := r.(map[string]interface{})
		if !ok {
			continue
		}
		ch, _ := root["children"].([]interface{})
		for _, c := range ch {
			cm, ok := c.(map[string]interface{})
			if !ok {
				continue
			}
			st := NormStatus(cm["status"])
			if st == "running" || st == "retrying" {
				n++
			}
		}
	}
	return n
}

// BuildTpopsTree 单份 manifest 字典 → 与 Python _build_tpops_tree 对齐的 JSON 友好结构
func BuildTpopsTree(data map[string]interface{}) map[string]interface{} {
	roots := []interface{}{}
	summary := map[string]interface{}{
		"levels_total": len(LevelOrder), "levels_done": 0, "levels_running": 0,
		"levels_error": 0, "levels_none": 0, "by_level": map[string]interface{}{},
	}
	byLevel := summary["by_level"].(map[string]interface{})

	for _, level := range LevelOrder {
		sk := level + "_status"
		agg := NormStatus(data[sk])
		byLevel[level] = agg
		switch agg {
		case "done":
			summary["levels_done"] = intFrom(summary["levels_done"]) + 1
		case "running":
			summary["levels_running"] = intFrom(summary["levels_running"]) + 1
		case "error":
			summary["levels_error"] = intFrom(summary["levels_error"]) + 1
		case "none":
			summary["levels_none"] = intFrom(summary["levels_none"]) + 1
		}
		children := []interface{}{}
		block := data[level]
		switch b := block.(type) {
		case []interface{}:
			for idx, item := range b {
				children = append(children, serviceNode(level, idx, item))
			}
		case map[string]interface{}:
			children = append(children, serviceNode(level, 0, b))
		}
		roots = append(roots, map[string]interface{}{
			"id": level, "label": level, "status": agg,
			"meta": map[string]interface{}{"level_status_key": sk},
			"children": children,
		})
	}
	svcTotal, svcDone := 0, 0
	for _, level := range LevelOrder {
		block, _ := data[level].([]interface{})
		for _, item := range block {
			if m, ok := item.(map[string]interface{}); ok {
				svcTotal++
				if NormStatus(m["status"]) == "done" {
					svcDone++
				}
			}
		}
	}
	summary["services_total"] = svcTotal
	summary["services_done"] = svcDone
	enrichManifestSummary(summary, rootsInterfaceToAny(roots), data)

	out := map[string]interface{}{
		"roots": roots, "levels": LevelOrder, "summary": summary,
		"pipeline": BuildPipelineFromRoots(roots),
	}
	return out
}

func rootsInterfaceToAny(roots []interface{}) []interface{} { return roots }

// ToJSONMaps 将 []interface{} 内 map 转为 map[string]interface{} 供 pipeline 使用
func toRootMaps(roots []interface{}) []map[string]interface{} {
	out := make([]map[string]interface{}, 0, len(roots))
	for _, r := range roots {
		if m, ok := r.(map[string]interface{}); ok {
			out = append(out, m)
		}
	}
	return out
}

// BuildPipelineFromRoots 与 Python build_pipeline_from_roots 一致
func BuildPipelineFromRoots(roots []interface{}) []interface{} {
	cn := "一二三四五六七八九十"
	pipe := []interface{}{}
	for i, r := range roots {
		root, ok := r.(map[string]interface{})
		if !ok {
			continue
		}
		idx := i + 1
		stepCn := strconv.Itoa(idx)
		if idx <= 10 {
			runes := []rune(cn)
			stepCn = string(runes[idx-1])
		}
		title := fmt.Sprintf("步骤%s：%s", stepCn, strOr(root["label"], root["id"]))
		subs := []interface{}{}
		ch, _ := root["children"].([]interface{})
		for _, c := range ch {
			cm, ok := c.(map[string]interface{})
			if !ok {
				continue
			}
			lab := strOr(cm["label"], cm["id"])
			subs = append(subs, map[string]interface{}{
				"id": cm["id"], "label": lab, "status": strOr(cm["status"], "none"),
			})
		}
		pipe = append(pipe, map[string]interface{}{
			"index": idx, "key": root["id"], "title": title,
			"level_status": strOr(root["status"], "none"),
			"parallel_note": "本层内子步骤并发执行",
			"children": subs,
		})
	}
	return pipe
}

func strOr(a, b interface{}) string {
	if a != nil && fmt.Sprint(a) != "" {
		return fmt.Sprint(a)
	}
	return fmt.Sprint(b)
}

// EnrichPipelineMultiNodes 与 Python enrich_pipeline_multi_nodes 对齐
func EnrichPipelineMultiNodes(pipeline []interface{}, roots []map[string]interface{}, nodesMeta []map[string]interface{}) []interface{} {
	if len(pipeline) == 0 || len(nodesMeta) < 2 {
		return pipeline
	}
	labels := make([]string, len(nodesMeta))
	for i, nm := range nodesMeta {
		lab := nm["label"]
		if lab == nil || fmt.Sprint(lab) == "" {
			labels[i] = fmt.Sprintf("节点%d", intFrom(nm["index"])+1)
		} else {
			labels[i] = fmt.Sprint(lab)
		}
	}
	rootByID := make(map[string]map[string]interface{})
	for _, r := range roots {
		if id := fmt.Sprint(r["id"]); id != "" {
			rootByID[id] = r
		}
	}
	for _, prow := range pipeline {
		row, ok := prow.(map[string]interface{})
		if !ok {
			continue
		}
		root := rootByID[fmt.Sprint(row["key"])]
		if root == nil {
			continue
		}
		byChild := make(map[string]map[string]interface{})
		ch, _ := root["children"].([]interface{})
		for _, c := range ch {
			cm, ok := c.(map[string]interface{})
			if !ok {
				continue
			}
			byChild[fmt.Sprint(cm["id"])] = cm
		}
		if len(nodesMeta) > 1 {
			row["parallel_note"] = "三节点并行安装（各节点 manifest 合并）"
		}
		subs, _ := row["children"].([]interface{})
		for _, s := range subs {
			sub, ok := s.(map[string]interface{})
			if !ok {
				continue
			}
			ch := byChild[fmt.Sprint(sub["id"])]
			if ch == nil {
				continue
			}
			meta, _ := ch["meta"].(map[string]interface{})
			if meta == nil {
				continue
			}
			nodesPart, _ := meta["nodes"].([]interface{})
			if len(nodesPart) == 0 {
				continue
			}
			nodeDetails := []interface{}{}
			for _, nmEntry := range nodesPart {
				nme, ok := nmEntry.(map[string]interface{})
				if !ok {
					continue
				}
				idx := intFrom(nme["node_index"])
				lab := labels[idx]
				if idx < 0 || idx >= len(labels) {
					lab = fmt.Sprintf("节点%d", idx+1)
				}
				nodeDetails = append(nodeDetails, map[string]interface{}{
					"node_index": idx, "node_label": lab,
					"status": NormStatus(nme["status"]),
				})
			}
			if len(nodeDetails) > 0 {
				sub["node_details"] = nodeDetails
			}
		}
	}
	return pipeline
}

func perNodeProgressFromDict(d map[string]interface{}) map[string]interface{} {
	lvDone := 0
	for _, lv := range LevelOrder {
		if NormStatus(d[lv+"_status"]) == "done" {
			lvDone++
		}
	}
	stDone, stTotal := 0, 0
	for _, lv := range LevelOrder {
		block, _ := d[lv].([]interface{})
		for _, item := range block {
			if m, ok := item.(map[string]interface{}); ok {
				stTotal++
				if NormStatus(m["status"]) == "done" {
					stDone++
				}
			}
		}
	}
	pct := 0
	if stTotal > 0 {
		pct = int(math.Round(100 * float64(stDone) / float64(stTotal)))
	}
	if pct < 0 {
		pct = 0
	}
	if pct > 100 {
		pct = 100
	}
	return map[string]interface{}{
		"levels_done": lvDone, "levels_total": len(LevelOrder),
		"services_done": stDone, "services_total": stTotal, "progress_percent": pct,
	}
}

// MergeTpopsManifestDicts 与 Python merge_tpops_manifest_dicts 对齐（多节点）
func MergeTpopsManifestDicts(dicts []map[string]interface{}, manifestPaths []string, node1IP string) map[string]interface{} {
	if len(dicts) == 0 {
		return map[string]interface{}{
			"roots": []interface{}{}, "levels": LevelOrder, "summary": map[string]interface{}{},
			"nodes": []interface{}{}, "pipeline": []interface{}{},
		}
	}
	nodesMeta := []map[string]interface{}{}
	for i := range dicts {
		label := fmt.Sprintf("node_%d", i+1)
		if i < len(manifestPaths) {
			p := manifestPaths[i]
			if strings.Contains(p, "manifest_") && strings.HasSuffix(p, ".yaml") {
				if m := regexp.MustCompile(`manifest_([0-9.]+)\.yaml`).FindStringSubmatch(p); len(m) > 1 {
					label = m[1]
				}
			} else if strings.HasSuffix(p, "manifest.yaml") || strings.Contains(p, "/manifest.yaml") {
				label = "local"
			}
		}
		role := fmt.Sprintf("node_%d", i+1)
		if i < 3 {
			role = []string{"node1", "node2", "node3"}[i]
		}
		path := ""
		if i < len(manifestPaths) {
			path = manifestPaths[i]
		}
		nodesMeta = append(nodesMeta, map[string]interface{}{
			"index": i, "label": label, "path": path, "role": role,
		})
	}
	n1 := strings.TrimSpace(node1IP)
	for _, nm := range nodesMeta {
		if fmt.Sprint(nm["role"]) == "node1" && n1 != "" {
			nm["label"] = n1
		} else if fmt.Sprint(nm["label"]) == "local" && n1 == "" {
			nm["label"] = "节点1（manifest.yaml）"
		}
	}
	mergedLevels := make(map[string]string)
	for _, level := range LevelOrder {
		sk := level + "_status"
		var sts []string
		for _, d := range dicts {
			if d == nil {
				continue
			}
			sts = append(sts, NormStatus(d[sk]))
		}
		if len(sts) > 0 {
			mergedLevels[level] = aggStatus(sts)
		} else {
			mergedLevels[level] = "none"
		}
	}
	roots := []interface{}{}
	summary := map[string]interface{}{
		"levels_total": len(LevelOrder),
		"levels_done": 0, "levels_running": 0, "levels_error": 0, "levels_none": 0,
		"by_level": map[string]interface{}{}, "services_total": 0, "services_done": 0,
	}
	for k, v := range mergedLevels {
		summary["by_level"].(map[string]interface{})[k] = v
		switch v {
		case "done":
			summary["levels_done"] = intFrom(summary["levels_done"]) + 1
		case "running", "retrying":
			summary["levels_running"] = intFrom(summary["levels_running"]) + 1
		case "error":
			summary["levels_error"] = intFrom(summary["levels_error"]) + 1
		case "none":
			summary["levels_none"] = intFrom(summary["levels_none"]) + 1
		}
	}

	for _, level := range LevelOrder {
		sk := level + "_status"
		agg := mergedLevels[level]
		perNodeByName := []map[string]map[string]interface{}{}
		allNames := map[string]struct{}{}
		for _, d := range dicts {
			byName := map[string]map[string]interface{}{}
			if d == nil {
				perNodeByName = append(perNodeByName, byName)
				continue
			}
			block := d[level]
			var lst []interface{}
			switch b := block.(type) {
			case []interface{}:
				lst = b
			case map[string]interface{}:
				lst = []interface{}{b}
			case nil:
			default:
			}
			for _, item := range lst {
				if m, ok := item.(map[string]interface{}); ok {
					nm := strings.TrimSpace(fmt.Sprint(m["name"]))
					if nm == "" {
						nm = "_unnamed"
					}
					byName[nm] = m
					allNames[nm] = struct{}{}
				}
			}
			perNodeByName = append(perNodeByName, byName)
		}
		names := make([]string, 0, len(allNames))
		for n := range allNames {
			names = append(names, n)
		}
		sort.Strings(names)
		children := []interface{}{}
		for _, name := range names {
			var statuses []string
			var metas []map[string]interface{}
			script := ""
			for ni, byName := range perNodeByName {
				item := byName[name]
				if item != nil {
					if s := item["script"]; s != nil && fmt.Sprint(s) != "" {
						script = fmt.Sprint(s)
					}
					stn := NormStatus(item["status"])
					statuses = append(statuses, stn)
					metas = append(metas, map[string]interface{}{
						"node_index": ni, "status": stn,
						"finish_execute_time": item["finish_execute_time"],
					})
				}
			}
			st := "none"
			if len(statuses) > 0 {
				st = aggStatus(statuses)
			}
			meta := map[string]interface{}{}
			for _, k := range serviceDetailKeys {
				meta[k] = nil
			}
			if len(metas) > 0 {
				meta["nodes"] = toIfaceSlice(metas)
			}
			lbl := name
			if script != "" {
				lbl = name + " · " + script
			}
			children = append(children, map[string]interface{}{
				"id": fmt.Sprintf("%s/%s", level, name), "label": lbl, "status": st, "meta": meta,
			})
			summary["services_total"] = intFrom(summary["services_total"]) + 1
			if st == "done" {
				summary["services_done"] = intFrom(summary["services_done"]) + 1
			}
		}
		roots = append(roots, map[string]interface{}{
			"id": level, "label": level, "status": agg,
			"meta": map[string]interface{}{"level_status_key": sk, "merged_nodes": len(dicts)},
			"children": children,
		})
	}
	estSum := 0.0
	for _, d := range dicts {
		if d != nil {
			estSum += estimatedInstallSeconds(d)
		}
	}
	rootMaps := toRootMaps(roots)
	enrichManifestSummary(summary, roots, nil)
	summary["estimated_total_seconds"] = round1(estSum)
	summary["multi_node"] = len(dicts) > 1
	perStats := []interface{}{}
	for i, d := range dicts {
		if d == nil {
			continue
		}
		ps := perNodeProgressFromDict(d)
		nm := map[string]interface{}{}
		if i < len(nodesMeta) {
			nm = nodesMeta[i]
		}
		entry := map[string]interface{}{
			"index": i,
			"label": nm["label"],
			"role":  nm["role"],
			"path":  nm["path"],
		}
		for k, v := range ps {
			entry[k] = v
		}
		perStats = append(perStats, entry)
	}
	summary["per_node_stats"] = perStats
	pipe := BuildPipelineFromRoots(roots)
	pipe = EnrichPipelineMultiNodes(pipe, rootMaps, nodesMeta)
	return map[string]interface{}{
		"roots": roots, "levels": LevelOrder, "summary": summary,
		"nodes": nodesMeta, "pipeline": pipe,
	}
}

func toIfaceSlice(m []map[string]interface{}) []interface{} {
	out := make([]interface{}, len(m))
	for i := range m {
		out[i] = m[i]
	}
	return out
}

// ManifestFromYAML 解析 YAML：单文件走 BuildTpopsTree；多文件路径与 dict 对齐后 Merge
func ManifestFromYAML(dicts []map[string]interface{}, paths []string, node1IP string) (map[string]interface{}, error) {
	if len(dicts) == 0 {
		return nil, fmt.Errorf("no yaml dicts")
	}
	if len(dicts) == 1 {
		t := BuildTpopsTree(dicts[0])
		t["manifest_paths"] = paths
		if s, ok := t["summary"].(map[string]interface{}); ok {
			s["multi_node"] = false
		}
		return t, nil
	}
	t := MergeTpopsManifestDicts(dicts, paths, node1IP)
	t["manifest_paths"] = paths
	return t, nil
}

// ParseYAMLToMap yaml 字符串 → map
func ParseYAMLToMap(raw string) (map[string]interface{}, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, fmt.Errorf("empty")
	}
	var data map[string]interface{}
	if err := yaml.Unmarshal([]byte(raw), &data); err != nil {
		return nil, err
	}
	if !isTPOPSManifest(data) {
		return nil, fmt.Errorf("not a tpops manifest top-level")
	}
	return data, nil
}
