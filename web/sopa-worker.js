// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Web Worker de la "Sopa de letras 3D": carga Pyodide y el motor (sopa_web.py).
/* global importScripts, loadPyodide */
importScripts("./vendor/pyodide/pyodide.js");

let py = null;
let api = null;

async function init() {
  const t0 = performance.now();
  self.postMessage({ type: "progreso", paso: 1 });
  py = await loadPyodide({ indexURL: "./vendor/pyodide/" });
  self.postMessage({ type: "progreso", paso: 2 });     // Python listo: ahora el motor
  const manifest = await (await fetch("./py/manifest.json", { cache: "no-cache" })).json();
  py.FS.mkdirTree("/eden/colecciones");
  const need = ["eden_core.py", "eden_surface.py", "eden_floor.py", "eden_font.py", "sopa_core.py", "sopa_web.py"];
  for (const f of manifest.files.filter((x) => need.includes(x))) {
    const txt = await (await fetch("./py/" + f + "?v=" + manifest.version)).text();
    py.FS.writeFile("/eden/" + f, txt);
  }
  py.runPython("import sys; sys.path.insert(0, '/eden'); import sopa_web");
  api = py.pyimport("sopa_web");
  const info = api.info().toJs({ dict_converter: Object.fromEntries });
  return { info, seconds: (performance.now() - t0) / 1000, version: manifest.version };
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
      parts.push({ name: p.get("name"), pieza: p.get("pieza"), positions: bytesOf(p.get("positions")), indices: bytesOf(p.get("indices")) });
      p.destroy();
    }
    pl.destroy();
    return { summary, parts };
  } finally {
    res.destroy();
  }
}

function exportFile(kind, opts) {
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
  const { id, type, opts } = ev.data;
  try {
    const boot = await ready;
    if (type === "init") {
      self.postMessage({ id, ok: true, result: boot });
    } else if (type === "build") {
      const r = build(opts);
      self.postMessage({ id, ok: true, result: r }, r.parts.flatMap((p) => [p.positions, p.indices]));
    } else if (type === "3mf" || type === "stl") {
      const r = exportFile(type, opts);
      self.postMessage({ id, ok: true, result: r }, [r.data]);
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
