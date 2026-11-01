# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Trofeos para eventos (TRO-001..004)."""
import io
import re
import struct
import zipfile

import pytest

import eden_web as ew
import topper_core as tc
import trofeo_core as tr
import trofeo_web as tw

FIGURAS = [k for k, _ in tr.FIGURAS]
_CACHE = {}


def trofeo(**o):
    k = tuple(sorted(o.items()))
    if k not in _CACHE:
        _CACHE[k] = tr.construir(o)
    return _CACHE[k]


def caja(V):
    return [(min(v[k] for v in V), max(v[k] for v in V)) for k in range(3)]


def volumen(V, F):
    s = 0.0
    for a, b, c in F:
        A, B, C = V[a], V[b], V[c]
        s += (A[0] * (B[1] * C[2] - B[2] * C[1]) - A[1] * (B[0] * C[2] - B[2] * C[0])
              + A[2] * (B[0] * C[1] - B[1] * C[0]))
    return s / 6.0


def pieza(r, nombre, cual="piezas"):
    for n, V, F in r[cual]:
        if n == nombre:
            return V, F
    raise KeyError(nombre)


# ----------------------------------------------------------------- TRO-001
@pytest.mark.spec("TRO-001")
@pytest.mark.parametrize("figura", FIGURAS)
def test_figura_en_una_pieza(figura):
    r = trofeo(figura=figura, colores="dos")
    F = r["figura"]
    g = F["grilla"]
    _, n, _ = tc.componentes(F["solido"], g.nx, g.ny)
    assert n == 1, figura
    for nombre, V, Fc in r["piezas"]:
        assert ew.mesh_check(Fc)["closed"], (figura, nombre)
        assert volumen(V, Fc) > 0, (figura, nombre)            # normales para afuera
    o = tr.opciones({"figura": figura})
    rep = r["reporte"]
    assert rep["figura_mm"][1] == pytest.approx(o["alto"] - o["base_alto"] - o["tallo"], abs=1.0)
    (_, _), (_, _), (z0, z1) = caja(pieza(r, "FIGURA")[0])
    assert z0 == pytest.approx(0.0, abs=1e-6) and z1 == pytest.approx(o["grosor"], abs=0.02)


@pytest.mark.spec("TRO-001")
def test_numero_de_dos_cifras_unido():
    r = trofeo(figura="numero", caracter="10")
    g = r["figura"]["grilla"]
    _, n, _ = tc.componentes(r["figura"]["solido"], g.nx, g.ny)
    assert n == 1
    assert r["reporte"]["caracter"] == "10"


# ----------------------------------------------------------------- TRO-002
@pytest.mark.spec("TRO-002")
@pytest.mark.parametrize("base", ["escalonada", "recta"])
def test_espiga_y_ranura(base):
    r = trofeo(base=base, holgura=0.3)
    rep = r["reporte"]
    ew_, et, ed = rep["espiga_mm"]
    rw, rt, rd = rep["ranura_mm"]
    assert rw == pytest.approx(ew_ + 0.6, abs=0.02) and rt == pytest.approx(et + 0.6, abs=0.02)
    assert rd == pytest.approx(ed)
    b = r["base"]["medidas"]
    assert (b["BW"] - rw) / 2 >= tr.PARED and (b["D"] - rt) / 2 >= tr.PARED
    assert b["BH"] - rd >= 4.0                                   # fondo debajo de la ranura
    # armado: la punta de la espiga en el fondo de la ranura, la figura arriba de la base
    Vf = pieza(r, "FIGURA", "armado")[0]
    (x0, x1), (y0, y1), (z0, z1) = caja(Vf)
    assert z0 == pytest.approx(b["BH"] - b["Ds"], abs=0.05)
    assert z1 == pytest.approx(rep["medidas_mm"][2], abs=0.5)
    abajo = [v for v in Vf if v[2] < b["BH"] - 0.01]              # lo que está adentro de la ranura
    assert max(abs(v[0]) for v in abajo) <= rw / 2 and max(abs(v[1]) for v in abajo) <= rt / 2 + 1e-6


@pytest.mark.spec("TRO-002")
@pytest.mark.parametrize("figura", ["estrella", "pelota", "copa"])
def test_detalles_no_bajan_a_la_espiga(figura):
    r = trofeo(figura=figura, colores="dos", texto_figura="1" if figura != "pelota" else "")
    Vd = pieza(r, "DETALLE")[0]
    y_pie = r["figura"]["info"]["y_pie"]
    assert min(v[1] for v in Vd) >= y_pie                         # (en la pieza acostada, y es el alto)


# ----------------------------------------------------------------- TRO-003
@pytest.mark.spec("TRO-003")
@pytest.mark.parametrize("texto", ["relieve", "grabado"])
def test_texto_adentro_del_frente(texto):
    r = trofeo(texto=texto, colores="dos")
    b = r["base"]["medidas"]
    (x0, x1), (y0, y1), (z0, z1) = caja(pieza(r, "TEXTO")[0])
    assert -b["BW"] / 2 < x0 and x1 < b["BW"] / 2
    assert b["hz"] < z0 and z1 < b["BH"]
    frente = -b["D"] / 2
    o = tr.opciones({})
    if texto == "relieve":
        assert y0 == pytest.approx(frente - o["relieve"], abs=0.02)   # sobresale
    else:
        assert y0 == pytest.approx(frente, abs=0.02) and y1 == pytest.approx(frente + o["relieve"], abs=0.02)
        arriba = [v for v in pieza(r, "BASE")[0] if v[2] > b["hz"] + 0.1]   # el bloque, sin el escalón
        assert min(v[1] for v in arriba) == pytest.approx(frente, abs=0.02)


@pytest.mark.spec("TRO-003")
def test_texto_mas_corto_mas_grande():
    largo = trofeo(linea1="CAMPEONATO REGIONAL", linea2="")["reporte"]["letra_base_mm"]
    corto = trofeo(linea1="MVP", linea2="")["reporte"]["letra_base_mm"]
    dos = trofeo(linea1="MVP", linea2="Torneo de verano 2026")["reporte"]["letra_base_mm"]
    assert corto > largo and corto > dos


@pytest.mark.spec("TRO-003")
def test_texto_en_la_figura_adentro():
    r = trofeo(figura="estrella", texto_figura="1°")
    assert r["reporte"]["letra_figura_mm"] >= 15
    F = r["figura"]
    g = F["grilla"]
    for j in range(g.ny):
        for i in range(g.nx):
            if F["detalle"][j][i]:
                assert F["silueta"][j][i]


@pytest.mark.spec("TRO-003")
@pytest.mark.parametrize("o, msg", [
    ({"linea1": "", "linea2": ""}, "Escribí el texto"),
    ({"linea1": "X" * 23}, "hasta 22"),
    ({"figura": "numero", "caracter": "1234"}, "hasta 3"),
    ({"figura": "numero", "caracter": ""}, "Escribí el número"),
    ({"alto": 90, "base_alto": 50, "tallo": 10}, "menos de 40 mm"),
    ({"linea1": "★"}, ""),
])
def test_errores_en_espanol(o, msg):
    with pytest.raises(ValueError) as e:
        tr.construir(o)
    assert msg in str(e.value)
    s = tw.build(o)["summary"]
    assert not s["valid"] and s["errors"]


# ----------------------------------------------------------------- TRO-004
@pytest.mark.spec("TRO-004")
def test_un_color_y_dos_colores():
    uno = trofeo()
    assert uno["reporte"]["piezas"] == ["FIGURA", "BASE"] and uno["reporte"]["cambio_mm"] is None
    dos = trofeo(colores="dos")
    assert dos["reporte"]["piezas"] == ["FIGURA", "DETALLE", "BASE", "TEXTO"]
    o = tr.opciones({})
    (_, _), (_, _), (z0, z1) = caja(pieza(dos, "DETALLE")[0])
    assert z0 == pytest.approx(o["grosor"], abs=0.02) and z1 == pytest.approx(o["grosor"] + o["relieve"], abs=0.02)
    assert dos["reporte"]["cambio_mm"] == pytest.approx(o["grosor"])
    # el visor siempre muestra los detalles y el texto aparte, para verlos de su color
    assert [n for n, _, _ in uno["armado"]] == ["FIGURA", "DETALLE", "BASE", "TEXTO"]


@pytest.mark.spec("TRO-004")
def test_descargas():
    o = {"colores": "dos", "linea1": "Campeón"}
    name, data = tw.export_stl(o, "BASE")
    assert name == "Trofeo-Estrella-Campeon_BASE.stl"
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n and n > 0
    name, data = tw.export_3mf(o)
    assert name == "Trofeo-Estrella-Campeon.3mf"
    z = zipfile.ZipFile(io.BytesIO(data))
    model = z.read("3D/3dmodel.model").decode("utf-8")
    assert len(re.findall(r"<item ", model)) == 2
    assert model.count("<component ") == 4
    assert "TecnoBear" in model and "LicenseTerms" in model
    with pytest.raises(ValueError):
        tw.export_stl({}, "DETALLE")                              # en un color no hay detalle aparte
