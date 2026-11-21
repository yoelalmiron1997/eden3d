// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// "Banda de recibida": el collar de cuentas con el texto que quieras (ME ♥ RECIBÍ, el
// nombre, la carrera…), con corazones y pelotitas, listo para imprimir.
import * as THREE from "three";
import { pantallaCarga } from "./cargando.js";
import { botonesPremium } from "./premium.js";
import { pdfConsideraciones } from "./guia-impresion.js";
import { Viewer, SCENES } from "./viewer.js";
import { BandaEscena } from "./banda-escena.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// estado visible para los tests e2e (window.__banda)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  auth: null, scene: "estudio", modo: "collar" };
window.__banda = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("banda-worker.js");
pantallaCarga({ motor: "banda", worker, estado: state });
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
viewer.viewDist = 1.15;
const mat = (color, rough = 0.45) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, side: THREE.DoubleSide });
viewer.mats.DISCO = mat(0xf4f1ea, 0.4);
viewer.mats.LETRAS = mat(0x1d1d1f, 0.5);
viewer.mats.CORAZON = mat(0xf7a8c4, 0.42);
viewer.mats.PELOTITA = mat(0xe0457b, 0.38);
viewer.mats.HILO = mat(0xd9cfc0, 0.8);
window.__bandaViewer = viewer;
const escena = new BandaEscena(viewer);
window.__bandaEscena = escena;
const SOMBRA0 = (({ left, right, top, bottom, near, far }) => ({ left, right, top, bottom, near, far }))(viewer.sun.shadow.camera);
const ANIMADAS = new Set(["persona", "pared"]);
const HINTS = {
  persona: "La soga pasa por todas las cuentas y la banda queda puesta de costado, del hombro a la cadera.",
  pared: "La soga pasa por todas las cuentas y la banda queda colgada de dos clavos, con el texto abajo.",
};

// normales con quiebre: las caras planas y los bordes vivos (bolsillo de la letra, tapas)
// no se promedian con las paredes redondeadas; lo curvo (hilo, pelotita, borde) queda suave
const CREASE = Math.cos(THREE.MathUtils.degToRad(34));
viewer.geom = (p) => {
  const P = new Float32Array(p.positions), I = new Uint32Array(p.indices);
  const nt = I.length / 3, nv = P.length / 3;
  const fn = new Float32Array(nt * 3);
  for (let t = 0; t < nt; t++) {
    const a = I[3 * t] * 3, b = I[3 * t + 1] * 3, c = I[3 * t + 2] * 3;
    const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
    const wx = P[c] - P[a], wy = P[c + 1] - P[a + 1], wz = P[c + 2] - P[a + 2];
    const nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
    const l = Math.hypot(nx, ny, nz) || 1;
    fn[3 * t] = nx / l; fn[3 * t + 1] = ny / l; fn[3 * t + 2] = nz / l;
  }
  // caras de cada vértice
  const cnt = new Uint32Array(nv + 1);
  for (let k = 0; k < I.length; k++) cnt[I[k] + 1]++;
  for (let v = 0; v < nv; v++) cnt[v + 1] += cnt[v];
  const fill = cnt.slice(0, nv), inc = new Uint32Array(I.length);
  for (let k = 0; k < I.length; k++) inc[fill[I[k]]++] = (k / 3) | 0;
  const pos = new Float32Array(I.length * 3), nor = new Float32Array(I.length * 3);
  for (let k = 0; k < I.length; k++) {
    const v = I[k], t = (k / 3) | 0;
    let sx = 0, sy = 0, sz = 0;
    for (let q = cnt[v]; q < cnt[v + 1]; q++) {
      const u = inc[q];
      if (fn[3 * u] * fn[3 * t] + fn[3 * u + 1] * fn[3 * t + 1] + fn[3 * u + 2] * fn[3 * t + 2] >= CREASE) {
        sx += fn[3 * u]; sy += fn[3 * u + 1]; sz += fn[3 * u + 2];
      }
    }
    const l = Math.hypot(sx, sy, sz) || 1;
    pos[3 * k] = P[3 * v]; pos[3 * k + 1] = P[3 * v + 1]; pos[3 * k + 2] = P[3 * v + 2];
    nor[3 * k] = sx / l; nor[3 * k + 1] = sy / l; nor[3 * k + 2] = sz / l;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  const idx = new Uint32Array(I.length);
  for (let k = 0; k < I.length; k++) idx[k] = k;
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
};
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.model.children.filter((m) => m.isMesh).map((m) => m.name), triangles: viewer.triangles,
  disco: "#" + viewer.mats.DISCO.color.getHexString(), letras: "#" + viewer.mats.LETRAS.color.getHexString(),
  corazon: "#" + viewer.mats.CORAZON.color.getHexString(), pelotita: "#" + viewer.mats.PELOTITA.color.getHexString(),
  escena: { ...escena.stats },
}) });

// ------------------------------------------------------------------ opciones
const SL = { largo: [0, " cm"], diametro: [0, " mm", "Ø "], agujero: [1, " mm"], profundidad: [1, " mm"] };
const COLORES = { "c-disco": "DISCO", "c-letras": "LETRAS", "c-corazon": "CORAZON", "c-pelotita": "PELOTITA" };

function opts() {
  const o = { texto: $("texto").value.trim(), separador: $("separador").value, relleno: $("relleno").value,
    caras: $("caras").value, fuente: $("fuente").value, vista: state.modo };
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

function contarLetras() {
  const n = $("texto").value.replace(/\s+/g, "").length;
  const max = state.info?.limites.letras || 24;
  $("cuenta-letras").textContent = `${n} de ${max} letras · un disco por letra`;
}

function showReport(s) {
  $("sku").textContent = s.sku || "—";
  const discos = (s.discos || []).map((d) => `${esc(d.letra)}${d.cantidad > 1 ? " ×" + d.cantidad : ""}`).join(" · ");
  const M = s.medidas_mm || {};
  const facts = s.valid ? [
    ["Collar", `${num(s.largo_cm, 0)} cm de largo · ${s.cuentas} cuentas`, "f-collar"],
    ["Discos", `${s.total_discos}: ${discos}`, "f-discos"],
    ["Corazones", String(s.corazones), "f-corazones"],
    ["Pelotitas", String(s.pelotitas), "f-pelotitas"],
    ["Letra", `${num(s.letra_mm)} mm · incrustada ${num(s.profundidad_mm)} mm ${s.caras === "dos" ? "en las dos caras" : "en una cara"}`, "f-letra"],
    ["Hilo", `elástico o cordón de hasta Ø ${num(s.agujero_mm - 1)} mm, unos ${s.hilo_cm} cm`, "f-hilo"],
    ["Piezas", [M.DISCO && `disco ${Math.round(M.DISCO[0])} × ${num(M.DISCO[2])} mm`,
      M.CORAZON && `corazón ${Math.round(M.CORAZON[0])} × ${Math.round(M.CORAZON[1])} × ${num(M.CORAZON[2])} mm`,
      M.PELOTITA && `pelotita Ø ${Math.round(M.PELOTITA[0])} mm`].filter(Boolean).join(" · "), "f-piezas", "minor"],
    ["Cálculo", `${s.seconds} s`, "f-tiempo", "minor"],
  ] : [];
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
}

function pintar() {
  for (const [id, m] of Object.entries(COLORES)) viewer.mats[m].color.set($(id).value);
}

let pendingBuild = false;
async function build() {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = true; return; }
  const o = opts();
  setBusy(true, "Armando el collar…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      const marco = [o.vista, o.largo, o.diametro, o.texto.length > 0].join("|");   // reencuadra si cambia el tamaño
      if (ANIMADAS.has(r.summary.vista)) mostrarAnimada(r, marco !== state.marco);
      else {
        salirAnimada();
        viewer.showModel(r.parts, null, marco !== state.marco);
      }
      state.marco = marco;
      pintar();
      state.builtOpts = o;
    }
    state.builds++;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : (r.summary.errors || ["No se pudo armar el collar"])[0],
      r.summary.valid ? "ok" : "err");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) { pendingBuild = false; build(); }
}

// vistas animadas: las mallas de cada pieza (en el marco de la cuenta) las reparte la escena
function mostrarAnimada(r, refit) {
  viewer.showModel([], null, false);                  // limpia el modelo (agua, despiece, etc.)
  const unicas = {};
  for (const p of r.parts) {
    const base = p.name.split("#")[0];
    const mesh = new THREE.Mesh(viewer.geom(p), viewer.mats[base]);
    mesh.name = base;
    (unicas[p.name] = unicas[p.name] || []).push(mesh);
  }
  const g = escena.montar(r.summary.vista, unicas, r.summary);
  viewer.triangles = r.summary.triangulos;
  const todo = new THREE.Box3().setFromObject(g);
  const encuadre = escena.cajaEncuadre();
  viewer.sceneBox = () => todo.clone();
  viewer.center = encuadre.getCenter(new THREE.Vector3());
  const sz = todo.getSize(new THREE.Vector3());
  viewer.contact.scale.set(Math.min(sz.x, 420) * 1.2, Math.min(sz.z, 420) * 1.2, 1);
  viewer.contact.position.set(viewer.center.x, todo.min.y + 0.3, viewer.center.z);
  // sombras: la escena es más grande que una pieza
  const e = encuadre.getSize(new THREE.Vector3()), rad = Math.max(e.x, e.y, e.z) * 0.75 + 80;
  Object.assign(viewer.sun.shadow.camera, { left: -rad, right: rad, top: rad, bottom: -rad, near: -3000, far: 4000 });
  viewer.sun.shadow.camera.updateProjectionMatrix();
  viewer.placeSun();
  viewer.fitScene();
  if (refit) {
    viewer.fit(encuadre, r.summary.vista === "persona" ? new THREE.Vector3(-0.35, 0.12, 1) : new THREE.Vector3(-0.2, 0.08, 1));
    viewer.needFit = false;
  }
  $("repetir").hidden = false;
  $("hint-modo").hidden = false;
  $("hint-modo").textContent = HINTS[r.summary.vista];
}

function salirAnimada() {
  if (!escena.grupo) return;
  escena.quitar();
  viewer.sceneBox = null;
  Object.assign(viewer.sun.shadow.camera, SOMBRA0);
  viewer.sun.shadow.camera.updateProjectionMatrix();
  $("repetir").hidden = true;
  $("hint-modo").hidden = true;
}

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
  setBusy(true, kind === "3mf" ? "Armando el 3MF…" : "Armando los STL…");
  try {
    const r = await call(kind, { opts: state.builtOpts || opts() });
    state.lastDownload = { name: r.name, bytes: r.data.byteLength };
    save(r.name, r.data, kind === "3mf" ? "model/3mf" : "application/zip");
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
    escena.terminar();
    const foto = viewer.photo(1200, 744, "image/jpeg").url;
    const doc = await pdfConsideraciones("banda", state.summary, { foto });
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
  escena.terminar();
  const r = viewer.photo(1080, 1350);
  const a = Object.assign(document.createElement("a"), { href: r.url, download: `${state.summary?.sku || "banda"}.png` });
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

function modoButtons() {
  for (const b of $("vistas-modo").querySelectorAll("button[data-modo]")) b.setAttribute("aria-pressed", String(b.dataset.modo === state.modo));
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

function sliderText(k) {
  const [d, u, pre = ""] = SL[k];
  return pre + num($(k).value, d) + u;
}

// ------------------------------------------------------------------ arranque
async function main() {
  sections();
  sceneButtons();
  try {
    const boot = await call("init");
    state.info = boot.info;
    const I = boot.info;
    const opciones = (id, lista, def) => { $(id).innerHTML = lista.map((e) => `<option value="${e.id}">${esc(e.nombre)}</option>`).join(""); $(id).value = def; $(id).disabled = false; };
    opciones("separador", I.separadores, I.defecto.separador);
    opciones("relleno", I.rellenos, I.defecto.relleno);
    opciones("caras", I.caras, I.defecto.caras);
    opciones("fuente", I.fuentes, I.defecto.fuente);
    contarLetras();
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
$("texto").addEventListener("input", () => { contarLetras(); clearTimeout(tTexto); tTexto = setTimeout(build, 650); });
for (const id of ["separador", "relleno", "caras", "fuente"]) $(id).addEventListener("change", () => build());
for (const k of Object.keys(SL)) {
  $(k).addEventListener("input", () => { $("o-" + k).textContent = sliderText(k); });
  $(k).addEventListener("change", () => build());
}
$("vistas-modo").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-modo]");
  if (!b || b.dataset.modo === state.modo) return;
  state.modo = b.dataset.modo;
  modoButtons();
  build();
});
$("build").addEventListener("click", () => build());
$("repetir").addEventListener("click", () => escena.empezar());
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl"));
botonesPremium(state, [
  { el: $("photo"), que: "El render (foto)", accion: () => takePhoto() },
  { el: $("pdf"), que: "El PDF con las consideraciones de impresión", accion: () => consideracionesPdf() },
]);
for (const id of Object.keys(COLORES)) $(id).addEventListener("change", pintar);
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
