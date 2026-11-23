// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Web Worker de la banda de recibida: carga Pyodide y el motor (banda_web.py).
/* global importScripts, loadPyodide */
importScripts("./vendor/pyodide/pyodide.js", "./motor-carga.js");

let py = null;
let api = null;
let version = "";

async function init() {
  const m = await cargarMotor({ archivos: ["eden_core.py", "cotizador.py", "eden_surface.py", "eden_floor.py", "eden_font.py", "mate_fuentes.py",
    "banda_core.py", "banda_web.py"], modulo: "banda_web" });
  py = m.py;
  api = m.api;
  version = m.version;
  const info = api.info().toJs({ dict_converter: Object.fromEntries });
  fuentesDe(info.defecto).catch(() => {});      // la tipografía por defecto, ya mismo
  return { info, seconds: (performance.now() - m.t0) / 1000, version };
}

// cada tipografía se baja sólo cuando se usa (100–460 KB)
const estadoMotor = { get py() { return py; }, get version() { return version; } };
const fuente = crearFuentes(estadoMotor);
async function fuentesDe(opts) {
  await fuente(opts && opts.fuente);
}

function bytesOf(proxy) {
  const buf = proxy.getBuffer("u8");
  try {
    return buf.data.slice().buffer;
  } finally {
    buf.release();
    proxy.destroy();
  }
}

function build(opts) {
  const res = api.build(py.toPy(opts));
  try {
    const sp = res.get("summary");
    const summary = sp.toJs({ dict_converter: Object.fromEntries });
    sp.destroy();
    const parts = [];
    const pl = res.get("parts");
    for (let i = 0; i < pl.length; i++) {
      const p = pl.get(i);
      parts.push({ name: p.get("name"), positions: bytesOf(p.get("positions")), indices: bytesOf(p.get("indices")) });
      p.destroy();
    }
    pl.destroy();
    return { summary, parts };
  } finally {
    res.destroy();
  }
}

function exportFile(kind, opts, pieza) {
  const o = py.toPy(opts);
  const r = kind === "3mf" ? api.export_3mf(o) : api.export_stl(o);
  try {
    return { name: r.get(0), data: bytesOf(r.get(1)) };
  } finally {
    r.destroy();
  }
}

const ready = init();

self.onmessage = async (ev) => {
  const { id, type, opts, pieza } = ev.data;
  try {
    const boot = await ready;
    if (type === "init") {
      self.postMessage({ id, ok: true, result: boot });
    } else if (type === "build") {
      await fuentesDe(opts);
      const r = build(opts);
      self.postMessage({ id, ok: true, result: r }, r.parts.flatMap((p) => [p.positions, p.indices]));
    } else if (type === "cotizar") {           // piezas para imprimir medidas (cotizador.js)
      await fuentesDe(opts);
      const r = api.cotizar(py.toPy(opts));
      const out = r.toJs({ dict_converter: Object.fromEntries });
      r.destroy();
      self.postMessage({ id, ok: true, result: out });
    } else if (type === "3mf" || type === "stl") {
      await fuentesDe(opts);
      const r = exportFile(type, opts, pieza);
      self.postMessage({ id, ok: true, result: r }, [r.data]);
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
