# Plan：Go（Gin）+ SQLite 轻量实现方案

> **分支**：`go-dev` — Go 相关实现与文档均在此分支推进；`main` 保持现有 Django 栈直至迁移就绪。  
> **状态**：设计文档（未开始 Go 代码实现）。

## 1. 背景与目标

- 当前仓库为 **Django + DRF + Channels + SQLite + Vue SPA**（见 `AGENTS.md`、`docs/PROJECT_GUIDE.md`）。
- 目标在 **`go-dev`** 分支探索 **轻量级** 替代实现：**单二进制、SQLite 单文件、低依赖**，尽量复用现有 **REST / WebSocket 契约** 与前端，降低切换成本。
- **非目标**（首期）：微服务拆分、PostgreSQL 必选、完整 Django Admin 等价物。

## 2. 范围与非目标

**范围内**

- HTTP：REST API（路径与 JSON 尽量与 `/api/*` 对齐）。
- 鉴权：JWT（Access/Refresh 行为与现网对齐思路）。
- 实时：WebSocket（任务日志、manifest 推送，消息 `type` 与现实现一致或可文档化差异）。
- 业务：用户、主机、部署任务、安装包（与现有模型能力对齐）。
- 执行：`runner` 等价管道（SSH、user_edit 下发、manifest 轮询、包同步）。
- 存储：**SQLite**（与现网一致，轻量部署）。

**范围外（首期可不做）**

- 多区域高可用、K8s Operator。
- 与 Django **同一 SQLite 文件双进程并发写**（迁移期禁止，见风险）。

## 3. 推荐技术栈（Gin + SQLite）

| 能力 | 选型 | 说明 |
|------|------|------|
| Web | **Gin** | 路由、中间件、与 `net/http` 兼容 |
| DB | **SQLite** + **`modernc.org/sqlite`** | 纯 Go、免 cgo，便于小镜像 |
| SQL | **`database/sql` + `jmoiron/sqlx`**（可选） | 比全功能 ORM 更轻、更可控 |
| 迁移 | **`pressly/goose`** 或 **`golang-migrate/migrate`** | 版本化 schema |
| 配置 | **`caarlos0/env`** | 环境变量驱动 |
| JWT | **`golang-jwt/jwt/v4`** | 与 Go 1.18 常用组合兼容 |
| 密码 | **`golang.org/x/crypto/bcrypt`** | |
| WebSocket | **`github.com/gorilla/websocket`** | Gin 中 Upgrade；Hub 内存分发 |
| YAML | **`gopkg.in/yaml.v3`** | manifest |
| SSH/SFTP | **`golang.org/x/crypto/ssh`** + **`github.com/pkg/sftp`** | 对齐 Paramiko 能力 |
| 校验 | **`go-playground/validator/v10`** | 请求 DTO |
| 日志 | **`go.uber.org/zap`** 或 **zerolog** | 结构化 |
| 静态资源 | **`embed.FS`** + Gin 静态路由 | 托管现有 SPA / `static/` |

**可选（变重再上）**

- **Redis**：仅多副本 WebSocket 广播或分布式限流时需要。
- **任务队列库**：默认 `go func` + DB 状态机；吞吐不足再引入 `river` / `asynq` 等。

**Go 版本**：若团队锁定 **Go 1.18**，`go.mod` 写 `go 1.18`，CI 固定小版本；依赖库需核对 `go` directive，避免间接升级到要求 1.20+ 的模块。

## 4. 仓库与目录约定（建议）

在 `go-dev` 上新增 **独立 Go 模块**（与 Python 树并存，避免污染现有 `manage.py` 工作流）：

```
go/                          # 或 cmd/tpops-server，团队定名后统一
  go.mod
  go.sum
  cmd/server/main.go         # 入口：配置、迁移、Listen
  internal/
    config/
    db/                      # SQLite 打开、DSN、迁移
    middleware/              # JWT、Recover、RequestID、CORS
    domain/                  # 纯类型与常量
    repository/              # SQL 层
    service/                 # 用例与 runner 编排
    handler/http/            # Gin 路由
    handler/ws/              # WS + Hub
    ssh/
    manifest/                # 与 apps/manifest/parser 行为对齐（测试驱动）
    crypto/                  # 主机密钥加解密（与现 Fernet 兼容或迁移说明）
```

Python 代码仍在仓库根目录；**CI** 可增加 `go test ./go/...`（路径按实际模块根调整）。

## 5. SQLite 使用规范（轻量但必须做对）

1. **DSN**（示例意图）：`_journal_mode=WAL`、`_busy_timeout=5000`、`_foreign_keys=on`。
2. **连接池**：`SetMaxOpenConns` 取小值；**写路径短事务**，避免长时间持锁。
3. **Runner**：先更新 DB 状态并 **提交**，再执行 SSH；SSH 期间不持有业务写锁。
4. **备份**：文件级备份 + WAL checkpoint 说明；文档写明「不建议 Django 与 Go 同时写同一 `.db`」。

## 6. API 与 WebSocket 衔接

- **REST**：保持 `/api/auth/`、`/api/hosts/`、`/api/deployment/tasks/`、`/api/packages/` 等前缀；差异在 `plan` 末尾「契约差异表」维护。
- **WebSocket**：与现网一致的路径与 query（如 `token`）；消息类型：`hello`、`phase`、`log`、`manifest`、`manifest_wait`、`status`、`done` 等（与 `apps/deployment/runner.py`、consumers 对齐）。
- **Manifest 快照**：保留 `GET /api/deployment/tasks/:id/manifest_snapshot/` 语义（任务结束后单次拉远端 YAML 解析），便于前端刷新流水线与子任务 meta（如 `finish_execute_time`）。

## 7. 安全

- JWT Secret、主机密钥不入库明文；日志脱敏。
- 登录接口简单限流（内存 token bucket 即可）。
- 文件上传：大小限制、路径白名单（与现产品约定一致）。

## 8. 分期交付（建议）

| 阶段 | 内容 | 验收 |
|------|------|------|
| P0 | Gin 骨架、配置、日志、`/healthz`、SQLite 打开 + goose 空库 | 容器/本地可启动 |
| P1 | 用户表 + JWT 登录/刷新 | 与前端登录联调 |
| P2 | Host / Task CRUD（只读列表优先） | 对齐现有列表字段 |
| P3 | WS Hub + 假 runner 推送 | 前端监控页有实时消息 |
| P4 | SSH 流式 + runner + manifest 解析 | 与现行为一致（黄金 YAML 测试） |
| P5 | 安装包上传、静态 embed | 功能闭环 |
| P6 | 数据迁移脚本、运维文档、压测与锁调优 | 上线 checklist |

## 9. 风险与对策

| 风险 | 对策 |
|------|------|
| SQLite `database is locked` | WAL + busy_timeout + 短写事务 + 限制并发写 |
| manifest 与 Python 不一致 | 同输入 YAML 双端 JSON 对比测试；差异文档化 |
| 双栈共 SQLite | 禁止双写；迁移窗口只读或导出再切换 |

## 10. 待产品 / 技术确认

- Go **目标版本**（1.18 锁定 vs 直接 1.21+）。
- 迁移期是否 **允许** 并行运行两套后端（建议 API 网关分流，**不**共享同一 DB 文件写）。
- 是否必须 **100% API 字段兼容** 或允许少量 breaking（需前端配合列表）。

## 11. 实现记录

- **2026-04**：在 `go-dev` 分支创建本 Plan。
- **2026-04**：落地 `go/` 模块骨架：`cmd/server`、Gin、`goose` 迁移、`SQLite`、JWT、`/api/auth/login|register|profile`、`/api/hosts/`、`/api/deployment/tasks/`（详见 `go/README.md`）。**未实现**：WS、runner、manifest、包管理。
- **2026-04**：增加 `manifest` 包（单/多节点合并与 Python 对齐）、`GET .../manifest_snapshot/`、`GET .../tasks/:id/`、WebSocket `/ws/deploy/:id/?token=`（hello）；Fernet 解密主机凭证。**未实现**：runner 实时流、包上传、log tail WS。
