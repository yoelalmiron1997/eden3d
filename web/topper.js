// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// "Topper para tortas": tu texto con la tipografía que quieras, todo unido en una pieza.
import * as THREE from "three";
import { Viewer, SCENES } from "./viewer.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";
import { Torta } from "./torta.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// estado visible para los tests e2e (window.__topper)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  auth: null, scene: "estudio", torta: true };
window.__topper = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("topper-worker.js");
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
window.__topperViewer = viewer;

// la torta (apoyada en la mesa) con el topper clavado; modo cumpleaños con confeti
const tortaV = new Torta(viewer);
const torta = tortaV.grupo;
window.__topperTorta = tortaV;
const pose = new THREE.Group();            // el topper parado y clavado en la torta
pose.name = "POSE";
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: pose.children.map((m) => m.name), triangles: viewer.triangles, frames: viewer.stats.frames,
  torta: !!torta.parent && torta.visible, parado: Math.abs(pose.rotation.x) > 1, scene: viewer.sceneKey,
  color: "#" + viewer.mats.TOPPER.color.getHexString(), letras: "#" + viewer.mats.LETRAS.color.getHexString(),
  ...tortaV.info(),
}) });

// medidas en el mundo (y = arriba, la mesa en y = 0), para los tests
window.__topperMedir = () => {
  const B = (o) => new THREE.Box3().setFromObject(o);
  const t = torta.parent && torta.visible ? B(torta) : null, p = B(pose);
  return { tortaPiso: t ? +t.min.y.toFixed(2) : null, tortaArriba: t ? +(tortaV.arriba).toFixed(2) : null,
    topperAbajo: +p.min.y.toFixed(2), topperArriba: +p.max.y.toFixed(2) };
};

// encuadre fijo de la escena (torta + topper): agregar un nombre no "baja" la torta
function encuadrar() {
  const box = new THREE.Box3().setFromObject(viewer.model);
  if (box.isEmpty()) return;
  const parado = $("torta").checked;
  // la estrella es el topper: se encuadra el topper con la parte de arriba de la torta
  const foco = parado ? new THREE.Box3().setFromObject(pose) : box.clone();
  if (parado) foco.expandByPoint(new THREE.Vector3(box.min.x * 0.8, box.max.y * 0 + tortaV.arriba * 0.45, box.max.z * 0.8));
  viewer.viewDir = parado ? new THREE.Vector3(-0.16, 0.36, 1) : new THREE.Vector3(0, 1.4, 0.5);
  viewer.viewDist = parado ? 1.3 : 1.1;
  viewer.fit(foco);
  const c = box.getCenter(new THREE.Vector3());
  viewer.contact.position.set(c.x, 0.3, c.z);
  const sz = box.getSize(new THREE.Vector3());
  viewer.contact.scale.set(sz.x * 1.3, sz.z * 1.3, 1);
}

// pone el topper parado (texto para arriba, mirando a la cámara) y clavado en la torta
function posar(animar = true) {
  const m = viewer.model;
  const piezas = m.children.filter((o) => o.isMesh && (o.name === "TOPPER" || o.name === "LETRAS"));
  for (const o of piezas) { m.remove(o); pose.add(o); }
  if (!pose.parent) m.add(pose);
  const parado = $("torta").checked;
  pose.rotation.set(parado ? Math.PI / 2 : 0, 0, 0);
  pose.position.set(0, 0, 0);
  if (parado) {
    tortaV.armar(+$("ancho").value);
    if (!torta.parent) m.add(torta);
    torta.visible = true;
    tortaV.clavar(pose, +$("largo").value, false);
    encuadrar();                                 // encuadra con el topper ya en su lugar
    if (animar) tortaV.clavar(pose, +$("largo").value, true);
  } else {
    torta.visible = false;
    if (tortaV.fiesta) fiesta(false);
    pose.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(pose);
    const inv = m.matrixWorld.clone().invert();
    pose.position.z = -b.min.clone().applyMatrix4(inv).z;        // apoyado en la mesa
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

function opts() {
  const lineas = [];
  for (const n of [1, 2, 3]) {
    const t = $("linea-" + n).value.trim();
    if (t) lineas.push({ texto: t, fuente: $("fuente-" + n).value, escala: +$("escala-" + n).value });
  }
  const o = { lineas, estilo: $("estilo").value, marco: $("marco").value, palitos: +$("palitos").value };
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
  for (const id of ["dl3mf", "dlstl", "photo", "dlletras"]) $(id).disabled = !ok;
}

function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const facts = s.valid ? [
    ["Medidas", `${Math.round(s.medidas_mm[0])} × ${Math.round(s.medidas_mm[1])} × ${num(s.medidas_mm[2])} mm`, "f-medidas"],
    ["Líneas", s.lineas.map((l) => `${esc(l.texto)} (${num(l.alto_mm, 0)} mm)`).join(" · "), "f-lineas"],
    ["Una sola pieza", s.puentes ? `sí · ${s.puentes} puente${s.puentes === 1 ? "" : "s"}` : "sí", "f-unida"],
    ...(s.estilo === "doble" ? [["Dos colores", `base ${num(s.grosor_mm)} mm + letras ${num(s.letras_mm)} mm · cambio de filamento a ${num(s.grosor_mm)} mm`, "f-colores"]] : []),
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

let pendingBuild = null;
async function build() {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = true; return; }
  const o = opts();
  setBusy(true, "Armando el topper…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      pose.clear();
      viewer.showModel(r.parts, null, true);
      viewer.mats.TOPPER.color.set($("color").value);
      viewer.mats.LETRAS.color.set($("color-letras").value);
      posar();
      $("dlletras").hidden = !r.parts.some((p) => p.name === "LETRAS");
    }
    state.builds++;
    if (r.summary.valid) state.builtOpts = o;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar el topper"])[0],
      r.summary.valid ? "ok" : "err");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) {
    pendingBuild = null;
    return build();
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
  $("letras-row").hidden = $("estilo").value !== "doble";
}

// ------------------------------------------------------------------ arranque
async function main() {
  sections();
  sceneButtons();
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
    $("estilo").innerHTML = I.estilos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("marco").innerHTML = I.marcos.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
    $("estilo").disabled = $("marco").disabled = false;
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
  $("linea-" + n).addEventListener("input", () => { clearTimeout(tTexto); tTexto = setTimeout(build, 700); });
  $("fuente-" + n).addEventListener("change", () => build());
  $("escala-" + n).addEventListener("change", () => build());
}
for (const id of ["estilo", "marco", "palitos"]) $(id).addEventListener("change", () => { letrasUi(); build(); });
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build());
}
$("build").addEventListener("click", () => build());
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl", "TOPPER"));
$("dlletras").addEventListener("click", () => download("stl", "LETRAS"));
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
