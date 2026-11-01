// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Web Worker de los trofeos para eventos: carga Pyodide y el motor (trofeo_web.py).
/* global importScripts, loadPyodide */
importScripts("./vendor/pyodide/pyodide.js");

let py = null;
let api = null;
let version = "";
const fuentes = new Set();

async function init() {
  const t0 = performance.now();
  self.postMessage({ type: "progreso", paso: 1 });
  py = await loadPyodide({ indexURL: "./vendor/pyodide/" });
  self.postMessage({ type: "progreso", paso: 2 });     // Python listo: ahora el motor
  const manifest = await (await fetch("./py/manifest.json", { cache: "no-cache" })).json();
  version = manifest.version;
  py.FS.mkdirTree("/eden/colecciones");
  py.FS.mkdirTree("/eden/fuentes");
  const need = ["eden_core.py", "eden_surface.py", "eden_floor.py", "eden_font.py", "mate_fuentes.py",
    "topper_core.py", "trofeo_core.py", "trofeo_web.py"];
  for (const f of manifest.files.filter((x) => need.includes(x))) {
    const txt = await (await fetch("./py/" + f + "?v=" + manifest.version)).text();
    py.FS.writeFile("/eden/" + f, txt);
  }
  py.runPython("import sys; sys.path.insert(0, '/eden'); import trofeo_web");
  api = py.pyimport("trofeo_web");
  const info = api.info().toJs({ dict_converter: Object.fromEntries });
  return { info, seconds: (performance.now() - t0) / 1000, version };
}

// cada tipografía se baja sólo cuando se usa (100–460 KB)
async function fuente(id) {
  if (!id || fuentes.has(id)) return;
  const res = await fetch("./py/fuentes/" + id + ".json?v=" + version);
  if (!res.ok) throw new Error("No se pudo bajar la tipografía " + id);
  py.FS.writeFile("/eden/fuentes/" + id + ".json", new Uint8Array(await res.arrayBuffer()));
  fuentes.add(id);
}
async function fuentesDe(opts) {
  await fuente(opts && opts.fuente);
  if (opts && opts.figura === "numero") await fuente(opts.fuente_figura);
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
  const r = kind === "3mf" ? api.export_3mf(o) : api.export_stl(o, pieza || "FIGURA");
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
    } else if (type === "3mf" || type === "stl") {
      await fuentesDe(opts);
      const r = exportFile(type, opts, pieza);
      self.postMessage({ id, ok: true, result: r }, [r.data]);
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
