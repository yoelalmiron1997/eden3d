// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// "Mate con hueco": mate imperial para imprimir en 3D con el hueco exacto del inserto.
import { Viewer, LIGHTS, SCENES } from "./viewer.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mm = (v, d = 1) => (v === undefined || v === null ? "—" : `${(+v).toFixed(d).replace(".", ",")} mm`);

// estado visible para los tests e2e (window.__mate)
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  stl: null, auth: null, scene: "estudio", light: "estudio" };
window.__mate = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("mate-worker.js");
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
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.meshNames(), triangles: viewer.triangles, frames: viewer.stats.frames, cut: viewer.cut,
  scene: viewer.sceneKey, light: viewer.lightKey, slicer: viewer.slicerInfo(),
  inserto: !!(viewer.model.getObjectByName("INSERTO") || {}).visible,
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
  for (const id of ["dlstl", "dl3mf", "photo"]) $(id).disabled = !ok;
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

async function download(kind) {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  if (!state.auth?.perms.download) {
    openLogin("Ingresá o creá tu cuenta gratis para descargar los archivos para imprimir.");
    return;
  }
  setBusy(true, kind === "3mf" ? "Armando el 3MF (calidad de impresión)…" : "Armando el STL…");
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

function takePhoto() {
  const r = viewer.photo(1080, 1350);
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
$("slicer").addEventListener("change", () => slicerUi(viewer.setSlicer($("slicer").checked, "MACETA")));
$("layer").addEventListener("input", () => { viewer.playSlicer(false); slicerUi(viewer.setLayer(+$("layer").value)); });
$("play-layers").addEventListener("click", () => { viewer.playSlicer(!viewer.slicer.playing); slicerUi(); });

mountAccount($("account"));
onAuth((a) => { state.auth = a; });
window.addEventListener("error", (e) => state.errors.push(String(e.message)));
main();
