// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// La torta del visor del topper: bizcochuelo con cobertura, borde de crema, chorreado,
// granas y velitas, apoyada en la mesa (z = 0 es la mesa). El topper entra desde arriba y
// se clava; "Modo cumpleaños" prende las velas, tira confeti y gira la cámara.
import * as THREE from "three";

const TAU = Math.PI * 2;
const COLORES = [0xff5d8f, 0xffc93c, 0x5ad1e8, 0x8be36b, 0xb388ff, 0xff8a3d, 0xffffff];
const easeOutBack = (u) => { const c = 1.6; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
const rnd = (a, b) => a + Math.random() * (b - a);

export class Torta {
  constructor(viewer) {
    this.v = viewer;
    this.grupo = new THREE.Group();
    this.grupo.name = "TORTA";
    this.fiesta = false;
    this.entrada = null;            // animación del topper que baja y se clava
    this.t = 0;
    this.stats = { frames: 0, confeti: 0, apoyados: 0, rafagas: 0, llamas: 0 };
    this.mats = {
      bizcocho: new THREE.MeshStandardMaterial({ color: 0xfdf3e7, roughness: 0.82, metalness: 0 }),
      crema: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.7, metalness: 0 }),
      chorreado: new THREE.MeshStandardMaterial({ color: 0xf29bb8, roughness: 0.35, metalness: 0 }),
      plato: new THREE.MeshStandardMaterial({ color: 0xf3f0ea, roughness: 0.25, metalness: 0.15 }),
      vela: new THREE.MeshStandardMaterial({ color: 0x8fd3f4, roughness: 0.5, metalness: 0 }),
      mecha: new THREE.MeshStandardMaterial({ color: 0x2b2b2b, roughness: 0.9 }),
      llama: new THREE.MeshBasicMaterial({ color: 0xffb02e, transparent: true, opacity: 0.95 }),
      nucleo: new THREE.MeshBasicMaterial({ color: 0xfff6c8 }),
      grana: new THREE.MeshStandardMaterial({ roughness: 0.5, metalness: 0 }),
      confeti: new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.1, side: THREE.DoubleSide }),
    };
    viewer.tickers = viewer.tickers || [];
    viewer.tickers.push((dt) => this.tick(dt));
  }

  // ------------------------------------------------------------------ armado
  armar(ancho) {
    const g = this.grupo;
    g.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    g.clear();
    const R = Math.max(88, ancho * 0.58 + 12);       // un topper de 14 cm en una torta de ~20 cm
    const H = 78, plato = 7;
    this.R = R;
    this.arriba = plato + H + 3;          // la cobertura de arriba
    const M = this.mats;
    const add = (m, sombra = true) => { m.castShadow = m.receiveShadow = sombra; g.add(m); return m; };
    const cil = (r0, r1, h, mat, z, seg = 96) => {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r1, r0, h, seg), mat);
      m.rotation.x = Math.PI / 2;
      m.position.z = z + h / 2;
      return add(m);
    };
    cil(R + 34, R + 30, plato, M.plato, 0);                       // plato
    cil(R, R, H, M.bizcocho, plato);                              // bizcochuelo cubierto
    cil(R + 1.2, R + 1.2, 3, M.crema, plato + H);                 // cobertura de arriba
    // borde de crema (copitos) arriba y abajo
    const copo = new THREE.SphereGeometry(1, 14, 10);
    for (const [r, z, n, s] of [[R - 4, this.arriba, 40, 6.2], [R + 2, plato + 4, 46, 6.8]]) {
      const im = new THREE.InstancedMesh(copo, M.crema, n);
      const o = new THREE.Object3D();
      for (let i = 0; i < n; i++) {
        const a = (i / n) * TAU;
        o.position.set(r * Math.cos(a), r * Math.sin(a), z);
        o.scale.set(s, s, s * 0.85);
        o.rotation.set(0, 0, a);
        o.updateMatrix();
        im.setMatrixAt(i, o.matrix);
      }
      add(im);
    }
    // chorreado: gotas que bajan desde el borde de arriba
    const n = 34;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU + rnd(-0.04, 0.04);
      const largo = rnd(6, 26);
      const gota = new THREE.Mesh(new THREE.CapsuleGeometry(rnd(3.2, 4.6), largo, 6, 12), M.chorreado);
      gota.rotation.x = Math.PI / 2;
      gota.position.set((R + 0.6) * Math.cos(a), (R + 0.6) * Math.sin(a), plato + H + 1 - largo / 2);
      add(gota, false);
    }
    const tapa = new THREE.Mesh(new THREE.CylinderGeometry(R + 1.6, R + 1.6, 2.2, 96), M.chorreado);
    tapa.rotation.x = Math.PI / 2;
    tapa.position.z = plato + H + 1.4;
    add(tapa);
    // granas de colores arriba
    const ng = 260;
    const granas = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.9, 3.2, 3, 6), M.grana, ng);
    const o = new THREE.Object3D();
    const c = new THREE.Color();
    for (let i = 0; i < ng; i++) {
      const r = Math.sqrt(Math.random()) * (R - 14), a = Math.random() * TAU;
      o.position.set(r * Math.cos(a), r * Math.sin(a), this.arriba + 0.8);
      o.rotation.set(Math.PI / 2, Math.random() * TAU, 0);
      o.updateMatrix();
      granas.setMatrixAt(i, o.matrix);
      granas.setColorAt(i, c.setHex(COLORES[i % COLORES.length]));
    }
    add(granas, false);
    // velitas atrás (no tapan el texto)
    this.llamas = [];
    for (const a of [0.08, 0.2, 0.8, 0.92].map((k) => Math.PI * k)) {   // atrás, en las esquinas: no tapan el texto
      const x = (R - 16) * Math.cos(a), y = (R - 16) * Math.sin(a) + 6;
      const vela = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 38, 18), M.vela);
      vela.rotation.x = Math.PI / 2;
      vela.position.set(x, y, this.arriba + 19);
      add(vela);
      const mecha = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4, 6), M.mecha);
      mecha.rotation.x = Math.PI / 2;
      mecha.position.set(x, y, this.arriba + 40);
      add(mecha, false);
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
      g.add(llama);
      this.llamas.push(llama);
    }
    this.armarConfeti();
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

  // ------------------------------------------------------------------ topper en la torta
  clavar(pose, largo, animar = true) {
    pose.updateMatrixWorld(true);
    const m = this.v.model;
    const inv = m.matrixWorld.clone().invert();
    const b = new THREE.Box3().setFromObject(pose);
    const zmin = b.min.clone().applyMatrix4(inv).z - pose.position.z;
    this.zFinal = this.arriba - zmin - 0.6 * largo;           // los palitos entran un 60 %
    this.pose = pose;
    if (animar) this.entrada = { t: 0, dur: 1.15, desde: this.zFinal + 160 };
    else pose.position.z = this.zFinal;
    if (!animar) this.entrada = null;
    else pose.position.z = this.entrada.desde;
  }

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
      if (this.pose) this.entrada = { t: 0, dur: 1.15, desde: this.zFinal + 160 };
    } else {
      this.vivos = 0;
      this.confeti.count = 0;
    }
  }

  // ráfaga de un cañón al costado de la torta
  rafaga(izq) {
    const n = 220;
    const R = this.R;
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
    const q = new THREE.Quaternion(), e = new THREE.Vector3();
    const P = this.p, Vl = this.vel, R = this.R;
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
        const r = Math.hypot(P[k], P[k + 1]);
        const piso = r < R + 4 ? this.arriba + 1.2 : (r < R + 34 ? 7.5 : 0.6);
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
      o.scale.setScalar(1);
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
    if (this.entrada && this.pose) {
      const E = this.entrada;
      E.t += dt;
      const u = Math.min(1, E.t / E.dur);
      this.pose.position.z = E.desde + (this.zFinal - E.desde) * easeOutBack(u);
      if (u >= 1) { this.pose.position.z = this.zFinal; this.entrada = null; }
    }
    if (this.fiesta) {
      // confeti que sigue cayendo desde arriba (hasta llenar)
      this.lluvia += dt * 26;
      while (this.lluvia >= 1) {
        this.lluvia -= 1;
        const i = this.nuevo();
        if (i < 0) break;
        const r = Math.sqrt(Math.random()) * (this.R + 60), a = Math.random() * TAU;
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
    return { fiesta: this.fiesta, confeti: this.vivos || 0, apoyados: this.vivos ? this.stats.apoyados : 0,
      rafagas: this.stats.rafagas, llamas: this.fiesta ? (this.llamas || []).filter((l) => l.visible).length : 0,
      entrando: !!this.entrada, arriba: this.arriba || 0, radio: this.R || 0,
      topperZ: this.pose ? +this.pose.position.z.toFixed(2) : null, zFinal: this.zFinal ?? null };
  }
}
