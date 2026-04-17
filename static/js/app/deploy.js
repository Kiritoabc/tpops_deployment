window.TPOPSDeploy = {
  createDeployModule(refs, shared, pageState, auth, hosts, packages) {
    const { ref, reactive, computed, nextTick } = refs;
    const tasks = ref([]);
    const deployRecordTableRef = ref(null);
    const logText = ref('');
    const logTailText = ref('');
    const logAppctlEl = ref(null);
    const logFileEl = ref(null);
    const logTailLabel = ref('（点击左侧步骤或日志标签）');
    const treeRoots = ref([]);
    const manifestPayload = ref(null);
    const manifestSummary = ref(null);
    const manifestPaths = ref([]);
    const deployWizardSteps = [
      { key: 'mode', title: '部署形态', desc: '单节点或三节点拓扑' },
      { key: 'hosts', title: '选择节点', desc: '指定执行 SSH 与 appctl 的主机' },
      { key: 'config', title: '操作与配置', desc: 'appctl 动作与 user_edit 内容' },
    ];
    const deployStep = ref(0);
    const taskRunStartedMs = ref(null);
    const taskRunEndedMs = ref(null);
    const deployNowMs = ref(Date.now());
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
    const flowS3 = ref('pending');
    const flowS4 = ref('pending');
    let deployElapsedTimer = null;
    let socket = null;
    let logSocket = null;

    const deployForm = shared.deployForm;
    const deploySubView = pageState.deploySubView;
    const activeMenu = pageState.activeMenu;

    const deployActionLabel = (action) => {
      const labels = {
        precheck_install: '安装前置检查',
        precheck_upgrade: '升级前置检查',
        install: '安装',
        upgrade: '升级',
        uninstall_all: '卸载全部',
      };
      return labels[action] || action || '—';
    };

    const deployStatusLabel = (status) => {
      const labels = {
        pending: '待执行',
        running: '执行中',
        success: '成功',
        failed: '失败',
        cancelled: '已取消',
      };
      return labels[status] || status || '—';
    };

    const deployStatusTagType = (status) => {
      if (status === 'success') return 'success';
      if (status === 'failed') return 'danger';
      if (status === 'running') return 'warning';
      if (status === 'cancelled') return 'info';
      return '';
    };

    const deployOutcomeTagType = (status) => {
      if (status === 'success') return 'success';
      if (status === 'failed') return 'danger';
      if (status === 'running') return 'warning';
      if (status === 'cancelled') return 'info';
      return 'info';
    };

    const deployTaskRowClass = ({ row }) => (
      deploySubView.value === 'monitor' && currentTaskId.value && row && row.id === currentTaskId.value ? 'row-current-task' : ''
    );

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

    const fetchTasks = async () => {
      const response = await shared.api.get('/deployment/tasks/');
      tasks.value = Array.isArray(response.data) ? response.data : (response.data.results || []);
    };

    const refreshTasksOnly = async () => {
      shared.loading.value = true;
      try {
        await fetchTasks();
        ElementPlus.ElMessage.success('部署列表已更新');
      } catch (_) {
        ElementPlus.ElMessage.error('刷新失败');
      } finally {
        shared.loading.value = false;
      }
    };

    const loadDeployWizardArtifacts = async (releaseId) => {
      await packages.loadDeployWizardArtifacts(releaseId);
    };

    const onDeployPackageReleaseChange = () => {
      packages.onDeployPackageReleaseChange(deployForm);
    };

    const onSkipPackageChange = () => {
      packages.onSkipPackageChange(deployForm);
    };

    const openDeployWizard = () => {
      deploySubView.value = 'wizard';
      deployStep.value = 0;
      packages.fetchPackageReleases().catch(() => {});
      pageState.syncHashFromState();
    };

    const backToDeployList = (shouldSyncRoute = true) => {
      deploySubView.value = 'list';
      fetchTasks().catch(() => {});
      if (shouldSyncRoute) pageState.syncHashFromState();
    };

    const isHostDisabledForNode1 = (hostId) => {
      if (deployForm.deploy_mode !== 'triple') return false;
      return hostId === deployForm.host_node2 || hostId === deployForm.host_node3;
    };

    const isHostDisabledTriple = (hostId, slot) => {
      if (deployForm.deploy_mode !== 'triple') return false;
      if (hostId === deployForm.host) return true;
      if (slot === 2) return hostId === deployForm.host_node3;
      if (slot === 3) return hostId === deployForm.host_node2;
      return false;
    };

    const goDeployWizardStep = (idx) => {
      const n = Number(idx);
      if (n === 0) {
        deployStep.value = 0;
        return;
      }
      if (n === 1) {
        deployStep.value = 1;
        return;
      }
      if (n === 2) {
        if (!deployForm.host) return ElementPlus.ElMessage.warning('请选择节点 1（执行机）');
        if (deployForm.deploy_mode === 'triple') {
          const ids = [deployForm.host, deployForm.host_node2, deployForm.host_node3].filter(Boolean);
          if (new Set(ids).size !== ids.length) return ElementPlus.ElMessage.warning('所选主机不能重复');
        }
        if (!(deployForm.user_edit_content || '').trim()) deployForm.user_edit_content = shared.USER_EDIT_TEMPLATE;
        deployStep.value = 2;
        return;
      }
    };

    const goDeployStep2 = () => goDeployWizardStep(2);

    const fillUserEditTemplate = () => {
      deployForm.user_edit_content = shared.USER_EDIT_TEMPLATE;
      ElementPlus.ElMessage.success('已恢复为默认模板');
    };

    const applyLiveTaskPatch = (partial) => {
      const id = currentTaskId.value;
      if (!id) return;
      let current = currentTaskSnapshot.value;
      if (!current || current.id !== id) current = { id };
      currentTaskSnapshot.value = Object.assign({}, current, partial);
    };

    const deployStatusStripVisible = computed(() => Boolean(currentTaskId.value));

    const effectiveLiveStatus = computed(() => {
      const snapshot = currentTaskSnapshot.value;
      if (snapshot && snapshot.status) return snapshot.status;
      const raw = taskStatus.value || '';
      if (raw.indexOf('finished:') === 0) {
        const code = parseInt(raw.split(':')[1], 10);
        return Number.isNaN(code) ? '' : (code === 0 ? 'success' : 'failed');
      }
      return raw;
    });

    const deployStatusStripType = computed(() => {
      const status = effectiveLiveStatus.value;
      if (status === 'success') return 'success';
      if (status === 'failed') return 'error';
      if (status === 'running') return 'warning';
      return 'info';
    });

    const deployStatusStripTitle = computed(() => {
      const id = currentTaskId.value;
      if (!id) return '';
      const snapshot = currentTaskSnapshot.value;
      const status = effectiveLiveStatus.value;
      const label = (snapshot && snapshot.outcome_label) || deployStatusLabel(status);
      const action = deployActionLabel((snapshot && snapshot.action) || lastAction.value);
      const parts = ['当前查看任务 #' + id, '操作：' + action, '结果：' + label];
      if (snapshot && snapshot.exit_code != null && (status === 'success' || status === 'failed' || status === 'cancelled')) parts.push('退出码 ' + snapshot.exit_code);
      if (snapshot && snapshot.finished_at) parts.push('结束 ' + hosts.formatHostTime(snapshot.finished_at));
      else if (snapshot && snapshot.started_at && status === 'running') parts.push('开始 ' + hosts.formatHostTime(snapshot.started_at));
      return parts.join(' · ');
    });

    const liveTaskFinishedHint = computed(() => {
      const id = currentTaskId.value;
      if (!id) return '';
      const snapshot = currentTaskSnapshot.value;
      const status = (snapshot && snapshot.status) || effectiveLiveStatus.value;
      if (status === 'success' || status === 'failed' || status === 'cancelled') {
        const exitCode = snapshot && snapshot.exit_code != null ? snapshot.exit_code : '—';
        return '任务 #' + id + ' 已结束（' + deployStatusLabel(status) + '，退出码 ' + exitCode + '）。上方 appctl 窗口无历史回放时，请点击流水线区域的 precheck.log / install.log 查看远程文件日志。';
      }
      return '';
    });

    const deployElapsedHuman = computed(() => {
      const snapshot = currentTaskSnapshot.value;
      const status = (snapshot && snapshot.status) || effectiveLiveStatus.value || '';
      const parseIso = (value) => {
        if (!value) return null;
        const parsed = Date.parse(value);
        return Number.isNaN(parsed) ? null : parsed;
      };
      if (snapshot && (status === 'success' || status === 'failed' || status === 'cancelled')) {
        const started = parseIso(snapshot.started_at);
        const finished = parseIso(snapshot.finished_at);
        if (started != null && finished != null && finished >= started) return formatDurationSec((finished - started) / 1000);
      }
      const start = taskRunStartedMs.value;
      if (start == null) return '—';
      const end = taskRunEndedMs.value != null ? taskRunEndedMs.value : deployNowMs.value;
      return formatDurationSec((end - start) / 1000);
    });

    const normSt = (s) => String(s || 'none').toLowerCase();

    const showManifestTree = computed(() => {
      const a = lastAction.value || '';
      return a === 'install' || a === 'upgrade';
    });

    const manifestProgressPercent = computed(() => {
      const s = manifestSummary.value;
      if (!s || s.services_total == null) return 0;
      const p = s.progress_percent != null ? s.progress_percent : s.services_progress_percent;
      const n = Number(p);
      if (Number.isNaN(n)) return 0;
      return Math.min(100, Math.max(0, Math.round(n)));
    });

    const manifestEstimatedHuman = computed(() => {
      const s = manifestSummary.value;
      if (!s || s.estimated_total_seconds == null) return '';
      const sec = Number(s.estimated_total_seconds);
      if (Number.isNaN(sec) || sec <= 0) return '';
      return '约 ' + formatDurationSec(sec);
    });

    const manifestCurrentStepLine = computed(() => {
      const s = manifestSummary.value;
      const cur = s && s.current_running_service;
      if (!cur || typeof cur !== 'object') return '';
      const lv = cur.level_label || cur.level || '';
      const lab = cur.label || cur.id || '';
      const st = normSt(cur.status);
      const parts = [lv, lab].filter(Boolean);
      return (parts.join(' · ') || '当前服务') + (st ? '（' + st + '）' : '');
    });

    const displayPipelineRows = computed(() => {
      const payload = manifestPayload.value;
      const pipe = payload && Array.isArray(payload.pipeline) ? payload.pipeline.slice() : [];
      const a = lastAction.value || '';
      if (a === 'install' || a === 'upgrade') {
        pipe.unshift({
          key: '__precheck__',
          title: '步骤零：前置检查',
          parallel_note: 'manifest 就绪前',
          children: [],
          level_status: 'running',
        });
      }
      return pipe;
    });

    const activePipelineKey = computed(() => selectedPipelineKey.value || '');

    const tripleDeployForManifest = computed(() => {
      const snap = currentTaskSnapshot.value;
      if (snap && snap.deploy_mode === 'triple') return true;
      const s = manifestSummary.value;
      return !!(s && s.multi_node);
    });

    const tripleNodeProgressList = computed(() => {
      const s = manifestSummary.value;
      const list = (s && Array.isArray(s.per_node_stats)) ? s.per_node_stats : [];
      return list;
    });

    const showTripleNodeStrip = computed(() => (
      tripleDeployForManifest.value && tripleNodeProgressList.value.length > 1
    ));

    const rowEffectiveLevelStatus = (row) => {
      if (!row) return 'none';
      if (row.key === '__precheck__') {
        const roots = treeRoots.value || [];
        const patch = roots.find((r) => r && r.id === 'patch');
        if (!patch) return 'running';
        const ps = normSt(patch.status);
        if (ps === 'none') return 'running';
        if (ps === 'error') return 'error';
        return 'done';
      }
      return row.level_status || 'none';
    };

    const pipelineLvPillClass = (st) => {
      const s = normSt(st);
      if (s === 'done') return 'pipeline-lv-pill lv-done';
      if (s === 'running' || s === 'retrying') return 'pipeline-lv-pill lv-running';
      if (s === 'error') return 'pipeline-lv-pill lv-error';
      if (s === 'none' || s === '') return 'pipeline-lv-pill lv-none';
      return 'pipeline-lv-pill lv-null';
    };

    const subStPillClass = (st) => {
      const s = normSt(st);
      if (s === 'done') return 'sub-st-pill st-done';
      if (s === 'running' || s === 'retrying') return 'sub-st-pill st-running';
      if (s === 'error') return 'sub-st-pill st-error';
      if (s === 'none' || s === '') return 'sub-st-pill st-none';
      return 'sub-st-pill st-null';
    };

    const subStatusDotClass = (st) => {
      const s = normSt(st);
      if (s === 'done') return 'node-dot done';
      if (s === 'running' || s === 'retrying') return 'node-dot running';
      if (s === 'error') return 'node-dot error';
      return 'node-dot none';
    };

    const shortPath = (p) => {
      if (!p) return '';
      const parts = String(p).replace(/\\/g, '/').split('/');
      return parts[parts.length - 1] || p;
    };

    const tripleNodeRoleText = (role) => {
      const r = String(role || '');
      if (r === 'node1') return '节点 1';
      if (r === 'node2') return '节点 2';
      if (r === 'node3') return '节点 3';
      return r || '节点';
    };

    const subLabelWithoutStatus = (sub) => {
      if (!sub || !sub.label) return '';
      return String(sub.label);
    };

    const tripleGroupedSubs = (row) => {
      if (!tripleDeployForManifest.value || !row || !Array.isArray(row.children)) return [];
      const out = [];
      const byLabel = {};
      row.children.forEach((sub) => {
        const nds = sub.node_details;
        if (nds && nds.length) {
          nds.forEach((nd) => {
            const lab = nd.node_label || ('节点' + ((nd.node_index || 0) + 1));
            if (!byLabel[lab]) byLabel[lab] = { node_label: lab, subs: [] };
            byLabel[lab].subs.push(Object.assign({}, sub, { _nodeStatus: nd.status }));
          });
        }
      });
      Object.keys(byLabel).forEach((k) => { out.push(byLabel[k]); });
      return out;
    };

    const refreshCurrentTaskSnapshot = async () => {
      const id = currentTaskId.value;
      if (!id) return;
      try {
        const response = await shared.api.get('/deployment/tasks/' + id + '/');
        currentTaskSnapshot.value = response.data;
        taskStatus.value = response.data.status;
        const index = tasks.value.findIndex((item) => item.id === id);
        if (index >= 0) {
          const next = tasks.value.slice();
          next[index] = Object.assign({}, next[index], response.data);
          tasks.value = next;
        }
      } catch (_) {}
    };

    const scrollLogEl = (elRef) => {
      nextTick(() => {
        const el = elRef && elRef.value;
        if (el && typeof el.scrollTop === 'number') el.scrollTop = el.scrollHeight;
      });
    };

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

    const closeSocket = () => {
      if (socket) {
        socket.close();
        socket = null;
      }
    };

    const closeLogSocket = () => {
      if (logSocket) {
        logSocket.close();
        logSocket = null;
      }
    };

    const openLogTail = (kind) => {
      if (!currentTaskId.value) return ElementPlus.ElMessage.warning('请先创建或订阅任务');
      closeLogSocket();
      logTailText.value = '';
      logTailLabel.value = kind === 'install' ? 'install.log' : 'precheck.log';
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${location.host}/ws/deploy/${currentTaskId.value}/log/?token=${encodeURIComponent(auth.token.value)}&kind=${encodeURIComponent(kind)}`;
      logSocket = new WebSocket(url);
      logSocket.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch (_) { return; }
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
      const url = `${proto}://${location.host}/ws/deploy/${currentTaskId.value}/log/?token=${encodeURIComponent(auth.token.value)}&rel=${encodeURIComponent(relFile)}`;
      logSocket = new WebSocket(url);
      logSocket.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch (_) { return; }
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
      const action = lastAction.value || '';
      if (action.indexOf('precheck') === 0) return 'precheck';
      if (action === 'uninstall_all') return 'uninstall';
      return 'install';
    };

    const onPipelineStepClick = (row) => {
      selectedPipelineKey.value = row.key || '';
      selectedLogHint.value = row.title || '';
      openLogTail(logKindForTask());
    };

    const onPipelineSubClick = (sub, row) => {
      selectedPipelineKey.value = row.key || '';
      const label = (sub && sub.label) ? String(sub.label) : '';
      selectedLogHint.value = (row.title || '') + ' → ' + label;
      openLogTail(logKindForTask());
    };

    const openSocket = (taskId, opts = {}) => {
      const preserveLogAndManifest = opts.preserveLogAndManifest === true;
      if (currentTaskId.value === taskId && socket && socket.readyState === WebSocket.OPEN) return;
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
      const url = `${proto}://${location.host}/ws/deploy/${taskId}/?token=${encodeURIComponent(auth.token.value)}`;
      socket = new WebSocket(url);
      socket.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch (_) { return; }
        if (msg.type === 'hello') {
          taskStatus.value = msg.status;
          if (msg.action) lastAction.value = msg.action;
          applyLiveTaskPatch({ id: msg.task_id, action: msg.action, status: msg.status, exit_code: msg.exit_code, error_message: msg.error_message, finished_at: msg.finished_at, started_at: msg.started_at });
          const status = msg.status || '';
          if (status === 'running' || status === 'pending') {
            const startedAt = msg.started_at ? Date.parse(msg.started_at) : NaN;
            taskRunStartedMs.value = Number.isNaN(startedAt) ? Date.now() : startedAt;
            taskRunEndedMs.value = null;
            startDeployElapsedTimer();
          } else {
            clearDeployElapsedTimer();
            const start = msg.started_at ? Date.parse(msg.started_at) : null;
            const end = msg.finished_at ? Date.parse(msg.finished_at) : null;
            taskRunStartedMs.value = start && !Number.isNaN(start) ? start : null;
            taskRunEndedMs.value = end && !Number.isNaN(end) ? end : Date.now();
          }
        }
        if (msg.type === 'phase') {
          phaseBanner.value = msg.message || '';
          if (msg.paths && msg.paths.length) phaseHint.value = '轮询: ' + msg.paths.join(', ');
          else if (msg.paths_tried && msg.paths_tried.length) phaseHint.value = '检测: ' + msg.paths_tried.join(', ');
          else phaseHint.value = msg.command || '';
          if (msg.phase === 'run_appctl') flowS1.value = 'active';
          if (msg.phase === 'manifest_polling') {
            flowS1.value = 'active';
            flowS3.value = 'active';
            flowS4.value = 'pending';
          }
          if (msg.phase === 'wait_init_in_stdout') {
            flowS1.value = 'active';
            flowS3.value = 'active';
            flowS4.value = 'pending';
          }
          if (msg.phase === 'init_manifest_ready') {
            flowS3.value = 'active';
            flowS4.value = 'active';
          }
          if (msg.phase === 'manifest_skipped' || msg.phase === 'precheck_no_manifest') {
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
          let tip = (msg.message || '') + (msg.paths ? ' — ' + msg.paths.join(', ') : '');
          if (msg.details && msg.details.length) tip += ' | ' + msg.details.join(' | ');
          phaseHint.value = tip;
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
          const finalStatus = msg.status || (msg.exit_code === 0 ? 'success' : 'failed');
          taskStatus.value = finalStatus;
          applyLiveTaskPatch({ status: finalStatus, exit_code: msg.exit_code, finished_at: msg.finished_at });
          taskRunEndedMs.value = msg.finished_at ? Date.parse(msg.finished_at) : Date.now();
          clearDeployElapsedTimer();
          flowS1.value = 'done';
          const action = lastAction.value || '';
          if (action === 'precheck_install' || action === 'precheck_upgrade' || action === 'uninstall_all') {
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

    const startDeploy = async () => {
      if (!deployForm.host) return ElementPlus.ElMessage.warning('请选择节点 1');
      if (!(deployForm.user_edit_content || '').trim()) return ElementPlus.ElMessage.warning('请填写或保留默认 user_edit 配置');
      if (!deployForm.skip_package_sync && deployForm.package_release && (!deployForm.package_artifact_ids || !deployForm.package_artifact_ids.length)) return ElementPlus.ElMessage.warning('请选择要下发的安装包，或勾选跳过同步');
      if (deployForm.deploy_mode === 'triple') {
        const ids = [deployForm.host, deployForm.host_node2, deployForm.host_node3].filter(Boolean);
        if (new Set(ids).size !== ids.length) return ElementPlus.ElMessage.warning('所选主机不能重复');
      }
      shared.loading.value = true;
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
        const response = await shared.api.post('/deployment/tasks/', body);
        currentTaskId.value = response.data.id;
        taskStatus.value = response.data.status;
        currentTaskSnapshot.value = response.data;
        deploySubView.value = 'monitor';
        openSocket(response.data.id);
        await fetchTasks();
        pageState.syncHashFromState();
        ElementPlus.ElMessage.success('任务已创建');
        deployStep.value = 0;
        deployForm.host_node2 = null;
        deployForm.host_node3 = null;
      } catch (e) {
        const msg = e.response && e.response.data;
        const text = typeof msg === 'object' ? JSON.stringify(msg) : (msg || '创建任务失败');
        ElementPlus.ElMessage.error(text);
      } finally {
        shared.loading.value = false;
      }
    };

    const attachTask = async (row, opts = {}) => {
      const shouldSyncRoute = opts.syncRoute !== false;
      const prevId = currentTaskId.value;
      const sameTask = prevId === row.id;
      currentTaskId.value = row.id;
      taskStatus.value = row.status;
      lastAction.value = row.action || '';
      currentTaskSnapshot.value = Object.assign({}, row);
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
        const response = await shared.api.get('/deployment/tasks/' + row.id + '/');
        currentTaskSnapshot.value = response.data;
        taskStatus.value = response.data.status;
      } catch (_) {}
      openSocket(row.id, { preserveLogAndManifest: sameTask });
      fetchTasks().catch(() => {});
      if (shouldSyncRoute) pageState.syncHashFromState();
      const status = (currentTaskSnapshot.value && currentTaskSnapshot.value.status) || row.status;
      if (status === 'running' || status === 'pending') {
        ElementPlus.ElMessage.info('已打开任务 #' + row.id + '，下方将推送 appctl 实时输出');
      } else {
        ElementPlus.ElMessage.info('已打开任务 #' + row.id + '（已结束：' + deployStatusLabel(status) + '）。标准输出无回放时请点 precheck.log / install.log');
      }
    };

    return {
      deployForm,
      tasks,
      deploySubView,
      deployStep,
      deployWizardSteps,
      deployWizardArtifacts: packages.deployWizardArtifacts,
      deployRecordTableRef,
      dashboardLastTasksTableRef: ref(null),
      logText,
      logTailText,
      logAppctlEl,
      logFileEl,
      logTailLabel,
      treeRoots,
      manifestPayload,
      manifestSummary,
      manifestPaths,
      taskRunStartedMs,
      taskRunEndedMs,
      deployNowMs,
      selectedPipelineKey,
      selectedLogHint,
      taskStatus,
      currentTaskId,
      currentTaskSnapshot,
      lastAction,
      phaseHint,
      phaseBanner,
      flowS1,
      flowS2,
      flowS3,
      flowS4,
      fetchTasks,
      refreshTasksOnly,
      loadDeployWizardArtifacts,
      onDeployPackageReleaseChange,
      onSkipPackageChange,
      openDeployWizard,
      backToDeployList,
      isHostDisabledForNode1,
      isHostDisabledTriple,
      goDeployWizardStep,
      goDeployStep2,
      fillUserEditTemplate,
      deployActionLabel,
      deployStatusLabel,
      deployStatusTagType,
      deployOutcomeTagType,
      deployTaskRowClass,
      deployStatusStripVisible,
      deployStatusStripType,
      deployStatusStripTitle,
      liveTaskFinishedHint,
      deployElapsedHuman,
      showManifestTree,
      manifestProgressPercent,
      manifestEstimatedHuman,
      manifestCurrentStepLine,
      displayPipelineRows,
      activePipelineKey,
      tripleDeployForManifest,
      tripleNodeProgressList,
      showTripleNodeStrip,
      rowEffectiveLevelStatus,
      pipelineLvPillClass,
      subStPillClass,
      subStatusDotClass,
      shortPath,
      tripleNodeRoleText,
      subLabelWithoutStatus,
      tripleGroupedSubs,
      refreshCurrentTaskSnapshot,
      scrollLogEl,
      resetFlow,
      closeSocket,
      closeLogSocket,
      openLogTail,
      openLogTailRel,
      logKindForTask,
      onPipelineStepClick,
      onPipelineSubClick,
      openSocket,
      startDeploy,
      attachTask,
    };
  }
};
