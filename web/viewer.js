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
        opacity: 0.5, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.8, specularIntensity: 1, depthWrite: false, side: THREE.DoubleSide }),
    };
    this.plantMats = {};
    this.water = null;
    this.waterOn = true;
    this.cut = false;
    this.lightKey = "estudio";
    this.sunAz = 35;
    this.stats = { frames: 0, waterTime: 0, waterLevel: 0, drops: 0, growing: 0 };
    this.animTime = 0;
    this.windOn = true;
    this.sceneKey = "estudio";
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
      const dt = Math.min(this.clock.getDelta(), this.lowPower ? 0.6 : 0.1);
      this.controls.update();
      this.tickWater(dt);
      this.tickPlants(dt);
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
    const S = SCENES[this.sceneKey];
    const bg = (S && S.stage) || L.stage;
    this.host.parentElement.style.setProperty("--stage", bg);
    this.host.parentElement.style.background = bg;
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
    this.fitScene();
    if (refit) { this.fit(box); this.needFit = true; this.fitH = 0; }
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
    const d = (r / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2))) * 1.4;
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
    const NR = 30, NS = 112;
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
    const amp = 0.55;
    // gotas: cada ~2,5 s cae una en un punto al azar y abre un anillo que se expande
    W.drops = W.drops || [];
    W.nextDrop = W.nextDrop ?? 0.4;
    if (t >= W.nextDrop) {
      const a = Math.random() * Math.PI * 2, d = Math.sqrt(Math.random()) * R * 0.75;
      W.drops.push({ x: d * Math.cos(a), y: d * Math.sin(a), t0: t });
      W.nextDrop = t + 1.6 + Math.random() * 1.8;
      this.stats.drops = (this.stats.drops || 0) + 1;
    }
    W.drops = W.drops.filter((d) => t - d.t0 < 3.2);
    const ring = (x, y) => {
      let z = 0;
      for (const d of W.drops) {
        const age = t - d.t0, front = age * 22;                 // 22 mm/s
        const dist = Math.hypot(x - d.x, y - d.y) - front;
        z += 1.1 * Math.exp(-age * 1.15) * Math.exp(-(dist * dist) / 18) * Math.cos(dist * 0.9);
      }
      return z;
    };
    top[0] = 0; top[1] = 0; top[2] = W.level + amp * 0.6 * Math.sin(t * 2.1) + ring(0, 0);
    for (let r = 0; r < W.NR; r++) {
      const rr = (R * (r + 1)) / W.NR;
      for (let s = 0; s < W.NS; s++) {
        const a = (s / W.NS) * Math.PI * 2;
        const x = rr * Math.cos(a), y = rr * Math.sin(a);
        // ondas concéntricas + oleaje cruzado + anillos de gotas (amortiguado en el borde)
        const edge = 1 - Math.pow(rr / R, 8);
        const z = W.level + edge * (amp * (0.5 * Math.sin(rr * 0.5 - t * 2.6) +
          0.3 * Math.sin(x * 0.23 + t * 1.4) * Math.cos(y * 0.19 - t * 1.2) +
          0.2 * Math.sin((x + y) * 0.6 - t * 3.3)) + ring(x, y));
        const i = (1 + r * W.NS + s) * 3;
        top[i] = x; top[i + 1] = y; top[i + 2] = z;
      }
    }
    W.geoms[0].attributes.position.needsUpdate = true;
    W.geoms[0].computeVertexNormals();               // reflejos que se mueven con las ondas
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
  // Viento: el vértice se desplaza según su altura sobre la tierra (las colgantes,
  // según cuánto cuelgan) y la flexibilidad de la planta (atributo aFlex).
  windPatch(mat) {
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = this.wind;
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\nattribute float aFlex;\nuniform float uTime;")
        .replace("#include <begin_vertex>", `#include <begin_vertex>
          float hgt = abs(transformed.z);
          float bend = aFlex * pow(hgt / 60.0, 1.6);
          float ph = modelMatrix[3].x * 0.07 + modelMatrix[3].z * 0.05;
          float w = sin(uTime * 1.3 + ph) * 0.7 + sin(uTime * 2.9 + ph * 1.7 + transformed.z * 0.04) * 0.3;
          transformed.x += bend * 2.2 * w;
          transformed.y += bend * 1.2 * cos(uTime * 1.1 + ph * 1.3);`);
    };
    mat.customProgramCacheKey = () => "eden-viento";
  }

  setPlantMaterials(def, decorMats = []) {
    this.wind = this.wind || { value: 0 };
    for (const [k, v] of Object.entries(def)) {
      if (this.plantMats[k]) continue;
      const [r, g, b] = v.rgb;
      const m = (this.plantMats[k] = new THREE.MeshStandardMaterial({
        color: new THREE.Color(r / 255, g / 255, b / 255).convertSRGBToLinear(),
        roughness: 1 - 0.6 * v.brillo, metalness: 0, side: THREE.DoubleSide,
      }));
      if (!decorMats.includes(k)) this.windPatch(m);
    }
  }

  // parts: [{name, positions, indices, planta, base:[x,y,z], flex}]; planta -1 = tierra
  showPlants(parts, ids = []) {
    this.plants.traverse((o) => o.geometry && o.geometry.dispose());
    this.plants.clear();
    const prev = new Set(this.prevIds || []);
    this.prevIds = ids.slice();
    this.plantGroups = [];
    let tris = 0;
    const groups = new Map();
    for (const p of parts) {
      const k = p.planta ?? -1;
      if (!groups.has(k)) {
        const g = new THREE.Group();
        const b = p.base || [0, 0, 0];
        g.position.set(b[0], b[1], b[2]);
        g.userData = { id: ids[k], k };
        groups.set(k, g);
        this.plants.add(g);
        if (k >= 0) this.plantGroups.push(g);
      }
      const g = groups.get(k);
      const geo = this.geom(p);
      geo.translate(-g.position.x, -g.position.y, -g.position.z);   // pivote en la base
      const n = geo.attributes.position.count;
      geo.setAttribute("aFlex", new THREE.BufferAttribute(new Float32Array(n).fill(k >= 0 ? p.flex ?? 0.5 : 0), 1));
      const mesh = new THREE.Mesh(geo, this.plantMats[p.name] || this.mats.PLATO);
      mesh.name = p.name;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      g.add(mesh);
      tris += geo.index.count / 3;
    }
    // encuadre: si las plantas (ya de tamaño final) salen del cuadro, se reencuadra todo
    const all = new THREE.Box3().setFromObject(this.model).union(new THREE.Box3().setFromObject(this.plants));
    const h = all.getSize(new THREE.Vector3()).y;
    if (this.needFit || h > (this.fitH || 0) * 1.12) { this.fit(all); this.fitH = h; }
    this.needFit = false;
    // nacimiento: sólo las plantas nuevas crecen desde la tierra, una después de otra
    let order = 0;
    this.stats.born = [];
    for (const g of this.plantGroups) {
      if (prev.has(g.userData.id)) continue;
      g.userData.birth = { t0: this.animTime + 0.28 * order++, dur: 1.5 };
      g.scale.setScalar(0.001);
      this.stats.born.push(g.userData.id);
    }
    this.plantTriangles = tris;
    if (this.cut) this.setCut(true);
  }

  tickPlants(dt) {
    this.animTime += dt;
    if (this.wind) this.wind.value = this.windOn ? this.animTime : 0;
    let growing = 0;
    for (const g of this.plantGroups || []) {
      const B = g.userData.birth;
      if (!B) continue;
      const u = Math.min(1, Math.max(0, (this.animTime - B.t0) / B.dur));
      // easeOutBack: crece, se pasa un poquito y vuelve (como un brote)
      const c1 = 1.4, c3 = c1 + 1, e = 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2);
      const sxy = Math.max(0.001, Math.min(e, 1.2)), sz = Math.max(0.001, Math.min(1.08, e * 1.04));
      g.scale.set(sxy, sxy, u < 1 ? sz : 1);
      g.rotation.z = (1 - u) * -1.2;
      if (u >= 1) { g.scale.setScalar(1); g.rotation.z = 0; delete g.userData.birth; } else growing++;
    }
    this.stats.growing = growing;
  }

  setWind(on) { this.windOn = on; }

  // ------------------------------------------------------------ escenarios
  setScene(key) {
    this.sceneKey = SCENES[key] ? key : "estudio";
    if (this.sceneGroup) {
      this.scene.remove(this.sceneGroup);
      this.sceneGroup.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    }
    this.sceneGroup = null;
    const S = SCENES[this.sceneKey];
    this.ground.visible = !S.build && !this.lowPower;
    if (S.build) {
      this.sceneGroup = S.build(THREE);
      this.sceneGroup.name = "ESCENARIO";
      this.sceneGroup.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = !o.userData.noShadow; } });
      this.scene.add(this.sceneGroup);
      this.fitScene();
    }
    const bg = S.stage || LIGHTS[this.lightKey].stage;
    this.host.parentElement.style.background = bg;
    this.host.parentElement.style.setProperty("--stage", bg);
    if (S.light) this.setLight(S.light);
  }

  // los escenarios están modelados para una maceta de ~150 mm; se escalan con la maceta
  fitScene() {
    if (!this.sceneGroup) return;
    const box = new THREE.Box3().setFromObject(this.model);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const k = THREE.MathUtils.clamp(Math.max(size.y, size.x * 1.2) / 150, 0.55, 2.2);
    this.sceneGroup.scale.setScalar(k);
    this.sceneGroup.position.set(box.getCenter(new THREE.Vector3()).x, box.min.y, box.getCenter(new THREE.Vector3()).z);
  }

  sceneMeshes() {
    const out = [];
    if (this.sceneGroup) this.sceneGroup.traverse((o) => o.isMesh && out.push(o.name));
    return out;
  }

  // ------------------------------------------------------------ foto
  // PNG 1080×1350 (formato Instagram) del encuadre actual.
  photo(w = 1080, h = 1350) {
    const r = this.renderer;
    const prevPR = r.getPixelRatio(), prevSize = r.getSize(new THREE.Vector2());
    const prevAspect = this.camera.aspect;
    const prevBg = this.scene.background;
    r.setPixelRatio(1);
    r.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    // fondo: el del escenario o un degradé con el color del visor
    const cv = document.createElement("canvas");
    cv.width = 4; cv.height = 256;
    const ctx = cv.getContext("2d");
    const [c1, c2] = (SCENES[this.sceneKey] || {}).sky || (LIGHTS[this.lightKey].sky || ["#fbf6ee", "#e3d6c2"]);
    const gr = ctx.createLinearGradient(0, 0, 0, 256);
    gr.addColorStop(0, c1); gr.addColorStop(1, c2);
    ctx.fillStyle = gr; ctx.fillRect(0, 0, 4, 256);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    this.scene.background = tex;
    r.render(this.scene, this.camera);
    const url = r.domElement.toDataURL("image/png");
    this.scene.background = prevBg;
    tex.dispose();
    r.setPixelRatio(prevPR);
    r.setSize(prevSize.x, prevSize.y, false);
    this.camera.aspect = prevAspect;
    this.camera.updateProjectionMatrix();
    return { url, width: w, height: h };
  }
}

// ======================================================================== escenarios
// Modelados en mm (Y arriba) para una maceta de ~150 mm apoyada en (0, 0, 0).
function std(THREE, color, rough = 0.8, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...extra });
}

function canvasTex(THREE, w, h, draw, repeat = [1, 1]) {
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  draw(cv.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat);
  return t;
}

function woodTex(THREE, base, dark, repeat) {
  return canvasTex(THREE, 512, 128, (c, w, h) => {
    c.fillStyle = base; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 70; i++) {
      c.strokeStyle = dark; c.globalAlpha = 0.08 + Math.random() * 0.18; c.lineWidth = 1 + Math.random() * 2.5;
      const y = Math.random() * h;
      c.beginPath(); c.moveTo(0, y);
      for (let x = 0; x <= w; x += 32) c.lineTo(x, y + Math.sin(x * 0.02 + i) * 3);
      c.stroke();
    }
    c.globalAlpha = 1;
  }, repeat);
}

function box(THREE, mat, w, h, d, x, y, z, name) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  if (name) m.name = name;
  return m;
}

function cyl(THREE, mat, r1, r2, h, x, y, z, seg = 32, name) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r1, r2, h, seg), mat);
  m.position.set(x, y, z);
  if (name) m.name = name;
  return m;
}

function buildOficina(THREE) {
  const g = new THREE.Group();
  const madera = std(THREE, 0xffffff, 0.55, { map: woodTex(THREE, "#c49a6c", "#6b4a2b", [2, 1]) });
  g.add(box(THREE, madera, 1100, 28, 640, 0, -14, -120, "escritorio"));
  const pared = std(THREE, 0xe9e4da, 0.95);
  const wall = box(THREE, pared, 2400, 1400, 10, 0, 560, -440, "pared");
  wall.userData.noShadow = true;
  g.add(wall);
  // ventana con persianas: la luz entra en franjas
  const marco = std(THREE, 0xf7f5f0, 0.6);
  g.add(box(THREE, std(THREE, 0xcfe4f5, 0.2, { emissive: 0xbcd8f0, emissiveIntensity: 0.6 }), 560, 520, 4, -330, 520, -432, "ventana"));
  for (let i = 0; i < 17; i++) g.add(box(THREE, marco, 560, 14, 8, -330, 280 + i * 30, -426, i ? undefined : "persiana"));
  g.add(box(THREE, marco, 590, 22, 20, -330, 260, -425));
  // monitor, teclado, taza y libros
  const negro = std(THREE, 0x22262b, 0.45);
  g.add(box(THREE, negro, 460, 270, 18, 300, 230, -330, "monitor"));
  g.add(box(THREE, std(THREE, 0x2e5a7a, 0.3, { emissive: 0x1d4466, emissiveIntensity: 0.5 }), 440, 250, 2, 300, 230, -320));
  g.add(cyl(THREE, negro, 12, 16, 100, 300, 50, -345));
  g.add(box(THREE, negro, 140, 8, 90, 300, 4, -345));
  g.add(box(THREE, std(THREE, 0xdedede, 0.6), 360, 14, 120, 250, 7, -120, "teclado"));
  const taza = cyl(THREE, std(THREE, 0xe46b4f, 0.35), 36, 32, 90, -230, 45, 10, 32, "taza");
  const asa = new THREE.Mesh(new THREE.TorusGeometry(22, 6, 10, 24), taza.material);
  asa.position.set(-268, 48, 10);
  g.add(taza, asa);
  const libros = [0x355c7d, 0xc06c84, 0xf8b195, 0x6c5b7b];
  libros.forEach((c, i) => g.add(box(THREE, std(THREE, c, 0.7), 220, 26, 160, -420, 13 + i * 26, -260 + i * 6, i ? undefined : "libros")));
  return g;
}

function buildJardin(THREE) {
  const g = new THREE.Group();
  const pasto = canvasTex(THREE, 256, 256, (c, w, h) => {
    c.fillStyle = "#5f8a3a"; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 2600; i++) {
      c.fillStyle = ["#4f7a2e", "#76a046", "#6b9440", "#87b052"][i % 4];
      c.fillRect(Math.random() * w, Math.random() * h, 1.5, 3 + Math.random() * 5);
    }
  }, [10, 10]);
  const suelo = new THREE.Mesh(new THREE.CircleGeometry(2200, 64), std(THREE, 0xffffff, 0.95, { map: pasto }));
  suelo.rotation.x = -Math.PI / 2;
  suelo.position.y = -18;
  suelo.name = "pasto";
  g.add(suelo);
  // laja de piedra bajo la maceta
  const laja = cyl(THREE, std(THREE, 0xb9b2a6, 0.9), 150, 158, 18, 0, -9, 0, 11, "laja");
  laja.rotation.y = 0.3;
  g.add(laja);
  // cerco de madera y cerco vivo
  const tabla = std(THREE, 0xffffff, 0.8, { map: woodTex(THREE, "#9b7653", "#5a3e26", [1, 1]) });
  for (let i = -12; i <= 12; i++) g.add(box(THREE, tabla, 92, 620 + (i % 2) * 30, 18, i * 100, 300, -900, i ? undefined : "cerco"));
  g.add(box(THREE, tabla, 2500, 30, 24, 0, 160, -885), box(THREE, tabla, 2500, 30, 24, 0, 470, -885));
  const verde = std(THREE, 0x3f6e2c, 0.95);
  for (let i = 0; i < 26; i++) {
    const s = new THREE.Mesh(new THREE.IcosahedronGeometry(110 + Math.random() * 60, 1), verde);
    s.position.set(-1300 + i * 104, 70 + Math.random() * 60, -760 + Math.random() * 40);
    if (!i) s.name = "cerco_vivo";
    g.add(s);
  }
  // flores en el pasto
  const colores = [0xf4d35e, 0xee964b, 0xf95738, 0xffffff, 0xb388eb];
  const tallo = std(THREE, 0x4c7a34, 0.8);
  for (let i = 0; i < 46; i++) {
    const a = Math.random() * Math.PI * 2, d = 330 + Math.random() * 700;
    const x = Math.cos(a) * d, z = Math.sin(a) * d - 120;
    if (z > 250) continue;
    const h = 22 + Math.random() * 40;
    g.add(cyl(THREE, tallo, 1.1, 1.1, h, x, -18 + h / 2, z, 5));
    const f = new THREE.Mesh(new THREE.SphereGeometry(5 + Math.random() * 3, 10, 8), std(THREE, colores[i % 5], 0.6));
    f.position.set(x, -18 + h, z);
    if (!i) f.name = "flores";
    g.add(f);
  }
  return g;
}

function buildTaller(THREE) {
  const g = new THREE.Group();
  const madera = std(THREE, 0xffffff, 0.7, { map: woodTex(THREE, "#b88a58", "#6e4c2a", [2, 1]) });
  g.add(box(THREE, madera, 1300, 46, 620, 0, -23, -120, "banco"));
  // tablero perforado con herramientas
  const perf = canvasTex(THREE, 128, 128, (c, w, h) => {
    c.fillStyle = "#c8a374"; c.fillRect(0, 0, w, h);
    c.fillStyle = "#5c4026";
    for (let y = 8; y < h; y += 16) for (let x = 8; x < w; x += 16) { c.beginPath(); c.arc(x, y, 2.6, 0, 7); c.fill(); }
  }, [14, 8]);
  const tab = box(THREE, std(THREE, 0xffffff, 0.85, { map: perf }), 1600, 900, 12, 0, 470, -440, "tablero_perforado");
  tab.userData.noShadow = true;
  g.add(tab);
  const metal = std(THREE, 0x9aa1a8, 0.35, { metalness: 0.8 });
  const mango = std(THREE, 0xd2462f, 0.5);
  // martillo, destornilladores, llave y pinza
  g.add(cyl(THREE, mango, 9, 9, 230, -480, 520, -420, 12, "martillo"));
  g.add(box(THREE, metal, 90, 30, 30, -480, 645, -420));
  [[-360, 0xf2c14e], [-320, 0x2b7de9], [-280, 0x38a169]].forEach(([x, c]) => {
    g.add(cyl(THREE, std(THREE, c, 0.5), 11, 11, 90, x, 600, -420, 12));
    g.add(cyl(THREE, metal, 3, 3, 120, x, 495, -420, 8));
  });
  g.add(box(THREE, metal, 26, 220, 10, -180, 540, -425, "llave"));
  // impresora 3D (la que hace las macetas) con un carretel de PLA
  const marco = std(THREE, 0x2b2d31, 0.5, { metalness: 0.3 });
  const px = 420, pz = -230;
  for (const [x, z] of [[-150, -150], [150, -150], [-150, 150], [150, 150]]) g.add(box(THREE, marco, 20, 420, 20, px + x, 210, pz + z, x < 0 && z < 0 ? "impresora_3d" : undefined));
  g.add(box(THREE, marco, 320, 20, 320, px, 410, pz), box(THREE, marco, 340, 30, 340, px, 15, pz));
  g.add(box(THREE, std(THREE, 0x1b1c1f, 0.3), 260, 6, 260, px, 90, pz));
  g.add(box(THREE, std(THREE, 0xe0e0e0, 0.4), 70, 50, 50, px, 250, pz));
  g.add(box(THREE, marco, 320, 14, 14, px, 250, pz));
  const carrete = cyl(THREE, std(THREE, 0x8fbf7a, 0.45), 100, 100, 70, -420, 100, -230, 40, "carrete_pla");
  carrete.rotation.z = Math.PI / 2;
  g.add(carrete);
  const pieza = cyl(THREE, std(THREE, 0x8fbf7a, 0.6), 30, 22, 50, px, 118, pz, 24);
  g.add(pieza);
  // lámpara de banco
  g.add(cyl(THREE, marco, 6, 6, 380, -620, 190, -300, 8));
  const pant = cyl(THREE, std(THREE, 0xf2c14e, 0.5, { side: THREE.DoubleSide }), 30, 70, 70, -560, 370, -260, 24);
  pant.rotation.z = -0.6;
  g.add(pant);
  return g;
}

export const SCENES = {
  estudio: { label: "Estudio" },
  oficina: { label: "Oficina", build: buildOficina, light: "manana",
    stage: "linear-gradient(180deg, #ece7de 0%, #ddd5c8 100%)", sky: ["#ece7de", "#d8cfc1"] },
  jardin: { label: "Jardín", build: buildJardin, light: "manana",
    stage: "linear-gradient(180deg, #a9d3f2 0%, #dcefff 55%, #cfe6c0 100%)", sky: ["#8fc6ee", "#e4f2ff"] },
  taller: { label: "Taller de trabajo", build: buildTaller, light: "estudio",
    stage: "linear-gradient(180deg, #d9cdbb 0%, #b9a88f 100%)", sky: ["#d9cdbb", "#b3a186"] },
};
