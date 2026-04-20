# TPOPS 部署服务（Go）

**分支 `go-dev`**：本仓库此分支为 **Gin + SQLite（modernc）** 单服务；**Vue 3 + Element Plus（CDN）控制台**由 Gin 提供 HTML 与静态资源（`web/templates`、`web/static`）。

**目录说明**：Go 模块在**仓库根目录**（`go.mod`、`cmd/`、`internal/`），不使用 `go/` 子目录。

## 运行

本仓库 **`go 1.18`**。若本机默认 Go 较新，可先切换工具链，例如：`GOTOOLCHAIN=go1.18.10 go run ./cmd/server`。

```bash
go mod download
go run ./cmd/server
```

默认：

- 监听：`TPOPS_GO_LISTEN`（默认 `:8081`）
- 数据库：`data/tpops_go.db`（自动 `goose` 迁移）
- JWT：`TPOPS_GO_JWT_SECRET`（生产务必修改）
- **解密主机凭证（Fernet）**：优先 `TPOPS_GO_FERNET_SECRET`，其次 `TPOPS_APP_SECRET_KEY`；若均未设置，**首次启动**会在 `data/.fernet_secret` 自动生成随机密钥并复用（仅便于本地；**生产务必显式配置**）
- **安装包文件目录**：`TPOPS_GO_PACKAGES_DIR`（默认 `data/packages/`）

浏览器打开 **`/`** 即控制台（与 API 同域）。

## 开发账号（仅迁移种子）

- 用户名：`admin`
- 密码：`admin`

来自 `migrations/00002_seed_dev_admin.sql`；生产请删除该迁移或改密。

## 已实现 API（节选）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | `html/template` 渲染 SPA 壳 |
| GET | `/static/*` | 嵌入的 JS/CSS |
| GET | `/healthz` | 健康检查 |
| POST | `/api/auth/login/`、`/register/`、`/token/refresh/` | 鉴权 |
| GET | `/api/auth/profile/` | 需 JWT |
| GET | `/api/hosts/` | 主机列表（含 `owner_username`） |
| POST | `/api/hosts/` | 新增主机（密码或私钥经 Fernet 加密入库） |
| PATCH | `/api/hosts/:id/` | 更新主机；不传 `password`/`private_key` 则保留原凭证 |
| DELETE | `/api/hosts/:id/` | 删除主机 |
| POST | `/api/hosts/:id/test_connection/` | SSH 连通性检测 → `{ok,message}` |
| GET/POST | `/api/deployment/tasks/` 等 | 任务列表、创建、详情、`manifest_snapshot` |
| GET/POST/DELETE | `/api/packages/releases/`、`/api/packages/artifacts/` | 安装包版本；上传 `multipart` 字段 `file`、`release` |
| GET | `/ws/deploy/:id/`、`/ws/deploy/:id/log/` | WebSocket |

**创建任务**：默认**创建后立即启动 Runner**。若只要落库不执行，传 `"no_start": true`。

```json
{
  "host": 1,
  "action": "install",
  "target": "gaussdb",
  "deploy_mode": "single",
  "user_edit_content": "...",
  "package_release": 1,
  "package_artifact_ids": [1, 2],
  "skip_package_sync": false,
  "use_raw_shell": false,
  "no_start": false
}
```

- **`use_raw_shell`: true**（或 **`action`** 不在 appctl 白名单内）时，**`target` 整段作为 shell** 在部署根下执行，**不**封装 `appctl`。
- **`action`** 为 `install` / `upgrade` / `uninstall_all` / `precheck_install` / `precheck_upgrade` 且 **`use_raw_shell`: false** 时，Runner 执行 **`appctl <子命令> <target>`**（优先 `$ROOT/appctl`，否则 `PATH`）。**`target`** 一般为组件名（如 `gaussdb`）。
- **`skip_package_sync`: false** 且提供 **`package_release` + `package_artifact_ids`** 时，Runner **SFTP** 到各节点 `<部署根>/pkgs/`：**单节点**仅节点 1；**三节点**向节点 1、2、3 中**去重后的各主机并行**同步（命令仍在节点 1 执行）。
- **user_edit**：Runner 在包同步之后、执行主命令之前，将 **`user_edit_content`** 经 **SFTP** 写入远端 **`remote_user_edit_path`**（相对部署根；未填则默认 **`config/user_edit.conf`**）。
- 日志仍写入 `remote_log_path`（默认 `logs/deploy_<id>.log`）。

## 与完整后端的差异（前端兼容说明）

- 安装包本地目录：`data/packages/release_<id>/`；远端目录：`<部署根>/pkgs/`。

详见 `plan/plan-go-gin-sqlite-lightweight.md`。
