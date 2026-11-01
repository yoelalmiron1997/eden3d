# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Chapitas para collares (CHA-001..004)."""
import io
import zipfile

import pytest

import chapita_core as cc
import chapita_web as cw
import eden_web as ew
import topper_core as tc

FORMAS = [k for k, _ in cc.FORMAS]
_CACHE = {}


def chapita(**o):
    k = tuple(sorted(o.items()))
    if k not in _CACHE:
        _CACHE[k] = cc.construir(o)
    return _CACHE[k]


def _celda(g, x, y):
    return int((y - g.y0) / g.res), int((x - g.x0) / g.res)


# ----------------------------------------------------------------- CHA-001
@pytest.mark.spec("CHA-001")
@pytest.mark.parametrize("forma", FORMAS)
def test_una_pieza_con_agujero(forma):
    r = chapita(forma=forma)
    g, B, rep = r["grilla"], r["placa"], r["reporte"]
    _, n, _ = tc.componentes(B, g.nx, g.ny)
    assert n == 1
    oj = rep["ojal"]
    j, i = _celda(g, oj["x"], oj["y"])
    assert not B[j][i]                                       # el agujero está abierto
    assert oj["r_ojal"] - oj["r_agujero"] >= 2.0
    j, i = _celda(g, oj["x"], oj["y"] + oj["r_agujero"] + 1.0)
    assert B[j][i]                                           # con pared arriba del agujero
    for nombre, V, F in r["piezas"]:
        assert ew.mesh_check(F)["closed"], nombre
    o = cc.opciones({"forma": forma})
    ancho, _, alto = rep["medidas_mm"]
    assert ancho == pytest.approx(o["ancho"], abs=1.0)
    assert alto == pytest.approx(o["grosor"] + o["relieve"], abs=0.02)


# ----------------------------------------------------------------- CHA-002
@pytest.mark.spec("CHA-002")
@pytest.mark.parametrize("forma", FORMAS)
def test_letras_adentro_y_grandes(forma):
    r = chapita(forma=forma)
    g, B, T, rep = r["grilla"], r["placa"], r["letras"], r["reporte"]
    assert rep["letra_mm"] >= cc.LETRA_MIN, rep["letra_mm"]
    oj = rep["ojal"]
    for j in range(g.ny):
        for i in range(g.nx):
            if T[j][i]:
                assert B[j][i]
    # nada de letra en el ojal (sólo el borde, que lo rodea)
    j, i = _celda(g, oj["x"], oj["y"])
    assert not T[j][i]


@pytest.mark.spec("CHA-002")
def test_nombre_corto_mas_grande_y_segunda_linea():
    corto = chapita(nombre="Leo")["reporte"]["letra_mm"]
    largo = chapita(nombre="Maximiliano")["reporte"]["letra_mm"]
    con2 = chapita(nombre="Leo", linea2="11 5555 1234")["reporte"]["letra_mm"]
    assert corto > largo and con2 < corto
    r = chapita(forma="circulo", ancho=28, nombre="Maximilianito")
    assert r["reporte"]["letra_mm"] < cc.LETRA_MIN and any("letra" in a.lower() for a in r["reporte"]["avisos"])


@pytest.mark.spec("CHA-002")
@pytest.mark.parametrize("o,msg", [({"nombre": "  "}, "nombre"), ({"nombre": "A" * 15}, "hasta 14"),
                                   ({"nombre": "Roma ☃"}, "tipografía")])
def test_rechazos_en_espanol(o, msg):
    with pytest.raises(ValueError) as e:
        cc.construir(o)
    assert msg in str(e.value)
    s = cw.build(o)["summary"]
    assert not s["valid"] and s["errors"]


# ----------------------------------------------------------------- CHA-003
@pytest.mark.spec("CHA-003")
def test_relieve_grabado_y_colores():
    h, rel = cc.DEFECTO["grosor"], cc.DEFECTO["relieve"]
    uno = chapita()
    assert [p[0] for p in uno["piezas"]] == ["CHAPITA"]
    doble = chapita(colores="doble")
    assert [p[0] for p in doble["piezas"]] == ["CHAPITA", "LETRAS"]
    zl = [v[2] for v in doble["piezas"][1][1]]
    assert min(zl) == pytest.approx(h - 0.01) and max(zl) == pytest.approx(h + rel)
    assert doble["reporte"]["cambio_mm"] == pytest.approx(h)
    ams = chapita(colores="ams")
    assert [p[0] for p in ams["piezas"]] == ["CHAPITA", "LETRAS"]
    zc = [v[2] for v in ams["piezas"][0][1]]
    zl = [v[2] for v in ams["piezas"][1][1]]
    assert max(zc) == pytest.approx(h) and max(zl) == pytest.approx(h)
    assert ams["reporte"]["capa_color_mm"] == pytest.approx(rel)
    grab = chapita(texto="grabado")
    assert [p[0] for p in grab["piezas"]] == ["CHAPITA"] and grab["reporte"]["borde_mm"] == 0
    assert max(v[2] for v in grab["piezas"][0][1]) == pytest.approx(h)
    assert cc.opciones({"texto": "grabado", "colores": "doble"})["colores"] == "ams"
    # patitas sólo donde van
    assert cc.opciones({"forma": "hueso"})["patitas"] and not cc.opciones({"forma": "gato"})["patitas"]
    sin = chapita(patitas=False)
    assert sum(map(sum, sin["letras"])) < sum(map(sum, uno["letras"]))


# ----------------------------------------------------------------- CHA-004
@pytest.mark.spec("CHA-004")
def test_descargas():
    o = {"forma": "gato", "nombre": "Michi", "colores": "doble"}
    name, data = cw.export_stl(o, "LETRAS")
    assert name == "Chapita-Gato-Michi_LETRAS.stl"
    n = int.from_bytes(data[80:84], "little")
    assert n > 0 and len(data) == 84 + 50 * n
    name, data = cw.export_3mf(o)
    assert name == "Chapita-Gato-Michi.3mf"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        m = z.read("3D/3dmodel.model").decode()
    assert m.count("<component ") == 2 and "TecnoBear" in m and "LicenseTerms" in m
    with pytest.raises(ValueError):
        cw.export_stl({"nombre": "Roma"}, "LETRAS")
    assert len(cw.info()["formas"]) == 6
