// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Web Worker del "Mate con hueco": carga Pyodide y el motor de mates (mate_web.py).
/* global importScripts, loadPyodide */
importScripts("./vendor/pyodide/pyodide.js");

let py = null;
let api = null;
let version = "";
const fuentes = new Set();

// las tipografías se bajan sólo cuando se eligen (cada una pesa 100–400 KB)
async function fuente(id) {
  if (!id || id === "eden" || fuentes.has(id)) return;
  const res = await fetch("./py/fuentes/" + id + ".json?v=" + version);
  if (!res.ok) throw new Error("No se pudo bajar la tipografía " + id);
  py.FS.writeFile("/eden/fuentes/" + id + ".json", new Uint8Array(await res.arrayBuffer()));
  fuentes.add(id);
}
const fuenteDe = (o) => (o && o.deco && o.deco.tipo === "texto" ? o.deco.fuente || "archivo_black" : null);
const STL_PATH = "/tmp/inserto_propio.stl";
const SVG_PATH = "/tmp/deco.svg";

async function init() {
  const t0 = performance.now();
  py = await loadPyodide({ indexURL: "./vendor/pyodide/" });
  const manifest = await (await fetch("./py/manifest.json", { cache: "no-cache" })).json();
  py.FS.mkdirTree("/eden/colecciones");
  const need = ["eden_core.py", "eden_surface.py", "eden_floor.py", "eden_font.py", "mate_core.py", "mate_web.py",
    "mate_deco.py", "mate_fuentes.py"];
  version = manifest.version;
  py.FS.mkdirTree("/eden/fuentes");
  for (const f of manifest.files.filter((x) => need.includes(x))) {
    const txt = await (await fetch("./py/" + f + "?v=" + manifest.version)).text();
    py.FS.writeFile("/eden/" + f, txt);
  }
  py.runPython("import sys; sys.path.insert(0, '/eden'); import mate_web");
  api = py.pyimport("mate_web");
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

function withPath(opts) {
  if (!opts) return opts;
  let o = opts.inserto === "propio" ? { ...opts, stl_path: STL_PATH } : opts;
  if (o.deco && o.deco.tipo === "svg") o = { ...o, deco: { ...o.deco, svg_path: SVG_PATH } };
  return o;
}

function build(opts) {
  const res = api.build(py.toPy(withPath(opts)));
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
  const o = py.toPy(withPath(opts));
  const r = kind === "3mf" ? api.export_3mf(o) : api.export_stl(o, pieza || "MATE");
  try {
    return { name: r.get(0), data: bytesOf(r.get(1)) };
  } finally {
    r.destroy();
  }
}

const ready = init();

self.onmessage = async (ev) => {
  const { id, type, opts, data, pieza, text } = ev.data;
  const fuenteId = ev.data.fuente;
  try {
    const boot = await ready;
    if (type === "init") {
      self.postMessage({ id, ok: true, result: boot });
    } else if (type === "build") {
      await fuente(fuenteDe(opts));
      const r = build(opts);
      self.postMessage({ id, ok: true, result: r }, r.parts.flatMap((p) => [p.positions, p.indices]));
    } else if (type === "3mf" || type === "stl") {
      await fuente(fuenteDe(opts));
      const r = exportFile(type, opts, pieza);
      self.postMessage({ id, ok: true, result: r }, [r.data]);
    } else if (type === "svg") {
      py.FS.writeFile(SVG_PATH, new Uint8Array(data));
      self.postMessage({ id, ok: true, result: { ok: true } });
    } else if (type === "texto") {
      await fuente(fuenteId || "archivo_black");
      const r = api.check_texto(text || "", fuenteId || "archivo_black");
      const out = r.toJs({ dict_converter: Object.fromEntries });
      r.destroy();
      self.postMessage({ id, ok: true, result: out });
    } else if (type === "marca") {
      const r = api.check_marca(text || "");
      const out = r.toJs({ dict_converter: Object.fromEntries });
      r.destroy();
      self.postMessage({ id, ok: true, result: out });
    } else if (type === "upload") {
      py.FS.writeFile(STL_PATH, new Uint8Array(data));
      const r = api.analizar_stl(STL_PATH);
      const out = r.toJs({ dict_converter: Object.fromEntries });
      r.destroy();
      self.postMessage({ id, ok: true, result: out });
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
