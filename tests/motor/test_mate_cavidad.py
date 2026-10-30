# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Cavidad del inserto para la animación del cebado (MAT-022)."""
import os

import pytest

import mate_core as mc
import mate_web

HERE = os.path.dirname(os.path.abspath(__file__))


def radio_ext(rz, z):
    best = 0.0
    for (r1, z1), (r2, z2) in zip(rz, rz[1:]):
        if min(z1, z2) - 1e-9 <= z <= max(z1, z2) + 1e-9:
            best = max(best, min(r1, r2) if abs(z2 - z1) < 1e-9 else r1 + (z - z1) * (r2 - r1) / (z2 - z1))
    return best


@pytest.mark.spec("MAT-022")
@pytest.mark.parametrize("ins", ["polimero", "adaptador", "ambos", "propio"])
def test_cavidad_adentro_del_inserto(ins, tmp_path):
    o = {"tipo": "imperial_clasico", "inserto": ins}
    if ins == "propio":
        p = os.path.join(HERE, "insertos", "Polimero_Mate.stl")
        o["stl_path"] = p
    r = mate_web.build(o)
    cav = r["summary"]["cavidad"]
    res = mate_web._resultado(o)
    canon, _, _ = mc.hueco_de(res["opts"])
    H = res["params"]["H"]
    rz = mc.colocar_hueco(mc.perfil_hueco(canon, 0.0, 0.0, 0.0), H, 0.0)
    z_bot = min(z for _, z in rz)
    assert cav["fondo"] == pytest.approx(z_bot + 3.0, abs=0.01)
    assert cav["boca"] == pytest.approx(max(z for _, z in rz), abs=0.01)
    assert cav["boca"] == pytest.approx(H, abs=0.5)
    zs, rs = cav["z"], cav["r"]
    assert len(zs) == len(rs) > 20
    assert all(b - a == pytest.approx(1.0, abs=0.011) for a, b in zip(zs, zs[1:]))
    for z, r in zip(zs, rs):
        lim = min(radio_ext(rz, z), radio_ext(rz, max(cav["fondo"], z - 4.5))) - 2.0
        assert 0 < r <= lim + 0.01
