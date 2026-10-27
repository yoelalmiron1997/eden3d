// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Visor 3D: escena, iluminación con presets, agua animada y plantas.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

export const LIGHTS = {
  estudio: { label: "Estudio", env: 0.85, sun: [0xfff4e6, 2.4], alt: 52, hemi: [0xfff6e8, 0x8a7a66, 0.55],
    fill: 0.45, exposure: 1.0, shadow: 0.2, stage: "radial-gradient(120% 90% at 60% 30%, #fbf6ee 0%, #efe6d8 55%, #e3d6c2 100%)" },
  manana: { label: "Mañana de sol", env: 0.7, sun: [0xfff0d0, 3.4], alt: 38, hemi: [0xdcecff, 0x9a8a6a, 0.6],
    fill: 0.3, exposure: 1.05, shadow: 0.32, stage: "radial-gradient(120% 90% at 70% 20%, #fffaf0 0%, #f3ead6 50%, #dfd0b2 100%)" },
  atardecer: { label: "Atardecer", env: 0.45, sun: [0xffa860, 3.6], alt: 12, hemi: [0xffd2a8, 0x5a4636, 0.45],
    fill: 0.18, exposure: 0.95, shadow: 0.38, stage: "radial-gradient(120% 90% at 80% 40%, #ffd9b0 0%, #e9b48a 45%, #8e6550 100%)" },
  noche: { label: "Noche con lámpara", env: 0.12, sun: [0xffc98a, 1.2], alt: 64, hemi: [0x2a3248, 0x14100c, 0.25],
    fill: 0.05, exposure: 0.9, shadow: 0.45, lamp: 2600, stage: "radial-gradient(90% 70% at 50% 25%, #4a3c2c 0%, #231d17 55%, #0f0d0b 100%)" },
};

export class Viewer {
  constructor(host) {
    this.host = host;
    const r = (this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }));
    r.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.localClippingEnabled = true;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    host.appendChild(r.domElement);

    this.scene = new THREE.Scene();
    const pm = new THREE.PMREMGenerator(r);
    this.envTex = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environment = this.envTex;

    this.camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
    this.camera.position.set(-180, 160, 320);
    this.controls = new OrbitControls(this.camera, r.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI * 0.49;

    this.hemi = new THREE.HemisphereLight(0xfff6e8, 0x8a7a66, 0.6);
    this.sun = new THREE.DirectionalLight(0xfff1dc, 2.2);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.radius = 4;
    Object.assign(this.sun.shadow.camera, { left: -220, right: 220, top: 220, bottom: -220, near: 10, far: 1200 });
    this.fill = new THREE.DirectionalLight(0xdfe8ff, 0.4);
    this.fill.position.set(-250, 120, -100);
    this.lamp = new THREE.PointLight(0xffc27a, 0, 0, 1.6);
    this.lamp.castShadow = true;
    this.lamp.shadow.mapSize.set(1024, 1024);
    this.scene.add(this.hemi, this.sun, this.sun.target, this.fill, this.lamp);
    this.ground = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), new THREE.ShadowMaterial({ opacity: 0.2 }));
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.receiveShadow = true;
    this.scene.add(this.ground);

    this.clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
    this.model = new THREE.Group();          // maceta y plato (Z del motor hacia arriba)
    this.model.rotation.x = -Math.PI / 2;
    this.plants = new THREE.Group();
    this.plants.rotation.x = -Math.PI / 2;
    this.scene.add(this.model, this.plants);

    this.mats = {
      MACETA: new THREE.MeshStandardMaterial({ color: 0xece9e2, roughness: 0.82, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      PLATO: new THREE.MeshStandardMaterial({ color: 0xdedad2, roughness: 0.84, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      AGUA: new THREE.MeshPhysicalMaterial({ color: 0x3f9fd8, roughness: 0.05, metalness: 0, transparent: true,
        opacity: 0.58, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.4, depthWrite: false, side: THREE.DoubleSide }),
    };
    this.plantMats = {};
    this.water = null;
    this.waterOn = true;
    this.cut = false;
    this.lightKey = "estudio";
    this.sunAz = 35;
    this.stats = { frames: 0, waterTime: 0, waterLevel: 0 };
    this.clock = new THREE.Clock();

    new ResizeObserver(() => this.resize()).observe(host);
    this.resize();
    this.setLight("estudio");
    // calidad adaptativa: si un cuadro tarda mucho (equipo sin GPU), baja la
    // resolución y las sombras y limita los cuadros por segundo
    this.minFrameMs = 0;
    this.slow = 0;
    let last = 0;
    const loop = (now) => {
      requestAnimationFrame(loop);
      if (document.hidden || now - last < this.minFrameMs) return;
      last = now;
      const t0 = performance.now();
      const dt = Math.min(this.clock.getDelta(), 0.1);
      this.controls.update();
      this.tickWater(dt);
      this.renderer.render(this.scene, this.camera);
      this.stats.frames++;
      // el costo real se ve en el intervalo entre cuadros (la GPU trabaja después)
      const gap = this.prevT ? t0 - this.prevT : 0;
      this.prevT = t0;
      this.stats.frameGap = gap;
      this.slow = gap > 120 + this.minFrameMs ? this.slow + 1 : Math.max(0, this.slow - 1);
      if (this.slow > 4 && !this.lowPower) this.setLowPower();
    };
    requestAnimationFrame(loop);
  }

  setLowPower() {
    this.lowPower = true;
    this.renderer.setPixelRatio(1);
    this.renderer.shadowMap.enabled = false;  // sin sombras dinámicas
    this.ground.visible = false;
    this.lamp.castShadow = false;
    for (const m of [...Object.values(this.mats), ...Object.values(this.plantMats)]) m.needsUpdate = true;
    this.scene.environment = null;            // sin reflejos de entorno
    this.minFrameMs = 500;                    // el agua se sigue moviendo, a 2 cuadros/s
    this.resize();
  }

  resize() {
    const b = this.host.getBoundingClientRect();
    const w = Math.max(10, b.width), h = Math.max(10, b.height);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ------------------------------------------------------------ iluminación
  setLight(key, az) {
    const L = LIGHTS[key] || LIGHTS.estudio;
    this.lightKey = key in LIGHTS ? key : "estudio";
    if (az !== undefined) this.sunAz = az;
    this.hemi.color.set(L.hemi[0]);
    this.hemi.groundColor.set(L.hemi[1]);
    this.hemi.intensity = L.hemi[2];
    this.sun.color.set(L.sun[0]);
    this.sun.intensity = L.sun[1];
    this.fill.intensity = L.fill;
    this.renderer.toneMappingExposure = L.exposure;
    this.ground.material.opacity = L.shadow;
    this.scene.environmentIntensity = L.env;
    this.lamp.intensity = L.lamp || 0;
    this.placeSun();
    this.host.parentElement.style.setProperty("--stage", L.stage);
    this.host.parentElement.style.background = L.stage;
  }

  placeSun() {
    const L = LIGHTS[this.lightKey];
    const az = THREE.MathUtils.degToRad(this.sunAz), alt = THREE.MathUtils.degToRad(L.alt);
    const d = 420;
    const c = this.center || new THREE.Vector3(0, 60, 0);
    this.sun.position.set(c.x + d * Math.cos(alt) * Math.sin(az), c.y + d * Math.sin(alt), c.z + d * Math.cos(alt) * Math.cos(az));
    this.sun.target.position.copy(c);
    this.lamp.position.set(c.x + 90, c.y + 170, c.z + 60);
  }

  // ------------------------------------------------------------ vistas
  setCut(on) {
    this.cut = on;
    const all = [...Object.values(this.mats), ...Object.values(this.plantMats)];
    for (const m of all) { m.clippingPlanes = on ? [this.clip] : []; m.needsUpdate = true; }
  }

  setColor(hex) {
    this.mats.MACETA.color.set(hex);
    this.mats.PLATO.color.set(hex).multiplyScalar(0.94);
  }

  geom(p) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(p.positions), 3));
    g.setIndex(new THREE.BufferAttribute(new Uint32Array(p.indices), 1));
    g.computeVertexNormals();
    return g;
  }

  showModel(parts, summary, refit) {
    this.model.clear();
    let tris = 0;
    for (const p of parts) {
      if (p.name === "AGUA") continue;                   // el agua la arma el visor (animada)
      const name = p.name === "MACETA" ? "MACETA" : "PLATO";
      const mesh = new THREE.Mesh(this.geom(p), this.mats[name]);
      mesh.name = name;
      mesh.castShadow = mesh.receiveShadow = true;
      this.model.add(mesh);
      tris += mesh.geometry.index.count / 3;
    }
    this.buildWater(summary && summary.assembly);
    this.triangles = tris;
    const box = new THREE.Box3().setFromObject(this.model);
    this.center = box.getCenter(new THREE.Vector3());
    this.placeSun();
    if (refit) this.fit(box);
  }

  meshNames() {
    return this.model.children.map((m) => m.name);
  }

  fit(box) {
    box = box || new THREE.Box3().setFromObject(this.model);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const c = box.getCenter(new THREE.Vector3());
    const r = Math.max(size.x, size.y * 1.15, size.z) * 0.5;
    const d = (r / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2))) * 1.55;
    const dir = new THREE.Vector3(-0.45, 0.5, 1).normalize();
    this.camera.position.copy(c).addScaledVector(dir, d);
    this.controls.target.copy(c).add(new THREE.Vector3(0, size.y * 0.08, 0));
    this.controls.update();
  }

  // ------------------------------------------------------------ agua animada
  buildWater(A) {
    if (this.water) { this.model.remove(this.water.group); this.water.geoms.forEach((g) => g.dispose()); }
    this.water = null;
    if (!A || A.dish_inner_r0_mm === undefined) return;
    const NR = 22, NS = 96;
    const top = new THREE.BufferGeometry();
    const pos = new Float32Array((NR * NS + 1) * 3);
    const idx = [];
    for (let s = 0; s < NS; s++) {
      idx.push(0, 1 + s, 1 + ((s + 1) % NS));
      for (let r = 0; r < NR - 1; r++) {
        const a = 1 + r * NS + s, b = 1 + r * NS + ((s + 1) % NS), c = a + NS, d = b + NS;
        idx.push(a, c, b, b, c, d);
      }
    }
    top.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    top.setIndex(idx);
    const side = new THREE.BufferGeometry();
    const spos = new Float32Array(NS * 2 * 3);
    const sidx = [];
    for (let s = 0; s < NS; s++) {
      const a = s, b = (s + 1) % NS;
      sidx.push(a, b, NS + b, a, NS + b, NS + a);
    }
    side.setAttribute("position", new THREE.BufferAttribute(spos, 3));
    side.setIndex(sidx);
    const group = new THREE.Group();
    const mTop = new THREE.Mesh(top, this.mats.AGUA), mSide = new THREE.Mesh(side, this.mats.AGUA);
    mTop.renderOrder = mSide.renderOrder = 3;
    group.add(mTop, mSide);
    group.name = "AGUA";
    this.model.add(group);
    const floor = A.dish_floor_mm + 0.8;
    this.water = {
      group, geoms: [top, side], NR, NS, A, t: 0,
      floor, levelMin: A.water_min_wet_level_mm, levelMax: A.water_level_max_mm,
      target: this.waterTarget === "min" ? A.water_min_wet_level_mm : A.water_level_max_mm,
      level: floor,
    };
    group.visible = this.waterOn;
  }

  setWater(on, which) {
    this.waterOn = on;
    if (which) this.waterTarget = which;
    if (!this.water) return;
    this.water.group.visible = on;
    this.water.target = this.waterTarget === "min" ? this.water.levelMin : this.water.levelMax;
    if (on) this.water.level = Math.min(this.water.level, this.water.floor + 0.2);  // se vuelve a llenar
  }

  tickWater(dt) {
    const W = this.water;
    if (!W || !W.group.visible) return;
    W.t += dt;
    this.stats.waterTime = W.t;
    // llenado suave hasta el nivel elegido
    W.level += (W.target - W.level) * Math.min(1, dt * 1.6);
    this.stats.waterLevel = W.level;
    const A = W.A, tan = Math.tan(THREE.MathUtils.degToRad(A.dish_flare_deg || 6));
    const R = A.dish_inner_r0_mm - 0.15 + (W.level - A.dish_floor_mm) * tan;
    const t = W.t;
    const top = W.geoms[0].attributes.position.array;
    const amp = 0.22;
    top[0] = 0; top[1] = 0; top[2] = W.level + amp * Math.sin(t * 2.1);
    for (let r = 0; r < W.NR; r++) {
      const rr = (R * (r + 1)) / W.NR;
      for (let s = 0; s < W.NS; s++) {
        const a = (s / W.NS) * Math.PI * 2;
        const x = rr * Math.cos(a), y = rr * Math.sin(a);
        // ondas concéntricas + oleaje cruzado suave (amortiguado en el borde)
        const edge = 1 - Math.pow(rr / R, 6);
        const z = W.level + edge * amp * (0.6 * Math.sin(rr * 0.42 - t * 2.4) +
          0.4 * Math.sin(x * 0.21 + t * 1.3) * Math.cos(y * 0.18 - t * 1.1));
        const i = (1 + r * W.NS + s) * 3;
        top[i] = x; top[i + 1] = y; top[i + 2] = z;
      }
    }
    W.geoms[0].attributes.position.needsUpdate = true;
    if (this.stats.frames % 2 === 0) W.geoms[0].computeVertexNormals();
    const side = W.geoms[1].attributes.position.array;
    const R0 = A.dish_inner_r0_mm - 0.15 + (W.floor - A.dish_floor_mm) * tan;
    for (let s = 0; s < W.NS; s++) {
      const a = (s / W.NS) * Math.PI * 2, c = Math.cos(a), sn = Math.sin(a);
      side.set([R0 * c, R0 * sn, W.floor], s * 3);
      const k = (1 + (W.NR - 1) * W.NS + s) * 3;
      side.set([top[k], top[k + 1], top[k + 2]], (W.NS + s) * 3);
    }
    W.geoms[1].attributes.position.needsUpdate = true;
    W.geoms[1].computeVertexNormals();
  }

  // ------------------------------------------------------------ plantas
  setPlantMaterials(def) {
    for (const [k, v] of Object.entries(def)) {
      if (this.plantMats[k]) continue;
      const [r, g, b] = v.rgb;
      this.plantMats[k] = new THREE.MeshStandardMaterial({
        color: new THREE.Color(r / 255, g / 255, b / 255).convertSRGBToLinear(),
        roughness: 1 - 0.6 * v.brillo, metalness: 0, side: THREE.DoubleSide,
      });
    }
    const extra = { tierra: [88, 64, 46, 0], piedra: [228, 222, 210, 0.05], arcilla: [172, 108, 72, 0.05] };
    for (const [k, [r, g, b, br]] of Object.entries(extra)) {
      if (!this.plantMats[k]) this.plantMats[k] = new THREE.MeshStandardMaterial({
        color: new THREE.Color(r / 255, g / 255, b / 255).convertSRGBToLinear(), roughness: 1 - br });
    }
  }

  showPlants(parts) {
    this.plants.traverse((o) => o.geometry && o.geometry.dispose());
    this.plants.clear();
    let tris = 0;
    for (const p of parts) {
      const mesh = new THREE.Mesh(this.geom(p), this.plantMats[p.name] || this.mats.PLATO);
      mesh.name = p.name;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.plants.add(mesh);
      tris += mesh.geometry.index.count / 3;
    }
    this.plantTriangles = tris;
    if (this.cut) this.setCut(true);
  }
}
