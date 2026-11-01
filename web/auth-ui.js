// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Botón de cuenta del encabezado y ventana de ingreso / registro.
import { initAuth, onAuth, signIn, signUp, signOut, resetPassword, ROLES, perfil, guardarPerfil } from "./auth.js";
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

// mode: "in" (ingresar) o "up" (crear cuenta)
export function openLogin(why = "", mode = "in") {
  if (!dialog) buildDialog();
  dialog.querySelector("#login-why").textContent = why;
  dialog.setMode(mode === "up" ? "up" : "in");
  dialog.showModal();
}

// ---------------------------------------------------------------- perfil
let dlgPerfil;

// la foto se achica a 96 × 96 (recorte cuadrado al centro) para que pese pocos KB
function achicarFoto(file) {
  return new Promise((res, rej) => {
    if (!file || !/^image\//.test(file.type)) return rej(new Error("Elegí una imagen (JPG, PNG o WebP)."));
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = c.height = 96;
      const k = Math.min(img.width, img.height);
      c.getContext("2d").drawImage(img, (img.width - k) / 2, (img.height - k) / 2, k, k, 0, 0, 96, 96);
      URL.revokeObjectURL(img.src);
      res(c.toDataURL("image/jpeg", 0.82));
    };
    img.onerror = () => rej(new Error("No se pudo leer la imagen."));
    img.src = URL.createObjectURL(file);
  });
}

function abrirPerfil() {
  if (!dlgPerfil) {
    dlgPerfil = document.createElement("dialog");
    dlgPerfil.className = "modal";
    dlgPerfil.dataset.testid = "perfil";
    dlgPerfil.innerHTML = `
      <form method="dialog" class="modal-box perfil-form">
        <button type="button" class="modal-x" aria-label="Cerrar" data-close>×</button>
        <h2>Mi perfil</h2>
        <div class="perfil-foto">
          <span class="perfil-cara" id="perfil-cara"></span>
          <label class="btn">Cambiar foto <input type="file" accept="image/*" data-testid="perfil-foto" hidden></label>
          <button type="button" class="link" id="perfil-sin-foto">Quitar</button>
        </div>
        <div class="row2">
          <label>Nombre <input type="text" name="nombre" maxlength="40" autocomplete="given-name" data-testid="perfil-nombre"></label>
          <label>Apellido <input type="text" name="apellido" maxlength="40" autocomplete="family-name" data-testid="perfil-apellido"></label>
        </div>
        <label>Fecha de nacimiento <input type="date" name="nacimiento" autocomplete="bday" data-testid="perfil-nacimiento"></label>
        <p class="login-msg" id="perfil-msg" role="alert"></p>
        <button type="submit" class="primary" data-testid="perfil-guardar">Guardar</button>
      </form>`;
    document.body.appendChild(dlgPerfil);
    dlgPerfil.querySelector("[data-close]").addEventListener("click", () => dlgPerfil.close());
    const q = (sel) => dlgPerfil.querySelector(sel);
    q("[data-testid=perfil-foto]").addEventListener("change", async (e) => {
      try { dlgPerfil.foto = await achicarFoto(e.target.files[0]); pintarCara(); q("#perfil-msg").textContent = ""; }
      catch (err) { q("#perfil-msg").textContent = err.message; }
    });
    q("#perfil-sin-foto").addEventListener("click", () => { dlgPerfil.foto = ""; pintarCara(); });
    q("form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const ok = q("[data-testid=perfil-guardar]");
      ok.disabled = true;
      try {
        await guardarPerfil({ nombre: q("[name=nombre]").value, apellido: q("[name=apellido]").value,
          nacimiento: q("[name=nacimiento]").value, foto: dlgPerfil.foto });
        dlgPerfil.close();
      } catch (err) { q("#perfil-msg").textContent = err.message; }
      finally { ok.disabled = false; }
    });
  }
  const p = perfil();
  const q = (sel) => dlgPerfil.querySelector(sel);
  q("[name=nombre]").value = p.nombre;
  q("[name=apellido]").value = p.apellido;
  q("[name=nacimiento]").value = p.nacimiento;
  q("[name=nacimiento]").max = new Date().toISOString().slice(0, 10);
  q("#perfil-msg").textContent = "";
  dlgPerfil.foto = p.foto;
  pintarCara();
  dlgPerfil.showModal();
}

function pintarCara() {
  const cara = dlgPerfil.querySelector("#perfil-cara");
  cara.innerHTML = dlgPerfil.foto ? `<img src="${esc(dlgPerfil.foto)}" alt="Tu foto">` : "<span>Sin foto</span>";
  dlgPerfil.querySelector("#perfil-sin-foto").hidden = !dlgPerfil.foto;
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
    const p = perfil();
    const nombre = [p.nombre, p.apellido].filter(Boolean).join(" ");
    // con nombre: sus iniciales; sin nombre: la primera letra del email
    const iniciales = nombre ? nombre.split(/\s+/).slice(0, 2).map((w) => w[0].toUpperCase()).join("") : a.user.email[0].toUpperCase();
    const cara = p.foto ? `<img src="${esc(p.foto)}" alt="">` : `<span>${esc(iniciales)}</span>`;
    host.innerHTML = `
      <div class="cuenta">
        <button type="button" class="cuenta-btn" data-testid="btn-cuenta" aria-haspopup="menu" aria-expanded="false"
          aria-label="Tu cuenta: ${esc(nombre || a.user.email)}">${cara}</button>
        <div class="cuenta-menu" role="menu" hidden data-testid="menu-cuenta">
          <div class="cuenta-quien">
            <strong>${esc(nombre || "Tu cuenta")}</strong>
            <span class="acc-mail">${esc(a.user.email)}</span>
            <span class="role role-${a.role}" data-testid="rol">${ROLES[a.role].label}</span>
          </div>
          <button type="button" role="menuitem" data-testid="btn-perfil">Mi perfil</button>
          ${a.perms.admin ? `<a role="menuitem" href="${RAIZ}admin.html" data-testid="link-admin">Administración</a>` : ""}
          <button type="button" role="menuitem" data-testid="btn-salir">Salir</button>
        </div>
      </div>`;
    const btn = host.querySelector(".cuenta-btn"), menu = host.querySelector(".cuenta-menu");
    const abrir = (on) => { menu.hidden = !on; btn.setAttribute("aria-expanded", String(on)); };
    btn.addEventListener("click", (e) => { e.stopPropagation(); abrir(menu.hidden); });
    if (host._fuera) host._fuera.abort();             // un solo juego de oyentes por encabezado
    host._fuera = new AbortController();
    const signal = host._fuera.signal;
    document.addEventListener("click", (e) => { if (!host.contains(e.target)) abrir(false); }, { signal });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) { abrir(false); btn.focus(); } }, { signal });
    host.querySelector("[data-testid=btn-perfil]").addEventListener("click", () => { abrir(false); abrirPerfil(); });
    host.querySelector("[data-testid=btn-salir]").addEventListener("click", () => { abrir(false); signOut(); });
  });
  initAuth();
}
