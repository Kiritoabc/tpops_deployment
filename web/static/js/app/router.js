window.TPOPSRouter = (function () {
  function normalizeMenu(menu) {
    if (menu === 'hosts' || menu === 'deploy' || menu === 'packages') return menu;
    return 'overview';
  }

  function normalizeSubView(menu, value) {
    if (menu === 'hosts') return value === 'form' ? 'form' : 'list';
    if (menu === 'deploy') {
      if (value === 'wizard' || value === 'monitor') return value;
      return 'list';
    }
    if (menu === 'packages') {
      if (value === 'form' || value === 'detail') return value;
      return 'list';
    }
    return '';
  }

  function parseHash(hash) {
    var raw = String(hash || '').replace(/^#/, '');
    var parts = raw.split('/').filter(Boolean);
    var menu = normalizeMenu(parts[0] || 'overview');
    return {
      menu: menu,
      hostSubView: normalizeSubView('hosts', parts[1]),
      deploySubView: normalizeSubView('deploy', parts[1]),
      packageSubView: normalizeSubView('packages', parts[1]),
      deployTaskId: menu === 'deploy' && parts[1] === 'monitor' ? parseInt(parts[2], 10) || null : null,
      packageReleaseId: menu === 'packages' && parts[1] === 'detail' ? parseInt(parts[2], 10) || null : null,
    };
  }

  function buildHash(state) {
    var menu = normalizeMenu(state && state.menu);
    if (menu === 'hosts') return '#/hosts/' + normalizeSubView('hosts', state && state.hostSubView);
    if (menu === 'deploy') {
      var deploySubView = normalizeSubView('deploy', state && state.deploySubView);
      if (deploySubView === 'monitor' && state && state.deployTaskId) return '#/deploy/monitor/' + state.deployTaskId;
      return '#/deploy/' + deploySubView;
    }
    if (menu === 'packages') {
      var packageSubView = normalizeSubView('packages', state && state.packageSubView);
      if (packageSubView === 'detail' && state && state.packageReleaseId) return '#/packages/detail/' + state.packageReleaseId;
      return '#/packages/' + packageSubView;
    }
    return '#/overview';
  }

  return { parseHash: parseHash, buildHash: buildHash };
})();
