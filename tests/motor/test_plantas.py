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
    tres = ["echeveria", "cereus", "pothos"]                  # tres tipos distintos
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, tres,
                        cobertura="piedra_blanca")
    assert r["ids"] == tres and r["parts"]
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


# ------------------------------------------------------------------ una por tipo
GRUPOS = {g["id"] for g in P.catalogo()["grupos"]}


@pytest.mark.spec("PLA-006")
def test_cada_planta_tiene_un_grupo_conocido():
    assert len(GRUPOS) >= 5
    for pid in IDS:
        assert P.ficha(pid)["grupo"] in GRUPOS, pid
    for g in GRUPOS:
        assert any(P.ficha(i)["grupo"] == g for i in IDS), g


@pytest.mark.spec("PLA-006")
@pytest.mark.parametrize("pedido,queda", [
    (["echeveria", "aloe"], ["aloe"]),                          # misma familia: gana la última
    (["echeveria", "cereus", "cardon"], ["echeveria", "cardon"]),
    (["ceibo", "jacaranda", "yerba_mate", "cortadera"], ["jacaranda", "cortadera"]),
    (["echeveria", "cereus", "pothos", "sansevieria", "ceibo"], ["echeveria", "cereus", "pothos", "sansevieria"]),
    (["echeveria", "inventada"], ["echeveria"]),
])
def test_una_planta_por_tipo(pedido, queda):
    assert P.limpiar_ids(pedido) == queda
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, pedido, decor=False)
    assert r["ids"] == queda
    assert sorted({p["planta"] for p in r["parts"]}) == list(range(len(queda)))


# ------------------------------------------------------------------ nativas
NATIVAS = ["ceibo", "jacaranda", "ombu", "yerba_mate", "cortadera", "lapacho", "espinillo",
           "cardon", "arrayan"]


@pytest.mark.spec("PLA-007")
def test_nueve_nativas_argentinas():
    for pid in NATIVAS:
        f = P.ficha(pid)
        assert f["nativa"] is True and pid in P.GENERADORES, pid
        assert f["grupo"] in ("arboles_nativos", "arbustos_nativos", "cactus"), pid
    assert sum(P.ficha(i).get("nativa", False) for i in IDS) == len(NATIVAS)
    # datos que las identifican
    assert "Erythrina crista-galli" in P.ficha("ceibo")["cientifico"]
    assert "Jacaranda mimosifolia" in P.ficha("jacaranda")["cientifico"]
    assert "Phytolacca dioica" in P.ficha("ombu")["cientifico"]
    assert "Ilex paraguariensis" in P.ficha("yerba_mate")["cientifico"]
    assert "flor nacional" in P.ficha("ceibo")["resumen"].lower()


@pytest.mark.spec("PLA-007")
def test_toxicidad_de_las_nativas_con_fuente():
    fu = P.catalogo()["fuentes"]
    assert P.ficha("jacaranda")["mascotas"]["toxica"] and "ucanr.edu" in fu["jacaranda"]
    assert P.ficha("ombu")["mascotas"]["toxica"] and "ombu" in fu
    assert "cafeína" in P.ficha("yerba_mate")["mascotas"]["detalle"]
    for pid in ("cardon", "espinillo"):
        assert "espina" in P.ficha(pid)["mascotas"]["detalle"].lower()


@pytest.mark.spec("PLA-007")
@pytest.mark.parametrize("pid,mat", [("ceibo", "flor_roja"), ("jacaranda", "flor_violeta"),
                                     ("lapacho", "flor_rosa"), ("espinillo", "flor_amarilla"),
                                     ("cortadera", "pluma"), ("arrayan", "corteza_canela"),
                                     ("cardon", "verde_cardon")])
def test_nativas_con_su_rasgo(pid, mat):
    mats = {m for m, _, _ in P.build([pid], AB)}
    assert mat in mats, (pid, mats)


@pytest.mark.spec("PLA-007")
@pytest.mark.parametrize("pid", NATIVAS)
def test_nativas_livianas_para_la_web(pid):
    tris = sum(len(F) for _, _, F in P.build([pid], AB))
    assert 2000 < tris < 40000, (pid, tris)


# ------------------------------------------------------------------ tipos de tierra
@pytest.mark.spec("PLA-008")
@pytest.mark.parametrize("cob", sorted(P.COBERTURAS))
def test_cobertura_dentro_de_la_boca(cob):
    ids = ["echeveria", "cereus"]
    items = P.decor(AB, ids, cobertura=cob)
    mats = [m for m, _, _ in items]
    assert mats[0] in ("tierra", "tierra_oscura") and len(items) >= 2, mats
    for m, V, F in items:
        assert m in P.MATERIALES and m in P.DECOR_MATS
        assert _area_ok(V, F)
        assert max(math.hypot(x, y) for x, y, _ in V) <= AB["r_in"] + 1e-6
        assert min(z for _, _, z in V) >= AB["z_s"] - 3.01
    # los granos no tapan el pie de las plantas
    for (x, y, R) in P.layout(len(ids), AB["r_in"]):
        for m, V, F in items[1:]:
            assert all(math.hypot(vx - x, vy - y) > R * 0.2 for vx, vy, vz in V if vz > AB["z_s"] + 0.5)


@pytest.mark.spec("PLA-008")
def test_coberturas_distintas_y_sugerida():
    vistos = {tuple(sorted({m for m, _, _ in P.decor(AB, ["aloe"], cobertura=c)})) for c in P.COBERTURAS}
    assert len(vistos) == len(P.COBERTURAS) >= 6
    assert P.cobertura_sugerida(["cereus"]) == "volcanica"
    assert P.cobertura_sugerida(["yerba_mate"]) == "musgo"
    assert P.cobertura_sugerida(["pothos"]) == "piedra_blanca"
    assert P.cobertura_sugerida(["cereus", "yerba_mate"]) == "volcanica"   # manda la más sensible
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, ["arrayan"])
    assert r["cobertura"] == "musgo" and any(p["name"] == "musgo" for p in r["parts"])
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, ["arrayan"], cobertura="leca")
    assert r["cobertura"] == "leca" and any(p["name"] == "leca" for p in r["parts"])
    info = eden_web.info()
    assert {c["id"] for c in info["coberturas"]} == set(P.COBERTURAS)


# ------------------------------------------------------------------ animación (datos)
@pytest.mark.spec("VIS-005")
def test_partes_por_planta_para_animar():
    ids = ["cardon", "pothos", "jacaranda"]
    r = eden_web.plants({"design": "ROMBO", "size": "S", "quality": "preview"}, ids)
    tierra = [p for p in r["parts"] if p["planta"] == -1]
    assert tierra and all(p["flex"] == 0 for p in tierra)
    for k, pid in enumerate(ids):
        ps = [p for p in r["parts"] if p["planta"] == k]
        assert ps, pid
        assert len({tuple(p["base"]) for p in ps}) == 1             # un pivote por planta
        assert ps[0]["flex"] == P.FLEX[pid]
    assert P.FLEX["cardon"] < 0.2 and P.FLEX["pothos"] == 1.0 and P.FLEX["lithops"] == 0
    assert set(P.FLEX) == set(P.GENERADORES)
