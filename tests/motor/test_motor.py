# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Motor, exportación, fondos y tiempos."""
import json
import os
import time
import zipfile

import numpy as np
import pytest
import trimesh
from PIL import Image

from motor_helpers import ROOT, build, catalog, design_codes

import eden_catalog as ec
import eden_core as core
import eden_selftest


@pytest.mark.spec("GEO-002")
@pytest.mark.parametrize("code", design_codes())
def test_autotest_de_grasshopper(code):
    """El mismo autotest que corre el botón `tests` en Grasshopper."""
    ok, lines = eden_selftest.check_design(catalog(), code, "S")
    assert ok, "\n".join(lines)


@pytest.mark.spec("GEO-001")
@pytest.mark.parametrize("code", design_codes())
def test_piezas_solidas_cerradas(code):
    res = build(code, "S")
    for V, F in [(res["vertices"], res["faces"])] + [(p["vertices"], p["faces"])
                                                     for p in res["parts"]]:
        m = trimesh.Trimesh(V, F, process=True)
        assert m.is_watertight and m.is_winding_consistent and m.volume > 0


@pytest.mark.spec("GEO-003")
def test_malla_de_agua_cerrada():
    V, F = core.water_mesh(build("ROMBO", "S"))
    m = trimesh.Trimesh(V, F)
    assert m.is_watertight and m.volume > 0


@pytest.mark.spec("EXP-001")
def test_exporta_3mf_con_las_dos_piezas(tmp_path):
    res = build("ROMBO", "S", quality="preview")
    files = ec.export_set(res, str(tmp_path), write_stl=False)
    f3 = [f for f in files if f.endswith(".3mf")][0]
    assert os.path.basename(f3).startswith("Eden3D-ROMBO-S-AUTORRIEGO-HOJAS")
    with zipfile.ZipFile(f3) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert model.count("<object ") == 2


@pytest.mark.spec("PER-001")
def test_tiempos():
    """Referencias en esta máquina; en Rhino suele ser 1,5-2× más."""
    cat = catalog()
    d = ec.find_design(cat, "ROMBO")
    for q, lim in (("preview", 3.0), ("normal", 5.0)):
        p = ec.design_params(cat, d, "M", "screw_dish_sw", "leaf", q, {})
        t = time.time()
        r = core.build_pot(p)
        dt = time.time() - t
        assert r["report"]["valid"]
        assert dt < lim, "%s tardó %.1f s" % (q, dt)


@pytest.mark.spec("PER-002")
def test_superficie_no_se_recarga_si_no_cambio():
    a = core._load_surface_module()
    b = core._load_surface_module()
    assert a is b and getattr(a, "_eden_mtime", None) is not None


# ------------------------------------------------------------------- fondos
FONDOS = os.path.join(ROOT, "renders", "fondos", "naturaleza")


@pytest.mark.spec("REN-001")
def test_fondos_de_naturaleza():
    meta = json.load(open(os.path.join(FONDOS, "fondos.json"), encoding="utf-8"))
    assert {"bosque_mesa", "hojas_bokeh", "musgo_oscuro"} <= set(meta)
    for name, m in meta.items():
        assert 0.7 <= m["suelo"] <= 0.9 and m["tema"] in ("claro", "oscuro")
        im = Image.open(os.path.join(FONDOS, name + ".jpg"))
        assert im.size == (1080, 1350)
        # desenfocado: poca energía de alta frecuencia en la parte de arriba
        # (a 1/4 de tamaño, para no medir el grano). Los florales viejos dan 100-190.
        sm = im.convert("L").resize((270, 338), Image.BOX)
        g = np.asarray(sm, np.float32)[:int(338 * 0.55)]
        lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
        assert lap.var() < 45.0, "%s no parece desenfocado (%.0f)" % (name, lap.var())


@pytest.mark.spec("REN-002")
def test_escena_de_la_foto():
    """Planta, piedritas y tierra: mallas sanas y dentro de la boca de la maceta."""
    import math
    import eden_escena as es
    res = build("ROMBO", "S")
    z_top, r_in, z_s = es.opening(res["vertices"])
    sc = es.build(res["vertices"])
    assert {k for k, _, _ in sc} == {"tierra", "piedra", "arcilla", "planta"}
    for k, V, F in sc:
        m = trimesh.Trimesh(V, F, process=False)
        assert (m.area_faces > 1e-9).all(), k                # sin triángulos degenerados
        if k != "planta":                                    # la planta puede asomar afuera
            assert max(math.hypot(x, y) for x, y, _ in V) <= r_in + 0.01, k
    assert len(es.layer_uv(res["vertices"])) == len(res["vertices"])
