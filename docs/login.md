<div class="login-container">
  <div class="login-frame">
    <div class="login-banner">
      <img class="login-banner-img" src="/assets/img/login-banner.png" alt="Banner de bienvenida" />
    </div>
    <div class="login-card-wrapper">
      <div class="login-card">
        <!-- <div class="login-header">
          <h1></h1>
        </div> -->
        <form id="login-form" action="/login" method="post">
          <div class="form-group">
            <input type="text" id="user" name="user" required placeholder="User" />
          </div>
          <div class="form-group">
            <input type="password" id="pass" name="pass" required placeholder="Password" />
          </div>
          <button type="submit" class="md-button" id="login-button">
            <span class="btn-text">Login</span>
            <span class="btn-spinner sr-only" id="btn-spinner"></span>
          </button>
        </form>
        <div id="error" class="error-message">Incorrect username or password.</div>
      </div>
    </div>
  </div>
</di
