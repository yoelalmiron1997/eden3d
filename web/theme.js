// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Modo claro / oscuro: automático (el del sistema), claro u oscuro, recordado por navegador.
const KEY = "tb-tema";
const ORDEN = ["auto", "light", "dark"];
const TXT = { auto: "Tema automático", light: "Modo claro", dark: "Modo oscuro" };
const ICON = {
  auto: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/></svg>',
  light: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></g></svg>',
  dark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" fill="currentColor"/></svg>',
};

export function getTheme() {
  try { const t = localStorage.getItem(KEY); return ORDEN.includes(t) ? t : "auto"; } catch (e) { return "auto"; }
}

export function setTheme(t) {
  const r = document.documentElement;
  if (t === "light" || t === "dark") r.dataset.theme = t;
  else delete r.dataset.theme;
  try { localStorage.setItem(KEY, t); } catch (e) { /* sin almacenamiento: sólo esta vez */ }
  document.dispatchEvent(new CustomEvent("tema", { detail: t }));
}

export function mountTheme(host) {
  if (!host) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "theme-btn";
  btn.dataset.testid = "btn-tema";
  const paint = () => {
    const t = getTheme();
    btn.innerHTML = ICON[t];
    btn.title = TXT[t] + " (tocá para cambiar)";
    btn.setAttribute("aria-label", TXT[t]);
    btn.dataset.tema = t;
  };
  btn.addEventListener("click", () => {
    setTheme(ORDEN[(ORDEN.indexOf(getTheme()) + 1) % ORDEN.length]);
    paint();
  });
  paint();
  host.prepend(btn);
}
