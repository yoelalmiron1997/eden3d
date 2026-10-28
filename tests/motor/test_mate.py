# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Mate con hueco: hueco exacto, mallas cerradas, autoajuste, inserto propio y descargas."""
import io
import math
import os
import struct
import time
import zipfile

import pytest

import mate_core as mc
import mate_web

HERE = os.path.dirname(os.path.abspath(__file__))
INS = os.path.join(HERE, "insertos")
STL = {"polimero": os.path.join(INS, "Polimero_Mate.stl"),
       "adaptador": os.path.join(INS, "Adaptador_Polimero_2.stl")}
TIPOS = [t["id"] for t in mc.TIPOS]
INSERTOS = ("polimero", "adaptador", "ambos")
_CACHE = {}


def mate(tipo, inserto="polimero", **kw):
    key = (tipo, inserto, tuple(sorted(kw.items())))
    if key not in _CACHE:
        _CACHE[key] = mc.build_mate(dict({"tipo": tipo, "inserto": inserto}, **kw))
    return _CACHE[key]


def radio_en(canon, d):
    """Radio máximo del perfil (r, d) a la profundidad d (sin contar el fondo)."""
    best = 0.0
    for (r1, d1), (r2, d2) in zip(canon, canon[1:]):
        lo, hi = min(d1, d2), max(d1, d2)
        if lo - 1e-9 <= d <= hi + 1e-9:
            t = 0.0 if hi - lo < 1e-12 else (d - d1) / (d2 - d1)
            best = max(best, r1 + t * (r2 - r1))
    return best


def caja_stl(a=20.0):
    """Cubo de lado a, en STL ASCII: no es de revolución."""
    v = [(x, y, z) for x in (0, a) for y in (0, a) for z in (0, a)]
    caras = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    out = ["solid caja"]
    for f in caras:
        out.append("facet normal 0 0 0\nouter loop")
        out += ["vertex %g %g %g" % v[i] for i in f]
        out.append("endloop\nendfacet")
    out.append("endsolid caja")
    return "\n".join(out).encode()


def a_ascii(data):
    """STL binario -> ASCII (mismo sólido)."""
    n = struct.unpack("<I", data[80:84])[0]
    out = ["solid x"]
    for i in range(n):
        v = struct.unpack("<12f", data[84 + 50 * i: 84 + 50 * i + 48])
        out.append("facet normal 0 0 0\nouter loop")
        out += ["vertex %r %r %r" % tuple(v[3 + 3 * k: 6 + 3 * k]) for k in range(3)]
        out.append("endloop\nendfacet")
    return ("\n".join(out) + "\nendsolid x").encode()


# ----------------------------------------------------------------- MAT-001
@pytest.mark.spec("MAT-001")
@pytest.mark.parametrize("nombre", ["polimero", "adaptador"])
def test_el_perfil_incluido_es_el_del_stl(nombre):
    with open(STL[nombre], "rb") as fh:
        tris = mc.leer_stl(fh.read())
    canon, info = mc.perfil_desde_stl(tris)
    ref = mc.INSERTOS[nombre]["perfil"]
    assert len(canon) == len(ref)
    for (r1, d1), (r2, d2) in zip(canon, ref):
        assert abs(r1 - r2) <= 0.05 and abs(d1 - d2) <= 0.05, (canon, ref)
    v_rev = mc.volumen_revolucion([(r, -d) for r, d in ref])
    assert abs(v_rev - info["volumen_mm3"]) / info["volumen_mm3"] < 0.01


@pytest.mark.spec("MAT-001")
@pytest.mark.parametrize("holgura", [0.0, 0.3])
def test_la_holgura_agranda_el_hueco(holgura):
    r = mate("imperial_clasico", holgura=holgura)
    rep = r["report"]
    ref = mc.INSERTOS["polimero"]["perfil"]
    prof = max(d for _, d in ref)
    assert rep["hueco_prof_mm"] == pytest.approx(prof + holgura, abs=0.06)
    assert rep["hueco_diam_mm"] == pytest.approx(2 * (34.92 + holgura), abs=0.11)


# ----------------------------------------------------------------- MAT-002
@pytest.mark.spec("MAT-002")
@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("inserto", INSERTOS)
def test_malla_cerrada(tipo, inserto):
    r = mate(tipo, inserto)
    rep = r["report"]
    assert rep["valid"], rep["errors"]
    assert rep["cerrada"]
    for V, F in r["shells"]:
        chk = mc.mesh_check(F)
        assert chk["closed"], chk
        assert mc.mesh_volume(V, F) > 0
    assert rep["peso_g"] > 100


# ----------------------------------------------------------------- MAT-003
@pytest.mark.spec("MAT-003")
@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("inserto", INSERTOS)
def test_pared_y_fondo_minimos(tipo, inserto):
    rep = mate(tipo, inserto)["report"]
    assert rep["pared_mm"] >= rep["pared_pedida_mm"] - 0.05
    assert rep["fondo_mm"] >= 4.0 - 0.05


@pytest.mark.spec("MAT-003")
def test_pared_mas_gruesa_agranda_el_mate():
    a = mate("imperial_torpedo", "adaptador", pared=3.0)["report"]
    b = mate("imperial_torpedo", "adaptador", pared=5.0)["report"]
    assert b["pared_mm"] >= 4.95
    assert b["diam_max_mm"] > a["diam_max_mm"]


@pytest.mark.spec("MAT-003")
def test_sin_autoajuste_avisa():
    rep = mate("imperial_torpedo", "adaptador", autoajuste=False, diam_max=70, diam_boca=70)["report"]
    assert not rep["valid"]
    assert any("sale" in e or "fina" in e for e in rep["errors"]), rep


@pytest.mark.spec("MAT-003")
def test_crece_en_alto_si_el_inserto_es_hondo():
    rep = mate("cilindrico", "adaptador", altura=60)["report"]
    assert rep["altura_mm"] >= 85 + 0.2 + 4.0 - 0.01
    assert rep["fondo_mm"] >= 3.95


# ----------------------------------------------------------------- MAT-004
@pytest.mark.spec("MAT-004")
def test_hueco_para_los_dos():
    env = mc.envolvente([mc.INSERTOS["polimero"]["perfil"], mc.INSERTOS["adaptador"]["perfil"]])
    pol, ada = mc.INSERTOS["polimero"]["perfil"], mc.INSERTOS["adaptador"]["perfil"]
    assert max(d for _, d in env) == pytest.approx(85.0)
    for k in range(1, 170):
        d = k * 0.5
        assert radio_en(env, d) >= max(radio_en(pol, d), radio_en(ada, d)) - 1e-6, d
    rep = mate("imperial_clasico", "ambos")["report"]
    assert rep["insertos"] == [mc.INSERTOS["polimero"]["nombre"], mc.INSERTOS["adaptador"]["nombre"]]


# ----------------------------------------------------------------- MAT-005
@pytest.mark.spec("MAT-005")
@pytest.mark.parametrize("formato", ["binario", "ascii"])
def test_inserto_propio(formato):
    with open(STL["polimero"], "rb") as fh:
        data = fh.read()
    if formato == "ascii":
        data = a_ascii(data)
    propio = mc.build_mate({"tipo": "facetado", "inserto": "propio", "stl_propio": data})
    base = mate("facetado", "polimero")
    assert propio["report"]["valid"]
    assert propio["report"]["hueco_diam_mm"] == pytest.approx(base["report"]["hueco_diam_mm"], abs=0.1)
    assert propio["report"]["hueco_prof_mm"] == pytest.approx(base["report"]["hueco_prof_mm"], abs=0.1)
    assert propio["report"]["inserto_propio"]["diam_abertura_mm"] == pytest.approx(69.84, abs=0.05)


@pytest.mark.spec("MAT-005")
@pytest.mark.parametrize("data", [caja_stl(), b"esto no es un stl", b""])
def test_inserto_propio_invalido(tmp_path, data):
    with pytest.raises(ValueError) as e:
        mc.build_mate({"tipo": "imperial_clasico", "inserto": "propio", "stl_propio": data})
    assert any(w in str(e.value) for w in ("revolución", "STL", "Subí"))
    p = tmp_path / "x.stl"
    p.write_bytes(data)
    r = mate_web.analizar_stl(str(p))
    assert not r["ok"] and r["error"]
    rep = mate_web.build({"tipo": "imperial_clasico", "inserto": "propio", "stl_path": str(p)})["summary"]
    assert not rep["valid"] and rep["errors"]


# ----------------------------------------------------------------- MAT-006
@pytest.mark.spec("MAT-006")
def test_descargas():
    o = {"tipo": "cohete", "inserto": "ambos"}
    name, data = mate_web.export_stl(o)
    assert name == "Mate-COHETE-AMBOS.stl"
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n and n > 10_000
    name, data = mate_web.export_3mf(o)
    assert name == "Mate-COHETE-AMBOS.3mf"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert 'name="Copyright"' in model and 'name="LicenseTerms"' in model
    assert "<triangle " in model


@pytest.mark.spec("MAT-006", "MAT-008")
def test_build_para_la_web():
    r = mate_web.build({"tipo": "vaso_redondeado", "inserto": "polimero"})
    assert r["summary"]["valid"]
    assert [p["name"] for p in r["parts"]] == ["MACETA", "INSERTO"]
    for p in r["parts"]:
        assert len(p["positions"]) == p["vertices"] * 12
        assert len(p["indices"]) == p["triangles"] * 12
    info = mate_web.info()
    assert len(info["tipos"]) == 10
    assert [i["id"] for i in info["insertos"]] == ["polimero", "adaptador", "ambos", "propio"]


# ----------------------------------------------------------------- MAT-007
@pytest.mark.spec("MAT-007")
@pytest.mark.parametrize("tipo", ["facetado", "cohete", "imperial_copa"])
def test_rapido(tipo):
    t0 = time.time()
    mc.build_mate({"tipo": tipo, "inserto": "ambos"})
    assert time.time() - t0 < 3.0
