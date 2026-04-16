window.TPOPSAuth = {
  createAuthModule(refs, shared, pageState) {
    const { ref } = refs;
    const token = ref(localStorage.getItem('access') || '');
    const refresh = ref(localStorage.getItem('refresh') || '');
    const user = ref(JSON.parse(localStorage.getItem('user') || '{}'));
    let loaders = {
      fetchHosts: async () => {},
      fetchTasks: async () => {},
      fetchPackageReleases: async () => {},
      resetRuntimeState: () => {},
    };

    function bindLoaders(next) {
      loaders = Object.assign(loaders, next || {});
    }

    function setAuth(access, refToken, nextUser) {
      token.value = access || '';
      refresh.value = refToken || '';
      if (access) localStorage.setItem('access', access); else localStorage.removeItem('access');
      if (refToken) localStorage.setItem('refresh', refToken); else localStorage.removeItem('refresh');
      if (nextUser) {
        user.value = nextUser;
        localStorage.setItem('user', JSON.stringify(nextUser));
      } else {
        user.value = {};
        localStorage.removeItem('user');
      }
    }

    function configureApi() {
      shared.api.interceptors.request.use((cfg) => {
        if (token.value) cfg.headers.Authorization = 'Bearer ' + token.value;
        return cfg;
      });
      shared.api.interceptors.response.use((r) => r, async (err) => {
        const orig = err.config || {};
        if (err.response && err.response.status === 401 && refresh.value && !orig._retry) {
          orig._retry = true;
          try {
            const result = await axios.post('/api/auth/token/refresh/', { refresh: refresh.value });
            setAuth(result.data.access, refresh.value, user.value);
            orig.headers = orig.headers || {};
            orig.headers.Authorization = 'Bearer ' + token.value;
            return shared.api(orig);
          } catch (_) {
            setAuth('', '', null);
          }
        }
        return Promise.reject(err);
      });
    }

    async function doLogin() {
      shared.loading.value = true;
      try {
        const result = await shared.api.post('/auth/login/', shared.loginForm);
        setAuth(result.data.token.access, result.data.token.refresh, result.data.user);
        ElementPlus.ElMessage.success('登录成功');
        pageState.activeMenu.value = 'overview';
        pageState.syncHashFromState(true);
        await loaders.fetchHosts();
        await loaders.fetchTasks();
        await loaders.fetchPackageReleases();
      } catch (e) {
        ElementPlus.ElMessage.error((e.response && e.response.data && e.response.data.detail) || '登录失败');
      } finally {
        shared.loading.value = false;
      }
    }

    async function doRegister() {
      shared.loading.value = true;
      try {
        await shared.api.post('/auth/register/', shared.regForm);
        ElementPlus.ElMessage.success('注册成功，请登录');
        shared.showRegister.value = false;
      } catch (_) {
        ElementPlus.ElMessage.error('注册失败');
      } finally {
        shared.loading.value = false;
      }
    }

    function logout() {
      loaders.resetRuntimeState();
      setAuth('', '', null);
    }

    return { token, refresh, user, bindLoaders, setAuth, configureApi, doLogin, doRegister, logout };
  }
};
