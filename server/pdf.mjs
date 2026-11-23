// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Arma un PDF con el mismo código que antes corría en el navegador (web/guia-impresion.js
// y web/guia.js), con jsPDF en Node. Lee el pedido (JSON) por stdin y escribe el PDF.
//   echo '{"tipo":"consideraciones","herramienta":"chapita","summary":{...}}' | node pdf.mjs > x.pdf
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const { jsPDF } = require("jspdf");
globalThis.window = globalThis;            // guia.js busca window.jspdf
globalThis.jspdf = { jsPDF };

const WEB = process.env.EDEN3D_WEB || path.join(path.dirname(new URL(import.meta.url).pathname), "..", "web");
const mod = (f) => import(pathToFileURL(path.join(WEB, f)).href);

let entrada = "";
for await (const c of process.stdin) entrada += c;
const p = JSON.parse(entrada);
let doc;
if (p.tipo === "guia") {
  const { makeGuide } = await mod("guia.js");
  doc = await makeGuide(p.datos);
} else {
  const { pdfConsideraciones } = await mod("guia-impresion.js");
  doc = await pdfConsideraciones(p.herramienta, p.summary, { foto: p.foto || undefined, numero: p.numero || undefined });
}
process.stdout.write(Buffer.from(doc.output("arraybuffer")));
