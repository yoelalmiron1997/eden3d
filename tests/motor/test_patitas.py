# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Macetas articuladas: patitas y bracitos que se imprimen armados (PAT-001..004)."""
import io
import math
import zipfile

import numpy as np
import pytest
from scipy.spatial import cKDTree

import eden_catalog as ec
import eden_core as core
import eden_patitas as pt
import eden_web as ew

_CACHE = {}


def maceta(mode="pot", size="S"):
    key = (mode, size)
    if key not in _CACHE:
        _CACHE[key] = core.build_pot(ew.params({"mode": mode, "size": size}))
    return _CACHE[key]


def nube(shells, dens=0.3):
    """Puntos sobre la superficie (cada ~dens mm), para medir distancias entre sólidos."""
    out = []
    for V, F in shells:
        V = np.asarray(V, dtype=float)
        T = V[np.asarray(F)]
        L = np.max(np.linalg.norm(T[:, [1, 2, 2]] - T[:, [0, 0, 1]], axis=2), axis=1)
        N = np.maximum(1, (L / dens).astype(int))
        for n in np.unique(N):
            g = [(i / n, j / n) for i in range(n + 1) for j in range(n + 1 - i)]
            B = np.array(g)
            Tn = T[N == n]
            out.append((Tn[:, None, 0] + B[None, :, :1] * (Tn[:, None, 1] - Tn[:, None, 0])
                        + B[None, :, 1:] * (Tn[:, None, 2] - Tn[:, None, 0])).reshape(-1, 3))
    return np.vstack(out)


# ----------------------------------------------------------------- PAT-001
@pytest.mark.spec("PAT-001")
@pytest.mark.parametrize("holgura", [0.35, 0.45, 0.6])
def test_cadenas_cerradas_y_con_holgura(holgura):
    res = maceta()
    nombre, cad, info = pt.armar(res, {"tipo": "patas_brazos", "eslabones": 3, "holgura": holgura})
    pared = cKDTree(np.asarray(res["vertices"]))
    todas = []
    for c in cad:
        piezas = [c["soporte"]] + [e["shells"] for e in c["eslabones"]]
        for sh in piezas:
            for V, F in sh:
                assert ew.mesh_check(F)["closed"] and pt._vol(V, F) > 0
                assert min(v[2] for v in V) >= -1e-9
        nubes = [nube(s) for s in piezas]
        trees = [cKDTree(n) for n in nubes]
        for k in range(len(piezas) - 1):
            d, _ = trees[k + 1].query(nubes[k])
            assert d.min() == pytest.approx(holgura, abs=0.05), (c["nombre"], k)
        for k in range(len(piezas)):
            for j in range(k + 2, len(piezas)):
                assert trees[j].query(nubes[k], distance_upper_bound=holgura + 0.1)[0].min() > holgura
        d, _ = pared.query(nubes[1], distance_upper_bound=holgura + 0.1)
        assert d.min() > holgura
        assert min(min(v[2] for v in V) for V, _ in piezas[1]) == pytest.approx(0.0, abs=1e-6)
        todas.append(np.vstack(nubes[1:])[::7])
    # las dos patas (y los brazos) no se tocan entre sí
    for i in range(len(todas)):
        for j in range(i + 1, len(todas)):
            assert cKDTree(todas[j]).query(todas[i], distance_upper_bound=2.5)[0].min() > 2.0


# ----------------------------------------------------------------- PAT-002
@pytest.mark.spec("PAT-002")
@pytest.mark.parametrize("D", [55.0, 92.0, 150.0, 200.0])
@pytest.mark.parametrize("brazo", [False, True])
def test_bisagra_gira_libre(D, brazo):
    m = pt.medidas(D, 0.45, brazo)
    t, c = m["t"], m["c"]
    assert 8.0 <= t <= 14.0
    assert m["rb"] + c == pytest.approx(m["Rr"] - m["rr"])          # barra en el agujero
    assert 2 * m["rb"] >= 2.5
    assert m["W"] - 2 * m["pw"] >= 2 * m["rr"] + 2 * c              # el anillo cabe entre púas
    assert m["u_s"] >= math.hypot(m["pe"], t / 2) + c - 1e-9        # el cuerpo siguiente no choca
    assert m["Rr"] + m["rr"] == pytest.approx(t / 2)                # el anillo apoya en la cama
    assert m["pe"] < m["Rr"] - 0.3 - c                              # las púas no tocan el cuello
    cuerpo = m["P"] - t / 2 - c - m["u_s"]                         # cuerpo con largo de verdad
    assert cuerpo >= 0.3 * t - 1e-9


@pytest.mark.spec("PAT-002")
def test_rodilla_gira_90_grados_sin_chocar():
    """Girando el eslabón siguiente ±90° alrededor de la barra, no toca al anterior."""
    m = pt.medidas(92.0, 0.45)
    cad = pt.cadena(m, 2, "bota")
    a = nube(cad[0]["shells"])
    b = nube(cad[1]["shells"])
    eje = np.array([m["P"], 0.0, m["t"] / 2])
    for ang in (-90, -45, 45, 90):
        r = math.radians(ang)
        R = np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])
        bb = (b - eje) @ R.T + eje
        assert cKDTree(a).query(bb)[0].min() > 0.3, ang


# ----------------------------------------------------------------- PAT-003
@pytest.mark.spec("PAT-003")
@pytest.mark.parametrize("mode", ["pot", "screw_dish_sw", "screw_dish", "saucer"])
def test_siempre_sin_plato_y_clavadas_a_la_base(mode):
    o = {"mode": mode, "size": "S", "patitas": {"tipo": "patas_brazos"}}
    p = ew.params(o)
    assert p["mode"] == "pot"
    r = ew.build(o)
    assert "SOLA" in r["summary"]["sku"]
    assert [x["name"] for x in r["parts"] if not x["name"].startswith(("PATA", "BRAZO"))] == ["MACETA"]
    res = core.build_pot(p)
    nombre, cad, info = pt.armar(res, o["patitas"])
    assert nombre == "MACETA" and info["pieza"] == "MACETA"
    tex, pared = float(p.get("tex_amp") or 0), float(p["wall"])
    zocalos = cad[0]["soporte"][-3:]                    # uno para las patas y uno por brazo
    assert len(zocalos) == 3
    for V, F in zocalos:
        assert ew.mesh_check(F)["closed"]
        rs = pt._radios(res["vertices"], max(v[2] for v in V))   # la pared a la altura del zócalo
        afuera = adentro = 0
        for x, y, z in V:
            k = int(round(math.degrees(math.atan2(y, x)))) % 360
            d = math.hypot(x, y) - rs[k]
            assert d >= -tex - 0.6 * pared - 1e-6          # no pasa al lado de adentro
            afuera += d > 0.5
            adentro += d < -0.1
        assert afuera and adentro                          # abraza la pared: adentro y afuera
    # el primer eslabón de cada cadena no toca ningún soporte (zócalos incluidos)
    sop = cKDTree(np.vstack([nube(c["soporte"]) for c in cad]))
    for c in cad:
        assert sop.query(nube(c["eslabones"][0]["shells"]), distance_upper_bound=1)[0].min() > 0.4


@pytest.mark.spec("PAT-003")
@pytest.mark.parametrize("tipo", ["patas", "patas_brazos", "brazos"])
def test_descargas_traen_las_patitas(tipo):
    o = {"mode": "pot", "size": "S"}
    n0, d0 = ew.export_stl(o, "MACETA")
    n1, d1 = ew.export_stl(dict(o, patitas={"tipo": tipo}), "MACETA")
    t0, t1 = int.from_bytes(d0[80:84], "little"), int.from_bytes(d1[80:84], "little")
    assert t1 > t0 + 5000
    name, data = ew.export_3mf(dict(o, patitas={"tipo": tipo}))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.read("3D/3dmodel.model").count(b"<triangle ") >= t1
    res = maceta()
    res2 = {"vertices": list(res["vertices"]), "faces": list(res["faces"]), "parts": [],
            "params": res["params"], "report": dict(res["report"])}
    pt.agregar(res2, {"tipo": tipo})
    assert ew.mesh_check(res2["faces"])["closed"]


# ----------------------------------------------------------------- PAT-004
@pytest.mark.spec("PAT-004")
def test_opciones():
    o = pt.opciones({"eslabones": 9, "holgura": 0.1})
    assert o["eslabones"] == 5 and o["holgura"] == 0.3
    assert pt.opciones({"eslabones": 0, "holgura": 3})["eslabones"] == 2
    with pytest.raises(ValueError):
        pt.opciones({"tipo": "tentaculos"})
    with pytest.raises(ValueError):
        pt.opciones({"pie": "aleta"})
    res = maceta()
    _, cad, info = pt.armar(res, {"tipo": "patas_brazos", "pie": "pato", "eslabones": 4})
    assert [c["nombre"] for c in cad] == ["PATA_I", "PATA_D", "BRAZO_I", "BRAZO_D"]
    assert [len(c["eslabones"]) for c in cad] == [4, 4, 2, 2]
    inf = ew.info()["patitas"]
    assert [t["id"] for t in inf["tipos"]] == ["patas", "patas_brazos", "brazos"]
    assert [p["id"] for p in inf["pies"]] == ["zapatilla", "bota", "pato"]
    assert inf["defecto"]["pie"] == "zapatilla"
    # la web recibe cada eslabón aparte con su eje
    r = ew.build({"mode": "pot", "size": "S", "patitas": {"tipo": "patas", "eslabones": 2}})
    nombres = [p["name"] for p in r["parts"]]
    assert nombres == ["MACETA", "PATA_I_1", "PATA_I_2", "PATA_D_1", "PATA_D_2"]
    e = r["summary"]["patitas"]["cadenas"][0]["eslabones"][0]
    assert len(e["eje"]) == 3 and abs(math.hypot(*e["dir"][:2]) - 1) < 1e-3
