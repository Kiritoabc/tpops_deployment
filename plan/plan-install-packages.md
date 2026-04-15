# Plan：TPOPS 安装包管理

**状态**：已实现（MVP）  
**关联**：华为 TPOPS 安装准备类文档（如 EDOC1100484838）；与现有「部署任务 / SSH / `appctl.sh`」衔接。

---

## 1. 背景与目标

- 在平台侧集中管理 **安装 TPOPS 所需的安装包**，支持 **多版本**；用户可 **新建版本**并上传介质。
- **执行安装类部署时**：用户可选 **版本**、可选 **要下发的包子集**、可选 **是否跳过上传**（环境上已有包时可不选）。
- 介质 **不通过 `appctl.sh` 参数传递**；仅同步到远端约定目录后，再 **照常执行** 现有 `sh appctl.sh ...`，由现场脚本从目录中取包。

---

## 2. 范围与非目标

**范围内（MVP）**

- 版本（Release）CRUD、包（Artifact）上传与元数据、部署任务关联「版本 + 勾选包列表」。
- 在 **节点 1（执行机，`DeploymentTask.host`）** 上：`mkdir -p <部署根>/pkgs` + SFTP 下发选中文件。
- 同名覆盖策略（见 §6）。

**非目标（可二期）**

- 分片上传、对象存储、包依赖拓扑、与 manifest 流水线 UI 深度联动。
- 向节点 2/3 传包（明确不做）。

---

## 3. 领域模型（建议）

| 实体 | 字段要点 |
|------|-----------|
| **Release** | 名称/版本号、描述、状态（启用/下线）、创建人、时间 |
| **Artifact** | 所属 `release_id`、存储路径或 object key、原始文件名、`remote_basename`（下发到 `pkgs/` 的文件名）、大小、SHA256、上传人、时间 |
| **DeploymentTask（扩展）** | `release_id`（可选）、`artifact_ids`（JSON 列表，可选）、`skip_package_sync`（bool，可选）等 |

**远端路径**：`<docker_service_root>/pkgs/`（如 `/data/docker-service/pkgs/`），与主机表 `docker_service_root` 一致。

---

## 4. 与现有流程的衔接

**执行顺序**（在 `apps/deployment/runner.py` 中，保持现有逻辑前后关系）：

1. 写 `user_edit_file.conf`（现有）。  
2. **若任务需要同步包**：对 `task.host` SSH → `mkdir -p <root>/pkgs` → 将选中 Artifact 以 **`remote_basename`** 写入 `pkgs/`（原子写：临时文件 + rename）。  
3. 执行 `sh appctl.sh ...`（现有）。  
4. WebSocket 打简短日志：`[pkgs] uploaded: a.tar.gz, b.zip` 或 `skipped`。

**不选包 / 跳过同步**：不执行步骤 2，或 `skip_package_sync=true`。

---

## 5. API 草案（REST）

前缀建议：`/api/packages/` 或 `/api/releases/`（与团队命名习惯二选一）。

- `GET/POST /api/releases/` — 版本列表、创建  
- `GET/PATCH/DELETE /api/releases/{id}/` — 详情、更新、删除（软删可选）  
- `GET/POST /api/releases/{id}/artifacts/` — 列表、上传（multipart）  
- `DELETE /api/releases/{id}/artifacts/{aid}/` — 删除包（可选）  
- 部署任务创建：`POST /api/deployment/tasks/` body 增加 `release`、`artifacts`、`skip_package_sync`（字段名以最终实现为准）

**权限**：与现有一致；上传/删版本建议 `operator`+，`viewer` 只读。

---

## 6. 同名包覆盖策略

### 6.1 平台库（同一 Release 内）

- 新上传与已有 **`remote_basename`（或规范化存储名）** 相同 → **更新同一条 Artifact 记录**：覆盖存储对象，刷新 size / SHA256 / 上传时间 / 操作人；**不保留两条同名记录**。

### 6.2 不同 Release

- 允许不同版本下存在相同 `remote_basename`；平台侧各存一份。

### 6.3 下发到远端 `pkgs/`

- 目标路径：`<root>/pkgs/<remote_basename>`。  
- 远端已存在同名文件：**覆盖**；实现建议 **临时文件 + rename** 原子替换。  
- 多版本先后下发同一 basename：**后执行的任务覆盖**远端文件。

### 6.4 文件名安全

- 禁止 `..`、`/`、`\` 等；规范化为 **单段文件名**。

---

## 7. 前端（Element Plus）

- 新菜单：**安装包管理**：左侧版本列表，右侧包列表 + 上传。  
- **部署向导**：增加「安装介质」——选版本、多选包、可选「跳过同步」。  
- **部署任务详情**：展示本次使用的版本与包列表。

---

## 8. 存储

- **MVP**：`MEDIA_ROOT` + DB 元数据。  
- **生产建议**：对象存储 / NFS，DB 仅存 key（二期）。

---

## 9. 待确认（若仍有歧义）

- [ ] 上传文件大小上限、是否仅允许白名单后缀（`.tar.gz` 等）。  
- [ ] Release「下线」后是否禁止新建任务选用该版本。

---

## 10. 实现记录

- **2026-04**：`apps.packages`（`PackageRelease` / `PackageArtifact`）、`MEDIA_ROOT`、`/api/packages/`、`DeploymentTask` 扩展字段、`runner` 在 `user_edit` 后同步 `pkgs/`；前端「安装包管理」+ 部署向导勾选；**不设**文件大小上限、后缀白名单、Release 下线逻辑（与产品约定一致）。
