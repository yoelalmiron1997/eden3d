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
