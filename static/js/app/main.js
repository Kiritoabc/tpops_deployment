(function (window) {
    const { createApp, ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } = Vue;
    const api = axios.create({ baseURL: '/api' });
    const router = window.TPOPSRouter;
    const appTemplate = window.TPOPSApp && window.TPOPSApp.template;
    createApp({
      template: appTemplate,
      setup() {
        const token = ref(localStorage.getItem('access') || '');
        const refresh = ref(localStorage.getItem('refresh') || '');
        const user = ref(JSON.parse(localStorage.getItem('user') || '{}'));
        const loading = ref(false);
        const sidebarCollapsed = ref(false);
        const activeMenu = ref('overview');
        const hosts = ref([]);
        const tasks = ref([]);
        const showRegister = ref(false);
        const loginForm = reactive({ username: '', password: '' });
        const regForm = reactive({ username: '', email: '', password: '', password_confirm: '', role: 'viewer' });
        const hostForm = reactive({ id: null, name: '', hostname: '', port: 22, username: 'root', auth_method: 'password', password: '', private_key: '', docker_service_root: '/data/docker-service' });

        const USER_EDIT_TEMPLATE = `[user_edit]
ssh_port = 22
gauss_path = /data/gaussdb
node1_ip = 192.168.0.1
node2_ip = 192.168.0.2
node3_ip = 192.168.0.3
influxdb_install_ip1 = 192.168.0.1
influxdb_install_ip2 = 192.168.0.2
sftp_install_ip1 = 192.168.0.1
sftp_install_ip2 = 192.168.0.2
main_path = /data/cloud
node1_ip2 = 192.168.0.1
node2_ip2 = 192.168.0.2
node3_ip2 = 192.168.0.3
log_path = /data/cloud/logs
sftp_path = /data/sftphome
influx_path = /data/influxdb
docker_path = /data/docker
use_cgroup = no
ntp_server =
cpu_limit =
mem_limit =
es_enable = no
es_path = /data/elasticsearch
ipv6_enable = no
use_import_ca = no
`;

        const deployForm = reactive({
          deploy_mode: 'single',
          host: null,
          host_node2: null,
          host_node3: null,
          user_edit_content: USER_EDIT_TEMPLATE,
          action: 'precheck_install',
          target: 'gaussdb',
          package_release: null,
          package_artifact_ids: [],
          skip_package_sync: false,
        });
        const packageReleases = ref([]);
        const packageSubView = ref('list');
        const packageReleaseForm = reactive({ name: '', description: '' });
        const packageDetailRelease = ref(null);
        const packageArtifacts = ref([]);
        const deployWizardArtifacts = ref([]);

        const packageUploadAction = computed(() => `${location.origin}/api/packages/artifacts/`);
        const packageUploadHeaders = computed(() => (token.value ? { Authorization: 'Bearer ' + token.value } : {}));
        const routeSyncMuted = ref(false);

        const normalizeListResponse = (data) => {
          if (Array.isArray(data)) return data;
          if (data && Array.isArray(data.results)) return data.results;
          if (data && Array.isArray(data.data)) return data.data;
          return [];
        };

        const fetchPackageReleases = async () => {
          try {
            const { data } = await api.get('/packages/releases/');
            packageReleases.value = normalizeListResponse(data);
          } catch { packageReleases.value = []; }
        };

        const openPackageReleaseForm = () => {
          packageReleaseForm.name = '';
          packageReleaseForm.description = '';
          packageSubView.value = 'form';
        };

        const backPackageList = () => {
          packageSubView.value = 'list';
          packageDetailRelease.value = null;
          packageArtifacts.value = [];
          fetchPackageReleases().catch(() => {});
        };

        const savePackageRelease = async () => {
          if (!(packageReleaseForm.name || '').trim()) return ElementPlus.ElMessage.warning('请填写版本名称');
          loading.value = true;
          try {
            await api.post('/packages/releases/', {
              name: packageReleaseForm.name.trim(),
              description: (packageReleaseForm.description || '').trim(),
            });
            ElementPlus.ElMessage.success('已创建');
            backPackageList();
          } catch (e) {
            ElementPlus.ElMessage.error(
              e.response && e.response.data ? JSON.stringify(e.response.data) : '保存失败'
            );
          } finally { loading.value = false; }
        };

        const openPackageDetail = async (row) => {
          packageDetailRelease.value = row;
          packageSubView.value = 'detail';
          await fetchPackageArtifacts(row.id);
        };

        const fetchPackageArtifacts = async (releaseId) => {
          if (!releaseId) return;
          loading.value = true;
          try {
            const { data } = await api.get('/packages/artifacts/', { params: { release: releaseId } });
            packageArtifacts.value = normalizeListResponse(data);
          } catch { packageArtifacts.value = []; }
          finally { loading.value = false; }
        };

        const deletePackageRelease = async (row) => {
          try {
            await ElementPlus.ElMessageBox.confirm('确定删除版本「' + row.name + '」及其下所有安装包？', '确认', { type: 'warning' });
          } catch { return; }
          loading.value = true;
          try {
            await api.delete('/packages/releases/' + row.id + '/');
            ElementPlus.ElMessage.success('已删除');
            fetchPackageReleases().catch(() => {});
            if (packageDetailRelease.value && packageDetailRelease.value.id === row.id) backPackageList();
          } catch { ElementPlus.ElMessage.error('删除失败'); }
          finally { loading.value = false; }
        };

        const deletePackageArtifact = async (row) => {
          try {
            await ElementPlus.ElMessageBox.confirm('确定删除文件「' + row.remote_basename + '」？', '确认', { type: 'warning' });
          } catch { return; }
          loading.value = true;
          try {
            await api.delete('/packages/artifacts/' + row.id + '/');
            ElementPlus.ElMessage.success('已删除');
            if (packageDetailRelease.value) await fetchPackageArtifacts(packageDetailRelease.value.id);
            fetchPackageReleases().catch(() => {});
          } catch { ElementPlus.ElMessage.error('删除失败'); }
          finally { loading.value = false; }
        };

        const onPackageUploadSuccess = () => {
          ElementPlus.ElMessage.success('上传成功');
          if (packageDetailRelease.value) fetchPackageArtifacts(packageDetailRelease.value.id);
          fetchPackageReleases().catch(() => {});
        };
        const onPackageUploadError = () => ElementPlus.ElMessage.error('上传失败');

        const loadDeployWizardArtifacts = async (releaseId) => {
          deployWizardArtifacts.value = [];
          if (!releaseId) return;
          try {
            const { data } = await api.get('/packages/artifacts/', { params: { release: releaseId } });
            deployWizardArtifacts.value = normalizeListResponse(data);
          } catch { deployWizardArtifacts.value = []; }
        };

        const onDeployPackageReleaseChange = () => {
          deployForm.package_artifact_ids = [];
          loadDeployWizardArtifacts(deployForm.package_release);
        };

        const onSkipPackageChange = () => {
          if (deployForm.skip_package_sync) {
            deployForm.package_release = null;
            deployForm.package_artifact_ids = [];
            deployWizardArtifacts.value = [];
          }
        };
        const logText = ref('');
        const logTailText = ref('');
        const logAppctlEl = ref(null);
        const logFileEl = ref(null);
        const obMainEl = ref(null);
        const logTailLabel = ref('（点击左侧步骤或日志标签）');
        const dashboardHostsTableRef = ref(null);
        const dashboardLastTasksTableRef = ref(null);
        const hostManageTableRef = ref(null);
        const deployRecordTableRef = ref(null);
        const treeRoots = ref([]);
        const manifestPayload = ref(null);
        const manifestSummary = ref(null);
        const manifestPaths = ref([]);
        const deployWizardSteps = [
          { key: 'mode', title: '部署形态', desc: '单节点或三节点拓扑' },
          { key: 'hosts', title: '选择节点', desc: '指定执行 SSH 与 appctl 的主机' },
          { key: 'config', title: '操作与配置', desc: 'appctl 动作与 user_edit 内容' },
        ];
        const taskRunStartedMs = ref(null);
        const taskRunEndedMs = ref(null);
        const deployNowMs = ref(Date.now());
        let deployElapsedTimer = null;
        const selectedPipelineKey = ref('');
        const selectedLogHint = ref('');
        const taskStatus = ref('');
        const currentTaskId = ref(null);
        const currentTaskSnapshot = ref(null);
        const lastAction = ref('');
        const phaseHint = ref('');
        const phaseBanner = ref('');
        const flowS1 = ref('pending');
        const flowS2 = ref('pending');
        const flowS3 = ref('pending'); // manifest 轮询
        const flowS4 = ref('pending'); // install.log
        let socket = null;
        let logSocket = null;

        const showManifestTree = computed(() => {
          const a = lastAction.value || '';
          return a === 'install' || a === 'upgrade';
        });

        const tripleDeployForManifest = computed(() => {
          const p = manifestPayload.value;
          if (p && p.deploy_mode === 'triple') return true;
          const snap = currentTaskSnapshot.value;
          return snap && snap.deploy_mode === 'triple';
        });

        const showTripleNodeStrip = computed(() => {
          const s = manifestSummary.value;
          return Boolean(
            showManifestTree.value
            && tripleDeployForManifest.value
            && s
            && s.multi_node
            && Array.isArray(s.per_node_stats)
            && s.per_node_stats.length >= 2
          );
        });

        const tripleNodeProgressList = computed(() => {
          const s = manifestSummary.value;
          if (!s || !Array.isArray(s.per_node_stats)) return [];
          return s.per_node_stats;
        });

        const tripleNodeRoleText = (role) => {
          const m = { node1: '节点1（manifest.yaml）', node2: '节点2', node3: '节点3' };
          return m[role] || role || '节点';
        };

        const shortPath = (p) => {
          if (!p) return '';
          const s = String(p);
          const i = s.lastIndexOf('/');
          return i >= 0 ? s.slice(i + 1) : s;
        };

        const subStatusDotClass = (st) => {
          const x = (st || '').toLowerCase();
          if (x === 'done') return 'done';
          if (x === 'running' || x === 'retrying') return 'running';
          if (x === 'error' || x === 'failed') return 'error';
          return 'none';
        };

        const pipelineRows = computed(() => {
          const p = manifestPayload.value;
          if (p && p.pipeline && p.pipeline.length) return p.pipeline;
          return [];
        });

        const patchRowFromPipeline = computed(() => {
          const rows = pipelineRows.value || [];
          return rows.find((r) => r && r.key === 'patch') || null;
        });

        const manifestInstallAllComplete = computed(() => {
          const s = manifestSummary.value;
          if (!s || s.services_total == null || s.services_total <= 0) return false;
          return (s.services_done || 0) >= s.services_total;
        });

        const patchChildrenAllTerminal = (pr) => {
          if (!pr) return false;
          const ch = pr.children || [];
          if (!ch.length) return false;
          return ch.every((c) => {
            const x = (c.status || 'none').toLowerCase();
            return x === 'done' || x === 'error' || x === 'failed';
          });
        };

        const precheckVirtualRow = computed(() => {
          if (!showManifestTree.value) return null;
          const pr = patchRowFromPipeline.value;
          if (!pr) return null;
          const ps = (pr.level_status || 'none').toLowerCase();
          // 现场 manifest 可能不写 patch_status，仅靠子项 done；或已全部完成但顶层仍为 none
          const patchStarted = (
            ps === 'running' || ps === 'retrying' || ps === 'done' || ps === 'error'
            || patchChildrenAllTerminal(pr)
            || manifestInstallAllComplete.value
          );
          const lv = patchStarted ? 'done' : 'running';
          return {
            key: '__precheck__',
            title: '步骤零：前置检查（precheck）',
            level_status: lv,
            parallel_note: '集群级，不区分节点',
            children: [],
          };
        });

        const displayPipelineRows = computed(() => {
          const v = precheckVirtualRow.value;
          const rest = pipelineRows.value || [];
          if (v) return [v, ...rest];
          return rest;
        });

        const activePipelineKey = computed(() => {
          const rows = pipelineRows.value || [];
          const pre = precheckVirtualRow.value;
          // 仅当虚拟前置检查仍为 running 时停留在该步（避免 patch_status 一直为 none 时永远卡在这一步）
          if (pre && (pre.level_status || '').toLowerCase() === 'running') {
            return '__precheck__';
          }
          if (manifestInstallAllComplete.value && rows.length) {
            return rows[rows.length - 1].key;
          }
          for (const r of rows) {
            if (!r) continue;
            const lv = (r.level_status || 'none').toLowerCase();
            if (lv === 'running' || lv === 'retrying') return r.key;
          }
          for (const r of rows) {
            const ch = r.children || [];
            for (const s of ch) {
              const st = (s.status || 'none').toLowerCase();
              if (st === 'running' || st === 'retrying') return r.key;
            }
          }
          for (const r of rows) {
            const lv = (r.level_status || 'none').toLowerCase();
            // 安装已完成时，不要把仍为 none 的空层当成「当前步」
            if (manifestInstallAllComplete.value) continue;
            if (lv !== 'done' && lv !== 'error') return r.key;
          }
          return rows.length ? rows[rows.length - 1].key : '';
        });

        const rowEffectiveLevelStatus = (row) => {
          if (!row || row.key === '__precheck__') return row ? row.level_status : 'none';
          if (manifestInstallAllComplete.value) return 'done';
          return row.level_status || 'none';
        };

        const tripleGroupedSubs = (row) => {
          if (!tripleDeployForManifest.value || !row || row.key === '__precheck__') return [];
          const ch0 = (row.children || [])[0];
          if (!ch0 || !Array.isArray(ch0.node_details) || !ch0.node_details.length) return [];
          const labels = tripleNodeProgressList.value.length
            ? tripleNodeProgressList.value.map((p) => p.label)
            : (ch0.node_details || []).map((d) => d.node_label);
          if (!labels.length) return [];
          return labels.map((node_label) => ({
            node_label,
            subs: (row.children || []).map((ch) => {
              const nd = (ch.node_details || []).find((d) => d.node_label === node_label);
              const st = nd ? nd.status : 'none';
              return { ...ch, _nodeStatus: st };
            }),
          }));
        };

        const subLabelWithoutStatus = (sub) => (sub && sub.label) ? String(sub.label) : '';

        const pipelineLvPillClass = (st) => {
          const x = (st || 'none').toLowerCase();
          if (x === 'done') return 'lv-done';
          if (x === 'running' || x === 'retrying') return x === 'retrying' ? 'lv-retrying' : 'lv-running';
          if (x === 'error' || x === 'failed') return 'lv-error';
          if (x === 'null') return 'lv-null';
          return 'lv-none';
        };

        const subStPillClass = (st) => {
          const x = (st || 'none').toLowerCase();
          if (x === 'done') return 'st-done';
          if (x === 'running') return 'st-running';
          if (x === 'retrying') return 'st-retrying';
          if (x === 'error' || x === 'failed') return 'st-error';
          if (x === 'null') return 'st-null';
          return 'st-none';
        };

        const formatDurationSec = (sec) => {
          if (sec == null || Number.isNaN(sec) || sec < 0) return '—';
          const s = Math.floor(sec);
          const h = Math.floor(s / 3600);
          const m = Math.floor((s % 3600) / 60);
          const r = s % 60;
          if (h > 0) return h + ' 小时 ' + m + ' 分 ' + r + ' 秒';
          if (m > 0) return m + ' 分 ' + r + ' 秒';
          return r + ' 秒';
        };


        const manifestProgressPercent = computed(() => {
          const s = manifestSummary.value;
          if (!s || s.services_total == null) return 0;
          const p = s.progress_percent != null ? s.progress_percent : s.services_progress_percent;
          if (p != null) return Math.min(100, Math.max(0, Math.round(p)));
          const t = s.services_total || 0;
          const d = s.services_done || 0;
          return t ? Math.min(100, Math.round((100 * d) / t)) : 0;
        });

        const manifestEstimatedHuman = computed(() => {
          const s = manifestSummary.value;
          const sec = s && s.estimated_total_seconds;
          if (sec == null || sec <= 0) return '';
          return formatDurationSec(Number(sec));
        });

        const manifestCurrentStepLine = computed(() => {
          const s = manifestSummary.value;
          const cur = s && s.current_running_service;
          if (cur && (cur.label || cur.level_label)) {
            let t = (cur.level_label || cur.level || '') + ' → ' + (cur.label || cur.id || '');
            if (cur.start_time) t += ' · 开始 ' + String(cur.start_time);
            return t;
          }
          const rows = pipelineRows.value || [];
          for (const row of rows) {
            if ((row.level_status || '') === 'running') return (row.title || '') + '（大层执行中）';
            const ch = row.children || [];
            for (const sub of ch) {
              if ((sub.status || '') === 'running' || (sub.status || '') === 'retrying')
                return (row.title || '') + ' → ' + (sub.label || '');
            }
          }
          return '';
        });

        const clearDeployElapsedTimer = () => {
          if (deployElapsedTimer) {
            clearInterval(deployElapsedTimer);
            deployElapsedTimer = null;
          }
        };

        const startDeployElapsedTimer = () => {
          clearDeployElapsedTimer();
          deployElapsedTimer = setInterval(() => { deployNowMs.value = Date.now(); }, 1000);
        };

        const goDeployWizardStep = (idx) => {
          if (idx <= deployStep.value) {
            deployStep.value = idx;
            return;
          }
          if (idx === 1 && deployStep.value === 0) {
            deployStep.value = 1;
            return;
          }
          if (idx === 2 && deployStep.value === 1) {
            goDeployStep2();
          }
        };

        const breadcrumbTitle = computed(() => {
          if (activeMenu.value === 'deploy') {
            if (deploySubView.value === 'wizard') return '部署任务 / 新建部署';
            if (deploySubView.value === 'monitor') return '部署任务 / 流水线与日志';
            return '部署任务 / 记录列表';
          }
          if (activeMenu.value === 'hosts') {
            return hostSubView.value === 'form' ? '主机管理 / 纳管主机' : '主机管理 / 主机列表';
          }
          if (activeMenu.value === 'packages') {
            if (packageSubView.value === 'form') return '安装包管理 / 新建版本';
            if (packageSubView.value === 'detail') return '安装包管理 / 包文件';
            return '安装包管理 / 版本列表';
          }
          const m = { overview: '概览' };
          return m[activeMenu.value] || '';
        });

        const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length);
        const successCount = computed(() => tasks.value.filter(t => t.status === 'success').length);
        const failedCount = computed(() => tasks.value.filter(t => t.status === 'failed').length);
        const lastTasks = computed(() => tasks.value.slice(0, 8));
        const hostsWithCredential = computed(() => hosts.value.filter(h => h.has_credential).length);
        const hostsKeyAuth = computed(() => hosts.value.filter(h => h.auth_method === 'key').length);

        const deployStep = ref(0);
        /** deploy 子页: list | wizard | monitor */
        const deploySubView = ref('list');
        /** hosts 子页: list | form */
        const hostSubView = ref('list');
        let tableLayoutTimer = null;

        const currentRouteState = () => ({
          menu: activeMenu.value,
          hostSubView: hostSubView.value,
          deploySubView: deploySubView.value,
          packageSubView: packageSubView.value,
          packageDetailId: packageDetailRelease.value && packageDetailRelease.value.id ? packageDetailRelease.value.id : '',
          taskId: currentTaskId.value || '',
        });

        const syncHashFromState = (replace) => {
          if (!router || routeSyncMuted.value) return;
          const hash = router.buildHash(currentRouteState());
          if (replace) {
            history.replaceState(null, '', hash);
            return;
          }
          if (window.location.hash !== hash) {
            window.location.hash = hash;
          }
        };

        const applyRouteState = async (routeState) => {
          const state = routeState || {};
          routeSyncMuted.value = true;
          activeMenu.value = state.menu || 'overview';
          hostSubView.value = state.hostSubView || 'list';
          deploySubView.value = state.deploySubView || 'list';
          packageSubView.value = state.packageSubView || 'list';
          try {
            if (activeMenu.value === 'packages') {
              if (packageSubView.value === 'detail' && state.packageDetailId) {
                await fetchPackageReleases();
                const targetId = parseInt(state.packageDetailId, 10);
                const row = packageReleases.value.find((item) => item.id === targetId);
                if (row) await openPackageDetail(row);
                else backPackageList();
              } else if (packageSubView.value === 'list') {
                fetchPackageReleases().catch(() => {});
              }
            }
            if (activeMenu.value === 'deploy') {
              if (deploySubView.value === 'monitor' && state.taskId) {
                await fetchTasks();
                const targetId = parseInt(state.taskId, 10);
                const row = tasks.value.find((item) => item.id === targetId);
                if (row) await attachTask(row, { syncRoute: false });
                else backToDeployList(false);
              } else if (deploySubView.value === 'list') {
                fetchTasks().catch(() => {});
              }
            }
          } finally {
            routeSyncMuted.value = false;
            syncHashFromState(true);
          }
        };

        const handleHashChange = () => {
          if (!router || routeSyncMuted.value) return;
          const parsed = router.parseHash(window.location.hash);
          applyRouteState(parsed).catch(() => {});
        };

        const relayoutTable = (tableRef) => {
          const table = tableRef && tableRef.value;
          if (table && typeof table.doLayout === 'function') table.doLayout();
        };

        const relayoutVisibleTables = () => {
          const run = () => {
            if (activeMenu.value === 'overview') {
              relayoutTable(dashboardHostsTableRef);
              relayoutTable(dashboardLastTasksTableRef);
              return;
            }
            if (activeMenu.value === 'hosts' && hostSubView.value === 'list') {
              relayoutTable(hostManageTableRef);
              return;
            }
            if (activeMenu.value === 'deploy' && deploySubView.value === 'list') {
              relayoutTable(deployRecordTableRef);
            }
          };
          nextTick(() => {
            run();
            if (tableLayoutTimer) clearTimeout(tableLayoutTimer);
            tableLayoutTimer = setTimeout(run, 32);
          });
        };

        const onMenuSelect = (key) => {
          activeMenu.value = key;
          if (key === 'deploy' && token.value) {
            deploySubView.value = 'list';
            fetchTasks().catch(() => {});
          }
          if (key === 'hosts' && token.value) {
            hostSubView.value = 'list';
          }
          if (key === 'packages' && token.value) {
            packageSubView.value = 'list';
            fetchPackageReleases().catch(() => {});
          }
          syncHashFromState();
        };

        const openHostEnroll = () => {
          resetHostForm();
          hostSubView.value = 'form';
          syncHashFromState();
        };

        const backToHostList = () => {
          hostSubView.value = 'list';
          resetHostForm();
          syncHashFromState();
        };

        const openDeployWizard = () => {
          deploySubView.value = 'wizard';
          deployStep.value = 0;
          fetchPackageReleases().catch(() => {});
          syncHashFromState();
        };

        const backToDeployList = (shouldSyncRoute = true) => {
          // 仅隐藏监控 UI，不断开 WebSocket；再次进入「流水线与日志」可继续收流与历史缓冲
          deploySubView.value = 'list';
          fetchTasks().catch(() => {});
          if (shouldSyncRoute) syncHashFromState();
        };

        const isHostDisabledForNode1 = (hid) => {
          if (deployForm.deploy_mode !== 'triple') return false;
          return hid === deployForm.host_node2 || hid === deployForm.host_node3;
        };
        const isHostDisabledTriple = (hid, slot) => {
          if (deployForm.deploy_mode !== 'triple') return false;
          if (hid === deployForm.host) return true;
          if (slot === 2) return hid === deployForm.host_node3;
          if (slot === 3) return hid === deployForm.host_node2;
          return false;
        };

        const goDeployStep2 = () => {
          if (!deployForm.host) return ElementPlus.ElMessage.warning('请选择节点 1（执行机）');
          if (deployForm.deploy_mode === 'triple') {
            const ids = [deployForm.host, deployForm.host_node2, deployForm.host_node3].filter(Boolean);
            if (new Set(ids).size !== ids.length)
              return ElementPlus.ElMessage.warning('所选主机不能重复');
          }
          if (!(deployForm.user_edit_content || '').trim()) {
            deployForm.user_edit_content = USER_EDIT_TEMPLATE;
          }
          deployStep.value = 2;
        };

        const fillUserEditTemplate = () => {
          deployForm.user_edit_content = USER_EDIT_TEMPLATE;
          ElementPlus.ElMessage.success('已恢复为默认模板');
        };

        watch(() => deployForm.deploy_mode, (v) => {
          if (v === 'single') {
            deployForm.host_node2 = null;
            deployForm.host_node3 = null;
          }
        });
        watch([activeMenu, hostSubView, deploySubView], () => { relayoutVisibleTables(); });
        watch(hosts, () => { relayoutVisibleTables(); });
        watch(tasks, () => { relayoutVisibleTables(); });

        const setAuth = (access, refToken, u) => {
          token.value = access || '';
          refresh.value = refToken || '';
          if (access) localStorage.setItem('access', access); else localStorage.removeItem('access');
          if (refToken) localStorage.setItem('refresh', refToken); else localStorage.removeItem('refresh');
          if (u) { user.value = u; localStorage.setItem('user', JSON.stringify(u)); }
        };

        api.interceptors.request.use(cfg => {
          if (token.value) cfg.headers.Authorization = 'Bearer ' + token.value;
          return cfg;
        });

        api.interceptors.response.use(r => r, async err => {
          const orig = err.config;
          if (err.response && err.response.status === 401 && refresh.value && !orig._retry) {
            orig._retry = true;
            try {
              const { data } = await axios.post('/api/auth/token/refresh/', { refresh: refresh.value });
              setAuth(data.access, refresh.value, user.value);
              orig.headers.Authorization = 'Bearer ' + token.value;
              return api(orig);
            } catch (e) {
              setAuth('', '', null);
            }
          }
          return Promise.reject(err);
        });

        const fetchHosts = async () => {
          const { data } = await api.get('/hosts/');
          hosts.value = Array.isArray(data) ? data : (data.results || []);
        };

        const refreshHostsPage = async () => {
          loading.value = true;
          try {
            await fetchHosts();
            ElementPlus.ElMessage.success('列表已更新');
          } catch (e) {
            ElementPlus.ElMessage.error('刷新失败');
          } finally { loading.value = false; }
        };

        const authMethodLabel = (m) => (m === 'key' ? '密钥' : '密码');
        const formatHostTime = (iso) => {
          if (!iso) return '—';
          const d = new Date(iso);
          if (Number.isNaN(d.getTime())) return String(iso).slice(0, 19).replace('T', ' ');
          return d.toLocaleString('zh-CN', { hour12: false });
        };
        const fetchTasks = async () => {
          const { data } = await api.get('/deployment/tasks/');
          tasks.value = Array.isArray(data) ? data : (data.results || []);
        };

        const refreshTasksOnly = async () => {
          loading.value = true;
          try {
            await fetchTasks();
            ElementPlus.ElMessage.success('部署列表已更新');
          } catch (e) {
            ElementPlus.ElMessage.error('刷新失败');
          } finally { loading.value = false; }
        };

        const deployActionLabel = (a) => {
          const m = {
            precheck_install: '安装前置检查',
            precheck_upgrade: '升级前置检查',
            install: '安装',
            upgrade: '升级',
            uninstall_all: '卸载全部',
          };
          return m[a] || a || '—';
        };

        const deployStatusLabel = (s) => {
          const m = {
            pending: '待执行',
            running: '执行中',
            success: '成功',
            failed: '失败',
            cancelled: '已取消',
          };
          return m[s] || s || '—';
        };

        const deployStatusTagType = (s) => {
          if (s === 'success') return 'success';
          if (s === 'failed') return 'danger';
          if (s === 'running') return 'warning';
          if (s === 'cancelled') return 'info';
          return '';
        };

        const deployOutcomeTagType = (s) => {
          if (s === 'success') return 'success';
          if (s === 'failed') return 'danger';
          if (s === 'running') return 'warning';
          if (s === 'cancelled') return 'info';
          return 'info';
        };

        const deployTaskRowClass = ({ row }) =>
          (deploySubView.value === 'monitor' && currentTaskId.value && row.id === currentTaskId.value ? 'row-current-task' : '');

        const applyLiveTaskPatch = (partial) => {
          const id = currentTaskId.value;
          if (!id) return;
          let cur = currentTaskSnapshot.value;
          if (!cur || cur.id !== id) cur = { id };
          currentTaskSnapshot.value = { ...cur, ...partial };
        };

        const deployStatusStripVisible = computed(() => Boolean(currentTaskId.value));

        const effectiveLiveStatus = computed(() => {
          const s = currentTaskSnapshot.value;
          if (s && s.status) return s.status;
          const raw = taskStatus.value || '';
          if (raw.startsWith('finished:')) {
            const code = parseInt(raw.split(':')[1], 10);
            return Number.isNaN(code) ? '' : (code === 0 ? 'success' : 'failed');
          }
          return raw;
        });

        const deployStatusStripType = computed(() => {
          const st = effectiveLiveStatus.value;
          if (st === 'success') return 'success';
          if (st === 'failed') return 'error';
          if (st === 'running') return 'warning';
          return 'info';
        });

        const deployStatusStripTitle = computed(() => {
          const id = currentTaskId.value;
          if (!id) return '';
          const s = currentTaskSnapshot.value;
          const st = effectiveLiveStatus.value;
          const label = (s && s.outcome_label) || deployStatusLabel(st);
          const action = deployActionLabel((s && s.action) || lastAction.value);
          const parts = ['当前查看任务 #' + id, '操作：' + action, '结果：' + label];
          if (s && s.exit_code != null && (st === 'success' || st === 'failed' || st === 'cancelled'))
            parts.push('退出码 ' + s.exit_code);
          if (s && s.finished_at) parts.push('结束 ' + formatHostTime(s.finished_at));
          else if (s && s.started_at && st === 'running') parts.push('开始 ' + formatHostTime(s.started_at));
          return parts.join(' · ');
        });

        const liveTaskFinishedHint = computed(() => {
          const id = currentTaskId.value;
          if (!id) return '';
          const s = currentTaskSnapshot.value;
          const st = (s && s.status) || effectiveLiveStatus.value;
          if (st === 'success' || st === 'failed' || st === 'cancelled') {
            const ec = s && s.exit_code != null ? s.exit_code : '—';
            return '任务 #' + id + ' 已结束（' + deployStatusLabel(st) + '，退出码 ' + ec + '）。上方 appctl 窗口无历史回放时，请点击流水线区域的 precheck.log / install.log 查看远程文件日志。';
          }
          return '';
        });

        const deployElapsedHuman = computed(() => {
          const snap = currentTaskSnapshot.value;
          const st = (snap && snap.status) || effectiveLiveStatus.value || '';
          const parseIso = (x) => {
            if (!x) return null;
            const t = Date.parse(x);
            return Number.isNaN(t) ? null : t;
          };
          if (snap && (st === 'success' || st === 'failed' || st === 'cancelled')) {
            const a = parseIso(snap.started_at);
            const b = parseIso(snap.finished_at);
            if (a != null && b != null && b >= a) return formatDurationSec((b - a) / 1000);
          }
          const start = taskRunStartedMs.value;
          if (start == null) return '—';
          const end = taskRunEndedMs.value != null ? taskRunEndedMs.value : deployNowMs.value;
          return formatDurationSec((end - start) / 1000);
        });

        const refreshCurrentTaskSnapshot = async () => {
          const id = currentTaskId.value;
          if (!id) return;
          try {
            const { data } = await api.get('/deployment/tasks/' + id + '/');
            currentTaskSnapshot.value = data;
            taskStatus.value = data.status;
            const idx = tasks.value.findIndex((t) => t.id === id);
            if (idx >= 0) {
              const next = tasks.value.slice();
              next[idx] = { ...next[idx], ...data };
              tasks.value = next;
            }
          } catch (_) {}
        };

        const scrollLogEl = (elRef) => {
          nextTick(() => {
            const el = elRef && elRef.value;
            if (el && typeof el.scrollTop === 'number') {
              el.scrollTop = el.scrollHeight;
            }
          });
        };

        watch(logText, () => scrollLogEl(logAppctlEl));
        watch(logTailText, () => scrollLogEl(logFileEl));

        const resetFlow = () => {
          flowS1.value = 'pending';
          flowS2.value = 'pending';
          flowS3.value = 'pending';
          flowS4.value = 'pending';
          phaseHint.value = '';
          phaseBanner.value = '';
          manifestPaths.value = [];
          manifestPayload.value = null;
          manifestSummary.value = null;
          treeRoots.value = [];
          selectedPipelineKey.value = '';
          selectedLogHint.value = '';
          taskRunStartedMs.value = null;
          taskRunEndedMs.value = null;
          clearDeployElapsedTimer();
        };

        const closeSocket = () => {
          if (socket) { socket.close(); socket = null; }
        };
        const closeLogSocket = () => {
          if (logSocket) { logSocket.close(); logSocket = null; }
        };

        const openLogTail = (kind) => {
          if (!currentTaskId.value) return ElementPlus.ElMessage.warning('请先创建或订阅任务');
          closeLogSocket();
          logTailText.value = '';
          logTailLabel.value = kind === 'install' ? 'install.log' : 'precheck.log';
          const proto = location.protocol === 'https:' ? 'wss' : 'ws';
          const url = `${proto}://${location.host}/ws/deploy/${currentTaskId.value}/log/?token=${encodeURIComponent(token.value)}&kind=${encodeURIComponent(kind)}`;
          logSocket = new WebSocket(url);
          logSocket.onmessage = (ev) => {
            let msg;
            try { msg = JSON.parse(ev.data); } catch { return; }
            if (msg.type === 'chunk' && msg.data) {
              logTailText.value += msg.data;
              scrollLogEl(logFileEl);
            }
            if (msg.type === 'meta') logTailLabel.value = (msg.path || '') + ' (' + (msg.kind || '') + ')';
            if (msg.type === 'error') ElementPlus.ElMessage.error(msg.message || '日志错误');
          };
          logSocket.onerror = () => ElementPlus.ElMessage.error('日志 WebSocket 错误');
        };

        const openLogTailRel = (relFile, hint) => {
          if (!currentTaskId.value) return ElementPlus.ElMessage.warning('请先创建或订阅任务');
          closeLogSocket();
          logTailText.value = '';
          logTailLabel.value = hint || relFile;
          const proto = location.protocol === 'https:' ? 'wss' : 'ws';
          const url = `${proto}://${location.host}/ws/deploy/${currentTaskId.value}/log/?token=${encodeURIComponent(token.value)}&rel=${encodeURIComponent(relFile)}`;
          logSocket = new WebSocket(url);
          logSocket.onmessage = (ev) => {
            let msg;
            try { msg = JSON.parse(ev.data); } catch { return; }
            if (msg.type === 'chunk' && msg.data) {
              logTailText.value += msg.data;
              scrollLogEl(logFileEl);
            }
            if (msg.type === 'meta') logTailLabel.value = (msg.path || '') + (hint ? ' · ' + hint : '');
            if (msg.type === 'error') ElementPlus.ElMessage.error(msg.message || '日志错误');
          };
          logSocket.onerror = () => ElementPlus.ElMessage.error('日志 WebSocket 错误');
        };

        const logKindForTask = () => {
          const a = lastAction.value || '';
          if (a.startsWith('precheck')) return 'precheck';
          if (a === 'uninstall_all') return 'uninstall';
          return 'install';
        };

        const onPipelineStepClick = (row) => {
          selectedPipelineKey.value = row.key || '';
          selectedLogHint.value = row.title || '';
          openLogTail(logKindForTask());
        };

        const onPipelineSubClick = (sub, row) => {
          selectedPipelineKey.value = row.key || '';
          const lab = tripleDeployForManifest.value ? subLabelWithoutStatus(sub) : (sub.label || '');
          selectedLogHint.value = (row.title || '') + ' → ' + lab;
          openLogTail(logKindForTask());
        };

        /**
         * 订阅任务 appctl 输出 WebSocket。
         * - 同一任务且连接仍存活：不重连、不清缓冲（离开监控页再回来仍能看到已输出内容并继续收流）。
         * - preserveLogAndManifest=true：重连同一任务时保留 logText / manifest 等（进程未结束时补连不断档）。
         * - 切换任务：清空缓冲并 resetFlow。
         */
        const openSocket = (taskId, opts = {}) => {
          const preserveLogAndManifest = opts.preserveLogAndManifest === true;
          if (
            currentTaskId.value === taskId &&
            socket &&
            socket.readyState === WebSocket.OPEN
          ) {
            return;
          }
          closeSocket();
          closeLogSocket();
          if (!preserveLogAndManifest) {
            resetFlow();
            logText.value = '';
            logTailText.value = '';
          } else {
            logTailText.value = '';
          }
          const proto = location.protocol === 'https:' ? 'wss' : 'ws';
          const url = `${proto}://${location.host}/ws/deploy/${taskId}/?token=${encodeURIComponent(token.value)}`;
          socket = new WebSocket(url);
          socket.onmessage = (ev) => {
            let msg;
            try { msg = JSON.parse(ev.data); } catch { return; }
            if (msg.type === 'hello') {
              taskStatus.value = msg.status;
              if (msg.action) lastAction.value = msg.action;
              applyLiveTaskPatch({
                id: msg.task_id,
                action: msg.action,
                status: msg.status,
                exit_code: msg.exit_code,
                error_message: msg.error_message,
                finished_at: msg.finished_at,
                started_at: msg.started_at,
              });
              const st = msg.status || '';
              if (st === 'running' || st === 'pending') {
                const t = msg.started_at ? Date.parse(msg.started_at) : NaN;
                taskRunStartedMs.value = Number.isNaN(t) ? Date.now() : t;
                taskRunEndedMs.value = null;
                startDeployElapsedTimer();
              } else {
                clearDeployElapsedTimer();
                const a = msg.started_at ? Date.parse(msg.started_at) : null;
                const b = msg.finished_at ? Date.parse(msg.finished_at) : null;
                taskRunStartedMs.value = a && !Number.isNaN(a) ? a : null;
                taskRunEndedMs.value = b && !Number.isNaN(b) ? b : Date.now();
              }
            }
            if (msg.type === 'phase') {
              phaseBanner.value = msg.message || '';
              if (msg.paths && msg.paths.length) {
                phaseHint.value = '轮询: ' + msg.paths.join(', ');
              } else if (msg.paths_tried && msg.paths_tried.length) {
                phaseHint.value = '检测: ' + msg.paths_tried.join(', ');
              } else {
                phaseHint.value = msg.command || '';
              }
              if (msg.phase === 'run_appctl') { flowS1.value = 'active'; }
              if (msg.phase === 'manifest_polling') {
                flowS1.value = 'active';
                flowS3.value = 'active';
                flowS4.value = 'pending';
              }
              if (msg.phase === 'wait_init_in_stdout') {
                /* 兼容旧后端；新逻辑为 manifest_polling */
                flowS1.value = 'active';
                flowS3.value = 'active';
                flowS4.value = 'pending';
              }
              if (msg.phase === 'init_manifest_ready') {
                flowS3.value = 'active';
                flowS4.value = 'active';
              }
              if (msg.phase === 'manifest_skipped') {
                flowS3.value = 'skip';
                flowS4.value = 'skip';
              }
              if (msg.phase === 'precheck_no_manifest') {
                flowS3.value = 'skip';
                flowS4.value = 'skip';
              }
            }
            if (msg.type === 'log' && msg.data) logText.value += msg.data;
            if (msg.type === 'manifest' && msg.data) {
              manifestPayload.value = msg.data;
              if (msg.data.roots) treeRoots.value = msg.data.roots;
              manifestSummary.value = msg.data.summary || null;
              if (msg.data.manifest_paths) manifestPaths.value = msg.data.manifest_paths;
              flowS3.value = 'active';
              flowS4.value = 'active';
            }
            if (msg.type === 'manifest_wait') {
              let t = (msg.message || '') + (msg.paths ? ' — ' + msg.paths.join(', ') : '');
              if (msg.details && msg.details.length) t += ' | ' + msg.details.join(' | ');
              phaseHint.value = t;
            }
            if (msg.type === 'status') {
              taskStatus.value = msg.data;
              applyLiveTaskPatch({ status: msg.data });
              if (msg.data === 'running') {
                flowS1.value = 'active';
                if (taskRunStartedMs.value == null) {
                  taskRunStartedMs.value = Date.now();
                  startDeployElapsedTimer();
                }
              }
            }
            if (msg.type === 'done') {
              const st = msg.status || (msg.exit_code === 0 ? 'success' : 'failed');
              taskStatus.value = st;
              applyLiveTaskPatch({
                status: st,
                exit_code: msg.exit_code,
                finished_at: msg.finished_at,
              });
              taskRunEndedMs.value = msg.finished_at ? Date.parse(msg.finished_at) : Date.now();
              clearDeployElapsedTimer();
              flowS1.value = 'done';
              const a = lastAction.value || '';
              if (a === 'precheck_install' || a === 'precheck_upgrade' || a === 'uninstall_all') {
                flowS2.value = 'done';
                flowS3.value = 'skip';
                flowS4.value = 'skip';
              } else {
                flowS2.value = 'done';
                flowS3.value = flowS3.value === 'skip' ? 'skip' : 'done';
                flowS4.value = 'done';
              }
              refreshCurrentTaskSnapshot();
              fetchTasks().catch(() => {});
            }
          };
          socket.onerror = () => ElementPlus.ElMessage.error('WebSocket 错误');
        };

        const doLogin = async () => {
          loading.value = true;
          try {
            const { data } = await api.post('/auth/login/', loginForm);
            setAuth(data.token.access, data.token.refresh, data.user);
            ElementPlus.ElMessage.success('登录成功');
            activeMenu.value = 'overview';
            await fetchHosts();
            await fetchTasks();
          } catch (e) {
            ElementPlus.ElMessage.error(
              (e.response && e.response.data && e.response.data.detail) || '登录失败'
            );
          } finally { loading.value = false; }
        };

        const doRegister = async () => {
          loading.value = true;
          try {
            await api.post('/auth/register/', regForm);
            ElementPlus.ElMessage.success('注册成功，请登录');
            showRegister.value = false;
          } catch (e) {
            ElementPlus.ElMessage.error('注册失败');
          } finally { loading.value = false; }
        };

        const logout = () => {
          closeSocket();
          closeLogSocket();
          clearDeployElapsedTimer();
          setAuth('', '', null);
          localStorage.removeItem('user');
          logText.value = '';
          logTailText.value = '';
          treeRoots.value = [];
          manifestSummary.value = null;
          manifestPaths.value = [];
          manifestPayload.value = null;
          selectedPipelineKey.value = '';
          selectedLogHint.value = '';
          currentTaskSnapshot.value = null;
          currentTaskId.value = null;
          taskStatus.value = '';
          taskRunStartedMs.value = null;
          taskRunEndedMs.value = null;
        };

        const resetHostForm = () => {
          Object.assign(hostForm, { id: null, name: '', hostname: '', port: 22, username: 'root', auth_method: 'password', password: '', private_key: '', docker_service_root: '/data/docker-service' });
        };

        const saveHost = async () => {
          loading.value = true;
          try {
            if (hostForm.id) {
              await api.patch('/hosts/' + hostForm.id + '/', hostForm);
            } else {
              await api.post('/hosts/', hostForm);
            }
            ElementPlus.ElMessage.success('已保存');
            resetHostForm();
            hostSubView.value = 'list';
            await fetchHosts();
          } catch (e) {
            ElementPlus.ElMessage.error('保存失败');
          } finally { loading.value = false; }
        };

        const editHost = (row) => {
          Object.assign(hostForm, { ...row, password: '', private_key: '' });
          hostSubView.value = 'form';
        };

        const testHost = async (row) => {
          row._testing = true;
          try {
            const { data } = await api.post('/hosts/' + row.id + '/test_connection/');
            if (data.ok) ElementPlus.ElMessage.success(data.message);
            else ElementPlus.ElMessage.error(data.message);
          } finally { row._testing = false; }
        };

        const deleteHost = async (row) => {
          try {
            await ElementPlus.ElMessageBox.confirm(
              '确定删除主机「' + (row.name || row.hostname) + '」？此操作不可恢复。',
              '删除确认',
              { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
            );
          } catch { return; }
          loading.value = true;
          try {
            await api.delete('/hosts/' + row.id + '/');
            ElementPlus.ElMessage.success('已删除');
            if (hostForm.id === row.id) {
              resetHostForm();
              hostSubView.value = 'list';
            }
            await fetchHosts();
          } catch (e) {
            ElementPlus.ElMessage.error('删除失败');
          } finally { loading.value = false; }
        };

        const startDeploy = async () => {
          if (!deployForm.host) return ElementPlus.ElMessage.warning('请选择节点 1');
          if (!(deployForm.user_edit_content || '').trim())
            return ElementPlus.ElMessage.warning('请填写或保留默认 user_edit 配置');
          if (!deployForm.skip_package_sync && deployForm.package_release && (!deployForm.package_artifact_ids || !deployForm.package_artifact_ids.length))
            return ElementPlus.ElMessage.warning('请选择要下发的安装包，或勾选跳过同步');
          if (deployForm.deploy_mode === 'triple') {
            const ids = [deployForm.host, deployForm.host_node2, deployForm.host_node3].filter(Boolean);
            if (new Set(ids).size !== ids.length)
              return ElementPlus.ElMessage.warning('所选主机不能重复');
          }
          loading.value = true;
          logText.value = '';
          logTailText.value = '';
          treeRoots.value = [];
          manifestSummary.value = null;
          manifestPaths.value = [];
          manifestPayload.value = null;
          selectedPipelineKey.value = '';
          selectedLogHint.value = '';
          lastAction.value = deployForm.action;
          try {
            const body = {
              host: deployForm.host,
              deploy_mode: deployForm.deploy_mode,
              user_edit_content: deployForm.user_edit_content,
              action: deployForm.action,
              target: deployForm.target,
              skip_package_sync: !!deployForm.skip_package_sync,
              package_release: deployForm.skip_package_sync ? null : deployForm.package_release,
              package_artifact_ids: deployForm.skip_package_sync ? [] : (deployForm.package_artifact_ids || []).slice(),
            };
            if (deployForm.deploy_mode === 'triple') {
              body.host_node2 = deployForm.host_node2;
              body.host_node3 = deployForm.host_node3;
            }
            const { data } = await api.post('/deployment/tasks/', body);
            currentTaskId.value = data.id;
            taskStatus.value = data.status;
            currentTaskSnapshot.value = data;
            deploySubView.value = 'monitor';
            openSocket(data.id);
            await fetchTasks();
            ElementPlus.ElMessage.success('任务已创建');
            deployStep.value = 0;
            deployForm.host_node2 = null;
            deployForm.host_node3 = null;
          } catch (e) {
            const msg = e.response && e.response.data;
            const t = typeof msg === 'object' ? JSON.stringify(msg) : (msg || '创建任务失败');
            ElementPlus.ElMessage.error(t);
          } finally { loading.value = false; }
        };

        const attachTask = async (row) => {
          const prevId = currentTaskId.value;
          const sameTask = prevId === row.id;
          currentTaskId.value = row.id;
          taskStatus.value = row.status;
          lastAction.value = row.action || '';
          currentTaskSnapshot.value = { ...row };
          if (!sameTask) {
            logText.value = '';
            logTailText.value = '';
            treeRoots.value = [];
            manifestSummary.value = null;
            manifestPaths.value = [];
            manifestPayload.value = null;
            selectedPipelineKey.value = '';
            selectedLogHint.value = '';
          }
          activeMenu.value = 'deploy';
          deploySubView.value = 'monitor';
          try {
            const { data } = await api.get('/deployment/tasks/' + row.id + '/');
            currentTaskSnapshot.value = data;
            taskStatus.value = data.status;
          } catch (_) {}
          openSocket(row.id, { preserveLogAndManifest: sameTask });
          fetchTasks().catch(() => {});
          const st = (currentTaskSnapshot.value && currentTaskSnapshot.value.status) || row.status;
          if (st === 'running' || st === 'pending') {
            ElementPlus.ElMessage.info('已打开任务 #' + row.id + '，下方将推送 appctl 实时输出');
          } else {
            ElementPlus.ElMessage.info('已打开任务 #' + row.id + '（已结束：' + deployStatusLabel(st) + '）。标准输出无回放时请点 precheck.log / install.log');
          }
        };

        onMounted(async () => {
          if (token.value) {
            try { await fetchHosts(); await fetchTasks(); await fetchPackageReleases(); } catch {}
          }
          window.addEventListener('resize', relayoutVisibleTables);
        });
        onUnmounted(() => {
          if (tableLayoutTimer) clearTimeout(tableLayoutTimer);
          window.removeEventListener('resize', relayoutVisibleTables);
          closeSocket();
          closeLogSocket();
        });

        return {
          token, user, loading, sidebarCollapsed, activeMenu, breadcrumbTitle, runningCount, successCount, failedCount, lastTasks, onMenuSelect,
          hosts, hostsWithCredential, hostsKeyAuth, tasks, showRegister, loginForm, regForm, hostForm, deployForm, deployStep,
          hostSubView, openHostEnroll, backToHostList,
          deploySubView, openDeployWizard, backToDeployList,
          deployWizardSteps, goDeployWizardStep,
          refreshTasksOnly, deployActionLabel, deployStatusLabel, deployStatusTagType, deployOutcomeTagType, deployTaskRowClass,
          currentTaskSnapshot, deployStatusStripVisible, deployStatusStripTitle, deployStatusStripType, liveTaskFinishedHint,
          deployElapsedHuman, manifestProgressPercent, manifestEstimatedHuman, manifestCurrentStepLine,
          logText, logTailText, logTailLabel, logAppctlEl, logFileEl, obMainEl, treeRoots, manifestSummary, manifestPaths, manifestPayload, taskStatus, currentTaskId,
          dashboardHostsTableRef, dashboardLastTasksTableRef, hostManageTableRef, deployRecordTableRef,
          showManifestTree, showTripleNodeStrip, tripleNodeProgressList, tripleNodeRoleText, shortPath, subStatusDotClass,
          pipelineRows, displayPipelineRows, activePipelineKey, rowEffectiveLevelStatus, tripleGroupedSubs, subLabelWithoutStatus, pipelineLvPillClass, subStPillClass,
          selectedPipelineKey, selectedLogHint, phaseHint, phaseBanner, flowS1, flowS2, flowS3, flowS4,
          openLogTail, openLogTailRel, onPipelineStepClick, onPipelineSubClick,
          isHostDisabledForNode1, isHostDisabledTriple, goDeployStep2, fillUserEditTemplate,
          authMethodLabel, formatHostTime, refreshHostsPage,
          doLogin, doRegister, logout, saveHost, resetHostForm, editHost, testHost, deleteHost, startDeploy, attachTask,
          packageReleases, packageSubView, packageReleaseForm, packageDetailRelease, packageArtifacts,
          packageUploadAction, packageUploadHeaders,
          fetchPackageReleases, openPackageReleaseForm, backPackageList, savePackageRelease,
          openPackageDetail, fetchPackageArtifacts, deletePackageRelease, deletePackageArtifact,
          onPackageUploadSuccess, onPackageUploadError, loadDeployWizardArtifacts, onDeployPackageReleaseChange, onSkipPackageChange,
          deployWizardArtifacts,
        };
      }
    }).use(ElementPlus).mount('#app');
})(window);
