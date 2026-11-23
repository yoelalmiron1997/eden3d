// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Arranque común de los motores (se carga con importScripts desde cada worker).
// Los archivos de Python del generador se bajan TODOS A LA VEZ y mientras Pyodide se
// inicia (antes: de a uno y recién cuando Python estaba listo, ~0,5–1 s de más con la
// latencia de una red real). Las tipografías se bajan una sola vez aunque las pidan dos
// pedidos al mismo tiempo.
/* global loadPyodide */

self.cargarMotor = async function ({ archivos, modulo }) {
  const t0 = performance.now();
  self.postMessage({ type: "progreso", paso: 1 });
  const manifestP = fetch("./py/manifest.json", { cache: "no-cache" }).then((r) => {
    if (!r.ok) throw new Error("no se pudo bajar el motor (" + r.status + ")");
    return r.json();
  });
  const textosP = manifestP.then((m) => Promise.all(archivos.filter((f) => m.files.includes(f)).map((f) =>
    fetch("./py/" + f + "?v=" + m.version).then((r) => {
      if (!r.ok) throw new Error(`no se pudo bajar ${f} (${r.status})`);
      return r.text();
    }).then((t) => [f, t]))));
  textosP.catch(() => {});                   // el error se informa abajo, al esperarlo
  const py = await loadPyodide({ indexURL: "./vendor/pyodide/" });
  self.postMessage({ type: "progreso", paso: 2 });     // Python listo: ahora el motor
  const manifest = await manifestP;
  py.FS.mkdirTree("/eden/colecciones");
  py.FS.mkdirTree("/eden/fuentes");
  for (const [f, t] of await textosP) py.FS.writeFile("/eden/" + f, t);
  py.runPython(`import sys; sys.path.insert(0, '/eden'); import ${modulo}`);
  const api = py.pyimport(modulo);
  return { py, api, manifest, version: manifest.version, t0 };
};

// fuente(id): baja /py/fuentes/<id>.json al sistema de archivos de Python (una sola vez)
self.crearFuentes = function (estado, saltear = () => false) {
  const listas = new Map();
  return function fuente(id) {
    if (!id || saltear(id)) return Promise.resolve();
    if (!listas.has(id)) {
      const p = fetch("./py/fuentes/" + id + ".json?v=" + estado.version).then(async (res) => {
        if (!res.ok) throw new Error("No se pudo bajar la tipografía " + id);
        estado.py.FS.writeFile("/eden/fuentes/" + id + ".json", new Uint8Array(await res.arrayBuffer()));
      });
      p.catch(() => listas.delete(id));      // si falló, el próximo pedido lo reintenta
      listas.set(id, p);
    }
    return listas.get(id);
  };
};
