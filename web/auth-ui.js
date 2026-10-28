// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Botón de cuenta del encabezado y ventana de ingreso / registro.
import { initAuth, onAuth, signIn, signUp, signOut, resetPassword, ROLES } from "./auth.js";
import { mountTheme } from "./theme.js";

const RAIZ = new URL("./", import.meta.url).href;

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let dialog;

function buildDialog() {
  dialog = document.createElement("dialog");
  dialog.className = "modal";
  dialog.dataset.testid = "login";
  dialog.innerHTML = `
    <form method="dialog" class="modal-box" id="login-form">
      <button type="button" class="modal-x" aria-label="Cerrar" data-close>×</button>
      <h2 id="login-title">Ingresar</h2>
      <p class="muted small" id="login-why"></p>
      <label>Email <input type="email" name="email" autocomplete="email" required data-testid="login-email"></label>
      <label>Contraseña <input type="password" name="pass" autocomplete="current-password" minlength="6" required data-testid="login-pass"></label>
      <p class="login-msg" id="login-msg" role="alert"></p>
      <button type="submit" class="primary" data-testid="login-ok" id="login-ok">Ingresar</button>
      <div class="login-alt">
        <button type="button" class="link" id="login-toggle">Crear cuenta</button>
        <button type="button" class="link" id="login-reset">Olvidé la contraseña</button>
      </div>
    </form>`;
  document.body.appendChild(dialog);
  let mode = "in";
  const $ = (id) => dialog.querySelector("#" + id);
  const setMode = (m) => {
    mode = m;
    $("login-title").textContent = m === "in" ? "Ingresar" : "Crear cuenta";
    $("login-ok").textContent = m === "in" ? "Ingresar" : "Crear cuenta";
    $("login-toggle").textContent = m === "in" ? "Crear cuenta" : "Ya tengo cuenta";
    dialog.querySelector("[name=pass]").autocomplete = m === "in" ? "current-password" : "new-password";
    $("login-msg").textContent = "";
  };
  $("login-toggle").addEventListener("click", () => setMode(mode === "in" ? "up" : "in"));
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  $("login-reset").addEventListener("click", async () => {
    const email = dialog.querySelector("[name=email]").value.trim();
    if (!email) { $("login-msg").textContent = "Escribí tu email primero."; return; }
    try { await resetPassword(email); $("login-msg").textContent = "Te mandamos un email para cambiarla."; }
    catch (e) { $("login-msg").textContent = e.message; }
  });
  $("login-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const email = dialog.querySelector("[name=email]").value.trim();
    const pass = dialog.querySelector("[name=pass]").value;
    $("login-ok").disabled = true;
    $("login-msg").textContent = "";
    try {
      if (mode === "in") { await signIn(email, pass); dialog.close(); }
      else {
        const r = await signUp(email, pass);
        if (r && r.confirm) $("login-msg").textContent = "Listo: confirmá tu email con el link que te mandamos y después ingresá.";
        else dialog.close();
      }
    } catch (e) {
      $("login-msg").textContent = e.message;
    } finally {
      $("login-ok").disabled = false;
    }
  });
  dialog.setMode = setMode;
}

export function openLogin(why = "") {
  if (!dialog) buildDialog();
  dialog.querySelector("#login-why").textContent = why;
  dialog.setMode("in");
  dialog.showModal();
}

// host: elemento del encabezado donde va el botón de cuenta
export function mountAccount(host) {
  if (!host) return;
  const theme = document.createElement("span");
  host.before(theme);
  mountTheme(theme);
  onAuth((a) => {
    // Calidad, specs y cobertura: sólo para administradores
    document.documentElement.classList.toggle("es-admin", !!a.perms.admin);
    if (!a.configured) { host.innerHTML = ""; return; }
    if (!a.user) {
      host.innerHTML = `<button type="button" class="acc-btn" data-testid="btn-ingresar">Ingresar</button>`;
      host.querySelector("button").addEventListener("click", () => openLogin());
      return;
    }
    host.innerHTML = `
      ${a.perms.admin ? `<a href="${RAIZ}admin.html" class="acc-link" data-testid="link-admin">Admin</a>` : ""}
      <span class="acc-chip" title="${esc(a.user.email)}"><span class="acc-mail">${esc(a.user.email)}</span>
        <span class="role role-${a.role}" data-testid="rol">${ROLES[a.role].label}</span></span>
      <button type="button" class="acc-btn ghost" data-testid="btn-salir">Salir</button>`;
    host.querySelector("[data-testid=btn-salir]").addEventListener("click", () => signOut());
  });
  initAuth();
}
