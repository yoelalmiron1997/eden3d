# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Autorriego con plato enroscable: ¿el agua del plato llega a la tierra?

Se arma la maceta enroscada en su plato (posición real de uso) y se "llena" el
plato con agua usando booleanas exactas (manifold3d). Se verifica que:
  * la base de la maceta queda casi apoyada en el piso del plato (luz chica);
  * con poca agua la base ya queda sumergida y el agua ENTRA por los agujeros
    de drenaje (que es lo que moja la tierra);
  * el agua es un solo volumen conectado (no quedan bolsones secos);
  * maceta y plato no se tocan (rosca y pared), y la rosca tiene >= 4 vueltas.
"""
import math

import numpy as np
import pytest
import trimesh

from motor_helpers import assembled_meshes, build, design_codes

SIZES = ["S", "M"]


def _water(pot, dish, level, outside_only=False):
    """Volumen de agua del plato hasta `level` (z armado). outside_only: solo el
    agua que queda fuera de la maceta (la de adentro la absorbe la tierra)."""
    lo, hi = dish.bounds
    R = max(abs(lo[0]), abs(lo[1]), hi[0], hi[1]) + 5.0
    z0 = 0.8                     # sobre la marca grabada en la cara de apoyo
    fill = trimesh.creation.cylinder(radius=R, height=level - z0, sections=128)
    fill.apply_translation([0, 0, (level + z0) / 2.0])
    # cuenco = casco convexo del plato menos el plato (contempla el perno)
    hull = dish.convex_hull
    cav = trimesh.boolean.difference([hull, dish], engine="manifold")
    w = trimesh.boolean.intersection([fill, cav], engine="manifold")
    w = trimesh.boolean.difference([w, pot.convex_hull if outside_only else pot],
                                   engine="manifold")
    return w


@pytest.mark.spec("AUT-001", "AUT-005")
@pytest.mark.parametrize("code", design_codes())
@pytest.mark.parametrize("size", SIZES)
def test_base_apoyada_y_rosca_larga(code, size):
    res = build(code, size)
    rep = res["report"]
    assert rep["valid"], rep["errors"]
    A = rep["assembly"]
    pot, dish = assembled_meshes(res)
    floor_top = res["parts"][0]["params"]["floor"]
    gap = pot.bounds[0][2] - floor_top
    # la maceta queda a 1-2 mm del piso: casi apoyada, pero el agua pasa por debajo
    assert 1.0 <= gap <= 2.0, gap
    assert abs(gap - A["water_gap_under_pot_mm"]) < 0.05
    assert A["thread_turns"] >= 4.0
    assert A["thread_engagement_mm"] >= 16.0
    assert A["thread_gap_mm"] >= 0.15             # holgura de rosca imprimible
    assert A["pot_dish_gap_mm"] >= 3.0             # pared del plato a la maceta


@pytest.mark.spec("AUT-002", "AUT-004")
@pytest.mark.parametrize("code", design_codes())
def test_agua_entra_por_los_drenajes(code):
    res = build(code, "S")
    A = res["report"]["assembly"]
    pot, dish = assembled_meshes(res)
    z_base = pot.bounds[0][2]
    # el nivel mínimo que informa el motor para "tierra mojada"
    z_soil = A["pot_floor_top_z_mm"]
    assert abs(z_soil - (z_base + res["params"]["floor"])) < 0.05
    w = _water(pot, dish, A["water_min_wet_level_mm"])
    assert w.is_volume and w.volume > 0
    # una sola masa de agua conectada (el agua de afuera llega abajo de la maceta)
    parts = sorted(w.split(only_watertight=False), key=lambda m: -abs(m.volume))
    assert abs(parts[0].volume) > 0.98 * w.volume
    # el agua SUBE por los agujeros de drenaje y llega a la tierra: hay agua
    # dentro de la maceta POR ENCIMA del piso interior (donde apoya la tierra),
    # fuera de la campana de la rosca
    ring = trimesh.creation.annulus(r_min=A["socket_radius_mm"] + 0.3,
                                    r_max=A["pot_floor_radius_mm"], height=1.2, sections=96)
    ring.apply_translation([0, 0, z_soil + 0.7])
    inside = trimesh.boolean.intersection([w, ring], engine="manifold")
    wet_mm3 = inside.volume if not inside.is_empty else 0.0
    assert wet_mm3 > 20.0, "el agua no entra por los drenajes (%.1f mm³)" % wet_mm3
    # el reporte (agua que hay que poner en el plato, fuera de la maceta)
    # coincide con la simulación (±15 %)
    wo = _water(pot, dish, A["water_min_wet_level_mm"], outside_only=True)
    assert abs(wo.volume / 1000.0 - A["water_min_wet_ml"]) <= 0.15 * A["water_min_wet_ml"] + 2


@pytest.mark.spec("AUT-003", "AUT-004")
@pytest.mark.parametrize("code", design_codes())
def test_plato_lleno_moja_bastante(code):
    res = build(code, "S")
    A = res["report"]["assembly"]
    # con el plato lleno el agua cubre >= 10 mm de maceta y el plato no rebalsa
    assert A["water_over_pot_base_mm"] >= 10.0
    assert A["water_over_soil_mm"] >= 8.0          # >= 8 mm de tierra en remojo
    assert A["water_level_max_mm"] <= A["dish_low_mm"] - 1.9
    pot, dish = assembled_meshes(res)
    w = _water(pot, dish, A["water_level_max_mm"], outside_only=True)
    assert abs(w.volume / 1000.0 - A["water_reservoir_ml"]) <= 0.15 * A["water_reservoir_ml"] + 2


@pytest.mark.spec("AUT-007")
@pytest.mark.parametrize("code", design_codes())
def test_maceta_y_plato_no_se_tocan(code):
    res = build(code, "S")
    pot, dish = assembled_meshes(res)
    inter = trimesh.boolean.intersection([pot, dish], engine="manifold")
    vol = 0.0 if inter.is_empty else inter.volume
    assert vol < 1.0, "interferencia de %.2f mm³" % vol


@pytest.mark.spec("AUT-006")
def test_vueltas_se_ajustan_en_macetas_bajas():
    res = build("ROMBO", "S", ovr=None)
    assert res["report"]["assembly"]["thread_turns"] == 4.0
    # una maceta muy baja reduce las vueltas en vez de romperse
    import eden_catalog as ec
    import eden_core as core
    from motor_helpers import catalog
    cat = catalog()
    p = ec.design_params(cat, ec.find_design(cat, "ROMBO"), "S", "screw_dish_sw", "leaf",
                         "preview", {})
    p["height"] = 52.0
    r = core.build_pot(p)
    turns = r["report"]["assembly"]["thread_turns"] if r["report"]["valid"] else 0
    assert 2.0 <= turns < 4.0
    assert any("vueltas" in w for w in r["report"]["warnings"])
