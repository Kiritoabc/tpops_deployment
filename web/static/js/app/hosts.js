window.TPOPSHosts = {
  createHostsModule(refs, shared, pageState) {
    const { ref, computed } = refs;
    const hosts = ref([]);
    const dashboardHostsTableRef = ref(null);
    const hostManageTableRef = ref(null);

    const hostsWithCredential = computed(() => hosts.value.filter((h) => h.has_credential).length);
    const hostsKeyAuth = computed(() => hosts.value.filter((h) => h.auth_method === 'key').length);

    function authMethodLabel(method) {
      return method === 'key' ? '密钥' : '密码';
    }

    function formatHostTime(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso).slice(0, 19).replace('T', ' ');
      return d.toLocaleString('zh-CN', { hour12: false });
    }

    function resetHostForm() {
      Object.assign(shared.hostForm, { id: null, name: '', hostname: '', port: 22, username: 'root', auth_method: 'password', password: '', private_key: '', docker_service_root: '/data/docker-service' });
    }

    async function fetchHosts() {
      const result = await shared.api.get('/hosts/');
      const data = result.data;
      hosts.value = Array.isArray(data) ? data : ((data && data.results) || []);
    }

    async function refreshHostsPage() {
      shared.loading.value = true;
      try {
        await fetchHosts();
        ElementPlus.ElMessage.success('列表已更新');
      } catch (_) {
        ElementPlus.ElMessage.error('刷新失败');
      } finally {
        shared.loading.value = false;
      }
    }

    function openHostEnroll() {
      resetHostForm();
      pageState.hostSubView.value = 'form';
      pageState.syncHashFromState();
    }

    function backToHostList(syncRoute) {
      pageState.hostSubView.value = 'list';
      resetHostForm();
      if (syncRoute !== false) pageState.syncHashFromState();
    }

    function editHost(row) {
      Object.assign(shared.hostForm, Object.assign({}, row, { password: '', private_key: '' }));
      pageState.hostSubView.value = 'form';
      pageState.syncHashFromState();
    }

    async function testHost(row) {
      row._testing = true;
      try {
        const result = await shared.api.post('/hosts/' + row.id + '/test_connection/');
        if (result.data && result.data.ok) ElementPlus.ElMessage.success(result.data.message);
        else ElementPlus.ElMessage.error((result.data && result.data.message) || '连接失败');
      } finally {
        row._testing = false;
      }
    }

    async function deleteHost(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定删除主机「' + (row.name || row.hostname) + '」？此操作不可恢复。', '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' });
      } catch (_) {
        return;
      }
      shared.loading.value = true;
      try {
        await shared.api.delete('/hosts/' + row.id + '/');
        ElementPlus.ElMessage.success('已删除');
        if (shared.hostForm.id === row.id) backToHostList();
        await fetchHosts();
      } catch (_) {
        ElementPlus.ElMessage.error('删除失败');
      } finally {
        shared.loading.value = false;
      }
    }

    async function saveHost() {
      shared.loading.value = true;
      try {
        if (shared.hostForm.id) await shared.api.patch('/hosts/' + shared.hostForm.id + '/', shared.hostForm);
        else await shared.api.post('/hosts/', shared.hostForm);
        ElementPlus.ElMessage.success('已保存');
        backToHostList(false);
        await fetchHosts();
        pageState.syncHashFromState();
      } catch (_) {
        ElementPlus.ElMessage.error('保存失败');
      } finally {
        shared.loading.value = false;
      }
    }

    return {
      hosts,
      hostsWithCredential,
      hostsKeyAuth,
      dashboardHostsTableRef,
      hostManageTableRef,
      authMethodLabel,
      formatHostTime,
      resetHostForm,
      fetchHosts,
      refreshHostsPage,
      openHostEnroll,
      backToHostList,
      editHost,
      testHost,
      deleteHost,
      saveHost,
    };
  }
};
