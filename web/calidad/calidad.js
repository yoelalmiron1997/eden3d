// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Tablero de calidad: lee data.json (generado en CI por tools/spec_matrix.py).
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const STATUS = {
  ok: ["✓", "OK"], falla: ["✕", "Falla"], "sin-tests": ["!", "Sin tests"], pendiente: ["◷", "Pendiente"],
  obsoleta: ["–", "Obsoleta"], passed: ["✓", "Pasó"], failed: ["✕", "Falló"], error: ["✕", "Error"], skipped: ["↷", "Salteado"],
};
const badge = (s) => `<span class="badge ${s}">${STATUS[s]?.[0] ?? ""} ${STATUS[s]?.[1] ?? s}</span>`;
const short = (nodeid) => nodeid.replace(/^tests\//, "").replace(/\[chromium\]$/, "");

let DATA = null;

function kpis(d) {
  const t = d.totales;
  const items = [
    [`${t.cobertura_specs_pct}%`, "Specs activas cubiertas", "k-cobertura"],
    [`${t.cubiertas}/${t.activas}`, "Specs en verde", "k-specs"],
    [`${t.passed}/${t.tests}`, "Tests pasados", "k-tests"],
    [t.failed, "Tests fallados", "k-fallas"],
    [t.pendientes, "Specs pendientes", "k-pendientes"],
    [`${Math.round(t.segundos)} s`, "Duración de la suite", "k-duracion"],
  ];
  $("kpis").innerHTML = items.map(([v, l, id]) => `<div class="kpi"><div class="v" data-testid="${id}">${esc(v)}</div><div class="l">${l}</div></div>`).join("");
}

function header(d) {
  const r = d.run;
  const link = r.run_url ? ` · <a href="${esc(r.run_url)}">ver ejecución</a>` : "";
  $("run").innerHTML = `Versión <code>${esc(r.commit || "local")}</code> (${esc(r.rama || "")}) · ${esc(r.fecha)}${r.mensaje ? " · " + esc(r.mensaje) : ""}${link}`;
  const g = $("gate");
  g.className = "gate " + (r.gate ? "ok" : "bad");
  g.textContent = r.gate ? "✓ Gate de calidad OK" : "✕ Gate de calidad en falla";
  const s = d.suites.map((x) => x.missing ? `${x.suite}: sin datos` : `${x.suite}: ${x.seconds} s`).join(" · ");
  $("suites").textContent = s;
  if (d.problemas.length) {
    $("problemas").hidden = false;
    $("probs").innerHTML = d.problemas.map((p) => `<li><b>${esc(p.tipo)}</b>: ${esc(p.detalle)}</li>`).join("");
  }
}

function matrix() {
  const area = $("f-area").value, est = $("f-estado").value, q = $("f-q").value.trim().toLowerCase();
  const byId = Object.fromEntries(DATA.tests.map((t) => [t.nodeid, t]));
  const rows = DATA.specs.filter((s) => (!area || s.area === area) && (!est || s.status === est) &&
    (!q || (s.id + " " + s.titulo + " " + s.tests.join(" ")).toLowerCase().includes(q)));
  $("rows").innerHTML = rows.map((s) => {
    const tests = s.tests.map((n) => byId[n]).filter(Boolean);
    const det = `<tr class="det" hidden data-for="${s.id}"><td colspan="6">
      <p><b>Criterio de aceptación:</b> ${esc(s.criterio)}</p>
      <p class="muted">${esc(s.descripcion)} · <code>${esc(s.archivo)}</code></p>
      ${tests.length ? `<ul>${tests.map((t) => `<li>${badge(t.outcome)} <code>${esc(short(t.nodeid))}</code> · ${t.duration.toFixed(2)} s${t.message ? `<pre class="msg">${esc(t.message)}</pre>` : ""}</li>`).join("")}</ul>` : "<p><i>Sin tests todavía.</i></p>"}
    </td></tr>`;
    return `<tr class="spec" data-id="${s.id}" data-testid="spec-${s.id}" tabindex="0" aria-expanded="false">
      <td class="id">${s.id}</td><td>${esc(s.titulo)}</td><td>${esc(s.nivel)}</td><td>${esc(s.prioridad)}</td>
      <td>${badge(s.status)}</td><td class="num">${s.passed}/${s.tests.length}</td></tr>${det}`;
  }).join("") || `<tr><td colspan="6" class="muted">Ninguna spec con esos filtros.</td></tr>`;
}

function testsTable() {
  const o = $("t-out").value;
  const rows = DATA.tests.filter((t) => !o || t.outcome === o || (o === "failed" && t.outcome === "error"));
  $("trows").innerHTML = rows.map((t) => `<tr><td><code>${esc(short(t.nodeid))}</code>${t.doc ? `<div class="muted">${esc(t.doc)}</div>` : ""}</td>
    <td>${esc(t.suite)}</td><td>${t.specs.map((x) => `<a class="id" href="#matriz" data-goto="${x}">${x}</a>`).join(" ") || "—"}</td>
    <td>${badge(t.outcome)}</td><td class="num">${t.duration.toFixed(2)} s</td></tr>`).join("");
}

// ---------- historial: una sola serie (cobertura %), con tooltip por punto
function history(h) {
  const host = $("hist");
  if (!h.length) { host.innerHTML = '<p class="muted">Todavía no hay historial.</p>'; return; }
  const W = host.clientWidth || 800, H = 190, L = 40, R = 12, T = 10, B = 26;
  const x = (i) => h.length === 1 ? (L + W - R) / 2 : L + (i * (W - L - R)) / (h.length - 1);
  const y = (v) => T + (1 - v / 100) * (H - T - B);
  const grid = [0, 50, 100].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/>`).join("");
  const ylab = [0, 50, 100].map((v) => `<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}%</text>`).join("");
  const step = Math.max(1, Math.ceil(h.length / 6));
  const xlab = h.map((r, i) => (i % step === 0 || i === h.length - 1)
    ? `<text x="${x(i)}" y="${H - 6}" text-anchor="middle">${esc((r.fecha || "").slice(5, 10))}</text>` : "").join("");
  const path = h.map((r, i) => `${i ? "L" : "M"}${x(i)},${y(r.cobertura_specs_pct)}`).join("");
  const dots = h.map((r, i) => `<circle class="dot ${r.gate ? "" : "bad"}" r="4.5" cx="${x(i)}" cy="${y(r.cobertura_specs_pct)}"/>`).join("");
  const hw = h.length > 1 ? (W - L - R) / (h.length - 1) : W;
  const hits = h.map((r, i) => `<rect class="hit" data-i="${i}" x="${x(i) - hw / 2}" y="${T}" width="${hw}" height="${H - T - B}"/>`).join("");
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Cobertura de specs por versión">
    <g class="grid">${grid}</g><g class="axis">${ylab}${xlab}</g>
    <line class="cross" id="cross" y1="${T}" y2="${H - B}" x1="-10" x2="-10"/>
    <path class="line" d="${path}"/>${dots}${hits}</svg>`;
  const tip = $("tip");
  host.querySelectorAll(".hit").forEach((el) => {
    el.addEventListener("mousemove", (ev) => {
      const r = h[+el.dataset.i];
      const cx = x(+el.dataset.i);
      host.querySelector("#cross").setAttribute("x1", cx);
      host.querySelector("#cross").setAttribute("x2", cx);
      tip.innerHTML = `<b>${esc(r.fecha)} · ${esc(r.commit || "")}</b>Cobertura: ${r.cobertura_specs_pct}%<br>Tests: ${r.passed}/${r.tests} pasados${r.failed ? ` · ${r.failed} fallados` : ""}<br>Gate: ${r.gate ? "✓ OK" : "✕ falla"}${r.mensaje ? `<br><span class="muted">${esc(r.mensaje)}</span>` : ""}`;
      tip.hidden = false;
      tip.style.left = Math.min(ev.clientX + 14, innerWidth - 280) + "px";
      tip.style.top = ev.clientY + 14 + "px";
    });
    el.addEventListener("mouseleave", () => { tip.hidden = true; host.querySelector("#cross").setAttribute("x1", -10); host.querySelector("#cross").setAttribute("x2", -10); });
  });
}

async function main() {
  try {
    DATA = await (await fetch("data.json", { cache: "no-cache" })).json();
  } catch (e) {
    $("run").textContent = "Todavía no hay resultados publicados (data.json).";
    return;
  }
  window.__calidad = DATA;
  header(DATA);
  kpis(DATA);
  for (const a of DATA.areas) $("f-area").insertAdjacentHTML("beforeend", `<option>${esc(a.area)}</option>`);
  matrix();
  testsTable();
  history(DATA.historial || []);
  for (const id of ["f-area", "f-estado", "f-q"]) $(id).addEventListener("input", matrix);
  $("t-out").addEventListener("change", testsTable);
  $("rows").addEventListener("click", (ev) => {
    const tr = ev.target.closest("tr.spec");
    if (!tr) return;
    const det = $("rows").querySelector(`tr.det[data-for="${tr.dataset.id}"]`);
    det.hidden = !det.hidden;
    tr.setAttribute("aria-expanded", String(!det.hidden));
  });
  $("rows").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.click(); });
  $("trows").addEventListener("click", (ev) => {
    const a = ev.target.closest("[data-goto]");
    if (!a) return;
    $("f-q").value = a.dataset.goto; $("f-area").value = ""; $("f-estado").value = "";
    matrix();
    const tr = $("rows").querySelector("tr.spec");
    if (tr) tr.click();
  });
  addEventListener("resize", () => history(DATA.historial || []));
  if (location.hash === "#matriz") $("matriz").scrollIntoView();
}
main();
