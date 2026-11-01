// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Feedback de la comunidad: un botón en todas las páginas para dejar una idea, avisar que
// algo no anda o comentar, y ver lo que dejaron los demás (sumarse con "Me sumo" y responder).
// Vive en Supabase (tablas feedback, feedback_respuestas y feedback_votos de
// supabase/esquema.sql); las reglas de quién ve, escribe y borra están en la base (RLS).
import { onAuth, conexion, perfil, nombrePublico } from "./auth.js";
import { caraHTML } from "./avatares.js";

export const TIPOS = { idea: "Idea", error: "Algo no anda", comentario: "Comentario" };
export const HERRAMIENTAS = { general: "General", macetas: "Macetas", mate: "Mate", sopa: "Sopa de letras", topper: "Topper", chapita: "Chapitas", trofeo: "Trofeos" };
const LARGO = 1000, LARGO_RESP = 600;

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const iniciales = (n) => String(n || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";

function herramientaDeLaPagina() {
  const f = (location.pathname.split("/").pop() || "").replace(/\.html$/, "");
  return HERRAMIENTAS[f] ? f : "general";
}

// ---------------------------------------------------------------- datos
function noActivado(error) {
  return error && (["42P01", "PGRST205", "PGRST202", "PGRST200"].includes(error.code) || /does not exist|schema cache/i.test(error.message || ""));
}
function falla(error) {
  if (!error) return;
  if (noActivado(error)) throw new Error("El feedback todavía no está activado: falta correr supabase/esquema.sql en Supabase (SQL Editor).");
  throw new Error(error.message || "No se pudo conectar con el feedback.");
}

// lo que se guarda de quien escribe (para que los demás lo vean sin leer su cuenta)
function quien() {
  const c = conexion(), p = perfil();
  return { autor: c.user.id, nombre: nombrePublico().slice(0, 60), detalle: [p.oficio, p.ciudad].filter(Boolean).join(" · ").slice(0, 90),
    avatar: p.foto || "" };
}

// modo de prueba (tests en localhost): todo en memoria
const mock = { lista: null, resp: [], votos: [], seq: 100 };
function mockLista() {
  if (!mock.lista) {
    const sem = window.__EDEN_FEEDBACK_MOCK || [];
    mock.lista = sem.map((f, i) => ({ id: i + 1, autor: "otro", nombre: "Alguien", detalle: "", avatar: "", herramienta: "general",
      tipo: "idea", estado: "abierto", creado: new Date(Date.now() - (i + 1) * 3600e3).toISOString(), ...f }));
  }
  return mock.lista;
}

export const datos = {
  async listar() {
    const c = conexion();
    let fb, resp, votos;
    if (c.mock) {
      fb = [...mockLista()].sort((a, b) => b.creado.localeCompare(a.creado));
      resp = mock.resp;
      votos = mock.votos;
    } else {
      const r = await c.client.from("feedback").select("*").order("creado", { ascending: false }).limit(150);
      falla(r.error);
      fb = r.data || [];
      const ids = fb.map((f) => f.id);
      resp = [];
      votos = [];
      if (ids.length) {
        const [a, b] = await Promise.all([
          c.client.from("feedback_respuestas").select("*").in("feedback_id", ids).order("creado", { ascending: true }),
          c.client.from("feedback_votos").select("feedback_id,autor").in("feedback_id", ids),
        ]);
        falla(a.error);
        falla(b.error);
        resp = a.data || [];
        votos = b.data || [];
      }
    }
    const yo = c.user && c.user.id;
    return fb.map((f) => ({ ...f, mio: f.autor === yo,
      respuestas: resp.filter((r) => r.feedback_id === f.id).map((r) => ({ ...r, mio: r.autor === yo })),
      votos: votos.filter((v) => v.feedback_id === f.id).length,
      yoVoto: votos.some((v) => v.feedback_id === f.id && v.autor === yo) }));
  },

  async enviar({ tipo, herramienta, texto }) {
    texto = String(texto || "").trim();
    if (texto.length < 3) throw new Error("Escribí un poco más: contá qué pasó o qué te gustaría.");
    if (texto.length > LARGO) throw new Error(`Hasta ${LARGO} caracteres.`);
    const fila = { ...quien(), tipo: TIPOS[tipo] ? tipo : "idea", herramienta: HERRAMIENTAS[herramienta] ? herramienta : "general", texto };
    const c = conexion();
    if (c.mock) { mockLista().push({ ...fila, id: ++mock.seq, estado: "abierto", creado: new Date().toISOString() }); return; }
    const { error } = await c.client.from("feedback").insert(fila);
    falla(error);
  },

  async responder(id, texto) {
    texto = String(texto || "").trim();
    if (!texto) throw new Error("Escribí tu respuesta.");
    const { autor, nombre, avatar } = quien();
    const fila = { feedback_id: id, autor, nombre, avatar, texto: texto.slice(0, LARGO_RESP) };
    const c = conexion();
    if (c.mock) { mock.resp.push({ ...fila, id: ++mock.seq, creado: new Date().toISOString() }); return; }
    const { error } = await c.client.from("feedback_respuestas").insert(fila);
    falla(error);
  },

  async votar(id, si) {
    const c = conexion(), yo = c.user.id;
    if (c.mock) {
      mock.votos = mock.votos.filter((v) => !(v.feedback_id === id && v.autor === yo));
      if (si) mock.votos.push({ feedback_id: id, autor: yo });
      return;
    }
    const q = si ? c.client.from("feedback_votos").insert({ feedback_id: id, autor: yo })
      : c.client.from("feedback_votos").delete().eq("feedback_id", id).eq("autor", yo);
    const { error } = await q;
    if (error && error.code !== "23505") falla(error);           // ya estaba: no pasa nada
  },

  async estado(id, estado) {
    const c = conexion();
    if (c.mock) { const f = mockLista().find((x) => x.id === id); if (f) f.estado = estado; return; }
    const { error } = await c.client.from("feedback").update({ estado }).eq("id", id);
    falla(error);
  },

  async borrar(id) {
    const c = conexion();
    if (c.mock) { mock.lista = mockLista().filter((x) => x.id !== id); mock.resp = mock.resp.filter((r) => r.feedback_id !== id); return; }
    const { error } = await c.client.from("feedback").delete().eq("id", id);
    falla(error);
  },

  async borrarRespuesta(id) {
    const c = conexion();
    if (c.mock) { mock.resp = mock.resp.filter((r) => r.id !== id); return; }
    const { error } = await c.client.from("feedback_respuestas").delete().eq("id", id);
    falla(error);
  },
};

// ---------------------------------------------------------------- interfaz
const RTF = new Intl.RelativeTimeFormat("es", { numeric: "auto" });
function hace(iso) {
  const s = (new Date(iso).getTime() - Date.now()) / 1000;
  for (const [u, k] of [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (Math.abs(s) >= k) return RTF.format(Math.round(s / k), u);
  }
  return "recién";
}

const ICONO = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5h16v10.5H9.5L5 20v-4H4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 9.5h8M8 12.5h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`;

const ui = { dlg: null, btn: null, auth: null, filtro: "todos", abiertos: new Set(), lista: [], login: null, tipo: "idea" };

export function mountFeedback(openLogin) {
  if (ui.btn) return;
  ui.login = openLogin;
  const b = document.createElement("button");
  b.type = "button";
  b.className = "fb-flotante";
  b.dataset.testid = "btn-feedback";
  b.hidden = true;
  b.innerHTML = `${ICONO}<span>Feedback</span>`;
  b.setAttribute("aria-label", "Dejar feedback");
  b.addEventListener("click", () => abrirFeedback());
  document.body.appendChild(b);
  ui.btn = b;
  onAuth((a) => {
    ui.auth = a;
    b.hidden = !a.configured;                      // sin cuentas no hay dónde guardarlo
    if (ui.dlg && ui.dlg.open) pintar();
  });
}

function q(sel) { return ui.dlg.querySelector(sel); }

function crearDialogo() {
  const d = document.createElement("dialog");
  d.className = "modal";
  d.dataset.testid = "feedback";
  d.setAttribute("aria-labelledby", "fb-titulo");
  d.innerHTML = `
    <div class="modal-box fb-box">
      <button type="button" class="modal-x" aria-label="Cerrar" data-close>×</button>
      <h2 id="fb-titulo">Feedback de la comunidad</h2>
      <p class="fb-intro">Contá qué mejorarías, qué no anda o qué te gustaría que sumemos. Lo leen todos los que participan: sumate a lo que ya dijeron o respondé.</p>
      <div class="fb-ingresar" data-testid="fb-ingresar" hidden>
        <p>Ingresá con tu cuenta para leer y dejar feedback.</p>
        <button type="button" class="primary" data-testid="fb-btn-ingresar">Ingresar</button>
      </div>
      <form class="fb-form" data-testid="fb-form" hidden>
        <div class="seg seg3 fb-tipos" role="radiogroup" aria-label="Tipo de feedback">
          ${Object.entries(TIPOS).map(([k, n]) => `<button type="button" role="radio" data-tipo="${k}" data-testid="fb-tipo-${k}">${n}</button>`).join("")}
        </div>
        <label>Sobre
          <select data-testid="fb-herramienta">${Object.entries(HERRAMIENTAS).map(([k, n]) => `<option value="${k}">${n}</option>`).join("")}</select>
        </label>
        <label>Descripción <span class="hint" id="fb-n"></span>
          <textarea rows="4" maxlength="${LARGO}" data-testid="fb-texto"
            placeholder="Por ejemplo: en el mate me gustaría elegir el grosor del borde…"></textarea>
        </label>
        <p class="login-msg" id="fb-msg" role="alert"></p>
        <button type="submit" class="primary" data-testid="fb-enviar">Enviar feedback</button>
      </form>
      <div class="fb-listado" hidden>
        <div class="fb-filtros" role="group" aria-label="Mostrar">
          ${[["todos", "Todos"], ["idea", "Ideas"], ["error", "Algo no anda"], ["comentario", "Comentarios"]].map(([k, n]) =>
            `<button type="button" data-filtro="${k}" data-testid="fb-filtro-${k}" aria-pressed="false">${n}</button>`).join("")}
        </div>
        <p class="fb-estado" data-testid="fb-estado" role="status"></p>
        <ul class="fb-lista" data-testid="fb-lista"></ul>
      </div>
    </div>`;
  document.body.appendChild(d);
  ui.dlg = d;
  q("[data-close]").addEventListener("click", () => d.close());
  d.addEventListener("click", (e) => { if (e.target === d) d.close(); });
  q("[data-testid=fb-btn-ingresar]").addEventListener("click", () => { d.close(); ui.login && ui.login("Ingresá para dejar feedback."); });
  q(".fb-tipos").addEventListener("click", (e) => {
    const b = e.target.closest("[data-tipo]");
    if (b) { ui.tipo = b.dataset.tipo; pintarTipo(); }
  });
  const txt = q("[data-testid=fb-texto]");
  const contar = () => { q("#fb-n").textContent = `${txt.value.length}/${LARGO}`; };
  txt.addEventListener("input", contar);
  ui.contar = contar;
  q(".fb-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const ok = q("[data-testid=fb-enviar]");
    ok.disabled = true;
    q("#fb-msg").textContent = "";
    try {
      await datos.enviar({ tipo: ui.tipo, herramienta: q("[data-testid=fb-herramienta]").value, texto: txt.value });
      txt.value = "";
      contar();
      q("#fb-msg").textContent = "¡Gracias! Ya lo pueden ver todos.";
      q("#fb-msg").classList.add("ok");
      await cargar();
    } catch (e) { q("#fb-msg").classList.remove("ok"); q("#fb-msg").textContent = e.message; }
    finally { ok.disabled = false; }
  });
  q(".fb-filtros").addEventListener("click", (e) => {
    const b = e.target.closest("[data-filtro]");
    if (b) { ui.filtro = b.dataset.filtro; pintarLista(); }
  });
  q(".fb-lista").addEventListener("click", accion);
  q(".fb-lista").addEventListener("submit", responder);
}

function pintarTipo() {
  for (const b of q(".fb-tipos").children) b.setAttribute("aria-checked", String(b.dataset.tipo === ui.tipo));
}

export function abrirFeedback() {
  if (!ui.dlg) crearDialogo();
  ui.tipo = "idea";
  q("[data-testid=fb-herramienta]").value = herramientaDeLaPagina();
  q("#fb-msg").textContent = "";
  ui.contar();
  pintarTipo();
  pintar();
  if (!ui.dlg.open) ui.dlg.showModal();
}

function pintar() {
  const a = ui.auth || {};
  const adentro = !!a.user;
  q("[data-testid=fb-ingresar]").hidden = adentro;
  q(".fb-form").hidden = !adentro;
  q(".fb-listado").hidden = !adentro;
  if (adentro) cargar();
}

async function cargar() {
  const est = q("[data-testid=fb-estado]");
  if (!ui.lista.length) est.textContent = "Cargando…";
  try {
    ui.lista = await datos.listar();
    est.textContent = "";
  } catch (e) {
    ui.lista = [];
    est.textContent = e.message;
  }
  pintarLista();
}

function pintarLista() {
  for (const b of q(".fb-filtros").children) b.setAttribute("aria-pressed", String(b.dataset.filtro === ui.filtro));
  const admin = !!(ui.auth && ui.auth.perms && ui.auth.perms.admin);
  const items = ui.lista.filter((f) => ui.filtro === "todos" || f.tipo === ui.filtro);
  const est = q("[data-testid=fb-estado]");
  if (!items.length && !est.textContent) est.textContent = ui.lista.length ? "No hay nada de este tipo todavía." : "Todavía no hay feedback: ¡dejá el primero!";
  else if (items.length && /todavía/.test(est.textContent)) est.textContent = "";
  q(".fb-lista").innerHTML = items.map((f) => {
    const abierto = ui.abiertos.has(f.id);
    return `<li class="fb-item${f.estado === "resuelto" ? " resuelto" : ""}" data-id="${f.id}" data-testid="fb-item">
      <div class="fb-cab">
        <span class="fb-cara">${caraHTML(f.avatar, iniciales(f.nombre))}</span>
        <div class="fb-quien"><strong>${esc(f.nombre)}</strong><small>${[f.detalle, hace(f.creado)].filter(Boolean).map(esc).join(" · ")}</small></div>
        <div class="fb-tags"><span class="fb-tag tipo-${esc(f.tipo)}">${esc(TIPOS[f.tipo] || f.tipo)}</span>
          <span class="fb-tag">${esc(HERRAMIENTAS[f.herramienta] || f.herramienta)}</span>
          ${f.estado === "resuelto" ? `<span class="fb-tag ok" data-testid="fb-resuelto">Resuelto</span>` : ""}</div>
      </div>
      <p class="fb-texto">${esc(f.texto)}</p>
      <div class="fb-acc">
        <button type="button" data-acc="votar" data-testid="fb-votar" aria-pressed="${f.yoVoto}">Me sumo <b>${f.votos}</b></button>
        <button type="button" data-acc="ver" data-testid="fb-ver" aria-expanded="${abierto}">Responder${f.respuestas.length ? ` <b>${f.respuestas.length}</b>` : ""}</button>
        ${admin ? `<button type="button" data-acc="estado" data-testid="fb-resolver">${f.estado === "resuelto" ? "Reabrir" : "Marcar resuelto"}</button>` : ""}
        ${f.mio || admin ? `<button type="button" data-acc="borrar" class="fb-borrar" data-testid="fb-borrar">Borrar</button>` : ""}
      </div>
      <div class="fb-resp" ${abierto ? "" : "hidden"}>
        <ul>${f.respuestas.map((r) => `<li data-rid="${r.id}" data-testid="fb-respuesta">
          <span class="fb-cara chica">${caraHTML(r.avatar, iniciales(r.nombre))}</span>
          <div><strong>${esc(r.nombre)}</strong> <small>${esc(hace(r.creado))}</small><p>${esc(r.texto)}</p></div>
          ${r.mio || admin ? `<button type="button" data-acc="borrar-resp" class="fb-borrar" aria-label="Borrar respuesta">Borrar</button>` : ""}</li>`).join("")}</ul>
        <form class="fb-resp-form"><textarea rows="2" maxlength="${LARGO_RESP}" placeholder="Tu respuesta…" data-testid="fb-resp-texto"></textarea>
          <button type="submit" data-testid="fb-resp-enviar">Responder</button></form>
      </div>
    </li>`;
  }).join("");
}

async function accion(e) {
  const b = e.target.closest("button[data-acc]");
  if (!b) return;
  const li = b.closest("[data-id]"), id = +li.dataset.id;
  const f = ui.lista.find((x) => x.id === id);
  const acc = b.dataset.acc;
  if (acc === "ver") {
    ui.abiertos.has(id) ? ui.abiertos.delete(id) : ui.abiertos.add(id);
    pintarLista();
    if (ui.abiertos.has(id)) q(`[data-id="${id}"] textarea`).focus();
    return;
  }
  // borrar: el primer toque pide confirmación en el mismo botón
  if ((acc === "borrar" || acc === "borrar-resp") && !b.dataset.seguro) {
    b.dataset.seguro = "1";
    b.textContent = "¿Seguro? Tocá de nuevo";
    setTimeout(() => { if (b.isConnected) { delete b.dataset.seguro; b.textContent = "Borrar"; } }, 4000);
    return;
  }
  b.disabled = true;
  try {
    if (acc === "votar") await datos.votar(id, !f.yoVoto);
    else if (acc === "estado") await datos.estado(id, f.estado === "resuelto" ? "abierto" : "resuelto");
    else if (acc === "borrar") await datos.borrar(id);
    else if (acc === "borrar-resp") await datos.borrarRespuesta(+b.closest("[data-rid]").dataset.rid);
    await cargar();
  } catch (err) {
    q("[data-testid=fb-estado]").textContent = err.message;
    b.disabled = false;
  }
}

async function responder(e) {
  e.preventDefault();
  const form = e.target.closest(".fb-resp-form");
  if (!form) return;
  const id = +form.closest("[data-id]").dataset.id;
  const t = form.querySelector("textarea");
  try {
    await datos.responder(id, t.value);
    ui.abiertos.add(id);
    await cargar();
  } catch (err) { q("[data-testid=fb-estado]").textContent = err.message; }
}
