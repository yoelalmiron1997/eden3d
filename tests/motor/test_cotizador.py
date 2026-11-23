# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Cotizador: qué se mide (COT-001) y qué tan cerca queda del laminador (COT-002)."""
import json
import os
import shutil
import subprocess
from collections import defaultdict

import pytest

import cotizador

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF = json.load(open(os.path.join(os.path.dirname(__file__), "datos", "cotizador_laminador.json"), encoding="utf-8"))


def cubo(l=10.0):
    V = [(x, y, z) for x in (0, l) for y in (0, l) for z in (0, l)]
    F = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4),
         (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2), (1, 3, 7), (1, 7, 5)]
    return V, F


@pytest.mark.spec("COT-001")
def test_medir_un_cubo():
    vol, area, arriba, abajo = cotizador.medir(*cubo())
    assert round(vol, 6) == 1000 and round(area, 6) == 600
    assert round(arriba, 6) == 100 and round(abajo, 6) == 100
    V, F = cubo()
    vol2, _, arriba2, abajo2 = cotizador.medir(V, [(a, c, b) for a, b, c in F])   # caras al revés
    assert round(vol2, 6) == 1000 and round(arriba2, 6) == 100 and round(abajo2, 6) == 100


CASOS = [("eden_web", {}), ("chapita_web", {"colores": "ams", "nombre": "Roma"}), ("mate_web", {}),
         ("topper_web", {}), ("trofeo_web", {"colores": "dos"}), ("banda_web", {}),
         ("sopa_web", {"palabras": ["SOL", "LUNA", "MAR"]})]


@pytest.mark.spec("COT-001")
@pytest.mark.parametrize("mod,opts", CASOS, ids=[c[0] for c in CASOS])
def test_cotizar_mide_las_piezas_del_3mf(mod, opts):
    m = __import__(mod)
    r = m.cotizar(opts)
    assert r["piezas"] and r["sku"]
    for p in r["piezas"]:
        assert p["volumen_mm3"] > 0 and p["area_mm2"] >= p["arriba_mm2"] + p["abajo_mm2"] and p["cantidad"] >= 1
    nombres = " ".join(p["nombre"] for p in r["piezas"]).lower()
    assert "agua" not in nombres and "inserto" not in nombres and "hilo" not in nombres
    normal = m.cotizar(dict(opts, cotizar_calidad="normal"))
    va = sum(p["volumen_mm3"] * p["cantidad"] for p in r["piezas"])
    vb = sum(p["volumen_mm3"] * p["cantidad"] for p in normal["piezas"])
    assert abs(va / vb - 1) < 0.06


@pytest.mark.spec("COT-001")
def test_la_banda_cuenta_todas_las_cuentas():
    import banda_core as bc
    import banda_web
    r = banda_web.cotizar({})
    rep = bc.construir(banda_web._normal({}))["reporte"]
    cuantas = defaultdict(int)
    for p in r["piezas"]:
        if "letra" not in p["nombre"]:
            cuantas["disco" if p["nombre"].startswith("Disco") else p["grupo"].lower()] += p["cantidad"]
    assert cuantas["disco"] == rep["total_discos"]
    assert cuantas["corazon"] == rep["corazones"] and cuantas["pelotita"] == rep["pelotitas"]
    assert r["colores"] == 2


def _gramos_js(casos):
    """La fórmula de web/cotizador.js, corrida en Node."""
    cod = ('import("%s").then(m => { const c = JSON.parse(process.argv[1]);'
           ' console.log(JSON.stringify(c.map(x => m.gramosPieza(x, { relleno: x.relleno, perimetros: x.perimetros, densidad: 1.24 })))); })'
           % ("file://" + os.path.join(REPO, "web", "cotizador.js")))
    out = subprocess.run(["node", "--input-type=module", "-e", cod, json.dumps(casos)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.spec("COT-002")
@pytest.mark.skipif(not shutil.which("node"), reason="hace falta Node para correr la fórmula de la web")
def test_gramos_cerca_del_laminador():
    casos = REF["casos"]
    est = _gramos_js(casos)
    errores = [e / c["gramos_laminador"] - 1 for e, c in zip(est, casos)]
    assert sum(abs(x) for x in errores) / len(errores) < 0.08
    totales = defaultdict(lambda: [0.0, 0.0])
    for e, c in zip(est, casos):
        t = totales[(c["producto"], c["relleno"], c["perimetros"])]
        t[0] += c["gramos_laminador"]
        t[1] += e
    for k, (lam, nuestro) in totales.items():
        assert abs(nuestro / lam - 1) < 0.15, k
    for e, c in zip(est, casos):
        if c["relleno"] == 100:
            assert abs(e / (c["volumen_mm3"] / 1000 * 1.24) - 1) < 0.03
