# 第 4 章：主机模块（`apps/hosts`）

本章说明：**如何在系统里登记一台远程 Linux、密码怎么存、怎么测 SSH、怎么把远程已有配置读回网页**。目录：`apps/hosts/`。

---

## 1. 一台「主机」在本系统里代表什么？

**不是**在系统里装一个操作系统，而是：**一条数据库记录**，告诉后台「以后执行任务时，用这些参数去 SSH 连哪台机」。

你需要提供：

- **连得上**：IP/域名、端口、用户名、密码或私钥。  
- **找得到脚本**：**部署根目录**（`docker_service_root`），即远程 **`appctl.sh` 所在文件夹**，例如 `/data/docker-service`。

---

## 2. 凭证为什么「看不见」？

字段 **`credential`** 存的是 **加密后的密文**（Fernet，见 `crypto.py`）。  
列表接口里不会返回密码，只返回 **`has_credential`**（有没有配置过）。

**小白提示**：这和「网站存密码要加密」是同一类道理；这里加密的是 **SSH 密码或私钥全文**。

---

## 3. API 行为（`HostViewSet`，路由在 `api/hosts/`）

| 操作 | HTTP | 说明 |
|------|------|------|
| 列表 | GET `/api/hosts/` | 普通用户通常只能看到自己创建的 + 历史上未绑定属主的主机；管理员看全部 |
| 新建 | POST `/api/hosts/` | Body 里可写 `password` 或 `private_key`（写一次）；服务端加密后写入 `credential` |
| 查看/改/删 | GET/PUT/PATCH/DELETE `/api/hosts/<id>/` | 标准 REST |

### 自定义：测 SSH

**POST** `/api/hosts/<id>/test_connection/`  

- 解密凭证 → 用 Paramiko 连一下 → 返回 `{ ok: true/false, message: "..." }`。  
- **不会**把密码打在返回里。

### 自定义：读远程 `user_edit`

**GET** `/api/hosts/<id>/fetch_user_edit/`  

- SSH 上去，用与部署任务**相同规则**探测 `user_edit_file.conf` 路径（`ssh_client.resolve_user_edit_conf_path`）。  
- 读出全文 → 用 `parse_user_edit_block` 校验格式 → 返回 `{ content, remote_path }`。  
- 若文件太大（>512KB）或格式不合法，会返回错误说明。

实现集中在 **`views.py`**；连接细节在 **`ssh_client.py`**。

---

## 4. 与部署任务的关系

创建 **DeploymentTask** 时要选一个 **`host`** 作为 **节点 1**。后台线程只会对这个 `host` 做 SSH。

节点 2/3 若填写，仅用于界面与 manifest 多文件路径；**不会**自动改 `user_edit` 里的 IP。

---

## 5. 小白常见疑问

**Q：改了主机密码怎么办？**  
A：在主机管理里编辑该主机，重新填密码保存（会重新加密）。

**Q：部署根写错了会怎样？**  
A：任务执行时 `cd` 错目录，`appctl.sh` 找不到会失败；manifest 路径也会错。应写成与现场一致的 `appctl.sh` 目录。

---

上一章：[认证模块](03-auth-module.md)  
下一章：[部署模块 deployment](05-deployment-module.md)
