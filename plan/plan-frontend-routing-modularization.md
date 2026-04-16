# 前端路由与模块化拆分计划

## 背景与目标

当前前端实现集中在 `templates/index.html`：

- 页面结构、样式、状态、接口调用、WebSocket 逻辑全部写在一个文件里；
- 只有 `activeMenu` / `hostSubView` / `deploySubView` / `packageSubView` 这类本地状态切换，没有显式前端路由；
- 随着主机管理、安装包管理、部署向导、部署监控等功能持续增加，单文件维护成本和回归风险都在增大。

本次目标是在**不引入额外 npm / bundler 构建链**的前提下，先完成一轮适合当前 Django 架构的工程化拆分：

1. 将内联样式拆到独立 CSS 文件；
2. 将内联脚本拆到独立 JS 文件；
3. 为前端引入可感知、可回退、可直达的 **hash 路由**；
4. 保留现有接口、WebSocket 协议与交互行为，避免功能回归；
5. 为后续继续拆组件/接入构建工具打基础。

## 范围

### 本次纳入

- `templates/index.html` 收敛为页面壳层；
- 新增 `static/css/app.css` 承载前端样式；
- 新增 `static/js/app/` 下的前端脚本文件；
- 引入 hash 路由并打通以下页面状态：
  - `#/overview`
  - `#/hosts`
  - `#/hosts/form`
  - `#/packages`
  - `#/packages/form`
  - `#/packages/detail/<id>`
  - `#/deploy`
  - `#/deploy/wizard`
  - `#/deploy/monitor/<id>`
- 保持主机、安装包、部署任务、部署监控的现有行为一致；
- 保持登录、注册、JWT、本地存储与 WebSocket 行为一致。

### 本次不纳入

- 不引入 `vite` / `webpack` / `npm` 构建流程；
- 不改动后端 API 路径与返回结构；
- 不重写为 Vue SFC；
- 不一次性细分到大量子组件文件；
- 不改动 `apps/deployment/runner.py`、WebSocket 后端协议等后端逻辑。

## 现状约束

1. `tpops_deployment/views.py` 使用**原始文本**返回 `templates/index.html`，避免 Django 模板引擎解析 Vue 的 `{{ }}`。
2. `tpops_deployment/settings.py` 已配置：
   - `STATIC_URL = "/static/"`
   - `STATICFILES_DIRS = [BASE_DIR / "static"]`
3. 当前前端依赖来自 CDN：
   - Vue 3
   - Element Plus
   - Axios
4. 仓库约定要求避免使用会导致旧浏览器直接白屏的过新语法。

## 设计方案

## 1. 页面壳层

将 `templates/index.html` 收敛为：

- 基础 `<head>` 元信息；
- Element Plus CDN 样式；
- 项目自有样式 `./static/css/app.css`；
- `#app` 挂载点；
- Vue / Element Plus / Axios CDN 脚本；
- 项目自有脚本：
  - `./static/js/app/template.js`
  - `./static/js/app/router.js`
  - `./static/js/app/main.js`

这样可以保留当前“原始 HTML 返回”的模式，同时避免继续把核心实现堆在一个文件里。

## 2. 模板拆分

将现有 `#app` 内的 Vue 模板迁移到 `static/js/app/template.js`，由脚本导出根模板字符串。

这样做的原因：

- 不引入构建链时，仍然可以使用 Vue 全量运行时编译模板；
- 模板代码不再和 HTML 壳层、样式、状态逻辑耦合在一起；
- 便于后续继续拆成按页面分块的模板文件。

## 3. 路由方案

采用 **hash 路由**，避免新增后端 URL 路由规则：

- Django 仍只负责返回 `/` 的 SPA 壳层；
- 前端通过 `location.hash` 驱动页面状态；
- 支持浏览器前进/后退；
- 支持直接打开特定页面，例如部署监控页。

### 路由到状态的映射

| hash 路径 | 前端状态 |
|-----------|-----------|
| `#/overview` | `activeMenu = "overview"` |
| `#/hosts` | `activeMenu = "hosts"` + `hostSubView = "list"` |
| `#/hosts/form` | `activeMenu = "hosts"` + `hostSubView = "form"` |
| `#/packages` | `activeMenu = "packages"` + `packageSubView = "list"` |
| `#/packages/form` | `activeMenu = "packages"` + `packageSubView = "form"` |
| `#/packages/detail/<id>` | `activeMenu = "packages"` + `packageSubView = "detail"` + 加载指定版本详情 |
| `#/deploy` | `activeMenu = "deploy"` + `deploySubView = "list"` |
| `#/deploy/wizard` | `activeMenu = "deploy"` + `deploySubView = "wizard"` |
| `#/deploy/monitor/<id>` | `activeMenu = "deploy"` + `deploySubView = "monitor"` + 打开指定任务 |

## 4. 脚本结构

### `static/js/app/template.js`

- 保存根模板字符串；
- 不放业务逻辑。

### `static/js/app/router.js`

- 路由规范化；
- hash 解析；
- `navigateTo(path)`；
- 路由路径与页面状态之间的映射辅助函数。

### `static/js/app/main.js`

- 保留原有 `createApp({ setup() { ... } })` 主逻辑；
- 将原有本地页面切换动作改造成“状态 + 路由同步”；
- 保留现有接口调用、WebSocket 连接、表格重布局逻辑；
- 在 `onMounted` 时监听 `hashchange`，并根据当前 hash 还原界面状态。

## 数据与状态约定

本次不改变以下核心状态结构，只改变其驱动方式：

- `activeMenu`
- `hostSubView`
- `packageSubView`
- `deploySubView`
- `currentTaskId`
- `packageDetailRelease`

原则：

1. **路由负责页面定位**；
2. **现有状态继续负责页面内部业务行为**；
3. 页面跳转入口统一走 `navigateTo(...)`，避免再出现“只有本地状态、没有可追踪路由”的情况。

## 与现有模块衔接

### Django

- `tpops_deployment/views.py` 保持 `spa_index` 模式不变；
- `tpops_deployment/urls.py` 保持 `/` 指向 SPA；
- 静态资源直接通过 `STATIC_URL` 提供。

### WebSocket

- 部署监控仍使用：
  - `ws/deploy/<task_id>/?token=<JWT>`
  - `ws/deploy/<task_id>/log/?token=<JWT>&...`
- 仅把“打开某个任务监控页”的入口改为可由 hash 路由恢复。

### 鉴权

- 保持 `localStorage` 中的 `access`、`refresh`、`user`；
- 登录成功后默认跳到 `#/overview`；
- 未登录时无论 hash 是什么，仍先显示登录页。

## 实施步骤

### 步骤 1：计划与壳层准备

- 新增本计划文件；
- 准备 `static/` 前端目录结构。

### 步骤 2：样式拆分

- 将 `templates/index.html` 中的 `<style>` 全量迁移到 `static/css/app.css`；
- HTML 通过相对路径引用。

### 步骤 3：模板拆分

- 将 `#app` 中的 Vue 模板迁移到 `static/js/app/template.js`；
- `templates/index.html` 仅保留挂载点。

### 步骤 4：脚本拆分与路由接入

- 将现有内联脚本迁移到 `static/js/app/main.js`；
- 新增 `static/js/app/router.js`；
- 把菜单切换、子页切换、详情打开动作接入 hash 路由。

### 步骤 5：联调与回归

- 验证登录、主机管理、安装包管理、部署列表、部署向导、部署监控；
- 验证浏览器前进/后退；
- 验证部署监控 hash 直达；
- 执行 Django 基础检查。

## 风险与应对

### 1. 模板迁移后语法解析差异

风险：从 DOM 内联模板迁移到 JS 模板字符串后，可能因为转义或标签闭合导致运行异常。  
应对：保持模板内容尽量原样迁移，并延续前面对 Element 标签显式闭合的修复。

### 2. 路由与原状态双写导致不一致

风险：既有本地状态又有 hash 路由，可能出现页面状态和 URL 不同步。  
应对：将“页面跳转入口”统一改为 `navigateTo()`，由路由负责驱动页面定位。

### 3. 监控页 WebSocket 生命周期回归

风险：任务监控页切换后可能导致日志缓冲丢失或重复重连。  
应对：保留当前 `openSocket(..., { preserveLogAndManifest })` 语义，路由层只负责页面定位。

### 4. 静态资源路径问题

风险：静态文件引用错误导致页面空白。  
应对：统一使用相对路径 `./static/...`，并在 Django 检查后进行页面级验证。

## 验收标准

满足以下条件视为本次拆分完成：

1. `templates/index.html` 不再包含大段内联样式与业务脚本；
2. 前端具备明确 hash 路由；
3. 菜单与子页面可通过 URL 直接定位；
4. 主机、安装包、部署任务、部署监控等现有功能可正常使用；
5. `python3 manage.py check` 通过；
6. 代码结构明显优于当前单文件方案，为后续继续拆组件保留空间。

## 实现记录

### 实际落地文件

- `templates/index.html`
  - 收敛为 SPA 壳层，仅保留挂载点、CDN 资源和项目静态资源引用。
- `static/css/app.css`
  - 承载原 `index.html` 中的前端样式。
- `static/js/app/template.js`
  - 承载原 `#app` 内的 Vue 根模板。
- `static/js/app/router.js`
  - 提供 hash 路由的解析与构建逻辑。
- `static/js/app/page-state.js`
  - 承载页面级路由状态、面包屑、表格重布局与 URL 同步。
- `static/js/app/auth.js`
  - 承载登录、注册、token/refresh、本地存储与 axios 鉴权接入。
- `static/js/app/hosts.js`
  - 承载主机管理列表/表单相关逻辑。
- `static/js/app/packages.js`
  - 承载安装包版本、文件列表与上传相关逻辑。
- `static/js/app/deploy.js`
  - 承载部署列表、部署向导、部署监控、日志与 WebSocket 逻辑。
- `static/js/app/main.js`
  - 收敛为前端应用装配入口，负责拼装各业务模块。

### 与计划的差异

- 本次已完成“壳层拆分 + 样式拆分 + 模板拆分 + 脚本拆分 + hash 路由接入”，并继续完成二阶段的业务模块拆分。
- 当前仍保持无 npm / bundler 的静态资源方案；模块拆分基于浏览器顺序加载的全局工厂模式，而非 ES module / 打包产物。
- 依旧保持无 npm / bundler 的静态资源方案，符合本轮计划目标。

### 已完成的路由行为

- `#/overview`
- `#/hosts`
- `#/hosts/form`
- `#/packages`
- `#/packages/form`
- `#/packages/detail/<id>`
- `#/deploy`
- `#/deploy/wizard`
- `#/deploy/monitor/<id>`

### 验证结果

- 已执行：

```bash
DJANGO_SECRET_KEY=cursor-temp-secret python3 manage.py check
```

- 结果：通过，无系统检查错误。
