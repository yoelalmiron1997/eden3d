# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Marca de agua personalizada: la fuente, la validación y la cobertura de TODAS las
macetas del catálogo con textos de prueba (que ninguna pieza se rompa)."""
import pytest
import trimesh

from motor_helpers import catalog

import eden_catalog as ec
import eden_core as core
import eden_font
import eden_web

TODAS = [d["code"] for d in catalog()["designs"]]
TEXTOS = ["TecnoBear", "Ñandú 2026!", "@Mi_Jardín (3)"]


@pytest.mark.spec("MAR-001")
def test_la_fuente_tiene_todos_los_caracteres():
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789áéíóúñüÁÉÍÓÚÑÜ -_.,:!?'/+#()&@":
        assert ch in eden_font.GLYPHS, ch
    loops, segs, hw, width = eden_font.outlines("".join(sorted(eden_font.GLYPHS)), 6.0)
    assert loops and width > 0
    for ext, holes in loops:
        assert eden_font._area(ext) > 0 and all(eden_font._area(h) < 0 for h in holes)


@pytest.mark.spec("MAR-001")
@pytest.mark.parametrize("texto,error", [
    ("Hola", None), ("  muchos   espacios ", None), ("", None),
    ("x" * 21, "hasta 20"), ("Precio €5", "€"), ("emoji 🌱", "🌱"),
])
def test_valida_el_texto(texto, error):
    t, err = eden_font.check(texto)
    if error is None:
        assert err is None and "  " not in t
    else:
        assert err and error in err
    r = eden_web.check_brand(texto)
    assert (r["error"] is None) == (error is None)


@pytest.mark.spec("MAR-001")
def test_la_web_rechaza_marcas_invalidas():
    with pytest.raises(ValueError, match="no se pueden grabar"):
        eden_web.params({"design": "ROMBO", "size": "S", "brand": "Hola €"})
    p = eden_web.params({"design": "ROMBO", "size": "S", "brand": "  Tecno  Bear "})
    assert p["brand"] == "Tecno Bear"
    assert eden_web.params({"design": "ROMBO", "size": "S"})["brand"] == "Eden3D"


def _build(code, texto, size="S", drain="leaf"):
    cat = catalog()
    p = ec.design_params(cat, ec.find_design(cat, code), size, "screw_dish_sw", drain, "preview", {})
    p["brand"] = texto
    return core.build_pot(p)


@pytest.mark.spec("MAR-002")
@pytest.mark.parametrize("texto", TEXTOS)
@pytest.mark.parametrize("code", TODAS)
def test_cobertura_marca_en_cada_maceta(code, texto):
    """Cada maceta del catálogo, con cada texto de prueba: piezas cerradas y la marca
    grabada al menos en una pieza (si no entra en la base, se avisa)."""
    res = _build(code, texto)
    rep = res["report"]
    assert rep["valid"], rep["errors"]
    piezas = [("MACETA", res["vertices"], res["faces"], rep)] + \
             [(p["name"], p["vertices"], p["faces"], p["report"]) for p in res["parts"]]
    grabadas = 0
    for nombre, V, F, r in piezas:
        m = trimesh.Trimesh(V, F, process=True)
        assert m.is_watertight and m.is_winding_consistent and m.volume > 0, (code, texto, nombre)
        if r.get("brand"):
            assert r["brand"]["text"] == texto and r["brand"]["cap_h_mm"] >= 3.5
            grabadas += 1
    assert grabadas >= 1, (code, texto)
    if not rep.get("brand"):
        assert any("Marca" in w for w in rep["warnings"]), "si no entra en la maceta, se avisa"


@pytest.mark.spec("MAR-002")
@pytest.mark.parametrize("size", ["M", "XL"])
def test_cobertura_marca_en_otros_tamanos(size):
    res = _build("ROMBO", "TecnoBear", size=size)
    for V, F in [(res["vertices"], res["faces"])] + [(p["vertices"], p["faces"]) for p in res["parts"]]:
        assert trimesh.Trimesh(V, F, process=True).is_watertight
