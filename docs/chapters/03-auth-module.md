# 第 3 章：认证模块（`apps/tpops_auth`）

本章说明：**谁可以登录、登录后发什么令牌、如何改密码**。对应代码目录：`apps/tpops_auth/`。

---

## 1. 这个模块解决什么问题？

Web API 没有传统「服务器 Session 里存登录态」的默认用法（也可以做，但本项目选用 **JWT**）：

- 用户用**用户名 + 密码**换两张令牌：  
  - **access**：短命，用来调 API。  
  - **refresh**：长命，用来换新 access。  
- 之后每次请求 API，浏览器在 HTTP 头里带上 access；服务端**不查 Session 表**，只**验证 JWT 签名**即可知道你是谁。

**小白类比**：access 像「当天有效的门禁卡」，refresh 像「去前台换新卡的长效凭证」。

---

## 2. URL 一览（`apps/tpops_auth/urls.py`）

| 方法 | 路径 | 谁能访问 | 做什么 |
|------|------|----------|--------|
| POST | `/api/auth/register/` | 任何人 | 注册新用户 |
| POST | `/api/auth/login/` | 任何人 | 校验密码，返回 JWT + 用户信息 |
| POST | `/api/auth/token/refresh/` | 任何人（需合法 refresh） | 换新的 access |
| GET | `/api/auth/profile/` | 已登录 | 返回当前用户资料 |
| PUT/PATCH | `/api/auth/update-profile/` | 已登录 | 改昵称等资料 |
| POST | `/api/auth/change-password/` | 已登录 | 校验旧密码后设新密码 |

实现文件：**`views.py`**；校验与数据结构在 **`serializers.py`**；用户表在 **`models.py`**（扩展 `AbstractUser`）。

---

## 3. 登录成功返回什么？

典型 JSON 结构（字段名以实际接口为准）：

- `token.access`：后面所有 API 放在 `Authorization: Bearer ...`。  
- `token.refresh`：存在前端内存或安全存储，用于刷新。  
- `user`：用户 id、用户名、`role` 等展示用字段。

---

## 4. 与 WebSocket 的关系

浏览器连 **`ws://.../ws/deploy/任务id/?token=...`** 时，**不能**像 HTTP 那样随便加 Header，所以把 **同一个 access token** 放在查询参数里。服务端用 SimpleJWT 解析 token 得到 `user_id`，再查库确认「这个用户能否看这个任务」（见 [第 8 章](08-logs-websockets-module.md)）。

---

## 5. 安全小贴士（小白版）

- **不要**把 access 发到聊天、截图里；它能在过期前代表你调用 API。  
- 生产环境务必配置 **`DJANGO_SECRET_KEY`**；JWT 签名依赖它。  
- 默认 `DEBUG=True` 时不要对公网暴露管理口。

---

上一章：[HTTP 路由与请求](02-http-routing-and-requests.md)  
下一章：[主机模块 hosts](04-hosts-module.md)
