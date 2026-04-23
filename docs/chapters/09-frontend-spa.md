# 第 9 章：前端单页（Vue SPA）

本章说明：**网页文件在哪、Vue 如何组织、它怎么调后端 API**。目录：`templates/`、`static/js/app/`、`static/css/app.css`。

---

## 1. 为什么只有一个 `index.html`？

传统多页网站：每个功能一个 `.html` 文件。  
本项目的界面是 **单页应用（SPA）**：浏览器只加载一次 **`templates/index.html`**，之后页面切换由 **JavaScript 在浏览器里改 DOM**，不再整页刷新。

**小白提示**：你看到的「主机管理 / 部署任务」等，其实是**同一张网页里不同区块的显示与隐藏**（配合 Vue 路由或状态）。

---

## 2. 页面壳与静态脚本

| 文件 | 作用 |
|------|------|
| `templates/index.html` | HTML 壳：挂载点 `<div id="app">`、引入 Vue / Element Plus **CDN**、引入 `/static/js/app/main.js` 等 |
| `static/js/app/main.js` | **入口**：创建 Vue 应用、注册路由或全局状态、配置 **axios**（API 基址、请求拦截器里自动带 JWT） |
| `static/js/app/template.js` | 大量界面 HTML 模板字符串（与 Element Plus 组件混写） |
| `static/js/app/deploy.js` | 部署向导、任务列表、WebSocket 连接 manifest 与日志展示逻辑 |
| `static/js/app/packages.js` | 安装包版本与上传进度 |
| 其它 `static/js/app/*.js` | 登录、主机等子模块（以 `main.js` 引用为准） |
| `static/css/app.css` | 全局样式、控制台布局、登录页样式等 |

---

## 3. 前端如何调用 API？

典型流程：

1. 用户登录成功 → 前端把 **`access` token** 存到内存（或 `localStorage`，视实现而定）。  
2. **axios 拦截器**：每次发请求前在 Header 加 `Authorization: Bearer ...`。  
3. 收到 **401** 时，可用 refresh 换新 access（具体逻辑以代码为准）。

**小白类比**：axios 像「邮递员」，拦截器像「每封信自动盖公章」。

---

## 4. 缓存问题：为什么 JS/CSS 后面有 `?v=数字`？

`tpops_deployment/views.py` 里的 **`spa_index`** 会扫描 `static/js/app/*.js` 与 `app.css` 的修改时间，给 URL 加上 **`?v=时间戳`**。  
这样你更新后端代码后，浏览器不容易继续用旧 JS，减少「明明改了代码却像没生效」的困惑。

---

## 5. 与 WebSocket 的配合

部署监控页会 **`new WebSocket(...)`**，URL 里带 **`token=`**。  
收到消息后根据 `msg.type` 分支：拼日志文本、更新 manifest 树、更新任务状态条等。

---

## 6. 小白改界面从哪里下手？

1. 先找到对应界面文案在 **`template.js`** 还是某模块里。  
2. 逻辑在 **`deploy.js` / `packages.js` / `hosts` 相关 js** 等。  
3. 样式在 **`app.css`**。  
4. 改完刷新浏览器；若仍像旧版，**强刷**或清缓存（因为有 `?v=` 一般还好）。

---

上一章：[WebSocket 模块](08-logs-websockets-module.md)  
下一章：[工程壳与目录地图](10-project-layout-and-files.md)
