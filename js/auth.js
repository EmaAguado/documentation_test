(async function() {
  const { origin, host, pathname, search } = window.location;
  const onGitHubPages = host.endsWith('.github.io');
  const segments = pathname.split('/').filter(Boolean);
  const repoBase = onGitHubPages && segments.length ? `/${segments[0]}` : '';

  const LOGIN_PATH = `${repoBase}/login/`;
  const LOGIN_URL = `${origin}${LOGIN_PATH}`;
  const API_TOKEN_URL = 'https://mondotv-api.herokuapp.com/api/v1/session/token';
  const API_ROLE_URL = 'https://mondotv-api.herokuapp.com/api/v1/session/roles';

  const STORAGE_TOKEN = 'mkdocs_auth_token';
  const STORAGE_TIME = 'mkdocs_auth_time';
  const STORAGE_REDIRECT = 'mkdocs_auth_target';
  const STORAGE_ROLES = 'mkdocs_user_roles';

  const SESSION_TTL = 3600 * 1000;
  const ALLOWED = new Set(['admin', 'dev']);

  function isValid() {
    const t = localStorage.getItem(STORAGE_TOKEN);
    const ts = Number(localStorage.getItem(STORAGE_TIME));
    return t && !isNaN(ts) && Date.now() - ts < SESSION_TTL;
  }

  function saveSession(token) {
    localStorage.setItem(STORAGE_TOKEN, token);
    localStorage.setItem(STORAGE_TIME, Date.now().toString());
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_TOKEN);
    localStorage.removeItem(STORAGE_TIME);
    localStorage.removeItem(STORAGE_ROLES);
  }

  function getToken() {
    return localStorage.getItem(STORAGE_TOKEN) || '';
  }

  async function fetchRoles() {
    const resp = await fetch(API_ROLE_URL, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    });
    if (!resp.ok) throw new Error(`Status ${resp.status}`);
    const data = await resp.json();
    // espera { roles: "admin" }
    const r = data.roles;
    return Array.isArray(r) ? r : [r];
  }

  function hideInternal(permitted) {
    document.querySelectorAll('.md-tabs a').forEach(a => {
      if (a.textContent.trim() === 'Dev Guide Internal' && !permitted) {
        a.parentElement.style.display = 'none';
      }
    });
  }

  function deny() {
    document.documentElement.style.visibility = '';
    document.body.innerHTML =
      '<div style="padding:2rem; text-align:center;">' +
      '<h1>Acceso Denegado</h1><p>No tienes permiso.</p></div>';
  }

  function setupLogin() {
    const form = document.getElementById('login-form');
    if (!form) return;
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = document.getElementById('login-button');
      const spinner = document.getElementById('btn-spinner');
      btn.disabled = true;
      spinner.classList.remove('sr-only');

      const user = form.user.value;
      const pass = form.pass.value;
      const basic = btoa(`${user}:${pass}`);

      try {
        const resp = await fetch(API_TOKEN_URL, {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${basic}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ machine_id: 'browser-' + navigator.userAgent })
        });
        if (!resp.ok) throw new Error();
        const { access_token: token } = await resp.json();
        saveSession(token);
        const target = sessionStorage.getItem(STORAGE_REDIRECT) || `${repoBase}/`;
        sessionStorage.removeItem(STORAGE_REDIRECT);
        window.location.replace(origin + target);
      } catch {
        document.getElementById('error').textContent = 'Credenciales inválidas';
        document.getElementById('error').style.display = 'block';
      } finally {
        btn.disabled = false;
        spinner.classList.add('sr-only');
      }
    });
  }

  document.documentElement.style.visibility = 'hidden';

  async function init() {
    if (pathname === LOGIN_PATH) {
      document.documentElement.style.visibility = '';
      return setupLogin();
    }

    if (!isValid()) {
      clearSession();
      sessionStorage.setItem(STORAGE_REDIRECT, pathname + search);
      return window.location.replace(LOGIN_URL);
    }

    saveSession(getToken());

    let roles = [];
    try {
      roles = await fetchRoles();
      localStorage.setItem(STORAGE_ROLES, JSON.stringify(roles));
    } catch {}
    const ok = roles.some(r => ALLOWED.has(r));

    if (pathname.includes('/internal/') && !ok) return deny();

    document.documentElement.style.visibility = '';
    hideInternal(ok);
  }

  await init();
})();