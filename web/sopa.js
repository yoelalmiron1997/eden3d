// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// "Sopa de letras 3D": sopa con tus palabras, cortada en piezas que encastran.
import * as THREE from "three";
import { botonesPremium } from "./premium.js";
import { pdfConsideraciones } from "./guia-impresion.js";
import { pantallaCarga } from "./cargando.js";
import { Viewer, SCENES } from "./viewer.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// estado visible para los tests e2e (window.__sopa)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  semilla: 1, auth: null, scene: "estudio", solucion: false, separar: 0, encontradas: new Set() };
window.__sopa = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("sopa-worker.js");
pantallaCarga({ motor: "sopa", worker, estado: state });   // la impresora imprimiendo mientras carga
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
viewer.viewDir = new THREE.Vector3(0.1, 1.6, 1);
viewer.viewDist = 0.95;
viewer.mats.LETRAS = new THREE.MeshStandardMaterial({ color: 0x2d4a2a, roughness: 0.7, metalness: 0, side: THREE.DoubleSide });
viewer.mats.SOLUCION = new THREE.MeshStandardMaterial({ color: 0x2d4a2a, roughness: 0.6, metalness: 0, side: THREE.DoubleSide });
viewer.mats.BLOQUE = new THREE.MeshStandardMaterial({ color: 0xe8562a, roughness: 0.45, metalness: 0, side: THREE.DoubleSide });
const bloques = new THREE.Group();          // copias del bloque puestas sobre las letras
bloques.name = "BLOQUES";
window.__sopaViewer = viewer;
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.meshNames(), triangles: viewer.triangles, frames: viewer.stats.frames,
  piezas: [...new Set(viewer.model.children.map((m) => m.userData.pieza).filter(Boolean))],
  separacion: piezaOffsetMax(), scene: viewer.sceneKey,
  solucion: "#" + viewer.mats.SOLUCION.color.getHexString(),
  bloquesPuestos: bloques.visible ? bloques.children.length : 0,
  palabrasMarcadas: bloques.visible ? [...new Set(bloques.children.flatMap((b) => b.userData.palabras))] : [],
}) });

// ------------------------------------------------------------------ opciones
const SL = { celda: [0, " mm"], holgura: [2, " mm"], base: [1, " mm"], relieve: [1, " mm"], ajuste: [2, " mm"] };

function palabras() {
  return $("palabras").value.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);
}

function opts() {
  const n = +$("grilla").value;
  const pz = +$("piezas").value;
  const o = { palabras: palabras(), dificultad: $("dificultad").value, semilla: state.semilla,
    filas: n, cols: n, cama: +$("cama").value, piezas_x: pz, piezas_y: pz, lista: $("lista").checked,
    bloques: $("bloques").checked };
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
  for (const id of ["dl3mf", "dlstl", "photo", "pdf"]) $(id).disabled = !ok;
}

function contar() {
  const p = palabras();
  $("cuenta").textContent = p.length ? `${p.length} palabra${p.length === 1 ? "" : "s"}` : "Escribí algunas palabras";
}

// ------------------------------------------------------------------ reporte y sopa 2D
function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Grilla", `${s.filas} × ${s.cols} · ${s.palabras} palabras`, "f-grilla"],
    ["Tablero", `${Math.round(s.tablero_mm[0])} × ${Math.round(s.tablero_mm[1])} mm`, "f-tablero"],
    ["Piezas", `${s.piezas} (${s.piezas_x} × ${s.piezas_y}) · ${s.lenguetas} encastres`, "f-piezas"],
    ["Letra", `${num(s.letra_mm)} mm · celda ${num(s.celda_mm, 0)} mm`, "f-letra", "minor"],
    ...(s.bloques ? [["Bloques para marcar", `${s.bloques} iguales (uno por letra) · ${num(s.bloque_mm[0])} × ${num(s.bloque_mm[1])} mm · ajuste ${num(s.ajuste_mm, 2)} mm`, "f-bloques"]] : []),
    ["Cambio de color", `a ${num(s.cambio_color_mm)} mm`, "f-color", "minor"],
    ["Peso", `${s.peso_g} g PLA (100 %)`, "f-peso"],
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

function celdasDe(u) {
  return Array.from(u.palabra, (_, i) => `${u.fila + u.df * i},${u.col + u.dc * i}`);
}

function render2d(s) {
  if (!s.grid) { $("tabla").innerHTML = ""; $("lista-palabras").innerHTML = ""; return; }
  const sol = new Set((s.ubicadas || []).flatMap(celdasDe));
  $("tabla").innerHTML = s.grid.map((fila, r) => `<tr>${Array.from(fila, (ch, c) =>
    `<td data-rc="${r},${c}" class="${sol.has(`${r},${c}`) ? "w" : ""}">${ch}</td>`).join("")}</tr>`).join("");
  $("lista-palabras").innerHTML = (s.ubicadas || []).map((u, i) =>
    `<li><button type="button" data-i="${i}" data-palabra="${esc(u.palabra)}" title="${u.dir}"
      aria-pressed="${state.encontradas.has(u.palabra)}">${esc(u.palabra)}</button></li>`).join("") +
    (s.faltan || []).map((w) => `<li class="falta" title="No entró">${esc(w)}</li>`).join("");
  verSolucion(state.solucion);
}

// los bloques se ponen sobre cada letra de las palabras marcadas (o de todas, con la solución)
function ponerBloques() {
  bloques.clear();
  const modelo = viewer.model.getObjectByName("BLOQUE");
  if (modelo) modelo.visible = false;
  if (modelo && !viewer.model.children.includes(bloques)) viewer.model.add(bloques);
  bloques.visible = state.separar === 0;
  if (!modelo || !state.summary?.valid) return;
  const enCelda = new Map();
  for (const u of state.summary.ubicadas || []) {
    if (!(state.solucion || state.encontradas.has(u.palabra))) continue;
    for (const [x, y] of u.centros) {
      const k = `${x},${y}`;
      if (enCelda.has(k)) { enCelda.get(k).userData.palabras.push(u.palabra); continue; }
      const b = new THREE.Mesh(modelo.geometry, viewer.mats.BLOQUE);
      b.position.set(x, y, state.summary.base_mm || 0);   // apoyado sobre la base
      b.castShadow = true;
      b.userData.palabras = [u.palabra];
      enCelda.set(k, b);
      bloques.add(b);
    }
  }
}

function marcar(palabra) {
  if (state.separar > 0) {                    // para ver los bloques, el tablero tiene que estar armado
    $("separar").value = 0;
    $("o-separar").textContent = "0 %";
    separar(0);
  }
  if (state.encontradas.has(palabra)) state.encontradas.delete(palabra);
  else state.encontradas.add(palabra);
  for (const b of $("lista-palabras").querySelectorAll("button[data-palabra]")) {
    b.setAttribute("aria-pressed", String(state.encontradas.has(b.dataset.palabra)));
  }
  ponerBloques();
}

function verSolucion(on) {
  state.solucion = on;
  $("tabla").classList.toggle("sol", on);
  $("solucion").checked = on;
  $("ver-sol").textContent = on ? "Ocultar solución" : "Ver solución";
  viewer.mats.SOLUCION.color.set(on ? "#e8562a" : $("color-letras").value);
  ponerBloques();
}

function resaltar(i) {
  for (const td of $("tabla").querySelectorAll("td.h")) td.classList.remove("h");
  const u = state.summary?.ubicadas?.[i];
  if (!u) return;
  for (const rc of celdasDe(u)) $("tabla").querySelector(`[data-rc="${rc}"]`)?.classList.add("h");
}

// ------------------------------------------------------------------ piezas separadas
function piezaOffsetMax() {
  let m = 0;
  for (const o of viewer.model.children) m = Math.max(m, o.position.length());
  return m;
}

function separar(k) {
  state.separar = k;
  const centros = {};
  const box = new THREE.Box3();
  for (const o of viewer.model.children) {
    const p = o.userData.pieza;
    if (!p || p === "LISTA" || p === "BLOQUE") continue;
    o.geometry.computeBoundingBox();
    (centros[p] = centros[p] || new THREE.Box3()).union(o.geometry.boundingBox);
    box.union(o.geometry.boundingBox);
  }
  const c0 = box.getCenter(new THREE.Vector3());
  for (const o of viewer.model.children) {
    const p = o.userData.pieza;
    if (!p || !centros[p]) { o.position.set(0, 0, 0); continue; }   // lista y bloques
    const c = centros[p].getCenter(new THREE.Vector3()).sub(c0);
    o.position.set(c.x * k * 0.35, c.y * k * 0.35, 0);
  }
  ponerBloques();
}

// ------------------------------------------------------------------ cálculo
let pendingBuild = null;
async function build(refit = false) {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = { refit: refit || (pendingBuild && pendingBuild.refit) }; return; }
  const o = opts();
  setBusy(true, "Armando la sopa…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, pieza: p.pieza, bytes: p.positions.byteLength }));
    showReport(r.summary);
    render2d(r.summary);
    if (r.summary.valid) {
      viewer.showModel(r.parts, null, refit);
      viewer.model.children.forEach((m, i) => { m.userData.pieza = r.parts[i]?.pieza; });
      const vigentes = new Set((r.summary.ubicadas || []).map((u) => u.palabra));
      for (const w of [...state.encontradas]) if (!vigentes.has(w)) state.encontradas.delete(w);
      viewer.setColor($("color").value);
      viewer.mats.LETRAS.color.set($("color-letras").value);
      verSolucion(state.solucion);
      separar(+$("separar").value / 100);
    }
    state.builds++;
    if (r.summary.valid) state.builtOpts = o;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar la sopa"])[0],
      r.summary.valid ? "ok" : "err");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) {
    const p = pendingBuild;
    pendingBuild = null;
    return build(p.refit);
  }
}

// ------------------------------------------------------------------ descargas y foto
function save(name, buffer, mime) {
  const url = URL.createObjectURL(new Blob([buffer], { type: mime }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

async function download(kind) {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  if (!state.auth?.perms.download) {
    openLogin("Ingresá o creá tu cuenta gratis para descargar los archivos para imprimir.");
    return;
  }
  setBusy(true, kind === "3mf" ? "Armando el 3MF…" : "Armando el STL…");
  try {
    const r = await call(kind, { opts: state.builtOpts || opts() });
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
    const doc = await pdfConsideraciones("sopa", state.summary, { foto });
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
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "sopa"}.png` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  state.lastPhoto = { width: r.width, height: r.height };
  setStatus("Foto descargada (1080×1350)", "ok");
}

// ------------------------------------------------------------------ armado de la UI
function sceneButtons() {
  $("scenes").innerHTML = Object.entries(SCENES).map(([k, S]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="escena-${k}" aria-pressed="${k === state.scene}">${S.label}</button>`).join("");
}

function sections() {
  const mobile = window.matchMedia("(max-width: 860px)").matches;
  for (const f of document.querySelectorAll("fieldset.sec")) {
    if (f.hasAttribute("data-closed") || (mobile && f.hasAttribute("data-closed-mobile"))) f.classList.add("closed");
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

const sliderText = (k) => num($(k).value, SL[k][0]) + SL[k][1];

async function main() {
  sections();
  sceneButtons();
  contar();
  try {
    const boot = await call("init");
    state.info = boot.info;
    $("dificultad").innerHTML = boot.info.dificultades.map((d) => `<option value="${d.id}">${esc(d.nombre)}</option>`).join("");
    $("dificultad").value = boot.info.defaults.dificultad;
    $("cama").innerHTML = boot.info.camas.map((c) => `<option value="${c}">${c} × ${c} mm</option>`).join("");
    $("cama").value = String(boot.info.defaults.cama);
    $("dificultad").disabled = false;
    $("engine-v").textContent = boot.info.motor;
    $("build-id").textContent = "web " + boot.version;
    state.ready = true;
    state.bootSeconds = boot.seconds;
    setStatus(`Motor listo en ${boot.seconds.toFixed(1)} s`, "ok");
    await build(true);
  } catch (e) {
    state.errors.push(String(e));
    setStatus("No se pudo cargar el motor: " + e.message, "err");
  }
}

let tPal = null;
$("palabras").addEventListener("input", () => {
  contar();
  clearTimeout(tPal);
  tPal = setTimeout(() => build(true), 900);
});
for (const id of ["dificultad", "grilla", "cama", "piezas", "lista", "bloques"]) $(id).addEventListener("change", () => build(true));
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build(k === "celda"));
}
$("mezclar").addEventListener("click", () => { state.semilla = 1 + Math.floor(Math.random() * 99999); build(); });
$("build").addEventListener("click", () => build(true));
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl"));
botonesPremium(state, [                                   // render y PDF: plan Premium
  { el: $("photo"), que: "El render (foto)", accion: () => takePhoto() },
  { el: $("pdf"), que: "El PDF con las consideraciones de impresión", accion: () => consideracionesPdf() },
]);
$("color").addEventListener("change", () => viewer.setColor($("color").value));
$("color-letras").addEventListener("change", () => { viewer.mats.LETRAS.color.set($("color-letras").value); verSolucion(state.solucion); });
$("solucion").addEventListener("change", () => verSolucion($("solucion").checked));
$("ver-sol").addEventListener("click", () => verSolucion(!state.solucion));
$("separar").addEventListener("input", () => { $("o-separar").textContent = $("separar").value + " %"; separar(+$("separar").value / 100); });
$("lista-palabras").addEventListener("mouseover", (ev) => { const b = ev.target.closest("button[data-i]"); if (b) resaltar(+b.dataset.i); });
$("lista-palabras").addEventListener("mouseout", () => resaltar(-1));
$("lista-palabras").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-i]");
  if (!b) return;
  resaltar(+b.dataset.i);
  marcar(b.dataset.palabra);
});
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
