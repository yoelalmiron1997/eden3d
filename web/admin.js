// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Panel de administración: roles de los usuarios y cobertura de la marca de agua en
// cada maceta. Que alguien sea admin lo decide la base (RLS), no esta página.
import { mountAccount, openLogin } from "./auth-ui.js";
import { onAuth, listUsers, setRole, ROLES } from "./auth.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const state = { auth: null, users: [], cov: { rows: [], running: false, stop: false }, info: null };
window.__edenAdmin = state;
let worker = null, seq = 0;                 // (arriba: onAuth puede llamar ya a startEngine)
const pending = new Map();

mountAccount($("account"));
onAuth(async (a) => {
  state.auth = a;
  const ok = a.perms.admin;
  $("panel").hidden = !ok;
  $("denied").hidden = ok;
  if (!ok) {
    $("denied-msg").textContent = !a.configured
      ? "Las cuentas todavía no están configuradas (ver docs/SUPABASE.md)."
      : a.user ? "Tu cuenta no es de administrador." : "Ingresá con una cuenta de administrador.";
    if (a.configured && !a.user) openLogin("Panel de administración");
    return;
  }
  loadUsers();
  startEngine();
});

// ------------------------------------------------------------------ pestañas
document.querySelector(".tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]");
  if (!b) return;
  for (const t of document.querySelectorAll("[data-tab]")) t.setAttribute("aria-selected", String(t === b));
  for (const p of document.querySelectorAll("[data-pane]")) p.hidden = p.dataset.pane !== b.dataset.tab;
});

// ------------------------------------------------------------------ usuarios
async function loadUsers() {
  try {
    state.users = await listUsers();
    renderUsers();
  } catch (e) {
    $("users-msg").textContent = "No se pudo leer la lista: " + e.message;
  }
}

function renderUsers() {
  const opts = (r) => ["usuario", "pro", "admin"].map((k) =>
    `<option value="${k}" ${k === r ? "selected" : ""}>${ROLES[k].label}</option>`).join("");
  $("users").innerHTML = state.users.map((u) => `
    <tr><td>${esc(u.email)}</td>
      <td><select data-id="${esc(u.id)}" data-testid="rol-${esc(u.email)}" ${u.id === state.auth.user.id ? "disabled title='No podés cambiar tu propio rol'" : ""}>${opts(u.rol)}</select></td>
      <td>${u.creado ? new Date(u.creado).toLocaleDateString("es-AR") : ""}</td></tr>`).join("")
    || `<tr><td colspan="3" class="muted">Todavía no hay usuarios.</td></tr>`;
  $("users-msg").textContent = `${state.users.length} usuario(s) · ${state.users.filter((u) => u.rol === "pro").length} con paquete Pro`;
}

$("users").addEventListener("change", async (e) => {
  const sel = e.target.closest("select[data-id]");
  if (!sel) return;
  try {
    await setRole(sel.dataset.id, sel.value);
    const u = state.users.find((x) => x.id === sel.dataset.id);
    if (u) u.rol = sel.value;
    $("users-msg").textContent = `Listo: ${u ? u.email : ""} ahora es ${ROLES[sel.value].label}.`;
  } catch (err) {
    $("users-msg").textContent = "No se pudo cambiar: " + err.message;
    renderUsers();
  }
});

// ------------------------------------------------------------------ cobertura
function call(type, payload = {}) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, ...payload });
  });
}

async function startEngine() {
  if (worker) return;
  worker = new Worker("worker.js");
  worker.onmessage = (ev) => {
    const { id, ok, result, error } = ev.data;
    const p = pending.get(id);
    if (!p) return;
    pending.delete(id);
    ok ? p.resolve(result) : p.reject(new Error(error));
  };
  const boot = await call("init");
  state.info = boot.info;
  $("cov-sizes").innerHTML = boot.info.sizes.map((s) =>
    `<label class="check"><input type="checkbox" value="${s}" ${s === "S" ? "checked" : ""} data-testid="cov-t-${s}"> ${s}</label>`).join("");
  $("cov-designs").innerHTML += boot.info.designs.map((d) => `<option value="${d.code}">${esc(d.code)} · ${esc(d.name)}</option>`).join("");
  $("cov-run").disabled = false;
  $("cov-status").textContent = `Motor listo · ${boot.info.designs.length} diseños`;
  state.engineReady = true;
}

const mm = (v) => (v ? `${v} mm` : "no entra");

async function runCoverage() {
  const text = $("cov-text").value;
  const chk = await call("brand", { text });
  if (chk.error) { $("cov-status").textContent = chk.error; return; }
  const sizes = [...document.querySelectorAll("#cov-sizes input:checked")].map((i) => i.value);
  const designs = $("cov-designs").value ? [$("cov-designs").value] : state.info.designs.map((d) => d.code);
  const jobs = designs.flatMap((d) => sizes.map((s) => [d, s]));
  if (!jobs.length) { $("cov-status").textContent = "Elegí al menos un tamaño."; return; }
  const C = state.cov;
  C.rows = [];
  C.running = true;
  C.stop = false;
  C.text = chk.text;
  $("cov-rows").innerHTML = "";
  $("cov-run").disabled = true;
  $("cov-stop").disabled = false;
  $("cov-csv").disabled = true;
  $("cov-bar").max = jobs.length;
  for (const [i, [design, size]] of jobs.entries()) {
    if (C.stop) break;
    $("cov-bar").value = i;
    $("cov-status").textContent = `Probando ${design} ${size} (${i + 1} de ${jobs.length})…`;
    const t0 = performance.now();
    const row = { design, size };
    try {
      const r = await call("build", { opts: { design, size, mode: "screw_dish_sw", drain: "leaf", quality: "preview",
        brand: chk.text, check: true } });
      const s = r.summary;
      const pieces = s.brand ? s.brand.pieces : {};
      const plato = Object.keys(pieces).find((k) => k !== "MACETA");
      const mc = s.mesh_check || {};
      row.valid = s.valid;
      row.closed = Object.values(mc).length > 0 && Object.values(mc).every((m) => m.closed);
      row.maceta = pieces.MACETA || null;
      row.plato = plato ? pieces[plato] : null;
      row.warnings = s.warnings.length;
      row.detail = [...s.errors, ...s.warnings].join(" · ");
      row.ok = s.valid && row.closed && !!(row.maceta || row.plato);
    } catch (e) {
      row.valid = false; row.ok = false; row.detail = e.message;
    }
    row.seconds = +((performance.now() - t0) / 1000).toFixed(1);
    C.rows.push(row);
    $("cov-rows").insertAdjacentHTML("beforeend", `
      <tr class="${row.ok ? "ok" : "bad"}" title="${esc(row.detail)}"><td>${esc(design)}</td><td>${size}</td>
        <td>${row.ok ? "✔ OK" : "✖ Revisar"}</td><td>${row.closed ? "cerrada" : "con fallas"}</td>
        <td>${mm(row.maceta)}</td><td>${mm(row.plato)}</td><td>${row.warnings ?? "-"}</td><td>${row.seconds}</td></tr>`);
  }
  const ok = C.rows.filter((r) => r.ok).length;
  $("cov-bar").value = C.rows.length;
  $("cov-status").textContent = `${ok} de ${C.rows.length} macetas OK con "${C.text}"${C.stop ? " (parado)" : ""}`;
  C.running = false;
  $("cov-run").disabled = false;
  $("cov-stop").disabled = true;
  $("cov-csv").disabled = !C.rows.length;
}

$("cov-run").addEventListener("click", () => runCoverage());
$("cov-stop").addEventListener("click", () => { state.cov.stop = true; });
$("cov-csv").addEventListener("click", () => {
  const head = "diseno,tamano,ok,valida,malla_cerrada,marca_maceta_mm,marca_plato_mm,avisos,segundos,detalle";
  const q = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const lines = state.cov.rows.map((r) => [r.design, r.size, r.ok, r.valid, r.closed, r.maceta ?? "", r.plato ?? "",
    r.warnings ?? "", r.seconds, q(r.detail)].join(","));
  const blob = new Blob([[head, ...lines].join("\n")], { type: "text/csv" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob),
    download: `cobertura_marca_${state.cov.text.replace(/[^\p{L}\p{N}_-]+/gu, "_")}.csv` });
  document.body.appendChild(a);
  a.click();
  a.remove();
});
