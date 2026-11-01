// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// "Chapitas para collares": el nombre de tu mascota en un hueso, un gato, un corazón…
// con la argolla para el collar, lista para imprimir.
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

// estado visible para los tests e2e (window.__chapita)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  auth: null, scene: "estudio", forma: "hueso" };
window.__chapita = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("chapita-worker.js");
pantallaCarga({ motor: "chapita", worker, estado: state });   // la impresora imprimiendo mientras carga
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
viewer.viewDist = 1.25;
viewer.mats.CHAPITA = new THREE.MeshStandardMaterial({ color: 0x2a5bd7, roughness: 0.5, metalness: 0, side: THREE.DoubleSide });
viewer.mats.LETRAS = new THREE.MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.45, metalness: 0, side: THREE.DoubleSide });
window.__chapitaViewer = viewer;
// normales con quiebre: la cara de arriba/abajo no se promedia con las paredes (si no, los
// bordes salen manchados); cada grupo se suaviza sólo consigo mismo
viewer.geom = (p) => {
  const P = new Float32Array(p.positions), I = new Uint32Array(p.indices);
  const nv = P.length / 3, mapa = new Map(), pos = [], idx = [];
  const v = (i, k) => P[3 * i + k];
  for (let t = 0; t < I.length; t += 3) {
    const [a, b, c] = [I[t], I[t + 1], I[t + 2]];
    const ux = v(b, 0) - v(a, 0), uy = v(b, 1) - v(a, 1), uz = v(b, 2) - v(a, 2);
    const wx = v(c, 0) - v(a, 0), wy = v(c, 1) - v(a, 1), wz = v(c, 2) - v(a, 2);
    const nz = ux * wy - uy * wx, nn = Math.hypot(uy * wz - uz * wy, uz * wx - ux * wz, nz) || 1;
    const grupo = Math.abs(nz / nn) > 0.7 ? (nz > 0 ? 1 : 2) : 0;   // 1 arriba, 2 abajo, 0 pared
    for (const i of [a, b, c]) {
      const key = grupo * nv + i;
      let j = mapa.get(key);
      if (j === undefined) { j = pos.length / 3; mapa.set(key, j); pos.push(v(i, 0), v(i, 1), v(i, 2)); }
      idx.push(j);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(idx), 1));
  g.computeVertexNormals();
  return g;
};
const metal = new THREE.MeshStandardMaterial({ color: 0xc9ccd1, roughness: 0.22, metalness: 1 });
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.model.children.filter((m) => m.isMesh && m.name !== "ARGOLLA").map((m) => m.name),
  argolla: viewer.model.children.some((m) => m.name === "ARGOLLA"), triangles: viewer.triangles,
  color: "#" + viewer.mats.CHAPITA.color.getHexString(), letras: "#" + viewer.mats.LETRAS.color.getHexString(),
}) });

// la argollita del collar pasando por el agujero, para ver cómo queda colgada
function argolla(s) {
  const O = s.ojal;
  const R = Math.max(7, O.r_ojal + 3.2);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(R, 0.75, 16, 96), metal);
  ring.name = "ARGOLLA";
  ring.rotation.y = Math.PI / 2;                       // de canto, atravesando el agujero
  ring.position.set(O.x, O.y + R - O.r_agujero * 0.55, s.grosor_mm / 2);
  ring.castShadow = true;
  viewer.model.add(ring);
}

function encuadrar() {
  const box = new THREE.Box3().setFromObject(viewer.model);
  if (box.isEmpty()) return;
  viewer.viewDir = new THREE.Vector3(-0.12, 1.25, 0.75);
  viewer.fit(box);
}

// ------------------------------------------------------------------ opciones
const SL = { ancho: [0, " mm"], borde: [1, " mm"], grosor: [1, " mm"], relieve: [1, " mm"], agujero: [1, " mm"] };

function opts() {
  const o = { forma: state.forma, nombre: $("nombre").value.trim(), linea2: $("linea2").value.trim(), fuente: $("fuente").value,
    texto: $("texto").value, colores: $("colores").value, patitas: $("patitas").checked };
  for (const k of Object.keys(SL)) o[k] = +$(k).value;
  return o;
}

function setStatus(text, kind = "") {
  const s = document.querySelector("[data-testid=estado]");
  s.textContent = text;
  s.className = "status " + kind;
}

function setBusy(on, text = "Calculando…") {
  state.busy = on;
  $("busy").hidden = !on;
  $("busy-text").textContent = text;
  const ok = !on && state.ready && !!state.summary?.valid;
  $("build").disabled = on || !state.ready;
  for (const id of ["dl3mf", "dlstl", "photo", "pdf", "dlletras"]) $(id).disabled = !ok;
}

function colores(s) {
  if (s.cambio_mm) return [["Dos colores", `letras ${num(s.relieve_mm)} mm arriba · pausá y cambiá el filamento a los ${num(s.cambio_mm)} mm`, "f-colores"]];
  if (s.capa_color_mm) return [["Dos colores", `misma altura: las letras de color en las últimas ${num(s.capa_color_mm)} mm (AMS)`, "f-colores"]];
  return [];
}

function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Medidas", `${Math.round(s.medidas_mm[0])} × ${Math.round(s.medidas_mm[1])} × ${num(s.medidas_mm[2])} mm`, "f-medidas"],
    ["Letra", `${num(s.letra_mm)} mm de alto`, "f-letra"],
    ["Letras", s.texto === "grabado" ? `grabadas ${num(s.relieve_mm)} mm` : `en relieve ${num(s.relieve_mm)} mm`, "f-texto"],
    ["Agujero", `Ø ${num(s.agujero_mm)} mm para la argollita`, "f-agujero", "minor"],
    ...colores(s),
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

let pendingBuild = false;
async function build() {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = true; return; }
  const o = opts();
  setBusy(true, "Armando la chapita…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      viewer.showModel(r.parts, null, false);
      viewer.mats.CHAPITA.color.set($("color").value);
      viewer.mats.LETRAS.color.set($("color-letras").value);
      argolla(r.summary);
      encuadrar();
      $("dlletras").hidden = !r.parts.some((p) => p.name === "LETRAS");
      state.builtOpts = o;
    }
    state.builds++;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar la chapita"])[0],
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

// PDF con las consideraciones de impresión (Premium)
async function consideracionesPdf() {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  setBusy(true, "Armando el PDF…");
  try {
    const foto = viewer.photo(1200, 744, "image/jpeg").url;
    const doc = await pdfConsideraciones("chapita", state.summary, { foto });
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
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "chapita"}.png` });
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

function formaButtons() {
  $("formas").innerHTML = (state.info?.formas || []).map((f) => `
    <button type="button" role="radio" data-forma="${f.id}" data-testid="forma-${f.id}" aria-pressed="${f.id === state.forma}">${esc(f.nombre)}</button>`).join("");
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

// lo que se muestra según la forma, el estilo de letra y los colores
function ui() {
  const grabado = $("texto").value === "grabado";
  const dobleOpt = $("colores").querySelector("option[value=doble]");
  if (dobleOpt) dobleOpt.disabled = grabado;
  if (grabado && $("colores").value === "doble") $("colores").value = "ams";
  $("borde-row").hidden = grabado;
  $("relieve-lbl").textContent = grabado ? "Profundidad" : "Relieve";
  $("patitas-row").hidden = !(state.info?.con_patitas || []).includes(state.forma);
  const c = $("colores").value, h = $("colores-hint");
  h.hidden = c === "uno";
  h.textContent = c === "doble"
    ? "Letras, patitas y borde en relieve arriba de la placa: en cualquier impresora, pausá en esa capa y cambiá el filamento."
    : (grabado ? "Las letras grabadas se rellenan de otro color al ras: para AMS / multicolor."
      : "Letras al ras de la placa, del mismo alto: cada capa de arriba lleva los dos colores (AMS / multicolor).");
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
    $("fuente").innerHTML = I.fuentes.map((f) => `<option value="${f.id}">${esc(f.nombre)}</option>`).join("");
    $("fuente").value = I.defecto.fuente;
    $("texto").innerHTML = I.textos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("colores").innerHTML = I.colores.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    for (const id of ["fuente", "texto", "colores"]) $(id).disabled = false;
    formaButtons();
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
for (const id of ["nombre", "linea2"]) $(id).addEventListener("input", () => { clearTimeout(tTexto); tTexto = setTimeout(build, 600); });
for (const id of ["fuente", "texto", "colores", "patitas"]) $(id).addEventListener("change", () => { ui(); build(); });
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build());
}
$("formas").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-forma]");
  if (!b || b.dataset.forma === state.forma) return;
  state.forma = b.dataset.forma;
  formaButtons();
  ui();
  build();
});
$("build").addEventListener("click", () => build());
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl", "CHAPITA"));
$("dlletras").addEventListener("click", () => download("stl", "LETRAS"));
botonesPremium(state, [                                   // render y PDF: plan Premium
  { el: $("photo"), que: "El render (foto)", accion: () => takePhoto() },
  { el: $("pdf"), que: "El PDF con las consideraciones de impresión", accion: () => consideracionesPdf() },
]);
$("color").addEventListener("change", () => viewer.mats.CHAPITA.color.set($("color").value));
$("color-letras").addEventListener("change", () => viewer.mats.LETRAS.color.set($("color-letras").value));
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
