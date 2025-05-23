(function() {
  // 1. Leemos el <base href="..."> que MkDocs/GitHub Pages pone en el <head>
  const baseHref = document
    .querySelector('base')
    ?.getAttribute('href')  // p. ej. '/documentation_test/'
    || '/';
  const BASE_PATH = baseHref.replace(/\/$/, '');  // quita la slash final

  // 2. Definimos LOGIN_PATH sobre ese BASE_PATH limpio
  const LOGIN_PATH   = `${BASE_PATH}/login/`;    // '/documentation_test/login/' o '/login/'
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
      if (loginButton && spinner) {
        loginButton.classList.add('loading');
        loginButton.disabled = true;
        spinner.classList.remove('sr-only');
      }

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
        const target = sessionStorage.getItem(REDIRECT_KEY) || `${BASE_PATH}/`;
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
        if (loginButton && spinner) {
          loginButton.classList.remove('loading');
          loginButton.disabled = false;
          spinner.classList.add('sr-only');
        }
      }
    });
  }

  async function requireLogin() {
    const { pathname, search } = window.location;

    // Si ya estamos justo en /<base>/login/, arrancamos el form
    if (pathname === LOGIN_PATH) {
      document.documentElement.style.visibility = '';
      return handleLoginForm();
    }

    // Si no hay sesión, guardamos destino y redirigimos
    if (!isSessionValid()) {
      clearSession();
      sessionStorage.setItem(REDIRECT_KEY, pathname + search);
      window.location.replace(LOGIN_PATH);
    } else {
      // refrescamos la hora de la sesión y mostramos contenido
      startSession(localStorage.getItem(STORAGE_KEY));
      document.documentElement.style.visibility = '';
    }
  }

  // Ocultamos todo hasta haber comprobado sesión / login
  document.documentElement.style.visibility = 'hidden';
  requireLogin();
})();
