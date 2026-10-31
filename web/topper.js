// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// "Topper para tortas": tu texto con la tipografía que quieras, todo unido en una pieza,
// y el número de años aparte; los dos clavados en la torta que elijas.
import * as THREE from "three";
import { pantallaCarga } from "./cargando.js";
import { Viewer, SCENES } from "./viewer.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";
import { Torta, TORTAS } from "./torta.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// estado visible para los tests e2e (window.__topper)
const state = { ready: false, busy: false, info: null, summary: null, summaryNum: null, parts: [], builds: 0,
  numBuilds: 0, errors: [], auth: null, scene: "estudio", torta: true };
window.__topper = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("topper-worker.js");
pantallaCarga({ motor: "topper", worker, estado: state });   // la impresora imprimiendo mientras carga
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
viewer.viewDist = 1.1;
viewer.mats.TOPPER = new THREE.MeshStandardMaterial({ color: 0xc9b6ec, roughness: 0.55, metalness: 0, side: THREE.DoubleSide });
viewer.mats.LETRAS = new THREE.MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.5, metalness: 0, side: THREE.DoubleSide });
viewer.mats.NUMERO = viewer.mats.TOPPER;                // el número, con los mismos colores
viewer.mats.NUMERO_LETRAS = viewer.mats.LETRAS;
window.__topperViewer = viewer;

// la torta (apoyada en la mesa) con el topper y el número clavados; modo cumpleaños
const tortaV = new Torta(viewer);
const torta = tortaV.grupo;
window.__topperTorta = tortaV;
const pose = new THREE.Group();            // el topper parado y clavado en la torta
pose.name = "POSE";
const poseN = new THREE.Group();           // el número de años, al lado
poseN.name = "POSE_NUMERO";
const numeroOn = () => $("numero-on").checked;
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: pose.children.map((m) => m.name), numero: poseN.parent ? poseN.children.map((m) => m.name) : [],
  triangles: viewer.triangles, frames: viewer.stats.frames,
  torta: !!torta.parent && torta.visible, parado: Math.abs(pose.rotation.x) > 1, scene: viewer.sceneKey,
  color: "#" + viewer.mats.TOPPER.color.getHexString(), letras: "#" + viewer.mats.LETRAS.color.getHexString(),
  ...tortaV.info(),
}) });

// medidas en el mundo (y = arriba, la mesa en y = 0), para los tests
window.__topperMedir = () => {
  const B = (o) => new THREE.Box3().setFromObject(o);
  const t = torta.parent && torta.visible ? B(torta) : null, p = B(pose);
  const n = poseN.parent && poseN.children.length ? B(poseN) : null;
  return { tortaPiso: t ? +t.min.y.toFixed(2) : null, tortaArriba: t ? +(tortaV.arriba).toFixed(2) : null,
    topperAbajo: +p.min.y.toFixed(2), topperArriba: +p.max.y.toFixed(2),
    topperX: [+p.min.x.toFixed(1), +p.max.x.toFixed(1)],
    numeroAbajo: n ? +n.min.y.toFixed(2) : null, numeroArriba: n ? +n.max.y.toFixed(2) : null,
    numeroX: n ? [+n.min.x.toFixed(1), +n.max.x.toFixed(1)] : null };
};

// encuadre fijo de la escena (torta + topper + número): agregar un nombre no "baja" la torta
function encuadrar() {
  const box = new THREE.Box3().setFromObject(viewer.model);
  if (box.isEmpty()) return;
  const parado = $("torta").checked;
  // las estrellas son el topper y el número: se encuadran con la parte de arriba de la torta
  const foco = parado ? new THREE.Box3().setFromObject(pose) : box.clone();
  if (parado && poseN.parent && poseN.children.length) foco.union(new THREE.Box3().setFromObject(poseN));
  if (parado) foco.expandByPoint(new THREE.Vector3(box.min.x * 0.8, tortaV.arriba * 0.45, box.max.z * 0.8));
  viewer.viewDir = parado ? new THREE.Vector3(-0.16, 0.36, 1) : new THREE.Vector3(0, 1.4, 0.5);
  viewer.viewDist = parado ? 1.15 : 1.1;
  viewer.fit(foco);
  const c = box.getCenter(new THREE.Vector3());
  viewer.contact.position.set(c.x, 0.3, c.z);
  const sz = box.getSize(new THREE.Vector3());
  viewer.contact.scale.set(sz.x * 1.3, sz.z * 1.3, 1);
}

// ancho de cada pieza (mm) y dónde va cada una: el topper y el número uno al lado del otro
function lugares() {
  const wT = state.summary?.valid ? state.summary.medidas_mm[0] : +$("ancho").value;
  const conN = numeroOn() && state.summaryNum?.valid;
  const wN = conN ? state.summaryNum.medidas_mm[0] : 0;
  const gap = conN ? 14 : 0;
  return { wT, wN, conN, total: wT + gap + wN, xT: -(wN + gap) / 2, xN: (wT + gap) / 2 };
}

// pone el topper (y el número) parados y clavados en la torta, o acostados en la mesa
function posar(animar = true) {
  const m = viewer.model;
  for (const o of m.children.filter((o) => o.isMesh)) {
    m.remove(o);
    (o.name.startsWith("NUMERO") ? poseN : pose).add(o);
  }
  if (!pose.parent) m.add(pose);
  const L = lugares();
  if (L.conN && !poseN.parent) m.add(poseN);
  if (!L.conN && poseN.parent) { m.remove(poseN); tortaV.soltar(poseN); }
  const parado = $("torta").checked;
  for (const p of [pose, poseN]) {
    p.rotation.set(parado ? Math.PI / 2 : 0, 0, 0);
    p.position.set(0, 0, 0);
  }
  if (parado) {
    tortaV.armar(L.total, $("torta-tipo").value);
    if (!torta.parent) m.add(torta);
    torta.visible = true;
    const largo = +$("largo").value;
    tortaV.clavar(pose, largo, false, { x: L.xT });
    if (L.conN) tortaV.clavar(poseN, largo, false, { x: L.xN, y: -16 });
    encuadrar();                                 // encuadra con todo ya en su lugar
    if (animar) {
      tortaV.clavar(pose, largo, true, { x: L.xT });
      if (L.conN) tortaV.clavar(poseN, largo, true, { x: L.xN, y: -16, retraso: 0.35 });
    }
  } else {
    torta.visible = false;
    if (tortaV.fiesta) fiesta(false);
    const inv = m.matrixWorld.clone().invert();
    for (const [p, x] of [[pose, L.xT], [poseN, L.xN]]) {
      if (!p.parent) continue;
      p.position.x = x;
      p.updateMatrixWorld(true);
      const b = new THREE.Box3().setFromObject(p);
      p.position.z = -b.min.clone().applyMatrix4(inv).z;        // apoyado en la mesa
    }
    encuadrar();
  }
}

function fiesta(on) {
  if (on && !$("torta").checked) { $("torta").checked = true; posar(false); }
  tortaV.setFiesta(on);
  $("fiesta").setAttribute("aria-pressed", String(on));
  $("fiesta").textContent = on ? "■ Terminar" : "🎉 Cumpleaños";
}

// ------------------------------------------------------------------ opciones
const SL = { ancho: [0, " mm"], contorno: [1, " mm"], grosor: [1, " mm"], letras: [1, " mm"], largo: [0, " mm"] };

// ?calidad=normal: el visor muestra la malla de exportación (más fina; para fotos)
const CALIDAD = new URLSearchParams(location.search).get("calidad") === "normal" ? "normal" : "preview";

function opts() {
  const lineas = [];
  for (const n of [1, 2, 3]) {
    const t = $("linea-" + n).value.trim();
    if (t) lineas.push({ texto: t, fuente: $("fuente-" + n).value, escala: +$("escala-" + n).value });
  }
  const o = { lineas, estilo: $("estilo").value, marco: $("marco").value, palitos: +$("palitos").value, calidad: CALIDAD };
  for (const k of Object.keys(SL)) o[k] = +$(k).value;
  o.numero = { activo: numeroOn(), numero: $("numero").value.trim(), estilo: $("estilo-num").value,
    fuente: $("fuente-num").value, alto: +$("alto-num").value, palitos: +$("palitos-num").value };
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
  for (const id of ["dl3mf", "dlstl", "photo", "dlletras"]) $(id).disabled = !ok;
  const okN = ok && numeroOn() && !!state.summaryNum?.valid;
  for (const id of ["dlnum", "dlnumletras"]) $(id).disabled = !okN;
}

function colores(s) {
  if (s.estilo === "doble") {
    return [["Dos colores", `base ${num(s.grosor_mm)} mm + letras ${num(s.letras_mm)} mm arriba · pausá y cambiá el filamento a los ${num(s.cambio_mm)} mm`, "f-colores"]];
  }
  if (s.estilo === "ams") {
    return [["Dos colores", `misma altura (${num(s.grosor_mm)} mm): las letras de color en las últimas ${num(s.capa_color_mm)} mm · para AMS / multicolor`, "f-colores"]];
  }
  return [];
}

function showReport() {
  const s = state.summary || {};
  const n = numeroOn() ? state.summaryNum : null;
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Medidas", `${Math.round(s.medidas_mm[0])} × ${Math.round(s.medidas_mm[1])} × ${num(s.medidas_mm[2])} mm`, "f-medidas"],
    ["Líneas", s.lineas.map((l) => `${esc(l.texto)} (${num(l.alto_mm, 0)} mm)`).join(" · "), "f-lineas"],
    ["Una sola pieza", s.puentes ? `sí · ${s.puentes} puente${s.puentes === 1 ? "" : "s"}` : "sí", "f-unida"],
    ...(s.huecos ? [["Huecos de las letras", `${s.huecos_abiertos} de ${s.huecos} abiertos`, "f-huecos", "minor"]] : []),
    ...colores(s),
    ...(n && n.valid ? [["Número", `${esc(n.numero)} · ${Math.round(n.medidas_mm[0])} × ${Math.round(n.medidas_mm[1])} mm · una pieza`, "f-numero"]] : []),
    ["Cálculo", `${s.seconds}${n && n.valid ? " + " + n.seconds : ""} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  const errs = [...(s.errors || []), ...(n && !n.valid ? n.errors || [] : [])];
  const warns = [...(s.warnings || []), ...(n && n.valid ? (n.warnings || []).map((w) => "Número: " + w) : [])];
  $("warnings").innerHTML = [...errs.map((e) => `<li class="err">${esc(e)}</li>`), ...warns.map((w) => `<li>${esc(w)}</li>`)].join("");
}

// las mallas del topper y del número juntas en el visor
let partsT = [], partsN = [];
function mostrar(animar = true) {
  pose.clear();
  poseN.clear();
  viewer.showModel([...partsT, ...(numeroOn() ? partsN : [])], null, true);
  viewer.mats.TOPPER.color.set($("color").value);
  viewer.mats.LETRAS.color.set($("color-letras").value);
  posar(animar);
  $("dlletras").hidden = !partsT.some((p) => p.name === "LETRAS");
  $("dlnum").hidden = !numeroOn();
  $("dlnumletras").hidden = !numeroOn() || !partsN.some((p) => p.name === "NUMERO_LETRAS");
}

// qué = "todo" (topper y número), "numero" (sólo el número)
let pendingBuild = null;
async function build(que = "todo") {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = pendingBuild === "todo" || que === "todo" ? "todo" : que; return; }
  const o = opts();
  setBusy(true, que === "numero" ? "Armando el número…" : "Armando el topper…");
  try {
    if (que === "todo") {
      const r = await call("build", { opts: o });
      state.summary = r.summary;
      state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
      if (r.summary.valid) partsT = r.parts;
    }
    if (numeroOn() && state.summary?.valid) {
      $("busy-text").textContent = "Armando el número…";
      const rn = await call("build_numero", { opts: o });
      state.summaryNum = rn.summary;
      if (rn.summary.valid) partsN = rn.parts;
      state.numBuilds++;
    }
    showReport();
    if (state.summary.valid) mostrar();
    state.builds++;
    if (state.summary.valid) state.builtOpts = o;
    const n = numeroOn() ? state.summaryNum : null;
    const err = !state.summary.valid ? (state.summary.errors || ["No se pudo armar el topper"])[0]
      : (n && !n.valid ? (n.errors || ["No se pudo armar el número"])[0] : null);
    setStatus(err || `Listo · ${state.summary.seconds}${n ? " + " + n.seconds : ""} s`, err ? "err" : "ok");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) {
    const q = pendingBuild;
    pendingBuild = null;
    return build(q);
  }
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

function takePhoto() {
  const r = viewer.photo(1080, 1350);
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "topper"}.png` });
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

function sliderText(k) {
  const [d, u] = SL[k];
  return num($(k).value, d) + u;
}

function letrasUi() {
  const e = $("estilo").value;
  $("letras-row").hidden = e === "simple";
  $("letras-lbl").textContent = e === "ams" ? "Color" : "Letras";
  const h = $("colores-hint");
  h.hidden = e === "simple";
  h.textContent = e === "doble"
    ? "Letras en relieve arriba de la base: en cualquier impresora, pausá en esa capa y cambiá el filamento a mano."
    : "Letras al ras de la base, del mismo alto: cada capa de arriba lleva los dos colores (Bambu Lab con AMS u otra multicolor).";
  $("numero-opts").hidden = !numeroOn();
}

// ------------------------------------------------------------------ arranque
async function main() {
  sections();
  sceneButtons();
  $("torta-tipo").innerHTML = TORTAS.map(([k, n]) => `<option value="${k}">${esc(n)}</option>`).join("");
  try {
    const boot = await call("init");
    state.info = boot.info;
    const I = boot.info;
    const fuentes = I.fuentes.map((f) => `<option value="${f.id}">${esc(f.nombre)}</option>`).join("");
    const def = { 1: "great_vibes", 2: "great_vibes", 3: "dancing_script" };
    for (const n of [1, 2, 3]) {
      $("fuente-" + n).innerHTML = fuentes;
      $("fuente-" + n).value = def[n];
      $("fuente-" + n).disabled = false;
    }
    $("fuente-num").innerHTML = fuentes;
    $("fuente-num").value = I.defecto_numero.fuente;
    $("estilo-num").innerHTML = I.estilos_numero.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("estilo-num").value = I.defecto_numero.estilo;
    $("estilo").innerHTML = I.estilos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("marco").innerHTML = I.marcos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    for (const id of ["estilo", "marco", "fuente-num", "estilo-num"]) $(id).disabled = false;
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
for (const n of [1, 2, 3]) {
  $("linea-" + n).addEventListener("input", () => { clearTimeout(tTexto); tTexto = setTimeout(() => build(), 700); });
  $("fuente-" + n).addEventListener("change", () => build());
  $("escala-" + n).addEventListener("change", () => build());
}
for (const id of ["estilo", "marco", "palitos"]) $(id).addEventListener("change", () => { letrasUi(); build(); });
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build());
}
// el número: sólo se recalcula el número
let tNum = null;
$("numero").addEventListener("input", () => {
  $("numero").value = $("numero").value.replace(/\D/g, "").slice(0, 3);
  clearTimeout(tNum);
  tNum = setTimeout(() => build("numero"), 600);
});
for (const id of ["estilo-num", "fuente-num", "palitos-num", "alto-num"]) $(id).addEventListener("change", () => build("numero"));
$("alto-num").addEventListener("input", () => { $("o-alto-num").textContent = $("alto-num").value + " mm"; });
$("numero-on").addEventListener("change", () => {
  letrasUi();
  if (numeroOn() && !state.summaryNum?.valid) build("numero");
  else if (state.summary?.valid) { mostrar(); showReport(); setBusy(false); }
});
$("torta-tipo").addEventListener("change", () => { if (state.summary?.valid && $("torta").checked) posar(); });
$("build").addEventListener("click", () => build());
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl", "TOPPER"));
$("dlletras").addEventListener("click", () => download("stl", "LETRAS"));
$("dlnum").addEventListener("click", () => download("stl", "NUMERO"));
$("dlnumletras").addEventListener("click", () => download("stl", "NUMERO_LETRAS"));
$("photo").addEventListener("click", () => takePhoto());
$("torta").addEventListener("change", () => { state.torta = $("torta").checked; if (state.summary?.valid) posar(); });
$("fiesta").addEventListener("click", () => fiesta(!tortaV.fiesta));
$("color").addEventListener("change", () => viewer.mats.TOPPER.color.set($("color").value));
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
