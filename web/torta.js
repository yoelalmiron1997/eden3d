// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Las tortas del visor del topper, apoyadas en la mesa (z = 0 es la mesa): de crema,
// chocolate, chocotorta, Oreo, pasta frola, rogel, frutillas y selva negra, con texturas
// dibujadas en el navegador (marcas de espátula, migas, capas, membrillo, merengue,
// virutas). El topper y el número entran desde arriba y se clavan; "Modo cumpleaños"
// prende las velas, tira confeti y gira la cámara.
import * as THREE from "three";

const TAU = Math.PI * 2;
const COLORES = [0xff5d8f, 0xffc93c, 0x5ad1e8, 0x8be36b, 0xb388ff, 0xff8a3d, 0xffffff];
const easeOutBack = (u) => { const c = 1.6; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
const rnd = (a, b) => a + Math.random() * (b - a);

export const TORTAS = [
  ["crema", "Crema con chorreado"], ["chocolate", "Chocolate y ganache"], ["chocotorta", "Chocotorta"],
  ["oreo", "Oreo"], ["pastafrola", "Pasta frola"], ["rogel", "Rogel"], ["frutillas", "Frutillas con crema"],
  ["selva", "Selva negra"],
];

// ------------------------------------------------------------------ texturas dibujadas
const CACHE = new Map();
function lienzo(key, w, h, dibujar) {
  if (CACHE.has(key)) return CACHE.get(key);
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  dibujar(c.getContext("2d"), w, h);
  CACHE.set(key, c);
  return c;
}
function tex(c, rx = 1, ry = 1, srgb = true) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rx, ry);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
function motas(g, w, h, n, colores, r0, r1, alfa = 1) {
  for (let i = 0; i < n; i++) {
    g.globalAlpha = alfa * rnd(0.4, 1);
    g.fillStyle = colores[(Math.random() * colores.length) | 0];
    g.beginPath();
    g.ellipse(Math.random() * w, Math.random() * h, rnd(r0, r1), rnd(r0, r1), Math.random() * TAU, 0, TAU);
    g.fill();
  }
  g.globalAlpha = 1;
}
// crema alisada con espátula: vetas horizontales suaves
const T_CREMA = (base = "#fbf6ee", veta = "#efe6d8") => lienzo("crema" + base, 512, 256, (g, w, h) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 90; i++) {
    const y = Math.random() * h;
    g.globalAlpha = rnd(0.15, 0.5);
    g.strokeStyle = Math.random() < 0.5 ? veta : "#ffffff";
    g.lineWidth = rnd(1, 4);
    g.beginPath();
    g.moveTo(0, y);
    for (let x = 0; x <= w; x += 32) g.lineTo(x, y + Math.sin(x * 0.02 + i) * 2);
    g.stroke();
  }
  g.globalAlpha = 1;
  motas(g, w, h, 400, [veta, "#ffffff"], 0.5, 1.6, 0.4);
});
// crema peinada con peine (vetas verticales), para la de frutillas
const T_PEINADA = () => lienzo("peinada", 512, 256, (g, w, h) => {
  g.fillStyle = "#fffdf8"; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 8) {
    const gr = g.createLinearGradient(x, 0, x + 8, 0);
    gr.addColorStop(0, "#efe8dc"); gr.addColorStop(0.5, "#ffffff"); gr.addColorStop(1, "#ece4d6");
    g.fillStyle = gr; g.fillRect(x, 0, 8, h);
  }
  motas(g, w, h, 300, ["#f3ece0"], 0.6, 2, 0.5);
});
// migas: Oreo (negro con blanco), cacao, virutas de chocolate
const T_MIGAS = (key, base, colores, n, r0, r1) => lienzo(key, 512, 512, (g, w, h) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  motas(g, w, h, n, colores, r0, r1);
});
const T_VIRUTAS = () => lienzo("virutas", 512, 512, (g, w, h) => {
  g.fillStyle = "#2c1810"; g.fillRect(0, 0, w, h);
  const cs = ["#4a2a18", "#5d3720", "#3a2014", "#6e4428", "#24130b"];
  for (let i = 0; i < 1400; i++) {
    const x = Math.random() * w, y = Math.random() * h, r = rnd(4, 14), a = Math.random() * TAU;
    g.strokeStyle = cs[(Math.random() * cs.length) | 0];
    g.lineWidth = rnd(2, 5);
    g.beginPath(); g.arc(x, y, r, a, a + rnd(1.2, 2.8)); g.stroke();
    g.strokeStyle = "rgba(255,220,180,0.18)"; g.lineWidth = 1;
    g.beginPath(); g.arc(x, y, r - 1, a, a + 1); g.stroke();
  }
});
// capas de costado (de abajo para arriba): [color, alto relativo, motas?]
const T_CAPAS = (key, capas, w = 256, h = 512) => lienzo(key, w, h, (g) => {
  const total = capas.reduce((s, c) => s + c[1], 0);
  let y = h;
  for (const [col, alto, mot] of capas) {
    const hh = (alto / total) * h;
    g.fillStyle = col; g.fillRect(0, y - hh, w, hh + 1);
    if (mot) {
      g.save(); g.beginPath(); g.rect(0, y - hh, w, hh); g.clip();
      motas(g, w, h, (mot * w * hh) / 400, [mot === 2 ? "#1a0e08" : "#ffffff22", "#00000033"], 0.6, 1.8);
      g.restore();
    }
    // borde irregular entre capas
    g.fillStyle = col;
    for (let x = 0; x < w; x += 6) g.fillRect(x, y - hh - rnd(0, 2), 6, 2);
    y -= hh;
  }
});
const T_MEMBRILLO = () => lienzo("membrillo", 512, 512, (g, w, h) => {
  const gr = g.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w / 1.4);
  gr.addColorStop(0, "#a8361c"); gr.addColorStop(1, "#6e1c0e");
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  motas(g, w, h, 900, ["#d8603c", "#7a1f10", "#b23a20"], 2, 9, 0.35);
});
const T_MASA = () => lienzo("masa", 256, 256, (g, w, h) => {
  g.fillStyle = "#e3ad62"; g.fillRect(0, 0, w, h);
  motas(g, w, h, 900, ["#c98a3e", "#f0c27e", "#b6762e", "#f6d49a"], 0.6, 2.4, 0.6);
});
const T_OREO = () => lienzo("oreo", 256, 256, (g, w, h) => {
  g.fillStyle = "#1d1918"; g.fillRect(0, 0, w, h);
  g.strokeStyle = "#2f2a28"; g.lineWidth = 6;
  for (const r of [118, 100]) { g.beginPath(); g.arc(w / 2, h / 2, r, 0, TAU); g.stroke(); }
  g.lineWidth = 4;
  for (let k = 0; k < 12; k++) {          // florcitas del grabado
    const a = (k / 12) * TAU, x = w / 2 + 84 * Math.cos(a), y = h / 2 + 84 * Math.sin(a);
    g.beginPath(); g.arc(x, y, 8, 0, TAU); g.stroke();
  }
  for (let k = 0; k < 4; k++) {
    g.beginPath(); g.ellipse(w / 2, h / 2, 46, 18, (k * Math.PI) / 4, 0, TAU); g.stroke();
  }
  motas(g, w, h, 300, ["#2a2524", "#141110"], 0.6, 1.6, 0.6);
});
const T_CHOCOLINA = () => lienzo("chocolina", 256, 192, (g, w, h) => {
  g.fillStyle = "#3a2316"; g.fillRect(0, 0, w, h);
  motas(g, w, h, 500, ["#4b2e1c", "#2a170d"], 0.6, 2, 0.7);
  g.fillStyle = "#1e110a";
  for (let y = 26; y < h - 10; y += 34) for (let x = 26; x < w - 10; x += 34) { g.beginPath(); g.arc(x, y, 3.2, 0, TAU); g.fill(); }
});
const T_FRUTILLA = () => lienzo("frutilla", 256, 256, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h);
  gr.addColorStop(0, "#e2283c"); gr.addColorStop(1, "#b0101f");
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  for (let y = 10; y < h; y += 22) for (let x = (y / 22) % 2 ? 6 : 17; x < w; x += 22) {
    g.fillStyle = "#f6d36b"; g.beginPath(); g.ellipse(x, y, 1.6, 2.6, 0, 0, TAU); g.fill();
    g.fillStyle = "#8c0a16"; g.beginPath(); g.arc(x, y + 3, 2.6, 0, Math.PI); g.fill();
  }
});

// ------------------------------------------------------------------ geometrías
// copo de crema con estrías (pico de manga): lathe + ondas, con la punta torcida
function rosetaGeo(h = 1, puntas = 8) {
  const pts = [];
  for (let i = 0; i <= 14; i++) {
    const t = i / 14;
    pts.push(new THREE.Vector2(Math.max(0.001, Math.pow(1 - t, 0.8) * (1 - 0.15 * Math.sin(t * Math.PI))), t * h));
  }
  const g = new THREE.LatheGeometry(pts, 48);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const a = Math.atan2(z, x), r = Math.hypot(x, z);
    const k = 1 + 0.16 * Math.cos(puntas * (a + y * 2.2));
    p.setXYZ(i, Math.cos(a) * r * k, y, Math.sin(a) * r * k);
  }
  g.rotateX(Math.PI / 2);
  g.computeVertexNormals();
  return g;
}
// pico de merengue (como un beso), con la punta doblada
function picoGeo() {
  const pts = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16;
    // panza redonda abajo y punta finita arriba (merengue de manga)
    pts.push(new THREE.Vector2(Math.max(0.001, Math.pow(1 - t, 1.25) * (1 + 0.25 * Math.sin(t * Math.PI * 0.9))), t * 1.25));
  }
  const g = new THREE.LatheGeometry(pts, 36);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const a = Math.atan2(z, x), r = Math.hypot(x, z), k = 1 + 0.1 * Math.cos(6 * (a + y * 1.5));
    p.setXYZ(i, Math.cos(a) * r * k + Math.pow(y / 1.25, 3) * 0.3, y, Math.sin(a) * r * k);
  }
  g.rotateX(Math.PI / 2);
  g.computeVertexNormals();
  return g;
}
function frutillaGeo() {
  const pts = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16;                 // 0 la punta, 1 arriba
    pts.push(new THREE.Vector2(Math.max(0.001, Math.sin(t * Math.PI * 0.62) * (0.7 + 0.3 * t)), t * 1.5));
  }
  pts.push(new THREE.Vector2(0.001, 1.5));
  const g = new THREE.LatheGeometry(pts, 24);
  g.rotateX(Math.PI / 2);
  g.computeVertexNormals();
  return g;
}

export class Torta {
  constructor(viewer) {
    this.v = viewer;
    this.grupo = new THREE.Group();
    this.grupo.name = "TORTA";
    this.fiesta = false;
    this.tipo = "crema";
    this.clavadas = [];              // piezas clavadas (topper, número) y su entrada animada
    this.t = 0;
    this.stats = { frames: 0, confeti: 0, apoyados: 0, rafagas: 0, llamas: 0 };
    const S = (o) => new THREE.MeshStandardMaterial({ roughness: 0.75, metalness: 0, ...o });
    const P = (o) => new THREE.MeshPhysicalMaterial({ roughness: 0.25, metalness: 0, clearcoat: 0.8, clearcoatRoughness: 0.2, ...o });
    this.S = S; this.P = P;
    this.mats = {
      plato: S({ color: 0xf3f0ea, roughness: 0.22, metalness: 0.12 }),
      tabla: S({ color: 0xd9d4cc, roughness: 0.35, metalness: 0.35 }),
      vela: S({ color: 0x8fd3f4, roughness: 0.5 }),
      vela2: S({ color: 0xf6a5c0, roughness: 0.5 }),
      mecha: S({ color: 0x2b2b2b, roughness: 0.9 }),
      llama: new THREE.MeshBasicMaterial({ color: 0xffb02e, transparent: true, opacity: 0.95 }),
      nucleo: new THREE.MeshBasicMaterial({ color: 0xfff6c8 }),
      grana: S({ roughness: 0.5 }),
      confeti: S({ roughness: 0.55, metalness: 0.1, side: THREE.DoubleSide }),
    };
    viewer.tickers = viewer.tickers || [];
    viewer.tickers.push((dt) => this.tick(dt));
  }

  // ------------------------------------------------------------------ armado
  // ancho: lo que hay que clavar arriba (topper + número), en mm
  armar(ancho, tipo = this.tipo) {
    this.tipo = TORTAS.some(([k]) => k === tipo) ? tipo : "crema";
    const g = this.grupo;
    g.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    g.clear();
    const R = Math.max(88, ancho * 0.58 + 12);       // un topper de 14 cm en una torta de ~20 cm
    this.R = R;
    this.plato = 7;
    this.forma = { rect: false, R, a: R, b: R, plato: R + 32 };
    this.llamas = [];
    const f = {
      crema: () => this.cremosa(R, false), chocolate: () => this.cremosa(R, true),
      chocotorta: () => this.chocotorta(R), oreo: () => this.oreo(R), pastafrola: () => this.pastafrola(R),
      rogel: () => this.rogel(R), frutillas: () => this.frutillas(R), selva: () => this.selva(R),
    }[this.tipo];
    f();
    this.velas();
    this.armarConfeti();
  }

  add(m, sombra = true) { m.castShadow = m.receiveShadow = sombra; this.grupo.add(m); return m; }

  // cilindro z-up: costado y tapa con materiales propios (la tapa con UV planas)
  cil(r, h, z, lado, tapa, seg = 128) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg, 1, !tapa), lado);
    m.rotation.x = Math.PI / 2;
    m.position.z = z + h / 2;
    this.add(m);
    if (tapa) {
      const t = new THREE.Mesh(new THREE.CircleGeometry(r, seg), tapa);
      t.position.z = z + h;
      this.add(t);
    }
    return m;
  }

  platoRedondo(R) {
    const m = this.mats;
    this.cil(R + 32, this.plato - 2, 0, m.plato, m.plato);
    const borde = new THREE.Mesh(new THREE.TorusGeometry(R + 32, 2, 10, 128), m.plato);
    borde.position.z = this.plato - 2;
    this.add(borde);
  }

  instancias(geo, mat, lista, colores) {
    const im = new THREE.InstancedMesh(geo, mat, lista.length);
    const o = new THREE.Object3D();
    const c = new THREE.Color();
    lista.forEach((L, i) => {
      o.position.set(L.x, L.y, L.z);
      o.rotation.set(L.rx || 0, L.ry || 0, L.rz || 0);
      const s = L.s || 1;
      o.scale.set(L.sx || s, L.sy || s, L.sz || s);
      o.updateMatrix();
      im.setMatrixAt(i, o.matrix);
      if (colores) im.setColorAt(i, c.set(colores(i)));
    });
    return this.add(im);
  }

  anillo(n, r, z, extra = {}) {
    return Array.from({ length: n }, (_, i) => {
      const a = (i / n) * TAU + (extra.fase || 0);
      return { x: r * Math.cos(a), y: r * Math.sin(a), z, rz: a, ...extra.f?.(i, a) };
    });
  }

  // crema con chorreado rosa y granas, o chocolate con ganache y perlitas doradas
  cremosa(R, choco) {
    const H = 78, z0 = this.plato;
    this.platoRedondo(R);
    this.arriba = z0 + H + 3;
    const crema = this.S({ map: tex(choco ? T_CREMA("#6b3f26", "#5a321d") : T_CREMA(), 3, 1),
      bumpMap: tex(T_CREMA(), 3, 1, false), bumpScale: 0.6, roughness: 0.7 });
    const cremaTapa = this.S({ map: tex(choco ? T_CREMA("#6b3f26", "#5a321d") : T_CREMA(), 1, 1), roughness: 0.7 });
    this.cil(R, H, z0, crema, null);
    this.cil(R + 1.2, 3, z0 + H, crema, cremaTapa);
    const baño = choco ? this.P({ color: 0x3a1d10, roughness: 0.18 }) : this.P({ color: 0xf29bb8, roughness: 0.3, clearcoat: 0.5 });
    // chorreado: gotas que bajan desde el borde
    for (let i = 0; i < 40; i++) {
      const a = (i / 40) * TAU + rnd(-0.04, 0.04), largo = rnd(6, 28);
      const gota = new THREE.Mesh(new THREE.CapsuleGeometry(rnd(3.2, 4.8), largo, 6, 12), baño);
      gota.rotation.x = Math.PI / 2;
      gota.position.set((R + 0.6) * Math.cos(a), (R + 0.6) * Math.sin(a), z0 + H + 1 - largo / 2);
      this.add(gota, false);
    }
    const tapa = new THREE.Mesh(new THREE.CylinderGeometry(R + 1.6, R + 1.6, 2.2, 128), baño);
    tapa.rotation.x = Math.PI / 2;
    tapa.position.z = z0 + H + 1.4;
    this.add(tapa);
    const copoMat = this.S({ color: choco ? 0x5a321d : 0xffffff, roughness: 0.6 });
    const ros = rosetaGeo(1);
    this.instancias(ros, copoMat, this.anillo(18, R - 9, this.arriba, { f: () => ({ s: 7, sz: 9 }) }));
    this.instancias(ros, this.S({ color: choco ? 0x4a2a18 : 0xffffff, roughness: 0.6 }),
      this.anillo(44, R + 2.5, z0, { f: () => ({ s: 6.5, sz: 6 }) }));
    if (choco) {
      const oro = new THREE.MeshStandardMaterial({ color: 0xe0b44c, metalness: 1, roughness: 0.22 });
      this.instancias(new THREE.SphereGeometry(1, 14, 10), oro,
        this.anillo(18, R - 9, this.arriba + 9.5, { fase: 0, f: () => ({ s: 2.6 }) }));
      this.instancias(new THREE.SphereGeometry(1, 10, 8), oro,
        Array.from({ length: 60 }, () => { const r = Math.sqrt(Math.random()) * (R - 22), a = Math.random() * TAU; return { x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba + 0.6, s: 1.3 }; }));
    } else {
      this.instancias(new THREE.CapsuleGeometry(0.9, 3.2, 3, 6), this.mats.grana,
        Array.from({ length: 280 }, () => { const r = Math.sqrt(Math.random()) * (R - 16), a = Math.random() * TAU; return { x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba + 0.8, rx: Math.PI / 2, ry: Math.random() * TAU }; }),
        (i) => COLORES[i % COLORES.length]);
    }
  }

  // chocotorta: rectangular, capas de chocolinas y crema de dulce de leche, cacao arriba
  chocotorta(R) {
    const a = Math.max(R * 1.12, 100), b = Math.max(R * 0.78, 72), H = 62, z0 = this.plato;
    this.forma = { rect: true, R, a, b, plato: 0 };
    this.arriba = z0 + H;
    // tabla
    const tabla = new THREE.Mesh(new THREE.BoxGeometry(2 * a + 50, 2 * b + 50, z0), this.mats.tabla);
    tabla.position.z = z0 / 2;
    this.add(tabla);
    this.forma.plato = Math.max(a, b) + 25;
    const capas = [];
    for (let i = 0; i < 5; i++) capas.push(["#3a2316", 1.0, 2], ["#e2c39a", 0.75, 1]);
    capas.push(["#4a2c1c", 0.35, 2]);
    const lado = this.S({ map: tex(T_CAPAS("chocotorta", capas), 4, 1), roughness: 0.85,
      bumpMap: tex(T_CAPAS("chocotorta", capas), 4, 1, false), bumpScale: 0.8 });
    for (const [ang, w, d] of [[0, 2 * a, b], [Math.PI / 2, 2 * b, a], [Math.PI, 2 * a, b], [-Math.PI / 2, 2 * b, a]]) {
      const p = new THREE.Mesh(new THREE.PlaneGeometry(w, H), lado);
      p.rotation.order = "ZXY";
      p.rotation.set(Math.PI / 2, 0, ang);
      p.position.set(Math.sin(ang) * d, -Math.cos(ang) * d, z0 + H / 2);
      this.add(p);
    }
    const cacao = tex(T_MIGAS("cacao", "#4a2b1b", ["#5c3823", "#3a2014", "#6a4129", "#2d170c"], 9000, 0.5, 2.2), 2, 1.4);
    const top = new THREE.Mesh(new THREE.PlaneGeometry(2 * a, 2 * b), this.S({ map: cacao, bumpMap: cacao, bumpScale: 1.2, roughness: 0.95 }));
    top.position.z = this.arriba;
    this.add(top);
    // copos de dulce de leche en el borde y chocolinas apoyadas
    const ros = rosetaGeo(1);
    const lista = [];
    for (let x = -a + 10; x <= a - 9; x += 19) lista.push({ x, y: -b + 9, z: this.arriba, s: 6.5, sz: 8 }, { x, y: b - 9, z: this.arriba, s: 6.5, sz: 8 });
    this.instancias(ros, this.S({ color: 0xd8a868, roughness: 0.55 }), lista);
    const chocolina = this.S({ map: tex(T_CHOCOLINA(), 1, 1), bumpMap: tex(T_CHOCOLINA(), 1, 1, false), bumpScale: 1.2, roughness: 0.8 });
    const galleta = new THREE.BoxGeometry(46, 32, 4);
    for (const [x, y, rz, rx] of [[-a + 34, -b + 30, 0.3, -0.25], [a - 34, -b + 30, -0.3, -0.25], [-a + 30, b - 32, -0.2, 0.2], [a - 30, b - 32, 0.25, 0.2]]) {
      const m = new THREE.Mesh(galleta, chocolina);
      m.position.set(x, y, this.arriba + 9);
      m.rotation.set(rx, 0, rz);
      this.add(m);
    }
  }

  // Oreo: costado de migas, crema blanca con migas y galletitas paradas en el borde
  oreo(R) {
    const H = 80, z0 = this.plato;
    this.platoRedondo(R);
    this.arriba = z0 + H + 2;
    const migas = tex(T_MIGAS("oreo-lado", "#1f1a19", ["#f2efe8", "#3a3330", "#0f0c0b", "#d6d0c6"], 7000, 0.6, 2.6), 5, 1.4);
    this.cil(R, H, z0, this.S({ map: migas, bumpMap: migas, bumpScale: 1.5, roughness: 0.9 }), null);
    const cremaTop = tex(T_MIGAS("oreo-top", "#f7f4ee", ["#1f1a19", "#3a3330", "#8a8580"], 2400, 0.6, 2.4), 1, 1);
    this.cil(R + 0.8, 2, z0 + H, this.S({ color: 0x241e1c, roughness: 0.3 }), this.S({ map: cremaTop, bumpMap: cremaTop, bumpScale: 0.5, roughness: 0.6 }));
    // chorreado de chocolate
    const baño = this.P({ color: 0x1c1412, roughness: 0.15 });
    for (let i = 0; i < 36; i++) {
      const a = (i / 36) * TAU + rnd(-0.05, 0.05), largo = rnd(6, 24);
      const gota = new THREE.Mesh(new THREE.CapsuleGeometry(rnd(3, 4.4), largo, 6, 12), baño);
      gota.rotation.x = Math.PI / 2;
      gota.position.set((R + 0.6) * Math.cos(a), (R + 0.6) * Math.sin(a), z0 + H + 1 - largo / 2);
      this.add(gota, false);
    }
    // copos de crema y galletitas Oreo paradas (mitad clavadas)
    const n = 12;
    this.instancias(rosetaGeo(1), this.S({ color: 0xffffff, roughness: 0.6 }),
      this.anillo(n, R - 10, this.arriba, { f: () => ({ s: 7.5, sz: 8 }) }));
    const cara = tex(T_OREO(), 1, 1);
    const negro = this.S({ map: cara, bumpMap: cara, bumpScale: 1.5, roughness: 0.75 });
    const canto = this.S({ color: 0x1d1918, roughness: 0.85 });
    const blanco = this.S({ color: 0xf8f6f0, roughness: 0.5 });
    const tapaG = new THREE.CylinderGeometry(21, 21, 3.6, 40);
    const relleno = new THREE.CylinderGeometry(19.5, 19.5, 3.2, 40);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU + Math.PI / n;
      const oreo = new THREE.Group();
      for (const [geo, y, mats] of [[tapaG, -3.4, [canto, negro, negro]], [relleno, 0, [blanco, blanco, blanco]], [tapaG, 3.4, [canto, negro, negro]]]) {
        const m = new THREE.Mesh(geo, mats);
        m.position.y = y;
        m.castShadow = m.receiveShadow = true;
        oreo.add(m);
      }
      // parada, mirando hacia afuera
      oreo.position.set((R - 11) * Math.cos(a), (R - 11) * Math.sin(a), this.arriba + 12);
      oreo.rotation.set(0, 0, a + Math.PI / 2);
      oreo.rotateX(-0.25);
      this.grupo.add(oreo);
    }
    // migas grandes por arriba
    this.instancias(new THREE.DodecahedronGeometry(1, 0), this.S({ color: 0x1d1918, roughness: 0.85 }),
      Array.from({ length: 90 }, () => { const r = Math.sqrt(Math.random()) * (R - 26), a = Math.random() * TAU; return { x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba + 0.4, s: rnd(1, 2.6), rx: rnd(0, 3), ry: rnd(0, 3) }; }));
  }

  // pasta frola: tarta baja de masa dorada, membrillo brillante y enrejado
  pastafrola(R) {
    const Rt = R * 1.06, H = 26, z0 = this.plato;
    this.platoRedondo(Rt);
    this.R = Rt;
    this.forma = { rect: false, R: Rt, a: Rt, b: Rt, plato: Rt + 32 };
    this.arriba = z0 + H - 3;
    const masa = tex(T_MASA(), 6, 1);
    const masaM = this.S({ map: masa, bumpMap: masa, bumpScale: 1, roughness: 0.85 });
    this.cil(Rt, H - 4, z0, masaM, null);
    const memb = tex(T_MEMBRILLO(), 1, 1);
    const relleno = new THREE.Mesh(new THREE.CircleGeometry(Rt - 4, 96), this.P({ map: memb, roughness: 0.2, clearcoat: 1 }));
    relleno.position.z = this.arriba;
    this.add(relleno);
    // borde repulgado: bollitos de masa alrededor
    const bollo = new THREE.SphereGeometry(1, 16, 12);
    this.instancias(bollo, masaM, this.anillo(54, Rt - 2.5, z0 + H - 4, { f: () => ({ sx: 4.4, sy: 3.4, sz: 3.6 }) }));
    // enrejado: tiras en diagonal en las dos direcciones, apenas abovedadas
    const masaT = this.S({ map: tex(T_MASA(), 1, 4), bumpMap: tex(T_MASA(), 1, 4, false), bumpScale: 1, roughness: 0.8 });
    for (const ang of [Math.PI / 4, -Math.PI / 4]) {
      for (let d = -Rt + 26; d <= Rt - 26; d += 40) {
        const L = 2 * Math.sqrt(Math.max(0, (Rt - 4) ** 2 - d * d));
        if (L < 12) continue;
        const tira = new THREE.Mesh(new THREE.CapsuleGeometry(1, L - 4, 4, 10), masaT);
        tira.scale.set(6.5, 1, 2.4);
        tira.rotation.set(0, 0, ang);
        // la tira va a lo largo de (−sen, cos); se corre d por la perpendicular (cos, sen)
        tira.position.set(Math.cos(ang) * d, Math.sin(ang) * d, this.arriba + (ang > 0 ? 1.4 : 2.6));
        this.add(tira);
      }
    }
  }

  // rogel: muchas capas finitas de masa y dulce de leche, merengue italiano tostado arriba
  rogel(R) {
    const H = 72, z0 = this.plato;
    this.platoRedondo(R);
    this.arriba = z0 + H;
    const capas = [];
    for (let i = 0; i < 9; i++) capas.push(["#e9c48b", 0.5, 1], ["#8a4a1c", 0.42, 0]);
    capas.push(["#e9c48b", 0.5, 1], ["#fbf3e3", 0.5, 0]);
    const lado = tex(T_CAPAS("rogel", capas), 5, 1);
    this.cil(R, H, z0, this.S({ map: lado, bumpMap: lado, bumpScale: 0.8, roughness: 0.8 }), this.S({ color: 0xfbf3e3, roughness: 0.6 }));
    // merengue: picos en espiral, tostados en las puntas (color por pico)
    const pico = picoGeo();
    const lista = [];
    const N = 150;
    for (let i = 0; i < N; i++) {
      const r = Math.sqrt((i + 0.5) / N) * (R - 7), a = i * 2.39996;
      lista.push({ x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba - 0.5, s: rnd(6.2, 7.4), sz: rnd(8, 10), rz: Math.random() * TAU });
    }
    this.instancias(pico, this.S({ color: 0xffffff, roughness: 0.55 }), lista,
      () => new THREE.Color().setHSL(0.09, 0.55, rnd(0.78, 0.95)).getHex());
  }

  // frutillas con crema: crema peinada, frutillas enteras en el borde y en el centro
  frutillas(R) {
    const H = 80, z0 = this.plato;
    this.platoRedondo(R);
    this.arriba = z0 + H;
    const lado = tex(T_PEINADA(), 8, 1);
    this.cil(R, H, z0, this.S({ map: lado, bumpMap: lado, bumpScale: 1.4, roughness: 0.65 }),
      this.S({ map: tex(T_CREMA("#fffdf8", "#f2ece2"), 1, 1), roughness: 0.65 }));
    const ros = rosetaGeo(1);
    const crema = this.S({ color: 0xfffdf8, roughness: 0.6 });
    this.instancias(ros, crema, this.anillo(16, R - 9, this.arriba, { f: () => ({ s: 7, sz: 8 }) }));
    this.instancias(ros, crema, this.anillo(40, R + 2.5, z0, { f: () => ({ s: 6.5, sz: 6 }) }));
    const fr = frutillaGeo();
    const rojo = this.P({ map: tex(T_FRUTILLA(), 2, 1), roughness: 0.3, clearcoat: 0.9 });
    const verde = this.S({ color: 0x3f9a3a, roughness: 0.6, side: THREE.DoubleSide });
    // en el borde, paradas con la punta para arriba entre los copos; adelante, un montoncito
    // acostadas con hojitas de menta (no tapan el texto: van abajo del topper)
    const borde = this.anillo(16, R - 9, this.arriba + 13, { fase: Math.PI / 16 }).map((u) => ({ ...u, s: 8, sz: 9, rx: Math.PI }));
    const monton = [];
    for (let i = 0; i < 7; i++) {
      const a = -Math.PI / 2 + rnd(-0.5, 0.5), r = R * rnd(0.45, 0.62);
      monton.push({ x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba + 5, s: 8, sz: 9, rx: Math.PI / 2, rz: Math.random() * TAU });
    }
    this.instancias(fr, rojo, [...borde, ...monton]);
    this.instancias(new THREE.CircleGeometry(1, 24), verde, monton.map((u) => ({ x: u.x + rnd(-8, 8), y: u.y + rnd(-8, 8),
      z: this.arriba + 0.6, sx: 7, sy: 3.2, rz: Math.random() * TAU })));
  }

  // selva negra: virutas de chocolate al costado, copos de crema con cerezas
  selva(R) {
    const H = 84, z0 = this.plato;
    this.platoRedondo(R);
    this.arriba = z0 + H;
    const vir = tex(T_VIRUTAS(), 5, 1.4);
    this.cil(R, H, z0, this.S({ map: vir, bumpMap: vir, bumpScale: 2.2, roughness: 0.85 }),
      this.S({ map: tex(T_CREMA("#fffdf8", "#efe8de"), 1, 1), roughness: 0.65 }));
    const ros = rosetaGeo(1);
    this.instancias(ros, this.S({ color: 0xfffdf8, roughness: 0.6 }), this.anillo(14, R - 10, this.arriba, { f: () => ({ s: 8, sz: 10 }) }));
    const cereza = this.P({ color: 0x8a0a14, roughness: 0.12, clearcoat: 1 });
    const lugares = this.anillo(14, R - 10, this.arriba + 12.5);
    this.instancias(new THREE.SphereGeometry(1, 20, 14), cereza, lugares.map((u) => ({ ...u, s: 5.4 })));
    const cabo = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, 0), new THREE.Vector3(1.5, 0, 6), new THREE.Vector3(4.5, 0, 11)]), 12, 0.55, 6), this.S({ color: 0x5b3b1c }));
    for (const u of lugares) {
      const c = cabo.clone();
      c.position.set(u.x, u.y, u.z + 4.2);
      c.rotation.z = u.rz;
      this.add(c, false);
    }
    // virutas en el centro
    const rulo = new THREE.TorusGeometry(3.2, 1.1, 6, 14, Math.PI * 1.3);
    this.instancias(rulo, this.S({ color: 0x3a2014, roughness: 0.7 }),
      Array.from({ length: 70 }, () => { const r = Math.sqrt(Math.random()) * (R * 0.55), a = Math.random() * TAU; return { x: r * Math.cos(a), y: r * Math.sin(a), z: this.arriba + 1.2, rx: rnd(0, 3), ry: rnd(0, 3), rz: rnd(0, 3), s: rnd(0.9, 1.4) }; }),
      () => [0x3a2014, 0x5c3a22, 0x2a160c, 0x6b4428][(Math.random() * 4) | 0]);
  }

  // velitas atrás, en las esquinas (no tapan el texto)
  velas() {
    const F = this.forma, M = this.mats;
    const puntos = F.rect
      ? [[-F.a + 16, F.b - 18], [-F.a + 34, F.b - 30], [F.a - 34, F.b - 30], [F.a - 16, F.b - 18]]
      : [0.08, 0.2, 0.8, 0.92].map((k) => [(F.R - 16) * Math.cos(Math.PI * k), (F.R - 16) * Math.sin(Math.PI * k) + 6]);
    const geo = new THREE.CylinderGeometry(3, 3, 38, 18);
    puntos.forEach(([x, y], i) => {
      const vela = new THREE.Mesh(geo, i % 2 ? M.vela2 : M.vela);
      vela.rotation.x = Math.PI / 2;
      vela.position.set(x, y, this.arriba + 19);
      this.add(vela);
      const mecha = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4, 6), M.mecha);
      mecha.rotation.x = Math.PI / 2;
      mecha.position.set(x, y, this.arriba + 40);
      this.add(mecha, false);
      const llama = new THREE.Group();
      const ext = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 10), M.llama);
      ext.scale.set(3.2, 3.2, 7);
      const nuc = new THREE.Mesh(new THREE.SphereGeometry(1, 10, 8), M.nucleo);
      nuc.scale.set(1.6, 1.6, 3.6);
      nuc.position.z = -1.2;
      llama.add(ext, nuc);
      llama.position.set(x, y, this.arriba + 47);
      llama.visible = this.fiesta;           // si se recalcula en plena fiesta, siguen prendidas
      llama.userData.fase = Math.random() * 10;
      this.grupo.add(llama);
      this.llamas.push(llama);
    });
  }

  // altura de lo que hay debajo de (x, y): la torta, el plato o la mesa
  alturaEn(x, y) {
    const F = this.forma;
    if (F.rect) {
      if (Math.abs(x) < F.a && Math.abs(y) < F.b) return this.arriba + 1.2;
      return Math.abs(x) < F.plato && Math.abs(y) < F.plato * 0.8 ? this.plato + 0.5 : 0.6;
    }
    const r = Math.hypot(x, y);
    return r < F.R + 4 ? this.arriba + 1.2 : (r < F.plato ? this.plato + 0.5 : 0.6);
  }

  armarConfeti() {
    const N = 700;
    this.N = N;
    const geo = new THREE.PlaneGeometry(4, 7);
    const im = new THREE.InstancedMesh(geo, this.mats.confeti, N);
    im.name = "CONFETI";
    im.frustumCulled = false;
    const c = new THREE.Color();
    for (let i = 0; i < N; i++) im.setColorAt(i, c.setHex(COLORES[i % COLORES.length]));
    im.count = 0;
    this.confeti = im;
    this.p = new Float32Array(N * 3);
    this.vel = new Float32Array(N * 3);
    this.giro = new Float32Array(N * 4);       // eje (3) y velocidad
    this.ang = new Float32Array(N);
    this.quieto = new Uint8Array(N);
    this.vivos = 0;
    this.grupo.add(im);
  }

  // ------------------------------------------------------------------ piezas clavadas
  // cuánto entran los palitos: 60 % del largo, sin atravesar una torta baja
  profundidad(largo) { return Math.min(0.6 * largo, this.arriba - this.plato - 6); }

  clavar(pose, largo, animar = true, donde = {}) {
    pose.position.x = donde.x || 0;
    pose.position.y = donde.y || 0;
    pose.position.z = 0;
    pose.updateMatrixWorld(true);
    const inv = this.v.model.matrixWorld.clone().invert();
    const b = new THREE.Box3().setFromObject(pose);
    const zmin = b.min.clone().applyMatrix4(inv).z - pose.position.z;
    let c = this.clavadas.find((x) => x.pose === pose);
    if (!c) { c = { pose }; this.clavadas.push(c); }
    c.zFinal = this.arriba - zmin - this.profundidad(largo);
    c.retraso = donde.retraso || 0;
    if (animar) {
      c.entrada = { t: -c.retraso, dur: 1.15, desde: c.zFinal + 160 };
      pose.position.z = c.entrada.desde;
    } else {
      c.entrada = null;
      pose.position.z = c.zFinal;
    }
  }

  soltar(pose) { this.clavadas = this.clavadas.filter((c) => c.pose !== pose); }

  get pose() { return this.clavadas[0]?.pose || null; }
  get zFinal() { return this.clavadas[0]?.zFinal ?? null; }
  get entrada() { return this.clavadas.some((c) => c.entrada); }

  // ------------------------------------------------------------------ modo cumpleaños
  setFiesta(on) {
    this.fiesta = on;
    for (const l of this.llamas || []) l.visible = on;
    this.v.controls.autoRotate = on;
    this.v.controls.autoRotateSpeed = 1.2;
    if (on) {
      this.rafaga(true);
      this.rafaga(false);
      this.lluvia = 0;
      this.clavadas.forEach((c, i) => {
        c.entrada = { t: -0.3 * i, dur: 1.15, desde: c.zFinal + 160 };
        c.pose.position.z = c.entrada.desde;
      });
    } else {
      this.vivos = 0;
      this.confeti.count = 0;
    }
  }

  // ráfaga de un cañón al costado de la torta
  rafaga(izq) {
    const n = 220;
    const R = Math.max(this.forma.a, this.R);
    for (let k = 0; k < n; k++) {
      const i = this.nuevo();
      if (i < 0) break;
      const s = izq ? -1 : 1;
      this.p.set([s * (R + 40), rnd(-30, 30), this.arriba * 0.4], i * 3);
      this.vel.set([-s * rnd(80, 260), rnd(-90, 90), rnd(420, 720)], i * 3);
    }
    this.stats.rafagas++;
  }

  nuevo() {
    if (this.vivos >= this.N) return -1;
    const i = this.vivos++;
    this.confeti.count = this.vivos;
    const e = new THREE.Vector3(rnd(-1, 1), rnd(-1, 1), rnd(-1, 1)).normalize();
    this.giro.set([e.x, e.y, e.z, rnd(6, 16)], i * 4);
    this.ang[i] = Math.random() * TAU;
    this.quieto[i] = 0;
    return i;
  }

  tickConfeti(dt) {
    if (!this.vivos) return;
    const o = new THREE.Object3D();
    const e = new THREE.Vector3();
    const P = this.p, Vl = this.vel;
    let apoyados = 0;
    for (let i = 0; i < this.vivos; i++) {
      const k = i * 3;
      if (!this.quieto[i]) {
        Vl[k + 2] -= 820 * dt;                                    // gravedad
        const roce = Math.exp(-2.4 * dt);                           // el aire lo frena
        Vl[k] *= roce; Vl[k + 1] *= roce;
        if (Vl[k + 2] < -95) Vl[k + 2] = -95 + (Vl[k + 2] + 95) * Math.exp(-6 * dt);   // cae flotando
        Vl[k] += Math.sin(this.t * 3 + i) * 30 * dt;                // vaivén
        P[k] += Vl[k] * dt; P[k + 1] += Vl[k + 1] * dt; P[k + 2] += Vl[k + 2] * dt;
        this.ang[i] += this.giro[i * 4 + 3] * dt;
        const piso = this.alturaEn(P[k], P[k + 1]);
        if (P[k + 2] <= piso && Vl[k + 2] < 0) {
          P[k + 2] = piso;
          this.quieto[i] = 1;
        }
      }
      if (this.quieto[i]) apoyados++;
      o.position.set(P[k], P[k + 1], P[k + 2]);
      if (this.quieto[i]) {
        o.quaternion.setFromAxisAngle(e.set(0, 0, 1), this.ang[i]);     // apoyado: plano
      } else {
        o.quaternion.setFromAxisAngle(e.set(this.giro[i * 4], this.giro[i * 4 + 1], this.giro[i * 4 + 2]), this.ang[i]);
      }
      o.updateMatrix();
      this.confeti.setMatrixAt(i, o.matrix);
    }
    this.confeti.instanceMatrix.needsUpdate = true;
    this.stats.confeti = this.vivos;
    this.stats.apoyados = apoyados;
  }

  tick(dt) {
    if (!this.grupo.parent) return;
    this.t += dt;
    this.stats.frames++;
    for (const c of this.clavadas) {
      const E = c.entrada;
      if (!E) continue;
      E.t += Math.min(dt, 1 / 30);          // un cuadro lento (texturas nuevas) no salta la entrada
      const u = Math.max(0, Math.min(1, E.t / E.dur));
      c.pose.position.z = E.desde + (c.zFinal - E.desde) * easeOutBack(u);
      if (u >= 1) { c.pose.position.z = c.zFinal; c.entrada = null; }
    }
    if (this.fiesta) {
      // confeti que sigue cayendo desde arriba (hasta llenar)
      this.lluvia += dt * 26;
      const R = Math.max(this.forma.a, this.R);
      while (this.lluvia >= 1) {
        this.lluvia -= 1;
        const i = this.nuevo();
        if (i < 0) break;
        const r = Math.sqrt(Math.random()) * (R + 60), a = Math.random() * TAU;
        this.p.set([r * Math.cos(a), r * Math.sin(a), this.arriba + rnd(180, 260)], i * 3);
        this.vel.set([rnd(-20, 20), rnd(-20, 20), -rnd(20, 60)], i * 3);
      }
      let on = 0;
      for (const l of this.llamas) {
        const f = l.userData.fase + this.t * 13;
        l.scale.set(1 + 0.08 * Math.sin(f), 1 + 0.08 * Math.cos(f * 1.3), 1 + 0.16 * Math.sin(f * 0.7));
        l.rotation.x = 0.12 * Math.sin(f * 0.5);
        on += l.visible ? 1 : 0;
      }
      this.stats.llamas = on;
    }
    this.tickConfeti(dt);
  }

  info() {
    const p = this.clavadas[0];
    return { fiesta: this.fiesta, confeti: this.vivos || 0, apoyados: this.vivos ? this.stats.apoyados : 0,
      rafagas: this.stats.rafagas, llamas: this.fiesta ? (this.llamas || []).filter((l) => l.visible).length : 0,
      entrando: this.entrada, arriba: this.arriba || 0, radio: this.R || 0, tortaTipo: this.tipo,
      clavadas: this.clavadas.length,
      topperZ: p ? +p.pose.position.z.toFixed(2) : null, zFinal: p ? p.zFinal : null };
  }
}
