// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// El motor (Pyodide, ~13 MB) arranca desde el <head> de cada generador, con un script
// mínimo, sin esperar a que bajen y se ejecuten three.js y el resto de los módulos (eso
// demoraba ~2,5 s el arranque). Acá la página toma ese worker y repite los avisos de
// progreso que llegaron antes de que la pantalla de carga estuviera escuchando.
//
// En el <head> de cada generador va el script que crea window.__motor = { url, pasos, w }.
export function tomarWorker(url) {
  const m = window.__motor;
  window.__motor = null;
  const w = m && m.w && m.url === url ? m.w : new Worker(url);
  const pasos = (m && m.pasos) || [];
  if (m) m.pasos = null;                      // primero se corta el registro: si no, se repetiría solo
  // los que escuchan se enganchan en esta misma vuelta; después se reproducen los avisos
  setTimeout(() => {
    for (const paso of pasos) w.dispatchEvent(new MessageEvent("message", { data: { type: "progreso", paso } }));
  }, 0);
  return w;
}
