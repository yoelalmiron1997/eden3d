// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// "Mate con hueco": mate imperial para imprimir en 3D con el hueco exacto del inserto.
import * as THREE from "three";
import { pantallaCarga } from "./cargando.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { Viewer, LIGHTS, SCENES } from "./viewer.js";
import { Cebado, ESTILOS } from "./mate-cebado.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mm = (v, d = 1) => (v === undefined || v === null ? "—" : `${(+v).toFixed(d).replace(".", ",")} mm`);

// estado visible para los tests e2e (window.__mate)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  stl: null, auth: null, scene: "estudio", light: "estudio", marca: null, cuna: false,
  deco: { tipo: "", texto: "TecnoBear", svg: null, angulo: -90, z: null, alto: 18, rot: 0, prof: 1.2,
    fuente: null, grosor: 0, medallon: false, diam: 36, holgura: 0.2 },
  gizmo: { mode: "translate", drags: 0 } };
window.__mate = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("mate-worker.js");
pantallaCarga({ motor: "mate", worker, estado: state });   // la impresora imprimiendo mientras carga
let seq = 0;
const pending = new Map();
worker.onmessage = (ev) => {
  const { id, ok, result, error } = ev.data;
  const p = pending.get(id);
  if (!p) return;
  pending.delete(id);
  ok ? p.resolve(result) : p.reject(new Error(error));
};
function call(type, payload = {}, transfer = []) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, ...payload }, transfer);
  });
}

const viewer = new Viewer($("viewer"));
viewer.mats.MACETA.roughness = 0.6;
window.__mateViewer = viewer;
const cebado = new Cebado(viewer);
window.__mateCebado = cebado;
Object.defineProperty(state, "cebado", { get: () => cebado.info() });
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.meshNames(), triangles: viewer.triangles, frames: viewer.stats.frames, cut: viewer.cut,
  scene: viewer.sceneKey, light: viewer.lightKey, slicer: viewer.slicerInfo(),
  inserto: !!(viewer.model.getObjectByName("INSERTO") || {}).visible,
  relieve: !!viewer.model.getObjectByName("RELIEVE"), cuna: !!viewer.model.getObjectByName("CUNA"),
  medallon: !!viewer.model.getObjectByName("MEDALLON"),
  gizmo: !!(gizmo && gizmo.object), gizmoMode: gizmo ? gizmo.mode : null,
}) });

// ------------------------------------------------------------------ UI
const SL = { pared: [1, " mm"], piso: [1, " mm"], holgura: [2, " mm"], altura: [0, " mm"],
  diam_max: [0, " mm"], diam_boca: [0, " mm"] };
const AUTO0 = ["altura", "diam_max", "diam_boca"];

function opts() {
  const o = { tipo: $("tipo").value, inserto: $("inserto").value, autoajuste: $("auto").checked,
    calidad: $("hq").checked ? "normal" : "preview" };
  for (const k of Object.keys(SL)) o[k] = +$(k).value;
  if (o.inserto === "propio") o.stl_nombre = state.stl?.name || "";
  const d = state.deco;
  if (d.tipo === "texto" || (d.tipo === "svg" && d.svg)) {
    o.deco = { tipo: d.tipo, texto: d.texto, angulo: d.angulo, alto: d.alto, rot: d.rot, prof: d.prof,
      grosor: d.grosor };
    if (d.z !== null) o.deco.z = d.z;
    if (d.tipo === "svg") o.deco.svg_nombre = d.svg;
    if (d.tipo === "texto" && d.fuente) o.deco.fuente = d.fuente;
    if (d.medallon) o.deco.medallon = { diam: d.diam, holgura: d.holgura };
  }
  // marca debajo de la base: la de Eden3D salvo para Pro / admin
  if (state.marca !== null && state.auth?.perms.brand) o.marca = state.marca;
  if (state.cuna) o.cuna = { angulo: +$("cuna-ang").value };
  return o;
}

function sliderText(k) {
  const v = +$(k).value;
  if (AUTO0.includes(k) && !v) return "del modelo";
  const [d, u] = SL[k];
  return v.toFixed(d).replace(".", ",") + u;
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
  for (const id of ["dlstl", "dl3mf", "photo", "dlcuna", "dlmedallon"]) $(id).disabled = !ok;
}

function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Modelo", esc(s.nombre), "f-modelo"],
    ["Hueco para", esc((s.insertos || []).join(" + ")), "f-inserto"],
    ["Medidas", `${Math.round(s.diam_max_mm)} × ${Math.round(s.altura_mm)} mm · boca ${Math.round(s.diam_boca_mm)} mm`, "f-medidas"],
    ["Pared mínima", mm(s.pared_mm), "f-pared"],
    ["Fondo", mm(s.fondo_mm), "f-fondo"],
    ["Hueco", `Ø ${Math.round(s.hueco_diam_mm)} × ${Math.round(s.hueco_prof_mm)} mm`, "f-hueco", "minor"],
    ["Peso", `${s.peso_g} g PLA (100 %)`, "f-peso"],
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  if (s.escala && s.escala > 1.001) facts.splice(3, 0, ["Agrandado", `×${(+s.escala).toFixed(2).replace(".", ",")}`, "f-escala", "minor"]);
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

let pendingBuild = null;
async function build(refit = false) {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = { refit: refit || (pendingBuild && pendingBuild.refit) }; return; }
  const o = opts();
  if (o.inserto === "propio" && !state.stl?.ok) {
    setStatus("Subí el STL de tu inserto para calcular el hueco", "");
    return;
  }
  setBusy(true, "Calculando el mate…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      viewer.showModel(r.parts, null, refit);
      viewer.setColor($("color").value);
      viewer.setCut($("cut").checked);
      insertoVisible();
      slicerUi();
      decoSync(r.summary.deco);
      marcaReport(r.summary.marca);
      montarGizmo(r.summary.deco);
      cebado.montar(r.summary.cavidad);
      $("dlcuna").hidden = !r.summary.cuna;
      $("dlmedallon").hidden = !r.summary.medallon;
    }
    state.triangles = viewer.triangles;
    state.meshes = viewer.meshNames();
    state.builds++;
    if (r.summary.valid) state.builtOpts = o;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar el mate"])[0],
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

function insertoVisible() {
  const m = viewer.model.getObjectByName("INSERTO");
  if (m) { m.visible = $("ver-inserto").checked && !viewer.slicer.on; m.castShadow = false; }
}

// ------------------------------------------------------------------ STL propio
async function subirStl(file) {
  if (!file) return;
  state.stl = { name: file.name, ok: false };
  $("stl-msg").classList.remove("err");
  $("stl-msg").textContent = "Leyendo " + file.name + "…";
  try {
    const buf = await file.arrayBuffer();
    const r = await call("upload", { data: buf }, [buf]);
    state.stl = { name: file.name, ok: r.ok, info: r.info, error: r.error };
    if (r.ok) {
      $("stl-msg").textContent = `${file.name}: boca Ø ${r.info.diam_abertura_mm} mm, ${r.info.alto_mm} mm de alto. Listo.`;
      build(true);
    } else {
      $("stl-msg").textContent = r.error;
      $("stl-msg").classList.add("err");
    }
  } catch (e) {
    state.errors.push(String(e));
    $("stl-msg").textContent = "No se pudo leer el archivo: " + e.message;
    $("stl-msg").classList.add("err");
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

async function download(kind, pieza) {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  if (!state.auth?.perms.download) {
    openLogin("Ingresá o creá tu cuenta gratis para descargar los archivos para imprimir.");
    return;
  }
  setBusy(true, kind === "3mf" ? "Armando el 3MF (calidad de impresión)…" : "Armando el STL…");
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

function takePhoto() {
  const h = gizmo ? gizmo.getHelper() : null;
  if (h) h.visible = false;                              // el gumball no sale en la foto
  const r = viewer.photo(1080, 1350);
  if (h) h.visible = true;
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "mate"}.png` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  state.lastPhoto = { width: r.width, height: r.height };
  setStatus("Foto descargada (1080×1350)", "ok");
}

// ------------------------------------------------------------------ ambiente, vista y capas
function sceneButtons() {
  $("scenes").innerHTML = Object.entries(SCENES).map(([k, S]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="escena-${k}" aria-pressed="${k === state.scene}">${S.label}</button>`).join("");
}
function lightButtons() {
  $("light-presets").innerHTML = Object.entries(LIGHTS).map(([k, L]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="luz-${k}" aria-pressed="${k === state.light}">${L.label}</button>`).join("");
}

function slicerUi(info) {
  info = info || viewer.slicerInfo();
  $("slicer-ui").hidden = !info.on;
  insertoVisible();
  if (!info.on) return;
  $("layer").max = info.layers;
  $("layer").value = info.layer;
  $("o-layer").textContent = `${info.layer} / ${info.layers}`;
  $("slicer-info").textContent = `${info.z.toFixed(1)} de ${info.height.toFixed(1)} mm`;
  $("play-layers").textContent = info.playing ? "❚❚ Pausa" : "▶ Imprimir";
}
viewer.onSlicer = slicerUi;

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

function fill(sel, items, val, lab) {
  sel.innerHTML = items.map((it) => `<option value="${val(it)}">${esc(lab(it))}</option>`).join("");
}

// ------------------------------------------------------------------ arranque
async function main() {
  sections();
  sceneButtons();
  lightButtons();
  try {
    const boot = await call("init");
    state.info = boot.info;
    fill($("tipo"), boot.info.tipos, (t) => t.id, (t) => t.nombre);
    fill($("inserto"), boot.info.insertos, (t) => t.id, (t) => t.nombre);
    $("engine-v").textContent = boot.info.motor;
    $("build-id").textContent = "web " + boot.version;
    for (const id of ["tipo", "inserto"]) $(id).disabled = false;
    state.ready = true;
    fill($("deco-fuente"), boot.info.deco.fuentes, (f) => f.id, (f) => f.nombre);
    state.deco.fuente = boot.info.deco.fuente;
    marcaUi();
    decoUi();
    state.bootSeconds = boot.seconds;
    setStatus(`Motor listo en ${boot.seconds.toFixed(1)} s`, "ok");
    await build(true);
  } catch (e) {
    state.errors.push(String(e));
    setStatus("No se pudo cargar el motor: " + e.message, "err");
  }
}

$("tipo").addEventListener("change", () => {
  for (const k of AUTO0) { $(k).value = 0; $("o-" + k).textContent = sliderText(k); }
  state.deco.z = null;                                   // el relieve va a la altura del modelo
  build(true);
});
$("inserto").addEventListener("change", () => {
  $("propio").hidden = $("inserto").value !== "propio";
  if ($("inserto").value === "propio" && !state.stl?.ok) $("stl").click();
  build(true);
});
$("stl").addEventListener("change", () => subirStl($("stl").files[0]));
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build(AUTO0.includes(k)));
}
$("auto").addEventListener("change", () => build());
$("hq").addEventListener("change", () => build());
$("build").addEventListener("click", () => build(true));
$("dlstl").addEventListener("click", () => download("stl"));
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlcuna").addEventListener("click", () => download("stl", "CUNA"));
$("dlmedallon").addEventListener("click", () => download("stl", "MEDALLON"));
$("photo").addEventListener("click", () => takePhoto());
$("color").addEventListener("change", () => viewer.setColor($("color").value));
$("cut").addEventListener("change", () => viewer.setCut($("cut").checked));
$("ver-inserto").addEventListener("change", insertoVisible);
$("scenes").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (!b) return;
  state.scene = b.dataset.k;
  viewer.setScene(state.scene);
  state.light = viewer.lightKey;
  sceneButtons();
  lightButtons();
});
$("light-presets").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (!b) return;
  state.light = b.dataset.k;
  viewer.setLight(state.light);
  lightButtons();
});
$("slicer").addEventListener("change", () => {
  slicerUi(viewer.setSlicer($("slicer").checked, "MACETA"));
  montarGizmo(state.summary?.deco);                      // en modo capas no hay gumball
  cebado.visibilidad();                                  // ni yerba ni agua
});
$("layer").addEventListener("input", () => { viewer.playSlicer(false); slicerUi(viewer.setLayer(+$("layer").value)); });
$("play-layers").addEventListener("click", () => { viewer.playSlicer(!viewer.slicer.playing); slicerUi(); });

// ------------------------------------------------------------------ relieve (texto / SVG) y gumball
const DSL = { "d-alto": ["alto", 0, " mm"], "d-prof": ["prof", 1, " mm"], "d-angulo": ["angulo", 0, "°"],
  "d-z": ["z", 1, " mm"], "d-rot": ["rot", 0, "°"], "d-grosor": ["grosor", 1, " mm"],
  "m-diam": ["diam", 0, " mm"], "m-holgura": ["holgura", 2, " mm"] };
const fmtNum = (v, d) => (+v).toFixed(d).replace(".", ",");

function decoUi() {
  const d = state.deco;
  for (const b of $("deco-tipo").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.t === d.tipo));
  $("deco-ui").hidden = !d.tipo;
  $("deco-texto-row").hidden = d.tipo !== "texto";
  $("deco-fuente-row").hidden = d.tipo !== "texto";
  if (d.fuente) $("deco-fuente").value = d.fuente;
  $("deco-svg-row").hidden = d.tipo !== "svg";
  $("medallon").checked = !!d.medallon;
  $("medallon-ui").hidden = !d.medallon;
  for (const [id, [k, dec, u]] of Object.entries(DSL)) {
    if (d[k] === null || d[k] === undefined) continue;
    $(id).value = d[k];
    $("o-" + id).textContent = fmtNum(d[k], dec) + u;
  }
  for (const b of $("gizmo").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.m === state.gizmo.mode));
}

function decoSync(info) {
  if (!info) { if (state.deco.tipo) $("deco-msg").textContent = ""; return; }
  // el motor completa lo que faltaba (la altura del medallón, por ejemplo)
  Object.assign(state.deco, { angulo: info.angulo, z: info.z, alto: info.alto, rot: info.rot, prof: info.prof });
  if (info.fuente) state.deco.fuente = info.fuente;
  $("d-z").max = Math.ceil(state.summary.altura_mm);
  $("deco-msg").textContent = `${fmtNum(info.ancho, 0)} × ${fmtNum(info.alto, 0)} mm · sobresale ${fmtNum(info.prof, 1)} mm`
    + (info.ajustado ? " · achicado para entrar en el medallón" : "");
  $("deco-msg").classList.remove("err");
  const m = state.summary.medallon;
  if (m) {
    $("medallon-msg").textContent = `Pieza de Ø ${fmtNum(m.diam_pieza_mm, 1)} × ${fmtNum(m.alto_pieza_mm, 1)} mm `
      + `en un bolsillo de Ø ${fmtNum(m.diam_mm, 0)} mm: juego de ${fmtNum(m.juego_mm[0], 2)} a ${fmtNum(m.juego_mm[1], 2)} mm. `
      + "Se imprime con la base plana en la cama.";
  }
  decoUi();
}

async function aplicarTextoDeco() {
  const r = await call("texto", { text: $("deco-txt").value, fuente: state.deco.fuente });
  if (r.error || !r.text) {
    $("deco-msg").textContent = r.error || "Escribí un texto";
    $("deco-msg").classList.add("err");
    return;
  }
  state.deco.texto = r.text;
  $("deco-txt").value = r.text;
  build();
}

async function subirSvg(file) {
  if (!file) return;
  if (file.size > 600000) {
    $("deco-msg").textContent = "El SVG es muy grande (máx. 600 KB)";
    $("deco-msg").classList.add("err");
    return;
  }
  const buf = await file.arrayBuffer();
  await call("svg", { data: buf }, [buf]);
  state.deco.svg = file.name;
  $("deco-msg").textContent = "Proyectando " + file.name + "…";
  build();
}

$("deco-tipo").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-t]");
  if (!b) return;
  const antes = state.deco.tipo;
  state.deco.tipo = b.dataset.t;
  // tamaño de arranque: un texto entra mejor más bajito que un logo
  if (b.dataset.t && b.dataset.t !== antes) state.deco.alto = b.dataset.t === "texto" ? 10 : 28;
  decoUi();
  if (state.deco.tipo === "svg" && !state.deco.svg) { $("deco-file").click(); return; }
  build();
});
$("deco-aplicar").addEventListener("click", () => aplicarTextoDeco());
$("deco-fuente").addEventListener("change", () => { state.deco.fuente = $("deco-fuente").value; aplicarTextoDeco(); });
$("medallon").addEventListener("change", () => {
  state.deco.medallon = $("medallon").checked;
  decoUi();
  build();
});
$("deco-txt").addEventListener("keydown", (e) => { if (e.key === "Enter") aplicarTextoDeco(); });
$("deco-file").addEventListener("change", () => subirSvg($("deco-file").files[0]));
for (const [id, [k, dec, u]] of Object.entries(DSL)) {
  $(id).addEventListener("input", () => { $("o-" + id).textContent = fmtNum($(id).value, dec) + u; });
  $(id).addEventListener("change", () => { state.deco[k] = +$(id).value; build(); });
}

// Gumball: un "pivote" en el centro del relieve, con X = tangente, Y = arriba y
// Z = hacia afuera. Mover lo desliza por la superficie (giro y altura), Girar lo rota
// sobre sí mismo y Escala lo agranda. Mientras se arrastra, el relieve (y el medallón) se
// vuelve a apoyar sobre la piel real del mate en cada cuadro (la tabla summary.piel); al
// soltar, el motor lo proyecta de nuevo con toda la precisión.
let gizmo = null;
const pivote = new THREE.Object3D();
pivote.name = "PIVOTE_RELIEVE";
const base = { th: 0, z: 0, R0: 0, rot: 0, alto: 18, prof: 1.2 };
let envolver = [];                         // [{mesh, local: Float32Array (a, b, h), diseño}]
const TAU = Math.PI * 2;
const angDif = (a) => ((a % TAU) + TAU + Math.PI) % TAU - Math.PI;

function pielRadio(z, th) {
  const P = state.summary?.piel;
  if (!P) return base.R0;
  const zs = P.z, m = P.m;
  const zz = Math.min(zs[zs.length - 1], Math.max(zs[0], z));
  let lo = 0, hi = zs.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (zs[mid] <= zz) lo = mid; else hi = mid; }
  const t = zs[hi] === zs[lo] ? 0 : (zz - zs[lo]) / (zs[hi] - zs[lo]);
  const x = (((th % TAU) + TAU) % TAU) / TAU * m;
  const k0 = Math.floor(x) % m, k1 = (k0 + 1) % m, w = x - Math.floor(x);
  const r0 = P.r[lo * m + k0] * (1 - w) + P.r[lo * m + k1] * w;
  const r1 = P.r[hi * m + k0] * (1 - w) + P.r[hi * m + k1] * w;
  return r0 * (1 - t) + r1 * t;
}

window.__matePiel = (z, th) => pielRadio(z, th);       // para los tests e2e

function orientar(th, extra = 0) {
  const X = new THREE.Vector3(-Math.sin(th), Math.cos(th), 0);
  const Y = new THREE.Vector3(0, 0, 1);
  const Z = new THREE.Vector3(Math.cos(th), Math.sin(th), 0);
  pivote.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(X, Y, Z));
  if (extra) pivote.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), extra));
}

// coordenadas propias de cada vértice: (a, b) en el plano del diseño (sin giro) y h = altura
// sobre la piel; así se puede volver a apoyar en cualquier lugar de la superficie
function prepararEnvolver() {
  envolver = [];
  const ca = Math.cos(-base.rot * Math.PI / 180), sa = Math.sin(-base.rot * Math.PI / 180);
  for (const [name, diseno] of [["RELIEVE", true], ["MEDALLON", false]]) {
    const mesh = viewer.model.getObjectByName(name);
    if (!mesh) continue;
    const pos = mesh.geometry.attributes.position;
    const local = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const th = Math.atan2(y, x);
      const u = angDif(th - base.th) * base.R0, v = z - base.z;
      local[i * 3] = diseno ? u * ca - v * sa : u;
      local[i * 3 + 1] = diseno ? u * sa + v * ca : v;
      local[i * 3 + 2] = Math.hypot(x, y) - pielRadio(z, th);
    }
    envolver.push({ mesh, local, diseno });
  }
}

function envolverEn(th0, z0, rotDeg, k) {
  const R0 = pielRadio(z0, th0);
  const ca = Math.cos(rotDeg * Math.PI / 180), sa = Math.sin(rotDeg * Math.PI / 180);
  for (const { mesh, local, diseno } of envolver) {
    const pos = mesh.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let u = local[i * 3], v = local[i * 3 + 1];
      if (diseno) { const a = u * k, b = v * k; u = a * ca - b * sa; v = a * sa + b * ca; }
      const th = th0 + u / R0, z = z0 + v;
      const r = pielRadio(z, th) + local[i * 3 + 2];
      pos.setXYZ(i, r * Math.cos(th), r * Math.sin(th), z);
    }
    pos.needsUpdate = true;
    mesh.geometry.computeVertexNormals();
    mesh.geometry.computeBoundingSphere();
  }
}

function montarGizmo(info) {
  if (!gizmo) {
    gizmo = new TransformControls(viewer.camera, viewer.renderer.domElement);
    gizmo.setSize(0.8);
    gizmo.addEventListener("dragging-changed", (e) => {
      viewer.controls.enabled = !e.value;
      if (!e.value) soltarGizmo();
    });
    gizmo.addEventListener("objectChange", () => moverGizmo());
    viewer.scene.add(gizmo.getHelper());
    window.__mateGizmo = gizmo;
  }
  const rel = viewer.model.getObjectByName("RELIEVE");
  if (!rel || !info || viewer.slicer.on) { gizmo.detach(); envolver = []; return; }
  base.th = info.angulo * Math.PI / 180;
  base.z = info.z;
  base.R0 = info.radio;
  base.rot = info.rot;
  base.alto = info.alto;
  base.prof = info.prof;
  prepararEnvolver();
  viewer.model.add(pivote);
  pivote.scale.set(1, 1, 1);
  colocarPivote(base.th, base.z);
  orientar(base.th);
  pivote.updateMatrixWorld(true);
  gizmo.attach(pivote);
  modoGizmo(state.gizmo.mode);
}

function colocarPivote(th, z) {
  const R = pielRadio(z, th) + base.prof / 2;
  pivote.position.set(R * Math.cos(th), R * Math.sin(th), z);
}

function modoGizmo(m) {
  state.gizmo.mode = m;
  if (!gizmo) return;
  gizmo.setMode(m);
  gizmo.setSpace("local");
  gizmo.showX = m !== "rotate";
  gizmo.showY = m !== "rotate";
  gizmo.showZ = m === "rotate";             // girar: sólo alrededor del eje que sale del mate
  decoUi();
}

// parámetros del relieve según dónde quedó el pivote
function lecturaGizmo() {
  const th = Math.atan2(pivote.position.y, pivote.position.x);
  const z = THREE.MathUtils.clamp(pivote.position.z, 0, state.summary.altura_mm);
  const q0 = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(
    new THREE.Vector3(-Math.sin(th), Math.cos(th), 0), new THREE.Vector3(0, 0, 1),
    new THREE.Vector3(Math.cos(th), Math.sin(th), 0)));
  const q = q0.invert().multiply(pivote.quaternion);
  let rot = base.rot + THREE.MathUtils.radToDeg(2 * Math.atan2(q.z, q.w));
  rot = ((rot + 180) % 360 + 360) % 360 - 180;
  const k = THREE.MathUtils.clamp((pivote.scale.x + pivote.scale.y) / 2, 0.2, 5);
  return { th, z, rot, k };
}

function moverGizmo() {
  const L = lecturaGizmo();
  if (state.gizmo.mode === "translate") {
    // se queda pegado a la superficie: del punto movido sale el nuevo giro y la altura
    colocarPivote(L.th, L.z);
    orientar(L.th, THREE.MathUtils.degToRad(L.rot - base.rot));
  } else if (state.gizmo.mode === "scale") {
    pivote.scale.set(L.k, L.k, 1);
  }
  envolverEn(L.th, L.z, L.rot, state.gizmo.mode === "scale" ? L.k : 1);
  state.gizmo.moves = (state.gizmo.moves || 0) + 1;
}

function soltarGizmo() {
  const d = state.deco;
  const L = lecturaGizmo();
  if (state.gizmo.mode === "translate") {
    d.angulo = Math.round(THREE.MathUtils.radToDeg(L.th) * 10) / 10;
    d.z = Math.round(L.z * 10) / 10;
  } else if (state.gizmo.mode === "rotate") {
    d.rot = Math.round(L.rot);
  } else {
    d.alto = Math.round(THREE.MathUtils.clamp(base.alto * L.k, 4, 120) * 10) / 10;
  }
  state.gizmo.drags++;
  decoUi();
  build();
}

$("gizmo").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-m]");
  if (b) modoGizmo(b.dataset.m);
});
window.addEventListener("keydown", (e) => {               // atajos como en Rhino/Blender
  if (e.target.closest("input, select, textarea") || !gizmo?.object) return;
  const m = { g: "translate", w: "translate", r: "rotate", e: "rotate", s: "scale" }[e.key.toLowerCase()];
  if (m) modoGizmo(m);
});

// ------------------------------------------------------------------ cebar el mate
const FASE_TXT = { llenar: "Cargando la yerba…", "montañita": "Inclinando para armar la montañita…",
  cebar: "Cebando con agua caliente por el costado…", bombilla: "Poniendo la bombilla…", listo: "¡Listo para tomar!" };

function cebadoUi() {
  const c = cebado.info();
  $("ver-yerba").checked = c.flags.yerba;
  $("ver-agua").checked = c.flags.agua;
  $("cebado-fase").textContent = c.enEscena ? FASE_TXT[c.fase] || "" : "";
  $("cebar").textContent = c.playing ? "■ Cebando…" : "▶ Cebar el mate";
  for (const id of ["gota", "olas"]) $(id).disabled = !(c.flags.agua && c.enEscena);
}

for (const [k, n] of Object.entries(ESTILOS)) $("bombilla-estilo").add(new Option(n, k));
$("bombilla-estilo").addEventListener("change", () => cebado.setEstilo($("bombilla-estilo").value));
$("cebar").addEventListener("click", () => { cebado.play(); cebadoUi(); });
$("ver-yerba").addEventListener("change", () => { cebado.setFlag("yerba", $("ver-yerba").checked); cebadoUi(); });
$("ver-agua").addEventListener("change", () => { cebado.setFlag("agua", $("ver-agua").checked); cebadoUi(); });
$("ver-bombilla").addEventListener("change", () => cebado.setFlag("bombilla", $("ver-bombilla").checked));
$("ver-vapor").addEventListener("change", () => cebado.setFlag("vapor", $("ver-vapor").checked));
$("montanita").addEventListener("input", () => { $("o-montanita").textContent = $("montanita").value + "°"; });
$("montanita").addEventListener("change", () => { cebado.setAlfa(+$("montanita").value); cebadoUi(); });
$("separar").addEventListener("input", () => {
  cebado.setLoop(false);
  $("separar-loop").setAttribute("aria-pressed", "false");
  $("separar-loop").textContent = "▶ Animar";
  cebado.setSeparar(+$("separar").value / 100);
  $("o-separar").textContent = $("separar").value + " %";
});
$("separar-loop").addEventListener("click", () => {
  const on = $("separar-loop").getAttribute("aria-pressed") !== "true";
  cebado.setLoop(on);
  $("separar-loop").setAttribute("aria-pressed", String(on));
  $("separar-loop").textContent = on ? "■ Parar" : "▶ Animar";
});
cebado.onSeparar = (k) => { $("separar").value = Math.round(k * 100); $("o-separar").textContent = Math.round(k * 100) + " %"; };
$("gota").addEventListener("click", () => cebado.gota());
$("olas").addEventListener("click", () => cebado.olas());
setInterval(cebadoUi, 300);

// ------------------------------------------------------------------ marca debajo de la base (Pro)
function marcaReport(m) {
  if (m) $("brand-msg").textContent = `"${m.texto}" grabada debajo de la base (${fmtNum(m.cap_mm, 1)} mm).`;
  else if (state.summary?.warnings?.some((w) => w.startsWith("Marca"))) $("brand-msg").textContent = state.summary.warnings.find((w) => w.startsWith("Marca"));
  else $("brand-msg").textContent = "Sin marca.";
  state.marcaReport = m || null;
}

function marcaUi() {
  const can = !!state.auth?.perms.brand;
  $("brand").disabled = !can || !state.ready;
  $("brand-apply").disabled = !can || !state.ready;
  $("brand-lock").hidden = can;
  $("brand-lock").title = "Cambiar la marca es parte del paquete Pro";
  if (!can) $("brand").value = state.info?.marca || "Eden3D";
}

async function aplicarMarca() {
  if (!state.auth?.perms.brand) return;
  const r = await call("marca", { text: $("brand").value });
  if (r.error) {
    $("brand-msg").textContent = r.error;
    $("brand-msg").classList.add("err");
    return;
  }
  $("brand-msg").classList.remove("err");
  $("brand").value = r.text;
  state.marca = r.text;
  build();
}
$("brand-apply").addEventListener("click", () => aplicarMarca());
$("brand").addEventListener("keydown", (e) => { if (e.key === "Enter") aplicarMarca(); });

// ------------------------------------------------------------------ cuña
$("cuna").addEventListener("change", () => {
  state.cuna = $("cuna").checked;
  $("cuna-row").hidden = !state.cuna;
  build();
});
$("cuna-ang").addEventListener("input", () => { $("o-cuna").textContent = $("cuna-ang").value + "°"; });
$("cuna-ang").addEventListener("change", () => build());

mountAccount($("account"));
onAuth((a) => {
  const antes = state.auth;
  state.auth = a;
  marcaUi();
  if (state.marca !== null && !a.perms.brand) { state.marca = null; build(); }
  else if (antes && antes.role !== a.role && state.ready) build();
});
window.addEventListener("error", (e) => state.errors.push(String(e.message)));
main();
