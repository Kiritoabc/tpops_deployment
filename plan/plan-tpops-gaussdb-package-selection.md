# TPOPS GaussDB 安装介质：选包与远端准备

**状态**：已实现（MVP）  
**关联**：`apps/deployment/runner.py`、`apps/deployment/serializers.py`、`apps/deployment/package_patterns.py`、`static/js/app/deploy.js`、`static/js/app/template.js`、`static/js/app/main.js`

## 目标

1. **部署向导**：将「安装包 / 介质」从「操作与配置」中拆出，**先选节点 → 再选包 → 最后配置与下发**。
2. **介质类型（当前版本）**：与上传命名一致的三类：
   - `TPOPS-GaussDB-Server_{CPU}_*.tar.gz`（安装 / 升级且未跳过时 **可选**；勾选才走 `/data` 解压与汇聚，否则仅扁平同步其它包）
   - `DBS-GaussDB-Kernel_{CPU}_*.tar.gz`（om-agent，可选）
   - `DBS-GaussDB-{OS}-Kernel_{CPU}_*.tar.gz`（内核，可选）
3. **执行机（节点 1）**：在 `install` / `upgrade`、未跳过同步且**勾选了 TPOPS 主包**时，于远端执行 `/data` 解压与 pkgs 汇聚；**未勾主包**则跳过该段，仅对已选 artifact 执行扁平 `pkgs/` 同步。其余动作仍使用原有扁平同步。

## 非目标（MVP）

- 多历史版本兼容策略、节点 2/3 传包。
- 自动探测远端是否已有介质（除包内 docker-service 解压外不做复杂跳过）。

## 数据模型

- `DeploymentTask.package_cpu_type`、`package_os_type`：字段保留；创建任务时不再由向导填写，服务端写空字符串。安装 / 升级时的介质规则仅依赖**文件名模式**（不再与用户所选 CPU/OS 交叉校验）。

## 验收

- 向导可走完；`install`/`upgrade` 未跳过时所选包文件名符合约定；主包可选（有则走 `/data` 流程，无则只同步已选包到 pkgs）。
- 任务执行日志可见 `/data` 与 `pkgs` 准备阶段；`appctl` 行为不变。
