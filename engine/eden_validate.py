# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Validación independiente de mallas (fuera de Rhino)
============================================================
OBJETIVO  Comprobar con una librería externa (trimesh) lo que el motor
          afirma: malla cerrada, orientada, manifold, volumen positivo,
          topología correcta y espesor REAL de pared (distancia piel exterior -> piel interior).
REQUIERE  pip install trimesh scipy
USO       from eden_validate import check
          rep = check(result)          # result = eden_core.build_pot(...)
"""
import numpy as np
import trimesh


def to_trimesh(result):
    return trimesh.Trimesh(vertices=np.array(result["vertices"]),
                           faces=np.array(result["faces"]), process=False)


def check(result, n_rays=3000, seed=1):
    p = result["params"]
    m = to_trimesh(result)
    rep = {
        "watertight": bool(m.is_watertight),
        "winding_consistent": bool(m.is_winding_consistent),
        "is_volume": bool(m.is_volume),
        "volume_cm3_trimesh": round(float(m.volume) / 1000.0, 2),
        "euler_number": int(m.euler_number),
        "degenerate_faces": int((m.area_faces < 1e-10).sum()),
    }
    # topología esperada: una esfera con un "asa" por agujero -> Euler = 2 - 2·agujeros
    expected = 2 - 2 * int(result["report"].get("drain_holes", 0))
    rep["topology_ok"] = rep["euler_number"] == expected

    # --- espesor real -------------------------------------------------------
    rng = np.random.default_rng(seed)
    n = m.face_normals
    c = m.triangles_center
    r_xy = np.hypot(c[:, 0], c[:, 1])
    radial = np.einsum("ij,ij->i", n[:, :2], c[:, :2] / np.maximum(r_xy[:, None], 1e-9))
    H = c[:, 2].max()
    outer = np.where((radial > 0.3) & (c[:, 2] > p["floor"] + 1.0) & (c[:, 2] < H - 3.0))[0]
    pick = rng.choice(outer, size=min(n_rays, len(outer)), replace=False)
    # piel interior = caras orientadas hacia el eje; se muestrea densamente y
    # la distancia mínima de cada punto exterior a esa nube = espesor local
    inner = np.where((radial < -0.3) & (c[:, 2] > p["floor"] + 0.5))[0]
    sub = m.submesh([inner], append=True)
    pts, _ = trimesh.sample.sample_surface_even(sub, 600000, seed=seed) \
        if hasattr(trimesh.sample, "sample_surface_even") else trimesh.sample.sample_surface(sub, 600000)
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pts).query(c[pick])
    wall = p["wall"]
    rep["wall_nominal_mm"] = wall
    rep["wall_measured_min_mm"] = round(float(d.min()), 3)
    rep["wall_measured_p5_mm"] = round(float(np.percentile(d, 5)), 3)
    rep["wall_measured_median_mm"] = round(float(np.median(d)), 3)
    rep["wall_measured_max_mm"] = round(float(d.max()), 3)
    rep["wall_ok"] = rep["wall_measured_p5_mm"] >= 0.9 * wall and rep["wall_measured_min_mm"] >= 0.75 * wall
    rep["pass"] = all([rep["watertight"], rep["winding_consistent"], rep["is_volume"],
                       rep["topology_ok"], rep["degenerate_faces"] == 0, rep["wall_ok"]])
    return rep
