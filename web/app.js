// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
import { Viewer, LIGHTS, SCENES } from "./viewer.js";
import { pantallaCarga } from "./cargando.js";
import { renderCare, renderCompat } from "./care.js";
import { makeGuide } from "./guia.js";
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth } from "./auth.js";
import { Patitas } from "./patitas.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const SLIDERS = [
  // clave, etiqueta, máx, paso
  ["tex_count", "Repeticiones", 80, 1],
  ["tex_pitch", "Paso vertical", 60, 0.5],
  ["tex_amp", "Relieve (mm)", 4, 0.1],
  ["tex_duty", "Ancho costilla", 0.8, 0.01],
  ["tex_wob", "Ondulación", 1.5, 0.01],
  ["ondas", "Ondas", 60, 1],
  ["amp_ondas", "Alto de onda", 4, 0.1],
];

// estado visible para los tests e2e (window.__eden)
const state = {
  ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [],
  plants: [], plantBuilds: 0, careTab: null, light: "estudio", scene: "estudio", cobertura: null,
  auth: null, brand: null,
};
window.__eden = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("worker.js");
pantallaCarga({ motor: "macetas", worker, estado: state });   // la impresora imprimiendo mientras carga
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
window.__edenViewer = viewer;
const patitas = new Patitas(viewer);
window.__edenPatitas = patitas;
Object.defineProperty(state, "patitas", { get: () => patitas.info() });
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.meshNames(), triangles: viewer.triangles, plantTriangles: viewer.plantTriangles || 0,
  waterTime: viewer.stats.waterTime, waterLevel: viewer.stats.waterLevel, frames: viewer.stats.frames,
  light: viewer.lightKey, sunAz: viewer.sunAz, cut: viewer.cut,
  sunIntensity: viewer.sun.intensity, lamp: viewer.lamp.intensity,
  scene: viewer.sceneKey, sceneMeshes: viewer.sceneMeshes(), groundVisible: viewer.ground.visible, lowPower: !!viewer.lowPower,
  drops: viewer.stats.drops, growing: viewer.stats.growing, born: viewer.stats.born || [], animTime: viewer.animTime,
  plantGroups: (viewer.plantGroups || []).map((g) => ({ id: g.userData.id, scale: g.scale.x,
    base: [g.position.x, g.position.y, g.position.z], meshes: g.children.length })),
  wind: viewer.windOn && viewer.wind ? viewer.wind.value : 0,
  impacts: viewer.stats.impacts || 0, taps: viewer.stats.taps || 0, panoLoaded: !!viewer.stats.panoLoaded,
  explode: viewer.explode, explodeOffset: viewer.stats.explodeOffset || 0, slicer: viewer.slicerInfo(),
  loop: !!viewer.loop, loopCycles: viewer.stats.loopCycles || 0,
  labels: [...document.querySelectorAll("#labels span")].filter((e) => e.style.opacity !== "0").map((e) => e.textContent),
}) });

// ------------------------------------------------------------------ UI
function opts() {
  const overrides = {};
  for (const [k] of SLIDERS) {
    const v = parseFloat($("s-" + k).value);
    if (v > 0) overrides[k] = v;
  }
  const o = {
    design: $("design").value, size: $("size").value, mode: $("mode").value,
    drain: $("drain").value, quality: $("hq").checked ? "normal" : "preview", overrides,
  };
  // marca personalizada: sólo con permiso (Pro o admin); si no, la del motor (Eden3D)
  if (state.brand !== null && state.auth?.perms.brand) o.brand = state.brand;
  if ($("patitas").value) {
    o.patitas = { tipo: $("patitas").value, pie: $("pies").value, eslabones: +$("eslabones").value,
      holgura: +$("holgura-patas").value };
  }
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
  for (const id of ["build", "dl3mf", "dlstl", "dlstlp", "photo", "pdf"]) $(id).disabled = on || !state.ready;
  if (!on && !state.summary?.valid) for (const id of ["dl3mf", "dlstl", "dlstlp", "photo", "pdf"]) $(id).disabled = true;
  if (!on && !state.parts.some((p) => p.name === "PLATO")) $("dlstlp").disabled = true;
}

const fmt = (v, u = "") => (v === undefined || v === null ? "—" : `${v}${u}`);
function showReport(s) {
  $("sku").textContent = s.sku;
  const A = s.assembly || {};
  const plate = Object.entries(s.parts_g || {})[0];
  const facts = [
    ["Maceta", fmt(s.pot_g, " g PLA"), "f-maceta"],
    ["Tierra", fmt(s.soil_ml, " ml"), "f-tierra"],
    ["Medidas", s.bbox_mm ? s.bbox_mm.map((x) => Math.round(x)).join(" × ") + " mm" : "—", "f-medidas"],
    ["Drenaje", fmt(s.drain_holes, " agujeros"), "f-drenaje", "minor"],
  ];
  if (plate) facts.push(["Plato", fmt(plate[1], " g PLA"), "f-plato", "minor"]);
  if (A.thread_turns !== undefined) {
    facts.push(["Rosca", `${A.thread_turns} vueltas · ${A.thread_engagement_mm} mm`, "f-rosca", "minor"]);
    facts.push(["Luz bajo la maceta", fmt(A.water_gap_under_pot_mm, " mm"), "f-luz", "minor"]);
    facts.push(["Agua mínima", fmt(A.water_min_wet_ml, " ml"), "f-agua-min"]);
    facts.push(["Plato lleno", `${fmt(A.water_reservoir_ml, " ml")} · ${fmt(A.water_over_soil_mm, " mm")} de tierra en remojo`, "f-agua-max"]);
  }
  facts.push(["Cálculo", fmt(s.seconds, " s"), "f-tiempo", "minor"]);
  $("facts").innerHTML = facts.map(([k, v, t, c]) => `<div class="${c || ""}"><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
  $("water-level").hidden = A.dish_inner_r0_mm === undefined;
  brandReport(s);
}

let lastKey = "";
// Si se cambia algo mientras calcula, se vuelve a calcular al terminar (antes se
// perdía el cambio y las plantas quedaban armadas para otro modelo).
let pendingBuild = null;
async function build(refit = false) {
  if (!state.ready) return;
  if (state.busy) { pendingBuild = { refit: refit || (pendingBuild && pendingBuild.refit) }; return; }
  const o = opts();
  const key = JSON.stringify(o);
  setBusy(true, "Calculando la maceta…");
  try {
    const r = await call("build", { opts: o });
    state.summary = r.summary;
    state.parts = r.parts.map((p) => ({ name: p.name, bytes: p.positions.byteLength }));
    showReport(r.summary);
    if (r.summary.valid) {
      viewer.showModel(r.parts, r.summary, refit || key.split('"overrides"')[0] !== lastKey.split('"overrides"')[0]);
      viewer.setColor($("color").value);
      viewer.setCut($("cut").checked);
      viewer.setWater($("water").checked);
      patitas.montar(r.summary.patitas);
      patitasMsg(r.summary.patitas);
      slicerUi();
    }
    state.triangles = viewer.triangles;
    state.meshes = viewer.meshNames();
    state.builds++;
    if (r.summary.valid) state.builtOpts = o;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : "El diseño no es válido con esta combinación", r.summary.valid ? "ok" : "err");
    lastKey = key;
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (pendingBuild) {                                  // hubo cambios durante el cálculo
    const p = pendingBuild;
    pendingBuild = null;
    return build(p.refit);
  }
  if (state.summary?.valid) await updatePlants();
}

// las plantas, la tierra y las descargas usan el modelo que está en pantalla
const builtOpts = () => state.builtOpts || opts();

// ------------------------------------------------------------------ plantas
let plantReq = 0;
async function updatePlants() {
  const ids = state.plants.slice();
  const my = ++plantReq;
  renderCarePanel([]);
  try {
    if (!ids.length) {                                 // sin plantas igual se ve la tierra
      const r = $("decor").checked ? await call("plants", { opts: builtOpts(), ids: [], decor: true, cobertura: state.cobertura }) : { parts: [] };
      if (my !== plantReq) return;
      viewer.showPlants(r.parts, []);
      state.plantBuilds++; state.compat = []; return;
    }
    const r = await call("plants", { opts: builtOpts(), ids, decor: $("decor").checked, cobertura: state.cobertura });
    if (my !== plantReq) return;                       // llegó una selección más nueva
    viewer.showPlants(r.parts, r.ids);
    state.compat = r.compat;
    state.coberturaUsada = r.cobertura;
    coberturaDesc();
    renderCarePanel(r.compat);
    state.plantBuilds++;
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error en plantas: " + e.message, "err");
  }
}

// una planta por tipo: los chips de un mismo grupo se comportan como radio
function plantChips() {
  const max = state.info.max_plantas;
  const grupos = state.info.grupos || [];
  const sel = (id) => state.plants.includes(id);
  const grupoDe = (id) => (state.info.plantas.find((p) => p.id === id) || {}).grupo;
  const usados = new Set(state.plants.map(grupoDe));
  $("plant-list").innerHTML = grupos.map((g) => {
    const ps = state.info.plantas.filter((p) => p.grupo === g.id);
    const lleno = !usados.has(g.id) && state.plants.length >= max;
    return `<div class="pgroup" role="radiogroup" aria-label="${esc(g.nombre)}" data-testid="grupo-${g.id}">
      <h3>${esc(g.nombre)}</h3><div class="chips">${ps.map((p) => `
      <button type="button" class="chip${p.nativa ? " nativa" : ""}" role="radio" data-id="${p.id}" data-testid="planta-${p.id}"
        aria-pressed="${sel(p.id)}" aria-checked="${sel(p.id)}" ${lleno ? "disabled" : ""}
        title="${esc(p.tipo)} · ${esc(p.dificultad)}">${esc(p.nombre)}</button>`).join("")}
      </div></div>`;
  }).join("");
}

function togglePlant(id) {
  const info = state.info;
  const grupo = (x) => (info.plantas.find((p) => p.id === x) || {}).grupo;
  const i = state.plants.indexOf(id);
  if (i >= 0) state.plants.splice(i, 1);
  else {
    const j = state.plants.findIndex((x) => grupo(x) === grupo(id));
    if (j >= 0) state.plants.splice(j, 1, id);          // reemplaza a la del mismo tipo
    else if (state.plants.length < info.max_plantas) state.plants.push(id);
  }
  if (!state.plants.includes(state.careTab)) state.careTab = state.plants[state.plants.length - 1] || null;
  plantChips();
  if (state.ready && !state.busy) updatePlants();
}

function coberturas() {
  $("cobertura").innerHTML = `<option value="">Automática</option>` +
    state.info.coberturas.map((c) => `<option value="${c.id}">${esc(c.nombre)}</option>`).join("");
  $("cobertura").value = state.cobertura || "";
  coberturaDesc();
}

function coberturaDesc() {
  const id = state.cobertura || state.coberturaUsada;
  const c = (state.info?.coberturas || []).find((x) => x.id === id);
  $("cob-desc").textContent = c ? (state.cobertura ? "" : `Sugerida: ${c.nombre}. `) + c.descripcion : "";
}

function sceneButtons() {
  $("scenes").innerHTML = Object.entries(SCENES).map(([k, S]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="escena-${k}" aria-pressed="${k === state.scene}">${S.label}</button>`).join("");
}

function takePhoto() {
  const r = viewer.photo(1080, 1350);
  const a = Object.assign(document.createElement("a"), { href: r.url,
    download: `${state.summary?.sku || "eden3d"}_${state.scene}.png` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  state.lastPhoto = { width: r.width, height: r.height, bytes: Math.round((r.url.length - 22) * 0.75) };
  setStatus("Foto descargada (1080×1350)", "ok");
}

function renderCarePanel(compat) {
  const sel = state.plants.map((id) => state.info.plantas.find((p) => p.id === id)).filter(Boolean);
  $("care").hidden = !sel.length;
  if (!sel.length) return;
  if (!state.careTab || !state.plants.includes(state.careTab)) state.careTab = sel[0].id;
  $("care-tabs").innerHTML = sel.length > 1 ? sel.map((f) => `<button type="button" role="tab" data-id="${f.id}"
    data-testid="tab-${f.id}" aria-selected="${f.id === state.careTab}">${esc(f.nombre)}</button>`).join("") : "";
  $("compat").innerHTML = renderCompat(compat || []);
  const f = sel.find((x) => x.id === state.careTab) || sel[0];
  const sw = ["screw_dish_sw", "screw_dish"].includes($("mode").value);
  $("care-body").innerHTML = renderCare(f, state.summary?.assembly, sw);
}

// ------------------------------------------------------------------ luces
function lightButtons() {
  $("light-presets").innerHTML = Object.entries(LIGHTS).map(([k, L]) => `
    <button type="button" role="radio" data-k="${k}" data-testid="luz-${k}" aria-pressed="${k === state.light}">${L.label}</button>`).join("");
}

// ------------------------------------------------------------------ descargas
function save(name, buffer, mime) {
  const url = URL.createObjectURL(new Blob([buffer], { type: mime }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

async function download(kind, part) {
  if (!state.ready || state.busy) return;
  if (!state.auth?.perms.download) {
    openLogin("Ingresá o creá tu cuenta gratis para descargar los archivos para imprimir.");
    return;
  }
  setBusy(true, kind === "3mf" ? "Armando el 3MF (calidad de impresión)…" : "Armando el STL…");
  try {
    const r = await call(kind, { opts: opts(), part });
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

function fill(sel, items, val, lab) {
  sel.innerHTML = items.map((it) => `<option value="${val(it)}">${lab(it)}</option>`).join("");
}

function buildSliders() {
  $("sliders").innerHTML = SLIDERS.map(([k, label, max, step]) => `
    <label class="slider"><span>${label}</span>
      <input type="range" id="s-${k}" data-testid="sl-${k}" min="0" max="${max}" step="${step}" value="0">
      <output id="o-${k}">—</output></label>`).join("");
  for (const [k] of SLIDERS) {
    const inp = $("s-" + k);
    inp.addEventListener("input", () => { $("o-" + k).textContent = +inp.value ? inp.value : "—"; });
    inp.addEventListener("change", () => build());
  }
}

// secciones plegables del panel (en el celular arrancan cerradas las menos usadas)
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
sections();

async function main() {
  buildSliders();
  lightButtons();
  sceneButtons();
  try {
    const boot = await call("init");
    const info = boot.info;
    state.info = info;
    viewer.setPlantMaterials(info.materiales, info.decor_mats || []);
    fill($("design"), info.designs, (d) => d.code, (d) => `${d.code} · ${d.name}`);
    fill($("size"), info.sizes, (s) => s, (s) => s);
    fill($("mode"), info.modes, (m) => m.code, (m) => m.label);
    fill($("drain"), info.drains, (d) => d.code, (d) => d.label);
    fill($("patitas"), [{ id: "", nombre: "Sin patitas" }, ...info.patitas.tipos], (t) => t.id, (t) => t.nombre);
    fill($("pies"), info.patitas.pies, (t) => t.id, (t) => t.nombre);
    $("patitas").disabled = $("pies").disabled = false;
    $("size").value = "S";
    $("engine-v").textContent = info.engine;
    $("build-id").textContent = "web " + boot.version;
    for (const id of ["design", "size", "mode", "drain"]) {
      $(id).disabled = false;
      $(id).addEventListener("change", () => build(id !== "drain"));
    }
    state.plants = ["echeveria"];
    plantChips();
    coberturas();
    state.ready = true;
    brandUi();
    state.bootSeconds = boot.seconds;
    setStatus(`Motor listo en ${boot.seconds.toFixed(1)} s`, "ok");
    await build(true);
  } catch (e) {
    state.errors.push(String(e));
    setStatus("No se pudo cargar el motor: " + e.message, "err");
  }
}

$("build").addEventListener("click", () => build(true));
$("dl3mf").addEventListener("click", () => download("3mf"));
$("dlstl").addEventListener("click", () => download("stl", "MACETA"));
$("dlstlp").addEventListener("click", () => download("stl", "PLATO"));
$("reset").addEventListener("click", () => {
  for (const [k] of SLIDERS) { $("s-" + k).value = 0; $("o-" + k).textContent = "—"; }
  build();
});
$("plant-list").addEventListener("click", (ev) => {
  const b = ev.target.closest(".chip");
  if (b && !b.disabled) togglePlant(b.dataset.id);
});
$("care-tabs").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-id]");
  if (!b) return;
  state.careTab = b.dataset.id;
  renderCarePanel(state.compat);
});
$("decor").addEventListener("change", () => updatePlants());
$("cobertura").addEventListener("change", () => {
  state.cobertura = $("cobertura").value || null;
  coberturaDesc();
  updatePlants();
});
$("scenes").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (!b) return;
  state.scene = b.dataset.k;
  viewer.setScene(state.scene);
  state.light = viewer.lightKey;
  sceneButtons();
  lightButtons();
});
$("wind").addEventListener("change", () => viewer.setWind($("wind").checked));
$("photo").addEventListener("click", () => takePhoto());

// ------------------------------------------------------------------ cuenta y marca de agua
const PIEZA = { MACETA: "maceta" };
function brandReport(s) {
  const b = s.brand;
  if (!b) return;
  const ok = Object.entries(b.pieces || {}).filter(([, h]) => h);
  const nombres = (list) => list.map(([n]) => PIEZA[n] || "plato").join(" y ");
  let txt;
  if (!b.text) txt = "Sin marca.";
  else if (!ok.length) txt = `"${b.text}" no entra en la base: probá un texto más corto.`;
  else if (ok.length < Object.keys(b.pieces).length) txt = `"${b.text}" va en el ${nombres(ok)}: en la maceta lo tapa el drenaje.`;
  else txt = `"${b.text}" grabada en ${nombres(ok)}.`;
  $("brand-msg").textContent = txt;
  state.brandReport = { text: b.text, pieces: b.pieces };
}

function brandUi() {
  const can = !!state.auth?.perms.brand;
  $("brand").disabled = !can || !state.ready;
  $("brand-apply").disabled = !can || !state.ready;
  $("brand-lock").hidden = can;
  $("brand-lock").title = "Cambiar la marca es parte del paquete Pro";
  if (!can) {
    $("brand").value = "Eden3D";
    if (!state.auth?.user && state.auth?.configured) $("brand-msg").textContent = "Con el paquete Pro grabás tu propio texto.";
  }
}

async function applyBrand() {
  if (!state.auth?.perms.brand) return;
  const r = await call("brand", { text: $("brand").value });
  if (r.error) {
    $("brand-msg").textContent = r.error;
    $("brand-msg").classList.add("err");
    return;
  }
  $("brand-msg").classList.remove("err");
  $("brand").value = r.text;
  state.brand = r.text;
  build();
}
$("brand-apply").addEventListener("click", () => applyBrand());
$("brand").addEventListener("keydown", (e) => { if (e.key === "Enter") applyBrand(); });

mountAccount($("account"));
onAuth((a) => {
  const before = state.auth;
  state.auth = a;
  brandUi();
  // si perdió el permiso (salió de la cuenta) se vuelve a la marca de Eden3D
  if (state.brand !== null && !a.perms.brand) { state.brand = null; build(); }
  else if (before && before.role !== a.role && state.ready) build();
});

// guía de uso en PDF
async function guidePdf() {
  if (!state.ready || state.busy || !state.summary?.valid) return;
  setBusy(true, "Armando la guía en PDF…");
  try {
    const fichas = state.plants.map((id) => state.info.plantas.find((p) => p.id === id)).filter(Boolean);
    const cobId = state.cobertura || state.coberturaUsada;
    const doc = await makeGuide({
      summary: state.summary, plantas: fichas, compat: state.compat || [],
      cobertura: $("decor").checked ? state.info.coberturas.find((c) => c.id === cobId) : null,
      selfWatering: ["screw_dish_sw", "screw_dish"].includes($("mode").value) && !!state.summary.assembly?.water_reservoir_ml,
      photo: viewer.photo(780, 975, "image/jpeg").url,
      layers: viewer.pieceLayers(),
      fecha: new Date().toLocaleDateString("es-AR"),
    });
    const buf = doc.output("arraybuffer");
    const name = `${state.summary.sku}_guia.pdf`;
    save(name, buf, "application/pdf");
    state.lastPdf = { name, bytes: buf.byteLength, pages: doc.getNumberOfPages() };
    setStatus("Guía descargada", "ok");
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error en el PDF: " + e.message, "err");
  } finally {
    setBusy(false);
  }
}
$("pdf").addEventListener("click", () => guidePdf());

// ------------------------------------------------------------------ agua, piezas y slicer
$("drop").addEventListener("click", () => viewer.randomDrop());
$("waves").addEventListener("click", () => viewer.makeWaves());
$("rain").addEventListener("change", () => viewer.setRain($("rain").checked));
$("explode").addEventListener("input", () => {
  if (viewer.loop) loopButton(false);
  $("o-explode").textContent = $("explode").value + " %";
  viewer.setExplode(+$("explode").value / 100);
});

// despiece en loop, con etiquetas de cada pieza
function loopButton(on) {
  viewer.setExplodeLoop(on);
  $("explode-loop").setAttribute("aria-pressed", String(on));
  $("explode-loop").textContent = on ? "❚❚ Pausa" : "▶ Animar";
}
$("explode-loop").addEventListener("click", () => loopButton(!viewer.loop));
viewer.onExplode = (k) => {
  $("explode").value = Math.round(k * 100);
  $("o-explode").textContent = Math.round(k * 100) + " %";
};
const labelsEl = document.createElement("div");
labelsEl.className = "labels";
labelsEl.id = "labels";
labelsEl.setAttribute("aria-hidden", "true");
$("viewer").appendChild(labelsEl);
viewer.onFrame = () => {
  const names = { tierra: "Tierra" };
  for (const p of state.info?.plantas || []) names[p.id] = p.nombre;
  const cob = (state.info?.coberturas || []).find((c) => c.id === (state.cobertura || state.coberturaUsada));
  if (cob) names.tierra = "Tierra con " + cob.nombre.toLowerCase();
  const list = viewer.partLabels(names);
  const seen = new Set();
  for (const L of list) {
    let el = labelsEl.querySelector(`[data-k="${L.key}"]`);
    if (!el) { el = document.createElement("span"); el.dataset.k = L.key; labelsEl.appendChild(el); }
    el.textContent = L.text;
    el.classList.toggle("left", !!L.left);
    el.style.left = (L.x * 100).toFixed(2) + "%";
    el.style.top = (L.y * 100).toFixed(2) + "%";
    el.style.opacity = String(Math.min(1, (viewer.explode - 0.05) * 3));
    seen.add(L.key);
  }
  for (const el of labelsEl.children) if (!seen.has(el.dataset.k)) el.style.opacity = "0";
};

function slicerUi(info) {
  info = info || viewer.slicerInfo();
  $("slicer-ui").hidden = !info.on;
  if (!info.on) return;
  $("layer").max = info.layers;
  $("layer").value = info.layer;
  $("o-layer").textContent = `${info.layer} / ${info.layers}`;
  $("slicer-info").textContent = `${info.z.toFixed(1)} de ${info.height.toFixed(1)} mm`;
  $("play-layers").textContent = info.playing ? "❚❚ Pausa" : "▶ Imprimir";
  for (const b of $("slicer-part").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.p === info.part));
  $("slicer-part").querySelector("[data-p=PLATO]").disabled = !viewer.meshNames().includes("PLATO");
}
viewer.onSlicer = slicerUi;
$("slicer").addEventListener("change", () => slicerUi(viewer.setSlicer($("slicer").checked)));
$("slicer-part").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-p]");
  if (!b || b.disabled) return;
  viewer.slicer.layer = 0;
  slicerUi(viewer.setSlicer(true, b.dataset.p));
});
$("layer").addEventListener("input", () => { viewer.playSlicer(false); slicerUi(viewer.setLayer(+$("layer").value)); });
$("play-layers").addEventListener("click", () => {
  viewer.playSlicer(!viewer.slicer.playing);
  slicerUi();
});
$("light-presets").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (!b) return;
  state.light = b.dataset.k;
  viewer.setLight(state.light);
  lightButtons();
});
$("sun-az").addEventListener("input", () => {
  $("o-sun").textContent = $("sun-az").value + "°";
  viewer.setLight(state.light, +$("sun-az").value);
});
$("water").addEventListener("change", () => viewer.setWater($("water").checked));
$("water-level").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-v]");
  if (!b) return;
  for (const x of $("water-level").querySelectorAll("button")) x.setAttribute("aria-pressed", String(x === b));
  $("water").checked = true;
  viewer.setWater(true, b.dataset.v);
});
$("cut").addEventListener("change", () => viewer.setCut($("cut").checked));
$("color").addEventListener("change", () => viewer.setColor($("color").value));
$("mode").addEventListener("change", () => renderCarePanel(state.compat));
$("hq").addEventListener("change", () => build());
window.addEventListener("error", (e) => state.errors.push(String(e.message)));
main();

// ------------------------------------------------------------------ patitas articuladas
function patitasMsg(p) {
  $("patitas-ui").hidden = !$("patitas").value;
  if (!p) { $("patitas-msg").textContent = ""; return; }
  const c = p.cadenas[0];
  $("patitas-msg").textContent = `Van clavadas a la base de la maceta (sin plato) y salen impresas ya armadas: `
    + `eslabones de ${String(c.grosor_mm).replace(".", ",")} mm con ${String(p.holgura).replace(".", ",")} mm de juego. `
    + "Al sacarlas de la cama, doblalas despacio para soltar las bisagras.";
}
// las patitas van siempre sin plato, clavadas a la base de la maceta
function patitasModo() {
  const con = !!$("patitas").value;
  if (con) {
    if ($("mode").value !== "pot") $("mode").dataset.antes = $("mode").value;
    $("mode").value = "pot";
  } else if ($("mode").dataset.antes) {
    $("mode").value = $("mode").dataset.antes;
    delete $("mode").dataset.antes;
  }
  $("mode").disabled = con || !state.ready;
  $("mode").title = con ? "Con patitas la maceta va sin plato" : "";
}
$("patitas").addEventListener("change", () => { patitasModo(); patitasMsg(null); build(); });
$("pies").addEventListener("change", () => { patitasMsg(null); build(); });
$("eslabones").addEventListener("input", () => { $("o-eslabones").textContent = $("eslabones").value; });
$("holgura-patas").addEventListener("input", () => {
  $("o-holgura-patas").textContent = (+$("holgura-patas").value).toFixed(2).replace(".", ",") + " mm";
});
for (const id of ["eslabones", "holgura-patas"]) $(id).addEventListener("change", () => build());
$("sentar").addEventListener("click", () => {
  const on = $("sentar").getAttribute("aria-pressed") !== "true";
  patitas.setPose(on);
  $("sentar").setAttribute("aria-pressed", String(on));
  $("sentar").textContent = on ? "■ Bajarla" : "▶ Sentarla";     // cortos: entran en el celular
  setTimeout(() => viewer.fit(), 1300);                 // encuadra la maceta con el estante
});
