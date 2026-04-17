# 功能设计文档（Plan）

本目录存放 **实现前** 的设计说明。

1. **新功能先写 Plan，再写代码**  
   新建 `plan/plan-<功能简述>.md`（英文小写 + 连字符），评审通过后再开发。

2. **Plan 建议包含**  
   背景与目标、范围与非目标、数据约定、API 与权限、与现有模块的衔接、分期、待确认问题。

3. **实现完成后**  
   可在同一文件末尾追加「实现记录」小节，或在根目录 `README.md` 中链接回本文档。

## 已有 Plan

| 文件 | 说明 |
|------|------|
| [plan-go-gin-sqlite-lightweight.md](./plan-go-gin-sqlite-lightweight.md) | Gin + SQLite 轻量实现的设计与分期（`go-dev`） |
