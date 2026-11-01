// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Imágenes de perfil prediseñadas: minimalistas, un fondo plano y una figura de un color.
// En el perfil se guardan como "av:<id>" (no pesan nada); una foto subida es un data URL.

const P = {
  lima: ["#c5f05b", "#0b1204"], crema: ["#e9eb9f", "#121a10"], noche: ["#101719", "#c5f05b"],
  noche2: ["#101719", "#e9eb9f"], agua: ["#8fd3c7", "#0d2b27"], coral: ["#f2a48b", "#3a1408"],
  lila: ["#c3b5f2", "#1e1540"], cielo: ["#9cc8f0", "#0e2236"], arena: ["#e6d3b3", "#3a2a12"],
};

function estrella(cx, cy, R, r, n = 5) {
  const pts = [];
  for (let i = 0; i < 2 * n; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / n, k = i % 2 ? r : R;
    pts.push(`${(cx + k * Math.cos(a)).toFixed(2)} ${(cy + k * Math.sin(a)).toFixed(2)}`);
  }
  return `M${pts.join("L")}Z`;
}

function engranaje(cx, cy, R, r, dientes = 8) {
  const pts = [];
  const paso = (Math.PI * 2) / dientes;
  for (let i = 0; i < dientes; i++) {
    const a = i * paso;
    for (const [d, k] of [[-0.3, r], [-0.18, R], [0.18, R], [0.3, r]]) {
      pts.push(`${(cx + k * Math.cos(a + d * paso * 2)).toFixed(2)} ${(cy + k * Math.sin(a + d * paso * 2)).toFixed(2)}`);
    }
  }
  return `M${pts.join("L")}Z`;
}

// cada figura usa G (color de la figura) y B (color del fondo, para los recortes)
const FIGURAS = [
  ["oso", "Oso", "lima", (G, B) => `<circle cx="20.5" cy="21" r="6.5" fill="${G}"/><circle cx="43.5" cy="21" r="6.5" fill="${G}"/>
    <circle cx="32" cy="34" r="15" fill="${G}"/><ellipse cx="32" cy="39.5" rx="6.5" ry="5" fill="${B}"/>
    <ellipse cx="32" cy="37.6" rx="2.6" ry="1.8" fill="${G}"/><circle cx="26" cy="30.5" r="1.9" fill="${B}"/><circle cx="38" cy="30.5" r="1.9" fill="${B}"/>`],
  ["perro", "Perro", "crema", (G, B) => `<rect x="20" y="19" width="24" height="28" rx="12" fill="${G}"/>
    <path d="M21 20c-7 0-9.5 7-8.5 14.5.6 4.5 4.6 5.6 8.5 3.2z" fill="${G}"/><path d="M43 20c7 0 9.5 7 8.5 14.5-.6 4.5-4.6 5.6-8.5 3.2z" fill="${G}"/>
    <circle cx="27" cy="30.5" r="1.9" fill="${B}"/><circle cx="37" cy="30.5" r="1.9" fill="${B}"/><ellipse cx="32" cy="38" rx="3.4" ry="2.4" fill="${B}"/>`],
  ["gato", "Gato", "noche", (G, B) => `<path d="M17 19l8 7.5a15 15 0 0 1 14 0l8-7.5v17a15 13.5 0 0 1-30 0z" fill="${G}"/>
    <ellipse cx="26" cy="34" rx="1.8" ry="2.7" fill="${B}"/><ellipse cx="38" cy="34" rx="1.8" ry="2.7" fill="${B}"/><path d="M29.8 39.5h4.4L32 42z" fill="${B}"/>`],
  ["pata", "Patita", "coral", (G) => `<path d="M32 33.5c-6 0-10.5 6-10.5 10.2 0 3.6 3 5 6.2 4.2 2-.5 2.9-1.3 4.3-1.3s2.3.8 4.3 1.3c3.2.8 6.2-.6 6.2-4.2 0-4.2-4.5-10.2-10.5-10.2z" fill="${G}"/>
    <ellipse cx="19.5" cy="30" rx="3.8" ry="4.9" transform="rotate(-22 19.5 30)" fill="${G}"/><ellipse cx="27" cy="21.5" rx="4" ry="5.2" transform="rotate(-8 27 21.5)" fill="${G}"/>
    <ellipse cx="37" cy="21.5" rx="4" ry="5.2" transform="rotate(8 37 21.5)" fill="${G}"/><ellipse cx="44.5" cy="30" rx="3.8" ry="4.9" transform="rotate(22 44.5 30)" fill="${G}"/>`],
  ["hueso", "Hueso", "cielo", (G) => `<g transform="rotate(-32 32 32)" fill="${G}"><rect x="17" y="27.8" width="30" height="8.4"/>
    <circle cx="17" cy="26.6" r="6.3"/><circle cx="17" cy="37.4" r="6.3"/><circle cx="47" cy="26.6" r="6.3"/><circle cx="47" cy="37.4" r="6.3"/></g>`],
  ["impresora", "Impresora 3D", "noche2", (G) => `<path d="M17.5 15.5h29v33h-29z" fill="none" stroke="${G}" stroke-width="3"/>
    <rect x="17.5" y="22" width="29" height="3" fill="${G}"/><path d="M28.5 25h7v4l-3.5 3.5-3.5-3.5z" fill="${G}"/>
    <rect x="27" y="37" width="10" height="5" fill="${G}"/><rect x="21" y="42.5" width="22" height="3" fill="${G}"/>`],
  ["cubo", "Cubo", "lila", (G) => `<path d="M32 15l15 8.5-15 8.5-15-8.5z" fill="${G}"/><path d="M17 23.5l15 8.5v17l-15-8.5z" fill="${G}" opacity=".72"/>
    <path d="M47 23.5l-15 8.5v17l15-8.5z" fill="${G}" opacity=".45"/>`],
  ["capas", "Capas", "agua", (G) => `<rect x="16" y="40" width="32" height="6" rx="1" fill="${G}"/><rect x="19" y="31.5" width="26" height="6" rx="1" fill="${G}" opacity=".78"/>
    <rect x="22" y="23" width="20" height="6" rx="1" fill="${G}" opacity=".56"/><path d="M29 12h6v4l-3 3-3-3z" fill="${G}"/>`],
  ["planta", "Planta", "arena", (G) => `<path d="M32 36c0-9.5-6.5-16-14-16 0 8.5 5.5 15 14 16z" fill="${G}"/><path d="M32 36c0-7.5 5.5-13 13-13 0 7.5-5.5 13-13 13z" fill="${G}" opacity=".7"/>
    <rect x="21" y="36" width="22" height="4" rx="1" fill="${G}"/><path d="M23.5 40h17l-2.5 9h-12z" fill="${G}"/>`],
  ["mate", "Mate", "lima", (G) => `<path d="M38 26l6.5-13.5" stroke="${G}" stroke-width="2.8" stroke-linecap="round"/>
    <rect x="22.5" y="23" width="19" height="4.5" rx="2" fill="${G}"/><path d="M24 27.5h16c2.4 3.6 5.5 7.4 5.5 13a13.5 13.5 0 0 1-27 0c0-5.6 3.1-9.4 5.5-13z" fill="${G}"/>`],
  ["rayo", "Rayo", "crema", (G) => `<path d="M36 11L19.5 36H30l-3.5 17L44.5 27H33.5z" fill="${G}"/>`],
  ["estrella", "Estrella", "cielo", (G) => `<path d="${estrella(32, 33, 17, 7.4)}" fill="${G}" stroke="${G}" stroke-width="2" stroke-linejoin="round"/>`],
  ["corazon", "Corazón", "coral", (G) => `<path d="M32 48S15.5 38 15.5 26.8A8.8 8.8 0 0 1 32 22.3a8.8 8.8 0 0 1 16.5 4.5C48.5 38 32 48 32 48z" fill="${G}"/>`],
  ["engranaje", "Engranaje", "noche", (G, B) => `<path d="${engranaje(32, 32, 17, 12.5)}" fill="${G}"/><circle cx="32" cy="32" r="5.5" fill="${B}"/>`],
  ["montana", "Montaña", "agua", (G) => `<circle cx="43" cy="21" r="5" fill="${G}" opacity=".6"/><path d="M11 48l15.5-23 8.5 12.5 6-8 12 18.5z" fill="${G}"/>`],
  ["luna", "Luna", "noche2", (G) => `<path d="M37 14a18 18 0 1 0 12 28.5A14.5 14.5 0 0 1 37 14z" fill="${G}"/>
    <path d="${estrella(46, 20, 3.2, 1.3, 4)}" fill="${G}"/><path d="${estrella(50.5, 31, 2.2, .9, 4)}" fill="${G}" opacity=".7"/>`],
];

export const AVATARES = FIGURAS.map(([id, nombre, pal, fig]) => {
  const [B, G] = P[pal];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="${B}"/>${fig(G, B)}</svg>`;
  return { id, nombre, svg };
});

const POR_ID = Object.fromEntries(AVATARES.map((a) => [a.id, a]));

export const esAvatar = (foto) => typeof foto === "string" && /^av:[a-z]+$/.test(foto) && !!POR_ID[foto.slice(3)];

// src para un <img>: la imagen prediseñada (SVG) o la foto subida
export function srcCara(foto) {
  if (esAvatar(foto)) return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(POR_ID[foto.slice(3)].svg);
  return typeof foto === "string" && foto.startsWith("data:image/") ? foto : "";
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// la cara de alguien: su imagen o, si no tiene, sus iniciales
export function caraHTML(foto, iniciales, alt = "") {
  const src = srcCara(foto);
  return src ? `<img src="${esc(src)}" alt="${esc(alt)}">` : `<span>${esc(iniciales || "?")}</span>`;
}
