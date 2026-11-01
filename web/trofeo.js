// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// "Trofeos para eventos": una figura (estrella, copa, llama, rayo, hojas, pelota o un número)
// parada sobre una base con el texto del evento. Dos piezas que encastran, listas para imprimir.
import * as THREE from "three";
import { pantallaCarga } from "./cargando.js";
import { botonesPremium } from "./premium.js";
import { pdfConsideraciones } from "./guia-impresion.js";
import { Viewer, SCENES } from "./viewer.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// estado visible para los tests e2e (window.__trofeo)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  auth: null, scene: "estudio", figura: "estrella" };
window.__trofeo = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("trofeo-worker.js");
pantallaCarga({ motor: "trofeo", worker, estado: state });
let seq = 0;
const pending = new Map();
worker.onmessage = (ev) => {
  const { id, ok, result, error } = ev.data;
  const p = pending.get(id);
  if (!p) return;
  pending.delete(id);
  ok ? p.resolve(result) : p.reject(new Error(error));
};
function call(type, payload = {}) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, ...payload });
  });
}

const viewer = new Viewer($("viewer"));
viewer.viewDist = 1.3;
const mat = (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0, side: THREE.DoubleSide });
viewer.mats.FIGURA = mat(0xd4a537);
viewer.mats.DETALLE = mat(0xd4a537);
viewer.mats.BASE = mat(0x1f1f1f);
viewer.mats.TEXTO = mat(0xd4a537);
window.__trofeoViewer = viewer;

// normales con quiebre: cada triángulo promedia sólo con los vecinos que doblan menos de
// 40° (las caras planas quedan planas y las paredes curvas, lisas)
const QUIEBRE = Math.cos(THREE.MathUtils.degToRad(40));
viewer.geom = (p) => {
  const P = new Float32Array(p.positions), I = new Uint32Array(p.indices);
  const nt = I.length / 3, N = new Float32Array(I.length);
  const porVertice = new Map();
  for (let t = 0; t < nt; t++) {
    const [a, b, c] = [I[3 * t], I[3 * t + 1], I[3 * t + 2]];
    const ux = P[3 * b] - P[3 * a], uy = P[3 * b + 1] - P[3 * a + 1], uz = P[3 * b + 2] - P[3 * a + 2];
    const wx = P[3 * c] - P[3 * a], wy = P[3 * c + 1] - P[3 * a + 1], wz = P[3 * c + 2] - P[3 * a + 2];
    const nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
    N[3 * t] = nx; N[3 * t + 1] = ny; N[3 * t + 2] = nz;     // con el área como peso
    for (const v of [a, b, c]) { let l = porVertice.get(v); if (!l) porVertice.set(v, l = []); l.push(t); }
  }
  const unit = (t) => { const l = Math.hypot(N[3 * t], N[3 * t + 1], N[3 * t + 2]) || 1; return [N[3 * t] / l, N[3 * t + 1] / l, N[3 * t + 2] / l]; };
  const pos = [], nor = [], idx = [], mapa = new Map();
  for (let t = 0; t < nt; t++) {
    const nt0 = unit(t);
    for (let k = 0; k < 3; k++) {
      const v = I[3 * t + k];
      let sx = 0, sy = 0, sz = 0;
      for (const u of porVertice.get(v)) {
        const n = unit(u);
        if (n[0] * nt0[0] + n[1] * nt0[1] + n[2] * nt0[2] >= QUIEBRE) { sx += N[3 * u]; sy += N[3 * u + 1]; sz += N[3 * u + 2]; }
      }
      const l = Math.hypot(sx, sy, sz) || 1;
      const nx = sx / l, ny = sy / l, nz = sz / l;
      const key = v + "|" + Math.round(nx * 50) + "," + Math.round(ny * 50) + "," + Math.round(nz * 50);
      let j = mapa.get(key);
      if (j === undefined) {
        j = pos.length / 3; mapa.set(key, j);
        pos.push(P[3 * v], P[3 * v + 1], P[3 * v + 2]); nor.push(nx, ny, nz);
      }
      idx.push(j);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute("normal", new THREE.BufferAttribute(new Float32Array(nor), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(idx), 1));
  return g;
};
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.model.children.filter((m) => m.isMesh).map((m) => m.name), triangles: viewer.triangles,
  figura: "#" + viewer.mats.FIGURA.color.getHexString(), base: "#" + viewer.mats.BASE.color.getHexString(),
  metal: viewer.mats.FIGURA.metalness,
}) });

// ------------------------------------------------------------------ opciones
const SL = { alto: [0, " mm"], tallo: [0, " mm"], grosor: [1, " mm"], base_ancho: [0, " mm"], base_alto: [0, " mm"],
  base_fondo: [0, " mm"], borde: [1, " mm"], relieve: [1, " mm"], holgura: [2, " mm"] };

function opts() {
  const o = { figura: state.figura, caracter: $("caracter").value.trim(), texto_figura: $("texto_figura").value.trim(),
    fuente_figura: $("fuente_figura").value, linea1: $("linea1").value.trim(), linea2: $("linea2").value.trim(),
    fuente: $("fuente").value, base: $("base").value, texto: $("texto").value, colores: $("colores").value };
  for (const k of Object.keys(SL)) o[k] = +$(k).value;
  return o;
}

function setStatus(text, kind = "") {
  const s = document.querySelector("[data-testid=estado]");
  s.textContent = text;
  s.className = "status " + kind;
}

const DESCARGAS = ["dl3mf", "dlfigura", "dlbase", "dldetalle", "dltexto", "photo", "pdf"];
function setBusy(on, text = "Calculando…") {
  state.busy = on;
  $("busy").hidden = !on;
  $("busy-text").textContent = text;
  const ok = !on && state.ready && !!state.summary?.valid;
  $("build").disabled = on || !state.ready;
  for (const id of DESCARGAS) $(id).disabled = !ok;
}

const mm3 = (a) => `${Math.round(a[0])} × ${Math.round(a[1])} × ${Math.round(a[2])} mm`;

function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Trofeo", mm3(s.medidas_mm), "f-medidas"],
    ["Figura", `${Math.round(s.figura_mm[0])} × ${Math.round(s.figura_mm[1])} mm · ${num(s.figura_mm[2])} mm de grosor`, "f-figura"],
    ["Base", mm3(s.base_mm), "f-base"],
    ["Encastre", `espiga ${Math.round(s.espiga_mm[0])} × ${num(s.espiga_mm[1])} mm · ${num(s.holgura_mm, 2)} mm de juego`, "f-encastre"],
    ["Texto", `${num(s.letra_base_mm)} mm de alto · ${s.texto === "grabado" ? "grabado" : "en relieve"} ${num(s.relieve_mm)} mm`, "f-texto"],
    ...(s.texto_figura ? [["En la figura", `«${esc(s.texto_figura)}» de ${num(s.letra_figura_mm)} mm`, "f-texto-figura"]] : []),
    ...(s.colores === "dos" ? [["Dos colores", (s.cambio_mm ? `figura: cambiá el filamento a los ${num(s.cambio_mm)} mm · ` : "")
      + "base: texto como parte aparte (AMS)", "f-colores"]] : []),
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

function pintar() {
  for (const [sel, nombres] of [["color", ["FIGURA"]], ["color-base", ["BASE"]], ["color-detalle", ["DETALLE", "TEXTO"]]]) {
    const o = $(sel).selectedOptions[0];
    for (const n of nombres) {
      viewer.mats[n].color.set(o.value);
      viewer.mats[n].metalness = o.dataset.metal ? 0.55 : 0;
      viewer.mats[n].roughness = o.dataset.metal ? 0.32 : 0.5;
    }
  }
  // detalles del mismo color que la figura: un poco más oscuros, para que se vean
  if ($("color-detalle").value === $("color").value) viewer.mats.DETALLE.color.multiplyScalar(0.72);
}

let pendingBuild = false;
async function build() {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = true; return; }
  const o = opts();
  setBusy(true, "Armando el trofeo…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      const marco = [o.figura, o.alto, o.base_ancho, o.base_fondo, o.base].join("|");   // reencuadra si cambia el tamaño
      viewer.showModel(r.parts, null, marco !== state.marco);
      state.marco = marco;
      pintar();
      const piezas = r.summary.piezas;
      $("dl-color").hidden = !(piezas.includes("DETALLE") || piezas.includes("TEXTO"));
      $("dldetalle").hidden = !piezas.includes("DETALLE");
      $("dltexto").hidden = !piezas.includes("TEXTO");
      state.builtOpts = o;
    }
    state.builds++;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar el trofeo"])[0],
      r.summary.valid ? "ok" : "err");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) { pendingBuild = false; build(); }
}

function save(name, buffer, mime) {
  const url = URL.createObjectURL(new Blob([buffer], { type: mime }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

async function download(kind, pieza) {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  if (!state.auth?.perms.download) {
    openLogin("Ingresá o creá tu cuenta gratis para descargar los archivos para imprimir.");
    return;
  }
  setBusy(true, kind === "3mf" ? "Armando el 3MF…" : "Armando el STL…");
  try {
    const r = await call(kind, { opts: state.builtOpts || opts(), pieza });
    state.lastDownload = { name: r.name, bytes: r.data.byteLength };
    save(r.name, r.data, kind === "3mf" ? "model/3mf" : "model/stl");
    setStatus(`Descargado ${r.name}`, "ok");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
}

async function consideracionesPdf() {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  setBusy(true, "Armando el PDF…");
  try {
    const foto = viewer.photo(1200, 744, "image/jpeg").url;
    const doc = await pdfConsideraciones("trofeo", state.summary, { foto });
    const buf = doc.output("arraybuffer");
    const name = `${state.summary.sku}_consideraciones.pdf`;
    save(name, buf, "application/pdf");
    state.lastPdf = { name, bytes: buf.byteLength, pages: doc.getNumberOfPages() };
    setStatus("PDF descargado", "ok");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error en el PDF: " + e.message, "err");
  } finally {
    setBusy(false);
  }
}

function takePhoto() {
  const r = viewer.photo(1080, 1350);
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "trofeo"}.png` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  state.lastPhoto = { width: r.width, height: r.height };
  setStatus("Foto descargada (1080×1350)", "ok");
}

function sceneButtons() {
  $("scenes").innerHTML = Object.entries(SCENES).map(([k, S]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="escena-${k}" aria-pressed="${k === state.scene}">${S.label}</button>`).join("");
}

function figuraButtons() {
  $("figuras").innerHTML = (state.info?.figuras || []).map((f) => `
    <button type="button" role="radio" data-figura="${f.id}" data-testid="figura-${f.id}" aria-pressed="${f.id === state.figura}">${esc(f.nombre)}</button>`).join("");
}

function sections() {
  const mobile = window.matchMedia("(max-width: 860px)").matches;
  for (const f of document.querySelectorAll("fieldset.sec")) {
    if (mobile && f.hasAttribute("data-closed-mobile")) f.classList.add("closed");
    const lg = f.querySelector("legend");
    lg.setAttribute("role", "button");
    lg.tabIndex = 0;
    lg.dataset.testid = "sec-" + f.dataset.sec;
    const toggle = () => { f.classList.toggle("closed"); lg.setAttribute("aria-expanded", String(!f.classList.contains("closed"))); };
    lg.setAttribute("aria-expanded", String(!f.classList.contains("closed")));
    lg.addEventListener("click", toggle);
    lg.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  }
}

// lo que se muestra según la figura y los colores
function ui() {
  const numero = state.figura === "numero";
  $("numero-row").hidden = !numero;
  $("texto-figura-row").hidden = numero || state.figura === "pelota";
  $("relieve-lbl").textContent = $("texto").value === "grabado" ? "Relieve / prof." : "Relieve";
  const h = $("colores-hint");
  h.hidden = $("colores").value !== "dos";
  h.textContent = "La figura se imprime acostada: pausá en la capa del grosor y cambiá el filamento (o usá AMS). "
    + "El texto de la base sale como parte aparte, para AMS / multicolor.";
}

function sliderText(k) {
  const [d, u] = SL[k];
  return num($(k).value, d) + u;
}

// ------------------------------------------------------------------ arranque
async function main() {
  sections();
  sceneButtons();
  try {
    const boot = await call("init");
    state.info = boot.info;
    const I = boot.info;
    const opcion = (l) => l.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("fuente").innerHTML = $("fuente_figura").innerHTML = opcion(I.fuentes);
    $("fuente").value = I.defecto.fuente;
    $("fuente_figura").value = I.defecto.fuente_figura;
    $("base").innerHTML = opcion(I.bases);
    $("texto").innerHTML = opcion(I.textos);
    $("colores").innerHTML = opcion(I.colores);
    for (const id of ["fuente", "fuente_figura", "base", "texto", "colores"]) $(id).disabled = false;
    figuraButtons();
    ui();
    $("engine-v").textContent = I.motor;
    $("build-id").textContent = "web " + boot.version;
    state.ready = true;
    state.bootSeconds = boot.seconds;
    setStatus(`Motor listo en ${boot.seconds.toFixed(1)} s`, "ok");
    await build();
  } catch (e) {
    state.errors.push(String(e));
    setStatus("No se pudo cargar el motor: " + e.message, "err");
  }
}

let tTexto = null;
for (const id of ["caracter", "texto_figura", "linea1", "linea2"]) {
  $(id).addEventListener("input", () => { clearTimeout(tTexto); tTexto = setTimeout(build, 600); });
}
for (const id of ["fuente", "fuente_figura", "base", "texto", "colores"]) $(id).addEventListener("change", () => { ui(); build(); });
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build());
}
$("figuras").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-figura]");
  if (!b || b.dataset.figura === state.figura) return;
  state.figura = b.dataset.figura;
  figuraButtons();
  ui();
  build();
});
$("build").addEventListener("click", () => build());
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlfigura").addEventListener("click", () => download("stl", "FIGURA"));
$("dlbase").addEventListener("click", () => download("stl", "BASE"));
$("dldetalle").addEventListener("click", () => download("stl", "DETALLE"));
$("dltexto").addEventListener("click", () => download("stl", "TEXTO"));
botonesPremium(state, [
  { el: $("photo"), que: "El render (foto)", accion: () => takePhoto() },
  { el: $("pdf"), que: "El PDF con las consideraciones de impresión", accion: () => consideracionesPdf() },
]);
for (const id of ["color", "color-base", "color-detalle"]) $(id).addEventListener("change", pintar);
$("scenes").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (!b) return;
  state.scene = b.dataset.k;
  viewer.setScene(state.scene);
  sceneButtons();
});

mountAccount($("account"));
onAuth((a) => { state.auth = a; });
window.addEventListener("error", (e) => state.errors.push(String(e.message)));
main();
