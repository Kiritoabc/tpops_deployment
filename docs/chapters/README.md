# 分章技术文档（按模块阅读）

本目录把平台按**模块**拆成多份文档，尽量用**通俗说法**解释概念；适合第一次接触本仓库的读者**按顺序**阅读。

| 顺序 | 章节 | 说明 |
|:----:|------|------|
| 0 | [写给完全小白：整体在干什么](00-overview-for-beginners.md) | 浏览器、服务器、数据库、SSH 各自做什么 |
| 1 | [数据库与数据模型](01-database-and-models.md) | 有哪些表、字段含义、表之间关系 |
| 2 | [HTTP 路由与一次请求怎么走](02-http-routing-and-requests.md) | URL、ASGI、DRF 视图、序列化器 |
| 3 | [认证模块 tpops_auth](03-auth-module.md) | 注册、登录、JWT、个人资料 |
| 4 | [主机模块 hosts](04-hosts-module.md) | SSH 主机、凭证加密、测连通、读远程配置 |
| 5 | [部署模块 deployment](05-deployment-module.md) | 任务、runner、传包、写配置、appctl、manifest |
| 6 | [安装包模块 packages](06-packages-module.md) | 版本、上传文件、远端 pkgs 文件名 |
| 7 | [清单模块 manifest](07-manifest-module.md) | YAML 解析、调试接口 |
| 8 | [日志与 WebSocket 模块 logs](08-logs-websockets-module.md) | 实时推送、任务日志 tail |
| 9 | [前端单页 SPA](09-frontend-spa.md) | Vue、模板、静态资源、和 API 怎么配合 |
| 10 | [Django 工程壳与目录地图](10-project-layout-and-files.md) | `tpops_deployment/`、各 `apps/` 文件职责总表 |
| 11 | [安全与运维注意](11-security-and-operations.md) | 密钥、JWT、Channels、日志路径 |

**合并总览（精简索引 + 常用图）：** 上一级 [`../PLATFORM_REFERENCE.md`](../PLATFORM_REFERENCE.md)

读完本目录后，可再读 [`../PROJECT_GUIDE.md`](../PROJECT_GUIDE.md) 做代码导航，或读根目录 [`../../README.md`](../../README.md) 做环境搭建。
