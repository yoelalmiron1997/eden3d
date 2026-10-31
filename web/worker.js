// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Web Worker: carga Pyodide (Python en WebAssembly) y el motor Eden3D, y
// responde pedidos sin congelar la página.
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
  for (const f of manifest.files) {
    const txt = await (await fetch("./py/" + f + "?v=" + manifest.version)).text();
    py.FS.writeFile("/eden/" + f, txt);
  }
  py.runPython("import sys; sys.path.insert(0, '/eden'); import eden_web");
  api = py.pyimport("eden_web");
  const info = api.info().toJs({ dict_converter: Object.fromEntries });
  return { info, seconds: (performance.now() - t0) / 1000, version: manifest.version };
}

function bytesOf(proxy) {
  // bytes de Python -> ArrayBuffer (copia), sin depender de conversiones implícitas
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
      parts.push({
        name: p.get("name"),
        positions: bytesOf(p.get("positions")),
        indices: bytesOf(p.get("indices")),
      });
      p.destroy();
    }
    pl.destroy();
    return { summary, parts };
  } finally {
    res.destroy();
  }
}

function plants(opts, ids, decor, cobertura) {
  const res = api.plants(py.toPy(opts), py.toPy(ids), decor, cobertura || null);
  try {
    const cp = res.get("compat");
    const compat = cp.toJs({ dict_converter: Object.fromEntries });
    cp.destroy();
    const parts = [];
    const pl = res.get("parts");
    for (let i = 0; i < pl.length; i++) {
      const p = pl.get(i);
      const base = p.get("base");
      parts.push({ name: p.get("name"), positions: bytesOf(p.get("positions")), indices: bytesOf(p.get("indices")),
        planta: p.get("planta"), base: base.toJs(), flex: p.get("flex") });
      base.destroy();
      p.destroy();
    }
    pl.destroy();
    const ids = res.get("ids");
    const idsJs = ids.toJs();
    ids.destroy();
    return { parts, compat, ids: idsJs, cobertura: res.get("cobertura") };
  } finally {
    res.destroy();
  }
}

function exportFile(kind, opts, part) {
  const r = kind === "3mf" ? api.export_3mf(py.toPy(opts)) : api.export_stl(py.toPy(opts), part);
  try {
    return { name: r.get(0), data: bytesOf(r.get(1)) };
  } finally {
    r.destroy();
  }
}

const ready = init();

self.onmessage = async (ev) => {
  const { id, type, opts, part, ids, decor, cobertura, text } = ev.data;
  try {
    const boot = await ready;
    if (type === "init") {
      self.postMessage({ id, ok: true, result: boot });
    } else if (type === "build") {
      const r = build(opts);
      self.postMessage({ id, ok: true, result: r },
        r.parts.flatMap((p) => [p.positions, p.indices]));
    } else if (type === "plants") {
      const r = plants(opts, ids || [], decor !== false, cobertura);
      self.postMessage({ id, ok: true, result: r }, r.parts.flatMap((p) => [p.positions, p.indices]));
    } else if (type === "3mf" || type === "stl") {
      const r = exportFile(type, opts, part);
      self.postMessage({ id, ok: true, result: r }, [r.data]);
    } else if (type === "brand") {
      const r = api.check_brand(text || "");
      const out = r.toJs({ dict_converter: Object.fromEntries });
      r.destroy();
      self.postMessage({ id, ok: true, result: out });
    } else if (type === "selftest") {
      self.postMessage({ id, ok: true, result: JSON.parse(api.selftest_json()) });
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
