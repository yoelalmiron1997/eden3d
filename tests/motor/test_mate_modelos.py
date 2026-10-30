# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Los siete modelos nuevos (MAT-016): la forma que se ve en las fotos de referencia."""
import math

import pytest

import mate_core as mc

TAU = 2.0 * math.pi


def filas(tid, M=240):
    p = mc.parametros_tipo(tid)
    return mc.filas_exteriores(p, 1.0, M, paso=1.0)[0], p


def fila_en(fs, z):
    return min(fs, key=lambda f: abs(f[0] - z))[1]


def maximos(rs, tol=1e-6):
    """Picos (o mesetas) locales de un anillo cerrado."""
    n = len(rs)
    sube = [rs[(i + 1) % n] - rs[i] for i in range(n)]
    signos = [1 if d > tol else -1 if d < -tol else 0 for d in sube]
    sg = [x for x in signos if x != 0]
    return sum(1 for a, b in zip(sg, sg[1:] + sg[:1]) if a > 0 and b < 0)


@pytest.mark.spec("MAT-016")
def test_estan_los_siete_modelos():
    ids = [t["id"] for t in mc.TIPOS]
    for tid in ("triangular", "patitas", "lowpoly_torcido", "vaso_conico", "lowpoly_irregular",
                "labio_grueso", "rombos"):
        assert tid in ids
    assert len(ids) == len(set(ids)) == 17


@pytest.mark.spec("MAT-016")
def test_triangular_tiene_tres_lobulos():
    fs, p = filas("triangular")
    rs = fila_en(fs, p["H"] * 0.5)
    assert maximos(rs) == 3
    assert max(rs) / min(rs) > 1.10


@pytest.mark.spec("MAT-016")
def test_patitas_cuatro_patas_y_redondo_arriba():
    fs, p = filas("patitas", M=240)
    base = fila_en(fs, 0.5)
    assert maximos(base) == 4
    assert max(base) - min(base) > 4.0
    # al frente (θ = -90°) queda el hueco entre dos patas
    k_frente = 3 * 240 // 4
    assert base[k_frente] == pytest.approx(min(base), abs=0.05)
    arriba = fila_en(fs, p["H"] * 0.24 + 2.0)
    assert max(arriba) - min(arriba) < 0.05


@pytest.mark.spec("MAT-016")
@pytest.mark.parametrize("tid", ["lowpoly_torcido", "lowpoly_irregular"])
def test_low_poly_caras_planas(tid):
    fs, p = filas(tid, M=720)
    n = p["extras"]["poliedro"]["n"]
    # cada corte es un polígono: entre esquinas, los puntos están alineados
    z = p["H"] * 0.3
    rs = fila_en(fs, z)
    pts = [(r * math.cos(TAU * k / 720), r * math.sin(TAU * k / 720)) for k, r in enumerate(rs)]
    giros = []
    for i in range(720):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % 720]
        giros.append(abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)))
    esquinas = sum(1 for g in giros if g > 1e-3)
    assert esquinas <= 2 * 2 * n           # ≤ 2n esquinas (cada una toca 1–2 muestras)
    assert sum(1 for g in giros if g <= 1e-6) > 600   # el resto: lados rectos


@pytest.mark.spec("MAT-016")
def test_torcido_gira_con_la_altura():
    fs, p = filas("lowpoly_torcido", M=720)
    def ang_max(z):
        rs = fila_en(fs, z)
        return TAU * rs.index(max(rs)) / 720
    zs = [lv for _, lv in mc._control(p, 1.0)]
    # el vértice más saliente se corre con la altura (no vuelve atrás como el facetado)
    a0, a1 = ang_max(zs[1]), ang_max(zs[3])
    assert abs((a1 - a0 + math.pi) % TAU - math.pi) > math.radians(5)


@pytest.mark.spec("MAT-016")
def test_irregular_siempre_igual():
    a, _ = filas("lowpoly_irregular", M=96)
    b, _ = filas("lowpoly_irregular", M=96)
    assert a == b
    rs = fila_en(a, 40.0)
    assert max(rs) / min(rs) > 1.08


@pytest.mark.spec("MAT-016")
def test_vaso_conico_se_abre_y_anillo_en_la_base():
    fs, p = filas("vaso_conico", M=48)
    radios = [(z, rs[0]) for z, rs in fs]
    medio = [r for z, r in radios if 0.1 * p["H"] < z < p["H"] - 1]
    assert all(b >= a - 1e-9 for a, b in zip(medio, medio[1:]))
    assert radios[0][1] > medio[0] + 1.5           # el anillo de la base sobresale


@pytest.mark.spec("MAT-016")
def test_labio_grueso():
    fs, p = filas("labio_grueso", M=48)
    r = lambda f: fila_en(fs, f * p["H"])[0]
    assert r(0.90) > r(0.80) + 2.5


@pytest.mark.spec("MAT-016")
def test_cubos_3d_relieve_periodico():
    fs, p = filas("rombos", M=200)
    liso = dict(p, extras={})
    base = mc.filas_exteriores(liso, 1.0, 200, paso=1.0)[0]
    alto = p["extras"]["rombos"]["alto"]
    rel = [r - r0 for (z, rs), (_, r0s) in zip(fs, base) if 10 < z < p["H"] - 10
           for r, r0 in zip(rs, r0s)]
    assert max(rel) == pytest.approx(alto, abs=0.15)      # la punta del cubo
    assert min(rel) == pytest.approx(0.0, abs=0.15)       # la esquina del fondo
    rs = fila_en(fs, p["H"] * 0.5)
    for k in range(200):
        assert rs[k] == pytest.approx(rs[(k + 20) % 200], abs=1e-6)
    lisa = fila_en(fs, 0.0)
    assert max(lisa) - min(lisa) < 1e-6           # la base queda lisa para apoyar
