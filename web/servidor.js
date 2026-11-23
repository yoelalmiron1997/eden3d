// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Descargas y PDF desde el servidor (server/api.py). En el VPS la web se arma con
// EDEN3D_API=/api: los archivos para imprimir y los PDF los genera el servidor después
// de comprobar la cuenta, y el motor del navegador ya no trae el código para exportar.
// Sin servidor (GitHub Pages, tests locales) todo sigue generándose en el navegador.
import { API } from "./config.js";
import { conexion } from "./auth.js";

export const hayServidor = () => !!(API && API.url);

async function token() {
  const c = conexion();
  if (c.mock) return (window.__EDEN_AUTH_MOCK && window.__EDEN_AUTH_MOCK.token) || "";   // tests e2e (sólo localhost)
  if (!c.client) return "";
  const { data } = await c.client.auth.getSession();
  return (data && data.session && data.session.access_token) || "";
}

const b64 = (buf) => {
  const u = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  return btoa(s);
};

async function pedir(ruta, cuerpo) {
  const t = await token();
  if (!t) throw new Error("Ingresá con tu cuenta para descargar.");
  let r;
  try {
    r = await fetch(API.url.replace(/\/$/, "") + ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + t },
      body: JSON.stringify(cuerpo),
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor. Revisá tu conexión y probá de nuevo.");
  }
  if (!r.ok) {
    let msg = "El servidor no pudo generar el archivo (" + r.status + ").";
    try { const j = await r.json(); if (j.error) msg = j.error; } catch { /* sin json */ }
    throw new Error(msg);
  }
  const disp = r.headers.get("Content-Disposition") || "";
  const m = /filename\*=UTF-8''([^;]+)/.exec(disp) || /filename="([^"]+)"/.exec(disp);
  return { name: m ? decodeURIComponent(m[1]) : "archivo", data: await r.arrayBuffer(),
    pages: +(r.headers.get("X-Paginas") || 0) };
}

// archivo para imprimir: con servidor lo pide; si no, lo arma el worker de la página
// (call = la función de mensajes del worker; args = { opts, pieza, archivos? })
export async function exportar(herramienta, kind, args, call) {
  if (!hayServidor()) return call(kind, { opts: args.opts, pieza: args.pieza, part: args.pieza });
  const archivos = {};
  for (const [k, v] of Object.entries(args.archivos || {})) if (v) archivos[k] = b64(v);
  return pedir("/descargar", { herramienta, formato: kind, opts: args.opts, pieza: args.pieza || null, archivos });
}

// PDF de consideraciones de impresión (chapita, banda, mate, topper, sopa, trofeo)
export async function pdfConsideracionesArchivo(motor, summary, { foto, numero } = {}) {
  if (hayServidor()) return pedir("/pdf", { tipo: "consideraciones", herramienta: motor, summary, foto, numero: numero || null });
  const { pdfConsideraciones } = await import("./guia-impresion.js");
  const doc = await pdfConsideraciones(motor, summary, { foto, numero });
  return { name: `${summary.sku}_consideraciones.pdf`, data: doc.output("arraybuffer"), pages: doc.getNumberOfPages() };
}

// guía de uso de la maceta
export async function guiaArchivo(datos) {
  if (hayServidor()) return pedir("/pdf", { tipo: "guia", herramienta: "macetas", datos });
  const { makeGuide } = await import("./guia.js");
  const doc = await makeGuide(datos);
  return { name: `${datos.summary.sku}_guia.pdf`, data: doc.output("arraybuffer"), pages: doc.getNumberOfPages() };
}
