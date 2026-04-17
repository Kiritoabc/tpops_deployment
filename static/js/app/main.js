(function (window) {
  const { createApp, ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } = Vue;
  const api = axios.create({ baseURL: '/api' });
  const router = window.TPOPSRouter;
  const appTemplate = window.TPOPSApp && window.TPOPSApp.template;

  createApp({
    template: appTemplate,
    setup() {
      const refs = { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted };
      const loading = ref(false);
      const sidebarCollapsed = ref(false);
      const loginPanelTab = ref('login');
      const obMainEl = ref(null);
      const loginForm = reactive({ username: '', password: '' });
      const regForm = reactive({ username: '', email: '', password: '', password_confirm: '', role: 'viewer' });
      const hostForm = reactive({ id: null, name: '', hostname: '', port: 22, username: 'root', auth_method: 'password', password: '', private_key: '', docker_service_root: '/data/docker-service' });
      const USER_EDIT_TEMPLATE = '[user_edit]\n# 请按现场填写；以下为占位示例，创建任务前请改为真实 IP 等\nnode1_ip = 127.0.0.1\n';
      const deployForm = reactive({
        deploy_mode: 'single',
        host: null,
        host_node2: null,
        host_node3: null,
        action: 'install',
        target: 'gaussdb',
        skip_package_sync: false,
        package_release: null,
        package_artifact_ids: [],
        user_edit_content: USER_EDIT_TEMPLATE,
      });
      const shared = {
        api,
        router,
        loading,
        sidebarCollapsed,
        loginPanelTab,
        loginForm,
        regForm,
        hostForm,
        obMainEl,
        deployForm,
        USER_EDIT_TEMPLATE,
      };

      const pageState = window.TPOPSPageState.createPageState(refs, shared);
      const auth = window.TPOPSAuth.createAuthModule(refs, shared, pageState);
      const hosts = window.TPOPSHosts.createHostsModule(refs, shared, pageState);
      const packages = window.TPOPSPackages.createPackagesModule(refs, shared, pageState, auth);
      const deploy = window.TPOPSDeploy.createDeployModule(refs, shared, pageState, auth, hosts, packages);

      auth.bindLoaders({
        fetchHosts: hosts.fetchHosts,
        fetchTasks: deploy.fetchTasks,
        fetchPackageReleases: packages.fetchPackageReleases,
        resetRuntimeState: function () {
          deploy.closeSocket();
          deploy.closeLogSocket();
          deploy.resetFlow();
          deploy.logText.value = '';
          deploy.logTailText.value = '';
          deploy.treeRoots.value = [];
          deploy.manifestSummary.value = null;
          deploy.manifestPaths.value = [];
          deploy.manifestPayload.value = null;
          deploy.selectedPipelineKey.value = '';
          deploy.selectedLogHint.value = '';
          deploy.currentTaskSnapshot.value = null;
          deploy.currentTaskId.value = null;
          deploy.taskStatus.value = '';
          deploy.taskRunStartedMs.value = null;
          deploy.taskRunEndedMs.value = null;
        },
      });
      auth.configureApi();

      pageState.bindRouteHelpers({
        fetchTasks: deploy.fetchTasks,
        fetchPackageReleases: packages.fetchPackageReleases,
        openPackageDetail: packages.openPackageDetail,
        backPackageList: packages.backPackageList,
        attachTask: deploy.attachTask,
        backToDeployList: deploy.backToDeployList,
      }, {
        getPackageDetailId: () => packages.packageDetailRelease.value && packages.packageDetailRelease.value.id,
        getCurrentTaskId: () => deploy.currentTaskId.value,
        getPackageById: (id) => packages.getPackageById(id),
        getTaskById: (id) => deploy.tasks.value.find((item) => item.id === id) || null,
      });
      pageState.bindTableRelayout({
        dashboardHostsTableRef: hosts.dashboardHostsTableRef,
        dashboardLastTasksTableRef: deploy.dashboardLastTasksTableRef,
        hostManageTableRef: hosts.hostManageTableRef,
        deployRecordTableRef: deploy.deployRecordTableRef,
      });

      watch([pageState.activeMenu, pageState.hostSubView, pageState.deploySubView], () => pageState.relayoutVisibleTables());
      watch(hosts.hosts, () => pageState.relayoutVisibleTables());
      watch(deploy.tasks, () => pageState.relayoutVisibleTables());
      watch(() => deploy.logText.value, () => deploy.scrollLogEl(deploy.logAppctlEl));
      watch(() => deploy.logTailText.value, () => deploy.scrollLogEl(deploy.logFileEl));
      watch(() => deploy.deployForm.deploy_mode, (value) => {
        if (value === 'single') {
          deploy.deployForm.host_node2 = null;
          deploy.deployForm.host_node3 = null;
        }
      });

      onMounted(async () => {
        if (auth.token.value) {
          try {
            await hosts.fetchHosts();
            await deploy.fetchTasks();
            await packages.fetchPackageReleases();
          } catch {}
        }
        window.addEventListener('resize', pageState.relayoutVisibleTables);
        if (router) {
          window.addEventListener('hashchange', pageState.handleHashChange);
          if (window.location.hash) pageState.handleHashChange();
          else pageState.syncHashFromState(true);
        }
      });

      onUnmounted(() => {
        pageState.teardown();
        if (router) window.removeEventListener('hashchange', pageState.handleHashChange);
        window.removeEventListener('resize', pageState.relayoutVisibleTables);
        deploy.closeSocket();
        deploy.closeLogSocket();
      });

      return Object.assign(
        {
          loading,
          sidebarCollapsed,
          loginPanelTab,
          loginForm,
          regForm,
          hostForm,
          obMainEl,
        },
        auth,
        pageState,
        hosts,
        packages,
        deploy
      );
    },
  }).use(ElementPlus).mount('#app');
})(window);
