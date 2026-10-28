# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Sopa de letras 3D: palabras, piezas que encastran, cama, mallas y descargas."""
import io
import math
import struct
import time
import zipfile

import pytest

import sopa_core as sc
import sopa_web

ARG = ["mate", "yerba", "bombilla", "termo", "pava", "asado", "empanada", "alfajor", "tango",
       "gaucho", "ñandú", "dulce de leche", "chamamé", "folclore", "pampa"]
ANIMALES = ["perro", "gato", "loro", "vaca", "caballo", "oveja", "conejo", "tortuga",
            "jirafa", "elefante", "leon", "tigre", "zorro", "puma", "carpincho", "yacare",
            "hornero", "tero", "ballena", "delfin", "pinguino", "condor", "llama", "vicuña",
            "guanaco"]


def leer(sopa, u):
    g = sopa["grid"]
    return "".join(g[u["fila"] + u["df"] * i][u["col"] + u["dc"] * i] for i in range(len(u["palabra"])))


def dentro(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def d_seg(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def d_poly(P, Q):
    """Distancia mínima entre los bordes de dos polígonos (vértices contra segmentos)."""
    m = 1e9
    for A, B in ((P, Q), (Q, P)):
        segs = list(zip(B, B[1:] + B[:1]))
        for p in A:
            for a, b in segs:
                m = min(m, d_seg(p, a, b))
    return m


# ----------------------------------------------------------------- SOP-001
@pytest.mark.spec("SOP-001")
@pytest.mark.parametrize("palabras", [ARG, ANIMALES])
@pytest.mark.parametrize("dif", ["facil", "media", "dificil"])
@pytest.mark.parametrize("semilla", [1, 7, 42])
def test_las_palabras_estan(palabras, dif, semilla):
    s = sc.generar(palabras, dificultad=dif, semilla=semilla)
    assert s["ubicadas"]
    for u in s["ubicadas"]:
        assert leer(s, u) == u["palabra"]
        assert (u["df"], u["dc"]) in sc.DIRECCIONES[dif]
    assert len(s["ubicadas"]) + len(s["faltan"]) == len(sc.limpiar_palabras(palabras)[0])
    assert all(len(f) == s["cols"] for f in s["grid"]) and len(s["grid"]) == s["filas"]
    assert all(ch in sc.ALFABETO for f in s["grid"] for ch in f)


@pytest.mark.spec("SOP-001")
def test_las_que_no_entran_se_avisan():
    r = sc.build_sopa({"palabras": ANIMALES, "filas": 6, "cols": 6})
    assert r["sopa"]["faltan"]
    assert any("No entraron" in w for w in r["report"]["warnings"])


# ----------------------------------------------------------------- SOP-002
@pytest.mark.spec("SOP-002")
def test_limpieza_de_palabras():
    limpias, descartadas = sc.limpiar_palabras(["ñandú", "Dulce de leche", "MATE", "mate", "a",
                                                "  ", "Chamamé!", "pingüino"])
    assert limpias == ["ÑANDU", "DULCEDELECHE", "MATE", "CHAMAME", "PINGUINO"]
    assert descartadas == ["a"]
    a = sc.generar(ARG, semilla=5)
    b = sc.generar(ARG, semilla=5)
    assert a["grid"] == b["grid"]
    assert sc.generar(ARG, semilla=6)["grid"] != a["grid"]


# ----------------------------------------------------------------- SOP-003
@pytest.mark.spec("SOP-003")
@pytest.mark.parametrize("piezas,holgura", [(2, 0.2), (3, 0.3), (3, 0.0)])
def test_piezas_encastran(piezas, holgura):
    s = sc.generar(ARG, semilla=3)
    p = sc.parametros({"piezas_x": piezas, "piezas_y": piezas, "holgura": holgura})
    pz, info = sc.armar_piezas(s, p)
    assert len(pz) == piezas * piezas
    assert info["sin_lengueta"] == 0
    assert info["lenguetas"] >= 2 * piezas * (piezas - 1)
    k = info["lengueta"]
    assert k["cabeza"] > k["cuello"] * 1.5             # la cabeza traba
    cap = info["cap_mm"]
    for a in pz:
        # cada letra entera dentro de su pieza, sin tocar el borde
        for ch, (x, y) in a["letras"]:
            res, _ = sc.glifo(ch, cap)
            for ext, _h in res:
                for q in ext[::3]:
                    pt = (x + q[0], y + q[1])
                    assert dentro(pt, a["contorno"]), (a["nombre"], ch)
                    for b in pz:
                        if b is not a:
                            assert not dentro(pt, b["contorno"])
    # vecinas: separadas exactamente por la holgura; las demás, lejos
    for i, a in enumerate(pz):
        for b in pz[i + 1:]:
            vecinas = abs(a["i"] - b["i"]) + abs(a["j"] - b["j"]) == 1
            d = d_poly(a["contorno"], b["contorno"])
            if vecinas:
                assert d == pytest.approx(holgura, abs=0.05), (a["nombre"], b["nombre"], d)
            assert d >= holgura - 0.05
            if holgura > 0:                       # con holgura 0 comparten el borde
                for q in a["contorno"][::4]:
                    assert not dentro(q, b["contorno"])


@pytest.mark.spec("SOP-003")
def test_piezas_no_se_superponen_en_3d():
    manifold3d = pytest.importorskip("manifold3d")
    import numpy as np
    r = sc.build_sopa({"palabras": ARG, "semilla": 2, "piezas_x": 3, "piezas_y": 3, "lista": False})
    ms = []
    for pz in r["piezas"]:
        V, F = pz["placa"]
        ms.append(manifold3d.Manifold(manifold3d.Mesh(np.array(V, dtype=np.float32),
                                                      np.array(F, dtype=np.uint32))))
    for i in range(len(ms)):
        assert ms[i].status() == manifold3d.Error.NoError
        for j in range(i + 1, len(ms)):
            assert (ms[i] ^ ms[j]).volume() < 1e-3


# ----------------------------------------------------------------- SOP-004
@pytest.mark.spec("SOP-004")
@pytest.mark.parametrize("cama", [180, 220, 256, 350])
@pytest.mark.parametrize("n", [10, 16, 20])
def test_entran_en_la_cama(cama, n):
    r = sc.build_sopa({"palabras": ANIMALES, "filas": n, "cols": n, "cama": cama, "celda": 15})
    rep = r["report"]
    assert rep["entra_en_cama"]
    assert rep["piezas_x"] >= 2 and rep["piezas_y"] >= 2
    for pz in r["piezas"]:
        assert max(pz["medidas_mm"]) <= cama - 5, (pz["nombre"], pz["medidas_mm"])


# ----------------------------------------------------------------- SOP-005
@pytest.mark.spec("SOP-005")
def test_mallas_cerradas():
    r = sc.build_sopa({"palabras": ARG, "semilla": 9})
    assert r["report"]["valid"] and r["report"]["cerradas"]
    for pz in r["piezas"]:
        for V, F in (pz["placa"], pz["letras"]):
            assert sc.mesh_check(F)["closed"]
            assert sc.mesh_volume(V, F) > 0
    assert any(pz["nombre"] == "LISTA" for pz in r["piezas"])


@pytest.mark.spec("SOP-005")
def test_descargas():
    o = {"palabras": ARG, "semilla": 4, "dificultad": "dificil"}
    rep = sc.build_sopa(o)["report"]
    name, data = sopa_web.export_3mf(o)
    assert name == rep["sku"] + ".3mf" and name.startswith("Sopa-") and "DIFICIL" in name
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert model.count("<object ") == rep["piezas"] + 1 + rep["marcadores"]   # + lista + marcadores
    assert rep["marcadores"] == rep["palabras"]
    assert 'name="Copyright"' in model and 'name="LicenseTerms"' in model
    name, data = sopa_web.export_stl(o)
    n = struct.unpack("<I", data[80:84])[0]
    assert name.endswith(".stl") and len(data) == 84 + 50 * n and n > 10_000


@pytest.mark.spec("SOP-005", "SOP-007")
def test_build_para_la_web():
    r = sopa_web.build({"palabras": ARG, "semilla": 1})
    s = r["summary"]
    assert s["valid"] and len(s["grid"]) == s["filas"]
    nombres = {p["name"] for p in r["parts"]}
    assert {"MACETA", "LETRAS", "SOLUCION"} <= nombres
    tablero = {p["pieza"] for p in r["parts"] if p["name"] != "MARCADOR"}
    assert len(tablero) == s["piezas"] + 1
    assert len([p for p in r["parts"] if p["name"] == "MARCADOR"]) == s["marcadores"] == len(s["ubicadas"])
    vacia = sopa_web.build({"palabras": []})["summary"]
    assert not vacia["valid"] and vacia["errors"]


# ----------------------------------------------------------------- SOP-006
@pytest.mark.spec("SOP-006")
def test_rapido():
    t0 = time.time()
    r = sc.build_sopa({"palabras": ANIMALES, "filas": 20, "cols": 20, "dificultad": "dificil"})
    assert r["report"]["valid"]
    assert time.time() - t0 < 3.0


# ----------------------------------------------------------------- SOP-009
def _pts_letra(r, sopa, p, cap, rc):
    return sc._puntos_letra(sopa, p, cap, *rc)


@pytest.mark.spec("SOP-009")
@pytest.mark.parametrize("dif", ["facil", "media", "dificil"])
@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_marcadores_agarran_y_no_se_tocan(dif, semilla):
    r = sc.build_sopa({"palabras": ARG, "semilla": semilla, "dificultad": dif})
    sopa, p, rep = r["sopa"], r["params"], r["report"]
    cap = rep["letra_mm"]
    marcs = r["marcadores"]
    assert len(marcs) == len(sopa["ubicadas"]) and rep["marcadores"] == len(marcs)
    usadas = {}
    for u in sopa["ubicadas"]:                          # sin letras compartidas
        for i in range(len(u["palabra"])):
            rc = (u["fila"] + u["df"] * i, u["col"] + u["dc"] * i)
            assert rc not in usadas, (u["palabra"], usadas.get(rc))
            usadas[rc] = u["palabra"]
    capsulas = []
    for mk in marcs:
        u = next(x for x in sopa["ubicadas"] if x["palabra"] == mk["palabra"])
        m = sc.medir_marcador(sopa, p, cap, u)
        A, B, ri, w = m["A"], m["B"], m["ri"], m["pared"]
        assert w >= sc.PARED_MARCADOR_MIN - 1e-6
        d = lambda q: sc._d_seg(q[0], q[1], A[0], A[1], B[0], B[1])
        propias = [q for rc in m["celdas"] for q in sc._puntos_letra(sopa, p, cap, *rc)]
        holgura_min = min(ri - d(q) for q in propias)
        assert holgura_min >= 0                               # todas adentro
        assert holgura_min == pytest.approx(p["ajuste"], abs=0.05)   # la más saliente agarra
        for rr in range(sopa["filas"]):
            for cc in range(sopa["cols"]):
                if (rr, cc) in m["celdas"]:
                    continue
                for q in sc._puntos_letra(sopa, p, cap, rr, cc):
                    assert d(q) >= ri + w + sc.LUZ_VECINAS - 1e-6
        V, F = mk["malla"]
        assert sc.mesh_check(F)["closed"] and sc.mesh_volume(V, F) > 0
        capsulas.append((A, B, ri + w))
    for i, (A, B, ro) in enumerate(capsulas):
        for A2, B2, ro2 in capsulas[i + 1:]:
            dist = sc._d_segs((A[0], A[1], B[0], B[1]), (A2[0], A2[1], B2[0], B2[1]))
            assert dist > ro + ro2


@pytest.mark.spec("SOP-009")
def test_sin_marcadores_las_palabras_se_pueden_cruzar():
    r = sc.build_sopa({"palabras": ARG, "semilla": 1, "marcadores": False})
    assert r["marcadores"] == [] and r["report"]["marcadores"] == 0
    assert r["report"]["letra_mm"] == pytest.approx(0.48 * 15, abs=0.01)


@pytest.mark.spec("SOP-009")
def test_marcadores_mas_flojos_con_mas_ajuste():
    a = sc.build_sopa({"palabras": ARG, "semilla": 2, "dificultad": "facil", "ajuste": 0.1})
    b = sc.build_sopa({"palabras": ARG, "semilla": 2, "dificultad": "facil", "ajuste": 0.3})
    assert b["marcadores"][0]["ri_mm"] == pytest.approx(a["marcadores"][0]["ri_mm"] + 0.2, abs=0.011)
