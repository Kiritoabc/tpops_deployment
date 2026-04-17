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
  "target": "echo step1 && your-remote-command-here",
  "deploy_mode": "single",
  "user_edit_content": "...",
  "skip_package_sync": true,
  "no_start": false
}
```

`target` 在远端以 `bash -lc` 在部署根目录下执行（输出写入 `remote_log_path`，默认 `logs/deploy_<id>.log`）。

## 与完整后端的差异（前端兼容说明）

- 安装包文件存于本地 `data/packages/release_<id>/`；与远端 `pkgs/` 同步等能力可按需扩展。

详见 `plan/plan-go-gin-sqlite-lightweight.md`。
