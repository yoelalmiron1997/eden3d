// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Visor 3D: escena, iluminación, escenarios, agua interactiva, plantas, piezas separadas y modo slicer.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { Water } from "./water.js";
import { LAYER_MM, slicerMaterial, sliceSegments, buildPlate, orderSegments, buildPrintHead } from "./slicer.js";

export const LIGHTS = {
  // estudio usa el fondo del tema (claro u oscuro) definido en style.css
  estudio: { label: "Estudio", env: 0.85, sun: [0xfff4e6, 2.4], alt: 52, hemi: [0xfff6e8, 0x8a7a66, 0.55],
    fill: 0.45, exposure: 1.0, shadow: 0.2, stage: "var(--stage)" },
  manana: { label: "Mañana", env: 0.7, sun: [0xfff0d0, 3.4], alt: 38, hemi: [0xdcecff, 0x9a8a6a, 0.6],
    fill: 0.3, exposure: 1.05, shadow: 0.32, stage: "radial-gradient(120% 90% at 70% 20%, #fffaf0 0%, #f3ead6 50%, #dfd0b2 100%)" },
  atardecer: { label: "Tarde", env: 0.45, sun: [0xffa860, 3.6], alt: 12, hemi: [0xffd2a8, 0x5a4636, 0.45],
    fill: 0.18, exposure: 0.95, shadow: 0.38, stage: "radial-gradient(120% 90% at 80% 40%, #ffd9b0 0%, #e9b48a 45%, #8e6550 100%)" },
  noche: { label: "Noche", env: 0.12, sun: [0xffc98a, 1.2], alt: 64, hemi: [0x2a3248, 0x14100c, 0.25],
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

    this.camera = new THREE.PerspectiveCamera(32, 1, 2, 120000);
    this.camera.position.set(-180, 160, 320);
    this.controls = new OrbitControls(this.camera, r.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI;              // todos los ángulos, también desde abajo
    this.controls.addEventListener("start", () => { this.vuelo = null; });
    this.ocultarAbajo = [];                              // lo que cada página esconde al mirar desde abajo

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
    this.luzAbajo = new THREE.DirectionalLight(0xfff6ea, 0);      // sólo al mirar desde abajo
    this.luzAbajo.position.set(60, -300, 120);
    this.scene.add(this.hemi, this.sun, this.sun.target, this.fill, this.lamp, this.luzAbajo);
    this.ground = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), new THREE.ShadowMaterial({ opacity: 0.2 }));
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.receiveShadow = true;
    this.scene.add(this.ground);
    // sombra de contacto suave (también en equipos sin sombras dinámicas)
    const cv = document.createElement("canvas");
    cv.width = cv.height = 128;
    const cx = cv.getContext("2d");
    const gr = cx.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, "rgba(0,0,0,0.55)"); gr.addColorStop(0.55, "rgba(0,0,0,0.28)"); gr.addColorStop(1, "rgba(0,0,0,0)");
    cx.fillStyle = gr; cx.fillRect(0, 0, 128, 128);
    this.contact = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({
      map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false, toneMapped: false }));
    this.contact.rotation.x = -Math.PI / 2;
    this.contact.renderOrder = 1;
    this.contact.name = "SOMBRA_CONTACTO";
    this.scene.add(this.contact);

    this.clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
    this.model = new THREE.Group();          // maceta y plato (Z del motor hacia arriba)
    this.model.rotation.x = -Math.PI / 2;
    this.plants = new THREE.Group();
    this.plants.rotation.x = -Math.PI / 2;
    this.scene.add(this.model, this.plants);

    this.mats = {
      MACETA: new THREE.MeshStandardMaterial({ color: 0xece9e2, roughness: 0.82, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      PLATO: new THREE.MeshStandardMaterial({ color: 0xdedad2, roughness: 0.84, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      // inserto del mate con hueco (polímero escalonado / base), semitransparente
      INSERTO: new THREE.MeshStandardMaterial({ color: 0xb9c2c9, roughness: 0.35, metalness: 0.55, transparent: true,
        opacity: 0.55, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 1.2,
        polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2 }),
      // relieve proyectado y cuña del mate
      RELIEVE: new THREE.MeshStandardMaterial({ color: 0xece9e2, roughness: 0.6, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      CUNA: new THREE.MeshStandardMaterial({ color: 0xd8d2c6, roughness: 0.8, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.8 }),
      // medallón encastrable: pieza aparte, en otro tono para que se note
      MEDALLON: new THREE.MeshStandardMaterial({ color: 0xc9a46a, roughness: 0.55, metalness: 0.05, side: THREE.DoubleSide, envMapIntensity: 0.9 }),
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
    this.explode = 0;
    this.pmrem = pm;
    this.slicer = { on: false, part: "MACETA", layer: 0, layers: 0, playing: false,
      uniforms: { uCut: { value: 1e6 }, uLayer: { value: LAYER_MM } } };
    this.setupPointer();
    this.mountVistas(host);

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
      this.tickVuelo(dt);
      this.controls.update();
      this.tickAbajo();
      this.tickWater(dt);
      this.tickPlants(dt);
      this.tickSlicer(dt);
      this.tickExplode(dt);
      if (this.tickers) for (const f of this.tickers) f(dt);   // animaciones de cada página (cebado del mate)
      if (this.onFrame) this.onFrame();
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
    this.host.parentElement.style.background = bg;
  }

  placeSun() {
    const L = LIGHTS[this.lightKey];
    const az = THREE.MathUtils.degToRad(this.sunAz), alt = THREE.MathUtils.degToRad(this.altOverride ?? L.alt);
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
    this.mats.RELIEVE.color.set(hex);
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
      // eslabones de las patitas: cada uno con su nombre (se animan), del color de la maceta
      const limb = /^(PATA|BRAZO)_/.test(p.name);
      const name = p.name === "MACETA" ? "MACETA" : (this.mats[p.name] || limb ? p.name : "PLATO");
      const mesh = new THREE.Mesh(this.geom(p), limb ? this.mats.MACETA : this.mats[name]);
      mesh.name = name;
      mesh.castShadow = mesh.receiveShadow = true;
      this.model.add(mesh);
      tris += mesh.geometry.index.count / 3;
    }
    this.buildWater(summary && summary.assembly);
    this.triangles = tris;
    this.applyExplode();
    if (this.slicer.on) { this.slicer.layer = 0; this.enterSlicer(); }
    const box = this.baseBox();
    this.center = box.getCenter(new THREE.Vector3());
    const sz = box.getSize(new THREE.Vector3());
    this.contact.scale.set(sz.x * 1.45, sz.z * 1.45, 1);
    this.contact.position.set(this.center.x, box.min.y + 0.3, this.center.z);
    this.placeSun();
    this.fitScene();
    if (refit) { this.fit(box); this.needFit = true; this.fitH = 0; }
  }

  meshNames() {
    return this.model.children.map((m) => m.name);
  }

  // caja de la pieza apoyada (la página puede dar otra: la chapita colgada sigue "apoyada" en la mesa)
  baseBox() {
    return this.sceneBox ? this.sceneBox() : new THREE.Box3().setFromObject(this.model);
  }

  // ------------------------------------------------------------ vistas (todos los ángulos)
  mountVistas(host) {
    const bar = document.createElement("div");
    bar.className = "vistas";
    bar.setAttribute("role", "toolbar");
    bar.setAttribute("aria-label", "Vistas de la cámara");
    bar.dataset.testid = "vistas";
    bar.innerHTML = Object.entries(VISTAS).map(([k, V]) =>
      `<button type="button" data-vista="${k}" data-testid="vista-${k}" title="${V.titulo}" aria-label="${V.titulo}">${V.label}</button>`).join("")
      + `<button type="button" data-vista="girar" data-testid="vista-girar" title="Girar 360°" aria-label="Girar 360°" aria-pressed="false">360°</button>`;
    bar.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-vista]");
      if (!b) return;
      if (b.dataset.vista === "girar") {
        this.controls.autoRotate = !this.controls.autoRotate;
        this.controls.autoRotateSpeed = 2.2;
        b.setAttribute("aria-pressed", String(this.controls.autoRotate));
      } else this.vista(b.dataset.vista);
    });
    host.appendChild(bar);
    this.vistasBar = bar;
  }

  // lleva la cámara (sin cambiar la distancia) a la vista pedida, en un vuelo corto
  vista(k, inmediato) {
    const V = VISTAS[k];
    if (!V) return;
    const t = this.controls.target;
    const rel = this.camera.position.clone().sub(t);
    const desde = new THREE.Spherical().setFromVector3(rel);
    const hacia = new THREE.Spherical().setFromVector3(new THREE.Vector3(...V.dir).normalize());
    hacia.radius = desde.radius;
    hacia.phi = THREE.MathUtils.clamp(hacia.phi, 0.001, Math.PI - 0.001);
    let dth = hacia.theta - desde.theta;                      // el giro más corto
    dth = Math.atan2(Math.sin(dth), Math.cos(dth));
    this.vuelo = { desde, dth, hacia, t: inmediato ? 1 : 0, dur: 0.75 };
    this.vistaActual = k;
    this.tickVuelo(0);
  }

  tickVuelo(dt) {
    const F = this.vuelo;
    if (!F) return;
    F.t = Math.min(1, F.t + dt / F.dur);
    const e = F.t < 0.5 ? 4 * F.t ** 3 : 1 - (-2 * F.t + 2) ** 3 / 2;
    const s = new THREE.Spherical(F.desde.radius, F.desde.phi + (F.hacia.phi - F.desde.phi) * e, F.desde.theta + F.dth * e);
    this.camera.position.copy(this.controls.target).add(new THREE.Vector3().setFromSpherical(s));
    this.camera.lookAt(this.controls.target);
    if (F.t >= 1) this.vuelo = null;
  }

  // mirando desde abajo de la mesa: se esconden la mesa, el escenario y el piso para ver la pieza
  tickAbajo() {
    const abajo = this.camera.position.y < (this.pisoY || 0) - 0.5;
    if (abajo) {
      this.ocultos = this.ocultos || new Set();
      for (const o of [this.ground, this.contact, this.sceneGroup, ...this.ocultarAbajo]) {
        if (o && o.visible) { o.visible = false; this.ocultos.add(o); }
      }
    } else if (this.ocultos && this.ocultos.size) {
      for (const o of this.ocultos) if (o.parent) o.visible = true;   // lo que se sacó de la escena, no
      this.ocultos.clear();
    }
    this.luzAbajo.intensity += ((abajo ? 1.6 : 0) - this.luzAbajo.intensity) * 0.2;
    this.stats.desdeAbajo = abajo;
  }

  fit(box, dir) {
    box = box || new THREE.Box3().setFromObject(this.model);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const c = box.getCenter(new THREE.Vector3());
    const r = Math.max(size.x, size.y * 1.15, size.z) * 0.5;
    const d = (r / Math.sin(THREE.MathUtils.degToRad(this.camera.fov / 2))) * (this.viewDist || 1.4);
    dir = (dir || this.viewDir || new THREE.Vector3(-0.45, 0.5, 1)).clone().normalize();
    this.camera.position.copy(c).addScaledVector(dir, d);
    this.controls.target.copy(c).add(new THREE.Vector3(0, size.y * 0.08, 0));
    this.controls.update();
  }

  // ------------------------------------------------------------ agua interactiva
  buildWater(A) {
    if (this.water) { this.model.remove(this.water.group); this.water.dispose(); }
    this.water = null;
    if (!A || A.dish_inner_r0_mm === undefined) return;
    this.water = new Water(this.mats.AGUA, A, this.waterTarget);
    this.water.rain = !!this.rain;
    this.model.add(this.water.group);
    this.water.group.visible = this.waterOn && !this.slicer.on;
  }

  setWater(on, which) {
    this.waterOn = on;
    if (which) this.waterTarget = which;
    const W = this.water;
    if (!W) return;
    W.group.visible = on && !this.slicer.on;
    W.target = this.waterTarget === "min" ? W.levelMin : W.levelMax;
    if (on) W.level = Math.min(W.level, W.floor + 0.2);     // se vuelve a llenar
  }

  tickWater(dt) {
    const W = this.water;
    if (!W || !W.group.visible) return;
    W.tick(dt, true);
    this.stats.waterTime = W.t;
    this.stats.waterLevel = W.level;
    this.stats.drops = W.stats.drops;
    this.stats.impacts = W.stats.impacts;
  }

  dropAt(x, y, size) { if (this.water) this.water.dropAt(x, y, size); }
  randomDrop() { if (this.water) this.water.randomDrop(1.8); }
  makeWaves() { if (this.water) this.water.makeWaves(); }
  setRain(on) { this.rain = on; if (this.water) this.water.rain = on; }

  // Tocar el agua deja caer una gota; pasar el mouse por encima deja una estela.
  setupPointer() {
    const el = this.renderer.domElement;
    this.ray = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let down = null, lastHover = 0;
    const hit = (ev) => {
      const W = this.water;
      if (!W || !W.group.visible) return null;
      const b = el.getBoundingClientRect();
      ndc.set(((ev.clientX - b.left) / b.width) * 2 - 1, -((ev.clientY - b.top) / b.height) * 2 + 1);
      this.ray.setFromCamera(ndc, this.camera);
      const h = this.ray.intersectObject(W.top, false)[0];
      return h ? W.top.worldToLocal(h.point.clone()) : null;
    };
    this.waterHit = hit;
    el.addEventListener("pointerdown", (ev) => { down = { x: ev.clientX, y: ev.clientY, t: performance.now() }; });
    el.addEventListener("pointerup", (ev) => {
      if (!down) return;
      const tap = Math.hypot(ev.clientX - down.x, ev.clientY - down.y) < 6 && performance.now() - down.t < 450;
      down = null;
      if (!tap) return;
      const p = hit(ev);
      if (p) { this.water.dropAt(p.x, p.y, 2.0); this.stats.taps = (this.stats.taps || 0) + 1; }
    });
    el.addEventListener("pointermove", (ev) => {
      if (ev.buttons || ev.pointerType === "touch") return;
      const now = performance.now();
      if (now - lastHover < 40) return;
      lastHover = now;
      const p = hit(ev);
      if (p) this.water.impulse(p.x, p.y, 0.35, 1.8);
    });
  }

  // ------------------------------------------------------------ piezas separadas
  // k de 0 (armada) a 1: la maceta (con tierra y plantas) sube y deja ver el plato y el agua.
  setExplode(k) {
    this.explode = Math.max(0, Math.min(1, k));
    this.applyExplode();
  }

  explodeOffset() {
    const pot = this.model.getObjectByName("MACETA");
    if (!pot || !this.model.getObjectByName("PLATO")) return 0;
    if (!pot.geometry.boundingBox) pot.geometry.computeBoundingBox();
    const bb = pot.geometry.boundingBox;
    return this.explode * (bb.max.z - bb.min.z) * 0.95;
  }

  // Despiece escalonado: plato quieto, maceta arriba, tierra un poco más y las plantas arriba de todo.
  applyExplode() {
    if (this.slicer.on) return;
    const off = this.explodeOffset();
    const pot = this.model.getObjectByName("MACETA");
    if (pot) pot.position.z = off;
    this.plants.position.y = off + (this.lift || 0);      // lift: la maceta sentada en un estante
    const H = off / 0.95 / Math.max(this.explode, 1e-6);
    for (const g of this.plants.children) {
      const b = g.userData.base;
      if (!b) continue;
      const extra = !pot || !this.model.getObjectByName("PLATO") ? 0 : this.explode * H * (g.userData.k < 0 ? 0.3 : 0.62);
      g.position.z = b[2] + extra;
    }
    this.stats.explodeOffset = off;
  }

  // Animación en loop: arma y desarma mostrando cada pieza (con la cámara girando despacio).
  setExplodeLoop(on) {
    this.loop = on ? { t: 0 } : null;
    this.controls.autoRotate = on;
    this.controls.autoRotateSpeed = 1.6;
    if (!on) this.setExplode(this.explode);
  }

  tickExplode(dt) {
    const L = this.loop;
    if (!L || this.slicer.on) return;
    L.t += dt;
    const ph = [0.8, 1.8, 2.6, 1.8];          // armada, se abre, abierta, se cierra
    const T = ph.reduce((a, b) => a + b, 0);
    let t = L.t % T, k = 0;
    const ease = (u) => u * u * (3 - 2 * u);
    if (t < ph[0]) k = 0;
    else if ((t -= ph[0]) < ph[1]) k = ease(t / ph[1]);
    else if ((t -= ph[1]) < ph[2]) k = 1;
    else k = 1 - ease((t - ph[2]) / ph[3]);
    this.explode = k;
    this.applyExplode();
    this.stats.loopCycles = Math.floor(L.t / T);
    if (this.onExplode) this.onExplode(k);
  }

  // Etiquetas de cada pieza, proyectadas en pantalla (las dibuja la página).
  partLabels(names = {}) {
    if (this.explode < 0.05 || this.slicer.on) return [];
    const out = [];
    const v = new THREE.Vector3();
    const bb = new THREE.Box3();
    // cada etiqueta al costado de su pieza; el agua a la izquierda para no pisar al plato
    const add = (obj, text, key, left = false) => {
      if (!obj || !obj.visible) return;
      bb.setFromObject(obj);
      if (bb.isEmpty()) return;
      const c = bb.getCenter(new THREE.Vector3());
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(this.camera.quaternion);
      const r = bb.getSize(new THREE.Vector3()).length() * 0.42;
      v.copy(c).addScaledVector(right, left ? -r : r).project(this.camera);
      out.push({ key, text, x: (v.x + 1) / 2, y: (1 - v.y) / 2, left });
    };
    const pls = (this.plants.children || []).filter((g) => g.userData.k >= 0);
    pls.forEach((g, i) => add(g, names[g.userData.id] || "Planta", "planta-" + i));
    add(this.plants.children.find((g) => g.userData.k < 0), names.tierra || "Tierra", "tierra");
    add(this.model.getObjectByName("MACETA"), "Maceta", "maceta");
    if (this.water && this.water.group.visible) add(this.water.top, "Agua de reserva", "agua", true);
    add(this.model.getObjectByName("PLATO"), "Plato con rosca", "plato");
    return out;
  }

  // ------------------------------------------------------------ modo slicer
  setSlicer(on, part) {
    const S = this.slicer;
    if (part) S.part = part;
    if (S.on && !on) this.exitSlicer();
    S.on = on;
    if (on) this.enterSlicer();
    return this.slicerInfo();
  }

  enterSlicer() {
    const S = this.slicer;
    this.exitSlicer(true);
    const src = this.model.getObjectByName(S.part) || this.model.getObjectByName("MACETA");
    if (!src) return;
    S.part = src.name;
    const geo = src.geometry;
    geo.computeBoundingBox();
    const bb = geo.boundingBox;
    S.height = bb.max.z - bb.min.z;
    S.layers = Math.ceil(S.height / LAYER_MM - 1e-6);
    S.layer = S.layer > 0 ? Math.min(S.layer, S.layers) : S.layers;
    // la pieza sola, apoyada en la cama, centrada
    const g = (S.group = new THREE.Group());
    g.rotation.x = -Math.PI / 2;
    g.name = "SLICER";
    const color = this.mats[S.part === "PLATO" ? "PLATO" : "MACETA"].color.clone();
    S.mat = slicerMaterial(color, S.uniforms);
    S.mat.clippingPlanes = [S.plane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0)];
    const mesh = new THREE.Mesh(geo, S.mat);
    mesh.position.set(-(bb.min.x + bb.max.x) / 2, -(bb.min.y + bb.max.y) / 2, -bb.min.z);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.name = "PIEZA_" + S.part;
    S.mesh = mesh;
    S.segs = new Float32Array(geo.index.count * 2);
    S.raw = new Float32Array(geo.index.count * 2);
    S.acc = new Float32Array(geo.index.count / 3 + 1);
    const lg = new THREE.BufferGeometry();
    lg.setAttribute("position", new THREE.BufferAttribute(S.segs, 3));
    S.lines = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0xff7a1a, depthTest: false }));
    S.lines.renderOrder = 10;
    S.lines.frustumCulled = false;
    S.lines.position.copy(mesh.position);
    S.lines.name = "CONTORNO_CAPA";
    const hb = buildPrintHead();
    S.head = hb.head;
    S.bar = hb.bar;
    S.head.position.copy(mesh.position);
    S.bar.position.copy(mesh.position);
    g.add(buildPlate(), mesh, S.lines, S.head, S.bar);
    this.scene.add(g);
    // se esconde lo demás
    S.hidden = [this.model, this.plants, this.sceneGroup, this.contact].filter((o) => o && o.visible);
    for (const o of S.hidden) o.visible = false;
    this.setLayer(S.layer);
    const fb = new THREE.Box3().setFromObject(mesh);
    fb.max.y += 55;                                   // que entre el cabezal
    fb.expandByScalar(12);
    this.fit(fb, new THREE.Vector3(-0.5, 0.55, 1));
  }

  exitSlicer(silent) {
    const S = this.slicer;
    if (S.group) {
      this.scene.remove(S.group);
      S.lines.geometry.dispose();
      S.mat.dispose();
      S.group = null;
    }
    for (const o of S.hidden || []) o.visible = true;
    S.hidden = [];
    S.playing = false;
    if (!silent) {
      if (this.water) this.water.group.visible = this.waterOn;
      this.fit(new THREE.Box3().setFromObject(this.model).union(new THREE.Box3().setFromObject(this.plants)));
    }
  }

  setLayer(n) {
    const S = this.slicer;
    if (!S.group) return this.slicerInfo();
    S.layer = Math.max(1, Math.min(S.layers, Math.round(n)));
    const zc = S.layer * LAYER_MM;
    S.uniforms.uCut.value = zc + (S.mesh.geometry.boundingBox.min.z);  // en coordenadas de la malla
    // plano de corte en el mundo: y <= zc (la cama está en y = 0)
    S.plane.constant = zc + 1e-3;
    const bbz = S.mesh.geometry.boundingBox;
    const zMesh = Math.min(zc - LAYER_MM * 0.5, S.height - 0.05) + bbz.min.z;
    const raw = sliceSegments(S.mesh.geometry, zMesh, S.raw);
    S.nv = orderSegments(S.raw, raw, S.segs, S.acc);       // recorrido continuo de la boquilla
    S.zMesh = zMesh;
    S.lines.geometry.attributes.position.needsUpdate = true;
    S.segments = S.nv / 2;
    this.setLayerProgress(1);
    return this.slicerInfo();
  }

  // p de 0 a 1: cuánto del recorrido de la capa actual ya hizo la boquilla.
  setLayerProgress(p) {
    const S = this.slicer;
    const n = S.nv / 2;
    let done = n;
    let x = 0, y = 0;
    if (n > 0) {
      const L = S.acc[n - 1] * p;
      done = p >= 1 ? n : Math.max(0, S.acc.subarray(0, n).findIndex((a) => a >= L));
      const k = Math.min(n - 1, done) * 2 * 3;
      x = S.segs[k]; y = S.segs[k + 1];
    }
    S.lines.geometry.setDrawRange(0, done * 2);
    S.progress = p;
    // la boquilla apoya sobre la capa que imprime; la barra del eje X la acompaña
    const base = S.mesh.position;
    S.head.position.set(base.x + x, base.y + y, base.z + S.zMesh + LAYER_MM * 0.5);
    S.bar.position.set(base.x, base.y + y, base.z + S.zMesh + 64);
    S.head.userData.glow.intensity = S.playing ? 30 : 0;
  }

  playSlicer(on) {
    const S = this.slicer;
    S.playing = on;
    S.playAcc = 0;
    if (on && S.layer >= S.layers) this.setLayer(1);
    if (S.group) this.setLayerProgress(on ? 0 : 1);
  }

  tickSlicer(dt) {
    const S = this.slicer;
    if (!S.on || !S.playing) return;
    // ~30 s para toda la pieza; dentro de cada capa la boquilla recorre el contorno
    const rate = Math.max(3, S.layers / 30);
    S.playAcc = (S.playAcc || 0) + dt * rate;
    if (S.playAcc >= 1) {
      const step = Math.floor(S.playAcc);
      S.playAcc -= step;
      this.setLayer(S.layer + step);
      if (S.layer >= S.layers) { S.playing = false; S.playAcc = 0; this.setLayerProgress(1); }
      if (this.onSlicer) this.onSlicer(this.slicerInfo());
    }
    if (S.playing) this.setLayerProgress(S.playAcc);
  }

  // capas de 0,2 mm de cada pieza (para la guía)
  pieceLayers() {
    const out = {};
    for (const n of ["MACETA", "PLATO"]) {
      const m = this.model.getObjectByName(n);
      if (!m) continue;
      if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
      const b = m.geometry.boundingBox;
      out[n === "MACETA" ? "maceta" : "plato"] = Math.ceil((b.max.z - b.min.z) / LAYER_MM - 1e-6);
    }
    return out;
  }

  slicerInfo() {
    const S = this.slicer;
    return { on: S.on, part: S.part, layer: S.layer, layers: S.layers, z: +(S.layer * LAYER_MM).toFixed(2),
      height: S.height || 0, segments: S.segments || 0, playing: S.playing, clip: S.plane ? S.plane.constant : null,
      progress: S.progress ?? 1, head: S.head ? S.head.position.toArray() : null };
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
        g.userData = { id: ids[k], k, base: b.slice() };
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
    this.applyExplode();
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
    // en el jardín la cámara baja (a la altura de la maceta) para ver el fondo
    const prevDir = this.viewDir;
    this.viewDir = S.viewDir ? new THREE.Vector3(...S.viewDir) : null;
    this.viewDist = S.viewDist || null;
    if (this.viewDir || prevDir) this.fit(new THREE.Box3().setFromObject(this.model).union(new THREE.Box3().setFromObject(this.plants)));
    this.setPano(S.pano);
    if (S.build) {
      this.sceneGroup = S.build(THREE);
      this.sceneGroup.name = "ESCENARIO";
      this.sceneGroup.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = !o.userData.noShadow; } });
      this.scene.add(this.sceneGroup);
      this.fitScene();
    }
    const bg = S.stage || LIGHTS[this.lightKey].stage;
    this.host.parentElement.style.background = bg;
    if (S.light) this.setLight(S.light, S.sun ? S.sun[0] : undefined);
    this.altOverride = S.sun ? S.sun[1] : null;
    this.placeSun();
  }

  // Fondo fotográfico (foto 360° real) desenfocado como en una foto de producto, y
  // la misma foto como luz ambiente (reflejos y color de la luz del jardín).
  setPano(P) {
    this.scene.background = null;
    this.scene.environment = this.lowPower ? null : this.envTex;
    this.stats.panoLoaded = false;
    if (!P) return;
    const done = (tex) => {
      if (SCENES[this.sceneKey].pano !== P) return;
      this.scene.background = tex;
      this.scene.backgroundBlurriness = P.blur;
      this.scene.backgroundIntensity = P.intensity || 1;
      this.scene.backgroundRotation.y = THREE.MathUtils.degToRad(P.rot || 0);
      if (!this.lowPower) {
        this.scene.environment = tex;
        this.scene.environmentRotation.y = this.scene.backgroundRotation.y;
      }
      this.stats.panoLoaded = true;
    };
    if (P.tex) done(P.tex);
    else new THREE.TextureLoader().load(P.url, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.mapping = THREE.EquirectangularReflectionMapping;
      P.tex = tex;
      done(tex);
    });
  }

  // los escenarios están modelados para una maceta de ~150 mm; se escalan con la maceta
  fitScene() {
    if (!this.sceneGroup) return;
    const box = this.baseBox();
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
  photo(w = 1080, h = 1350, mime = "image/png") {
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
    if (!prevBg) this.scene.background = tex;
    r.render(this.scene, this.camera);
    const url = r.domElement.toDataURL(mime, 0.9);
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

const TEX = {};
function loadTex(THREE, url, srgb) {
  if (!TEX[url]) {
    TEX[url] = new THREE.TextureLoader().load(url);
    TEX[url].colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    TEX[url].wrapS = TEX[url].wrapT = THREE.RepeatWrapping;
    TEX[url].anisotropy = 8;
  }
  return TEX[url];
}

function buildJardin(THREE) {
  const g = new THREE.Group();
  const d = "assets/escenarios/";
  const rep = (t) => { const c = t.clone(); c.repeat.set(1.5, 1.0); c.needsUpdate = true; return c; };
  const madera = new THREE.MeshStandardMaterial({
    map: rep(loadTex(THREE, d + "madera_color.jpg", true)),
    normalMap: rep(loadTex(THREE, d + "madera_normal.jpg", false)), normalScale: new THREE.Vector2(0.9, 0.9),
    roughnessMap: rep(loadTex(THREE, d + "madera_rugosidad.jpg", false)), roughness: 1, metalness: 0 });
  // tapa de la mesa (tablas a lo largo de X) y su canto
  g.add(box(THREE, madera, 820, 34, 540, 0, -17, -60, "mesa_jardin"));
  const canto = std(THREE, 0x6e4a2e, 0.85);
  g.add(box(THREE, canto, 830, 50, 18, 0, -40, 214));
  // hojas caídas y una piedrita sobre la mesa
  const hoja = new THREE.Shape();
  hoja.moveTo(0, 0); hoja.quadraticCurveTo(9, 10, 0, 26); hoja.quadraticCurveTo(-9, 10, 0, 0);
  const hg = new THREE.ShapeGeometry(hoja, 8);
  const cols = [0x6f8f3a, 0x9aa645, 0xc9a23c, 0x8a6a2c];
  [[-140, 95, 0.6], [-105, 140, 2.2], [150, 120, 4.1], [190, 30, 1.2], [-175, -25, 5.4]].forEach(([x, z, r], i) => {
    const m = new THREE.Mesh(hg, new THREE.MeshStandardMaterial({ color: cols[i % 4], roughness: 0.7, side: THREE.DoubleSide }));
    m.rotation.set(-Math.PI / 2 + 0.06, 0, r);
    m.position.set(x, 0.6, z);
    m.scale.setScalar(2.2 + (i % 3) * 0.4);
    m.userData.noShadow = true;
    if (!i) m.name = "hojas";
    g.add(m);
  });
  const piedra = new THREE.Mesh(new THREE.IcosahedronGeometry(14, 2), std(THREE, 0x9b968c, 0.9));
  piedra.scale.set(1.4, 0.55, 1);
  piedra.position.set(170, 6, -60);
  g.add(piedra);
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

// vistas fijas (dirección desde la pieza hacia la cámara; y arriba, z hacia el frente)
export const VISTAS = {
  frente: { label: "Frente", titulo: "Vista de frente", dir: [0, 0, 1] },
  atras: { label: "Atrás", titulo: "Vista de atrás", dir: [0, 0, -1] },
  izquierda: { label: "Izq.", titulo: "Vista desde la izquierda", dir: [-1, 0, 0] },
  derecha: { label: "Der.", titulo: "Vista desde la derecha", dir: [1, 0, 0] },
  arriba: { label: "Arriba", titulo: "Vista desde arriba", dir: [0, 1, 0] },
  abajo: { label: "Abajo", titulo: "Vista desde abajo", dir: [0, -1, 0] },
  tres4: { label: "3/4", titulo: "Vista en perspectiva", dir: [-0.6, 0.55, 1] },
};

export const SCENES = {
  estudio: { label: "Estudio" },
  oficina: { label: "Oficina", build: buildOficina, light: "manana",
    stage: "linear-gradient(180deg, #ece7de 0%, #ddd5c8 100%)", sky: ["#ece7de", "#d8cfc1"] },
  // mesa de madera al aire libre con el jardín real (foto 360° de Poly Haven, CC0) desenfocado atrás
  jardin: { label: "Jardín", build: buildJardin, light: "manana", sun: [62, 40],
    stage: "linear-gradient(180deg, #8fc6ee 0%, #cfe6c0 100%)", viewDir: [-0.45, 0.22, 1], viewDist: 1.6,
    pano: { url: "assets/escenarios/jardin_chino.jpg", blur: 0.14, intensity: 1.0, rot: 70 } },
  taller: { label: "Taller", build: buildTaller, light: "estudio",
    stage: "linear-gradient(180deg, #d9cdbb 0%, #b9a88f 100%)", sky: ["#d9cdbb", "#b3a186"] },
};
