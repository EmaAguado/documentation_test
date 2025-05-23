(function() {
  // 1) Origen de la web (https://localhost:8000 o https://emaaguado.github.io)
  const ORIGIN = window.location.origin;

  // 2) Base href de MkDocs ("/" en local, "/documentation_test/" en GitHub Pages)
  const rawBase = document.querySelector('base')?.getAttribute('href') || '/';
  //    Lo dejamos sin slash final, para concatenar con seguridad
  const BASE_PATH = rawBase.replace(/\/$/, '');

  // 3) Construimos la URL absoluta de login
  const LOGIN_URL = `${ORIGIN}${BASE_PATH}/login/`;

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

    const loginButton = document.getElementById('login-button');
    const spinner     = document.getElementById('btn-spinner');

    form.addEventListener('submit', async e => {
      e.preventDefault();
      loginButton?.classList.add('loading');
      loginButton && (loginButton.disabled = true);
      spinner?.classList.remove('sr-only');

      const user      = form.user.value;
      const pass      = form.pass.value;
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

        if (!resp.ok) {
          throw new Error(`Error ${resp.status}: ${resp.statusText}`);
        }
        const { access_token: token } = await resp.json();
        if (!token) {
          throw new Error('No se recibió access_token');
        }

        startSession(token);
        const target = sessionStorage.getItem(REDIRECT_KEY) || `${ORIGIN}${BASE_PATH}/`;
        sessionStorage.removeItem(REDIRECT_KEY);
        window.location.replace(target);

      } catch (err) {
        console.error('Login failed:', err);
        const errorDiv = document.getElementById('error');
        if (errorDiv) {
          errorDiv.textContent = 'Usuario o contraseña incorrectos';
          errorDiv.style.display = 'block';
        }
      } finally {
        loginButton?.classList.remove('loading');
        loginButton && (loginButton.disabled = false);
        spinner?.classList.add('sr-only');
      }
    });
  }

  async function requireLogin() {
    const { pathname, search } = window.location;

    // Si estamos ya en la página de login, arrancamos el form
    if (`${ORIGIN}${pathname}` === LOGIN_URL) {
      document.documentElement.style.visibility = '';
      return handleLoginForm();
    }

    // Si no hay sesión válida, guardamos destino y vamos a login
    if (!isSessionValid()) {
      clearSession();
      sessionStorage.setItem(REDIRECT_KEY, pathname + search);
      window.location.replace(LOGIN_URL);
    } else {
      // sesion válida → refrescamos timestamp y mostramos
      startSession(localStorage.getItem(STORAGE_KEY));
      document.documentElement.style.visibility = '';
    }
  }

  // Ocultamos el contenido hasta validar o mostrar form
  document.documentElement.style.visibility = 'hidden';
  requireLogin();
})();
