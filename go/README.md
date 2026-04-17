# TPOPS Go 服务（`go-dev`）

轻量 **Gin + SQLite（modernc）** 实现；默认自带嵌入的静态页（`/`、`/assets/`），也可单独用 HTTP 客户端联调 API。

## 运行

本模块 **`go 1.18`**。若本机默认 Go 较新，可用官方工具链切换后再构建，例如：`GOTOOLCHAIN=go1.18.10 go run ./cmd/server`。

```bash
cd go
go mod download
go run ./cmd/server
```

默认：

- 监听：`TPOPS_GO_LISTEN`（默认 `:8081`）
- 数据库：`go/data/tpops_go.db`（自动 `goose` 迁移）
- JWT：`TPOPS_GO_JWT_SECRET`（生产务必修改）
- **解密主机凭证（Fernet）**：设置 `TPOPS_GO_FERNET_SECRET`；若为空则读取 `TPOPS_APP_SECRET_KEY`（须与加密主机凭证时使用的应用主密钥一致）

## 开发账号（仅迁移种子）

- 用户名：`admin`
- 密码：`admin`

来自 `migrations/00002_seed_dev_admin.sql`；生产部署请删除该迁移或改密。

## 已实现 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 嵌入的简单控制台页面 |
| GET | `/assets/*` | 嵌入的静态资源 |
| GET | `/healthz` | 健康检查 |
| POST | `/api/auth/login/` | 登录，body `{"username","password"}` |
| POST | `/api/auth/register/` | 注册 |
| GET | `/api/auth/profile/` | `Authorization: Bearer <access>` |
| GET | `/api/hosts/` | 需 JWT |
| GET | `/api/deployment/tasks/` | 需 JWT |
| GET | `/api/deployment/tasks/:id/` | 任务详情 |
| GET | `/api/deployment/tasks/:id/manifest_snapshot/` | 单次 SSH 拉 manifest 并解析（install/upgrade） |
| GET | `/ws/deploy/:id/?token=<access_jwt>` | WebSocket：连接后推送 `hello` |

## 客户端说明

- 本服务签发的 JWT 仅用于访问本服务；与其他后端的密钥或 token 不可混用。
- 浏览器打开 `http://<listen>/` 可试用嵌入页；或将 `fetch` / `axios` 的 base URL 指向同一地址调用 `/api/*`。

## 后续（见 `plan/plan-go-gin-sqlite-lightweight.md`）

- Runner 实时流（SSH、`phase` / `log` / `manifest` / `done` 等 WS 消息）
- `/ws/deploy/:id/log/` 日志 tail
- 安装包上传
