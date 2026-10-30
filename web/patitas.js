// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Patitas articuladas en el visor: cada eslabón cuelga de su bisagra (el eje que manda el
// motor en summary.patitas). "Sentarla en el borde" la sube a un estante: las patas
// cuelgan y se balancean, y los bracitos saludan.
import * as THREE from "three";

const easeIO = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));

export class Patitas {
  constructor(viewer) {
    this.v = viewer;
    this.cadenas = [];
    this.pose = false;
    this.k = 0;                 // 0 = como sale de la impresora, 1 = sentada en el estante
    this.t = 0;
    this.estante = null;
    this.stats = { frames: 0, montajes: 0 };
    viewer.tickers = viewer.tickers || [];
    viewer.tickers.push((dt) => this.tick(dt));
  }

  // después de cada cálculo: arma la cadena de pivotes con los eslabones del visor
  montar(info) {
    this.cadenas = [];
    this.quitarEstante();
    if (!info || !info.cadenas) { this.aplicarAltura(0); return; }
    const m = this.v.model;
    for (const c of info.cadenas) {
      let padre = m, anterior = new THREE.Vector3();
      const piv = [];
      for (const e of c.eslabones) {
        const mesh = m.getObjectByName(e.parte);
        if (!mesh) continue;
        const eje = new THREE.Vector3(...e.eje);
        const p = new THREE.Object3D();
        p.name = "ART_" + e.parte;
        p.position.copy(eje).sub(anterior);
        p.userData = { dir: new THREE.Vector3(...e.dir).normalize() };
        padre.add(p);
        m.remove(mesh);
        mesh.position.copy(eje).multiplyScalar(-1);
        p.add(mesh);
        piv.push(p);
        padre = p;
        anterior = eje;
      }
      const pata = c.nombre.startsWith("PATA");
      this.cadenas.push({ nombre: c.nombre, pivotes: piv, pata, izq: c.nombre.endsWith("_I"),
        largo: c.eslabones.length, grosor: c.grosor_mm, y0: c.eslabones[0] ? c.eslabones[0].eje[1] : 0 });
    }
    this.stats.montajes++;
    if (this.pose) this.ponerEstante();
    this.posar(0);
  }

  // ángulos de cada bisagra (positivo = para abajo)
  angulos(c, t) {
    const k = this.k;
    const s = c.izq ? 0 : Math.PI;                       // las patas van alternadas
    if (c.pata) {
      return c.pivotes.map((_, i) => {
        if (i === 0) return k * (THREE.MathUtils.degToRad(80) + 0.22 * Math.sin(2.4 * t + s));
        if (i === c.pivotes.length - 1) return k * 0.18 * Math.sin(2.4 * t + s - 0.9);
        return k * (THREE.MathUtils.degToRad(6) + 0.16 * Math.sin(2.4 * t + s - 0.5 * i));
      });
    }
    // bracitos: saludan (para arriba = negativo)
    return c.pivotes.map((_, i) => (i === 0 ? -k * (0.35 + 0.3 * Math.max(0, Math.sin(3 * t + s)))
      : -k * 0.45 * Math.sin(6 * t + s)));
  }

  posar(t) {
    const q = new THREE.Quaternion();
    for (const c of this.cadenas) {
      const a = this.angulos(c, t);
      c.pivotes.forEach((p, i) => { p.quaternion.copy(q.setFromAxisAngle(p.userData.dir, a[i])); });
    }
  }

  setPose(on) {
    this.pose = on;
    if (on) this.ponerEstante();
    this.stats.pedidas = (this.stats.pedidas || 0) + 1;
  }

  tick(dt) {
    if (!this.cadenas.length) return;
    this.stats.frames++;
    const objetivo = this.pose ? 1 : 0;
    if (this.k !== objetivo) {
      this.k = Math.max(0, Math.min(1, this.k + Math.sign(objetivo - this.k) * dt / 1.2));
      this.aplicarAltura(easeIO(this.k));
      if (this.k === 0) this.quitarEstante();
    }
    if (this.k > 0) this.t += dt;
    this.posar(this.t);
  }

  // estante de madera debajo de la maceta: el borde queda justo detrás de las caderas
  ponerEstante() {
    if (this.estante || !this.cadenas.length) return;
    const patas = this.cadenas.filter((c) => c.pata);
    const box = new THREE.Box3().setFromObject(this.v.model.getObjectByName("MACETA") || this.v.model);
    const ancho = Math.max(220, (box.max.x - box.min.x) * 2.6);
    const largo = patas.reduce((a, c) => Math.max(a, c.largo), 0);
    const g = patas.reduce((a, c) => Math.max(a, c.grosor), 10);
    this.alto = Math.max(90, (largo + 1.6) * g * 1.6 + 20);
    const borde = patas.length ? patas[0].y0 + g / 2 + 1.5 : box.min.y - 2;   // las patas salen hacia -y
    const fondo = 170;
    const geo = new THREE.BoxGeometry(ancho, fondo, this.alto);
    const mat = new THREE.MeshStandardMaterial({ color: 0x9a6a3e, roughness: 0.78, metalness: 0 });
    const e = new THREE.Mesh(geo, mat);
    e.name = "ESTANTE";
    e.position.set(0, borde + fondo / 2, -this.alto / 2 - 0.05);
    e.castShadow = e.receiveShadow = true;
    this.v.model.add(e);
    this.estante = e;
  }

  quitarEstante() {
    if (!this.estante) return;
    this.v.model.remove(this.estante);
    this.estante.geometry.dispose();
    this.estante = null;
  }

  aplicarAltura(k) {
    this.v.lift = (this.alto || 0) * k;
    this.v.model.position.y = this.v.lift;
    this.v.applyExplode();
  }

  info() {
    return { cadenas: this.cadenas.map((c) => ({ nombre: c.nombre, eslabones: c.pivotes.length,
      angulos: c.pivotes.map((p) => +(2 * Math.acos(Math.min(1, Math.abs(p.quaternion.w)))).toFixed(3)) })),
      pose: this.pose, k: +this.k.toFixed(3), estante: !!this.estante, alto: this.alto || 0 };
  }
}
