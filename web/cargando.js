// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Pantalla de carga de cada motor: una impresora 3D (vector propio) imprime la pieza de
// la herramienta capa por capa, con una barra de carga, mientras se baja Python, se carga
// el motor y se arma la primera vista previa (el texto sólo lo leen los lectores de
// pantalla, o se ve si falla). No bloquea clics y se va sola con la vista previa.
//
//   pantallaCarga({ motor: "macetas" | "mate" | "sopa" | "topper", worker, estado })
//
// El worker avisa sus pasos con postMessage({ type: "progreso", paso: 2 }); el estado de
// la página (ready, builds, errors) dice cuándo termina.

const NOMBRES = { macetas: "de macetas", mate: "del mate", sopa: "de la sopa de letras", topper: "del topper", chapita: "de chapitas", trofeo: "de trofeos" };

// la pieza que imprime cada motor: silueta sobre la cama (y = 200), unos 110 mm de alto
const PIEZAS = {
  macetas: `<path d="M104 92h112v13h-6l-14 95h-72l-14-95h-6z"/>`,
  mate: `<path d="M140 92h40c3 7 13 17 19 34 9 26 3 58-17 68l-4 6h-36l-4-6c-20-10-26-42-17-68 6-17 16-27 19-34z"/>`,
  sopa: `<path d="M106 112h42v-6a9 9 0 1 1 18 0v6h42v40h-6a9 9 0 1 0 0 18h6v30H106z"/>`,
  chapita: `<rect x="112" y="160" width="96" height="26"/><circle cx="112" cy="157" r="15"/><circle cx="112" cy="185" r="15"/>
    <circle cx="208" cy="157" r="15"/><circle cx="208" cy="185" r="15"/><path d="M160 136a12 12 0 1 1 0 24 12 12 0 1 1 0-24zm0 6a6 6 0 1 0 0 12 6 6 0 1 0 0-12z" fill-rule="evenodd"/>`,
  trofeo: `<path d="M160 82l9 19 21 3-15 15 4 21-19-10-19 10 4-21-15-15 21-3z"/><rect x="155" y="138" width="10" height="26"/>
    <rect x="122" y="164" width="76" height="24"/><rect x="114" y="186" width="92" height="14"/>`,
  topper: `<path d="M160 146c-30-17-46-30-46-45 0-12 9-20 20-20 11 0 20 7 26 16 6-9 15-16 26-16 11 0 20 8 20 20 0 15-16 28-46 45z"/>
    <rect x="139" y="132" width="7" height="68"/><rect x="174" y="132" width="7" height="68"/>`,
};

function impresora(motor) {
  return `
  <svg class="carga-svg" viewBox="0 0 320 250" role="img" aria-label="Una impresora 3D imprimiendo la pieza">
    <defs>
      <pattern id="carga-capas-${motor}" width="8" height="5" patternUnits="userSpaceOnUse">
        <rect width="8" height="5" class="carga-capa"/><rect y="3.6" width="8" height="1.4" class="carga-capa-junta"/>
      </pattern>
      <clipPath id="carga-recorte-${motor}"><rect class="carga-crece" x="60" y="80" width="200" height="120"/></clipPath>
    </defs>
    <!-- marco -->
    <path class="carga-marco" d="M42 222V24h236v198"/>
    <path class="carga-marco-fino" d="M54 36h212"/>
    <rect class="carga-base" x="30" y="214" width="260" height="14"/>
    <rect class="carga-cama" x="78" y="200" width="164" height="8"/>
    <!-- carrete y tubo del filamento -->
    <circle class="carga-carrete" cx="292" cy="40" r="15"/><circle class="carga-carrete-eje" cx="292" cy="40" r="4"/>
    <path class="carga-tubo" d="M292 55c0 40-60 30-90 46"/>
    <!-- la pieza que se va imprimiendo -->
    <g clip-path="url(#carga-recorte-${motor})">
      <g class="carga-pieza" fill="url(#carga-capas-${motor})">${PIEZAS[motor]}</g>
    </g>
    <!-- el pórtico sube con cada capa; el cabezal va y viene -->
    <g class="carga-portico">
      <rect class="carga-eje" x="42" y="76" width="236" height="6"/>
      <g class="carga-cabezal">
        <rect class="carga-carro" x="-15" y="66" width="30" height="22"/>
        <rect class="carga-ventilador" x="-10" y="70" width="20" height="10"/>
        <path class="carga-pico" d="M-5 88h10l-3 8h-4z"/>
        <circle class="carga-gota" cx="0" cy="98" r="1.6"/>
      </g>
    </g>
  </svg>`;
}

export function pantallaCarga({ motor, worker, estado, contenedor }) {
  const stage = contenedor || document.querySelector(".stage");
  if (!stage || !PIEZAS[motor]) return null;
  const el = document.createElement("div");
  el.className = "carga";
  el.dataset.testid = "carga";
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");
  el.innerHTML = `
    <div class="carga-caja">
      ${impresora(motor)}
      <div class="carga-barra" aria-hidden="true"><span></span></div>
      <p class="carga-titulo">Cargando el motor ${NOMBRES[motor]}</p>
    </div>`;
  stage.appendChild(el);
  const t0 = performance.now();
  let paso = 0, cerrada = false;

  const marcar = (n) => {
    if (n <= paso || cerrada) return;
    paso = n;
    el.dataset.paso = String(n);
    el.querySelector(".carga-barra span").style.width = `${Math.min(100, (n - 1) * 33 + 12)}%`;
  };
  const cerrar = () => {
    if (cerrada) return;
    cerrada = true;
    el.dataset.paso = "4";
    el.querySelector(".carga-barra span").style.width = "100%";
    el.classList.add("carga-lista");          // se desvanece y después se saca del visor
    el.addEventListener("transitionend", () => el.remove(), { once: true });
    setTimeout(() => el.remove(), 700);
  };
  const fallar = (msg) => {
    cerrada = true;
    el.classList.add("carga-error");
    el.querySelector(".carga-titulo").textContent = msg || "No se pudo cargar el motor";
  };

  marcar(1);
  if (worker) {
    worker.addEventListener("message", (ev) => {
      if (ev.data && ev.data.type === "progreso") marcar(ev.data.paso);
    });
  }
  const mirar = () => {
    if (cerrada) return;
    if (estado) {
      if (estado.builds >= 1) return cerrar();
      if (estado.ready) marcar(3);
      const err = document.querySelector("[data-testid=estado].err");
      if (!estado.ready && err && performance.now() - t0 > 300) return fallar(err.textContent);
    }
    setTimeout(mirar, 150);
  };
  mirar();
  return { marcar, cerrar, fallar, el };
}
