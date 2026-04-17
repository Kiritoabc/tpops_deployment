# Plan：Go（Gin）+ SQLite 轻量实现方案

> **分支**：`go-dev` — 本分支为 **仅 Go** 的独立实现线，不与 `main` 合并。  
> **状态**：已含 **SSH Runner**（`target` 远程执行 + 日志落盘 + WS 推送）、**manifest 轮询**（install/upgrade）、**日志专用 WS**、**任务创建/启动**、**refresh token**；安装包上传等仍待办。

## 1. 背景与目标

- 在 **`go-dev`** 维护 **轻量级** 服务：**单二进制、SQLite 单文件、低依赖**，REST / WebSocket 契约与产品约定对齐。
- **非目标**（首期）：微服务拆分、PostgreSQL 必选、完整后台管理等价物。

## 2. 范围与非目标

**范围内**

- HTTP：REST API（路径与 JSON 尽量与既有 `/api/*` 产品约定对齐）。
- 鉴权：JWT（Access/Refresh 行为按产品需要演进）。
- 实时：WebSocket（任务日志、manifest 推送，消息 `type` 可文档化）。
- 业务：用户、主机、部署任务、安装包（能力逐步对齐）。
- 执行：`runner` 等价管道（SSH、user_edit、manifest 轮询、包同步）。
- 存储：**SQLite**。

**范围外（首期可不做）**

- 多区域高可用、K8s Operator。
- 多进程对 **同一 SQLite 文件并发写**（须避免，见风险）。

## 3. 推荐技术栈（Gin + SQLite）

| 能力 | 选型 | 说明 |
|------|------|------|
| Web | **Gin** | 路由、中间件、与 `net/http` 兼容 |
| DB | **SQLite** + **`modernc.org/sqlite`** | 纯 Go、免 cgo |
| SQL | **`database/sql` + `jmoiron/sqlx`** | 轻量数据访问 |
| 迁移 | **`pressly/goose`** | 版本化 schema |
| 配置 | **`caarlos0/env`** | 环境变量驱动 |
| JWT | **`golang-jwt/jwt/v5`** | HS256 |
| WebSocket | **`github.com/gorilla/websocket`** | Gin Upgrade；Hub 内存分发 |
| YAML | **`gopkg.in/yaml.v3`** | manifest |
| SSH | **`golang.org/x/crypto/ssh`** | 远程命令与文件 |
| 静态资源 | **`embed.FS`** + Gin 静态路由 | 内嵌控制台页 |

**Go 版本**：仓库锁定 **Go 1.18**（根目录 `go.mod`）；CI 建议固定 `GOTOOLCHAIN=go1.18.x`，避免依赖在较新工具链上“能编过”但实际要求更高 `go` directive。

## 4. 仓库与目录约定

`go-dev` 上 **模块根即仓库根**（与 `go.mod` 同级）：

```
cmd/server/main.go
internal/
  config/ db/ middleware/ repository/ service/ handler/ ...
migrations/
web/static/          # embed 静态前端
data/                # 本地 SQLite（默认路径，不入库大文件）
go.mod go.sum
```

CI：`go test ./...` 在仓库根执行。

## 5. SQLite 使用规范

1. DSN：`_journal_mode=WAL`、`_busy_timeout=5000`、`_foreign_keys=on`。
2. 连接池：`SetMaxOpenConns` 取小值；写路径短事务。
3. Runner：先提交 DB 状态再执行 SSH；SSH 期间不长时间持业务写锁。
4. 备份：文件级备份 + WAL checkpoint；避免多服务同时写同一 `.db`。

## 6. API 与 WebSocket

- **REST**：`/api/auth/`、`/api/hosts/`、`/api/deployment/tasks/`、`/api/packages/` 等按产品迭代。
- **WebSocket**：路径与 query（如 `token`）；消息类型目标：`hello`、`phase`、`log`、`manifest`、`manifest_wait`、`status`、`done` 等。
- **Manifest 快照**：`GET /api/deployment/tasks/:id/manifest_snapshot/`（远端 YAML 单次拉取并解析）。

## 7. 安全

- JWT Secret、主机密钥不入库明文；日志脱敏。
- 登录接口限流（内存 token bucket 等）。
- 文件上传：大小限制、路径白名单。

## 8. 分期交付（建议）

| 阶段 | 内容 | 验收 |
|------|------|------|
| P0 | Gin 骨架、配置、`/healthz`、SQLite + goose | 可启动 |
| P1 | 用户表 + JWT 登录/注册 | 可鉴权 |
| P2 | Host / Task 只读列表与详情 | 列表可用 |
| P3 | WS Hub + runner 推送 | 监控页有实时消息 |
| P4 | SSH 流式 + manifest | 与约定行为一致 |
| P5 | 安装包上传、静态 embed | 功能闭环 |
| P6 | 运维文档、压测与锁调优 | 上线 checklist |

## 9. 风险与对策

| 风险 | 对策 |
|------|------|
| SQLite `database is locked` | WAL + busy_timeout + 短写事务 |
| manifest 与参考行为不一致 | 黄金 YAML 测试；差异文档化 |
| 多写者争用 DB | 单写者或明确迁移窗口 |

## 10. 实现记录

- **2026-04**：本 Plan 与 `go-dev` 分支创建。
- **2026-04**：根目录模块：`cmd/server`、Gin、goose、SQLite、JWT、hosts/tasks API、manifest 包、`manifest_snapshot`、WS `hello`、Fernet、embed 静态页。
- **2026-04**：`go-dev` 去除历史 Web 栈目录，**Go 模块提升至仓库根**；`go-dev` 独立演进、**不合入 `main`**。
- **2026-04**：Runner：`POST /api/deployment/tasks/`、`POST .../start/`、`RunRemoteStream`、`phase`/`log`/`manifest`/`done`；`GET /ws/deploy/:id/log/`；`POST /api/auth/token/refresh/`；DB 列 `remote_log_path`。**待办**：包上传、主机 CRUD、与具体 `appctl` 产品命令对齐、登录限流。
