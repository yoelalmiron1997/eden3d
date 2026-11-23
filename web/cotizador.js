// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Cotizador: cuánto material lleva la pieza y cuánto sale, con el precio del kilo de
// filamento de cada uno (en pesos argentinos o en la moneda que use).
//
// El motor mide las mismas piezas que van al 3MF (volumen y superficie de cada una, con
// su cantidad) y acá se estima lo que pondría un laminador: paredes y tapas macizas y el
// interior con el relleno elegido. Cambiar material, relleno o precio es instantáneo.
//
//   montarCotizador({ dentro: filaDeBotones, pedir: () => call("cotizar", { opts }),
//                     version: () => state.builds, nombre: "chapita" })

export const MATERIALES = [
  { id: "PLA", nombre: "PLA", densidad: 1.24 },
  { id: "PETG", nombre: "PETG", densidad: 1.27 },
  { id: "ABS", nombre: "ABS", densidad: 1.04 },
  { id: "ASA", nombre: "ASA", densidad: 1.07 },
  { id: "TPU", nombre: "TPU (flexible)", densidad: 1.21 },
  { id: "PLA-CF", nombre: "PLA con fibra de carbono", densidad: 1.29 },
  { id: "PETG-CF", nombre: "PETG con fibra de carbono", densidad: 1.30 },
  { id: "PA", nombre: "Nylon (PA)", densidad: 1.14 },
  { id: "PC", nombre: "Policarbonato (PC)", densidad: 1.20 },
  { id: "OTRO", nombre: "Otro (poné la densidad)", densidad: 1.24 },
];

export const MONEDAS = ["ARS", "USD", "EUR", "BRL", "CLP", "COP", "MXN", "PEN", "UYU", "PYG", "BOB", "GBP", "CAD", "AUD"];

// moneda por defecto según el país del navegador
const POR_PAIS = { AR: "ARS", US: "USD", ES: "EUR", BR: "BRL", CL: "CLP", CO: "COP", MX: "MXN", PE: "PEN",
  UY: "UYU", PY: "PYG", BO: "BOB", GB: "GBP", CA: "CAD", AU: "AUD", DE: "EUR", FR: "EUR", IT: "EUR", PT: "EUR" };
function monedaDelPais() {
  for (const l of navigator.languages || [navigator.language || ""]) {
    const m = /-([A-Z]{2})\b/.exec(l || "");
    if (m && POR_PAIS[m[1]]) return POR_PAIS[m[1]];
  }
  return "ARS";
}

const ANCHO_LINEA = 0.42;       // mm, boquilla 0,4
const FILAMENTO_CM3_POR_M = Math.PI * 0.0875 * 0.0875 * 100;   // 1,75 mm: 2,405 cm³ por metro

// Gramos de UNA pieza, como un laminador: las paredes llevan "perimetros" líneas de
// 0,42 mm, los techos 5 capas macizas y los pisos 3 (de 0,2 mm), y el resto del interior
// el relleno elegido. Los factores salen de calibrar contra PrusaSlicer (grilla, capa
// 0,2 mm) con las piezas de todos los generadores: error medio 5 % por pieza y menos de
// 12 % en el total de cada producto; al 100 % coincide con volumen × densidad.
export const K_PARED = 1.4;     // las paredes ocupan algo más que n × ancho de línea (solapes, anclajes)
export const K_TAPAS = 0.85;
export const K_RELLENO = 0.95;
export function gramosPieza(p, { relleno = 15, perimetros = 2, densidad = 1.24 } = {}) {
  const vol = p.volumen_mm3;
  const arriba = p.arriba_mm2 || 0, abajo = p.abajo_mm2 || 0;
  const lados = Math.max(0, p.area_mm2 - arriba - abajo);
  const macizo = Math.min(vol, lados * perimetros * ANCHO_LINEA * K_PARED + (arriba * 5 + abajo * 3) * 0.2 * K_TAPAS);
  const fraccion = relleno >= 100 ? 1 : Math.max(0, relleno) / 100 * K_RELLENO;
  return ((macizo + (vol - macizo) * fraccion) / 1000) * densidad;
}

export function cotizar(datos, cfg) {
  const material = MATERIALES.find((m) => m.id === cfg.material) || MATERIALES[0];
  const densidad = material.id === "OTRO" ? (+cfg.densidad || 1.24) : material.densidad;
  const unidades = Math.max(1, Math.round(+cfg.unidades || 1));
  const extra = 1 + Math.max(0, +cfg.desperdicio || 0) / 100;
  const grupos = new Map();
  const porColor = {};
  let total = 0;
  for (const p of datos.piezas) {
    const g1 = gramosPieza(p, { relleno: +cfg.relleno, perimetros: +cfg.perimetros, densidad }) * extra;
    const g = g1 * p.cantidad * unidades;
    total += g;
    porColor[p.color] = (porColor[p.color] || 0) + g;
    const k = p.grupo || p.nombre;
    const fila = grupos.get(k) || { nombre: k, cantidad: p.cantidad * unidades, gramos: 0, gramosUna: 0 };
    fila.gramos += g;
    fila.gramosUna += g1;
    grupos.set(k, fila);
  }
  const precio = +cfg.precioKg > 0 ? +cfg.precioKg : 0;
  return {
    filas: [...grupos.values()], total, porColor, unidades, densidad,
    metros: total / densidad / FILAMENTO_CM3_POR_M,
    costo: precio ? total / 1000 * precio : null,
    costoUnidad: precio ? total / unidades / 1000 * precio : null,
  };
}

// ------------------------------------------------------------------ configuración guardada
const CLAVE = "tecnobear.cotizador";
function leer() {
  let c = {};
  try { c = JSON.parse(localStorage.getItem(CLAVE) || "{}") || {}; } catch { c = {}; }
  return { material: "PLA", densidad: 1.24, precioKg: "", moneda: monedaDelPais(), relleno: 15, perimetros: 2,
    desperdicio: 5, unidades: 1, ...c };
}
function guardar(c) {
  try { localStorage.setItem(CLAVE, JSON.stringify({ ...c, unidades: 1 })); } catch { /* modo privado */ }
}

function dinero(v, moneda) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: moneda,
      maximumFractionDigits: v >= 100 ? 0 : 2 }).format(v);
  } catch {
    return (v >= 100 ? Math.round(v) : v.toFixed(2)) + " " + moneda;
  }
}
const g1 = (g) => (g >= 100 ? Math.round(g) : g.toFixed(1)).toString().replace(".", ",");

// ------------------------------------------------------------------ interfaz
let estilos = false;
function ponerEstilos() {
  if (estilos) return;
  estilos = true;
  const st = document.createElement("style");
  st.textContent = `
  .cot-box{width:560px;gap:10px}
  .cot-box h2{padding-right:40px}
  .cot-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px}
  .cot-grid label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--muted)}
  .cot-grid label[hidden]{display:none}
  .cot-grid input,.cot-grid select{font:inherit;color:var(--ink);min-width:0;width:100%;box-sizing:border-box}
  .cot-grid input[type=range]{padding:0}
  .cot-precio{display:flex;gap:6px}.cot-precio input{flex:1}.cot-precio select{width:96px;flex:none}
  .cot-res{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
  .cot-total{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
  .cot-total b{font-size:26px;color:var(--ink)}
  .cot-costo{font-size:24px;font-weight:700;color:var(--green)}
  .cot-sub{color:var(--muted);font-size:13px;margin-top:2px}
  .cot-tabla{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
  .cot-tabla td{padding:4px 0;border-top:1px solid var(--line)}.cot-tabla td:last-child{text-align:right;white-space:nowrap}
  .cot-nota{font-size:12px;color:var(--muted);margin:8px 0 0}
  .cot-cargando{color:var(--muted);padding:10px 0}
  .cot-boton{width:100%}
  @media (max-width:520px){.cot-grid{grid-template-columns:1fr}}`;
  document.head.appendChild(st);
}

export function montarCotizador({ dentro, pedir, version, nombre = "pieza" }) {
  if (!dentro) return null;
  ponerEstilos();
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "cot-boton";
  boton.dataset.testid = "btn-cotizar";
  boton.textContent = "Cotizar";
  boton.title = "Cuántos gramos lleva y cuánto sale, con tu precio del kilo de filamento";
  dentro.appendChild(boton);

  const dlg = document.createElement("dialog");
  dlg.className = "modal";
  dlg.dataset.testid = "cotizador";
  const c = leer();
  const opcionesMat = MATERIALES.map((m) => `<option value="${m.id}">${m.nombre}</option>`).join("");
  const opcionesMon = [...new Set([c.moneda, ...MONEDAS])].map((m) => `<option>${m}</option>`).join("") +
    '<option value="__otra">Otra…</option>';
  dlg.innerHTML = `
    <div class="modal-box wide cot-box">
      <button class="modal-x cot-x" type="button" aria-label="Cerrar">×</button>
      <h2>Cotizar ${nombre}</h2>
      <div class="cot-grid">
        <label>Material<select data-c="material" data-testid="cot-material">${opcionesMat}</select></label>
        <label data-densidad hidden>Densidad (g/cm³)<input data-c="densidad" type="number" min="0.5" max="3" step="0.01"></label>
        <label>Precio del kilo
          <span class="cot-precio"><input data-c="precioKg" data-testid="cot-precio" type="number" min="0" step="any" inputmode="decimal" placeholder="ej. 25000">
          <select data-c="moneda" data-testid="cot-moneda">${opcionesMon}</select></span></label>
        <label><span>Relleno: <span data-v="relleno"></span> %</span><input data-c="relleno" data-testid="cot-relleno" type="range" min="0" max="100" step="5"></label>
        <label>Paredes (perímetros)<select data-c="perimetros"><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
        <label>Desperdicio y pruebas (%)<input data-c="desperdicio" type="number" min="0" max="100" step="1"></label>
        <label>Unidades<input data-c="unidades" data-testid="cot-unidades" type="number" min="1" max="1000" step="1"></label>
      </div>
      <div class="cot-res" data-testid="cot-resultado"><div class="cot-cargando">Midiendo las piezas…</div></div>
      <p class="cot-nota">Estimación del filamento (±15 %): el laminador da el número exacto. No incluye la purga
      de los cambios de color (AMS), los soportes ni la luz y el tiempo de máquina.</p>
    </div>`;
  document.body.appendChild(dlg);
  const $ = (s) => dlg.querySelector(s);
  const campos = [...dlg.querySelectorAll("[data-c]")];
  for (const el of campos) el.value = c[el.dataset.c];
  let datos = null, versionMedida = null, error = null, midiendo = false;

  const leerCampos = () => {
    for (const el of campos) c[el.dataset.c] = el.value;
    return c;
  };
  const pintar = () => {
    $("[data-v=relleno]").textContent = c.relleno;
    $("[data-densidad]").hidden = c.material !== "OTRO";
    const res = $("[data-testid=cot-resultado]");
    if (error) { res.innerHTML = `<div class="cot-cargando">${error}</div>`; return; }
    if (!datos) { res.innerHTML = '<div class="cot-cargando">Midiendo las piezas…</div>'; return; }
    const r = cotizar(datos, c);
    estado.ultimo = { ...r, moneda: c.moneda, material: c.material };
    const colores = Object.keys(r.porColor).length > 1
      ? `<div class="cot-sub">Color 1: ${g1(r.porColor[1] || 0)} g · color 2: ${g1(r.porColor[2] || 0)} g</div>` : "";
    const costo = r.costo != null
      ? `<span class="cot-costo" data-testid="cot-costo">${dinero(r.costo, c.moneda)}</span>`
      : '<span class="cot-sub">Poné el precio del kilo para ver el costo</span>';
    const porUnidad = r.costo != null && r.unidades > 1 ? `<div class="cot-sub">${dinero(r.costoUnidad, c.moneda)} cada una</div>` : "";
    const filas = r.filas.length > 1 ? `<table class="cot-tabla">${r.filas.map((f) =>
      `<tr><td>${f.nombre}${f.cantidad > 1 ? ` × ${f.cantidad}` : ""}</td><td>${g1(f.gramos)} g</td></tr>`).join("")}</table>` : "";
    res.innerHTML = `<div class="cot-total"><span><b data-testid="cot-gramos">${g1(r.total)} g</b> de ${
      (MATERIALES.find((m) => m.id === c.material) || {}).nombre || c.material}</span>${costo}</div>
      <div class="cot-sub">≈ ${r.metros.toFixed(1).replace(".", ",")} m de filamento de 1,75 mm</div>${colores}${porUnidad}${filas}
      ${(datos.notas || []).map((n) => `<p class="cot-nota">${n}</p>`).join("")}`;
  };
  const medir = async () => {
    const v = version();
    if (midiendo || (datos && v === versionMedida)) return;
    midiendo = true;
    error = null;
    try {
      const d = await pedir();
      datos = d;
      versionMedida = v;
    } catch (e) {
      error = (e && e.message) || "No se pudo medir la pieza.";
    } finally {
      midiendo = false;
    }
    if (dlg.open) pintar();
    if (dlg.open && version() !== versionMedida) medir();     // cambió mientras medía
  };
  dlg.addEventListener("input", (e) => {
    if (e.target.dataset.c === "moneda" && e.target.value === "__otra") {
      const m = (prompt("Código de la moneda (3 letras, por ejemplo GTQ o DOP):") || "").trim().toUpperCase();
      if (/^[A-Z]{3}$/.test(m)) {
        if (![...e.target.options].some((o) => o.value === m)) e.target.add(new Option(m, m), 0);
        e.target.value = m;
      } else {
        e.target.value = c.moneda;
      }
    }
    leerCampos();
    guardar(c);
    pintar();
  });
  $(".cot-x").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  let reloj = null;
  boton.addEventListener("click", () => {
    if (!dlg.open) dlg.showModal();
    pintar();
    medir();
    clearInterval(reloj);
    reloj = setInterval(() => { if (!dlg.open) clearInterval(reloj); else medir(); }, 800);
  });
  const estado = { boton, dialogo: dlg, ultimo: null, abrir: () => boton.click() };
  return estado;
}
