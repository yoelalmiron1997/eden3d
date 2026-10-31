# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Topper para tortas (TOP-001..004)."""
import io
import math
import os
import zipfile

import pytest

import eden_web as ew
import mate_fuentes as mf
import topper_core as tc
import topper_web as tw

LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÁÉÍÓÚÑáéíóúñ"
CASOS = [
    {},
    {"marco": "circulo", "estilo": "doble"},
    {"marco": "corazon", "lineas": [{"texto": "Feliz", "fuente": "lobster"}, {"texto": "Cumple", "fuente": "lobster"},
                                    {"texto": "Sofi", "fuente": "pacifico", "escala": 1.3}]},
    {"marco": "flor", "palitos": 1, "lineas": [{"texto": "Happy", "fuente": "satisfy"}, {"texto": "Birthday", "fuente": "satisfy"}]},
    {"marco": "rombo", "contorno": 0.0, "lineas": [{"texto": "Feliz día", "fuente": "archivo_black"}]},
    {"marco": "sol", "contorno": 6.0, "lineas": [{"texto": "Mamá", "fuente": "allura", "escala": 1.5}]},
    {"contorno": 0.0, "lineas": [{"texto": "Te quiero mucho", "fuente": "bungee"}]},
]
_CACHE = {}


def topper(i):
    if i not in _CACHE:
        _CACHE[i] = tc.construir(CASOS[i])
    return _CACHE[i]


# ----------------------------------------------------------------- TOP-001
@pytest.mark.spec("TOP-001")
@pytest.mark.parametrize("i", range(len(CASOS)))
def test_una_sola_pieza(i):
    r = topper(i)
    g, S = r["grilla"], r["region"]
    _, n, _ = tc.componentes(S, g.nx, g.ny)
    assert n == 1
    # cada palito arranca adentro de la región (no queda colgando) y mide lo pedido
    o = tc.opciones(CASOS[i])
    palos = r["reporte"]["palos"]
    assert len(palos) == o["palitos"]
    for p in palos:
        assert p["adentro_mm"] >= 1.0
        assert p["arriba"] - p["adentro_mm"] - p["punta"] == pytest.approx(o["largo"], abs=0.2)
        i_ = int((p["x"] - g.x0) / g.res)
        j_ = int((p["arriba"] - 0.5 - g.y0) / g.res)
        assert S[j_][i_], "el palito no entra en la pieza"


@pytest.mark.spec("TOP-001")
def test_lo_suelto_se_une_con_puentes():
    r = topper(6)                               # contorno 0 y palabras separadas
    assert r["reporte"]["puentes"] >= 1
    s = tw.build(CASOS[6])["summary"]
    assert s["puentes"] >= 1 and any("puente" in w for w in s["warnings"])


# ----------------------------------------------------------------- TOP-002
@pytest.mark.spec("TOP-002")
@pytest.mark.parametrize("i", range(len(CASOS)))
def test_mallas_cerradas_y_medidas(i):
    r = topper(i)
    o = tc.opciones(CASOS[i])
    for nombre, V, F in r["piezas"]:
        assert ew.mesh_check(F)["closed"], nombre
    V = r["piezas"][0][1]
    zs = [v[2] for v in V]
    assert min(zs) == 0.0 and max(zs) == pytest.approx(o["grosor"])
    xs = [v[0] for v in V]
    ancho = max(xs) - min(xs)
    if o["marco"] == "ninguno":
        assert ancho == pytest.approx(o["ancho"] + 2 * o["contorno"], abs=1.5)
    else:
        assert ancho <= o["ancho"] + 10.0
    ys = [v[1] for v in V]
    assert min(ys) < -o["largo"] / 2               # los palitos bajan
    if o["estilo"] == "doble":
        Vl = r["piezas"][1][1]
        zl = [v[2] for v in Vl]
        assert min(zl) == pytest.approx(o["grosor"] - 0.01) and max(zl) == pytest.approx(o["grosor"] + o["letras"])
        assert o["contorno"] >= 2.0


@pytest.mark.spec("TOP-002")
def test_palitos_con_punta_y_largo():
    r = tc.construir({"palitos": 1, "largo": 70})
    V = r["piezas"][0][1]
    abajo = min(v[1] for v in V)
    punta = [v for v in V if abs(v[1] - abajo) < 1e-6]
    assert len({(round(v[0], 3)) for v in punta}) == 1          # termina en una punta
    xs = [v[0] for v in V if v[1] < abajo + 30]
    assert max(xs) - min(xs) == pytest.approx(tc.ANCHO_PALITO, abs=0.01)


# ----------------------------------------------------------------- TOP-003
@pytest.mark.spec("TOP-003")
def test_tipografias_completas():
    assert len(tc.FUENTES) == 16
    lic = open(os.path.join(mf.DIR, "LICENCIAS.md"), encoding="utf-8").read()
    for fid in tc.IDS:
        f = mf.cargar(fid)
        assert not [c for c in LETRAS if c not in f["glifos"]], fid
        assert fid + ".json" in lic
    assert [x["id"] for x in tw.info()["fuentes"]] == tc.IDS


@pytest.mark.spec("TOP-003")
def test_lineas_apiladas():
    polys, info, caja = tc.maquetar([{"texto": "Feliz", "fuente": "great_vibes"},
                                     {"texto": "Cumpleaños", "fuente": "great_vibes"},
                                     {"texto": "Sofi", "fuente": "dancing_script"}], 140)
    assert [i["texto"] for i in info] == ["Feliz", "Cumpleaños", "Sofi"]
    assert max(i["ancho_mm"] for i in info) == pytest.approx(140, abs=0.01)
    assert caja[0] == pytest.approx(-caja[2], abs=0.01)              # centrado
    assert caja[3] - caja[1] < sum(i["alto_mm"] for i in info)       # encimadas


@pytest.mark.spec("TOP-003")
@pytest.mark.parametrize("malo,txt", [
    ({"lineas": [{"texto": "☃☃", "fuente": "cookie"}]}, "no están en la tipografía"),
    ({"lineas": [{"texto": "a"}, {"texto": "b"}, {"texto": "c"}, {"texto": "d"}]}, "hasta 3 líneas"),
    ({"lineas": [{"texto": "x" * 30}]}, "hasta 24 letras"),
    ({"lineas": [{"texto": "   "}]}, "al menos una línea"),
    ({"lineas": [{"texto": "hola", "fuente": "comic_sans"}]}, "Tipografía desconocida"),
    ({"marco": "estrella"}, "marco desconocido"),
])
def test_errores_en_espanol(malo, txt):
    with pytest.raises(ValueError) as e:
        tc.construir(malo)
    assert txt in str(e.value)
    s = tw.build(malo)["summary"]
    assert not s["valid"] and txt in s["errors"][0]


# ----------------------------------------------------------------- TOP-004
@pytest.mark.spec("TOP-004")
def test_descargas():
    o = {"estilo": "doble", "lineas": [{"texto": "Feliz"}, {"texto": "Cumpleaños Sofía"}]}
    n, d = tw.export_stl(o, "TOPPER")
    assert n == "Topper-Feliz-Cumpleanos-Sofia_TOPPER.stl" and len(d) > 84
    n, d = tw.export_stl(o, "LETRAS")
    assert n.endswith("_LETRAS.stl")
    n, d = tw.export_3mf(o)
    assert n == "Topper-Feliz-Cumpleanos-Sofia.3mf"
    with zipfile.ZipFile(io.BytesIO(d)) as z:
        m = z.read("3D/3dmodel.model").decode("utf-8")
    assert m.count("<component ") == 2 and m.count("<item ") == 1
    assert "uso personal" in m and "Eden3D" in m
    with pytest.raises(ValueError):
        tw.export_stl({}, "LETRAS")                 # un color: no hay letras aparte


# ----------------------------------------------------------------- TOP-006
APOYO_CASOS = [
    [{"texto": "Feliz", "fuente": "great_vibes"}, {"texto": "Cumpleaños", "fuente": "great_vibes"}],
    [{"texto": "Feliz", "fuente": "great_vibes"}, {"texto": "Cumpleaños", "fuente": "great_vibes"},
     {"texto": "Sofi", "fuente": "dancing_script", "escala": 1.1}],
    [{"texto": "Happy", "fuente": "lobster"}, {"texto": "Birthday", "fuente": "lobster"}, {"texto": "Martina", "fuente": "pacifico"}],
    [{"texto": "Feliz", "fuente": "allura"}, {"texto": "cumple", "fuente": "allura"}, {"texto": "Juan", "fuente": "lilita_one", "escala": 0.8}],
    [{"texto": "FELIZ", "fuente": "bungee"}, {"texto": "DIA", "fuente": "bungee"}],
]


@pytest.mark.spec("TOP-006")
@pytest.mark.parametrize("lineas", APOYO_CASOS)
def test_cada_linea_con_dos_apoyos(lineas):
    r = tc.construir({"lineas": lineas})
    ap = r["reporte"]["apoyos"]
    assert len(ap) == len(lineas) - 1
    for a in ap:
        assert a["apoyos"] >= 2 or a["contacto_max_mm"] >= 0.4 * a["ancho_comun_mm"], a
    g, S = r["grilla"], r["region"]
    assert tc.componentes(S, g.nx, g.ny)[1] == 1


@pytest.mark.spec("TOP-006")
def test_palabras_sueltas_con_dos_puentes():
    r = tc.construir({"contorno": 0.0, "lineas": [{"texto": "Te quiero", "fuente": "bungee"}]})
    assert r["reporte"]["puentes"] >= 2
    g, S = r["grilla"], r["region"]
    assert tc.componentes(S, g.nx, g.ny)[1] == 1
