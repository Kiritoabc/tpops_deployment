# TPOPS 白屏化部署平台 — 项目说明与实现逻辑

本文面向**需要自行阅读代码、理解实现与数据流**的开发者，说明本仓库的定位、架构、核心模块与执行路径。更偏「设计 + 导航」，与根目录 `README.md` 的「快速上手」互补。

**更系统的参考（数据模型表、每个 HTTP/WS URL 的实现说明、仓库文件地图、多张 Mermaid 图）：** [`PLATFORM_REFERENCE.md`](PLATFORM_REFERENCE.md)

---

## 1. 项目定位与目标

本系统是 **TPOPS / GaussDB 轻量化 docker-service 场景**下的 **Web 白屏化部署控制台**：

- 在 Web 上**纳管 SSH 主机**（部署根目录即 `appctl.sh` 所在目录，如 `/data/docker-service`）。
- 创建**部署任务**：选择操作类型（前置检查 / 安装 / 升级 / 卸载等）、填写 `user_edit_file.conf` 内容、可选**安装包版本与文件**。
- 服务端在**后台线程**中通过 **Paramiko** SSH 到**节点 1（执行机）**，**先**同步/解压安装介质（含 TPOPS 主包时：所选包先落到 `/data/`，解压 TPOPS 与包内 `docker-service` 后再创建 `<部署根>/pkgs/` 并汇入；避免覆盖已写配置），**再**写入 `user_edit_file.conf`、执行 `sh appctl.sh ...`。任务日志除 WebSocket 外可追加写入 `logs/deployment_tasks/task_<id>.log`。
- 通过 **Django Channels WebSocket** 向浏览器**实时推送**标准输出、manifest 解析结果、任务状态；可选连接**文件日志 tail**。

**非目标（当前 MVP）：** 不替代 `appctl.sh` 的业务逻辑；不在此项目内实现集群编排引擎；默认单机 SQLite 仅适合演示/小规模（生产建议 PostgreSQL 等）。

---

## 2. 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 语言 / Web | Python 3.7.9 兼容 | 生产环境约束 → **Django 3.2 LTS** |
| HTTP API | Django REST Framework + **SimpleJWT** | 无 Session 前端，Bearer / Query token |
| 实时通道 | **Django Channels** + Daphne | ASGI；默认 **InMemoryChannelLayer** |
| SSH | **Paramiko** | 执行远程命令、SFTP 写文件/传包 |
| 敏感存储 | **Fernet**（见 `apps/hosts/crypto.py`） | 主机密码/私钥加密落库 |
| 配置解析 | **PyYAML** | 远程 `manifest.yaml` 与本地解析 |
| 前端 | **Vue 3 + Element Plus（CDN）** 单页 | `templates/index.html` 内联应用；`tpops_deployment/views.py` **原始 HttpResponse** 避免 Django 模板误解析 `{{ }}` |

---

## 3. 仓库目录结构（逻辑地图）

```
tpops_deployment/          # Django 工程配置
  settings.py              # INSTALLED_APPS、JWT、Channels、MEDIA、DB timeout 等
  urls.py                  # /api/* 路由 + SPA 根路径
  asgi.py                  # HTTP + WebSocket 路由挂载顺序（注意 settings 先于 JWT 相关导入）
  views.py                 # spa_index：返回 index.html 原始内容

apps/
  tpops_auth/              # 自定义 User + 注册/登录/JWT
  hosts/                   # 主机模型、SSH、凭证加解密
  deployment/              # 部署任务模型、序列化、runner 编排、权限
  packages/                # 安装包 Release / Artifact、上传 API
  manifest/                # manifest REST（若存在）+ 核心解析在 parser
  logs/                    # WebSocket：部署事件 + 远程日志 tail

apps/manifest/parser.py    # TPOPS manifest YAML → 前端用树/流水线结构（含多文件合并）
apps/deployment/runner.py  # 任务线程：同步 pkgs（含 TPOPS 解压）、写配置、appctl、轮询 manifest、发 WS 消息
apps/hosts/ssh_client.py   # SSH 命令、SFTP、探测 user_edit 路径等

templates/index.html       # 完整前端 SPA（Vue setup）
plan/                      # 功能设计文档（plan-xxx.md）
```

---

## 4. 运行时与请求路径

### 4.1 启动方式

- **推荐：** `daphne -b 0.0.0.0 -p 8000 tpops_deployment.asgi:application`  
  同时承载 **HTTP（DRF）** 与 **WebSocket**。
- `manage.py runserver` 在开发中也可试 Channels，但生产/稳定演示建议 Daphne。

### 4.2 HTTP 路由摘要（`tpops_deployment/urls.py`）

| 路径 | 说明 |
|------|------|
| `/` | SPA：`spa_index` → `templates/index.html` |
| `/api/auth/` | 注册、登录、JWT 刷新等（`apps.tpops_auth`） |
| `/api/hosts/` | 主机 CRUD、连通性测试等 |
| `/api/deployment/tasks/` | 部署任务列表、创建、详情；`create` 会触发异步执行 |
| `/api/packages/` | 安装包版本与文件上传 |
| `/api/manifest/` | 与 manifest 相关的 HTTP（如有） |
| `/admin/` | Django Admin |
| `/media/...` | **仅 DEBUG** 下提供本地上传文件 |

### 4.3 WebSocket（`apps/logs/routing.py`）

| URL | Consumer | 用途 |
|-----|----------|------|
| `ws/deploy/<task_id>/?token=<JWT>` | `DeploymentConsumer` | 订阅任务组 `deployment_<id>`，接收 runner 推送的 log / manifest / status / done |
| `ws/deploy/<task_id>/log/?...` | `DeployLogTailConsumer` | 按参数 tail 远程 `log_path/deploy/` 下日志 |

**鉴权：** WS 连接使用 **Query String 中的 JWT**（浏览器原生 WebSocket 无法设 Header）。`DeploymentConsumer` 用 `AccessToken` 解析 `user_id`，再与 `get_deployment_task_for_user` 对齐权限。

---

## 5. 数据模型与职责

### 5.1 用户（`apps/tpops_auth`）

- 自定义 **`AUTH_USER_MODEL`**，避免与业务概念混淆；JWT 用于 API 与 WS。

### 5.2 主机 `Host`（`apps/hosts/models.py`）

- **连接信息：** `hostname`、`port`、`username`、`auth_method`（密码 / 私钥）。
- **凭证：** 加密字段 `credential`（明文仅通过 API 写入，不落明文）。
- **部署根目录：** `docker_service_root` → 远程 `cd <root> && sh appctl.sh ...`；manifest 相对路径为 `<root>/config/gaussdb/manifest.yaml` 等。
- **可见性：** 列表接口按 `created_by` 过滤（与部署任务一致思路）；详见 `HostViewSet`。

### 5.3 部署任务 `DeploymentTask`（`apps/deployment/models.py`）

核心字段逻辑：

- **`host`**：执行 SSH 的节点 1。
- **`action`**：`precheck_install` / `precheck_upgrade` / `install` / `upgrade` / `uninstall_all`。
- **`target`**：precheck 时组件名（如 `gaussdb`）；install/upgrade/uninstall 可选。
- **`deploy_mode`**：`single` / `triple`；影响 manifest **读取文件列表**（见下文）。
- **`host_node2` / `host_node3`**：三节点时在 UI 登记；**runner 不会用主机表 IP 覆盖 user_edit 里的 IP**。
- **`user_edit_content`**：整段文本写入远程 `user_edit_file.conf`（先解析 `[user_edit]` 校验，**原文覆盖写入**，不自动改用户 IP）。
- **`package_release` / `package_artifact_ids` / `skip_package_sync`**：安装包同步策略。
- **状态机：** `pending` → `running` → `success` / `failed` / `cancelled`；时间戳 `started_at` / `finished_at`。

### 5.4 安装包（`apps/packages/models.py`）

- **`PackageRelease`**：版本分组。
- **`PackageArtifact`**：`FileField` 存本地，`remote_basename` 为远端 `<部署根>/pkgs/` 下文件名；**同名同版本覆盖**策略在 serializer 中实现。

---

## 6. 部署任务：从创建到结束的执行逻辑

### 6.1 入口：`DeploymentTaskViewSet.create`

1. `DeploymentTaskCreateSerializer` 校验主机归属、user_edit、包与版本关系等。
2. `serializer.save()` 持久化任务。
3. **`run_task_async(task.id)`** → 启动 **daemon 线程** `_run_task`（**不在** HTTP 请求内阻塞）。

### 6.2 线程内主流程：`_run_task` → `_run_task_body`（`runner.py`）

**重要：** 线程开头与关键 ORM 操作前调用 **`close_old_connections()`**，避免 SQLite「database is locked」或连接失效。

建议按代码顺序理解：

1. **加载任务** `select_related(host, host_node2, host_node3, package_release)`。
2. **解密 SSH 凭证**；若无凭证则失败并 WS 通知。
3. **`parse_user_edit_block`**：校验 `[user_edit]` 段落；得到 **kv**（含 `node1_ip` / `node2_ip` / `node3_ip` 等）供 manifest 路径使用。
4. **`_sync_pkgs_to_remote`**：若未勾选跳过且选了 artifact，则同步介质（扁平到 `<root>/pkgs/`；或含 TPOPS 主包时先 `/data` 落盘再解压、移动/移入 `pkgs/`）。**先于**写入 `user_edit`，避免解压出的 `docker-service` 覆盖刚写入的配置。上传过程可通过 WebSocket `phase`（如 `media_upload`）驱动前端进度条。
5. **`resolve_user_edit_conf_path`**：在远端探测 `user_edit_file.conf` 位于 `config/gaussdb/` 或 `config/`；失败则可在默认路径创建目录。
6. **`write_remote_file_utf8`**：将 `user_edit_content` **原样**写入远程路径。
7. **`_build_appctl_command`**：拼出  
   `export LANG=...; cd <root> && yes y 2>/dev/null | sh appctl.sh <subcommand>`（install/upgrade/uninstall 自动答 y）。
8. **`run_remote_command`**：流式读 stdout/stderr，**逐块 `_emit` type=`log`**。
9. **Manifest 轮询（仅 install / upgrade）：**  
   - 启动 **`_poll_manifest_loop`**（单独逻辑：`threading.Event` 停止；**先立刻执行一次** `_poll_manifest_once`，再每 5s，避免「只 wait 不读」的竞态）。  
   - `_remote_manifest_paths_for_task`：单节点仅 `manifest.yaml`；三节点为 `manifest.yaml` + `manifest_<node2_ip>.yaml` + `manifest_<node3_ip>.yaml`（ip 非空才追加）。  
   - 每次 `remote_cat_file` → `yaml.safe_load` → `manifest_to_tree` 或 **`merge_tpops_manifest_dicts`** → `_emit` type=`manifest`。
10. **appctl 退出后**：更新 `exit_code`、`status`、`_emit` `done`；停止 manifest 轮询。

### 6.3 实时推送通道

- **`_emit(task_id, payload)`** → `channel_layer.group_send("deployment_<id>", {"type": "deployment_event", "payload": ...})`。
- **`DeploymentConsumer.deployment_event`** 将 payload **JSON** 发给浏览器。

常见 **`payload.type`**：

| type | 含义 |
|------|------|
| `log` | appctl 文本行（或平台前缀说明） |
| `manifest` | 解析后的树/流水线 JSON |
| `manifest_wait` / `manifest_error` | 未读到或异常 |
| `status` | 任务状态字符串 |
| `done` | 结束：含 `exit_code`、`finished_at` 等 |

前端 `templates/index.html` 中根据 type 更新流水线、日志区、状态条；从列表返回监控页时**可不断开 WS**，并尽量**保留同一任务的 log 缓冲**。

### 6.4 远程日志 WebSocket

- `DeployLogTailConsumer`：根据任务关联主机与部署根，在已知 `log_path` 规则下 **tail** `precheck.log` / `install.log` / `uninstall.log` 等（实现见 `apps/logs/log_tail_consumer.py` 与 `apps/deployment/remote_logs.py`）。

---

## 7. Manifest 解析与多节点合并（`apps/manifest/parser.py`）

- **输入：** TPOPS 风格 YAML：顶层有各层 `*_status`，各层名（如 `patch`）对应服务列表（`name`、`status`、耗时字段等）。
- **输出：** 供前端绘制的 **层级结构**、**汇总进度**、三节点时的 **`per_node_stats`** 等（具体字段以 `manifest_to_tree` / `merge_tpops_manifest_dicts` 返回为准）。
- **多文件：** 三节点多个 YAML 先分别解析再 **合并** 为单一流水线视图，并带上 `manifest_paths`、`deploy_mode` 等元数据。

---

## 8. 权限与多租户边界

- **部署任务列表/详情：** `filter_deployment_tasks_for_user` — 普通用户仅 `created_by=self` 或历史空属主任务；**staff** 看全部（与 README 描述一致，以代码为准）。
- **WebSocket 附加任务：** `get_deployment_task_for_user`，与 API 一致，防止越权订阅他人任务日志。

---

## 9. 前端 SPA（`templates/index.html`）

- **单文件应用**：Vue 3 `setup`、`axios` 调 REST、原生 `WebSocket` 带 token。
- **菜单模块：** 工作台、主机管理（列表 / 纳管表单）、安装包管理、部署任务（列表 / 向导 / 监控）。
- **兼容性：** 避免可选链等老浏览器不支持的语法（曾因此白屏）。
- **样式：** OceanBase 类控制台；大量 CSS 变量、`clamp`、`vh`；表格区域注意 **Element Plus `el-card` 默认 `overflow: hidden`** 与 `el-table` fixed 列的交互（项目内已针对性覆盖，见历史提交说明）。

---

## 10. 配置与环境变量（摘要）

| 变量 | 作用 |
|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥；兼用于凭证加密 |
| `DJANGO_DEBUG` | 调试开关；控制 `/media/` 等 |
| `DJANGO_ALLOWED_HOSTS` | 允许的主机头 |

数据库默认 **SQLite** + `timeout: 30`；生产请换 **PostgreSQL / MySQL** 并配置 `DATABASES`。

---

## 11. 扩展与维护建议

1. **Channel Layer**：多进程 / 多机部署时 **InMemoryChannelLayer** 无法跨进程；需换 **Redis** 等 `CHANNEL_LAYERS`。
2. **任务取消**：当前 `cancel` 多为标记；长时间 SSH 会话的真正中断需进程组 / 远端协作（文档已说明限制）。
3. **并发：** 同一主机并行多个 appctl 的风险由业务侧约束；平台未做强排他锁。
4. **新功能：** 先在 `plan/plan-xxx.md` 写方案再改代码（仓库约定）。

---

## 12. 相关文档

- 根目录 **`README.md`**：安装、迁移、启动、远程命令清单、`user_edit` 说明。
- **`docs/CODE_READING_GUIDE.md`**：按固定顺序阅读源码的主链路与文件索引（与本文互补）。
- **`plan/README.md`**：计划文档索引。
- **`plan/plan-install-packages.md`**：安装包管理功能设计与实现记录。

---

## 13. 关键文件速查表

| 需求 | 优先阅读文件 |
|------|----------------|
| 任务怎么跑起来 | `apps/deployment/views.py` → `runner.py` |
| SSH / 写文件 / 传包 | `apps/hosts/ssh_client.py` |
| manifest 结构 | `apps/manifest/parser.py` |
| WS 消息格式 | `apps/logs/consumers.py`、`runner.py` 中 `_emit` |
| 权限过滤 | `apps/deployment/access.py` |
| user_edit 解析 | `apps/deployment/user_edit.py` |
| 前端交互与 WS | `templates/index.html` |

---

*文档版本：与仓库实现同步维护；若代码与本文冲突，以代码为准。*
