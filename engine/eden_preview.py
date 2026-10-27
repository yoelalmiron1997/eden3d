# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Hoja de contacto (vista previa rápida sin Rhino)
USO: python eden_preview.py colecciones/eden_wave_v1.json preview.png
REQUIERE: matplotlib, numpy
"""
import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import eden_core as core
import eden_batch

BG = "#f4f1ea"
CLAY = np.array([0.80, 0.55, 0.42])


DARK = np.array([0.24, 0.22, 0.21])
PART_COLORS = {"PLATO-OCULTO": np.array([0.55, 0.41, 0.34]),
               "PLATO-ROSCA": np.array([0.55, 0.41, 0.34]),
               "PLATO-INCLINADO": DARK, "PLATO-AUTORRIEGO": DARK, "PLATO": DARK,
               "INSERTO": np.array([0.49, 0.60, 0.43])}
RAISED = ("hidden_tray", "screw_tray", "screw_dish", "screw_dish_sw", "saucer")


def assembled(res, cut=False):
    """Lista de (triángulos, color) con las piezas en su posición de uso.
    cut=True: corte en cuarto (se quitan los triángulos con 0<θ<90°)."""
    out = [(np.array(res["vertices"])[np.array(res["faces"])], CLAY)]
    A = res["report"].get("assembly") or {}
    mode = res["params"].get("mode", "pot")
    for part in res.get("parts") or []:
        T = np.array(part["vertices"])[np.array(part["faces"])]
        if mode in RAISED:
            out[0] = (out[0][0] + np.array([0, 0, A["pot_bottom_z_mm"]
                                            - A.get("pot_drop_on_seat_mm", 0.0)]), CLAY)
        elif mode == "self_watering":
            T = T + np.array([0, 0, res["params"]["floor"] + A["reservoir_h_mm"] - A["insert_drop_on_rim_mm"]])
        out.append((T, PART_COLORS.get(part["name"], CLAY)))
    if cut:
        res_ = []
        for T, c in out:
            cen = T.mean(axis=1)
            keep = ~((cen[:, 0] > 0) & (cen[:, 1] < 0))
            res_.append((T[keep], c))
        out = res_
    return out


def draw(ax, res, title, sub, cut=False, elev=14):
    groups = assembled(res, cut)
    tri = np.concatenate([g[0] for g in groups])
    base_col = np.concatenate([np.repeat(g[1][None, :], len(g[0]), 0) for g in groups])
    V = tri.reshape(-1, 3)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    light = np.array([-0.5, -0.8, 0.6]); light /= np.linalg.norm(light)
    shade = np.clip(n @ light, 0, 1) * 0.75 + 0.25
    cols = np.clip(base_col * shade[:, None] + 0.05, 0, 1)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolors="none"))
    r = np.abs(V[:, :2]).max(); h = V[:, 2].max()
    ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(0, max(h, 2 * r) * 0.95)
    ax.set_box_aspect((1, 1, max(h, 2 * r) * 0.95 / (2 * r)))
    ax.view_init(elev=elev, azim=-60)
    ax.set_axis_off(); ax.set_facecolor(BG)
    ax.set_title(title, fontsize=11, fontweight="bold", color="#3a2e26", pad=0)
    ax.text2D(0.5, -0.02, sub, transform=ax.transAxes, ha="center", fontsize=8, color="#6b5d52")


def main(col_path, out_png):
    col = json.load(open(col_path, encoding="utf-8"))
    variants = [v for v in eden_batch.expand(col) if not v["model_id"].startswith("TEST")]
    fig = plt.figure(figsize=(3.6 * len(variants), 5.4), facecolor=BG)
    for i, p in enumerate(variants):
        p = dict(p); p["quality"] = "preview"
        res = core.build_pot(p)
        full = core.build_pot(dict(p, quality="normal"))["report"]
        ax = fig.add_subplot(1, len(variants), i + 1, projection="3d")
        sub = "%d g PLA · %d ml · voladizo %.0f°" % (full["mass_g_PLA_100pct"],
                                                  full["soil_capacity_ml"], full["overhang_max_deg"])
        A = full.get("assembly") or {}
        if A.get("water_reservoir_ml"):
            sub += "\n+ %s · agua %d ml" % (" + ".join(full.get("parts", [])), A["water_reservoir_ml"])
        draw(ax, res, p["model_id"].replace("EDEN-", ""), sub)
    fig.suptitle(col.get("collection", ""), fontsize=13, color="#3a2e26", y=0.98)
    plt.subplots_adjust(left=0, right=1, top=0.9, bottom=0.05, wspace=0)
    fig.savefig(out_png, dpi=130, facecolor=BG)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
