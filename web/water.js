// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Agua del plato de autorriego: olas + simulación de ondas (ecuación de onda en
// una grilla) para que se pueda tocar: gotas que caen, salpicaduras, lluvia y estela.
import * as THREE from "three";

const G = 2600;          // gravedad "de cámara lenta" (mm/s²) para que la gota se vea caer
const MAX_FALL = 24;
const MAX_SPLASH = 96;

export class Water {
  // A: datos del ensamble del motor (dish_inner_r0_mm, dish_flare_deg, dish_floor_mm, niveles)
  constructor(mat, A, which = "max") {
    this.A = A;
    this.mat = mat;
    this.NR = 30;
    this.NS = 112;
    this.t = 0;
    this.floor = A.dish_floor_mm + 0.8;
    this.levelMin = A.water_min_wet_level_mm;
    this.levelMax = A.water_level_max_mm;
    this.target = which === "min" ? this.levelMin : this.levelMax;
    this.level = this.floor;
    this.tan = Math.tan(THREE.MathUtils.degToRad(A.dish_flare_deg || 6));
    this.Rmax = this.radiusAt(this.levelMax) + 1;
    this.waveAmp = 0.45;            // olas de fondo (mm)
    this.slosh = 0.35;              // vaivén del plato (mm en el borde)
    this.rain = false;
    this.rainNext = 0;
    this.nextDrop = 0.6;
    this.autoDrops = true;
    this.stats = { drops: 0, impacts: 0, splashes: 0, energy: 0 };

    this.group = new THREE.Group();
    this.group.name = "AGUA";
    this.buildSurface();
    this.buildSim();
    this.buildDrops();
  }

  radiusAt(z) {
    return this.A.dish_inner_r0_mm - 0.15 + (z - this.A.dish_floor_mm) * this.tan;
  }

  // ------------------------------------------------------------------ mallas
  buildSurface() {
    const { NR, NS } = this;
    const top = new THREE.BufferGeometry();
    top.setAttribute("position", new THREE.BufferAttribute(new Float32Array((NR * NS + 1) * 3), 3));
    const idx = [];
    for (let s = 0; s < NS; s++) {
      idx.push(0, 1 + s, 1 + ((s + 1) % NS));
      for (let r = 0; r < NR - 1; r++) {
        const a = 1 + r * NS + s, b = 1 + r * NS + ((s + 1) % NS), c = a + NS, d = b + NS;
        idx.push(a, c, b, b, c, d);
      }
    }
    top.setIndex(idx);
    const side = new THREE.BufferGeometry();
    side.setAttribute("position", new THREE.BufferAttribute(new Float32Array(NS * 2 * 3), 3));
    const sidx = [];
    for (let s = 0; s < NS; s++) {
      const a = s, b = (s + 1) % NS;
      sidx.push(a, b, NS + b, a, NS + b, NS + a);
    }
    side.setIndex(sidx);
    // la superficie cambia en cada cuadro: esfera fija y generosa para el raycast
    const sph = new THREE.Sphere(new THREE.Vector3(0, 0, (this.floor + this.levelMax) / 2), this.Rmax + 12);
    top.boundingSphere = sph;
    side.boundingSphere = sph.clone();
    const R = this.Rmax + 12;
    top.boundingBox = new THREE.Box3(new THREE.Vector3(-R, -R, this.floor - 15), new THREE.Vector3(R, R, this.levelMax + 25));
    side.boundingBox = top.boundingBox.clone();
    this.geoms = [top, side];
    this.top = new THREE.Mesh(top, this.mat);
    this.side = new THREE.Mesh(side, this.mat);
    this.top.name = "AGUA_SUPERFICIE";
    this.top.renderOrder = this.side.renderOrder = 3;
    this.group.add(this.top, this.side);
  }

  buildSim() {
    const N = (this.N = 120);
    this.cell = (2 * this.Rmax) / N;
    this.h = new Float32Array(N * N);
    this.p = new Float32Array(N * N);
    this.mask = new Uint8Array(N * N);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const x = (i + 0.5) * this.cell - this.Rmax, y = (j + 0.5) * this.cell - this.Rmax;
      this.mask[j * N + i] = Math.hypot(x, y) <= this.Rmax && i > 0 && j > 0 && i < N - 1 && j < N - 1 ? 1 : 0;
    }
    this.simAcc = 0;
  }

  buildDrops() {
    const geo = new THREE.SphereGeometry(1, 14, 10);
    this.fallMesh = new THREE.InstancedMesh(geo, this.mat, MAX_FALL);
    this.splashMesh = new THREE.InstancedMesh(geo, this.mat, MAX_SPLASH);
    this.fallMesh.name = "GOTAS";
    this.splashMesh.name = "SALPICADURAS";
    this.fallMesh.count = 0;
    this.splashMesh.count = 0;
    this.fallMesh.frustumCulled = this.splashMesh.frustumCulled = false;
    this.fallMesh.renderOrder = this.splashMesh.renderOrder = 4;
    this.falling = [];
    this.splashes = [];
    this.group.add(this.fallMesh, this.splashMesh);
    this._m = new THREE.Matrix4();
  }

  dispose() {
    for (const g of this.geoms) g.dispose();
    this.fallMesh.geometry.dispose();
  }

  // ------------------------------------------------------------------ interacción
  // Gota que cae desde arriba sobre (x, y) del plato (coordenadas del motor, mm).
  dropAt(x, y, size = 1.7) {
    const R = this.radiusAt(this.level) - 1.5;
    const d = Math.hypot(x, y);
    if (d > R) { x *= R / d; y *= R / d; }
    if (this.falling.length >= MAX_FALL) this.falling.shift();
    this.falling.push({ x, y, z: this.level + 70 + Math.random() * 25, v: 0, r: size });
    this.stats.drops++;
  }

  randomDrop(size) {
    const a = Math.random() * Math.PI * 2, d = Math.sqrt(Math.random()) * this.radiusAt(this.level) * 0.85;
    this.dropAt(d * Math.cos(a), d * Math.sin(a), size);
  }

  // perturbación directa de la superficie (estela del puntero, impacto)
  impulse(x, y, amount, radius = 2.2) {
    const { N, cell, Rmax, h, mask } = this;
    const ci = (x + Rmax) / cell - 0.5, cj = (y + Rmax) / cell - 0.5;
    const rc = Math.ceil((radius * 2.5) / cell);
    for (let j = Math.max(1, Math.floor(cj - rc)); j <= Math.min(N - 2, Math.ceil(cj + rc)); j++) {
      for (let i = Math.max(1, Math.floor(ci - rc)); i <= Math.min(N - 2, Math.ceil(ci + rc)); i++) {
        const k = j * N + i;
        if (!mask[k]) continue;
        const dx = (i - ci) * cell, dy = (j - cj) * cell;
        h[k] -= amount * Math.exp(-(dx * dx + dy * dy) / (radius * radius));
      }
    }
  }

  // olas fuertes por un rato (botón "Hacer olas")
  makeWaves() {
    this.slosh = 2.4;
    this.waveBoost = 1;
  }

  // ------------------------------------------------------------------ simulación
  stepSim() {
    const { N, mask } = this;
    const h = this.h, p = this.p;
    const c = 0.42, damp = 0.9935;
    let e = 0;
    for (let j = 1; j < N - 1; j++) {
      for (let i = 1; i < N - 1; i++) {
        const k = j * N + i;
        if (!mask[k]) continue;
        const hc = h[k];
        // borde = pared (la onda rebota): el vecino de afuera copia al centro
        const l = mask[k - 1] ? h[k - 1] : hc, r = mask[k + 1] ? h[k + 1] : hc;
        const u = mask[k - N] ? h[k - N] : hc, d = mask[k + N] ? h[k + N] : hc;
        const v = (2 * hc - p[k] + c * (l + r + u + d - 4 * hc)) * damp;
        p[k] = v;
        e += v * v;
      }
    }
    this.h = p;
    this.p = h;
    this.stats.energy = e;
  }

  sample(x, y) {
    const { N, cell, Rmax, h } = this;
    const gx = (x + Rmax) / cell - 0.5, gy = (y + Rmax) / cell - 0.5;
    const i = Math.max(0, Math.min(N - 2, Math.floor(gx))), j = Math.max(0, Math.min(N - 2, Math.floor(gy)));
    const fx = Math.min(1, Math.max(0, gx - i)), fy = Math.min(1, Math.max(0, gy - j));
    const k = j * N + i;
    return (h[k] * (1 - fx) + h[k + 1] * fx) * (1 - fy) + (h[k + N] * (1 - fx) + h[k + N + 1] * fx) * fy;
  }

  // olas de fondo: tres trenes de ondas cruzados + vaivén del plato
  waves(x, y, t, R) {
    const A = this.waveAmp * (1 + (this.waveBoost || 0));
    const w = 0.5 * Math.sin(0.34 * x + 0.12 * y - 2.3 * t) +
      0.3 * Math.sin(-0.18 * x + 0.29 * y - 1.7 * t + 1.3) +
      0.2 * Math.sin(0.52 * (x - y) - 3.4 * t + 0.4);
    const edge = 1 - Math.pow(Math.min(1, Math.hypot(x, y) / R), 10);
    return A * w * edge + this.slosh * (x / R) * Math.cos(2.2 * t) + 0.6 * this.slosh * (y / R) * Math.sin(1.7 * t);
  }

  tick(dt, visible) {
    if (!visible) return;
    this.t += dt;
    const t = this.t;
    this.level += (this.target - this.level) * Math.min(1, dt * 1.6);
    const R = this.radiusAt(this.level);
    this.slosh += (0.35 - this.slosh) * Math.min(1, dt * 0.45);
    if (this.waveBoost) this.waveBoost = Math.max(0, this.waveBoost - dt * 0.3);

    // gotas automáticas y lluvia
    if (this.autoDrops && t >= this.nextDrop) {
      this.randomDrop(1.4);
      this.nextDrop = t + 2.2 + Math.random() * 2.2;
    }
    if (this.rain && t >= this.rainNext) {
      this.randomDrop(0.9 + Math.random() * 0.6);
      this.rainNext = t + 0.07 + Math.random() * 0.08;
    }
    this.tickDrops(dt);

    // pasos de la simulación (~60 por segundo, con tope para equipos lentos)
    this.simAcc += dt * 60;
    let n = Math.min(6, Math.floor(this.simAcc));
    this.simAcc -= Math.floor(this.simAcc);
    while (n-- > 0) this.stepSim();

    const top = this.geoms[0].attributes.position.array;
    top[0] = 0; top[1] = 0; top[2] = this.level + this.waves(0, 0, t, R) + this.sample(0, 0);
    for (let r = 0; r < this.NR; r++) {
      const rr = (R * (r + 1)) / this.NR;
      for (let s = 0; s < this.NS; s++) {
        const a = (s / this.NS) * Math.PI * 2;
        const x = rr * Math.cos(a), y = rr * Math.sin(a);
        const i = (1 + r * this.NS + s) * 3;
        top[i] = x; top[i + 1] = y;
        top[i + 2] = this.level + this.waves(x, y, t, R) + this.sample(x, y);
      }
    }
    this.geoms[0].attributes.position.needsUpdate = true;
    this.geoms[0].computeVertexNormals();
    const side = this.geoms[1].attributes.position.array;
    const R0 = this.radiusAt(this.floor);
    for (let s = 0; s < this.NS; s++) {
      const a = (s / this.NS) * Math.PI * 2;
      side.set([R0 * Math.cos(a), R0 * Math.sin(a), this.floor], s * 3);
      const k = (1 + (this.NR - 1) * this.NS + s) * 3;
      side.set([top[k], top[k + 1], top[k + 2]], (this.NS + s) * 3);
    }
    this.geoms[1].attributes.position.needsUpdate = true;
    this.geoms[1].computeVertexNormals();
  }

  tickDrops(dt) {
    const m = this._m;
    // gotas cayendo
    for (const d of this.falling) {
      d.v -= G * dt;
      d.z += d.v * dt;
    }
    const keep = [];
    for (const d of this.falling) {
      const surf = this.level + this.sample(d.x, d.y);
      if (d.z - d.r > surf) { keep.push(d); continue; }
      // impacto: hueco en el centro + anillo, y salpicadura
      this.impulse(d.x, d.y, 2.6 * d.r, 1.6 * d.r);
      this.impulse(d.x, d.y, -0.9 * d.r, 3.2 * d.r);
      this.stats.impacts++;
      const n = 6 + Math.floor(Math.random() * 5);
      for (let k = 0; k < n; k++) {
        if (this.splashes.length >= MAX_SPLASH) this.splashes.shift();
        const a = (k / n) * Math.PI * 2 + Math.random() * 0.4;
        const sp = 35 + Math.random() * 55;
        this.splashes.push({ x: d.x, y: d.y, z: surf + 0.3, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp,
          vz: 110 + Math.random() * 120, r: d.r * (0.22 + Math.random() * 0.2) });
      }
      // chorrito central (como en una foto de gota en cámara lenta)
      this.splashes.push({ x: d.x, y: d.y, z: surf + 0.3, vx: 0, vy: 0, vz: 230, r: d.r * 0.55 });
      this.stats.splashes++;
    }
    this.falling = keep;
    for (const s of this.splashes) {
      s.vz -= G * dt;
      s.x += s.vx * dt; s.y += s.vy * dt; s.z += s.vz * dt;
    }
    this.splashes = this.splashes.filter((s) => {
      if (s.vz > 0 || s.z > this.level) return true;
      this.impulse(s.x, s.y, 0.5 * s.r, 1.2);     // cada gotita vuelve a tocar el agua
      return false;
    });
    this.fallMesh.count = this.falling.length;
    this.falling.forEach((d, i) => {
      const stretch = 1 + Math.min(0.8, -d.v / 900);   // se estira al caer rápido
      m.makeScale(d.r, d.r, d.r * stretch).setPosition(d.x, d.y, d.z);
      this.fallMesh.setMatrixAt(i, m);
    });
    this.fallMesh.instanceMatrix.needsUpdate = true;
    this.splashMesh.count = this.splashes.length;
    this.splashes.forEach((s, i) => {
      m.makeScale(s.r, s.r, s.r * 1.3).setPosition(s.x, s.y, s.z);
      this.splashMesh.setMatrixAt(i, m);
    });
    this.splashMesh.instanceMatrix.needsUpdate = true;
  }
}
