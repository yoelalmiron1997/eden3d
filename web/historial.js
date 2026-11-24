// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Historial de cada generador: deshacer / rehacer (Ctrl+Z, Ctrl+Shift+Z o Ctrl+Y), volver
// a la vista inicial de la cámara y volver a los valores por defecto ("Default").
//
// Cada vez que el motor termina de armar un modelo se guarda un paso: el valor de los
// controles del modelo (no los de la vista: colores, escenario, plantas) y el estado propio
// de la página (la forma de la chapita, la figura del trofeo, la decoración del mate…).
// Deshacer vuelve a poner esos valores, refresca la página y vuelve a armar el modelo; ese
// armado no crea un paso nuevo. El primer modelo es el "origen": "Default" vuelve a él como
// un paso más, así que también se puede deshacer.
//
//   window.__historial = montarHistorial({
//     controles: () => ["ancho", "nombre", …],        // ids de los controles del modelo
//     extra: { capturar: () => ({ forma: state.forma }), restaurar: (x) => { … } },
//     refrescar: () => { …etiquetas, ui()… },          // después de poner los valores
//     generar: () => build(),
//     version: () => state.builds, ocupado: () => state.busy,
//     viewer,                                          // para el botón "Inicio" de la cámara
//   });

const MAX_PASOS = 100;

export function montarHistorial({ controles, extra = null, refrescar = () => {}, generar, version, ocupado, viewer }) {
  let pila = [];            // [{ c: {id: valor}, x: {...}, clave }]
  let pos = -1;
  let origen = null;
  let visto = null;         // última versión del modelo registrada
  let restaurando = false;  // el próximo modelo es el de un deshacer/rehacer/de cero
  let tAplicar = 0;
  let tocado = false;       // la persona cambió algo después de deshacer
  for (const tipo of ["input", "change", "click"]) {
    document.addEventListener(tipo, (e) => {
      if (e.isTrusted && !(e.target.closest && e.target.closest(".historial, .vistas, dialog"))) tocado = true;
    }, true);
  }

  const capturar = () => {
    const c = {};
    for (const id of controles()) {
      const el = document.getElementById(id);
      if (!el || el.type === "file") continue;
      c[id] = el.type === "checkbox" || el.type === "radio" ? el.checked : el.value;
    }
    const x = extra ? JSON.parse(JSON.stringify(extra.capturar() ?? null)) : null;
    const paso = { c, x };
    paso.clave = JSON.stringify([c, x]);
    return paso;
  };

  const poner = (c) => {
    for (const [id, v] of Object.entries(c)) {
      const el = document.getElementById(id);
      if (!el) continue;
      if (el.type === "checkbox" || el.type === "radio") el.checked = !!v;
      else if (el.tagName === "SELECT" && ![...el.options].some((o) => o.value === v)) continue;
      else el.value = v;
    }
  };

  const aplicar = (paso) => {
    restaurando = true;
    tocado = false;
    tAplicar = Date.now();
    // dos pasadas: hay controles que aparecen o cambian según otros (selects, figura…)
    poner(paso.c);
    if (extra) extra.restaurar(JSON.parse(JSON.stringify(paso.x)));
    poner(paso.c);
    // las etiquetas de los sliders se actualizan con su evento "input" (no arma nada)
    for (const id of Object.keys(paso.c)) {
      const el = document.getElementById(id);
      if (el && el.type === "range") el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    refrescar();
    generar();
    pintar();
  };

  const registrar = () => {
    const v = version();
    if (!v || v === visto || ocupado()) return;          // todavía no hay ningún modelo armado
    visto = v;
    const paso = capturar();
    if (restaurando && tocado) restaurando = false;   // lo nuevo es un cambio de la persona
    if (restaurando) {
      // el modelo del paso restaurado: se guarda como quedó (el motor puede completar
      // valores, p. ej. dónde quedó el relieve del mate), sin crear un paso nuevo
      restaurando = false;
      if (pos >= 0) pila[pos] = paso;
    } else if (pos < 0 || pila[pos].clave !== paso.clave) {
      pila = pila.slice(0, pos + 1);
      pila.push(paso);
      if (pila.length > MAX_PASOS) pila.shift();
      pos = pila.length - 1;
    }
    if (!origen) origen = paso;
    pintar();
  };
  // si el armado restaurado falla (modelo inválido) no queda "restaurando" para siempre
  const vigilar = () => {
    if (restaurando && Date.now() - tAplicar > 60000) restaurando = false;
    registrar();
  };
  setInterval(vigilar, 250);

  const deshacer = () => { if (pos > 0) { pos--; aplicar(pila[pos]); } };
  const rehacer = () => { if (pos < pila.length - 1) { pos++; aplicar(pila[pos]); } };
  const deCero = () => {
    if (!origen) return;
    if (pila[pos] && pila[pos].clave === origen.clave) return;
    pila = pila.slice(0, pos + 1);
    pila.push(origen);
    pos = pila.length - 1;
    aplicar(origen);
  };

  // ---------------------------------------------------------------- botones sobre el visor
  const host = viewer && viewer.renderer ? viewer.renderer.domElement.parentElement : null;
  const bar = document.createElement("div");
  bar.className = "historial";
  bar.setAttribute("role", "toolbar");
  bar.setAttribute("aria-label", "Historial de cambios");
  bar.dataset.testid = "historial";
  bar.innerHTML = `
    <button type="button" data-h="deshacer" data-testid="btn-deshacer" title="Deshacer (Ctrl+Z)" aria-label="Deshacer">↶</button>
    <button type="button" data-h="rehacer" data-testid="btn-rehacer" title="Rehacer (Ctrl+Shift+Z o Ctrl+Y)" aria-label="Rehacer">↷</button>
    <button type="button" data-h="cero" data-testid="btn-default" title="Volver a los valores por defecto del generador (se puede deshacer)">Default</button>`;
  bar.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-h]");
    if (!b || b.disabled) return;
    ({ deshacer, rehacer, cero: deCero })[b.dataset.h]();
  });
  if (host) host.appendChild(bar);

  function pintar() {
    bar.querySelector("[data-h=deshacer]").disabled = pos <= 0;
    bar.querySelector("[data-h=rehacer]").disabled = pos >= pila.length - 1;
    bar.querySelector("[data-h=cero]").disabled = !origen || (pila[pos] && pila[pos].clave === origen.clave);
  }
  pintar();

  // ---------------------------------------------------------------- teclado
  // En un campo de texto, Ctrl+Z deshace lo escrito (lo normal del navegador); en el resto
  // de la página deshace el último cambio del modelo.
  document.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k !== "z" && k !== "y") return;
    const t = e.target;
    const escribe = t && (t.isContentEditable || t.tagName === "TEXTAREA"
      || (t.tagName === "INPUT" && !["range", "checkbox", "radio", "button", "color", "file"].includes(t.type)));
    if (escribe || document.querySelector("dialog[open]")) return;
    e.preventDefault();
    if (k === "y" || e.shiftKey) rehacer();
    else deshacer();
  });

  return {
    deshacer, rehacer, deCero,
    get pasos() { return pila.length; },
    get posicion() { return pos; },
    get origen() { return origen; },
    get claves() { return pila.map((p) => p.clave); },
    capturar,
  };
}
