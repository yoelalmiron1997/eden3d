// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Inicio: catálogo (desde herramientas.js) con buscador y filtros, menú del celular,
// giro del isotipo, pop-ups de cada herramienta y la cuenta (auth-ui.js).
import { mountAccount } from "./auth-ui.js";
import { CATEGORIAS, HERRAMIENTAS, REDES } from "./herramientas.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ico = (id) => `<svg class="tb-ico" aria-hidden="true"><use href="#i-${id}"/></svg>`;
const cat = Object.fromEntries(CATEGORIAS.map((c) => [c.id, c]));
const sinTildes = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// ------------------------------------------------------------------ catálogo
function tarjeta(h, i) {
  const c = cat[h.categoria];
  return `
    <li class="tb-card" data-id="${h.id}" data-cat="${h.categoria}" data-buscar="${esc(sinTildes(h.nombre + " " + h.corto + " " + h.descripcion + " " + c.nombre))}">
      <button type="button" class="tb-card-foto" data-testid="tool-${h.id}" aria-haspopup="dialog" data-modal="${h.modal}">
        <img src="${h.imagen}" srcset="${h.imagen} 450w, ${h.imagen2x} 900w" sizes="(max-width: 640px) 92vw, (max-width: 1100px) 46vw, 320px"
          alt="${esc(h.alt)}" width="450" height="563" ${i ? 'loading="lazy"' : ""} decoding="async"
          style="object-position:${h.foco}" data-testid="${h.testImagen}">
        <span class="tb-card-ver">Ver detalles</span><span class="tb-sr">: ${esc(h.nombre)}</span>
      </button>
      <div class="tb-card-cuerpo">
        <h3>${esc(h.nombre)}</h3>
        <p class="tb-card-desc">${esc(h.descripcion)}</p>
        <p class="tb-cat">${ico(c.icono)}${esc(c.nombre)}</p>
        <a class="tb-btn tb-btn-card" href="${h.ruta}" data-testid="ir-${h.id}">Abrir herramienta${ico("flecha")}<span class="tb-sr">: ${esc(h.nombre)}</span></a>
      </div>
    </li>`;
}

function armarCatalogo() {
  $("#tb-grilla").innerHTML = HERRAMIENTAS.map(tarjeta).join("");
  $("#tb-indice").innerHTML = HERRAMIENTAS.map((h) => `
    <li><a href="${h.ruta}" data-testid="indice-${h.id}"><span class="tb-indice-n">${esc(h.corto)}</span>
      <span class="tb-indice-c">${esc(cat[h.categoria].nombre)}</span>${ico("flecha")}</a></li>`).join("");
  $("#tb-filtros").innerHTML = [{ id: "todas", nombre: "Todas", icono: "todas" }, ...CATEGORIAS].map((c) => `
    <button type="button" class="tb-filtro" data-cat="${c.id}" aria-pressed="${c.id === "todas"}" data-testid="filtro-${c.id}">${ico(c.icono)}${esc(c.nombre)}</button>`).join("");
  $("#tb-pie-herr").innerHTML = HERRAMIENTAS.map((h) => `<a href="${h.ruta}">${esc(h.nombre)}</a>`).join("");
  $("#tb-redes").innerHTML = REDES.map((r) => `
    <a class="tb-red" href="${r.url}" target="_blank" rel="noopener noreferrer" data-testid="red-${r.id}">${ico(r.id)}
      <span><strong>${esc(r.nombre)}</strong> ${esc(r.usuario)}</span><span class="tb-sr"> (abre en otra pestaña)</span></a>`).join("");
}

let categoria = "todas";
function filtrar() {
  const q = sinTildes($("#tb-q").value.trim());
  const palabras = q.split(/\s+/).filter(Boolean);
  let n = 0;
  for (const li of document.querySelectorAll(".tb-card")) {
    const ok = (categoria === "todas" || li.dataset.cat === categoria) && palabras.every((p) => li.dataset.buscar.includes(p));
    li.hidden = !ok;
    n += ok ? 1 : 0;
  }
  $("#tb-n").textContent = String(n);
  $("#tb-n-txt").textContent = n === 1 ? "herramienta" : "herramientas";
  $("#tb-vacio").hidden = n > 0;
  for (const b of document.querySelectorAll(".tb-filtro")) b.setAttribute("aria-pressed", String(b.dataset.cat === categoria));
}

// ------------------------------------------------------------------ menú del celular
function menu() {
  const head = $(".tb-nav"), btn = $(".tb-hamb");
  const set = (abierto) => {
    head.dataset.abierto = String(abierto);
    btn.setAttribute("aria-expanded", String(abierto));
    btn.querySelector("use").setAttribute("href", abierto ? "#i-cerrar" : "#i-menu");
    btn.querySelector(".tb-sr").textContent = abierto ? "Cerrar menú" : "Abrir menú";
  };
  btn.addEventListener("click", () => set(head.dataset.abierto !== "true"));
  $("#tb-menu").addEventListener("click", (e) => { if (e.target.closest("a")) set(false); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && head.dataset.abierto === "true") { set(false); btn.focus(); }
  });
  matchMedia("(min-width: 961px)").addEventListener("change", (m) => { if (m.matches) set(false); });
}

// ------------------------------------------------------------------ giro del isotipo
// El giro es CSS (18 s por vuelta); al pasar el mouse acelera sin saltar, cambiando la
// velocidad de la misma animación. Con movimiento reducido no hay animación.
function giro() {
  for (const el of document.querySelectorAll(".tb-iso:not(.tb-iso-quieto)")) {
    const zona = el.closest(".tb-marca, .tb-placa") || el;
    const vel = (v) => { for (const a of el.getAnimations()) a.updatePlaybackRate(v); };
    zona.addEventListener("pointerenter", () => vel(3));
    zona.addEventListener("pointerleave", () => vel(1));
    zona.addEventListener("focusin", () => vel(3));
    zona.addEventListener("focusout", () => vel(1));
  }
}

// ------------------------------------------------------------------ pop-ups
function modales() {
  for (const d of document.querySelectorAll("dialog.modal")) {
    d.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => d.close()));
    d.addEventListener("click", (e) => { if (e.target === d) d.close(); });
  }
  $("#tb-grilla").addEventListener("click", (e) => {
    const b = e.target.closest("[data-modal]");
    if (b) document.getElementById(b.dataset.modal).showModal();
  });
  // la primera visita muestra el generador de macetas en un pop-up
  let visto = false;
  try { visto = localStorage.getItem("tb-popup-macetas") === "1"; localStorage.setItem("tb-popup-macetas", "1"); } catch (e) { /* sin almacenamiento */ }
  if (!visto) setTimeout(() => { if (!document.querySelector("dialog[open]")) $("#tool-modal").showModal(); }, 500);
}

// ------------------------------------------------------------------ aparición
// El contenido se ve siempre; si hay movimiento, entra con un desplazamiento corto.
function aparicion() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver((es) => {
    for (const e of es) if (e.isIntersecting) { e.target.classList.add("tb-visto"); io.unobserve(e.target); }
  }, { rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".tb-card, .tb-ben li").forEach((el, i) => {
    if (el.getBoundingClientRect().top > innerHeight) {
      el.classList.add("tb-entra");
      el.style.setProperty("--tb-retraso", `${(i % 4) * 70}ms`);
      io.observe(el);
    }
  });
}

armarCatalogo();
filtrar();
$("#tb-q").addEventListener("input", filtrar);
$("#tb-filtros").addEventListener("click", (e) => {
  const b = e.target.closest(".tb-filtro");
  if (!b) return;
  categoria = b.dataset.cat;
  filtrar();
});
$("#tb-limpiar").addEventListener("click", () => {
  $("#tb-q").value = "";
  categoria = "todas";
  filtrar();
  $("#tb-q").focus();
});
$("#tb-anio").textContent = String(new Date().getFullYear());
menu();
giro();
modales();
aparicion();
mountAccount($("#account"));
