# 第 7 章：清单模块（`apps/manifest`）

本章说明：**`manifest.yaml` 是什么、系统如何把它变成前端能画的树、调试接口怎么用**。目录：`apps/manifest/`。

---

## 1. manifest 是干什么的？

在现场 TPOPS 安装过程中，脚本会把**当前安装进度**写进一个（或多个）**YAML 文本文件**，通常叫 **`manifest.yaml`**，里面有大步骤、子步骤、状态、时间等。

本系统**不负责生成**这个文件，只负责：

- **通过 SSH 读文件内容**（在部署任务的 runner 里轮询）；或  
- 你在调试时 **把 YAML 文本 POST 给解析接口**，立刻看解析结果。

---

## 2. 解析入口：`parser.py`

核心函数例如 **`manifest_to_tree`**：把 YAML 字符串变成 **嵌套 JSON 结构**（含 `roots`、`summary` 等），供前端画「流水线」与总进度。

还会做一些**汇总**：例如父层状态由子任务推导（具体逻辑以代码为准）。

---

## 3. 调试 API：`POST /api/manifest/parse/`

用途：**不执行任务**，只在浏览器或 Postman 里粘贴一段 manifest YAML，看解析树是否正确。

请求方式（二选一）：

- JSON body：`{ "content": "yaml 文本..." }`  
- 或 multipart 上传字段 **`file`**

需要 **已登录 JWT**。

实现文件：**`apps/manifest/views.py`**。

---

## 4. 与部署任务的关系

- **运行时**：`runner` 周期性 `remote_cat_file` → `yaml.safe_load` → `manifest_to_tree` → WebSocket 推送。  
- **任务结束后**：前端可调用 **`/api/deployment/tasks/<id>/manifest_snapshot/`** 再拉一次（避免 WS 已断开看不到最终树）。

---

上一章：[安装包模块](06-packages-module.md)  
下一章：[日志与 WebSocket 模块 logs](08-logs-websockets-module.md)
