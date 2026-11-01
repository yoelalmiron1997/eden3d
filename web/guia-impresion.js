// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// PDF Premium con las consideraciones de impresión de cada motor (mate, sopa, topper):
// el render de la pieza, sus datos y cómo imprimirla, para tenerla a mano o mandarla al
// cliente. (Las macetas tienen su propia guía: guia.js.)
import { loadJsPDF } from "./guia.js";

const LIMA = [61, 95, 0];
const GRIS = [70, 82, 79];
const TINTA = [13, 19, 20];
const clean = (t) => String(t ?? "").replace(/[≈]/g, "aprox.").replace(/[→]/g, "->").replace(/[“”]/g, '"')
  .replace(/[‘’]/g, "'").replace(/[×]/g, "x").replace(/[^\x00-\xFF–—…•€]/g, "");
const n = (v, d = 1) => (+v).toFixed(d).replace(".", ",");

// ------------------------------------------------------------------ contenido por motor
const MOTORES = {
  mate: (s) => ({
    titulo: "Mate con hueco",
    datos: [["Modelo", s.nombre], ["Hueco para", (s.insertos || []).join(" + ")],
      ["Medidas", `${Math.round(s.diam_max_mm)} x ${Math.round(s.altura_mm)} mm · boca ${Math.round(s.diam_boca_mm)} mm`],
      ["Pared mínima / fondo", `${n(s.pared_mm)} mm / ${n(s.fondo_mm)} mm`],
      ["Hueco", `Ø ${Math.round(s.hueco_diam_mm)} x ${Math.round(s.hueco_prof_mm)} mm`], ["Peso", `${s.peso_g} g de PLA (al 100 %)`]],
    secciones: [
      ["Preparar la impresión", [
        "Imprimilo parado, con la base apoyada en la cama: no necesita soportes.",
        "Capa de 0,2 mm, 3 perímetros y 15 a 20 % de relleno: la pared queda firme y el hueco, exacto.",
        "La holgura del hueco ya está calculada para que el inserto entre justo: no escales la pieza en el laminador.",
        "Si el modelo tiene relieve o texto, imprimilo a 0,16 mm para que se lea mejor.",
      ]],
      ["Uso", [
        "El agua caliente va dentro del inserto, no en contacto con la pieza impresa.",
        "El PLA se ablanda cerca de los 55 °C: para más resistencia al calor imprimilo en PETG.",
        "Lavalo a mano, sin lavavajillas ni microondas.",
      ]],
    ],
  }),
  sopa: (s) => ({
    titulo: "Sopa de letras 3D",
    datos: [["Grilla", `${s.filas} x ${s.cols} · ${s.palabras} palabras`],
      ["Tablero", `${Math.round(s.tablero_mm[0])} x ${Math.round(s.tablero_mm[1])} mm`],
      ["Piezas", `${s.piezas} (${s.piezas_x} x ${s.piezas_y}) · ${s.lenguetas} encastres`],
      ["Letra", `${n(s.letra_mm)} mm · celda ${n(s.celda_mm, 0)} mm`],
      ["Cambio de color", `a ${n(s.cambio_color_mm)} mm`], ["Peso", `${s.peso_g} g de PLA (al 100 %)`]],
    secciones: [
      ["Preparar la impresión", [
        "Imprimí cada pieza acostada, con las letras para arriba: no hace falta soporte.",
        `Para las letras en otro color, pausá la impresión y cambiá el filamento a los ${n(s.cambio_color_mm)} mm (con AMS asigná un filamento a las letras).`,
        "Capa de 0,2 mm (0,16 mm si la letra es chica) y 2 a 3 perímetros: las letras salen nítidas.",
        "No escales las piezas: la holgura de los encastres ya está calculada.",
      ]],
      ["Armado", [
        "Encastrá las piezas de a una, desde una esquina, sin forzar.",
        "Si un encastre queda duro, lijá apenas el borde de la lengüeta.",
        s.bloques ? "Los bloques para marcar son todos iguales: van uno por letra encontrada." : "Usá la placa con la lista de palabras para jugar.",
      ]],
    ],
  }),
  chapita: (s) => ({
    titulo: "Chapita para collar",
    datos: [["Nombre", [s.nombre, s.linea2].filter(Boolean).join(" / ")],
      ["Forma", s.forma], ["Medidas", `${Math.round(s.medidas_mm[0])} x ${Math.round(s.medidas_mm[1])} x ${n(s.medidas_mm[2])} mm`],
      ["Letras", `${s.texto === "grabado" ? "grabadas" : "en relieve"} ${n(s.relieve_mm)} mm · ${n(s.letra_mm)} mm de alto`],
      ["Agujero", `Ø ${n(s.agujero_mm)} mm`],
      ["Colores", s.cambio_mm ? `dos alturas: cambio de filamento a los ${n(s.cambio_mm)} mm`
        : (s.capa_color_mm ? `misma altura: letras en las últimas ${n(s.capa_color_mm)} mm (AMS)` : "un color")]],
    secciones: [
      ["Preparar la impresión", [
        "Imprimila acostada, tal como sale el archivo: no necesita soportes.",
        "Capa de 0,16 a 0,2 mm y 100 % de relleno: queda dura y no se quiebra con el uso.",
        s.cambio_mm ? `Dos colores en cualquier impresora: pausá en la capa de los ${n(s.cambio_mm)} mm y cambiá el filamento.`
          : (s.capa_color_mm ? "Dos colores con AMS: asigná un filamento a la placa y otro a las letras (son partes del mismo objeto)."
            : "Un color: elegí uno que se vea bien sobre el pelo de tu mascota."),
        "PETG o TPU aguantan mejor el agua, el sol y los mordiscos que el PLA.",
      ]],
      ["Uso", [
        "Pasá una argollita de metal por el agujero y colgala del collar.",
        "Revisala cada tanto: si se gasta o se agrieta, imprimí una nueva.",
        "Si pusiste el teléfono, chequeá que se lea bien antes de colgarla.",
      ]],
    ],
  }),
  topper: (s) => ({
    titulo: "Topper para tortas",
    datos: [["Texto", (s.lineas || []).map((l) => l.texto).join(" / ")],
      ["Medidas", `${Math.round(s.medidas_mm[0])} x ${Math.round(s.medidas_mm[1])} x ${n(s.medidas_mm[2])} mm`],
      ["Colores", s.estilo === "doble" ? `dos alturas: cambio de filamento a los ${n(s.cambio_mm)} mm`
        : (s.estilo === "ams" ? `misma altura: letras en las últimas ${n(s.capa_color_mm)} mm (AMS)` : "un color")],
      ["Una sola pieza", s.puentes ? `sí · ${s.puentes} puente${s.puentes === 1 ? "" : "s"}` : "sí"],
      ...(s.numero ? [["Número", `${s.numero.numero} · ${Math.round(s.numero.medidas_mm[0])} x ${Math.round(s.numero.medidas_mm[1])} mm`]] : [])],
    secciones: [
      ["Preparar la impresión", [
        "Imprimilo acostado, tal como sale el archivo: no necesita soportes.",
        "Capa de 0,2 mm y 100 % de relleno (o 4 perímetros): los palitos quedan firmes para clavarlo.",
        s.estilo === "doble" ? `Dos colores en cualquier impresora: pausá en la capa de los ${n(s.cambio_mm)} mm y cambiá el filamento.`
          : (s.estilo === "ams" ? "Dos colores con AMS: asigná un filamento a la base y otro a las letras (son partes del mismo objeto)."
            : "Un color: elegí uno que contraste con la cobertura de la torta."),
        "Usá una buena adherencia en la primera capa: es una pieza fina y larga.",
      ]],
      ["En la torta", [
        "El PLA no es apto para estar en contacto con alimentos: cubrí los palitos con film o papel aluminio antes de clavarlo.",
        "Clavalo justo antes de servir y sacalo antes de cortar la torta.",
        "Para limpiarlo, agua tibia (no caliente) y jabón; nada de lavavajillas.",
      ]],
    ],
  }),
};

export async function pdfConsideraciones(motor, summary, { foto, numero } = {}) {
  const jsPDF = await loadJsPDF();
  const s = { ...summary, numero };
  const C = MOTORES[motor](s);
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  const W = 210, M = 16, CW = W - 2 * M;
  let y = 0, page = 1;
  const pie = () => {
    doc.setFont("helvetica", "normal"); doc.setFontSize(8); doc.setTextColor(...GRIS);
    doc.text(clean(`TecnoBear · ${summary.sku} · © 2026 TecnoBear — Yoel Almirón. Uso personal y para tus clientes.`), M, 290);
    doc.text(String(page), W - M, 290, { align: "right" });
  };
  const necesita = (h) => { if (y + h > 280) { pie(); doc.addPage(); page++; y = 18; } };
  // encabezado
  doc.setFillColor(9, 14, 15); doc.rect(0, 0, W, 30, "F");
  doc.setFillColor(197, 240, 91); doc.rect(0, 30, W, 1.2, "F");
  doc.setFont("helvetica", "bold"); doc.setFontSize(19); doc.setTextColor(246, 248, 246);
  doc.text(clean(C.titulo.toUpperCase()), M, 15);
  doc.setFont("helvetica", "normal"); doc.setFontSize(10); doc.setTextColor(197, 240, 91);
  doc.text(clean(`Consideraciones de impresión · ${summary.sku}`), M, 22.5);
  y = 40;
  if (foto) {
    const iw = CW, ih = CW * 0.62;
    doc.addImage(foto, "JPEG", M, y, iw, ih);
    doc.setDrawColor(52, 67, 70); doc.rect(M, y, iw, ih);
    y += ih + 8;
  }
  const h2 = (t) => {
    necesita(14);
    doc.setFont("helvetica", "bold"); doc.setFontSize(12.5); doc.setTextColor(...LIMA);
    doc.text(clean(t.toUpperCase()), M, y);
    doc.setDrawColor(181, 193, 190); doc.line(M, y + 1.8, W - M, y + 1.8);
    y += 8;
  };
  h2("La pieza");
  for (const [k, v] of C.datos) {
    necesita(6);
    doc.setFont("helvetica", "bold"); doc.setFontSize(10); doc.setTextColor(...TINTA);
    doc.text(clean(k), M, y);
    doc.setFont("helvetica", "normal");
    const lineas = doc.splitTextToSize(clean(v), CW - 48);
    lineas.forEach((ln) => { doc.text(ln, M + 48, y); y += 4.6; });
    y += 1;
  }
  y += 3;
  for (const [titulo, items] of C.secciones) {
    h2(titulo);
    for (const t of items) {
      const lineas = doc.splitTextToSize(clean(t), CW - 7);
      necesita(lineas.length * 4.6 + 2);
      doc.setFillColor(...LIMA); doc.rect(M + 0.5, y - 2.6, 2.2, 2.2, "F");
      doc.setFont("helvetica", "normal"); doc.setFontSize(10); doc.setTextColor(...TINTA);
      lineas.forEach((ln) => { doc.text(ln, M + 7, y); y += 4.6; });
      y += 1.6;
    }
    y += 3;
  }
  pie();
  return doc;
}
