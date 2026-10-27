// © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados.
// Vista "modo slicer": la pieza apoyada en la cama de la impresora, cortada en la
// capa elegida, con las líneas de capa a la vista y el contorno de la capa actual.
import * as THREE from "three";

export const LAYER_MM = 0.2;

export function slicerMaterial(color, uniforms) {
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0, side: THREE.DoubleSide });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uCut = uniforms.uCut;
    sh.uniforms.uLayer = uniforms.uLayer;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vZ;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvZ = position.z;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying float vZ;\nuniform float uCut;\nuniform float uLayer;")
      .replace("#include <color_fragment>", `#include <color_fragment>
        // líneas de capa (como se ven en la pieza impresa) y la capa actual resaltada
        float f = fract(vZ / uLayer);
        float line = smoothstep(0.0, 0.18, f) * smoothstep(1.0, 0.82, f);
        diffuseColor.rgb *= mix(0.78, 1.0, line);
        if (vZ > uCut - uLayer) diffuseColor.rgb = vec3(1.0, 0.45, 0.08);
        if (!gl_FrontFacing) diffuseColor.rgb *= 0.55;`);
  };
  m.customProgramCacheKey = () => "eden-slicer";
  return m;
}

// Segmentos donde el plano z = zc corta a la malla (contorno de la capa).
export function sliceSegments(geo, zc, out) {
  const p = geo.attributes.position.array;
  const idx = geo.index.array;
  let n = 0;
  const pts = [0, 0, 0, 0, 0, 0];
  for (let t = 0; t < idx.length; t += 3) {
    let k = 0;
    for (let e = 0; e < 3; e++) {
      const a = idx[t + e] * 3, b = idx[t + ((e + 1) % 3)] * 3;
      const za = p[a + 2] - zc, zb = p[b + 2] - zc;
      if ((za < 0) !== (zb < 0) && k < 2) {
        const u = za / (za - zb);
        pts[k * 3] = p[a] + (p[b] - p[a]) * u;
        pts[k * 3 + 1] = p[a + 1] + (p[b + 1] - p[a + 1]) * u;
        pts[k * 3 + 2] = zc;
        k++;
      }
    }
    if (k === 2) {
      if ((n + 2) * 3 > out.length) break;
      out.set(pts, n * 3);
      n += 2;
    }
  }
  return n;   // cantidad de vértices (2 por segmento)
}

// Cama de impresión (textura PEI con grilla) de 256 mm.
export function buildPlate() {
  const cv = document.createElement("canvas");
  cv.width = cv.height = 512;
  const c = cv.getContext("2d");
  c.fillStyle = "#2a2c30"; c.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) {
    c.fillStyle = `rgba(255,255,255,${Math.random() * 0.05})`;
    c.fillRect(Math.random() * 512, Math.random() * 512, 1.5, 1.5);
  }
  c.strokeStyle = "rgba(255,255,255,0.13)"; c.lineWidth = 1;
  for (let i = 0; i <= 512; i += 32) {
    c.beginPath(); c.moveTo(i, 0); c.lineTo(i, 512); c.stroke();
    c.beginPath(); c.moveTo(0, i); c.lineTo(512, i); c.stroke();
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const plate = new THREE.Mesh(new THREE.BoxGeometry(256, 256, 4),
    new THREE.MeshStandardMaterial({ map: tex, roughness: 0.55, metalness: 0.2 }));
  plate.position.z = -2;
  plate.name = "CAMA";
  plate.receiveShadow = true;
  return plate;
}

// Ordena los segmentos sueltos del corte en recorridos continuos (como los hace la
// boquilla): devuelve la cantidad de vértices escritos en `out` (en pares, ordenados)
// y las longitudes acumuladas por segmento en `acc`.
export function orderSegments(src, nv, out, acc) {
  const ns = nv / 2;
  const key = (x, y) => Math.round(x * 200) + "," + Math.round(y * 200);
  const map = new Map();
  for (let s = 0; s < ns; s++) {
    for (let e = 0; e < 2; e++) {
      const k = key(src[(s * 2 + e) * 3], src[(s * 2 + e) * 3 + 1]);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(s * 2 + e);
    }
  }
  const used = new Uint8Array(ns);
  let w = 0, total = 0;
  const put = (vi) => {
    out[w * 3] = src[vi * 3]; out[w * 3 + 1] = src[vi * 3 + 1]; out[w * 3 + 2] = src[vi * 3 + 2];
    w++;
  };
  for (let s0 = 0; s0 < ns; s0++) {
    if (used[s0]) continue;
    let s = s0, from = s0 * 2;               // recorre desde el extremo 0
    while (s >= 0) {
      used[s] = 1;
      const to = from ^ 1;
      put(from); put(to);
      const dx = src[to * 3] - src[from * 3], dy = src[to * 3 + 1] - src[from * 3 + 1];
      total += Math.hypot(dx, dy);
      acc[w / 2 - 1] = total;
      // siguiente segmento que empieza donde terminó este
      const cand = map.get(key(src[to * 3], src[to * 3 + 1])) || [];
      s = -1;
      for (const v of cand) {
        const sv = v >> 1;
        if (!used[sv]) { s = sv; from = v; break; }
      }
    }
  }
  return w;
}

// Cabezal de impresión (boquilla de bronce, bloque calefactor, disipador y ventilador)
// y la barra del eje X, en coordenadas de la pieza (Z hacia arriba, punta en z = 0).
export function buildPrintHead() {
  const head = new THREE.Group();
  head.name = "CABEZAL";
  const bronce = new THREE.MeshStandardMaterial({ color: 0xc8963e, metalness: 0.9, roughness: 0.3 });
  const alu = new THREE.MeshStandardMaterial({ color: 0xb9bec4, metalness: 0.8, roughness: 0.35 });
  const negro = new THREE.MeshStandardMaterial({ color: 0x24262a, metalness: 0.1, roughness: 0.6 });
  const nozzle = new THREE.Mesh(new THREE.ConeGeometry(3.2, 5, 16), bronce);
  nozzle.rotation.x = -Math.PI / 2;
  nozzle.position.z = 2.5;
  const hex = new THREE.Mesh(new THREE.CylinderGeometry(4, 4, 3, 6), bronce);
  hex.rotation.x = Math.PI / 2;
  hex.position.z = 6.2;
  const block = new THREE.Mesh(new THREE.BoxGeometry(20, 16, 10), alu);
  block.position.set(4, 0, 12.5);
  const sink = new THREE.Mesh(new THREE.CylinderGeometry(9, 9, 24, 20), alu);
  sink.rotation.x = Math.PI / 2;
  sink.position.z = 30;
  const shroud = new THREE.Mesh(new THREE.BoxGeometry(34, 28, 38), negro);
  shroud.position.set(0, -6, 34);
  const fan = new THREE.Mesh(new THREE.CylinderGeometry(13, 13, 2, 24), new THREE.MeshStandardMaterial({ color: 0x3a3d42 }));
  fan.position.set(0, -24, 34);
  const glow = new THREE.PointLight(0xff8a3d, 0, 40, 2);
  glow.position.z = 1;
  head.add(nozzle, hex, block, sink, shroud, fan, glow);
  head.userData.glow = glow;
  head.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  const bar = new THREE.Mesh(new THREE.BoxGeometry(260, 12, 12),
    new THREE.MeshStandardMaterial({ color: 0x9aa1a8, metalness: 0.7, roughness: 0.4 }));
  bar.name = "EJE_X";
  return { head, bar };
}
