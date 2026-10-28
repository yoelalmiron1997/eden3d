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
    assert model.count("<object ") == rep["piezas"] + 1 + rep["bloques"]   # + lista + bloques
    assert model.count("BLOQUE_") == rep["bloques"] > 0
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
    tablero = {p["pieza"] for p in r["parts"] if p["name"] != "BLOQUE"}
    assert len(tablero) == s["piezas"] + 1
    assert len([p for p in r["parts"] if p["name"] == "BLOQUE"]) == 1      # un modelo; la web lo copia
    for u in s["ubicadas"]:
        assert len(u["centros"]) == len(u["palabra"])
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
@pytest.mark.spec("SOP-009")
@pytest.mark.parametrize("cap", [6.0, 7.2, 9.0])
@pytest.mark.parametrize("ajuste", [0.0, 0.1, 0.25])
def test_un_bloque_agarra_cualquier_letra(cap, ajuste):
    p = sc.parametros({"ajuste": ajuste})
    m = sc.medidas_bloque(p, cap)
    iw, ih = m["hueco"]
    _, (_, h0, _, h1) = sc.glifo("H", cap)
    for ch in sc.ALFABETO:
        res, (x0, y0, x1, y1) = sc.glifo(ch, cap)
        assert y0 == pytest.approx(h0, abs=0.02) and y1 == pytest.approx(h1, abs=0.02), ch
        for ext, _h in res:
            for x, y in ext:
                assert abs(x) <= iw / 2 - sc.LUZ_LATERAL + 1e-6 and abs(y) <= ih / 2 + 1e-6
        assert ih / 2 - max(abs(y0), abs(y1)) == pytest.approx(ajuste, abs=0.02), ch


@pytest.mark.spec("SOP-009")
@pytest.mark.parametrize("dif", ["facil", "dificil"])
def test_bloques_en_el_tablero(dif):
    r = sc.build_sopa({"palabras": ARG, "semilla": 3, "dificultad": dif})
    sopa, p, rep = r["sopa"], r["params"], r["report"]
    cap = rep["letra_mm"]
    assert rep["bloques"] == max(len(u["palabra"]) for u in sopa["ubicadas"]) == 12   # DULCEDELECHE
    ow, oh = sc.medidas_bloque(p, cap)["afuera"]
    cel = p["celda"]
    assert ow < cel and oh < cel                       # vecinos (y en diagonal) no se tocan
    # puesto en cualquier celda, no toca las letras de al lado
    for r0 in range(sopa["filas"]):
        for c0 in range(sopa["cols"]):
            cx, cy = sc.centro_celda(sopa, p, r0, c0)
            for rr in range(max(0, r0 - 1), min(sopa["filas"], r0 + 2)):
                for cc in range(max(0, c0 - 1), min(sopa["cols"], c0 + 2)):
                    if (rr, cc) == (r0, c0):
                        continue
                    for x, y in sc._puntos_letra(sopa, p, cap, rr, cc):
                        dx = max(0.0, abs(x - cx) - ow / 2)
                        dy = max(0.0, abs(y - cy) - oh / 2)
                        assert math.hypot(dx, dy) >= sc.LUZ_VECINAS
    V, F = r["bloque"]
    assert sc.mesh_check(F)["closed"] and sc.mesh_volume(V, F) > 0
    assert min(v[2] for v in V) == pytest.approx(0.0)


@pytest.mark.spec("SOP-009")
def test_sin_bloques():
    r = sc.build_sopa({"palabras": ARG, "semilla": 1, "bloques": False})
    assert r["bloque"] is None and r["report"]["bloques"] == 0
    name, data = sopa_web.export_3mf({"palabras": ARG, "semilla": 1, "bloques": False})
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert "BLOQUE" not in z.read("3D/3dmodel.model").decode("utf-8")
