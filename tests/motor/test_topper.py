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
    jmin = next(j for j in range(g.ny) if any(S[j]))
    ymin = g.y0 + jmin * g.res
    for p in palos:
        assert p["adentro_mm"] >= 1.0
        # todos terminan `largo` mm por debajo de lo más bajo de la pieza (y arrancan cerca)
        assert p["punta"] == pytest.approx(ymin - o["largo"], abs=0.05)
        assert p["desde_abajo_mm"] <= max(8.0, 0.2 * r["reporte"]["medidas_mm"][1]) + 0.5
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


@pytest.mark.spec("TOP-002")
def test_palitos_del_corazon_cerca_de_la_punta():
    r = tc.construir({"marco": "corazon", "lineas": [{"texto": "Feliz"}, {"texto": "Cumpleaños"}, {"texto": "Yoel"}]})
    g, S = r["grilla"], r["region"]
    jmin = next(j for j in range(g.ny) if any(S[j]))
    alto = (max(j for j in range(g.ny) if any(S[j])) - jmin) * g.res
    palos = r["reporte"]["palos"]
    assert len(palos) == 2 and len({p["punta"] for p in palos}) == 1          # misma punta
    for p in palos:
        assert p["desde_abajo_mm"] <= max(8.0, 0.2 * alto) + 0.5            # no en los costados altos
        assert p["arriba"] - p["punta"] >= 90.0                              # largos, no cortitos


# ----------------------------------------------------------------- TOP-008
@pytest.mark.spec("TOP-008")
@pytest.mark.parametrize("lineas", [
    [{"texto": "Happy", "fuente": "lobster"}, {"texto": "Birthday", "fuente": "lobster"}, {"texto": "Martina", "fuente": "pacifico"}],
    [{"texto": "Feliz", "fuente": "great_vibes"}, {"texto": "Cumpleaños", "fuente": "great_vibes"}],
])
def test_huecos_de_las_letras_abiertos(lineas):
    r = tc.construir({"lineas": lineas})
    rep = r["reporte"]
    assert rep["contorno_mm"] == pytest.approx(0.8)
    assert rep["huecos"] > 0 and rep["huecos_abiertos"] == rep["huecos"]
    g, S, T = r["grilla"], r["region"], r["letras"]
    A = tc.afuera(T, g)
    tapados = sum(1 for j in range(g.ny) for i in range(g.nx) if not T[j][i] and not A[j][i] and S[j][i])
    libres = sum(1 for j in range(g.ny) for i in range(g.nx) if not T[j][i] and not A[j][i])
    assert tapados <= 0.05 * libres                     # sólo algún pilar o puente los cruza
    assert tc.componentes(S, g.nx, g.ny)[1] == 1


@pytest.mark.spec("TOP-008")
def test_lineas_se_tocan_sin_encimarse():
    polys, info, caja, grupos = tc.maquetar([{"texto": "Happy", "fuente": "lobster"},
                                            {"texto": "Birthday", "fuente": "lobster"}], 140, True)
    pa, pb = tc._perfiles(grupos[0]), tc._perfiles(grupos[1])
    cruce = [pb[c][1] - pa[c][0] for c in pa if c in pb]
    assert max(cruce) > 0                                 # se tocan
    assert sum(1 for d in cruce if d > 0) <= 0.35 * len(cruce)   # sin encimarse las panzas


# ----------------------------------------------------------------- TOP-009
NUM_CASOS = [("lleno", "1", "luckiest_guy"), ("estrellas", "5", "lilita_one"), ("corazones", "18", "fredoka"),
             ("corona", "40", "bungee"), ("anios", "3", "pacifico"), ("estrellas", "100", "great_vibes")]


@pytest.mark.spec("TOP-009")
@pytest.mark.parametrize("estilo,n,fuente", NUM_CASOS)
def test_numero_en_una_pieza(estilo, n, fuente):
    r = tc.construir_numero({"numero": {"numero": n, "estilo": estilo, "fuente": fuente, "alto": 60}})
    g, S = r["grilla"], r["region"]
    assert tc.componentes(S, g.nx, g.ny)[1] == 1
    rep = r["reporte"]
    assert rep["numero"] == n and rep["alto_mm"] == pytest.approx(60)
    for nombre, V, F in r["piezas"]:
        assert ew.mesh_check(F)["closed"], nombre
    assert [p[0] for p in r["piezas"]] == ["NUMERO"]
    assert len(rep["palos"]) == 1 and rep["huecos_abiertos"] == rep["huecos"]
    jmin = next(j for j in range(g.ny) if any(S[j]))
    assert rep["palos"][0]["punta"] == pytest.approx(g.y0 + jmin * g.res - 90.0, abs=0.05)


@pytest.mark.spec("TOP-009")
@pytest.mark.parametrize("malo", ["", "12a", "1234", "-3"])
def test_numero_errores(malo):
    with pytest.raises(ValueError) as e:
        tc.construir_numero({"numero": {"numero": malo}})
    assert "años" in str(e.value)
    s = tw.build_numero({"numero": {"numero": malo}})["summary"]
    assert not s["valid"] and "años" in s["errors"][0]


@pytest.mark.spec("TOP-009")
def test_numero_descargas():
    o = {"estilo": "doble", "lineas": [{"texto": "Feliz"}, {"texto": "Cumple"}],
         "numero": {"activo": True, "numero": "7", "estilo": "corona", "palitos": 2}}
    n, d = tw.export_stl(o, "NUMERO")
    assert n == "Numero-7_NUMERO.stl" and len(d) > 84
    n, d = tw.export_stl(o, "NUMERO_LETRAS")
    assert n == "Numero-7_NUMERO_LETRAS.stl"
    n, d = tw.export_3mf(o)
    assert n == "Topper-Feliz-Cumple-7.3mf"
    with zipfile.ZipFile(io.BytesIO(d)) as z:
        m = z.read("3D/3dmodel.model").decode("utf-8")
    assert m.count("<item ") == 2 and m.count("<component ") == 4 and "Numero-7" in m
    assert tw.build_numero(o)["summary"]["palitos"] == 2


# ----------------------------------------------------------------- TOP-010
@pytest.mark.spec("TOP-010")
@pytest.mark.parametrize("fn", ["topper", "numero"])
def test_dos_colores_dos_alturas_y_ams(fn):
    base = {"lineas": [{"texto": "Feliz", "fuente": "lobster"}, {"texto": "Sofi", "fuente": "pacifico"}],
            "numero": {"numero": "8", "estilo": "estrellas"}, "grosor": 3.0, "letras": 1.0}
    hacer = tc.construir if fn == "topper" else tc.construir_numero
    d = hacer(dict(base, estilo="doble"))
    a = hacer(dict(base, estilo="ams"))
    for r in (d, a):
        assert len(r["piezas"]) == 2
        for nombre, V, F in r["piezas"]:
            assert ew.mesh_check(F)["closed"], nombre
    zs = lambda r, k: [v[2] for v in r["piezas"][k][1]]
    # dos alturas: letras arriba de la base, cambio de filamento al grosor
    assert max(zs(d, 0)) == pytest.approx(3.0) and min(zs(d, 1)) == pytest.approx(2.99)
    assert max(zs(d, 1)) == pytest.approx(4.0) and d["reporte"]["cambio_mm"] == pytest.approx(3.0)
    # misma altura: todo de 3 mm; las letras en el último milímetro, al ras
    assert max(zs(a, 0)) == pytest.approx(3.0) and max(zs(a, 1)) == pytest.approx(3.0)
    assert min(zs(a, 1)) == pytest.approx(2.0) and a["reporte"]["capa_color_mm"] == pytest.approx(1.0)
    assert a["reporte"]["medidas_mm"][2] == pytest.approx(3.0)
    # el borde de las últimas capas tiene las letras como agujeros: con el mismo largo de
    # borde que las letras de afuera más el contorno de la pieza
    assert a["reporte"]["cambio_mm"] is None and d["reporte"]["capa_color_mm"] is None
