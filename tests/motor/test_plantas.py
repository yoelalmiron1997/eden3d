# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Plantas 3D, fichas de cuidado y compatibilidad."""
import math

import pytest

import eden_plantas as P
import eden_web

AB = {"r_in": 36.5, "z_s": 71.1, "z_top": 77.4, "r_out": 46.1, "z_bot": 3.6}
IDS = [p["id"] for p in P.catalogo()["plantas"]]
CAMPOS = ("luz", "sustrato", "humedad", "fertilizante", "trasplante", "propagacion", "plagas",
          "resumen", "cientifico", "tipo", "dificultad")


def _area_ok(V, F):
    for a, b, c in F:
        A, B, C = V[a], V[b], V[c]
        u = [B[i] - A[i] for i in range(3)]
        v = [C[i] - A[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        if n[0] ** 2 + n[1] ** 2 + n[2] ** 2 <= 1e-12:
            return False
    return True


@pytest.mark.spec("PLA-001")
def test_hay_al_menos_10_plantas_de_varios_tipos():
    assert len(IDS) >= 10 and len(set(IDS)) == len(IDS)
    assert set(IDS) == set(P.GENERADORES)
    tipos = " ".join(P.ficha(i)["tipo"] for i in IDS)
    for t in ("Suculenta", "Cactus", "colgante", "Follaje"):
        assert t.lower() in tipos.lower(), t


@pytest.mark.spec("PLA-001")
@pytest.mark.parametrize("pid", IDS)
def test_malla_de_cada_planta(pid):
    parts = P.build([pid], AB)
    assert parts
    for mat, V, F in parts:
        assert mat in P.MATERIALES, mat
        assert F and max(max(f) for f in F) < len(V)
        assert _area_ok(V, F), (pid, mat)
    if not P.ficha(pid)["colgante"]:
        r = max(math.hypot(x, y) for _, V, _ in parts for x, y, _ in V)
        assert r <= 1.6 * AB["r_in"], (pid, r)
    # puede enterrarse un poco en la tierra (como una planta real), no hundirse
    zmin = min(z for _, V, _ in parts for _, _, z in V)
    assert zmin >= AB["z_s"] - 0.25 * AB["r_in"] or P.ficha(pid)["colgante"]


@pytest.mark.spec("PLA-002")
@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_layout_sin_superponer(n):
    L = P.layout(n, AB["r_in"])
    assert len(L) == n
    for x, y, R in L:
        assert math.hypot(x, y) + R <= AB["r_in"] * 1.0 + 1e-6
    for i in range(n):
        for j in range(i + 1, n):
            (x1, y1, r1), (x2, y2, r2) = L[i], L[j]
            assert math.hypot(x1 - x2, y1 - y2) >= (r1 + r2) * 0.98


@pytest.mark.spec("PLA-002")
def test_maximo_4_plantas():
    ids = IDS[:6]
    parts = P.build(ids, AB)
    assert parts
    assert any(c["nivel"] == "error" for c in P.compatibilidad(ids))
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, ids[:3])
    assert r["ids"] == ids[:3] and r["parts"]
    mats = {p["name"] for p in r["parts"]}
    assert {"tierra", "piedra"} <= mats


@pytest.mark.spec("PLA-003")
@pytest.mark.parametrize("pid", IDS)
def test_ficha_completa(pid):
    f = P.ficha(pid)
    for k in CAMPOS:
        assert str(f.get(k, "")).strip(), (pid, k)
    for k in ("primavera_verano", "otono_invierno", "como"):
        assert f["riego"][k].strip(), (pid, k)
    assert f["temperatura"]["min"] < f["temperatura"]["max"]
    assert f["autorriego"]["nivel"] in ("recomendado", "con-cuidado", "no-recomendado")
    assert "{min_ml}" in f["autorriego"]["consejo"]
    assert len(f["senales"]) >= 3
    for s in f["senales"]:
        assert s["sintoma"] and s["causa"] and s["solucion"]
    assert isinstance(f["mascotas"]["toxica"], bool) and f["mascotas"]["detalle"]
    assert f["grupo_riego"] in ("seco", "medio", "humedo")
    assert f["grupo_luz"] in ("sol", "brillante", "media")


@pytest.mark.spec("PLA-004")
@pytest.mark.parametrize("ids,nivel,palabra", [
    (["echeveria", "pothos"], "aviso", "Riego distinto"),
    (["cereus", "pothos"], "alerta", "Luz distinta"),
    (["echeveria", "haworthia"], "ok", "compatible"),
    (["cereus", "mammillaria"], "aviso", "cactus"),
])
def test_compatibilidad(ids, nivel, palabra):
    c = P.compatibilidad(ids)
    assert any(x["nivel"] == nivel and palabra in x["texto"] for x in c), c
