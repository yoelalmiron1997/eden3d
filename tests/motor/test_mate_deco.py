# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Mate: nombres de insertos, marca debajo de la base, relieve (texto/SVG) y cuña."""
import io
import math
import zipfile

import pytest

import mate_core as mc
import mate_deco as md
import mate_web

TIPOS = [t["id"] for t in mc.TIPOS]
SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
  <g transform="translate(2 4) scale(0.96)">
    <path d="M50 4 C 28 4 14 24 18 46 C 21 64 36 80 50 116 C 64 80 79 64 82 46 C 86 24 72 4 50 4 Z
             M50 28 a 14 14 0 1 0 0.1 0 Z" fill="#000"/>
    <rect x="40" y="60" width="20" height="8" rx="2"/>
    <polyline points="20,100 35,110 50,100" fill="none" stroke="#000" stroke-width="3"/>
  </g></svg>"""


def ang(x, y):
    return math.degrees(math.atan2(y, x))


# ----------------------------------------------------------------- MAT-011
@pytest.mark.spec("MAT-011")
def test_nombres_de_los_insertos():
    assert mc.INSERTOS["polimero"]["nombre"] == "Polímero escalonado"
    assert mc.INSERTOS["adaptador"]["nombre"] == "Polímero base"
    web = {i["id"]: i["nombre"] for i in mate_web.info()["insertos"]}
    assert web["polimero"] == "Polímero escalonado" and web["adaptador"] == "Polímero base"
    rep = mc.build_mate({"tipo": "cilindrico", "inserto": "ambos"})["report"]
    assert rep["insertos"] == ["Polímero escalonado", "Polímero base"]


# ----------------------------------------------------------------- MAT-012
@pytest.mark.spec("MAT-012")
@pytest.mark.parametrize("tipo", TIPOS)
def test_marca_eden3d_debajo_de_la_base(tipo):
    r = mc.build_mate({"tipo": tipo})
    rep = r["report"]
    assert rep["valid"] and rep["cerrada"], rep["errors"]
    if rep["marca"]:
        assert rep["marca"]["texto"] == "Eden3D" and rep["marca"]["prof_mm"] == pytest.approx(0.6)
        V = r["shells"][0][0]
        z0 = min(v[2] for v in V)
        hundidos = [v for v in V if abs(v[2] - (z0 + 0.6)) < 1e-6]
        assert hundidos, "el fondo de las letras está 0,6 mm adentro"
    else:
        assert any(w.startswith("Marca") for w in rep["warnings"]), "si no entra, avisa"


@pytest.mark.spec("MAT-012")
@pytest.mark.parametrize("texto", ["TecnoBear", "Ñandú 2026!", "@mi_mate"])
def test_marca_pro(texto):
    rep = mc.build_mate({"tipo": "imperial_clasico", "marca": texto})["report"]
    assert rep["valid"] and rep["cerrada"]
    assert rep["marca"]["texto"] == texto and rep["marca"]["cap_mm"] >= 3.5


@pytest.mark.spec("MAT-012")
def test_marca_vacia_o_invalida():
    assert mc.build_mate({"tipo": "imperial_clasico", "marca": ""})["report"]["marca"] is None
    with pytest.raises(ValueError, match="no se pueden grabar"):
        mc.build_mate({"tipo": "imperial_clasico", "marca": "Hola €"})
    assert mate_web.check_marca("x" * 21)["error"]


# ----------------------------------------------------------------- MAT-013
def _relieve(tipo, deco):
    r = mc.build_mate({"tipo": tipo, "deco": deco})
    assert r["report"]["valid"], r["report"]["errors"]
    return r


@pytest.mark.spec("MAT-013")
@pytest.mark.parametrize("tipo", TIPOS)
def test_texto_en_relieve_en_cada_modelo(tipo):
    r = _relieve(tipo, {"tipo": "texto", "texto": "TecnoBear", "alto": 10})
    rep = r["report"]
    assert rep["cerrada"] and rep["deco"]["cerrada"]
    V, F = r["deco"]
    assert mc.mesh_check(F)["closed"] and mc.mesh_volume(V, F) > 0


@pytest.mark.spec("MAT-013")
@pytest.mark.parametrize("angulo,z,prof", [(-90, 60, 1.2), (30, 45, 2.0), (150, 70, 0.6)])
def test_relieve_en_su_lugar_y_sobresale(angulo, z, prof):
    r = _relieve("cilindrico", {"tipo": "svg", "svg": SVG, "alto": 24, "angulo": angulo, "z": z, "prof": prof})
    V, _ = r["deco"]
    info = r["report"]["deco"]
    xs, ys, zs = zip(*V)
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    assert abs((ang(cx, cy) - angulo + 180) % 360 - 180) < 1.0
    assert (min(zs) + max(zs)) / 2 == pytest.approx(z, abs=0.5)
    assert max(zs) - min(zs) == pytest.approx(24, abs=0.6)
    # lo que más sale está a prof de la piel; lo de abajo queda 0,8 mm adentro
    piel = md.Piel(*_filas("cilindrico"))
    afuera = max(math.hypot(x, y) - piel.radio(zz, math.atan2(y, x)) for x, y, zz in V)
    adentro = min(math.hypot(x, y) - piel.radio(zz, math.atan2(y, x)) for x, y, zz in V)
    assert afuera == pytest.approx(prof, abs=0.1)
    assert adentro == pytest.approx(-md.EMBUTIDO, abs=0.1)
    assert info["angulo"] == pytest.approx(angulo) and info["prof"] == pytest.approx(prof)


def _filas(tipo):
    p = mc.parametros_tipo(tipo)
    filas, _ = mc.filas_exteriores(p, 1.0, 192)
    return filas, 192


@pytest.mark.spec("MAT-013")
def test_rotacion_del_relieve():
    a = _relieve("cilindrico", {"tipo": "texto", "texto": "I", "alto": 20, "rot": 0})["deco"][0]
    b = _relieve("cilindrico", {"tipo": "texto", "texto": "I", "alto": 20, "rot": 90})["deco"][0]
    alto = lambda V: max(v[2] for v in V) - min(v[2] for v in V)
    assert alto(a) == pytest.approx(20, abs=0.6)
    assert alto(b) < 8, "girada 90°, la I queda acostada"


@pytest.mark.spec("MAT-013")
@pytest.mark.parametrize("datos,msg", [
    (b"<svg", "no es un SVG"),
    (b'<svg xmlns="http://www.w3.org/2000/svg"><text>hola</text></svg>', "no tiene figuras"),
    (b"x" * 700000, "muy grande"),
])
def test_svg_invalido(datos, msg):
    r = mc.build_mate({"tipo": "imperial_clasico", "deco": {"tipo": "svg", "svg": datos}})
    assert not r["report"]["valid"]
    assert any(msg in e for e in r["report"]["errors"]), r["report"]["errors"]


@pytest.mark.spec("MAT-013")
def test_trazos_y_formas_del_svg():
    f = md.forma_svg(SVG, 30)
    assert len(f["polys"]) >= 3 and f["lineas"], "rellenos y el trazo del polyline"
    assert f["alto"] == pytest.approx(30)
    x0, y0, x1, y1 = md._bbox(f)
    assert (y1 - y0) == pytest.approx(30, abs=1e-6) and abs(x0 + x1) < 1e-6


# ----------------------------------------------------------------- MAT-014
@pytest.mark.spec("MAT-014")
@pytest.mark.parametrize("angulo", [45, 30, 10])
def test_cuna(angulo):
    r = mc.build_mate({"tipo": "imperial_clasico", "cuna": {"angulo": angulo}})
    V, F = r["cuna"]
    info = r["report"]["cuna"]
    assert mc.mesh_check(F)["closed"] and mc.mesh_volume(V, F) > 0
    assert info["angulo"] == pytest.approx(angulo)
    # la cara de arriba: los puntos del borde superior están en un plano inclinado
    sup = sorted(V, key=lambda v: -v[2])[:40]
    (x1, _, z1), (x2, _, z2) = max(V, key=lambda v: v[2]), min((v for v in V if v[2] > 1.0), key=lambda v: v[0])
    pend = math.degrees(math.atan2(z1 - z2, x1 - x2))
    assert pend == pytest.approx(angulo, abs=0.5)
    pie = min(r["shells"][0][0], key=lambda v: v[2])
    r_pie = min(math.hypot(v[0], v[1]) for v in r["shells"][0][0] if abs(v[2] - pie[2]) < 1e-6 and
                math.hypot(v[0], v[1]) > 5)
    assert info["hueco_diam_mm"] / 2 > r_pie, "el pie entra en el hueco"
    assert sup


@pytest.mark.spec("MAT-014")
def test_cuna_en_las_descargas():
    opts = {"tipo": "imperial_clasico", "cuna": {"angulo": 45}}
    name, data = mate_web.export_stl(opts, "CUNA")
    assert name.endswith("_CUNA.stl")
    n = int.from_bytes(data[80:84], "little")
    assert len(data) == 84 + 50 * n
    name, data = mate_web.export_3mf(opts)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        modelo = z.read("3D/3dmodel.model").decode()
    assert modelo.count("<object ") == 2 and "_CUNA" in modelo
    with pytest.raises(ValueError, match="cuña"):
        mate_web.export_stl({"tipo": "imperial_clasico"}, "CUNA")
