// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Modo oscuro (el de la marca, por defecto) o claro: un botón en el encabezado de todas
// las páginas, recordado por navegador.
const KEY = "tb-tema";
const ICON = {
  dark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.5 14.6A8 8 0 0 1 9.4 4.5a8 8 0 1 0 10.1 10.1z" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  light: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" stroke="currentColor" stroke-width="1.6"/></svg>',
};
const TXT = { dark: "Oscuro", light: "Claro" };

// "light" o "dark"; lo guardado de antes como "auto" (o nada) es el oscuro de la marca
export function getTheme() {
  try { return localStorage.getItem(KEY) === "light" ? "light" : "dark"; } catch (e) { return "dark"; }
}

export function setTheme(t) {
  t = t === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem(KEY, t); } catch (e) { /* sin almacenamiento: sólo esta vez */ }
  document.dispatchEvent(new CustomEvent("tema", { detail: t }));
}

// un solo botón: muestra la luna en oscuro y el sol en claro; cada toque cambia
export function mountTheme(host) {
  if (!host) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "tema-btn";
  btn.dataset.testid = "btn-tema";
  const pintar = () => {
    const t = getTheme();
    btn.dataset.tema = t;
    btn.innerHTML = ICON[t];
    const otro = t === "dark" ? "claro" : "oscuro";
    btn.setAttribute("aria-label", `Modo ${TXT[t].toLowerCase()} (cambiar a ${otro})`);
    btn.title = `Cambiar a modo ${otro}`;
  };
  btn.addEventListener("click", () => setTheme(getTheme() === "dark" ? "light" : "dark"));
  document.addEventListener("tema", pintar);
  pintar();
  host.prepend(btn);
}
