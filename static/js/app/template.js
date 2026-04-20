window.TPOPSApp = window.TPOPSApp || {};
window.TPOPSApp.template = String.raw`
    <!-- 登录（TPOPS Platform 科技风参考） -->
    <div v-if="!token" class="login-wrap">
      <div class="login-bg-pattern" aria-hidden="true"></div>
      <div class="login-bg-dots" aria-hidden="true"></div>
      <div class="login-bg-glow login-bg-glow--tl" aria-hidden="true"></div>
      <div class="login-bg-glow login-bg-glow--br" aria-hidden="true"></div>
      <div class="login-panel">
        <div class="login-brand">
          <div class="login-brand-icon" aria-hidden="true">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h1 class="login-brand-title">TPOPS <span class="login-brand-sub">Platform</span></h1>
          <p class="login-brand-tagline">Technical Platform Operations</p>
        </div>
        <div class="login-form-switcher">
          <div class="login-switch-slider" :class="{ 'is-register': loginPanelTab === 'register' }"></div>
          <button type="button" class="login-switch-item" :class="{ active: loginPanelTab === 'login' }" @click="loginPanelTab = 'login'">身份验证</button>
          <button type="button" class="login-switch-item" :class="{ active: loginPanelTab === 'register' }" @click="loginPanelTab = 'register'">申请访问</button>
        </div>
        <div class="login-forms-clip">
          <div class="login-forms-track" :class="{ 'is-register': loginPanelTab === 'register' }">
            <div class="login-form-col">
              <el-form :model="loginForm" label-position="top" class="login-el-form" @keyup.enter="doLogin">
                <el-form-item label="用户名" class="login-form-item-plain">
                  <el-input v-model="loginForm.username" size="large" autocomplete="username" placeholder="管理员账号 / ID" class="login-el-input"></el-input>
                </el-form-item>
                <el-form-item label="密码" class="login-form-item-plain">
                  <el-input v-model="loginForm.password" size="large" type="password" show-password autocomplete="current-password" placeholder="访问令牌 / 密码" class="login-el-input"></el-input>
                </el-form-item>
                <div class="login-row-meta">
                  <label class="login-remember"><input type="checkbox" /> 记住该设备</label>
                  <span class="login-forgot-pseudo">忘记凭证?</span>
                </div>
                <el-button type="primary" class="login-submit-btn" size="large" :loading="loading" @click="doLogin">验证并进入系统</el-button>
              </el-form>
            </div>
            <div class="login-form-col">
              <el-form :model="regForm" label-position="top" class="login-el-form">
                <el-form-item label="用户名" class="login-form-item-plain">
                  <el-input v-model="regForm.username" size="large" autocomplete="username" placeholder="登录用户名" class="login-el-input"></el-input>
                </el-form-item>
                <el-form-item label="邮箱" class="login-form-item-plain">
                  <el-input v-model="regForm.email" size="large" autocomplete="email" placeholder="工作邮箱" class="login-el-input"></el-input>
                </el-form-item>
                <el-form-item label="密码" class="login-form-item-plain">
                  <el-input v-model="regForm.password" size="large" type="password" show-password autocomplete="new-password" placeholder="密码" class="login-el-input"></el-input>
                </el-form-item>
                <el-form-item label="确认密码" class="login-form-item-plain">
                  <el-input v-model="regForm.password_confirm" size="large" type="password" show-password autocomplete="new-password" placeholder="再次输入密码" class="login-el-input"></el-input>
                </el-form-item>
                <el-form-item label="角色" class="login-form-item-plain">
                  <el-select v-model="regForm.role" size="large" placeholder="选择角色" style="width:100%">
                    <el-option label="只读" value="viewer"></el-option>
                    <el-option label="操作员" value="operator"></el-option>
                    <el-option label="管理员" value="admin"></el-option>
                  </el-select>
                </el-form-item>
                <el-button type="primary" class="login-submit-btn" size="large" :loading="loading" @click="doRegister">提交访问申请</el-button>
              </el-form>
            </div>
          </div>
        </div>
        <div class="login-footer-meta">TPOPS 白屏化部署 · JWT 鉴权 · 请妥善保管账号</div>
      </div>
    </div>

    <!-- 主布局：侧栏 + 顶栏 + 内容区（参考 OAT/OCP：可折叠导航 + 居中内容区） -->
    <el-container v-else class="layout-root">
      <el-aside :width="sidebarCollapsed ? '64px' : '240px'" :class="['ob-aside', { 'ob-aside--collapsed': sidebarCollapsed }]">
        <div class="ob-logo">
          <span class="ob-logo-mark">T</span>
          <span class="ob-logo-text">TPOPS</span>
        </div>
        <el-menu
          class="ob-menu"
          :class="{ 'ob-menu--collapse': sidebarCollapsed }"
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          :collapse-transition="false"
          background-color="transparent"
          text-color="#64748b"
          active-text-color="#0062ff"
          @select="onMenuSelect"
        >
          <div v-if="!sidebarCollapsed" class="ob-nav-group-label">资源监控</div>
          <el-menu-item index="overview">
            <span>控制台概览</span>
          </el-menu-item>
          <div v-if="!sidebarCollapsed" class="ob-nav-group-label">部署与任务</div>
          <el-menu-item index="deploy">
            <span>部署任务</span>
          </el-menu-item>
          <el-menu-item index="packages">
            <span>安装包管理</span>
          </el-menu-item>
          <div v-if="!sidebarCollapsed" class="ob-nav-group-label">配置</div>
          <el-menu-item index="hosts">
            <span>主机管理</span>
          </el-menu-item>
        </el-menu>
        <div v-if="token && !sidebarCollapsed" class="ob-sidebar-user">
          <div class="ob-sidebar-user-avatar" v-text="(user.username || '?').charAt(0).toUpperCase()"></div>
          <div class="ob-sidebar-user-meta">
            <div class="ob-sidebar-user-name" v-text="user.username || '用户'"></div>
            <div class="ob-sidebar-user-sub">运维控制台</div>
          </div>
        </div>
        <div class="ob-aside-toggle">
          <el-button size="small" @click="sidebarCollapsed = !sidebarCollapsed">{{ sidebarCollapsed ? '展开' : '收起' }}</el-button>
        </div>
      </el-aside>
      <el-container direction="vertical">
        <el-header class="ob-header">
          <div class="ob-breadcrumb">
            控制台 / <strong v-text="breadcrumbTitle"></strong>
          </div>
          <div class="ob-header-actions">
            <el-tag effect="plain" type="info" v-text="user.username || '-'"></el-tag>
            <el-button type="danger" link @click="logout">退出登录</el-button>
          </div>
        </el-header>
        <el-main ref="obMainEl" class="ob-main">
          <div class="ob-main-inner">
          <!-- 概览 -->
          <template v-if="activeMenu === 'overview'">
            <h2 class="ob-page-title">概览工作台</h2>
            <p class="ob-page-sub">资源与任务总览；部署形态与 appctl 流程说明见下方卡片。</p>
            <el-row :gutter="16" style="margin-bottom:20px;">
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" v-text="hosts.length"></div>
                  <div class="lab">已配置主机</div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" v-text="tasks.length"></div>
                  <div class="lab">历史任务数</div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" style="color:#e6a23c;" v-text="runningCount"></div>
                  <div class="lab">进行中</div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" style="color:#52c41a;" v-text="successCount"></div>
                  <div class="lab">成功</div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" style="color:#f56c6c;" v-text="failedCount"></div>
                  <div class="lab">失败</div>
                </el-card>
              </el-col>
              <el-col :xs="24" :sm="8" :md="4">
                <el-card shadow="hover" class="stat-card ob-card-elevated">
                  <div class="num" style="color:#909399;" v-text="taskSuccessRatePercent + '%'"></div>
                  <div class="lab">成功率</div>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-bottom:20px;">
              <el-col :xs="24" :lg="14">
                <el-card shadow="never" class="ob-card-elevated">
                  <template #header><span style="font-weight:600">平台说明</span></template>
                  <p style="margin:0 0 10px;line-height:1.7;color:#606266;">
                    本控制台用于 <strong>TPOPS / GaussDB 容器化部署</strong>：在「主机管理」登记 SSH 可达的执行机（部署根目录需含 <code>appctl.sh</code>），在「部署任务」按向导填写
                    <code>user_edit_file.conf</code> 后，系统会<strong>自动检测</strong>远程
                    <code>config/gaussdb/user_edit_file.conf</code> 或 <code>config/user_edit_file.conf</code> 是否存在并<strong>覆盖写入</strong>，再执行所选 <code>appctl.sh</code> 操作。
                  </p>
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="Manifest">安装/升级时在执行机 <code>config/gaussdb/</code> 下轮询：<strong>单节点</strong>仅 <code>manifest.yaml</code>；<strong>三节点</strong>为 <code>manifest.yaml</code> + <code>manifest_&lt;node2_ip&gt;.yaml</code> + <code>manifest_&lt;node3_ip&gt;.yaml</code>（IP 来自 user_edit），合并展示流水线</el-descriptions-item>
                    <el-descriptions-item label="配置文件"><code>user_edit</code> 以页面填写为准原样下发；所选节点仅用于 SSH 连接与执行 appctl</el-descriptions-item>
                    <el-descriptions-item label="注意">docker-service 不建议并发执行多个 appctl；同一主机请避免并行任务。</el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
              <el-col :xs="24" :lg="10">
                <el-card shadow="never" class="ob-card-elevated">
                  <template #header><span style="font-weight:600">快速开始</span></template>
                  <el-steps direction="vertical" :active="4" finish-status="success">
                    <el-step title="登记主机" description="SSH、部署根目录 /data/docker-service"></el-step>
                    <el-step title="选择部署形态" description="单节点或三节点形态"></el-step>
                    <el-step title="选择节点" description="节点 1 必填；三节点时 2/3 可选"></el-step>
                    <el-step title="配置与下发" description="编辑 user_edit 并选择 appctl 操作"></el-step>
                  </el-steps>
                </el-card>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :xs="24" :lg="14">
                <el-card shadow="never" class="ob-card-elevated">
                  <template #header><span style="font-weight:600">已纳管主机</span></template>
                  <div v-if="hosts.length" class="ob-table-scroll">
                  <el-table ref="dashboardHostsTableRef" key="dashboard-hosts-table" :data="hosts" stripe border size="small" table-layout="auto" max-height="40vh" class="host-table ob-table-compact" row-key="id">
                    <el-table-column key="dashboard-hosts-name" prop="name" label="名称" width="120" show-overflow-tooltip></el-table-column>
                    <el-table-column key="dashboard-hosts-conn" label="连接" min-width="150">
                      <template #default="{ row }">
                        <span class="host-conn-inline">
                          <span class="host-endpoint mono">{{ row.hostname }}:{{ row.port }}</span>
                          <span class="host-inline-meta">{{ row.username }} · {{ authMethodLabel(row.auth_method) }}</span>
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column key="dashboard-hosts-root" prop="docker_service_root" label="部署根目录" min-width="160" show-overflow-tooltip></el-table-column>
                    <el-table-column key="dashboard-hosts-credential" label="凭证" width="80" align="center">
                      <template #default="{ row }">
                        <el-tag :type="row.has_credential ? 'success' : 'warning'" size="small" effect="plain">{{ row.has_credential ? '已配' : '未配' }}</el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                  </div>
                  <el-empty v-else description="暂无主机，请前往「主机管理」点击纳管主机"></el-empty>
                </el-card>
              </el-col>
              <el-col :xs="24" :lg="10">
                <el-card shadow="never" class="ob-card-elevated">
                  <template #header><span style="font-weight:600">最近任务</span></template>
                  <div v-if="lastTasks.length" class="ob-table-scroll">
                  <el-table ref="dashboardLastTasksTableRef" key="dashboard-last-tasks-table" :data="lastTasks" stripe border size="small" table-layout="auto" max-height="40vh" class="overview-task-table ob-table-compact" row-key="id">
                    <el-table-column key="dashboard-last-tasks-id" prop="id" label="ID" width="56"></el-table-column>
                    <el-table-column key="dashboard-last-tasks-host" prop="host_name" label="节点1" min-width="90" show-overflow-tooltip></el-table-column>
                    <el-table-column key="dashboard-last-tasks-mode" label="形态" width="88" align="center">
                      <template #default="{ row }">
                        <el-tag size="small" :type="row.deploy_mode === 'triple' ? 'warning' : 'info'" effect="plain">{{ row.deploy_mode === 'triple' ? '三节点' : '单节点' }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column key="dashboard-last-tasks-action" label="操作" min-width="100" show-overflow-tooltip>
                      <template #default="{ row }"><span v-text="deployActionLabel(row.action)"></span></template>
                    </el-table-column>
                    <el-table-column key="dashboard-last-tasks-outcome" label="结果" width="88" align="center">
                      <template #default="{ row }">
                        <el-tag size="small" :type="deployOutcomeTagType(row.status)" effect="dark">{{ row.outcome_label || deployStatusLabel(row.status) }}</el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                  </div>
                  <el-empty v-else description="暂无任务记录"></el-empty>
                </el-card>
              </el-col>
            </el-row>
          </template>

          <!-- 主机管理：列表 / 纳管表单 -->
          <template v-else-if="activeMenu === 'hosts'">
            <template v-if="hostSubView === 'list'">
            <h2 class="ob-page-title">主机管理</h2>
            <p class="ob-page-sub">纳管执行机与部署根目录，供部署任务 SSH 下发使用。</p>
            <div class="host-hero">
              <div>
                <h2>主机纳管</h2>
                <p>本页展示已纳管主机列表。点击<strong>纳管主机</strong>填写 SSH 与部署根目录；仅本人创建及未绑定属主的主机对本账号可见。</p>
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;">
                <el-button :loading="loading" @click="refreshHostsPage">
                  <span style="margin-right:4px">↻</span> 刷新列表
                </el-button>
                <el-button type="success" @click="openHostEnroll">纳管主机</el-button>
              </div>
            </div>
            <div class="host-stat-row">
              <div class="host-stat-pill"><div class="n" v-text="hosts.length"></div><div class="l">已纳管主机</div></div>
              <div class="host-stat-pill"><div class="n" v-text="hostsWithCredential"></div><div class="l">已配置 SSH 凭证</div></div>
              <div class="host-stat-pill"><div class="n" v-text="hostsKeyAuth"></div><div class="l">密钥登录</div></div>
            </div>
            <el-card shadow="never" class="host-card-accent">
              <template #header>
                <div class="ob-card-table-head">
                  <span>主机列表</span>
                  <span class="ob-card-table-head-meta">共 {{ hosts.length }} 台</span>
                </div>
              </template>
                  <div class="ob-table-scroll">
                  <el-table
                    ref="hostManageTableRef"
                    key="host-manage-table"
                    :data="hosts"
                    stripe
                    border
                    table-layout="auto"
                    style="width:100%"
                    class="host-table ob-table-wide"
                    row-key="id"
                    empty-text="暂无主机，请点击「纳管主机」添加"
                    :default-sort="{ prop: 'created_at', order: 'descending' }"
                  >
                    <el-table-column key="host-manage-id" prop="id" label="ID" width="64" sortable></el-table-column>
                    <el-table-column key="host-manage-name" prop="name" label="显示名称" min-width="140" show-overflow-tooltip sortable></el-table-column>
                    <el-table-column key="host-manage-ssh" label="SSH 连接" min-width="220">
                      <template #default="{ row }">
                        <span class="host-conn-inline">
                          <span class="host-endpoint mono">{{ row.hostname }}:{{ row.port }}</span>
                          <span class="host-inline-meta">用户 {{ row.username }}</span>
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column key="host-manage-auth" label="认证" width="96" align="center">
                      <template #default="{ row }">
                        <el-tag size="small" :type="row.auth_method === 'key' ? 'primary' : 'info'" effect="light">{{ authMethodLabel(row.auth_method) }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column key="host-manage-credential" label="凭证" width="96" align="center">
                      <template #default="{ row }">
                        <el-tooltip :content="row.has_credential ? '已保存加密凭证，可测连通性' : '未保存密码/私钥，请先编辑填写'" placement="top">
                          <el-tag size="small" :type="row.has_credential ? 'success' : 'warning'" effect="plain">{{ row.has_credential ? '已保存' : '未配置' }}</el-tag>
                        </el-tooltip>
                      </template>
                    </el-table-column>
                    <el-table-column key="host-manage-root" prop="docker_service_root" label="部署根目录" min-width="220" show-overflow-tooltip></el-table-column>
                    <el-table-column key="host-manage-owner" label="属主" width="100" show-overflow-tooltip>
                      <template #default="{ row }">
                        <span>{{ row.owner_username || '—' }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column key="host-manage-created-at" prop="created_at" label="创建时间" width="168" sortable>
                      <template #default="{ row }">
                        <span class="mono" style="font-size:12px;color:#606266">{{ formatHostTime(row.created_at) }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column key="host-manage-actions" label="操作" min-width="180">
                      <template #default="{ row }">
                        <el-button link type="primary" @click="editHost(row)">编辑</el-button>
                        <el-button link type="success" @click="testHost(row)" :loading="row._testing">连通性</el-button>
                        <el-button link type="danger" @click="deleteHost(row)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  </div>
            </el-card>
            </template>

            <template v-else-if="hostSubView === 'form'">
            <h2 class="ob-page-title">纳管主机</h2>
            <p class="ob-page-sub">填写 SSH 与远程 <code>appctl.sh</code> 所在目录；凭证加密存储。</p>
            <div class="deploy-page-toolbar">
              <div class="left">
                <el-button @click="backToHostList">← 返回主机列表</el-button>
                <h2 class="ob-page-title">{{ hostForm.id ? '编辑主机' : '纳管主机' }}</h2>
              </div>
            </div>
            <el-card shadow="never" class="host-card-accent host-form-card-narrow">
              <template #header><span>{{ hostForm.id ? '修改配置' : '新增主机' }}</span></template>
              <el-form :model="hostForm" label-width="112px" size="default">
                <el-form-item label="显示名称">
                  <el-input v-model="hostForm.name" placeholder="如：生产节点-1"></el-input>
                </el-form-item>
                <el-form-item label="IP / 域名">
                  <el-input v-model="hostForm.hostname" placeholder="SSH 地址"></el-input>
                </el-form-item>
                <el-form-item label="SSH 端口">
                  <el-input-number v-model="hostForm.port" :min="1" :max="65535" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item label="SSH 用户">
                  <el-input v-model="hostForm.username" placeholder="如 root"></el-input>
                </el-form-item>
                <el-form-item label="认证方式">
                  <el-radio-group v-model="hostForm.auth_method">
                    <el-radio label="password">密码</el-radio>
                    <el-radio label="key">私钥</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="hostForm.auth_method==='password'" label="密码">
                  <el-input v-model="hostForm.password" type="password" show-password placeholder="保存时写入"></el-input>
                </el-form-item>
                <el-form-item v-else label="私钥 PEM">
                  <el-input v-model="hostForm.private_key" type="textarea" :rows="5" placeholder="-----BEGIN ... KEY-----"></el-input>
                </el-form-item>
                <el-form-item label="部署根目录">
                  <el-input v-model="hostForm.docker_service_root" placeholder="/data/docker-service"></el-input>
                  <div class="hint">与远程 <code>appctl.sh</code> 所在目录一致（如 <code>/data/docker-service</code>）。执行：<code>cd &lt;目录&gt; && sh appctl.sh ...</code>。进度文件：<code>&lt;目录&gt;/config/gaussdb/manifest.yaml</code>。</div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveHost" :loading="loading">保存</el-button>
                  <el-button v-if="hostForm.id" @click="backToHostList">取消并返回列表</el-button>
                  <el-button v-else @click="resetHostForm">清空表单</el-button>
                </el-form-item>
              </el-form>
            </el-card>
            </template>
          </template>

          <!-- 安装包管理：版本列表 / 新建 / 包文件 -->
          <template v-else-if="activeMenu === 'packages'">
            <h2 class="ob-page-title">安装包管理</h2>
            <p class="ob-page-sub">维护 TPOPS 安装介质版本；下发时在<strong>节点 1</strong>写入 <code>&lt;部署根&gt;/pkgs/</code>（扁平文件名），不传入 <code>appctl.sh</code>。</p>
            <template v-if="packageSubView === 'list'">
              <div class="pkg-toolbar">
                <el-button type="primary" @click="openPackageReleaseForm">新建版本</el-button>
                <el-button :loading="loading" @click="fetchPackageReleases">刷新</el-button>
                <span class="pkg-meta">共 {{ packageReleases.length }} 个版本</span>
              </div>
              <el-card shadow="never" class="deploy-task-card">
                <template #header><span style="font-weight:600">版本列表</span></template>
                <div class="pkg-table-scroll">
                  <el-table
                    key="package-release-table"
                    :data="packageReleases"
                    stripe
                    border
                    table-layout="auto"
                    class="pkg-release-table ob-table-compact"
                    style="width:100%"
                    row-key="id"
                    empty-text="暂无版本，请点击「新建版本」"
                  >
                    <el-table-column label="ID" width="80" align="center">
                      <template #default="{ row }"><span class="mono" v-text="row.id"></span></template>
                    </el-table-column>
                    <el-table-column label="版本名称" min-width="160" show-overflow-tooltip>
                      <template #default="{ row }"><span v-text="row.name || '—'"></span></template>
                    </el-table-column>
                    <el-table-column label="包数量" width="96" align="center">
                      <template #default="{ row }"><span v-text="row.artifact_count != null ? row.artifact_count : 0"></span></template>
                    </el-table-column>
                    <el-table-column label="创建人" width="112" show-overflow-tooltip>
                      <template #default="{ row }"><span v-text="row.created_by_username || '—'"></span></template>
                    </el-table-column>
                    <el-table-column label="创建时间" width="178">
                      <template #default="{ row }"><span class="mono" style="font-size:12px;color:#606266">{{ formatHostTime(row.created_at) }}</span></template>
                    </el-table-column>
                    <el-table-column label="操作" width="180" fixed="right" align="center">
                      <template #default="{ row }">
                        <el-button link type="primary" @click="openPackageDetail(row)">管理包</el-button>
                        <el-button link type="danger" @click="deletePackageRelease(row)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-card>
            </template>
            <template v-else-if="packageSubView === 'form'">
              <div class="pkg-toolbar">
                <el-button @click="backPackageList">← 返回列表</el-button>
                <span class="pkg-meta">新建安装包版本</span>
              </div>
              <el-card shadow="never" class="deploy-task-card">
                <el-form label-width="100px" style="max-width:560px;">
                  <el-form-item label="版本名称"><el-input v-model="packageReleaseForm.name" placeholder="如 TPOPS-1.0"></el-input></el-form-item>
                  <el-form-item label="说明"><el-input v-model="packageReleaseForm.description" type="textarea" :rows="3"></el-input></el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="loading" @click="savePackageRelease">保存</el-button>
                    <el-button @click="backPackageList">取消</el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </template>
            <template v-else-if="packageSubView === 'detail' && packageDetailRelease">
              <div class="pkg-toolbar">
                <el-button @click="backPackageList">← 返回列表</el-button>
                <span style="font-weight:600">版本：{{ packageDetailRelease.name }}</span>
                <el-button type="primary" :loading="loading" @click="fetchPackageArtifacts(packageDetailRelease.id)">刷新包列表</el-button>
              </div>
              <el-card shadow="never" class="deploy-task-card" style="margin-bottom:12px;">
                <template #header>
                  <div class="ob-card-table-head">
                    <span>上传安装包</span>
                    <span class="hint ob-card-table-head-meta" style="max-width:min(100%,420px);text-align:right">不限制大小与后缀；同名将覆盖该版本下已有记录</span>
                  </div>
                </template>
                <el-upload
                  :http-request="submitPackageArtifactUpload"
                  :disabled="packageArtifactUploading"
                  :show-file-list="false"
                >
                  <el-button type="primary" :loading="packageArtifactUploading">选择文件上传</el-button>
                </el-upload>
                <div v-if="packageArtifactUploading || packageUploadProgress > 0" style="margin-top:12px;max-width:480px;">
                  <el-progress :percentage="packageUploadProgress" :status="packageUploadProgress >= 100 ? 'success' : undefined" />
                  <div class="hint" style="margin-top:6px;">上传中请勿关闭页面；大文件请耐心等待。</div>
                </div>
              </el-card>
              <el-card shadow="never" class="deploy-task-card">
                <template #header><span style="font-weight:600">包列表</span></template>
                <div class="pkg-table-scroll">
                  <el-table
                    key="package-artifact-table"
                    :data="packageArtifacts"
                    stripe
                    border
                    table-layout="auto"
                    class="pkg-artifact-table ob-table-wide"
                    style="width:100%"
                    row-key="id"
                    empty-text="暂无文件，请上传"
                  >
                    <el-table-column label="ID" width="80" align="center">
                      <template #default="{ row }"><span class="mono" v-text="row.id"></span></template>
                    </el-table-column>
                    <el-table-column label="远端文件名" min-width="160" show-overflow-tooltip>
                      <template #default="{ row }"><span v-text="row.remote_basename || '—'"></span></template>
                    </el-table-column>
                    <el-table-column label="原始名" min-width="120" show-overflow-tooltip>
                      <template #default="{ row }"><span v-text="row.original_name || '—'"></span></template>
                    </el-table-column>
                    <el-table-column label="大小(字节)" width="120" align="right">
                      <template #default="{ row }"><span v-text="row.size != null ? row.size : 0"></span></template>
                    </el-table-column>
                    <el-table-column label="SHA256" min-width="120" show-overflow-tooltip>
                      <template #default="{ row }"><span class="mono" style="font-size:11px">{{ (row.sha256 || '').slice(0, 16) }}…</span></template>
                    </el-table-column>
                    <el-table-column label="操作" width="88" fixed="right" align="center">
                      <template #default="{ row }">
                        <el-button link type="danger" @click="deletePackageArtifact(row)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-card>
            </template>
          </template>

          <!-- 部署任务：列表 / 新建向导 / 执行监控 -->
          <template v-else-if="activeMenu === 'deploy'">
            <!-- ① 部署记录列表（与新建入口同页） -->
            <template v-if="deploySubView === 'list'">
            <div class="installer-page-intro">
              <div>
                <h2 class="ob-page-title">部署任务</h2>
                <p class="ob-page-sub">查看历史记录与结果；新建部署进入引导，查看详情进入实时监控（从监控返回列表不会断开连接）。</p>
              </div>
              <div class="installer-page-actions">
                <el-button :loading="loading" @click="refreshTasksOnly">刷新列表</el-button>
                <el-button type="primary" @click="openDeployWizard">新建部署</el-button>
              </div>
            </div>

            <el-card shadow="never" class="deploy-task-card installer-data-card">
              <template #header>
                <div class="ob-card-table-head">
                  <span>部署记录</span>
                  <span class="ob-card-table-head-meta">共 {{ tasks.length }} 条</span>
                </div>
              </template>
              <div class="ob-table-scroll">
              <el-table
                ref="deployRecordTableRef"
                key="deploy-record-table"
                :data="tasks"
                stripe
                border
                table-layout="auto"
                class="deploy-table ob-table-deploy"
                style="width:100%"
                row-key="id"
                empty-text="暂无记录，请点击右上角「新建部署」"
                :default-sort="{ prop: 'created_at', order: 'descending' }"
                :row-class-name="deployTaskRowClass"
              >
                <el-table-column key="deploy-record-id" prop="id" label="任务 ID" width="88" sortable></el-table-column>
                <el-table-column key="deploy-record-created-at" prop="created_at" label="触发时间" width="176" sortable>
                  <template #default="{ row }">
                    <span class="mono" style="font-size:12px;color:#606266">{{ formatHostTime(row.created_at) }}</span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-host" prop="host_name" label="执行机" min-width="120" show-overflow-tooltip></el-table-column>
                <el-table-column key="deploy-record-node23" label="节点 2/3" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-if="row.deploy_mode !== 'triple'" class="hint">—</span>
                    <span v-else v-text="[row.host_node2_name, row.host_node3_name].filter(Boolean).join(' / ') || '同节点1'"></span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-mode" prop="deploy_mode" label="形态" width="88" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.deploy_mode === 'triple' ? 'warning' : 'info'" effect="plain">{{ row.deploy_mode === 'triple' ? '三节点' : '单节点' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-action" label="任务类型" min-width="130" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-text="deployActionLabel(row.action)"></span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-target" prop="target" label="目标" min-width="100" show-overflow-tooltip></el-table-column>
                <el-table-column key="deploy-record-package" label="安装包" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-if="row.skip_package_sync" class="hint">已跳过</span>
                    <span v-else-if="row.package_release_name" v-text="row.package_release_name + '（' + ((row.package_artifact_ids || []).length) + ' 个）'"></span>
                    <span v-else class="hint">—</span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-outcome" label="结果" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="deployOutcomeTagType(row.status)" effect="dark">{{ row.outcome_label || deployStatusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-status" prop="status" label="状态" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="deployStatusTagType(row.status)" effect="plain">{{ deployStatusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-exit-code" prop="exit_code" label="退出码" width="88" align="center">
                  <template #default="{ row }">
                    <span v-if="row.exit_code != null" class="mono" v-text="row.exit_code"></span>
                    <span v-else class="hint">—</span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-owner" label="属主" width="96" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-text="row.created_by_username || '—'"></span>
                  </template>
                </el-table-column>
                <el-table-column key="deploy-record-actions" label="操作" min-width="110">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="attachTask(row)">查看详情</el-button>
                  </template>
                </el-table-column>
              </el-table>
              </div>
            </el-card>
            <div class="installer-tip-banner">
              <strong>提示：</strong>部署前请在「主机管理」登记 SSH 可达的执行机（部署根目录含 <code>appctl.sh</code>）；同一主机避免并行多个 appctl 任务。
            </div>
            </template>

            <!-- ② 新建部署（独立全页引导） -->
            <template v-else-if="deploySubView === 'wizard'">
            <div class="deploy-wizard-page">
            <div class="deploy-page-toolbar installer-toolbar">
              <div class="left">
                <el-button @click="backToDeployList">← 返回部署列表</el-button>
                <h2 class="ob-page-title">新建部署</h2>
              </div>
            </div>
            <el-card shadow="never" class="deploy-task-card installer-wizard-card" style="margin-bottom:16px;">
              <template #header>
                <div class="ob-card-table-head">
                  <span>集群部署引导</span>
                  <span class="ob-card-table-head-meta">横条切换步骤 · 完成后点「下发执行」进入流水线与日志</span>
                </div>
              </template>
              <div class="deploy-wizard-shell">
                <div class="deploy-installer-steps" role="tablist" aria-label="部署步骤">
                  <template v-for="(s, idx) in deployWizardSteps" :key="s.key">
                    <button
                      type="button"
                      class="deploy-installer-step-btn"
                      :class="{ 'is-active': deployStep === idx, 'is-done': deployStep > idx }"
                      @click="goDeployWizardStep(idx)"
                    >
                      <span class="deploy-installer-step-num">{{ deployStep > idx ? '✓' : (idx + 1) }}</span>
                      <span class="deploy-installer-step-label" v-text="s.title"></span>
                    </button>
                    <div v-if="idx < deployWizardSteps.length - 1" class="deploy-installer-connector" aria-hidden="true"></div>
                  </template>
                </div>
                <div class="deploy-wizard-body">
                    <div v-show="deployStep === 0">
                      <h2 class="installer-step-heading">选择部署形态</h2>
                      <p class="installer-step-lead">单节点仅一台执行机；三节点时 manifest 与登记节点按平台约定展示，<code>user_edit</code> 内 IP 需自行填写，平台不覆盖。</p>
                      <div class="deploy-mode-cards">
                        <div
                          class="deploy-mode-card"
                          :class="{ 'is-selected': deployForm.deploy_mode === 'single' }"
                          role="button"
                          tabindex="0"
                          @click="setDeployModeAndAdvance('single')"
                          @keyup.enter="setDeployModeAndAdvance('single')"
                        >
                          <svg v-if="deployForm.deploy_mode === 'single'" class="deploy-mode-check" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                          <h3>单节点</h3>
                          <p>一台执行机完成 SSH、写入 <code>user_edit_file.conf</code> 与 <code>appctl.sh</code>，适合标准单机或联调环境。</p>
                          <span class="deploy-mode-badge">常用</span>
                        </div>
                        <div
                          class="deploy-mode-card"
                          :class="{ 'is-selected': deployForm.deploy_mode === 'triple' }"
                          role="button"
                          tabindex="0"
                          @click="setDeployModeAndAdvance('triple')"
                          @keyup.enter="setDeployModeAndAdvance('triple')"
                        >
                          <svg v-if="deployForm.deploy_mode === 'triple'" class="deploy-mode-check" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                          <h3>三节点</h3>
                          <p>节点 2/3 可选登记；安装阶段可合并展示多节点 manifest 流水线，与单节点流程一致由执行机发起。</p>
                        </div>
                      </div>
                      <div class="hint" style="margin-top:4px;">
                        <strong>执行机</strong>始终为节点 1；三节点时节点 2/3 仅作记录，IP 以 <code>user_edit</code> 为准。
                      </div>
                      <div class="deploy-installer-footer">
                        <el-button type="primary" @click="goDeployWizardStep(1)">下一步：选择节点</el-button>
                      </div>
                    </div>

                    <div v-show="deployStep === 1">
                      <h2 class="installer-step-heading">选择节点</h2>
                      <p class="installer-step-lead">节点 1 为必填执行机；三节点形态下节点 2、3 可不选（默认与节点 1 同机）。</p>
                      <el-form label-width="112px" label-position="left" style="max-width:640px;">
                        <el-form-item label="节点 1（执行）">
                          <el-select v-model="deployForm.host" placeholder="选择已纳管主机" filterable style="width:100%">
                            <el-option v-for="h in hosts" :key="h.id" :disabled="isHostDisabledForNode1(h.id)" :label="h.name + ' — ' + h.hostname + ':' + h.port + ' (' + h.username + ')'" :value="h.id"></el-option>
                          </el-select>
                        </el-form-item>
                        <template v-if="deployForm.deploy_mode === 'triple'">
                          <el-form-item label="节点 2（可选）">
                            <el-select v-model="deployForm.host_node2" clearable placeholder="不选则与节点 1 同机" filterable style="width:100%">
                              <el-option v-for="h in hosts" :key="h.id" :disabled="isHostDisabledTriple(h.id, 2)" :label="h.name + ' — ' + h.hostname + ':' + h.port" :value="h.id"></el-option>
                            </el-select>
                          </el-form-item>
                          <el-form-item label="节点 3（可选）">
                            <el-select v-model="deployForm.host_node3" clearable placeholder="不选则与节点 1 同机" filterable style="width:100%">
                              <el-option v-for="h in hosts" :key="h.id" :disabled="isHostDisabledTriple(h.id, 3)" :label="h.name + ' — ' + h.hostname + ':' + h.port" :value="h.id"></el-option>
                            </el-select>
                          </el-form-item>
                        </template>
                      </el-form>
                      <div class="deploy-installer-footer">
                        <el-button @click="goDeployWizardStep(0)">上一步</el-button>
                        <el-button type="primary" @click="goDeployWizardStepHostsToPackages">下一步：选择安装包</el-button>
                      </div>
                    </div>

                    <div v-show="deployStep === 2">
                      <h2 class="installer-step-heading">选择安装包</h2>
                      <p class="installer-step-lead">安装 / 升级且同步介质时，需选择 TPOPS 主包（必选）及可选 om-agent / OS 内核包；包名须符合约定（CPU/OS 由文件名自身体现，无需单独选择）。</p>
                      <el-alert v-if="deployPackageStepError" type="warning" :closable="false" show-icon style="margin-bottom:12px;max-width:720px;">
                        <template #title><span style="white-space:pre-wrap;" v-text="deployPackageStepError"></span></template>
                      </el-alert>
                      <el-form label-width="112px" label-position="left" style="max-width:720px;">
                        <el-form-item label="安装包">
                          <div style="width:100%;">
                            <el-checkbox v-model="deployForm.skip_package_sync" @change="onSkipPackageChange">跳过同步（远端 <code>pkgs/</code> 已有介质）</el-checkbox>
                            <div v-if="!deployForm.skip_package_sync" style="margin-top:10px;">
                              <el-select v-model="deployForm.package_release" clearable filterable placeholder="选择安装包版本" style="width:100%;max-width:480px;margin-bottom:10px;" @change="onDeployPackageReleaseChange">
                                <el-option v-for="r in packageReleases" :key="r.id" :label="r.name + '（' + (r.artifact_count || 0) + ' 个包）'" :value="r.id"></el-option>
                              </el-select>
                              <div v-if="deployForm.package_release" style="max-height:220px;overflow:auto;border:1px solid #ebeef5;border-radius:8px;padding:10px 12px;background:#fafbfc;">
                                <div v-if="!deployWizardArtifacts.length" class="hint">该版本下暂无包，请先到「安装包管理」上传。</div>
                                <el-checkbox-group v-else v-model="deployForm.package_artifact_ids" style="display:flex;flex-direction:column;gap:8px;">
                                  <el-checkbox v-for="a in deployWizardArtifacts" :key="a.id" :label="a.id">
                                    <span v-text="a.remote_basename"></span>
                                    <span class="hint" style="margin-left:8px;">{{ a.size }} B</span>
                                  </el-checkbox>
                                </el-checkbox-group>
                              </div>
                              <div v-else class="hint" style="margin-top:6px;">请先选择版本；不选版本则不下发安装包。</div>
                            </div>
                          </div>
                        </el-form-item>
                      </el-form>
                      <div class="deploy-installer-footer">
                        <el-button @click="goDeployWizardStep(1)">上一步</el-button>
                        <el-button type="primary" @click="goDeployWizardStepPackagesToConfig">下一步：操作与配置</el-button>
                      </div>
                    </div>

                    <div v-show="deployStep === 3">
                      <h2 class="installer-step-heading">操作与配置</h2>
                      <p class="installer-step-lead">选择 appctl 操作并编辑 <code>user_edit</code>；内容将原样写入远程配置文件。</p>
                      <el-alert type="info" :closable="false" show-icon style="margin-bottom:14px;">
                        <template #title>选择 appctl 操作后点击「下发执行」；<code>user_edit</code> 将<strong>原样</strong>写入远程配置文件。</template>
                      </el-alert>
                      <el-form label-width="100px" style="max-width:100%;">
                        <el-form-item label="操作类型">
                          <el-radio-group v-model="deployForm.action" class="deploy-action-rg">
                            <el-radio-button label="precheck_install">安装前置检查 — <code>precheck install</code>（需填目标组件）</el-radio-button>
                            <el-radio-button label="precheck_upgrade">升级前置检查 — <code>precheck upgrade</code>（需填目标组件）</el-radio-button>
                            <el-radio-button label="install">安装 — <code>install</code></el-radio-button>
                            <el-radio-button label="upgrade">升级 — <code>upgrade</code></el-radio-button>
                            <el-radio-button label="uninstall_all">卸载全部 — <code>uninstall_all</code>（高危；单/三节点均自动应答 y）</el-radio-button>
                          </el-radio-group>
                        </el-form-item>
                        <el-form-item label="目标参数">
                          <el-input v-model="deployForm.target" placeholder="precheck 类必填组件名（如 gaussdb）；install / upgrade / uninstall_all 按现场可留空"></el-input>
                        </el-form-item>
                        <el-form-item label="user_edit">
                          <el-input v-model="deployForm.user_edit_content" type="textarea" :rows="12" placeholder="[user_edit] ..." class="mono-ta"></el-input>
                          <div style="margin-top:8px;">
                            <el-button size="small" @click="fillUserEditTemplate">恢复默认模板</el-button>
                          </div>
                        </el-form-item>
                      </el-form>
                      <div class="deploy-installer-footer">
                        <el-button @click="goDeployWizardStep(2)">上一步</el-button>
                        <el-button type="primary" size="large" @click="startDeploy" :loading="loading">下发执行</el-button>
                      </div>
                    </div>
                </div>
              </div>
            </el-card>
            <div class="installer-tip-banner">
              <strong>提示：</strong><code>precheck</code> 类操作需填写目标组件；安装 / 升级同步介质时请在「选择安装包」步骤勾选主包与可选内核包，并核对 CPU/OS。
            </div>
            </div>
            </template>

            <!-- ③ 下发后：安装流水线 + 日志（独立页） -->
            <template v-else-if="deploySubView === 'monitor'">
            <div class="deploy-monitor-stack">
            <div class="deploy-page-toolbar installer-toolbar">
              <div class="left">
                <el-button @click="backToDeployList">← 返回部署列表</el-button>
                <el-button type="primary" plain @click="openDeployWizard">新建部署</el-button>
                <h2 class="ob-page-title" v-if="currentTaskId">任务 #{{ currentTaskId }} · 流水线与日志</h2>
                <h2 class="ob-page-title" v-else>流水线与日志</h2>
              </div>
            </div>

            <el-alert
              v-if="currentTaskId && deployStatusStripVisible"
              class="deploy-status-strip"
              :title="deployStatusStripTitle"
              :type="deployStatusStripType"
              :closable="false"
              show-icon
            >
              <template v-if="currentTaskSnapshot && (currentTaskSnapshot.error_message || '').trim()">
                <div style="margin-top:8px;font-size:12px;word-break:break-all;opacity:.95;">
                  <strong>失败原因：</strong><span v-text="currentTaskSnapshot.error_message"></span>
                </div>
              </template>
            </el-alert>

            <el-card shadow="never" class="deploy-split deploy-task-card deploy-console-card">
              <template #header>
                <div class="deploy-console-head">
                  <div>
                    <div class="t">部署执行 · 流水线与输出</div>
                    <div class="hint" style="margin-top:4px;max-width:720px;">
                      大层串行、层内并发；点击步骤或子步骤切换右侧文件日志。
                      <template v-if="showTripleNodeStrip">三节点时子步骤按 IP 分组展示。</template>
                    </div>
                  </div>
                  <div class="meta">
                    <el-tag size="small" @click="openLogTail('precheck')" style="cursor:pointer">precheck.log</el-tag>
                    <el-tag size="small" @click="openLogTail('install')" style="cursor:pointer">install.log</el-tag>
                    <el-tag size="small" type="danger" @click="openLogTail('uninstall')" style="cursor:pointer">uninstall.log</el-tag>
                  </div>
                </div>
              </template>
              <div class="phase-strip deploy-console-phase">
                <span class="deploy-console-phase-lab">阶段</span>
                <span class="deploy-console-phase-val" v-text="phaseBanner"></span>
              </div>
              <div class="deploy-console-body">
                <div class="deploy-console-left">
                  <div class="deploy-console-left-scroll">
                  <div v-if="showManifestTree && manifestSummary && manifestSummary.services_total != null" class="manifest-dash">
                    <div class="manifest-dash-top">
                      <div>
                        <div style="font-size:13px;color:#606266;margin-bottom:6px;">安装总进度（按服务项）</div>
                        <div class="manifest-dash-pct">{{ manifestProgressPercent }}<span>%</span></div>
                      </div>
                      <div class="manifest-dash-meta">
                        <div>已用时间 <strong>{{ deployElapsedHuman }}</strong></div>
                        <div v-if="manifestEstimatedHuman">预估合计 <strong>{{ manifestEstimatedHuman }}</strong></div>
                        <div>层 <strong>{{ manifestSummary.levels_done || 0 }}/{{ manifestSummary.levels_total || 0 }}</strong></div>
                        <div>服务 <strong>{{ manifestSummary.services_done || 0 }}/{{ manifestSummary.services_total || 0 }}</strong></div>
                      </div>
                    </div>
                    <el-progress class="manifest-dash-bar" :percentage="manifestProgressPercent" :stroke-width="10"></el-progress>
                    <div v-if="manifestCurrentStepLine" class="manifest-current-box">
                      <div class="lab">当前进行</div>
                      <div class="val" v-text="manifestCurrentStepLine"></div>
                    </div>
                    <div v-if="showTripleNodeStrip && tripleNodeProgressList.length" class="triple-node-strip">
                      <div v-for="pn in tripleNodeProgressList" :key="pn.index" class="triple-node-card">
                        <div class="head" v-text="pn.label"></div>
                        <div class="role" v-text="tripleNodeRoleText(pn.role) + (pn.path ? ' · ' + shortPath(pn.path) : '')"></div>
                        <div style="font-size:12px;color:#606266;">层 {{ pn.levels_done }}/{{ pn.levels_total }} · 服务 {{ pn.services_done }}/{{ pn.services_total }}</div>
                        <el-progress :percentage="pn.progress_percent" :stroke-width="8"></el-progress>
                      </div>
                    </div>
                    <div class="hint" style="margin-top:10px;word-break:break-all;" v-text="'manifest: ' + ((manifestPaths || []).join(' · ') || '—')"></div>
                  </div>
                  <el-card v-else-if="manifestSummary && manifestSummary.services_total != null" shadow="hover" style="margin-bottom:12px;">
                    <template #header><span style="font-weight:600">汇总</span></template>
                    <div style="font-size:12px;color:#606266;">
                      层 <span v-text="manifestSummary.levels_done || 0"></span>/<span v-text="manifestSummary.levels_total || 8"></span>
                      · 服务 <span v-text="manifestSummary.services_done || 0"></span>/<span v-text="manifestSummary.services_total || 0"></span>
                    </div>
                    <div class="hint" style="margin-top:6px;word-break:break-all;" v-text="(manifestPaths || []).join(' · ')"></div>
                  </el-card>
                  <div class="pipeline-scroll">
                    <template v-if="displayPipelineRows.length && showManifestTree">
                      <div
                        v-for="row in displayPipelineRows"
                        :key="row.key"
                        class="pipeline-step"
                        :class="{ sel: activePipelineKey === row.key }"
                      >
                        <div class="pipeline-head" @click="onPipelineStepClick(row)">
                          <span v-text="row.title"></span>
                          <span class="pipeline-lv-pill" :class="pipelineLvPillClass(rowEffectiveLevelStatus(row))" v-text="rowEffectiveLevelStatus(row)"></span>
                          <span class="parallel-badge" v-text="'（' + row.parallel_note + '）'"></span>
                        </div>
                        <div class="pipeline-sub">
                          <div v-if="row.key === '__precheck__'" class="hint" style="margin:4px 0 0 4px;">在 <strong>patch</strong> 层状态为 <strong>running</strong> 或 <strong>done</strong> 之前，本步骤保持 <strong>running</strong>；不区分节点。</div>
                          <template v-if="tripleGroupedSubs(row).length">
                            <div
                              v-for="grp in tripleGroupedSubs(row)"
                              :key="row.key + '-' + grp.node_label"
                              class="pipeline-node-block"
                            >
                              <div class="pipeline-node-label" v-text="grp.node_label + '：'"></div>
                              <div
                                v-for="sub in grp.subs"
                                :key="sub.id + '-' + grp.node_label"
                                class="pipeline-subline"
                                @click.stop="onPipelineSubClick(sub, row)"
                              >
                                <span>·</span>
                                <span v-text="subLabelWithoutStatus(sub)"></span>
                                <span v-if="subFinishExecuteTime(sub)" class="hint" style="margin-left:6px;">用时 <span class="mono" v-text="subFinishExecuteTime(sub)"></span></span>
                                <span class="sub-st-pill" :class="subStPillClass(sub._nodeStatus || sub.status)" v-text="sub._nodeStatus || sub.status"></span>
                              </div>
                            </div>
                          </template>
                          <template v-else>
                          <div
                            v-for="sub in row.children"
                            :key="sub.id"
                            class="pipeline-subline"
                            @click.stop="onPipelineSubClick(sub, row)"
                          >
                            <span>·</span>
                            <span v-text="sub.label"></span>
                            <span v-if="subFinishExecuteTime(sub)" class="hint" style="margin-left:6px;">用时 <span class="mono" v-text="subFinishExecuteTime(sub)"></span></span>
                            <span class="sub-st-pill" :class="subStPillClass(sub.status)" v-text="sub.status"></span>
                            <div v-if="sub.node_details && sub.node_details.length && !tripleDeployForManifest" class="node-status-dots">
                              <span
                                v-for="nd in sub.node_details"
                                :key="nd.node_index + '-' + nd.node_label"
                                class="node-dot"
                                :class="subStatusDotClass(nd.status)"
                                v-text="nd.node_label + ':' + nd.status"
                              ></span>
                            </div>
                          </div>
                          </template>
                        </div>
                      </div>
                    </template>
                    <el-empty
                      v-else
                      :description="showManifestTree ? '安装/升级期间，在执行机轮询 manifest：单节点为 manifest.yaml；三节点另读 manifest_<node2_ip>.yaml、manifest_<node3_ip>.yaml（与 user_edit 一致）。有有效 YAML 后即展示流水线。' : '当前为前置检查，无 manifest 流水线'"
                    />
                  </div>
                  </div>
                </div>
                <div class="deploy-console-gutter" aria-hidden="true"></div>
                <div class="deploy-console-right">
                  <div class="deploy-log-stack">
                    <div class="deploy-log-seg">
                      <div class="deploy-log-seg-title">
                        <span>appctl 标准输出</span>
                      </div>
                      <div ref="logAppctlEl" class="log-box log-deploy-main" v-text="logText"></div>
                    </div>
                    <div class="deploy-log-seg deploy-log-seg--sub">
                      <div class="deploy-log-seg-title">
                        <span>文件日志</span>
                        <span class="hint mono" v-if="selectedLogHint" v-text="selectedLogHint"></span>
                        <span class="hint" v-else v-text="logTailLabel"></span>
                      </div>
                      <div ref="logFileEl" class="log-box log-deploy-sub" v-text="logTailText"></div>
                    </div>
                  </div>
                  <div class="hint deploy-log-footer-hint" style="font-size:12px;line-height:1.55;">
                    <span v-if="liveTaskFinishedHint" v-text="liveTaskFinishedHint"></span>
                    <span v-else>实时流；任务结束后可点顶部 <code>precheck.log</code> / <code>install.log</code> 查看文件。</span>
                  </div>
                </div>
              </div>
            </el-card>
            </div>
            </template>
          </template>
          </div>
        </el-main>
      </el-container>
    </el-container>

`;
