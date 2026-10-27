# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Corte del autorriego con el agua dibujada (verificación visual, sin Rhino).
USO: python tools/corte_agua.py ROMBO S salida.png
Dibuja la sección por el plano XZ de la maceta enroscada en su plato, con el
agua al nivel mínimo para mojar la tierra y al nivel máximo del plato."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "tests", "motor"))
from motor_helpers import assembled_meshes, build  # noqa: E402


def water_mesh(pot, dish, level):
    lo, hi = dish.bounds
    R = max(abs(lo[0]), abs(lo[1]), hi[0], hi[1]) + 5.0
    z0 = 0.8                     # sobre la marca grabada en la cara de apoyo
    fill = trimesh.creation.cylinder(radius=R, height=level - z0, sections=128)
    fill.apply_translation([0, 0, (level + z0) / 2.0])
    cav = trimesh.boolean.difference([dish.convex_hull, dish], engine="manifold")
    w = trimesh.boolean.intersection([fill, cav], engine="manifold")
    return trimesh.boolean.difference([w, pot], engine="manifold")


def draw_section(ax, mesh, color, alpha=1.0, z=0):
    sec = mesh.section(plane_origin=[0, 0.01, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return
    for ent in sec.discrete:
        pts = np.asarray(ent)
        ax.add_patch(Polygon(pts[:, [0, 2]], closed=True, fc=color, ec="none", alpha=alpha,
                             zorder=z))


def main(code="ROMBO", size="S", out="corte_agua.png"):
    res = build(code, size)
    A = res["report"]["assembly"]
    pot, dish = assembled_meshes(res)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.6), facecolor="white")
    for ax, (lvl, tit) in zip(axs, ((A["water_min_wet_level_mm"],
                                    "Mínimo para mojar la tierra: %s ml" % A["water_min_wet_ml"]),
                                   (A["water_level_max_mm"],
                                    "Plato lleno: %s ml" % A["water_reservoir_ml"]))):
        w = water_mesh(pot, dish, lvl)
        draw_section(ax, w, "#4aa3df", 0.85, 1)
        draw_section(ax, dish, "#5b5b5b", 1.0, 2)
        draw_section(ax, pot, "#d98c5f", 1.0, 3)
        ax.axhline(A["pot_floor_top_z_mm"], color="#2f4f2e", lw=0.8, ls="--", zorder=4)
        ax.text(pot.bounds[1][0] + 4, A["pot_floor_top_z_mm"] + 0.5, "piso de la tierra",
                fontsize=8, color="#2f4f2e")
        ax.set_title(tit, fontsize=11)
        ax.set_aspect("equal")
        lo, hi = dish.bounds
        ax.set_xlim(lo[0] - 5, hi[0] + 5)
        ax.set_ylim(-2, min(pot.bounds[1][2], 70) + 2)
        ax.set_xlabel("mm")
    fig.suptitle("Eden3D-%s-%s · autorriego: luz bajo la maceta %.1f mm · rosca %.2f vueltas · "
                 "agua sobre la tierra con plato lleno %.1f mm"
                 % (code, size, A["water_gap_under_pot_mm"], A["thread_turns"],
                    A["water_over_soil_mm"]), fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    print(main(*(a or [])))
