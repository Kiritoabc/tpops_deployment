# TPOPS 白屏化部署工具 (MVP)

基于 **Django 3.2 + DRF + Channels** 与 **Vue 3 + Element Plus（CDN）** 的最小可用白屏化部署界面：管理 SSH 目标机、通过 WebSocket 推送 `appctl.sh` 日志，并按设计文档轮询解析远程 `manifest.yaml` 为树形结构。

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

在主机配置的部署根目录下执行（与 `appctl.sh` 同级读取 `manifest.yaml`）：

- 预检查：`bash appctl.sh precheck install <target>`
- 安装：`bash appctl.sh install <target>`

## 项目结构（摘要）

- `apps/tpops_auth`：自定义用户 + JWT（避免与 `django.contrib.auth` 的 app label 冲突）
- `apps/hosts`：主机与 SSH 凭证（Fernet 加密）
- `apps/deployment`：任务模型与后台线程执行 + Channels 组播
- `apps/manifest`：`manifest.yaml` 解析 API（调试）
- `apps/logs`：WebSocket 路由与消费者
- `templates/index.html`：Vue3 + Element Plus 单页（CDN）

## API 前缀

- `/api/auth/` — 注册、登录、刷新 Token、个人信息  
- `/api/hosts/` — 主机 CRUD、连通性测试  
- `/api/deployment/tasks/` — 创建 / 列表 / 详情任务  
- `/ws/deploy/<task_id>/?token=<access_jwt>` — 任务日志与 manifest 推送  

## 许可

内部工具，按仓库策略使用。
