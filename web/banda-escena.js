// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// Banda de recibida animada: la soga pasa por todas las cuentas y la banda queda
//   · "persona": puesta de costado en un maniquí (del hombro a la cadera), o
//   · "pared":   colgada de dos clavos como un colgante.
// Todo en el marco del motor (z hacia arriba, el frente hacia -y): se arma dentro de viewer.model.
import * as THREE from "three";

const TAU = Math.PI * 2;
const _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _m = new THREE.Matrix4();
const _uno = new THREE.Vector3(1, 1, 1), _x = new THREE.Vector3(1, 0, 0);
const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));

// --- maniquí (medidas a escala 1, en mm): medio ancho a(z) y media profundidad b(z) del torso
const TORSO_Z = [0, 60, 150, 250, 330, 420, 500, 550, 585, 620];
const TORSO_A = [165, 172, 158, 140, 142, 156, 166, 160, 125, 52];
const TORSO_B = [112, 116, 106, 96, 100, 110, 108, 96, 78, 46];
const TORSO_H = 620;
const PIE_H = 640;                    // pie del maniquí (del piso a la cadera)

// perfiles suavizados (promedio móvil sobre la tabla, cada 5 mm) para que el torso no salga facetado
function suave(ys) {
  const paso = 5, n = Math.round(TORSO_H / paso) + 1, crudo = [];
  for (let i = 0; i < n; i++) crudo.push(interp(TORSO_Z, ys, i * paso));
  const out = [], w = 9;
  for (let i = 0; i < n; i++) {
    let s = 0, c = 0;
    for (let j = -w; j <= w; j++) {
      const k = Math.min(n - 1, Math.max(0, i + j)), peso = 1 - Math.abs(j) / (w + 1);
      s += crudo[k] * peso; c += peso;
    }
    out.push(s / c);
  }
  return (z) => {
    const u = Math.min(Math.max(z / paso, 0), n - 1), i = Math.min(Math.floor(u), n - 2), t = u - i;
    return out[i] * (1 - t) + out[i + 1] * t;
  };
}
let _A = null, _B = null;
const torsoA = (z) => (_A = _A || suave(TORSO_A))(z);
const torsoB = (z) => (_B = _B || suave(TORSO_B))(z);

function interp(xs, ys, x) {
  if (x <= xs[0]) return ys[0];
  for (let i = 1; i < xs.length; i++) {
    if (x <= xs[i]) {
      const t = (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
      return ys[i - 1] + (ys[i] - ys[i - 1]) * t;
    }
  }
  return ys[ys.length - 1];
}

// --- recorrido cerrado del hilo: muestras parejas por largo, con tangente y normal (afuera)
class Recorrido {
  constructor(puntos, normalDe, largo, M = 720) {
    // puntos: polilínea cerrada cruda; se re-muestrea en M puntos parejos
    const n = puntos.length;
    const acc = [0];
    for (let i = 1; i <= n; i++) acc.push(acc[i - 1] + puntos[i % n].distanceTo(puntos[i - 1]));
    this.L = acc[n];
    this.P = [];
    let j = 0;
    for (let k = 0; k < M; k++) {
      const s = (k / M) * this.L;
      while (acc[j + 1] < s) j++;
      const t = (s - acc[j]) / Math.max(acc[j + 1] - acc[j], 1e-9);
      this.P.push(puntos[j].clone().lerp(puntos[(j + 1) % n], t));
    }
    this.M = M;
    this.T = this.P.map((_, k) => this.P[(k + 1) % M].clone().sub(this.P[(k - 1 + M) % M]).normalize());
    this.N = this.P.map((p, k) => {
      const nn = normalDe(p, this.T[k]);
      return nn.sub(this.T[k].clone().multiplyScalar(nn.dot(this.T[k]))).normalize();
    });
    this.largo = largo;
  }

  // punto, tangente y normal en el largo s (vuelve a empezar al pasar L)
  en(s) {
    const u = (((s / this.L) % 1) + 1) % 1 * this.M;
    const i = Math.floor(u) % this.M, i1 = (i + 1) % this.M, t = u - Math.floor(u);
    return {
      p: this.P[i].clone().lerp(this.P[i1], t),
      t: this.T[i].clone().lerp(this.T[i1], t).normalize(),
      n: this.N[i].clone().lerp(this.N[i1], t).normalize(),
    };
  }
}

// banda puesta: el lazo sigue el cuerpo en un plano inclinado del hombro derecho a la cadera izquierda
function recorridoPersona(L, grosor) {
  // el maniquí se escala para que el lazo mida lo que la banda (una banda de 60 cm es de un nene)
  let k = 1, rec = null, datos = null;
  for (let iter = 0; iter < 3; iter++) {
    const S = new THREE.Vector3(-118 * k, 0, 575 * k);           // arriba del hombro derecho (el de la izquierda en pantalla)
    const H = new THREE.Vector3(150 * k, 0, 45 * k);             // costado de la cadera izquierda
    const C = S.clone().add(H).multiplyScalar(0.5);
    const u = S.clone().sub(H).normalize(), v = new THREE.Vector3(0, 1, 0);
    const dentro = (p) => {
      const z = p.z / k;
      if (z < 0 || z > TORSO_H) return false;
      const a = torsoA(z) * k, b = torsoB(z) * k;
      return (p.x / a) ** 2 + (p.y / b) ** 2 <= 1;
    };
    const pts = [];
    const N = 540;
    let frente = 0;
    for (let i = 0; i < N; i++) {
      // de la cadera, por la espalda, sobre el hombro y por el pecho de vuelta a la cadera
      const phi = Math.PI - (TAU * i) / N;
      if (Math.abs(phi + Math.PI / 2) < Math.PI / N) frente = i;
      const d = u.clone().multiplyScalar(Math.cos(phi)).addScaledVector(v, Math.sin(phi));
      let lo = 0, hi = 900 * k;
      for (let q = 0; q < 40; q++) {
        const m = (lo + hi) / 2;
        if (dentro(C.clone().addScaledVector(d, m))) lo = m; else hi = m;
      }
      pts.push(C.clone().addScaledVector(d, lo + grosor * 0.5 + 2));
    }
    // largo del lazo y dónde cae el centro del pecho
    let P = 0, sFrente = 0;
    for (let i = 1; i <= N; i++) { P += pts[i % N].distanceTo(pts[i - 1]); if (i === frente) sFrente = P; }
    datos = { k, C, pts, sFrente, P };
    if (Math.abs(P - L) < 0.004 * L) break;
    k *= L / P;
  }
  const { C, pts } = datos;
  rec = new Recorrido(pts, (p) => p.clone().sub(C), L);
  rec.sFrente = (datos.sFrente / datos.P) * rec.L;
  rec.inicio = 0;
  rec.k = datos.k;
  return rec;
}

// colgada en la pared: arriba recta entre dos clavos y abajo una catenaria con el texto
function recorridoPared(L, grosor) {
  const w = 0.36 * L, Lc = L - w;
  let lo = w / 40, hi = w * 50;
  for (let q = 0; q < 80; q++) {                      // 2 a sinh(w / 2a) = Lc
    const a = (lo + hi) / 2;
    if (2 * a * Math.sinh(w / (2 * a)) > Lc) lo = a; else hi = a;
  }
  const a = (lo + hi) / 2;
  const ch = Math.cosh(w / (2 * a));
  const pts = [];
  const N1 = 420, N2 = 120;
  for (let i = 0; i < N1; i++) {                      // del clavo izquierdo, por abajo, al derecho
    const x = -w / 2 + (w * i) / N1;
    pts.push(new THREE.Vector3(x, 0, -a * (ch - Math.cosh(x / a))));
  }
  for (let i = 0; i < N2; i++) {                      // de vuelta por arriba de los clavos
    const x = w / 2 - (w * i) / N2;
    pts.push(new THREE.Vector3(x, 0, 0));
  }
  const rec = new Recorrido(pts, () => new THREE.Vector3(0, -1, 0), L);
  rec.sFrente = Lc / 2;                               // el fondo de la catenaria
  rec.inicio = 0;
  rec.w = w;
  rec.caida = a * (ch - 1);
  return rec;
}

export class BandaEscena {
  constructor(viewer) {
    this.v = viewer;
    this.grupo = null;
    this.cuentas = [];
    this.anim = null;
    this.stats = { montajes: 0, fase: "—", enhebradas: 0, total: 0, modo: null, frames: 0 };
    viewer.tickers = viewer.tickers || [];
    viewer.tickers.push((dt) => this.tick(dt));
  }

  quitar() {
    if (this.grupo) {
      this.grupo.parent && this.grupo.parent.remove(this.grupo);
      this.grupo.traverse((o) => { if (o.geometry && o.userData.propia) o.geometry.dispose(); });
    }
    if (this.hilo) { this.hilo.geometry.dispose(); this.hilo = null; }
    for (const im of this.instancias || []) im.dispose();
    this.instancias = [];
    this.grupo = null;
    this.cuentas = [];
    this.anim = null;
    this.stats.modo = null;
    this.stats.fase = "—";
  }

  // unicas: { "DISCO#M": [mesh,...] } mallas del visor en el marco de la cuenta.
  // Optimizado: una InstancedMesh por pieza distinta (pocas llamadas de dibujo) y la soga se
  // arma una sola vez y se va "destapando" con drawRange (antes se rehacía en cada cuadro).
  montar(modo, unicas, s) {
    this.quitar();
    const g = new THREE.Group();
    g.name = "BANDA_" + modo.toUpperCase();
    const L = s.largo_mm, grosor = s.grosor_mm;
    this.hiloR = s.hilo_r_mm;
    this.grosor = grosor;
    const rec = modo === "persona" ? recorridoPersona(L, grosor) : recorridoPared(L, grosor);
    this.rec = rec;
    // posiciones de las cuentas sobre el hilo (el texto centrado en el frente)
    const sec = s.secuencia, pos = [];
    let acc = 0;
    for (const c of sec) { pos.push(acc + c.largo / 2); acc += c.largo + s.hueco_mm; }
    const nt = Math.max(1, s.n_texto);
    const mitad = (pos[0] + pos[nt - 1]) / 2;
    // cuántas cuentas usa cada malla
    const claves = (c) => (c.pieza === "DISCO" ? ["DISCO#" + c.letra, "LETRAS#" + c.letra] : [c.pieza + "#"]);
    const cuantas = {};
    for (const c of sec) for (const k of claves(c)) cuantas[k] = (cuantas[k] || 0) + 1;
    const inst = {};
    for (const [k, n] of Object.entries(cuantas)) {
      inst[k] = (unicas[k] || []).map((base) => {
        const im = new THREE.InstancedMesh(base.geometry, base.material, n);
        im.name = base.name;
        im.castShadow = im.receiveShadow = true;
        im.frustumCulled = false;                  // las cuentas se mueven: la esfera de la base no sirve
        im.userData.libre = 0;
        g.add(im);
        return im;
      });
    }
    this.instancias = Object.values(inst).flat();
    const m = new THREE.Matrix4(), X = new THREE.Vector3(), Y = new THREE.Vector3(), Z = new THREE.Vector3();
    sec.forEach((c, i) => {
      const sc = rec.sFrente + pos[i] - mitad;
      const f = rec.en(sc);
      X.copy(f.t); Z.copy(f.n); Y.crossVectors(Z, X).normalize();
      if (i >= nt && Y.z < -0.3) { X.negate(); Y.negate(); }   // las cuentas del relleno, derechas
      m.makeBasis(X, Y, Z);
      const q = new THREE.Quaternion().setFromRotationMatrix(m);
      const slots = [];
      for (const k of claves(c)) for (const im of inst[k] || []) slots.push([im, im.userData.libre++]);
      // antes de enhebrar: flotando un poco afuera del recorrido, apenas giradas
      const fuera = f.p.clone().addScaledVector(f.n, grosor * 2.2 + 18).addScaledVector(Y, (i % 2 ? 1 : -1) * grosor * 0.5);
      const q0 = q.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(0.5 * Math.sin(i * 1.7), 0.6 * Math.cos(i * 2.3), 0.4 * Math.sin(i))));
      const sFix = ((sc % rec.L) + rec.L) % rec.L;
      this.cuentas.push({ slots, p1: f.p.clone(), q1: q, p0: fuera, q0, s: sFix, largo: c.largo, k: -1 });
    });
    this.cuentas.sort((a, b) => a.s - b.s);          // en el orden en que pasa la aguja
    // la soga entera, de una vez (se muestra hasta la punta con drawRange)
    const r = this.hiloR || 2.5;
    const pts = [];
    for (let k = 0; k < rec.M; k += 2) pts.push(rec.P[k].clone());
    this.SEG = 720;
    this.RAD = 8;
    const tubo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true, "centripetal"), this.SEG, r, this.RAD, true);
    this.hilo = new THREE.Mesh(tubo, this.v.mats.HILO);
    this.hilo.name = "HILO";
    this.hilo.castShadow = true;
    this.hilo.frustumCulled = false;
    tubo.setDrawRange(0, 0);
    g.add(this.hilo);
    // aguja en la punta del hilo
    const aguja = new THREE.Mesh(new THREE.ConeGeometry(r * 1.6, r * 14, 10), new THREE.MeshStandardMaterial({ color: 0xb8bcc4, metalness: 0.85, roughness: 0.25 }));
    aguja.geometry.rotateZ(-Math.PI / 2);                // la punta hacia +x
    aguja.userData.propia = true;
    aguja.name = "AGUJA";
    g.add(aguja);
    this.aguja = aguja;
    // escenario: maniquí o pared con clavos
    const extra = modo === "persona" ? this.maniqui(rec.k) : this.pared(rec, grosor);
    g.add(extra);
    this.extra = extra;
    // todo apoyado en el piso (z = 0 del modelo)
    if (modo === "persona") g.position.z = PIE_H * rec.k + 30 * rec.k;
    else g.position.z = 260 + rec.caida;
    this.grupo = g;
    this.v.model.add(g);
    this.stats.modo = modo;
    this.stats.total = this.cuentas.length;
    this.stats.montajes++;
    this.empezar();
    return g;
  }

  // caja para encuadrar: la banda (y el torso), sin el pie del maniquí ni toda la pared
  cajaEncuadre() {
    const b = new THREE.Box3();
    const pad = new THREE.Vector3(1, 1, 1).multiplyScalar(this.grosor || 20);
    const tmp = new THREE.Box3();
    for (const c of this.cuentas) for (const p of [c.p0, c.p1]) {
      tmp.min.copy(p).sub(pad); tmp.max.copy(p).add(pad);
      b.union(tmp);
    }
    this.grupo.updateWorldMatrix(true, true);
    b.applyMatrix4(this.grupo.matrixWorld);
    if (this.torso) b.expandByObject(this.torso);
    return b;
  }

  _poner(c, k) {
    if (k === c.k) return false;
    c.k = k;
    _p.lerpVectors(c.p0, c.p1, k);
    _q.slerpQuaternions(c.q0, c.q1, k);
    _m.compose(_p, _q, _uno);
    for (const [im, i] of c.slots) im.setMatrixAt(i, _m);
    return true;
  }

  _marcar() {
    for (const im of this.instancias) im.instanceMatrix.needsUpdate = true;
  }

  _hasta(tip) {
    const segs = Math.max(0, Math.min(this.SEG, Math.floor((tip / this.rec.L) * this.SEG)));
    this.hilo.geometry.setDrawRange(0, segs * this.RAD * 6);
  }

  empezar() {
    const dur = THREE.MathUtils.clamp((this.rec.L / 1300) * 6.5, 4.5, 9);
    this.anim = { tip: -60, vel: (this.rec.L + 120) / dur, listo: false };
    this.stats.fase = "enhebrando";
    this.stats.enhebradas = 0;
    this.aguja.visible = true;
    for (const c of this.cuentas) { c.k = -1; this._poner(c, 0); }
    this._marcar();
    this._hasta(0);
    const f = this.rec.en(0);
    this.aguja.position.copy(f.p);
    this.aguja.quaternion.setFromUnitVectors(_x, f.t);
  }

  // terminar ya (para fotos y descargas)
  terminar() {
    if (!this.anim) return;
    this.anim.tip = this.rec.L + 80;
    this.tick(0);
  }

  tick(dt) {
    const A = this.anim;
    if (!A || A.listo || !this.grupo) return;
    this.stats.frames++;
    A.tip += A.vel * Math.min(dt, 0.1);
    const L = this.rec.L;
    let n = 0, cambio = false;
    for (const c of this.cuentas) {
      // la cuenta baja al hilo cuando la punta llega a ella (sólo se tocan las que se mueven)
      const k = ease((A.tip - c.s + c.largo) / (c.largo * 2.5 + 40));
      if (k >= 1) n++;
      if (this._poner(c, k)) cambio = true;
    }
    if (cambio) this._marcar();
    this.stats.enhebradas = n;
    const tip = Math.min(Math.max(A.tip, 0), L);
    this._hasta(tip);
    const f = this.rec.en(tip);
    this.aguja.position.copy(f.p).addScaledVector(f.t, (this.hiloR || 2.5) * 6);
    this.aguja.quaternion.setFromUnitVectors(_x, f.t);
    if (A.tip >= L + 60) {
      A.listo = true;
      for (const c of this.cuentas) this._poner(c, 1);
      this._marcar();
      this.stats.enhebradas = this.cuentas.length;
      this.aguja.visible = false;
      this.hilo.geometry.setDrawRange(0, Infinity);
      this.stats.fase = "lista";
    }
  }

  // maniquí de costura (torso de tela, cuello, perilla y pie de madera)
  maniqui(k) {
    const g = new THREE.Group();
    g.name = "MANIQUI";
    const tela = new THREE.MeshStandardMaterial({ color: 0xe8e1d4, roughness: 0.92 });
    const madera = new THREE.MeshStandardMaterial({ color: 0x5b3f2b, roughness: 0.55, metalness: 0.05 });
    const SEG = 96, pos = [], idx = [];
    const zs = [];
    for (let z = 0; z <= TORSO_H; z += 5) zs.push(z);
    for (const z of zs) {
      const a = torsoA(z) * k, b = torsoB(z) * k;
      for (let j = 0; j < SEG; j++) {
        const t = (TAU * j) / SEG;
        pos.push(a * Math.cos(t), b * Math.sin(t), z * k);
      }
    }
    for (let i = 0; i < zs.length - 1; i++) for (let j = 0; j < SEG; j++) {
      const a0 = i * SEG + j, a1 = i * SEG + ((j + 1) % SEG), b0 = a0 + SEG, b1 = a1 + SEG;
      idx.push(a0, a1, b1, a0, b1, b0);
    }
    // tapas
    const c0 = pos.length / 3; pos.push(0, 0, 0);
    const c1 = pos.length / 3; pos.push(0, 0, TORSO_H * k);
    const top = (zs.length - 1) * SEG;
    for (let j = 0; j < SEG; j++) {
      idx.push(c0, (j + 1) % SEG, j);
      idx.push(c1, top + j, top + ((j + 1) % SEG));
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const torso = new THREE.Mesh(geo, tela);
    torso.name = "TORSO";
    torso.userData.propia = true;
    this.torso = torso;
    const cuello = new THREE.Mesh(new THREE.CylinderGeometry(44 * k, 50 * k, 70 * k, 32), tela);
    cuello.rotation.x = Math.PI / 2;
    cuello.position.z = (TORSO_H + 30) * k;
    const tapa = new THREE.Mesh(new THREE.CylinderGeometry(46 * k, 44 * k, 10 * k, 32), madera);
    tapa.rotation.x = Math.PI / 2;
    tapa.position.z = (TORSO_H + 70) * k;
    const perilla = new THREE.Mesh(new THREE.SphereGeometry(16 * k, 20, 14), madera);
    perilla.position.z = (TORSO_H + 88) * k;
    const palo = new THREE.Mesh(new THREE.CylinderGeometry(12 * k, 14 * k, PIE_H * k, 20), madera);
    palo.rotation.x = Math.PI / 2;
    palo.position.z = -PIE_H * k / 2;
    const base = new THREE.Mesh(new THREE.CylinderGeometry(150 * k, 165 * k, 26 * k, 48), madera);
    base.rotation.x = Math.PI / 2;
    base.position.z = -PIE_H * k - 17 * k;
    for (const o of [torso, cuello, tapa, perilla, palo, base]) {
      o.castShadow = o.receiveShadow = true;
      o.userData.propia = true;
      g.add(o);
    }
    g.position.z = 0;
    return g;
  }

  // pared con dos clavos donde se cuelga la banda
  pared(rec, grosor) {
    const g = new THREE.Group();
    g.name = "PARED";
    this.torso = null;
    const atras = grosor * 0.5 + 3;
    const ancho = rec.w + 1400, alto = rec.caida + 1600;
    const muro = new THREE.Mesh(new THREE.PlaneGeometry(ancho, alto),
      new THREE.MeshStandardMaterial({ color: 0xefe9df, roughness: 0.95 }));
    muro.rotation.x = Math.PI / 2;                     // el plano mira hacia -y (al frente)
    muro.position.set(0, atras, alto / 2 - rec.caida - 260);
    muro.receiveShadow = true;
    muro.userData.propia = true;
    muro.name = "MURO";
    g.add(muro);
    const metal = new THREE.MeshStandardMaterial({ color: 0x9a9ea6, metalness: 0.9, roughness: 0.3 });
    for (const x of [-rec.w / 2, rec.w / 2]) {
      const largo = atras + grosor * 0.6 + 6;
      const clavo = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, largo, 12), metal);
      clavo.position.set(x, atras - largo / 2, -(2.2 + this.hiloR));
      const cabeza = new THREE.Mesh(new THREE.CylinderGeometry(5, 5, 1.6, 20), metal);
      cabeza.position.set(x, atras - largo, -(2.2 + this.hiloR));
      for (const o of [clavo, cabeza]) { o.castShadow = true; o.userData.propia = true; o.name = "CLAVO"; g.add(o); }
    }
    return g;
  }
}
