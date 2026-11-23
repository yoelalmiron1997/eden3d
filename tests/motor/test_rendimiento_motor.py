# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Optimizaciones del motor que no pueden cambiar el resultado (PER-005) y arranque de
los generadores (PER-004, la parte que se ve en los archivos)."""
import math
import os
import random
import re
import time

import pytest

import eden_font
import topper_core

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(REPO, "web")


def _campo_fuerza_bruta(segs, hw, res, x0, y0, nx, ny):
    return [[hw - min(eden_font._dist_seg(x0 + i * res, y0 + j * res, s) for s in segs) for j in range(ny)]
            for i in range(nx)]


@pytest.mark.spec("PER-005")
@pytest.mark.parametrize("texto", ["Eden3D", "Rocío Ñandú", "TecnoBear 2026", "Il"])
def test_campo_del_texto_igual_al_de_fuerza_bruta(texto):
    cap = 6.0
    segs, width = eden_font.strokes(texto, cap)
    hw = cap * 0.17 / 2.0
    res = max(0.06, min(0.14, hw / 4.0)) * 2          # más grueso: el de fuerza bruta es lento
    pad = hw + 3 * res
    ylo, yhi = eden_font.extents(segs, cap)
    x0, y0 = -width / 2.0 - pad, ylo - pad
    nx = int(math.ceil((width + 2 * pad) / res)) + 1
    ny = int(math.ceil((yhi - ylo + 2 * pad) / res)) + 1
    rapido = eden_font._campo(segs, hw, res, x0, y0, nx, ny)
    lento = _campo_fuerza_bruta(segs, hw, res, x0, y0, nx, ny)
    for i in range(nx):
        for j in range(ny):
            # cerca del trazo (lo que usa el contorno) el valor es exactamente el mismo;
            # lejos alcanza con que diga "afuera"
            if lento[i][j] > -2 * res:
                assert rapido[i][j] == lento[i][j], (i, j)
            else:
                assert rapido[i][j] < 0


@pytest.mark.spec("PER-005")
def test_contorno_espejado_es_el_normal_invertido():
    eden_font._CACHE.clear()
    eden_font._LOOPS.clear()
    normal = eden_font.outlines("Roma", 5.0, mirror=False)[0]
    espejo = eden_font.outlines("Roma", 5.0, mirror=True)[0]
    assert len(eden_font._LOOPS) == 1, "el campo se calcula una sola vez"
    invertir = lambda L: sorted((round(-x, 9), round(y, 9)) for x, y in L)
    assert sorted(sorted((round(x, 9), round(y, 9)) for x, y in ext) for ext, _ in espejo) == \
        sorted(invertir(ext) for ext, _ in normal)


@pytest.mark.spec("PER-005")
def test_pasada_binaria_igual_a_felzenszwalb():
    rnd = random.Random(7)
    INF = 1e20
    for n in (1, 2, 5, 40, 333):
        for _ in range(30):
            es = [rnd.random() < rnd.choice((0.02, 0.2, 0.7)) for _ in range(n)]
            if not any(es):
                assert topper_core._edt1_bin(es, n, INF) == [INF] * n
                continue
            assert topper_core._edt1_bin(es, n, INF) == topper_core._edt1([0.0 if e else INF for e in es], n)


@pytest.mark.spec("PER-005")
def test_la_maceta_por_defecto_arma_rapido():
    import eden_web
    eden_font._CACHE.clear()
    eden_font._LOOPS.clear()
    eden_font._PLACE.clear()
    t = time.perf_counter()
    eden_web.build({})
    assert time.perf_counter() - t < 1.5


@pytest.mark.spec("PER-004")
def test_el_motor_arranca_desde_el_head():
    paginas = {"macetas": "worker.js", "banda": "banda-worker.js", "chapita": "chapita-worker.js",
               "mate": "mate-worker.js", "sopa": "sopa-worker.js", "topper": "topper-worker.js",
               "trofeo": "trofeo-worker.js"}
    for pag, worker in paginas.items():
        html = open(os.path.join(WEB, pag + ".html"), encoding="utf-8").read()
        head = html.split("</head>")[0]
        assert 'new Worker("%s")' % worker in head, pag
        assert head.index("new Worker") < head.index('type="importmap"'), pag
        js = open(os.path.join(WEB, "app.js" if pag == "macetas" else pag + ".js"), encoding="utf-8").read()
        assert 'tomarWorker("%s")' % worker in js and "new Worker(" not in js, pag
    for pag in ("banda", "chapita", "mate", "sopa", "topper", "trofeo"):
        w = open(os.path.join(WEB, pag + "-worker.js"), encoding="utf-8").read()
        assert "motor-carga.js" in w and "cargarMotor(" in w, pag
        assert not re.search(r"for \(const f of manifest", w), "los archivos se bajan todos a la vez"
