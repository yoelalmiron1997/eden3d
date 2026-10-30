// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Cebado del mate: la yerba cae adentro del inserto, el mate se inclina y arma la
// montañita, se vuelve a parar, entra el agua caliente por el costado bajo (con el
// agua interactiva del plato de las macetas: gotas, olas y ondas al tocarla), entra la
// bombilla y sale vapor. También "Separar": el inserto sale del mate con todo adentro.
import * as THREE from "three";
import { Water } from "./water.js";

const TAU = Math.PI * 2;
const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
const seg = (t, a, b) => ease((t - a) / (b - a));
// fases (segundos): llenar, asentar, inclinar, quieto, enderezar, cebar, bombilla
const F = { llenar: [0, 2.8], inclinar: [3.2, 4.4], enderezar: [5.0, 6.4], cebar: [6.6, 10.2],
  bombilla: [10.4, 11.8], fin: 12.0 };
const FASES = [["llenar", 3.2], ["montañita", 6.4], ["cebar", 10.3], ["bombilla", 12.0], ["listo", 1e9]];

function ruido(i) {                         // hash determinista 0..1
  const s = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
}

export class Cebado {
  constructor(viewer) {
    this.v = viewer;
    this.flags = { yerba: false, agua: false, bombilla: true, vapor: true };
    this.alfa = 40;                         // ángulo de la montañita (°)
    this.t = F.fin;                         // fin de la animación = mate cebado
    this.playing = false;
    this.explode = 0;
    this.loop = null;
    this.group = null;
    this.stats = { frames: 0, cebados: 0, gotas: 0 };
    viewer.mats.YERBA = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0,
      side: THREE.DoubleSide, envMapIntensity: 0.6 });
    viewer.mats.BOMBILLA = new THREE.MeshStandardMaterial({ color: 0xeceef0, roughness: 0.28, metalness: 0.75,
      envMapIntensity: 1.6 });
    // el agua del mate (verdosa, por la yerba) y el chorro de la pava (transparente)
    viewer.mats.AGUA_MATE = new THREE.MeshPhysicalMaterial({ color: 0x8f9a3a, roughness: 0.06, metalness: 0,
      transparent: true, opacity: 0.78, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 1.2 });
    viewer.mats.CHORRO = new THREE.MeshPhysicalMaterial({ color: 0xdff1f7, roughness: 0.04, metalness: 0,
      transparent: true, opacity: 0.55, envMapIntensity: 1.4 });
    this.matGrano = new THREE.PointsMaterial({ color: 0x6c7a2c, size: 1.5, sizeAttenuation: true });
    this.texVapor = this.texturaVapor();
    viewer.tickers = viewer.tickers || [];
    viewer.tickers.push((dt) => this.tick(dt));
  }

  get activo() { return this.flags.yerba || this.flags.agua || this.playing; }

  // ------------------------------------------------------------------ armado
  // cav: {z, r, fondo, boca} del motor (summary.cavidad); se llama después de cada cálculo
  montar(cav) {
    this.desmontar();
    if (!cav || !cav.z || cav.z.length < 3) return;
    this.cav = cav;
    const v = this.v;
    this.q0 = v.model.quaternion.clone();
    this.p0 = v.model.position.clone();
    const pot = v.model.getObjectByName("MACETA");
    if (pot) {
      if (!pot.geometry.boundingBox) pot.geometry.computeBoundingBox();
      this.Rpie = pot.geometry.boundingBox.max.x * 0.8;
    }
    this.group = new THREE.Group();
    this.group.name = "CEBADO";
    this.R = this.radio(this.nivelYerba());
    this.armarYerba();
    this.armarGranos();
    this.armarAgua();
    this.armarChorro();
    this.armarBombilla();
    this.armarVapor();
    this.actualizar(true);
    this.visibilidad();
    this.aplicarSeparar();
  }

  desmontar() {
    if (this.group) {
      this.v.model.remove(this.group);
      this.group.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    }
    if (this.water && this.v.water === this.water) this.v.water = null;
    if (this.water) this.water.dispose();
    this.group = null;
    this.water = null;
    if (this.q0) { this.v.model.quaternion.copy(this.q0); this.v.model.position.copy(this.p0); }
  }

  radio(z) {                                // radio libre del inserto a la altura z
    const { z: zs, r } = this.cav;
    if (z <= zs[0]) return r[0];
    if (z >= zs[zs.length - 1]) return r[r.length - 1];
    const i = Math.min(zs.length - 2, Math.floor((z - zs[0]) / (zs[1] - zs[0])));
    const u = (z - zs[i]) / (zs[i + 1] - zs[i]);
    return r[i] * (1 - u) + r[i + 1] * u;
  }

  nivelYerba() { const c = this.cav; return c.fondo + 0.6 * (c.boca - c.fondo); }

  armarYerba() {
    const NR = 34, NS = 128;
    this.NR = NR; this.NS = NS;
    const n = 1 + NR * NS;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const idx = [];
    for (let s = 0; s < NS; s++) {
      idx.push(0, 1 + s, 1 + ((s + 1) % NS));
      for (let r = 0; r < NR - 1; r++) {
        const a = 1 + r * NS + s, b = 1 + r * NS + ((s + 1) % NS), c = a + NS, d = b + NS;
        idx.push(a, c, b, b, c, d);
      }
    }
    g.setIndex(idx);
    // color base de cada grano: verde yerba con motas claras (palo) y oscuras (hoja)
    this.colBase = new Float32Array(n * 3);
    this.rugo = new Float32Array(n);
    const verde = new THREE.Color(0x7a8a35), claro = new THREE.Color(0xc4b77a), osc = new THREE.Color(0x4d5a1e);
    const c = new THREE.Color();
    for (let i = 0; i < n; i++) {
      const k = ruido(i);
      c.copy(verde).offsetHSL((ruido(i + 7) - 0.5) * 0.04, 0, (ruido(i + 3) - 0.5) * 0.12);
      if (k > 0.93) c.copy(claro);
      else if (k < 0.12) c.lerp(osc, 0.7);
      this.colBase.set([c.r, c.g, c.b], i * 3);
      this.rugo[i] = (ruido(i + 11) - 0.5) * 1.1;
    }
    // costado (contra la pared del inserto) y fondo, para el corte
    const NZ = 18;
    const lado = new THREE.BufferGeometry();
    lado.setAttribute("position", new THREE.BufferAttribute(new Float32Array(NS * (NZ + 1) * 3), 3));
    const lidx = [];
    for (let j = 0; j < NZ; j++) {
      for (let s = 0; s < NS; s++) {
        const a = j * NS + s, b = j * NS + ((s + 1) % NS);
        lidx.push(a, b, a + NS, b, b + NS, a + NS);
      }
    }
    lado.setIndex(lidx);
    const cl = new Float32Array(NS * (NZ + 1) * 3);
    for (let i = 0; i < cl.length / 3; i++) cl.set([0.36 + 0.06 * ruido(i), 0.42 + 0.06 * ruido(i + 5), 0.15], i * 3);
    lado.setAttribute("color", new THREE.BufferAttribute(cl, 3));
    this.NZ = NZ;
    this.yerba = new THREE.Mesh(g, this.v.mats.YERBA);
    this.yerba.name = "YERBA";
    this.yerba.castShadow = this.yerba.receiveShadow = true;
    this.lado = new THREE.Mesh(lado, this.v.mats.YERBA);
    this.lado.name = "YERBA_LADO";
    this.group.add(this.yerba, this.lado);
  }

  armarGranos() {
    const N = 900;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
    this.granos = new THREE.Points(g, this.matGrano);
    this.granos.name = "GRANOS";
    this.granos.frustumCulled = false;
    this.vel = new Float32Array(N);
    this.N = N;
    for (let i = 0; i < N; i++) this.soltarGrano(i, true);
    this.group.add(this.granos);
  }

  soltarGrano(i, inicio) {
    const p = this.granos.geometry.attributes.position.array;
    const c = this.cav;
    const R = this.radio(c.boca) * 0.55;
    const a = Math.random() * TAU, r = Math.sqrt(Math.random()) * R;
    p[i * 3] = r * Math.cos(a) + 4;
    p[i * 3 + 1] = r * Math.sin(a);
    p[i * 3 + 2] = c.boca + 10 + Math.random() * (inicio ? 140 : 50);
    this.vel[i] = 0;
  }

  armarAgua() {
    const c = this.cav;
    const W = this.nivelAgua();
    const zf = c.fondo;
    const r0 = this.radio(zf) - 0.2, r1 = this.radio(W) - 0.2;
    const A = { dish_inner_r0_mm: r0 + 0.15, dish_flare_deg: THREE.MathUtils.radToDeg(Math.atan((r1 - r0) / Math.max(1, W - zf))),
      dish_floor_mm: zf - 0.8, water_min_wet_level_mm: W - 6, water_level_max_mm: W };
    this.water = new Water(this.v.mats.AGUA_MATE, A, "max");
    this.water.side.visible = false;            // la pared la pone el inserto (es escalonado)
    this.water.waveAmp = 0.25;
    this.water.slosh = 0.15;
    this.water.autoDrops = false;
    this.water.group.name = "AGUA_MATE";
    this.group.add(this.water.group);
    this.v.water = this.water;                // el visor la anima y la deja tocar (gotas)
  }

  nivelAgua() {
    const c = this.cav;
    const s = Math.tan(THREE.MathUtils.degToRad(this.alfa));
    return Math.min(c.boca - 4, Math.max(c.fondo + 6, this.nivelYerba() - 0.12 * s * this.R));
  }

  armarChorro() {
    const g = new THREE.TubeGeometry(this.curvaChorro(), 40, 1.4, 10, false);
    this.chorro = new THREE.Mesh(g, this.v.mats.CHORRO);
    this.chorro.name = "CHORRO";
    this.chorro.visible = false;
    this.group.add(this.chorro);
  }

  curvaChorro() {
    const c = this.cav, R = this.R;
    this.impacto = new THREE.Vector3(-0.5 * R, 0, this.nivelAgua());
    const pico = new THREE.Vector3(-R - 38, 0, c.boca + 62);
    return new THREE.QuadraticBezierCurve3(pico, new THREE.Vector3(-R - 6, 0, c.boca + 58), this.impacto.clone());
  }

  armarBombilla() {
    const c = this.cav, R = this.R;
    const b = new THREE.Group();
    b.name = "BOMBILLA";
    // de la cuchara (abajo, del lado del agua) hasta el pico (afuera del mate)
    const abajo = new THREE.Vector3(-0.3 * R, 0, c.fondo + 7);
    const boca = new THREE.Vector3(-0.78 * R, 0, c.boca);
    const dir = boca.clone().sub(abajo).normalize();
    const largo = 168;
    const recta = abajo.clone().addScaledVector(dir, largo - 26);
    const codo = recta.clone().add(new THREE.Vector3(-9, 0, 12));
    const pico = codo.clone().add(new THREE.Vector3(-12, 0, 6));
    const curva = new THREE.CatmullRomCurve3([abajo.clone().addScaledVector(dir, 10), recta, codo, pico], false, "centripetal");
    const tubo = new THREE.Mesh(new THREE.TubeGeometry(curva, 80, 3.2, 14, false), this.v.mats.BOMBILLA);
    const cuchara = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), this.v.mats.BOMBILLA);
    cuchara.scale.set(7.5, 2.6, 12);
    cuchara.position.copy(abajo.clone().addScaledVector(dir, 4));
    cuchara.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    const boquilla = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 10), this.v.mats.BOMBILLA);
    boquilla.scale.set(4.5, 2.2, 4.5);
    boquilla.position.copy(pico);
    for (const m of [tubo, cuchara, boquilla]) { m.castShadow = true; b.add(m); }
    this.dirBombilla = dir;
    this.bombilla = b;
    this.group.add(b);
  }

  texturaVapor() {
    const cv = document.createElement("canvas");
    cv.width = cv.height = 64;
    const g = cv.getContext("2d");
    const grd = g.createRadialGradient(32, 32, 2, 32, 32, 30);
    grd.addColorStop(0, "rgba(255,255,255,0.9)");
    grd.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grd;
    g.fillRect(0, 0, 64, 64);
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }

  armarVapor() {
    this.vapor = new THREE.Group();
    this.vapor.name = "VAPOR";
    this.bocanadas = [];
    for (let i = 0; i < 22; i++) {
      const m = new THREE.SpriteMaterial({ map: this.texVapor, color: 0xffffff, transparent: true, opacity: 0, depthWrite: false });
      const s = new THREE.Sprite(m);
      s.userData = { vida: Math.random() * 3.2, x: 0, y: 0 };
      this.vapor.add(s);
      this.bocanadas.push(s);
    }
    this.group.add(this.vapor);
  }

  // ------------------------------------------------------------------ estado en el tiempo t
  estado(t) {
    const c = this.cav;
    const llenar = seg(t, ...F.llenar);
    const sube = seg(t, ...F.inclinar), baja = seg(t, ...F.enderezar);
    const tiltMax = Math.max(45, this.alfa + 5);
    const tilt = tiltMax * (sube - baja);                         // grados del mate
    const alfa = this.alfa;
    const pend = t >= F.inclinar[1] ? alfa : Math.min(alfa, tiltMax * sube);
    const cebar = seg(t, ...F.cebar);
    return {
      L: c.fondo + llenar * (this.nivelYerba() - c.fondo),
      monton: 7 * llenar * (1 - seg(t, F.llenar[1], F.inclinar[0] + 0.6)),
      tilt, s: Math.tan(THREE.MathUtils.degToRad(pend)),
      cebar, crater: 5 * cebar,
      chorro: t > F.cebar[0] && t < F.cebar[1] - 0.3,
      bombilla: seg(t, ...F.bombilla),
      vapor: cebar,
      llenando: t < F.llenar[1],
    };
  }

  fase() {
    if (!this.cav) return "";
    for (const [n, hasta] of FASES) if (this.t < hasta) return n;
    return "listo";
  }

  // ------------------------------------------------------------------ cuadro
  tick(dt) {
    if (!this.group) return;
    this.stats.frames++;
    if (this.playing) {
      this.t += dt;
      if (this.t >= F.fin) { this.t = F.fin; this.playing = false; this.stats.cebados++; this.visibilidad(); }
      this.actualizar(false, dt);
    } else if (this.activo && this.flags.agua) {
      this.mojar();                                                // la yerba se moja si sube el agua
    }
    if (this.loop) this.tickLoop(dt);
    if (this.activo && this.flags.vapor) this.tickVapor(dt);
  }

  actualizar(forzar, dt = 0) {
    const E = this.estado(this.t);
    this.E = E;
    this.alturas(E);
    this.mojar();
    // granos cayendo mientras se llena
    this.granos.visible = this.flags.yerba && E.llenando && this.playing;
    if (this.granos.visible) {
      const p = this.granos.geometry.attributes.position.array;
      for (let i = 0; i < this.N; i++) {
        this.vel[i] += 900 * dt;
        p[i * 3 + 2] -= this.vel[i] * dt;
        if (p[i * 3 + 2] < E.L + E.monton * 0.6) this.soltarGrano(i, false);
      }
      this.granos.geometry.attributes.position.needsUpdate = true;
    }
    // el mate se inclina sobre el borde del pie para armar la montañita
    this.inclinar(E.tilt);
    // agua: sube cuando se ceba
    const W = this.water;
    if (W) {
      const ver = !!this.group?.parent && this.flags.agua && E.cebar > 0;
      if (ver !== W.group.visible) { W.group.visible = ver; this.v.water = ver ? W : null; }
      W.target = E.cebar > 0 ? this.cav.fondo + E.cebar * (this.nivelAgua() - this.cav.fondo) : this.cav.fondo;
      if (forzar || !this.playing) W.level = W.target;
      if (E.chorro && this.flags.agua) {
        // el chorro agita el agua donde cae (ondas), sin gotas sueltas
        W.impulse(this.impacto.x + (Math.random() - 0.5) * 3, this.impacto.y + (Math.random() - 0.5) * 3, 0.5 * dt * 60, 2.6);
      }
    }
    this.chorro.visible = this.flags.agua && E.chorro;
    if (this.chorro.visible) this.chorro.scale.set(1, 1 + 0.06 * Math.sin(this.t * 40), 1);
    // bombilla que entra desde arriba
    const k = E.bombilla;
    this.bombilla.visible = this.flags.bombilla && k > 0.001 && (this.flags.yerba || this.flags.agua);
    this.bombilla.position.copy(this.dirBombilla).multiplyScalar((1 - k) * 90);
  }

  alturas(E) {
    const c = this.cav, NR = this.NR, NS = this.NS;
    const pos = this.yerba.geometry.attributes.position.array;
    const zmin = c.fondo + 0.5, zmax = c.boca - 2.5;
    const crX = -0.5 * this.R;
    let i = 0;
    const altura = (x, y, j) => {
      const rho2 = (x * x + y * y) / (this.R * this.R);
      let h = E.L + E.s * x + E.monton * Math.max(0, 1 - rho2) + (j >= 0 ? this.rugo[j] * Math.min(1, (E.L - c.fondo) / 8) : 0);
      h -= E.crater * Math.exp(-((x - crX) ** 2 + y * y) / 90);
      return Math.min(zmax, Math.max(zmin, h));
    };
    pos[0] = 0; pos[1] = 0; pos[2] = altura(0, 0, 0);
    this.hBorde = new Float32Array(NS);
    for (let r = 0; r < NR; r++) {
      const rho = (r + 1) / NR;
      for (let s = 0; s < NS; s++) {
        const a = (s / NS) * TAU, ca = Math.cos(a), sa = Math.sin(a);
        i = 1 + r * NS + s;
        let rad = rho * this.R, h = E.L;
        for (let it = 0; it < 2; it++) {                   // el borde sigue la pared escalonada
          h = altura(rad * ca, rad * sa, i);
          rad = rho * (this.radio(h) - 0.3);
        }
        pos[i * 3] = rad * ca; pos[i * 3 + 1] = rad * sa; pos[i * 3 + 2] = h;
        if (r === NR - 1) this.hBorde[s] = h;
      }
    }
    this.yerba.geometry.attributes.position.needsUpdate = true;
    this.yerba.geometry.computeVertexNormals();
    // costado contra la pared, del fondo hasta el borde de la superficie
    const lp = this.lado.geometry.attributes.position.array;
    for (let j = 0; j <= this.NZ; j++) {
      for (let s = 0; s < NS; s++) {
        const a = (s / NS) * TAU;
        const z = c.fondo + (this.hBorde[s] - c.fondo) * (j / this.NZ);
        const rad = this.radio(z) - 0.3;
        lp.set([rad * Math.cos(a), rad * Math.sin(a), z], (j * NS + s) * 3);
      }
    }
    this.lado.geometry.attributes.position.needsUpdate = true;
    this.lado.geometry.computeVertexNormals();
    this.yerba.visible = this.lado.visible = this.flags.yerba && E.L > c.fondo + 0.6;
  }

  mojar() {                                    // la yerba bajo el agua (y cerca) queda más oscura
    const pos = this.yerba.geometry.attributes.position.array;
    const col = this.yerba.geometry.attributes.color.array;
    const nivel = this.flags.agua && this.water && this.E && this.E.cebar > 0 ? this.water.level : -1e9;
    if (this._ultimo !== undefined && Math.abs(this._ultimo - nivel) < 0.05 && !this.playing) return;
    this._ultimo = nivel;
    for (let i = 0, n = col.length / 3; i < n; i++) {
      const d = nivel + 1.5 - pos[i * 3 + 2];
      const k = d <= 0 ? 1 : Math.max(0.55, 1 - d * 0.12);
      col[i * 3] = this.colBase[i * 3] * k;
      col[i * 3 + 1] = this.colBase[i * 3 + 1] * k;
      col[i * 3 + 2] = this.colBase[i * 3 + 2] * k;
    }
    this.yerba.geometry.attributes.color.needsUpdate = true;
  }

  inclinar(grados) {
    const m = this.v.model;
    if (!this.q0) return;
    if (Math.abs(grados) < 1e-3) { m.quaternion.copy(this.q0); m.position.copy(this.p0); this.stats.tilt = 0; return; }
    const e = new THREE.Vector3(this.Rpie || 30, 0, 0);              // borde del pie (lado de la montañita)
    const qt = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(grados));
    const q = this.q0.clone().multiply(qt);
    m.quaternion.copy(q);
    m.position.copy(this.p0).add(e.clone().applyQuaternion(this.q0)).sub(e.clone().applyQuaternion(q));
    this.stats.tilt = grados;
  }

  tickVapor(dt) {
    const on = this.flags.vapor && this.flags.agua && this.E && this.E.vapor > 0.3 && !this.v.slicer.on;
    this.vapor.visible = on;
    if (!on) return;
    const W = this.water;
    for (const s of this.bocanadas) {
      const u = s.userData;
      u.vida += dt;
      if (u.vida > 3.2) {
        u.vida = 0;
        const a = Math.random() * TAU, r = Math.random() * this.R * 0.6;
        u.x = -0.35 * this.R + r * Math.cos(a) * 0.7;
        u.y = r * Math.sin(a);
      }
      const k = u.vida / 3.2;
      s.position.set(u.x + Math.sin(u.vida * 1.7 + u.y) * 4 * k, u.y + Math.cos(u.vida * 1.3) * 3 * k, W.level + 2 + k * 55);
      const tam = 8 + k * 22;
      s.scale.set(tam, tam, 1);
      s.material.opacity = 0.22 * Math.sin(Math.PI * k) * this.E.vapor;
    }
  }

  // ------------------------------------------------------------------ controles
  visibilidad() {
    if (!this.group) return;
    const on = this.activo && !this.v.slicer.on;
    if (on && !this.group.parent) this.v.model.add(this.group);
    if (!on && this.group.parent) this.v.model.remove(this.group);
    if (this.water) {
      this.water.group.visible = on && this.flags.agua && (!this.E || this.E.cebar > 0);
      this.v.water = this.water.group.visible ? this.water : null;
    }
    this.actualizar(!this.playing);
  }

  play() {
    if (!this.group) return;
    this.flags.yerba = this.flags.agua = true;
    this.t = 0;
    this.playing = true;
    if (this.water) { this.water.level = this.cav.fondo; this.water.group.visible = true; this.v.water = this.water; }
    this.visibilidad();
  }

  setFlag(k, on) {
    this.flags[k] = on;
    if (!this.playing) this.t = F.fin;
    this.visibilidad();
  }

  setAlfa(a) {
    this.alfa = a;
    if (!this.group) return;
    this.armarDeNuevo();
  }

  armarDeNuevo() {                             // el nivel del agua depende de la montañita
    const cav = this.cav, t = this.t, playing = this.playing;
    this.montar(cav);
    this.t = t;
    this.playing = playing;
    this.visibilidad();
  }

  gota() { if (this.water && this.water.group.visible) { this.water.randomDrop(1.8); this.stats.gotas++; } }
  olas() { if (this.water && this.water.group.visible) this.water.makeWaves(); }

  // Separar: el inserto sale del mate con la yerba, el agua y la bombilla adentro
  setSeparar(k) {
    this.explode = Math.max(0, Math.min(1, k));
    this.aplicarSeparar();
  }

  aplicarSeparar() {
    const ins = this.v.model.getObjectByName("INSERTO");
    const off = this.cav ? this.explode * (this.cav.boca - this.cav.fondo + 30) : 0;
    if (ins) ins.position.z = off;
    if (this.group) this.group.position.z = off;
    this.stats.separar = off;
  }

  setLoop(on) {
    this.loop = on ? { t: 0 } : null;
    this.v.controls.autoRotate = on;
    this.v.controls.autoRotateSpeed = 1.6;
  }

  tickLoop(dt) {
    const L = this.loop;
    L.t += dt;
    const ph = [0.8, 1.8, 2.6, 1.8];
    const T = ph.reduce((a, b) => a + b, 0);
    let t = L.t % T, k = 0;
    if (t < ph[0]) k = 0;
    else if ((t -= ph[0]) < ph[1]) k = ease(t / ph[1]);
    else if ((t -= ph[1]) < ph[2]) k = 1;
    else k = 1 - ease((t - ph[2]) / ph[3]);
    this.setSeparar(k);
    this.stats.loopCycles = Math.floor(L.t / T);
    if (this.onSeparar) this.onSeparar(k);
  }

  info() {
    return { fase: this.fase(), t: +this.t.toFixed(2), playing: this.playing, flags: { ...this.flags },
      alfa: this.alfa, nivelAgua: this.water ? +this.water.level.toFixed(2) : null,
      nivelYerba: this.cav ? +this.nivelYerba().toFixed(2) : null, separar: this.explode,
      enEscena: !!(this.group && this.group.parent), tilt: this.stats.tilt || 0,
      bombilla: !!(this.bombilla && this.bombilla.visible), vapor: !!(this.vapor && this.vapor.visible),
      cebados: this.stats.cebados, gotas: this.stats.gotas };
  }
}
