// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Modo oscuro (el de la marca, por defecto) o claro, a la vista en el encabezado de todas
// las páginas y recordado por navegador.
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

export function mountTheme(host) {
  if (!host) return;
  const grupo = document.createElement("div");
  grupo.className = "tema-sel";
  grupo.setAttribute("role", "group");
  grupo.setAttribute("aria-label", "Tema de la página");
  grupo.dataset.testid = "btn-tema";
  grupo.innerHTML = ["dark", "light"].map((t) => `
    <button type="button" data-modo="${t}" data-testid="tema-${t === "dark" ? "oscuro" : "claro"}" aria-pressed="false">
      ${ICON[t]}<span>${TXT[t]}</span></button>`).join("");
  const pintar = () => {
    const actual = getTheme();
    grupo.dataset.tema = actual;
    for (const b of grupo.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.modo === actual));
  };
  grupo.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-modo]");
    if (b) setTheme(b.dataset.modo);
  });
  document.addEventListener("tema", pintar);
  pintar();
  host.prepend(grupo);
}
