# 第 11 章：安全与运维注意（小白版）

本章列出**最容易踩坑**的配置与习惯；不涉及复杂安全审计，只帮助日常自建环境不翻车。

---

## 1. 密钥与环境变量

| 项 | 说明 |
|------|------|
| `DJANGO_SECRET_KEY` | 生产必须改成随机长串；JWT 签名、Session（若用）等都依赖它 |
| 主机 `credential` | 存的是加密密文；**日志里不要打印解密后的密码/私钥** |
| `.env` | 若有，勿提交到 git（仓库 `.gitignore` 已忽略常见项） |

---

## 2. JWT 使用习惯

- **access**：短命；泄露后在过期前他人可冒充你调 API。  
- **refresh**：更长；泄露后果更严重。前端应谨慎存放。  
- **HTTPS**：生产环境务必整站 HTTPS，否则 token 易被窃听。

---

## 3. Channels 与多进程

默认 **`InMemoryChannelLayer`**：

- **单进程 Daphne**：开发足够。  
- **多 worker**：后台线程 `group_send` 与浏览器 WebSocket **可能不在同一进程** → 收不到消息。  

生产多进程请改为 **Redis Channel Layer**（需额外运维 Redis）。

---

## 4. 数据库与并发

默认 **SQLite** 在「HTTP 请求 + 后台任务线程」同时写库时可能出现 **database is locked**。  
`settings` 里已加 `timeout` 缓解；若仍频繁失败，请换 **PostgreSQL** 等。

---

## 5. 任务本地日志

部署任务除 WebSocket 外，可写 **`logs/deployment_tasks/task_<id>.log`**（可用环境变量改目录，见 `task_file_log.py`）。  

- 便于事后排错；  
- 注意磁盘空间与权限。

---

## 6. DEBUG 与公网

`DEBUG=True` 时 Django 会暴露详细错误页，**切勿对公网开放**。  
`CORS_ALLOW_ALL_ORIGINS` 在 DEBUG 下常为真，生产需收紧。

---

## 7. 备份建议（运维）

定期备份：

- 数据库文件或 DB 导出  
- `media/`（若存安装包）  
- 主机与任务相关的业务配置导出（若有）

---

上一章：[工程壳与目录地图](10-project-layout-and-files.md)  
返回：[分章目录](README.md)
