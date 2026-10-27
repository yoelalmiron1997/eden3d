# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""El puente que usa la web (eden_web), nomenclatura y licencia."""
import array
import glob
import io
import os
import zipfile

import pytest

import eden_catalog as ec
import eden_web

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPTS = {"design": "ROMBO", "size": "S", "mode": "screw_dish_sw", "drain": "leaf",
        "quality": "preview"}


@pytest.mark.spec("EXP-002")
@pytest.mark.parametrize("opts,sku", [
    (OPTS, "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS"),
    (dict(OPTS, mode="saucer", drain="circle", size="M"), "Eden3D-ROMBO-M-PLATO-CIRCULAR"),
    (dict(OPTS, overrides={"tex_count": 36}), "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS-N36"),
    (dict(OPTS, overrides={"tex_count": 0, "basura": 3}), "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS"),
])
def test_sku(opts, sku):
    """El SKU sigue la nomenclatura y sólo los ajustes válidos agregan sufijo."""
    assert eden_web.params(opts)["model_id"] == sku


@pytest.mark.spec("WEB-002", "WEB-003")
def test_build_para_la_web():
    """Lo que recibe la web: piezas ubicadas en bytes y el resumen del autorriego."""
    r = eden_web.build(OPTS)
    s = r["summary"]
    assert s["valid"] and s["sku"] == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS"
    names = [p["name"] for p in r["parts"]]
    assert names == ["MACETA", "PLATO", "AGUA"]
    for p in r["parts"]:
        pos = array.array("f")
        pos.frombytes(p["positions"])
        idx = array.array("I")
        idx.frombytes(p["indices"])
        assert len(pos) == 3 * p["vertices"] and len(idx) == 3 * p["triangles"]
        assert max(idx) < p["vertices"]
    A = s["assembly"]
    assert A["thread_turns"] >= 4 and 1.0 <= A["water_gap_under_pot_mm"] <= 2.0
    assert A["water_min_wet_ml"] > 0 and A["water_reservoir_ml"] > A["water_min_wet_ml"]
    # la maceta está levantada sobre el plato (posición de uso)
    pot = array.array("f")
    pot.frombytes(r["parts"][0]["positions"])
    assert min(pot[2::3]) > 3.0


@pytest.mark.spec("WEB-001")
def test_info_del_catalogo():
    info = eden_web.info()
    cat = eden_web.catalog()
    assert [d["code"] for d in info["designs"]] == [d["code"] for d in cat["designs"]]
    assert len(info["designs"]) == 17
    assert {m["code"] for m in info["modes"]} == set(eden_web.WEB_MODES)


@pytest.mark.spec("EXP-001", "LIC-002")
def test_3mf_con_autoria():
    name, data = eden_web.export_3mf(dict(OPTS, quality="preview"))
    assert name == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS.3mf"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert model.count("<object ") == 2
    assert 'name="Copyright"' in model and "Eden3D" in model and "uso personal" in model


@pytest.mark.spec("WEB-008", "LIC-002")
def test_stl_con_autoria():
    name, data = eden_web.export_stl(OPTS, "MACETA")
    assert name == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS_MACETA.stl"
    assert b"Eden3D" in data[:80]
    n = int.from_bytes(data[80:84], "little")
    assert len(data) == 84 + 50 * n and n > 1000


@pytest.mark.spec("LIC-001")
def test_licencia_propietaria():
    """LICENSE de todos los derechos reservados y aviso en cada fuente del motor."""
    with open(os.path.join(REPO, "LICENSE"), encoding="utf-8") as fh:
        lic = fh.read()
    assert "Todos los derechos reservados" in lic and "Yoel Almirón" in lic
    for bad in ("MIT License", "GNU GENERAL PUBLIC", "Apache License"):
        assert bad not in lic
    fuentes = glob.glob(os.path.join(REPO, "engine", "*.py")) + \
        glob.glob(os.path.join(REPO, "web", "*.js"))
    sin_aviso = [f for f in fuentes
                 if "Todos los derechos reservados" not in open(f, encoding="utf-8").read(400)]
    assert not sin_aviso, sin_aviso
    with open(os.path.join(REPO, "web", "index.html"), encoding="utf-8") as fh:
        assert "Todos los derechos reservados" in fh.read()


@pytest.mark.spec("EXP-002")
def test_catalogo_sin_codigos_repetidos():
    """Códigos de diseño únicos = SKUs únicos."""
    cat = ec.load_catalog(eden_web.CAT_PATH)
    codes = [d["code"] for d in cat["designs"]]
    assert len(codes) == len(set(codes))
