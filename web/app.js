// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
import { Viewer, LIGHTS } from "./viewer.js";
import { renderCare, renderCompat } from "./care.js";

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
  plants: [], plantBuilds: 0, careTab: null, light: "estudio",
};
window.__eden = state;

// ------------------------------------------------------------------ worker
const worker = new Worker("worker.js");
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
Object.defineProperty(state, "viewer", { get: () => ({
  meshes: viewer.meshNames(), triangles: viewer.triangles, plantTriangles: viewer.plantTriangles || 0,
  waterTime: viewer.stats.waterTime, waterLevel: viewer.stats.waterLevel, frames: viewer.stats.frames,
  light: viewer.lightKey, sunAz: viewer.sunAz, cut: viewer.cut,
  sunIntensity: viewer.sun.intensity, lamp: viewer.lamp.intensity,
}) });

// ------------------------------------------------------------------ UI
function opts() {
  const overrides = {};
  for (const [k] of SLIDERS) {
    const v = parseFloat($("s-" + k).value);
    if (v > 0) overrides[k] = v;
  }
  return {
    design: $("design").value, size: $("size").value, mode: $("mode").value,
    drain: $("drain").value, quality: $("hq").checked ? "normal" : "preview", overrides,
  };
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
  for (const id of ["build", "dl3mf", "dlstl", "dlstlp"]) $(id).disabled = on || !state.ready;
  if (!on && !state.summary?.valid) for (const id of ["dl3mf", "dlstl", "dlstlp"]) $(id).disabled = true;
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
    ["Drenaje", fmt(s.drain_holes, " agujeros"), "f-drenaje"],
  ];
  if (plate) facts.push(["Plato", fmt(plate[1], " g PLA"), "f-plato"]);
  if (A.thread_turns !== undefined) {
    facts.push(["Rosca", `${A.thread_turns} vueltas · ${A.thread_engagement_mm} mm`, "f-rosca"]);
    facts.push(["Luz bajo la maceta", fmt(A.water_gap_under_pot_mm, " mm"), "f-luz"]);
    facts.push(["Agua para mojar la tierra", fmt(A.water_min_wet_ml, " ml"), "f-agua-min"]);
    facts.push(["Plato lleno", `${fmt(A.water_reservoir_ml, " ml")} · ${fmt(A.water_over_soil_mm, " mm")} de tierra en remojo`, "f-agua-max"]);
  }
  facts.push(["Cálculo", fmt(s.seconds, " s"), "f-tiempo"]);
  $("facts").innerHTML = facts.map(([k, v, t]) => `<div><dt>${k}</dt><dd data-testid="${t}">${v}</dd></div>`).join("");
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${esc(e)}</li>`),
    ...(s.warnings || []).map((w) => `<li>${esc(w)}</li>`)].join("");
  $("water-level").hidden = A.dish_inner_r0_mm === undefined;
}

let lastKey = "";
async function build(refit = false) {
  if (!state.ready || state.busy) return;
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
    }
    state.triangles = viewer.triangles;
    state.meshes = viewer.meshNames();
    state.builds++;
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : "El diseño no es válido con esta combinación", r.summary.valid ? "ok" : "err");
    lastKey = key;
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
  }
  if (state.summary?.valid) await updatePlants();
}

// ------------------------------------------------------------------ plantas
let plantReq = 0;
async function updatePlants() {
  const ids = state.plants.slice();
  const my = ++plantReq;
  renderCarePanel([]);
  if (!ids.length) { viewer.showPlants([]); state.plantBuilds++; state.compat = []; return; }
  try {
    const r = await call("plants", { opts: opts(), ids, decor: $("decor").checked });
    if (my !== plantReq) return;                       // llegó una selección más nueva
    viewer.showPlants(r.parts);
    state.compat = r.compat;
    renderCarePanel(r.compat);
    state.plantBuilds++;
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error en plantas: " + e.message, "err");
  }
}

function plantChips() {
  const max = state.info.max_plantas;
  $("plant-list").innerHTML = state.info.plantas.map((p) => `
    <button type="button" class="chip" data-id="${p.id}" data-testid="planta-${p.id}" aria-pressed="${state.plants.includes(p.id)}"
      title="${esc(p.tipo)} · ${esc(p.dificultad)}">${esc(p.nombre)}<small>${esc(p.tipo.split(" ")[0])}</small></button>`).join("");
  for (const b of $("plant-list").querySelectorAll(".chip")) {
    b.disabled = !state.plants.includes(b.dataset.id) && state.plants.length >= max;
  }
}

function togglePlant(id) {
  const i = state.plants.indexOf(id);
  if (i >= 0) state.plants.splice(i, 1);
  else if (state.plants.length < state.info.max_plantas) state.plants.push(id);
  if (!state.plants.includes(state.careTab)) state.careTab = state.plants[state.plants.length - 1] || null;
  plantChips();
  if (state.ready && !state.busy) updatePlants();
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

async function main() {
  buildSliders();
  lightButtons();
  try {
    const boot = await call("init");
    const info = boot.info;
    state.info = info;
    viewer.setPlantMaterials(info.materiales);
    fill($("design"), info.designs, (d) => d.code, (d) => `${d.code} · ${d.name}`);
    fill($("size"), info.sizes, (s) => s, (s) => s);
    fill($("mode"), info.modes, (m) => m.code, (m) => m.label);
    fill($("drain"), info.drains, (d) => d.code, (d) => d.label);
    $("size").value = "S";
    $("engine-v").textContent = info.engine;
    $("build-id").textContent = "web " + boot.version;
    for (const id of ["design", "size", "mode", "drain"]) {
      $(id).disabled = false;
      $(id).addEventListener("change", () => build(id !== "drain"));
    }
    state.plants = ["echeveria"];
    plantChips();
    state.ready = true;
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
