// © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados.
// La chapita con su llavero: argolla partida (doble vuelta), cadenita y el ganchito
// (argollita abierta) que pasa por el agujero de la chapita.
//   puesto:    la chapita cuelga de la argolla y se hamaca despacito
//   sin poner: todo apoyado en la mesa, el ganchito abierto al lado
// El cambio entre los dos es una animación: la chapita se levanta, llega la cadenita con
// la argolla, el ganchito pasa por el agujero y se cierra (y al revés).
import * as THREE from "three";

const TAU = Math.PI * 2;
const RJ = 4.2, TJ = 0.55;            // ganchito: radio y alambre (mm)
const RL = 1.5, TL = 0.4, KL = 1.5;   // eslabón: radio, alambre y estirado
const NL = 6, PASO = 3.5;             // eslabones y paso de la cadenita
const RS = 12, TS = 0.5;              // argolla partida (24 mm)
const ALTO = 8;                       // la chapita colgada queda a 8 mm de la mesa
const DUR = 3.2;                      // segundos de la animación
// tramos de la animación (0..1): la chapita sube, llega la cadenita, el ganchito y se cierra
const T_TAG = [0, 0.32], T_CAD = [0.3, 0.62], T_GAN = [0.58, 0.86], T_CIE = [0.86, 0.97];

const ease = (t) => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2);
const tramo = (t, [a, b]) => ease(THREE.MathUtils.clamp((t - a) / (b - a), 0, 1));

class Helice extends THREE.Curve {
  constructor(R, vueltas, paso) { super(); Object.assign(this, { R, vueltas, paso }); }
  getPoint(t, out = new THREE.Vector3()) {
    const a = t * this.vueltas * TAU;
    return out.set(this.R * Math.cos(a), this.R * Math.sin(a), (t - 0.5) * this.paso * this.vueltas);
  }
}

const M = () => new THREE.Matrix4();
const comp = (pos, quat) => M().compose(pos, quat, new THREE.Vector3(1, 1, 1));
const qx = (a) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), a);
const qy = (a) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), a);
const qz = (a) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), a);
const ACOSTADA = comp(new THREE.Vector3(), qx(-Math.PI / 2));     // como la deja el visor (z del motor arriba)

export class Llavero {
  constructor(viewer) {
    this.v = viewer;
    this.metal = new THREE.MeshStandardMaterial({ color: 0xd4d7dc, roughness: 0.3, metalness: 0.9, envMapIntensity: 1.5 });
    this.grupo = new THREE.Group();
    this.grupo.name = "LLAVERO";
    viewer.scene.add(this.grupo);
    this.puesto = true;
    this.tau = 1;                     // 0 sin poner … 1 puesto
    this.dir = 0;                     // animando hacia puesto (+1) o sin poner (-1)
    this.hora = 0;
    this.listo = false;
    this.cam = null;
    // la mesa y la sombra siguen a la chapita acostada aunque esté colgada
    viewer.sceneBox = () => this.cajaAcostada();
    (viewer.tickers = viewer.tickers || []).push((dt) => this.tick(dt));
  }

  get estado() {
    return { puesto: this.puesto, animando: this.dir !== 0, tau: +this.tau.toFixed(3), piezas: this.grupo.children.length,
      gap: this.gap ? +this.gap.toFixed(2) : 0, colgada: Math.abs(this.v.model.rotation.x) < 0.01 };
  }

  // caja de la chapita (sólo sus mallas) como si estuviera acostada en la mesa
  cajaLocal() {
    const b = new THREE.Box3();
    for (const m of this.v.model.children) {
      if (!m.isMesh) continue;
      m.geometry.computeBoundingBox();
      b.union(m.geometry.boundingBox);
    }
    return b;
  }
  cajaAcostada() {
    const b = this.cajaLocal();
    return b.isEmpty() ? b : b.applyMatrix4(ACOSTADA);
  }

  // después de cada cálculo: arma las piezas para el ojal de esta chapita
  montar(s) {
    for (const c of [...this.grupo.children]) { c.geometry.dispose(); this.grupo.remove(c); }
    const O = s.ojal, box = this.cajaLocal();
    const top = box.max.z, zc = top / 2;
    const ra = O.r_agujero;
    // -- puesto (coordenadas de la chapita: x, y en la placa, z el grosor)
    const yc = O.y + 0.3 * ra + RJ;                      // el ganchito cruza la placa dentro del agujero
    const cy0 = yc + RJ + 1.15;
    const ys = cy0 + (NL - 1) * PASO + 1.15 + RS;
    this.pivote = new THREE.Vector3(O.x, ys + RS, zc);   // de acá cuelga todo
    const hang = [];
    hang.push(comp(new THREE.Vector3(O.x, yc, zc), qy(Math.PI / 2)));
    for (let i = 0; i < NL; i++) hang.push(comp(new THREE.Vector3(O.x, cy0 + i * PASO, zc), i % 2 ? qy(Math.PI / 2) : new THREE.Quaternion()));
    hang.push(comp(new THREE.Vector3(O.x, ys, zc), qz(-0.5)));
    // -- sin poner (acostado en la mesa, al costado de la chapita; z arriba)
    const xr = box.max.x + 8 + RS, yr = Math.max(box.max.y - RS + 4, box.min.y + RS + 10);
    const loose = [];
    loose.push(comp(new THREE.Vector3(box.max.x + 9, box.min.y + RJ + 1, TJ), qz(0.7)));
    for (let i = 0; i < NL; i++) {
      const y = yr - RS - 1.15 - (NL - 1 - i) * PASO;
      loose.push(i % 2 ? comp(new THREE.Vector3(xr, y, RL + TL), qy(Math.PI / 2))
        : comp(new THREE.Vector3(xr, y, TL), new THREE.Quaternion()));
    }
    loose.push(comp(new THREE.Vector3(xr, yr, 0.95 + TS), qz(1.1)));
    this.hang = hang;
    this.loose = loose.map((m) => ACOSTADA.clone().multiply(m));    // a coordenadas del mundo
    // -- mallas
    this.gap = null;
    this.gancho = new THREE.Mesh(this.geoGancho(this.tau >= 1 ? 0.06 : 1.0), this.metal);
    this.gancho.name = "GANCHITO";
    const esl = new THREE.TorusGeometry(RL, TL, 10, 28).scale(1, KL, 1);
    const piezas = [this.gancho];
    for (let i = 0; i < NL; i++) { const m = new THREE.Mesh(i ? esl.clone() : esl, this.metal); m.name = "ESLABON"; piezas.push(m); }
    const arg = new THREE.Mesh(new THREE.TubeGeometry(new Helice(RS, 1.94, 1.05), 260, TS, 10, false), this.metal);
    arg.name = "ARGOLLA";
    piezas.push(arg);
    for (const p of piezas) { p.castShadow = true; p.receiveShadow = true; p.matrixAutoUpdate = false; this.grupo.add(p); }
    this.piezas = piezas;
    // colgada: el pivote en el aire, centrado en x y en el grosor
    const cy = this.pivote.y - box.min.y + ALTO;
    this.pivoteMundo = new THREE.Vector3(0, cy, 0);
    this.listo = true;
    this.pose();
  }

  geoGancho(gap) {
    this.gap = gap;
    // el hueco del ganchito arriba (por donde entra la cadenita)
    return new THREE.TorusGeometry(RJ, TJ, 12, 56, TAU - gap).rotateZ(Math.PI / 2 + gap / 2);
  }

  // matriz de la chapita: acostada (u = 0) o colgada y hamacándose (u = 1)
  matChapita(u, ang) {
    const colgada = M().makeTranslation(this.pivoteMundo.x, this.pivoteMundo.y, this.pivoteMundo.z)
      .multiply(M().makeRotationZ(ang)).multiply(M().makeTranslation(-this.pivote.x, -this.pivote.y, -this.pivote.z));
    if (u >= 1) return colgada;
    if (u <= 0) return ACOSTADA.clone();
    return mezcla(ACOSTADA, colgada, u, 8);
  }

  pose() {
    if (!this.listo) return;
    const t = this.tau;
    const hamaca = this.dir === 0 && this.puesto ? 0.07 * Math.sin(this.hora * 1.4) : 0;
    const uTag = tramo(t, T_TAG);
    const Mt = this.matChapita(uTag, hamaca);
    const m = this.v.model;
    Mt.decompose(m.position, m.quaternion, m.scale);
    m.updateMatrixWorld(true);
    // cada pieza: de la mesa a su lugar en la chapita (con un arco por el aire)
    this.piezas.forEach((p, i) => {
      const u = i === 0 ? tramo(t, T_GAN) : tramo(t, T_CAD);
      const fin = Mt.clone().multiply(this.hang[i]);
      p.matrix.copy(u <= 0 ? this.loose[i] : u >= 1 ? fin : mezcla(this.loose[i], fin, u, 14));
      p.matrixWorldNeedsUpdate = true;
    });
    // el ganchito se cierra al final (se abre al principio del camino de vuelta)
    const gap = 1.0 - 0.94 * tramo(t, T_CIE);
    if (Math.abs(gap - this.gap) > 0.01) { this.gancho.geometry.dispose(); this.gancho.geometry = this.geoGancho(gap); }
  }

  poner(puesto, animar = true) {
    this.puesto = !!puesto;
    if (!animar) { this.tau = this.puesto ? 1 : 0; this.dir = 0; this.pose(); return; }
    this.dir = this.puesto ? 1 : -1;
    this.encuadrar(true);
  }

  tick(dt) {
    this.hora += dt;
    if (this.dir) {
      this.tau = THREE.MathUtils.clamp(this.tau + (this.dir * dt) / DUR, 0, 1);
      if (this.tau === 0 || this.tau === 1) this.dir = 0;
    }
    if (this.cam) {
      const C = this.cam;
      C.t = Math.min(1, C.t + dt / 1.1);
      const e = ease(C.t);
      this.v.camera.position.lerpVectors(C.p0, C.p1, e);
      this.v.controls.target.lerpVectors(C.t0, C.t1, e);
      if (C.t >= 1) this.cam = null;
    }
    if (this.listo && (this.dir || this.puesto)) this.pose();
  }

  // encuadre que entra la chapita colgada y también todo apoyado en la mesa
  cajaTotal() {
    const b = new THREE.Box3();
    const local = this.cajaLocal();
    for (const u of [0, 1]) b.union(local.clone().applyMatrix4(this.matChapita(u, 0)));
    const pts = [...this.loose.map((m) => new THREE.Vector3().setFromMatrixPosition(m))];
    const Mh = this.matChapita(1, 0);
    for (const h of this.hang) pts.push(new THREE.Vector3().setFromMatrixPosition(Mh.clone().multiply(h)));
    for (const p of pts) b.expandByPoint(p);
    return b.expandByScalar(3);
  }

  encuadrar(suave) {
    if (!this.listo) return;
    const v = this.v;
    const p0 = v.camera.position.clone(), t0 = v.controls.target.clone();
    v.viewDir = new THREE.Vector3(-0.3, 0.45, 1);
    v.fit(this.cajaTotal());
    if (!suave) return;
    const p1 = v.camera.position.clone(), t1 = v.controls.target.clone();
    v.camera.position.copy(p0);
    v.controls.target.copy(t0);
    this.cam = { p0, p1, t0, t1, t: 0 };
  }
}

// mezcla de dos matrices (posición lineal + giro esférico), con un arco hacia arriba
function mezcla(A, B, u, arco) {
  const pa = new THREE.Vector3(), qa = new THREE.Quaternion(), sa = new THREE.Vector3();
  const pb = new THREE.Vector3(), qb = new THREE.Quaternion(), sb = new THREE.Vector3();
  A.decompose(pa, qa, sa);
  B.decompose(pb, qb, sb);
  const p = pa.lerp(pb, u);
  p.y += Math.sin(Math.PI * u) * arco;
  return comp(p, qa.slerp(qb, u));
}
