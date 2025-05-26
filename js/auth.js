(function() {
  const { origin, host, pathname, search } = window.location;

  // Detectamos si estamos en GitHub Pages (ej. "usuario.github.io")
  const onGitHubPages = host.endsWith('.github.io');

  // Si es GH-Pages, el primer segmento de pathname es el repo; si no, no hay base
  const segments = pathname.split('/').filter(Boolean);
  const repoBase  = onGitHubPages && segments.length
    ? `/${segments[0]}`   // "/documentation_test"
    : '';                 // en local, ""

  // Construimos el pathname y la URL completa de login
  const LOGIN_PATHNAME = `${repoBase}/login/`;        // "/login/" o "/documentation_test/login/"
  const LOGIN_URL      = `${origin}${LOGIN_PATHNAME}`;

  const API_TOKEN    = 'https://mondotv-api.herokuapp.com/api/v1/session/token';
  const STORAGE_KEY  = 'mkdocs_auth_token';
  const TIME_KEY     = 'mkdocs_auth_time';
  const REDIRECT_KEY = 'mkdocs_auth_target';
  const SESSION_TTL  = 60 * 60 * 1000; // 1 hora

  function isSessionValid() {
    const token = localStorage.getItem(STORAGE_KEY);
    const ts    = parseInt(localStorage.getItem(TIME_KEY), 10);
    return token && !isNaN(ts) && (Date.now() - ts < SESSION_TTL);
  }

  function startSession(token) {
    localStorage.setItem(STORAGE_KEY, token);
    localStorage.setItem(TIME_KEY, Date.now().toString());
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(TIME_KEY);
  }

  function handleLoginForm() {
    const form = document.getElementById('login-form');
    if (!form) return;

    const btn = document.getElementById('login-button');
    const sp  = document.getElementById('btn-spinner');

    form.addEventListener('submit', async e => {
      e.preventDefault();
      btn?.classList.add('loading');
      if (btn) btn.disabled = true;
      sp?.classList.remove('sr-only');

      const user = form.user.value;
      const pass = form.pass.value;
      const machineId = 'browser-' + navigator.userAgent;
      const basic     = btoa(`${user}:${pass}`);

      try {
        const resp = await fetch(API_TOKEN, {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${basic}`,
            'Content-Type':  'application/json',
            'Accept':        '*/*'
          },
          body: JSON.stringify({ machine_id: machineId })
        });
        if (!resp.ok) throw new Error(`Error ${resp.status}`);

        const { access_token: token } = await resp.json();
        if (!token) throw new Error('No se recibió access_token');

        startSession(token);
        const targetPath = sessionStorage.getItem(REDIRECT_KEY) || `${repoBase}/`;
        sessionStorage.removeItem(REDIRECT_KEY);
        window.location.replace(`${origin}${targetPath}`);

      } catch (err) {
        console.error('Login failed:', err);
        const errDiv = document.getElementById('error');
        if (errDiv) {
          errDiv.textContent = 'Usuario o contraseña incorrectos';
          errDiv.style.display = 'block';
        }
      } finally {
        btn?.classList.remove('loading');
        if (btn) btn.disabled = false;
        sp?.classList.add('sr-only');
      }
    });
  }

  async function requireLogin() {
    // Si ya estamos exactamente en la URL de login, arrancamos el form
    if (pathname === LOGIN_PATHNAME) {
      document.documentElement.style.visibility = '';
      return handleLoginForm();
    }

    // Si no hay sesión, redirigimos a login
    if (!isSessionValid()) {
      clearSession();
      sessionStorage.setItem(REDIRECT_KEY, pathname + search);
      window.location.replace(LOGIN_URL);
    } else {
      // Sesión válida: refrescamos timestamp y mostramos contenido
      startSession(localStorage.getItem(STORAGE_KEY));
      document.documentElement.style.visibility = '';
    }
  }

  // Ocultamos todo hasta validar la sesión o mostrar el login
  document.documentElement.style.visibility = 'hidden';
  requireLogin();
})();
