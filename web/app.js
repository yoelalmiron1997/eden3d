// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const $ = (id) => document.getElementById(id);
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
const state = { ready: false, busy: false, info: null, summary: null, parts: [], builds: 0, errors: [] };
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
function call(type, payload = {}, transfer = []) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, ...payload }, transfer);
  });
}

// ------------------------------------------------------------------ visor 3D
const host = $("viewer");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
camera.position.set(-180, 160, 320);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.HemisphereLight(0xfff6e8, 0x8a7a66, 1.15));
const sun = new THREE.DirectionalLight(0xfff1dc, 2.2);
sun.position.set(220, 300, 120);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0004;
Object.assign(sun.shadow.camera, { left: -200, right: 200, top: 200, bottom: -200, near: 10, far: 900 });
scene.add(sun);
const fillLight = new THREE.DirectionalLight(0xdfe8ff, 0.5);
fillLight.position.set(-250, 120, -100);
scene.add(fillLight);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.ShadowMaterial({ opacity: 0.18 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);   // corta la mitad delantera
const model = new THREE.Group();
model.rotation.x = -Math.PI / 2;            // el motor usa Z hacia arriba
scene.add(model);

const mats = {
  MACETA: new THREE.MeshStandardMaterial({ color: 0xece9e2, roughness: 0.78, metalness: 0, side: THREE.DoubleSide }),
  PLATO: new THREE.MeshStandardMaterial({ color: 0xdedad2, roughness: 0.8, metalness: 0, side: THREE.DoubleSide }),
  AGUA: new THREE.MeshPhysicalMaterial({ color: 0x4aa3df, roughness: 0.1, transmission: 0, transparent: true, opacity: 0.5, depthWrite: false }),
};

function resize() {
  const r = host.getBoundingClientRect();
  const w = Math.max(10, r.width), h = Math.max(10, r.height);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host);
resize();
(function loop() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();

function applyView() {
  const cut = $("cut").checked;
  for (const m of Object.values(mats)) {
    m.clippingPlanes = cut ? [clip] : [];
    m.needsUpdate = true;
  }
  model.children.forEach((o) => { if (o.name === "AGUA") o.visible = $("water").checked; });
  mats.MACETA.color.set($("color").value);
  mats.PLATO.color.set($("color").value).multiplyScalar(0.94);
  state.cut = cut;
}

function showParts(parts, refit) {
  model.clear();
  let tris = 0;
  for (const p of parts) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(p.positions), 3));
    g.setIndex(new THREE.BufferAttribute(new Uint32Array(p.indices), 1));
    g.computeVertexNormals();
    const name = p.name === "MACETA" || p.name === "AGUA" ? p.name : "PLATO";
    const mesh = new THREE.Mesh(g, mats[name]);
    mesh.name = name;
    mesh.castShadow = name !== "AGUA";
    mesh.receiveShadow = name !== "AGUA";
    if (name === "AGUA") mesh.renderOrder = 2;
    model.add(mesh);
    tris += g.index.count / 3;
  }
  state.triangles = tris;
  state.meshes = model.children.map((m) => m.name);
  applyView();
  if (refit) fit();
}

function fit() {
  const box = new THREE.Box3().setFromObject(model);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const c = box.getCenter(new THREE.Vector3());
  const r = Math.max(size.x, size.y, size.z) * 0.5;
  const d = r / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.5;
  const dir = new THREE.Vector3(-0.45, 0.5, 1).normalize();
  camera.position.copy(c).addScaledVector(dir, d);
  controls.target.copy(c);
  controls.update();
}

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
  $("warnings").innerHTML = [...(s.errors || []).map((e) => `<li class="err">${e}</li>`),
    ...(s.warnings || []).map((w) => `<li>${w}</li>`)].join("");
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
    state.builds++;
    showReport(r.summary);
    if (r.summary.valid) showParts(r.parts, refit || key.split('"overrides"')[0] !== lastKey.split('"overrides"')[0]);
    setStatus(r.summary.valid ? `Listo · ${r.summary.seconds} s` : "El diseño no es válido con esta combinación", r.summary.valid ? "ok" : "err");
    lastKey = key;
  } catch (e) {
    state.errors.push(String(e));
    setStatus("Error: " + e.message, "err");
  } finally {
    setBusy(false);
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
  try {
    const boot = await call("init");
    const info = boot.info;
    state.info = info;
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
for (const id of ["water", "cut", "color"]) $(id).addEventListener("change", applyView);
$("hq").addEventListener("change", () => build());
window.addEventListener("error", (e) => state.errors.push(String(e.message)));
main();
