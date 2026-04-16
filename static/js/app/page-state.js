window.TPOPSPageState = {
  createPageState(refs, shared) {
    const { ref, computed, nextTick } = refs;
    const activeMenu = ref('overview');
    const hostSubView = ref('list');
    const deploySubView = ref('list');
    const packageSubView = ref('list');
    const routeSyncMuted = ref(false);
    let tableLayoutTimer = null;
    let routeHelpers = {};
    let routeStateGetters = {};
    let tableRefs = {};

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
      return '概览';
    });

    function bindRouteHelpers(helpers, getters) {
      routeHelpers = helpers || {};
      routeStateGetters = getters || {};
    }

    function bindTableRelayout(refMap) {
      tableRefs = refMap || {};
    }

    function currentRouteState() {
      return {
        menu: activeMenu.value,
        hostSubView: hostSubView.value,
        deploySubView: deploySubView.value,
        packageSubView: packageSubView.value,
        packageReleaseId: routeStateGetters.getPackageDetailId ? routeStateGetters.getPackageDetailId() : null,
        deployTaskId: routeStateGetters.getCurrentTaskId ? routeStateGetters.getCurrentTaskId() : null,
      };
    }

    function syncHashFromState(replace) {
      if (!shared.router || routeSyncMuted.value) return;
      const hash = shared.router.buildHash(currentRouteState());
      if (replace) {
        history.replaceState(null, '', hash);
      } else if (window.location.hash !== hash) {
        window.location.hash = hash;
      }
    }

    function relayoutTable(tableRef) {
      const table = tableRef && tableRef.value;
      if (table && typeof table.doLayout === 'function') table.doLayout();
    }

    function relayoutVisibleTables() {
      const run = () => {
        if (activeMenu.value === 'overview') {
          relayoutTable(tableRefs.dashboardHostsTableRef);
          relayoutTable(tableRefs.dashboardLastTasksTableRef);
          return;
        }
        if (activeMenu.value === 'hosts' && hostSubView.value === 'list') {
          relayoutTable(tableRefs.hostManageTableRef);
          return;
        }
        if (activeMenu.value === 'deploy' && deploySubView.value === 'list') {
          relayoutTable(tableRefs.deployRecordTableRef);
        }
      };
      nextTick(() => {
        run();
        if (tableLayoutTimer) clearTimeout(tableLayoutTimer);
        tableLayoutTimer = setTimeout(run, 32);
      });
    }

    async function applyRouteState(routeState) {
      const state = routeState || {};
      routeSyncMuted.value = true;
      activeMenu.value = state.menu || 'overview';
      hostSubView.value = state.hostSubView || 'list';
      deploySubView.value = state.deploySubView || 'list';
      packageSubView.value = state.packageSubView || 'list';
      try {
        if (activeMenu.value === 'packages') {
          if (packageSubView.value === 'detail' && state.packageReleaseId && routeHelpers.fetchPackageReleases && routeHelpers.openPackageDetail && routeStateGetters.getPackageById) {
            await routeHelpers.fetchPackageReleases();
            const row = routeStateGetters.getPackageById(state.packageReleaseId);
            if (row) await routeHelpers.openPackageDetail(row, { syncRoute: false });
            else if (routeHelpers.backPackageList) routeHelpers.backPackageList(false);
          } else if (packageSubView.value === 'list' && routeHelpers.fetchPackageReleases) {
            routeHelpers.fetchPackageReleases().catch(() => {});
          }
        }
        if (activeMenu.value === 'deploy') {
          if (deploySubView.value === 'monitor' && state.deployTaskId && routeHelpers.fetchTasks && routeHelpers.attachTask && routeStateGetters.getTaskById) {
            await routeHelpers.fetchTasks();
            const row = routeStateGetters.getTaskById(state.deployTaskId);
            if (row) await routeHelpers.attachTask(row, { syncRoute: false });
            else if (routeHelpers.backToDeployList) routeHelpers.backToDeployList(false);
          } else if (deploySubView.value === 'list' && routeHelpers.fetchTasks) {
            routeHelpers.fetchTasks().catch(() => {});
          }
        }
      } finally {
        routeSyncMuted.value = false;
        syncHashFromState(true);
      }
    }

    function handleHashChange() {
      if (!shared.router || routeSyncMuted.value) return;
      const parsed = shared.router.parseHash(window.location.hash);
      applyRouteState(parsed).catch(() => {});
    }

    function onMenuSelect(key) {
      activeMenu.value = key;
      if (key === 'hosts') hostSubView.value = 'list';
      if (key === 'deploy') {
        deploySubView.value = 'list';
        if (routeHelpers.fetchTasks) routeHelpers.fetchTasks().catch(() => {});
      }
      if (key === 'packages') {
        packageSubView.value = 'list';
        if (routeHelpers.fetchPackageReleases) routeHelpers.fetchPackageReleases().catch(() => {});
      }
      syncHashFromState();
    }

    function teardown() {
      if (tableLayoutTimer) clearTimeout(tableLayoutTimer);
      tableLayoutTimer = null;
    }

    return {
      activeMenu,
      hostSubView,
      deploySubView,
      packageSubView,
      routeSyncMuted,
      breadcrumbTitle,
      bindRouteHelpers,
      bindTableRelayout,
      currentRouteState,
      syncHashFromState,
      relayoutVisibleTables,
      applyRouteState,
      handleHashChange,
      onMenuSelect,
      teardown,
    };
  }
};
