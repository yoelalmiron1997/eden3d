# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Banda de recibida (BAN-001..003)."""
import io
import math
import struct
import zipfile

import pytest
import trimesh

import banda_core as bc
import banda_web as bw

_CACHE = {}


def banda(**o):
    k = tuple(sorted(o.items()))
    if k not in _CACHE:
        _CACHE[k] = bc.construir(o)
    return _CACHE[k]


def malla(V, F):
    return trimesh.Trimesh(vertices=V, faces=F, process=False)


# ----------------------------------------------------------------- BAN-001
@pytest.mark.spec("BAN-001")
@pytest.mark.parametrize("diam", [38.0, 28.0, 45.0])
def test_piezas_cerradas_con_un_agujero(diam):
    r = banda(diametro=diam, texto="MB I")
    s = diam / bc.D0
    for (nombre, ch), (V, F) in r["piezas"].items():
        assert bc.mesh_check(F)["ok"], (nombre, ch)
        m = malla(V, F)
        assert m.is_watertight and m.volume > 0, (nombre, ch)
        if nombre != "LETRAS":
            assert m.euler_number == 0, (nombre, ch)          # género 1: un agujero pasante
    V, _ = r["piezas"][("DISCO", "M")]
    xs, zs = [v[0] for v in V], [v[2] for v in V]
    assert abs((max(xs) - min(xs)) - diam) < 0.2
    assert abs((max(zs) - min(zs)) - bc.H_DISCO * s) < 1e-6


@pytest.mark.spec("BAN-001")
def test_agujeros_donde_van():
    r = banda()
    ra = r["opciones"]["agujero"] / 2.0
    H, T = bc.H_DISCO, bc.CORAZON_T
    for clave, zc in ((("DISCO", "M"), H / 2), (("CORAZON", None), T / 2)):
        m = malla(*r["piezas"][clave])
        # el eje del agujero (x a media altura) está fuera de la pieza; un poco más arriba, adentro
        dentro = m.contains([[x, 0.0, zc] for x in (-5.0, 0.0, 5.0)] + [[0.0, ra + 1.5, zc]])
        assert list(dentro) == [False, False, False, True], clave
        # el rayo a lo largo del eje no toca la pieza: atraviesa de lado a lado
        hits, _, _ = m.ray.intersects_location([[-100.0, 0.0, zc]], [[1.0, 0.0, 0.0]])
        assert len(hits) == 0, clave
    m = malla(*r["piezas"][("PELOTITA", None)])
    hits, _, _ = m.ray.intersects_location([[0.0, 0.0, -50.0]], [[0.0, 0.0, 1.0]])
    assert len(hits) == 0                                       # vertical


@pytest.mark.spec("BAN-001")
def test_letras_espejadas_y_que_llenan_el_bolsillo():
    r = banda(texto="MRB")
    vols = []
    for ch in "MRB":
        Vd, Fd = r["piezas"][("DISCO", ch)]
        Vl, Fl = r["piezas"][("LETRAS", ch)]
        vols.append(malla(Vd, Fd).volume + malla(Vl, Fl).volume)
        H = bc.H_DISCO
        arriba = sorted((round(x, 3), round(y, 3)) for x, y, z in Vl if z > H - 1e-6)
        abajo = sorted((round(x, 3), round(-y, 3)) for x, y, z in Vl if z < 1e-6)
        assert arriba and arriba == abajo, ch                  # la de abajo es la de arriba espejada
    assert max(vols) / min(vols) - 1 < 0.005
    una = banda(texto="MRB", caras="una")
    Vl, _ = una["piezas"][("LETRAS", "M")]
    assert min(v[2] for v in Vl) > 1.0                          # sólo arriba


# ----------------------------------------------------------------- BAN-002
@pytest.mark.spec("BAN-002")
def test_me_recibi_arma_el_collar():
    r = banda()
    rep = r["reporte"]
    assert rep["texto"] == "ME RECIBÍ" and rep["total_discos"] == 8
    assert {d["letra"]: d["cantidad"] for d in rep["discos"]}["E"] == 2
    orden = [(c["pieza"], c["letra"]) for c in r["collar"]]
    assert orden[:9] == [("DISCO", "M"), ("DISCO", "E"), ("CORAZON", None), ("DISCO", "R"), ("DISCO", "E"),
                         ("DISCO", "C"), ("DISCO", "I"), ("DISCO", "B"), ("DISCO", "Í")]
    assert orden[9][0] == "PELOTITA" and orden[-1][0] == "PELOTITA"
    resto = [p for p, _ in orden[9:]]
    assert all(a != b for a, b in zip(resto, resto[1:]))       # alternado
    assert abs(rep["largo_cm"] - 130) < (bc.CORAZON_W + bc.PELOTITA_H) / 10.0
    # el texto centrado adelante (y < 0), de izquierda a derecha
    ys = [c["y"] for c in r["collar"][:9]]
    xs = [c["x"] for c in r["collar"][:9]]
    assert max(ys) < -0.6 * r["radio"] and abs(xs[0] + xs[-1]) < 1.0 and xs == sorted(xs)


@pytest.mark.spec("BAN-002")
@pytest.mark.parametrize("sep,rell", [("pelotita", "corazones"), ("nada", "pelotitas"), ("corazon", "alternado")])
def test_cuentas_sin_pisarse(sep, rell):
    r = banda(texto="lic. sofia", separador=sep, relleno=rell, largo=90)
    assert r["reporte"]["texto"] == "LIC. SOFIA"
    items = r["collar"]
    ang = []
    for it in items:
        ang.append((math.atan2(it["y"], it["x"]), bc.largo_de("letra" if it["pieza"] == "DISCO" else it["pieza"].lower(),
                                                                r["opciones"]) / 2.0))
    R = r["radio"]
    for (a1, l1), (a2, l2) in zip(ang, ang[1:] + ang[:1]):
        d = (a1 - a2) % (2 * math.pi) * R
        assert d >= l1 + l2 - 1e-6
    tipos = {it["pieza"] for it in items[len("LIC.SOFIA") + (1 if sep != "nada" else 0):]}
    assert tipos == ({"CORAZON", "PELOTITA"} if rell == "alternado" else {{"corazones": "CORAZON", "pelotitas": "PELOTITA"}[rell]})


@pytest.mark.spec("BAN-002")
@pytest.mark.parametrize("opts,msg", [
    ({"texto": "  "}, "Escribí"),
    ({"texto": "A" * 25}, "hasta 24"),
    ({"texto": "ME RECIBÍ ☺"}, "no están"),
    ({"texto": "LICENCIADA EN TODO", "largo": 60}, "muy largo"),
])
def test_rechazos(opts, msg):
    with pytest.raises(ValueError) as e:
        bc.construir(opts)
    assert msg in str(e.value)
    r = bw.build(opts)
    assert not r["summary"]["valid"] and msg in r["summary"]["errors"][0]


@pytest.mark.spec("BAN-002")
def test_agujero_que_no_entra_se_achica():
    r = banda(diametro=26, agujero=9, profundidad=2)
    assert r["opciones"]["agujero"] < 9
    assert any("agujero" in a for a in r["reporte"]["avisos"])
    assert all(malla(*m).is_watertight for m in r["piezas"].values())


# ----------------------------------------------------------------- BAN-003
@pytest.mark.spec("BAN-003")
def test_3mf_con_todas_las_cuentas():
    name, data = bw.export_3mf({"texto": "ANA", "largo": 70})
    assert name == "Banda-ANA-70cm.3mf"
    z = zipfile.ZipFile(io.BytesIO(data))
    model = z.read("3D/3dmodel.model").decode("utf-8")
    rep = bc.construir({"texto": "ANA", "largo": 70})["reporte"]
    assert model.count("<item ") == rep["cuentas"]
    assert model.count("<components>") == 2                   # A y N: disco + letras
    assert "TecnoBear" in model and "LicenseTerms" in model


@pytest.mark.spec("BAN-003")
def test_zip_de_stl_y_leeme():
    name, data = bw.export_stl({})
    assert name == "Banda-ME-RECIBI-130cm_STL.zip"
    z = zipfile.ZipFile(io.BytesIO(data))
    nombres = set(z.namelist())
    for ch in ("M", "E", "R", "C", "I", "B", "I_tilde"):
        assert {"Disco_%s.stl" % ch, "Disco_%s_letras.stl" % ch} <= nombres
    assert {"Corazon.stl", "Pelotita.stl", "LEEME.txt"} <= nombres
    stl = z.read("Corazon.stl")
    n = struct.unpack("<I", stl[80:84])[0]
    assert len(stl) == 84 + 50 * n
    leeme = z.read("LEEME.txt").decode("utf-8")
    assert "Disco_E" in leeme and "x 2" in leeme
