// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Ficha de cuidados de las plantas elegidas.
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const AUTO = {
  recomendado: ["good", "Ideal con autorriego"],
  "con-cuidado": ["warn", "Autorriego con cuidado"],
  "no-recomendado": ["bad", "Sin autorriego"],
};

export function fillMl(text, A) {
  const min = A && A.water_min_wet_ml !== undefined ? Math.round(A.water_min_wet_ml) : null;
  const max = A && A.water_reservoir_ml !== undefined ? Math.round(A.water_reservoir_ml) : null;
  return String(text)
    .replaceAll("{min_ml}", min !== null ? String(min) : "una pequeña cantidad de")
    .replaceAll("{max_ml}", max !== null ? String(max) : "el plato lleno");
}

export function renderCare(f, A, modeIsSelfWatering) {
  const [cls, lab] = AUTO[f.autorriego.nivel] || ["", f.autorriego.nivel];
  const pet = f.mascotas.toxica
    ? '<span class="tag bad">Tóxica para mascotas</span>' : '<span class="tag good">No tóxica para mascotas</span>';
  const signs = f.senales.map((s) => `<tr><td>${esc(s.sintoma)}</td><td>${esc(s.causa)}</td><td>${esc(s.solucion)}</td></tr>`).join("");
  const autoTxt = modeIsSelfWatering
    ? esc(fillMl(f.autorriego.consejo, A))
    : "Esta maceta no tiene autorriego: regá desde arriba y vaciá el agua que drene.";
  return `
  <div class="care-title" data-testid="ficha-${esc(f.id)}">
    <h3>${esc(f.nombre)}</h3><span class="sci">${esc(f.cientifico)}</span>
  </div>
  <div class="tags">
    <span class="tag">${esc(f.tipo)}</span><span class="tag">${esc(f.dificultad)}</span>
    <span class="tag ${cls}">${lab}</span>${pet}
  </div>
  <p>${esc(f.resumen)}</p>
  <div class="care-grid">
    <section class="auto" data-testid="ficha-autorriego"><h4>Autorriego</h4><p>${autoTxt}</p></section>
    <section><h4>Luz</h4><p>${esc(f.luz)}</p></section>
    <section><h4>Riego</h4>
      <p><b>Verano:</b> ${esc(f.riego.primavera_verano)}</p>
      <p><b>Invierno:</b> ${esc(f.riego.otono_invierno)}</p></section>
    <section><h4>Mascotas</h4><p>${esc(f.mascotas.detalle)}</p></section>
  </div>
  <details class="care-more" data-testid="ficha-mas">
    <summary>Más cuidados</summary>
    <div class="care-grid">
      <section><h4>Cómo regar</h4><p>${esc(f.riego.como)}</p></section>
      <section><h4>Sustrato</h4><p>${esc(f.sustrato)}</p></section>
      <section><h4>Temperatura</h4><p>${f.temperatura.min} a ${f.temperatura.max} °C. ${esc(f.temperatura.nota)}</p></section>
      <section><h4>Humedad</h4><p>${esc(f.humedad)}</p></section>
      <section><h4>Fertilizante</h4><p>${esc(f.fertilizante)}</p></section>
      <section><h4>Trasplante</h4><p>${esc(f.trasplante)}</p></section>
      <section><h4>Reproducción</h4><p>${esc(f.propagacion)}</p></section>
      <section><h4>Plagas</h4><p>${esc(f.plagas)}</p></section>
    </div>
    <table class="signs" data-testid="ficha-senales">
      <thead><tr><th>Si ves…</th><th>Causa</th><th>Qué hacer</th></tr></thead>
      <tbody>${signs}</tbody>
    </table>
  </details>`;
}

export function renderCompat(list) {
  return list.map((c) => `<li class="${esc(c.nivel)}">${esc(c.texto)}</li>`).join("");
}
