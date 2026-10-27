// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Guía de uso en PDF: la maceta elegida, cómo usar el autorriego con los ml reales,
// los cuidados de cada planta, la tierra y cómo cuidar la pieza de PLA.
import { fillMl } from "./care.js";

const VERDE = [47, 79, 46];
const GRIS = [109, 106, 99];
const TINTA = [43, 42, 39];

let jspdfLoading = null;
export function loadJsPDF() {
  if (window.jspdf) return Promise.resolve(window.jspdf.jsPDF);
  jspdfLoading = jspdfLoading || new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "vendor/jspdf/jspdf.umd.min.js";
    s.onload = () => res(window.jspdf.jsPDF);
    s.onerror = () => rej(new Error("no se pudo cargar el generador de PDF"));
    document.head.appendChild(s);
  });
  return jspdfLoading;
}

// La fuente estándar del PDF (Helvetica) usa WinAnsi: se reemplaza lo que no entra.
const clean = (t) => String(t ?? "").replace(/[≈]/g, "aprox.").replace(/[→]/g, "->").replace(/[“”]/g, '"')
  .replace(/[‘’]/g, "'").replace(/[^\x00-\xFF–—…•€]/g, "");

export async function makeGuide({ summary, plantas, compat, cobertura, selfWatering, photo, layers, fecha }) {
  const jsPDF = await loadJsPDF();
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: false });
  const W = 210, M = 16, CW = W - 2 * M;
  const A = summary.assembly || {};
  let y = 0;
  let page = 1;

  const footer = () => {
    doc.setFontSize(8);
    doc.setTextColor(...GRIS);
    doc.text(clean(`Eden3D · ${summary.sku} · © 2026 Eden3D — Yoel Almirón. Uso personal, no comercial.`), M, 290);
    doc.text(String(page), W - M, 290, { align: "right" });
  };
  const newPage = () => {
    // el pie cambia la letra: se guarda y se restaura la que estaba en uso
    const f = doc.getFont(), size = doc.getFontSize(), color = doc.getTextColor();
    footer(); doc.addPage(); page++; y = 18;
    doc.setFont(f.fontName, f.fontStyle); doc.setFontSize(size); doc.setTextColor(color);
  };
  const need = (h) => { if (y + h > 280) newPage(); };
  const h2 = (t) => {
    need(14);
    y += 4;
    doc.setFont("helvetica", "bold"); doc.setFontSize(13); doc.setTextColor(...VERDE);
    doc.text(clean(t), M, y);
    doc.setDrawColor(226, 220, 207); doc.line(M, y + 1.8, W - M, y + 1.8);
    y += 7;
  };
  const para = (t, opt = {}) => {
    const size = opt.size || 10;
    doc.setFont("helvetica", opt.bold ? "bold" : "normal"); doc.setFontSize(size); doc.setTextColor(...(opt.color || TINTA));
    const x = M + (opt.indent || 0);
    const lines = doc.splitTextToSize(clean(t), CW - (opt.indent || 0));
    for (const ln of lines) { need(size * 0.45); doc.text(ln, x, y); y += size * 0.45; }
    y += opt.after ?? 1.6;
  };
  const kv = (k, v, indent = 0) => {
    doc.setFont("helvetica", "bold"); doc.setFontSize(10); doc.setTextColor(...TINTA);
    const kw = doc.getTextWidth(clean(k) + " ");
    need(5);
    doc.text(clean(k), M + indent, y);
    doc.setFont("helvetica", "normal");
    const lines = doc.splitTextToSize(clean(v), CW - indent - kw);
    lines.forEach((ln, i) => { if (i) { need(4.5); } doc.text(ln, M + indent + kw, y); y += 4.5; });
    y += 0.8;
  };
  const steps = (list) => list.forEach((t, i) => {
    need(6);
    doc.setFillColor(...VERDE); doc.circle(M + 2.6, y - 1.3, 2.6, "F");
    doc.setFont("helvetica", "bold"); doc.setFontSize(8.5); doc.setTextColor(255, 255, 255);
    doc.text(String(i + 1), M + 2.6, y - 0.3, { align: "center" });
    para(t, { indent: 8, after: 1.2 });
  });

  // ---------------------------------------------------------------- portada
  doc.setFillColor(...VERDE);
  doc.rect(0, 0, W, 30, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold"); doc.setFontSize(20);
  doc.text("Eden3D · Guía de uso", M, 14);
  doc.setFont("helvetica", "normal"); doc.setFontSize(10);
  doc.text(clean(`${summary.sku} · ${fecha}`), M, 22);
  y = 38;
  const imgW = 78, imgH = 97.5;
  if (photo) {
    doc.addImage(photo, "JPEG", M, y, imgW, imgH);
    doc.setDrawColor(226, 220, 207); doc.rect(M, y, imgW, imgH);
  }
  // datos al lado de la foto
  const x0 = M + imgW + 8;
  let yy = y + 4;
  const fact = (k, v) => {
    if (v === undefined || v === null || v === "") return;
    doc.setFont("helvetica", "normal"); doc.setFontSize(8.5); doc.setTextColor(...GRIS);
    doc.text(clean(k), x0, yy);
    doc.setFont("helvetica", "bold"); doc.setFontSize(11); doc.setTextColor(...TINTA);
    doc.text(doc.splitTextToSize(clean(v), W - M - x0), x0, yy + 5);
    yy += 12;
  };
  const r = (v) => (v === undefined || v === null ? null : Math.round(v));
  fact("Medidas", summary.bbox_mm ? summary.bbox_mm.map((v) => Math.round(v)).join(" × ") + " mm" : null);
  fact("Tierra que entra", r(summary.soil_ml) !== null ? `${r(summary.soil_ml)} ml` : null);
  if (selfWatering && A.water_reservoir_ml !== undefined) {
    fact("Agua mínima para mojar la tierra", `${r(A.water_min_wet_ml)} ml`);
    fact("Plato lleno", `${r(A.water_reservoir_ml)} ml`);
    fact("Rosca", A.thread_turns !== undefined ? `${A.thread_turns} vueltas` : null);
  }
  fact("Agujeros de drenaje", summary.drain_holes);
  fact("Material", `PLA · maceta ${r(summary.pot_g) ?? "-"} g`);
  if (cobertura) fact("Tierra elegida", cobertura.nombre);
  if (plantas.length) fact(plantas.length > 1 ? "Plantas" : "Planta", plantas.map((p) => p.nombre).join(", "));
  y = Math.max(y + imgH, yy) + 4;

  // ---------------------------------------------------------------- autorriego
  if (selfWatering) {
    h2("Cómo usar el autorriego");
    steps([
      "Poné un poco de sustrato en la maceta y plantá. Dejá 1 a 2 cm libres hasta el borde.",
      `Enroscá la maceta en el plato a mano, sin forzar${A.thread_turns ? ` (${A.thread_turns} vueltas)` : ""}. La base queda casi apoyada y el agua del plato llega a la tierra.`,
      `Cargá el agua por el costado: con ${r(A.water_min_wet_ml)} ml ya se moja la tierra; el plato lleno lleva ${r(A.water_reservoir_ml)} ml.`,
      "Volvé a cargar cuando el plato esté vacío. Cada tanto regá desde arriba para lavar las sales del fertilizante.",
      "En invierno, o con plantas de riego seco (cactus y suculentas), cargá menos y dejá que el plato se vacíe entre cargas.",
    ]);
  } else {
    h2("Riego y drenaje");
    steps([
      "Regá desde arriba hasta que el agua salga por los agujeros de drenaje.",
      "Vaciá el plato a los 15 minutos: el agua estancada pudre las raíces.",
      "Antes de volver a regar, tocá la tierra: si está húmeda a 2 cm, esperá.",
    ]);
  }

  // ---------------------------------------------------------------- plantas
  for (const f of plantas) {
    h2(`${f.nombre} (${f.cientifico})`);
    para(f.resumen, { color: GRIS });
    kv("Luz:", f.luz);
    kv("Riego en verano:", f.riego.primavera_verano);
    kv("Riego en invierno:", f.riego.otono_invierno);
    if (selfWatering) kv("Autorriego:", fillMl(f.autorriego.consejo, A));
    kv("Sustrato:", f.sustrato);
    kv("Temperatura:", `${f.temperatura.min} a ${f.temperatura.max} °C. ${f.temperatura.nota}`);
    kv("Fertilizante:", f.fertilizante);
    kv("Mascotas:", (f.mascotas.toxica ? "Tóxica. " : "") + f.mascotas.detalle);
    need(10);
    para("Señales de alerta", { bold: true, size: 10, after: 0.8 });
    for (const s of f.senales) para(`• ${s.sintoma}: ${s.causa}. ${s.solucion}`, { indent: 3, size: 9.5, after: 0.6 });
  }
  if (compat && compat.length && plantas.length > 1) {
    h2("Combinación de plantas");
    for (const c of compat) para(c.texto);
  }
  if (cobertura) {
    h2("La tierra");
    para(`${cobertura.nombre}: ${cobertura.descripcion}`);
    para("Cada 1 o 2 años renová el sustrato: se compacta y pierde nutrientes.");
  }

  // ---------------------------------------------------------------- la pieza
  h2("Cuidado de la maceta (PLA)");
  steps([
    "El PLA se ablanda con calor: no la dejes dentro de un auto al sol ni cerca de estufas u hornos (más de 50 °C).",
    "Lavala con agua tibia y jabón neutro. No uses lavavajillas ni agua hirviendo.",
    "Al exterior el sol fuerte puede decolorarla con el tiempo: mejor interior, balcón o media sombra.",
    "Enroscá y desenroscá a mano. Si la rosca se traba, sacá la tierra del filete con un cepillo.",
  ]);
  if (layers) {
    h2("Si la imprimís vos");
    para(`Maceta: ${layers.maceta} capas de 0,2 mm${layers.plato ? ` · plato: ${layers.plato} capas` : ""}. Imprimí cada pieza por separado, apoyada sobre su base, en PLA.`);
    para("Los archivos descargados son para uso personal: no se pueden vender ni compartir.", { color: GRIS });
  }
  footer();
  return doc;
}
