# TPOPS 白屏化部署工具 (MVP)

基于 **Django 3.2 + DRF + Channels** 与 **Vue 3 + Element Plus（CDN）** 的最小可用白屏化部署界面：管理 SSH 目标机、通过 WebSocket 推送 `appctl.sh` 日志，并按设计文档轮询解析远程 `manifest.yaml` 为树形结构。前端为深色侧栏控制台风格（可折叠侧栏、顶栏面包屑、卡片层次）。样式使用 **`clamp` / `vh` / `dvh`** 等做日志区、流水线区与表格高度的**响应式适配**，便于不同分辨率与笔记本小屏使用。

**实现与架构详解（推荐阅读）：** [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) — 数据流、runner 步骤、WebSocket、manifest、权限与目录导航。

**按顺序读代码：** [`docs/CODE_READING_GUIDE.md`](docs/CODE_READING_GUIDE.md) — 建议阅读路径、主链路、路由与 WebSocket 速查。

## 环境说明

- **生产目标**：Linux 上 **Python 3.7.9**（Django 4.x 需要 Python 3.8+，因此依赖锁定为 **Django 3.2 LTS**）。
- **本地开发**：可使用 Python 3.8+，依赖范围见 `requirements.txt`。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_SECRET_KEY='change-me'
# 每次更新代码或新环境后务必执行；跳过会导致表结构不一致，任务/接口异常
python3 manage.py migrate
python3 manage.py createsuperuser

# ASGI（HTTP + WebSocket）
daphne -b 0.0.0.0 -p 8000 tpops_deployment.asgi:application
```

### 在远程服务器上启动（不依赖 PyCharm Run）

若 PyCharm 远程运行报 **`Failed to prepare environment`** 等，可在 **SSH 登录服务器** 后在项目根执行：

```bash
cd /data/tpops_deployment   # 按你的实际路径
chmod +x scripts/run_daphne.sh
export DJANGO_SECRET_KEY='你的密钥'
./scripts/run_daphne.sh
```

等价于 `python -m daphne ...`；可用 `DAPHNE_BIND`、`DAPHNE_PORT` 覆盖监听地址与端口。**开发时**仍建议用 PyCharm 编辑代码 + 远程解释器做检查，服务在 SSH 终端里用上述方式启动。

若执行脚本时出现 **`/usr/bin/env: 'bash\r': No such file or directory`**，说明 `.sh` 被保存成 Windows 换行（CRLF）。仓库已用 `.gitattributes` 强制 `*.sh` 为 LF；请 **`git pull`** 后重试，或在服务器执行：`sed -i 's/\r$//' scripts/run_daphne.sh`

> **注意**：若 SSH 断开后未在本机跑过 `migrate`，`db.sqlite3` 可能仍是旧结构，部署任务等接口会表现异常；连上后补跑一次即可。

浏览器访问 `http://localhost:8000/`：

1. 注册 / 登录获取 JWT（登录页为左右分栏的华为云风格布局）  
2. 在「主机管理」填写远程 **部署根目录**（`appctl.sh` 所在目录，如 `/data/docker-service`）及 SSH 凭证  
3. 在「安装包管理」维护版本与介质（可选）；在「部署任务」向导中选择节点、按 **TPOPS 主包 / om-agent / OS 内核** 三类决定是否同步（未勾「同步此类」即跳过该类；介质写入节点 1 的 `<部署根>/pkgs/`）  
4. 在「操作与配置」步骤可点击 **从节点 1 读取远程配置**，从执行机拉取已有 `user_edit_file.conf` 填入编辑区（需主机已配置 SSH，见下文 API）  
5. 下发任务后通过 WebSocket 查看日志与 manifest 树  

**更新代码后请重启 Daphne**，否则新 API 与前端脚本不会生效；首页会为 `static/js/app/*.js` 自动追加 `?v=` 缓存破坏参数（见 `tpops_deployment/views.py` 中 `spa_index`）。

### 任务一直「待执行」、远程无动作？

默认使用 **SQLite**。创建任务后，执行逻辑在 **HTTP 请求外的后台线程**里跑；若未在子线程中刷新数据库连接，或并发写入触发 **`database is locked`**，可能出现任务不推进、界面无日志。当前版本已在执行线程入口调用 `close_old_connections()`，并为 SQLite 配置了 **`timeout: 30`**。生产环境仍建议使用 **PostgreSQL / MySQL** 等多连接数据库。

### 环境变量

| 变量 | 说明 |
|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥（亦用于加密存储 SSH 密码/私钥） |
| `DJANGO_DEBUG` | `1` / `0` |
| `DJANGO_ALLOWED_HOSTS` | 逗号分隔，默认 `*`（仅建议开发环境） |
| `DOCKER_SERVICE_ROOT` | 本机参考路径（当前 MVP 主要使用主机表中的远程路径） |

## 远程执行命令

在主机配置的部署根目录下执行；进度文件与脚本中 `CONFIG_HOME` 一致：

- 安装前置检查：`sh appctl.sh precheck install <组件>`
- 升级前置检查：`sh appctl.sh precheck upgrade <组件>`
- 安装操作：`sh appctl.sh install`（可选再跟「目标参数」）；**单节点**时通过 `yes y | sh appctl.sh …` 自动应答脚本中的 `(y/n)` 确认（非交互 SSH）。
- 升级操作：`sh appctl.sh upgrade`（可选「目标参数」）
- 卸载全部：`sh appctl.sh uninstall_all`（可选「目标参数」）；**通过 `yes y | sh appctl.sh …` 自动应答**脚本中可能出现的 `(y/n)` 确认（高危操作请谨慎）。
- **install / upgrade**：appctl 启动后在**执行机**上按任务形态轮询 manifest：  
  - **单节点**：`<部署根>/config/gaussdb/manifest.yaml`  
  - **三节点**：同上 `manifest.yaml`（对应 `user_edit` 中 **node1_ip** 侧主文件），并追加 **`manifest_<node2_ip>.yaml`**、**`manifest_<node3_ip>.yaml`**（仅当 `user_edit` 中填写了 `node2_ip` / `node3_ip`）；多文件解析后**合并**为一条流水线。路径均在执行机本地可读（需保证其它节点 manifest 已同步到该目录，或现场脚本约定一致）。  
  - **前端**：三节点安装时展示 **各节点独立进度条**（`summary.per_node_stats`）；流水线每层下按 **node1_ip / node2_ip / node3_ip** 分块列出子步骤及该节点状态。虚拟 **「步骤零：前置检查」** 在 patch 层未开始前保持 running；**当前进行的大层**自动高亮（类选中样式）。
- **precheck install / precheck upgrade / uninstall_all**：**不轮询 manifest**。
- **appctl 标准输出**：runner 按**行**（及无换行时约每 64 字符）拆分后写入通道；对 **`type: log`** 在服务端做**短时合并**（约 40ms 或 2KB 一批再 `group_send`），减轻 InMemory Channel Layer 下「每行一次跨线程调度」导致的积压，前端回显更接近实时。若现场脚本仍整块缓冲 stdout，可优先看 **`deploy/*.log`** 的 tail 通道。
- 部署日志：`{log_path}/deploy/precheck.log`、`{log_path}/deploy/install.log`、`{log_path}/deploy/uninstall.log`；WebSocket `ws/deploy/<id>/log/?kind=precheck|install|uninstall` 或 `&rel=文件名`（仅 `log_path/deploy/` 下安全文件名）实时 tail。Manifest 每层服务以横向圆点链展示，点击圆点默认 tail 当前阶段对应日志。

### 部署向导与 `user_edit_file.conf`

1. 选择 **单节点** 或 **三节点**（**节点 1** 为执行 SSH、写入 `user_edit_file.conf` 与执行 appctl 的机器）。节点 2/3 可选，仅作登记；**不在后台改写配置文件中的 IP**。
2. 填写 **`[user_edit]`** 段配置文本；**按填写内容原样写入远程文件**，不会用所选 SSH 节点的地址覆盖其中的 IP。向导中可先选节点 1，再使用 **「从节点 1 读取远程配置」** 调用 `GET /api/hosts/<id>/fetch_user_edit/`：在远端按与任务相同的规则探测上述路径之一，读出全文并通过 `[user_edit]` 校验后返回 JSON（`content`、`remote_path`），供粘贴到表单。
3. 后端在节点 1 上检测存在的文件并覆盖（与脚本一致）：
   - `<部署根>/config/gaussdb/user_edit_file.conf`
   - `<部署根>/config/user_edit_file.conf`  
   若两个都不存在，则 **创建** 默认路径 `config/gaussdb/user_edit_file.conf`（自动 `mkdir -p`）。
4. **安装包同步**（未勾选「跳过全部同步」时）：在 `install` / `upgrade` 下若勾选了 **TPOPS-GaussDB-Server** 主包，runner 会在节点 1 上走 `/data` 解压与介质汇聚；否则仅将已选文件 **扁平 SFTP** 到 `<部署根>/pkgs/`。其它任务类型为扁平同步。详见 `plan/plan-tpops-gaussdb-package-selection.md`。
5. 再执行所选 `appctl.sh` 操作。

## 项目结构（摘要）

- `apps/tpops_auth`：自定义用户 + JWT（避免与 `django.contrib.auth` 的 app label 冲突）
- `apps/hosts`：主机与 SSH 凭证（Fernet 加密）
- `apps/deployment`：任务模型、user_edit 解析合并、`user_edit_file.conf` 远程写入、appctl 执行 + Channels 组播
- `apps/manifest`：`manifest.yaml` 解析 API（调试）
- `apps/logs`：WebSocket 路由与消费者
- `templates/index.html`：应用壳（标题、CDN 脚本、`spa_index` 注入的静态资源 `?v=`）  
- `static/js/app/*.js`、`static/css/app.css`：Vue 单页模板与样式（登录、工作台、部署向导等）

## 安装包管理（设计）

完整约定与分期说明见 **`plan/plan-install-packages.md`**；新功能请先在该目录增加 **`plan/plan-<主题>.md`** 再开发（见 **`plan/README.md`**）。

## API 前缀

- `/api/auth/` — 注册、登录、刷新 Token、个人信息  
- `/api/hosts/` — 主机 CRUD、`POST …/test_connection/` 连通性测试、`GET …/<id>/fetch_user_edit/` 从执行机读取已有 `user_edit_file.conf`（需 JWT，与主机列表同权限；返回 `content` + `remote_path`，内容须含合法 `[user_edit]` 段）  
- `/api/deployment/tasks/` — 创建 / 列表 / 详情任务  
- `/api/packages/releases/`、`/api/packages/artifacts/` — 安装包版本与文件上传（multipart）  
- `/ws/deploy/<task_id>/?token=<access_jwt>` — 任务 appctl 输出与 manifest 推送  
- `/ws/deploy/<task_id>/log/?token=<jwt>&kind=precheck|install|uninstall` — `deploy/*.log`  
- `/ws/deploy/<task_id>/log/?token=<jwt>&rel=precheck.log` — 同上目录指定文件名  

## 许可

内部工具，按仓库策略使用。
