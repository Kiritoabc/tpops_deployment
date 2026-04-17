# TPOPS Go 服务（`go-dev`）

轻量 **Gin + SQLite（modernc）** 实现，与现有 Django 前端可并行联调（**不同端口**）。

## 运行

```bash
cd go
go mod download
go run ./cmd/server
```

默认：

- 监听：`TPOPS_GO_LISTEN`（默认 `:8081`，避免与 Django `8000` 冲突）
- 数据库：`go/data/tpops_go.db`（自动 `goose` 迁移）
- JWT：`TPOPS_GO_JWT_SECRET`（务必在生产修改）

## 开发账号（仅迁移种子）

- 用户名：`admin`
- 密码：`admin`

来自 `migrations/00002_seed_dev_admin.sql`；生产部署请删除该迁移或改密。

## 已实现 API（前缀与 Django 一致）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/healthz` | 健康检查 |
| POST | `/api/auth/login/` | 登录，body `{"username","password"}` |
| POST | `/api/auth/register/` | 注册 |
| GET | `/api/auth/profile/` | `Authorization: Bearer <access>` |
| GET | `/api/hosts/` | 需 JWT |
| GET | `/api/deployment/tasks/` | 需 JWT |

## 前端联调

将浏览器或 `axios` 的 `baseURL` 指向 Go 服务（例如 `http://127.0.0.1:8081`）。注意：Go 签发的 JWT **与 Django SimpleJWT 密钥不同**，不能混用同一 `access` 调两个后端。

## 后续（见 `plan/plan-go-gin-sqlite-lightweight.md`）

- WebSocket、`runner`、manifest、`manifest_snapshot`、安装包上传等。
