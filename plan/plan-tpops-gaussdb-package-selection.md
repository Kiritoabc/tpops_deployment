# TPOPS GaussDB 安装介质：选包与远端准备

**状态**：已实现（MVP）  
**关联**：`apps/deployment/runner.py`、`apps/deployment/serializers.py`、`apps/deployment/package_patterns.py`、`static/js/app/deploy.js`、`static/js/app/template.js`、`static/js/app/main.js`

## 目标

1. **部署向导**：将「安装包 / 介质」从「操作与配置」中拆出，**先选节点 → 再选包 → 最后配置与下发**。
2. **介质类型（当前版本）**：与上传命名一致的三类（可选除 TPOPS 主包外）：
   - `TPOPS-GaussDB-Server_{CPU}_*.tar.gz`（安装 / 升级且未跳过时 **必选**）
   - `DBS-GaussDB-Kernel_{CPU}_*.tar.gz`（om-agent，可选）
   - `DBS-GaussDB-{OS}-Kernel_{CPU}_*.tar.gz`（内核，可选）
3. **执行机（节点 1）**：在 `install` / `upgrade` 且未跳过同步时，于远端执行：`/data` 落盘 → 解压 TPOPS 包 → 解压包内 `DBS-*docker-service*.tar.gz`（若存在）→ 将 TPOPS 目录下 `DBS-*` / `GaussDB_*` 移入 `<部署根>/pkgs/` → 将所选内核包上传至 `pkgs/`。其余动作仍使用原有扁平 `pkgs/` 同步。

## 非目标（MVP）

- 多历史版本兼容策略、节点 2/3 传包。
- 自动探测远端是否已有介质（除包内 docker-service 解压外不做复杂跳过）。

## 数据模型

- `DeploymentTask.package_cpu_type`、`package_os_type`：用于校验文件名中的 `{CPU}`、`{OS}`；向导提供下拉默认值。

## 验收

- 向导四步可走完；`install`/`upgrade` 未跳过时必选 TPOPS 主包且文件名符合 CPU/OS 约定。
- 任务执行日志可见 `/data` 与 `pkgs` 准备阶段；`appctl` 行为不变。
