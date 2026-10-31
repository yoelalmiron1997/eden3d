// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Funciones Premium (cuenta Pro): el render (Foto) y el PDF con consideraciones de
// impresión. Con una cuenta gratis el botón muestra "Pro" y al tocarlo explica el plan.
import { onAuth } from "./auth.js";
import { openLogin } from "./auth-ui.js";

const INSTAGRAM = "https://www.instagram.com/tecnobearr/";
let dlg = null;

function dialogo() {
  if (dlg) return dlg;
  dlg = document.createElement("dialog");
  dlg.className = "modal";
  dlg.dataset.testid = "premium";
  dlg.innerHTML = `
    <div class="modal-box">
      <button type="button" class="modal-x" aria-label="Cerrar" data-close>×</button>
      <h2>Premium <span class="badge-pro">Pro</span></h2>
      <p id="premium-que"></p>
      <ul class="tm-list">
        <li>Render de tus piezas para mandarle al cliente</li>
        <li>PDF con las consideraciones de impresión</li>
        <li>Sin marca de agua y actualizaciones más directas</li>
        <li>Colecciones preseteadas (próximamente)</li>
      </ul>
      <div class="tm-actions">
        <a class="btn primary" href="${INSTAGRAM}" target="_blank" rel="noopener noreferrer" data-testid="premium-quiero">Quiero Premium</a>
        <a class="btn" href="./#planes" data-testid="premium-planes">Ver planes</a>
      </div>
      <p class="muted small" id="premium-login" hidden>¿Ya tenés Premium? <button type="button" class="link" data-testid="premium-ingresar">Ingresá con tu cuenta</button></p>
    </div>`;
  document.body.appendChild(dlg);
  dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  dlg.querySelector("[data-testid=premium-ingresar]").addEventListener("click", () => { dlg.close(); openLogin("Ingresá con tu cuenta Premium."); });
  return dlg;
}

export function pedirPremium(que, auth) {
  const d = dialogo();
  d.querySelector("#premium-que").textContent = `${que} es parte del plan Premium para la comunidad.`;
  d.querySelector("#premium-login").hidden = !!(auth && auth.user);
  d.showModal();
}

// botones: [{ el, que, accion }] — con Premium hace la acción; sin Premium, explica el plan
export function botonesPremium(estado, botones) {
  for (const b of botones) {
    if (!b.el) continue;
    const marca = document.createElement("span");
    marca.className = "badge-pro";
    marca.textContent = "Pro";
    marca.hidden = true;
    b.el.append(" ", marca);
    b.el.addEventListener("click", () => {
      if (estado.auth && !estado.auth.perms.premium) pedirPremium(b.que, estado.auth);
      else b.accion();
    });
  }
  onAuth((a) => {
    for (const b of botones) if (b.el) b.el.querySelector(".badge-pro").hidden = !!a.perms.premium;
  });
}
