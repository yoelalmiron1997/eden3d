# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Autotest (Python puro: corre en Rhino/Grasshopper y fuera)
===================================================================
Verifica el autorriego con rosca y la geometría de cada diseño, sin librerías
externas. En Grasshopper: botón `tests`. Fuera: python eden_selftest.py [CODIGO ...]

Qué revisa por diseño (modo Autorriego con rosca):
  1. se genera y es válido; maceta y plato son sólidos cerrados (cada arista
     compartida por 2 triángulos con orientación opuesta);
  2. la base de la maceta queda a 1-2 mm del piso del plato (casi apoyada; el
     agua pasa por debajo);
  3. tiene agujeros de drenaje y quedan bajo el nivel de "tierra mojada";
  4. con el plato lleno hay >= 8 mm de tierra en remojo y el agua no rebalsa;
  5. rosca de >= 4 vueltas (o avisa si la altura no da) con holgura imprimible;
  6. la maceta no toca la pared del plato (muestreo de vértices);
  7. tiempo de cálculo.
Los tests completos con booleanas exactas están en tests/ (pytest + trimesh).
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eden_catalog as ec  # noqa: E402
import eden_core as core  # noqa: E402


def closed_manifold(F):
    """True si cada arista dirigida aparece una vez y su opuesta también."""
    seen = set()
    for a, b, c in F:
        for e in ((a, b), (b, c), (c, a)):
            if e in seen:
                return False
            seen.add(e)
    for a, b in seen:
        if (b, a) not in seen:
            return False
    return True


def check_design(cat, code, size="S", quality="preview", ovr=None):
    """Devuelve (ok, [líneas])."""
    out, ok = [], True

    def bad(msg):
        out.append("   FALLA: " + msg)
        return False

    d = ec.find_design(cat, code)
    p = ec.design_params(cat, d, size, "screw_dish_sw", "leaf", quality, ovr or {})
    t0 = time.time()
    res = core.build_pot(p)
    dt = time.time() - t0
    rep = res["report"]
    if not rep.get("valid"):
        # tamaños chicos: probar drenaje circular antes de dar por fallado
        p = ec.design_params(cat, d, size, "screw_dish_sw", "circle", quality, ovr or {})
        res = core.build_pot(p)
        rep = res["report"]
        if not rep.get("valid"):
            return False, ["%s-%s: NO SE GENERA: %s" % (code, size, rep["errors"][:2])]
    A = rep["assembly"]
    dish = res["parts"][0]
    # 1. sólidos cerrados
    if not closed_manifold(res["faces"]):
        ok = bad("la maceta no es un sólido cerrado")
    if not closed_manifold(dish["faces"]):
        ok = bad("el plato no es un sólido cerrado")
    # 2. luz bajo la maceta
    lift = A["pot_bottom_z_mm"] - A.get("pot_drop_on_seat_mm", 0.0)
    zmin = min(v[2] for v in res["vertices"]) + lift
    gap = zmin - A["dish_floor_mm"]
    if not 1.0 <= gap <= 2.0:
        ok = bad("luz bajo la maceta %.2f mm (debe ser 1-2 mm)" % gap)
    # 3. drenajes bajo el nivel de tierra mojada
    if not rep.get("drain_holes"):
        ok = bad("sin agujeros de drenaje: el agua no entra")
    if not zmin < A["water_min_wet_level_mm"]:
        ok = bad("el nivel mínimo de agua no llega a la base")
    # 4. agua con el plato lleno
    if A["water_over_soil_mm"] < 8.0:
        ok = bad("plato lleno: sólo %.1f mm de tierra en remojo" % A["water_over_soil_mm"])
    if A["water_level_max_mm"] > A["dish_low_mm"] - 1.9:
        ok = bad("el agua rebalsa por el borde bajo")
    # 5. rosca
    if A["thread_turns"] < 4.0:
        msg = "rosca de %.2f vueltas" % A["thread_turns"]
        if any("vueltas" in w for w in rep["warnings"]):
            out.append("   aviso: %s (la altura de la maceta no da para 4)" % msg)
        else:
            ok = bad(msg)
    if A["thread_gap_mm"] < 0.15:
        ok = bad("holgura de rosca %.2f mm" % A["thread_gap_mm"])
    # 6. pared del plato vs. maceta (vértices de la maceta armada)
    t = math.tan(math.radians(A["dish_flare_deg"]))
    worst = float("inf")
    for i in range(0, len(res["vertices"]), 7):
        x, y, z = res["vertices"][i]
        z += lift
        if z > A["tray_h_mm"]:
            continue
        r_wall = A["dish_inner_r0_mm"] + max(z - A["dish_floor_mm"], 0.0) * t
        worst = min(worst, r_wall - math.hypot(x, y))
    if worst < 1.0:
        ok = bad("la maceta queda a %.2f mm de la pared del plato" % worst)
    out.insert(0, "%s %s-%s: %.1f s · luz %.1f mm · rosca %.2f v · agua mín %s ml / lleno %s ml"
               " · %.0f mm de tierra en remojo · pared %.1f mm"
               % ("OK   " if ok else "FALLA", code, size, dt, gap, A["thread_turns"],
                  A["water_min_wet_ml"], A["water_reservoir_ml"], A["water_over_soil_mm"],
                  worst))
    return ok, out


def run(cat, codes=None, sizes=("S", "M"), log=print, quality="preview"):
    codes = codes or [d["code"] for d in cat["designs"]]
    t0 = time.time()
    n_ok = n = 0
    for code in codes:
        for s in sizes:
            ok, lines = check_design(cat, code, s, quality)
            n += 1
            n_ok += ok
            for ln in lines:
                log(ln)
    log("RESUMEN: %d/%d OK en %.0f s" % (n_ok, n, time.time() - t0))
    return n_ok == n


if __name__ == "__main__":
    cat = ec.load_catalog(os.path.join(HERE, "colecciones", "catalogo_eden3d.json"))
    sys.exit(0 if run(cat, sys.argv[1:] or None) else 1)
