window.TPOPSPackages = {
  createPackagesModule(refs, shared, pageState, auth) {
    const { ref, reactive, computed } = refs;
    const packageReleases = ref([]);
    const packageReleaseForm = reactive({ name: '', description: '' });
    const packageDetailRelease = ref(null);
    const packageArtifacts = ref([]);
    const deployWizardArtifacts = ref([]);

    const packageUploadAction = computed(() => `${location.origin}/api/packages/artifacts/`);
    const packageUploadHeaders = computed(() => (auth.token.value ? { Authorization: 'Bearer ' + auth.token.value } : {}));

    function normalizeListResponse(data) {
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.results)) return data.results;
      if (data && Array.isArray(data.data)) return data.data;
      return [];
    }

    async function fetchPackageReleases() {
      try {
        const result = await shared.api.get('/packages/releases/');
        packageReleases.value = normalizeListResponse(result.data);
      } catch (_) {
        packageReleases.value = [];
      }
    }

    async function fetchPackageArtifacts(releaseId) {
      if (!releaseId) return;
      shared.loading.value = true;
      try {
        const result = await shared.api.get('/packages/artifacts/', { params: { release: releaseId } });
        packageArtifacts.value = normalizeListResponse(result.data);
      } catch (_) {
        packageArtifacts.value = [];
      } finally {
        shared.loading.value = false;
      }
    }

    function getPackageById(id) {
      return packageReleases.value.find((item) => item.id === id) || null;
    }

    function openPackageReleaseForm(syncRoute) {
      packageReleaseForm.name = '';
      packageReleaseForm.description = '';
      pageState.packageSubView.value = 'form';
      if (syncRoute !== false) pageState.syncHashFromState();
    }

    function backPackageList(syncRoute) {
      pageState.packageSubView.value = 'list';
      packageDetailRelease.value = null;
      packageArtifacts.value = [];
      fetchPackageReleases().catch(() => {});
      if (syncRoute !== false) pageState.syncHashFromState();
    }

    async function savePackageRelease() {
      if (!(packageReleaseForm.name || '').trim()) return ElementPlus.ElMessage.warning('请填写版本名称');
      shared.loading.value = true;
      try {
        await shared.api.post('/packages/releases/', { name: packageReleaseForm.name.trim(), description: (packageReleaseForm.description || '').trim() });
        ElementPlus.ElMessage.success('已创建');
        backPackageList(false);
        pageState.syncHashFromState();
      } catch (e) {
        ElementPlus.ElMessage.error(e.response && e.response.data ? JSON.stringify(e.response.data) : '保存失败');
      } finally {
        shared.loading.value = false;
      }
    }

    async function openPackageDetail(row, opts) {
      opts = opts || {};
      packageDetailRelease.value = row;
      pageState.packageSubView.value = 'detail';
      await fetchPackageArtifacts(row.id);
      if (opts.syncRoute !== false) pageState.syncHashFromState();
    }

    async function deletePackageRelease(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定删除版本「' + row.name + '」及其下所有安装包？', '确认', { type: 'warning' });
      } catch (_) {
        return;
      }
      shared.loading.value = true;
      try {
        await shared.api.delete('/packages/releases/' + row.id + '/');
        ElementPlus.ElMessage.success('已删除');
        fetchPackageReleases().catch(() => {});
        if (packageDetailRelease.value && packageDetailRelease.value.id === row.id) backPackageList();
      } catch (_) {
        ElementPlus.ElMessage.error('删除失败');
      } finally {
        shared.loading.value = false;
      }
    }

    async function deletePackageArtifact(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定删除文件「' + row.remote_basename + '」？', '确认', { type: 'warning' });
      } catch (_) {
        return;
      }
      shared.loading.value = true;
      try {
        await shared.api.delete('/packages/artifacts/' + row.id + '/');
        ElementPlus.ElMessage.success('已删除');
        if (packageDetailRelease.value) await fetchPackageArtifacts(packageDetailRelease.value.id);
        fetchPackageReleases().catch(() => {});
      } catch (_) {
        ElementPlus.ElMessage.error('删除失败');
      } finally {
        shared.loading.value = false;
      }
    }

    function onPackageUploadSuccess() {
      ElementPlus.ElMessage.success('上传成功');
      if (packageDetailRelease.value) fetchPackageArtifacts(packageDetailRelease.value.id);
      fetchPackageReleases().catch(() => {});
    }

    function onPackageUploadError() {
      ElementPlus.ElMessage.error('上传失败');
    }

    async function loadDeployWizardArtifacts(releaseId) {
      deployWizardArtifacts.value = [];
      if (!releaseId) return;
      try {
        const result = await shared.api.get('/packages/artifacts/', { params: { release: releaseId } });
        deployWizardArtifacts.value = normalizeListResponse(result.data);
      } catch (_) {
        deployWizardArtifacts.value = [];
      }
    }

    function onDeployPackageReleaseChange(deployForm) {
      deployForm.package_artifact_ids = [];
      loadDeployWizardArtifacts(deployForm.package_release);
    }

    function onSkipPackageChange(deployForm) {
      if (!deployForm.skip_package_sync) return;
      deployForm.package_release = null;
      deployForm.package_artifact_ids = [];
      deployWizardArtifacts.value = [];
    }

    return {
      packageReleases,
      packageSubView: pageState.packageSubView,
      packageReleaseForm,
      packageDetailRelease,
      packageArtifacts,
      deployWizardArtifacts,
      packageUploadAction,
      packageUploadHeaders,
      normalizeListResponse,
      getPackageById,
      fetchPackageReleases,
      fetchPackageArtifacts,
      openPackageReleaseForm,
      backPackageList,
      savePackageRelease,
      openPackageDetail,
      deletePackageRelease,
      deletePackageArtifact,
      onPackageUploadSuccess,
      onPackageUploadError,
      loadDeployWizardArtifacts,
      onDeployPackageReleaseChange,
      onSkipPackageChange,
    };
  }
};
