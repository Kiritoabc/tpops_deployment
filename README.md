# TPOPS 部署服务（Go）

**分支 `go-dev`**：本仓库此分支仅保留 **Gin + SQLite（modernc）** 实现；内嵌静态页（`/`、`/assets/`），与历史 Web 栈无代码依赖。

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
- **解密主机凭证（Fernet）**：`TPOPS_GO_FERNET_SECRET`；若为空则读取 `TPOPS_APP_SECRET_KEY`（须与加密主机凭证时使用的应用主密钥一致）

## 开发账号（仅迁移种子）

- 用户名：`admin`
- 密码：`admin`

来自 `migrations/00002_seed_dev_admin.sql`；生产请删除该迁移或改密。

## 已实现 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 嵌入的简单控制台页面 |
| GET | `/assets/*` | 嵌入的静态资源 |
| GET | `/healthz` | 健康检查 |
| POST | `/api/auth/login/` | 登录 |
| POST | `/api/auth/register/` | 注册 |
| GET | `/api/auth/profile/` | 需 JWT |
| GET | `/api/hosts/` | 需 JWT |
| GET | `/api/deployment/tasks/` | 需 JWT |
| GET | `/api/deployment/tasks/:id/` | 任务详情 |
| GET | `/api/deployment/tasks/:id/manifest_snapshot/` | SSH 拉 manifest 并解析 |
| GET | `/ws/deploy/:id/?token=<access_jwt>` | WebSocket：`hello` |

## 设计与后续

见 `plan/plan-go-gin-sqlite-lightweight.md`（Runner 全量流式、日志 WS、包上传等）。
