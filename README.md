# TPOPS 白屏化部署工具 (MVP)

基于 **Django 3.2 + DRF + Channels** 与 **Vue 3 + Element Plus（CDN）** 的最小可用白屏化部署界面：管理 SSH 目标机、通过 WebSocket 推送 `appctl.sh` 日志，并按设计文档轮询解析远程 `manifest.yaml` 为树形结构。前端为深色侧栏控制台风格（可折叠侧栏、顶栏面包屑、卡片层次）。样式使用 **`clamp` / `vh` / `dvh`** 等做日志区、流水线区与表格高度的**响应式适配**，便于不同分辨率与笔记本小屏使用。

## 环境说明

- **生产目标**：Linux 上 **Python 3.7.9**（Django 4.x 需要 Python 3.8+，因此依赖锁定为 **Django 3.2 LTS**）。
- **本地开发**：可使用 Python 3.8+，依赖范围见 `requirements.txt`。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_SECRET_KEY='change-me'
python3 manage.py migrate
python3 manage.py createsuperuser

# ASGI（HTTP + WebSocket）
daphne -b 0.0.0.0 -p 8000 tpops_deployment.asgi:application
```

浏览器访问 `http://localhost:8000/`：

1. 注册 / 登录获取 JWT  
2. 在「主机管理」填写远程 **部署根目录**（`appctl.sh` 所在目录，如 `/data/docker-service`）及 SSH 凭证  
3. 在「部署任务」执行 **预检查** 或 **安装**，通过 WebSocket 查看日志与 manifest 树  

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
- 部署日志：`{log_path}/deploy/precheck.log`、`{log_path}/deploy/install.log`、`{log_path}/deploy/uninstall.log`；WebSocket `ws/deploy/<id>/log/?kind=precheck|install|uninstall` 或 `&rel=文件名`（仅 `log_path/deploy/` 下安全文件名）实时 tail。Manifest 每层服务以横向圆点链展示，点击圆点默认 tail 当前阶段对应日志。

### 部署向导与 `user_edit_file.conf`

1. 选择 **单节点** 或 **三节点**（**节点 1** 为执行 SSH、写入 `user_edit_file.conf` 与执行 appctl 的机器）。节点 2/3 可选，仅作登记；**不在后台改写配置文件中的 IP**。
2. 填写 **`[user_edit]`** 段配置文本；**按填写内容原样写入远程文件**，不会用所选 SSH 节点的地址覆盖其中的 IP。
3. 后端在节点 1 上检测存在的文件并覆盖（与脚本一致）：
   - `<部署根>/config/gaussdb/user_edit_file.conf`
   - `<部署根>/config/user_edit_file.conf`  
   若两个都不存在，则 **创建** 默认路径 `config/gaussdb/user_edit_file.conf`（自动 `mkdir -p`）。
4. 再执行所选 `appctl.sh` 操作。

## 项目结构（摘要）

- `apps/tpops_auth`：自定义用户 + JWT（避免与 `django.contrib.auth` 的 app label 冲突）
- `apps/hosts`：主机与 SSH 凭证（Fernet 加密）
- `apps/deployment`：任务模型、user_edit 解析合并、`user_edit_file.conf` 远程写入、appctl 执行 + Channels 组播
- `apps/manifest`：`manifest.yaml` 解析 API（调试）
- `apps/logs`：WebSocket 路由与消费者
- `templates/index.html`：Vue3 + Element Plus 单页（CDN）

## API 前缀

- `/api/auth/` — 注册、登录、刷新 Token、个人信息  
- `/api/hosts/` — 主机 CRUD、连通性测试  
- `/api/deployment/tasks/` — 创建 / 列表 / 详情任务  
- `/ws/deploy/<task_id>/?token=<access_jwt>` — 任务 appctl 输出与 manifest 推送  
- `/ws/deploy/<task_id>/log/?token=<jwt>&kind=precheck|install|uninstall` — `deploy/*.log`  
- `/ws/deploy/<task_id>/log/?token=<jwt>&rel=precheck.log` — 同上目录指定文件名  

## 许可

内部工具，按仓库策略使用。
