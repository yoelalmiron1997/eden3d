# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Escena para el render de producto (sólo para la foto, no se exporta)
=============================================================================
Arma, a partir de la maceta ya ubicada, lo que va adentro en la foto:
  * una suculenta tipo echeveria (roseta de hojas carnosas en filotaxis),
  * tierra y piedritas decorativas (blancas y bolitas de arcilla) sobre la tierra.
Python puro: devuelve listas (V, F) por material. Determinista (semilla fija).

    build(pot_vertices, seed=3) -> [(material, V, F), ...]
      material: "planta" | "piedra" | "arcilla" | "tierra"
"""
import math
import random

TAU = 2.0 * math.pi
GOLD = math.radians(137.508)


# ------------------------------------------------------------------ medidas
def opening(V):
    """(z del borde, radio interior a la altura de la tierra, z de la tierra)."""
    z_top = max(v[2] for v in V)
    z_bot = min(v[2] for v in V)
    H = z_top - z_bot
    z_s = z_top - max(6.0, 0.085 * H)          # tierra unos mm bajo el borde
    band = [math.hypot(v[0], v[1]) for v in V if abs(v[2] - z_s) < max(0.8, 0.012 * H)]
    if not band:
        band = [math.hypot(v[0], v[1]) for v in V]
    # la pared interior es la de menor radio en esa franja (la exterior tiene relieve)
    band.sort()
    r_in = band[min(len(band) - 1, max(0, len(band) // 50))]
    return z_top, r_in, z_s


# ------------------------------------------------------------------ hoja
def _leaf(L, W, T, a0, a1, cup, nu=14, nv=9):
    """Hoja carnosa en coordenadas locales: crece en +X, se curva hacia +Z.
    Devuelve (V, F) cerrada (arriba + abajo unidas en los bordes)."""
    # línea media
    pts, ang = [(0.0, 0.0)], []
    x = z = 0.0
    for i in range(1, nu + 1):
        t = i / float(nu)
        a = a0 + (a1 - a0) * t ** 1.4
        x += math.cos(a) * L / nu
        z += math.sin(a) * L / nu
        pts.append((x, z))
    for i in range(nu + 1):
        t = i / float(nu)
        a = a0 + (a1 - a0) * t ** 1.4
        ang.append(a)

    def width(t):                               # cuchara con punta
        w = math.sin(math.pi * min(1.0, 0.18 + 0.82 * t) ** 0.8) * (1 - t ** 8)
        return max(W * max(w, 0.0) * (0.55 + 0.45 * math.sin(math.pi * 0.5 * min(1, t * 1.6))),
                   0.06)

    def thick(t):
        return T * (1.0 - t) ** 0.6 + 0.15

    V, F = [], []
    rows = []
    for i in range(nu + 1):
        t = i / float(nu)
        cx, cz = pts[i]
        a = ang[i]
        nx, nz = -math.sin(a), math.cos(a)      # normal "arriba" de la hoja
        w, th = width(t), thick(t)
        row_top, row_bot = [], []
        for j in range(nv + 1):
            s = -1.0 + 2.0 * j / nv
            e = math.sqrt(max(0.0, 1.0 - s * s))
            y = s * w
            lift = cup * w * s * s                # hoja levemente acucharada
            top = th * 0.5 * e + lift
            bot = -th * 0.5 * e + lift
            row_top.append((cx + nx * top, y, cz + nz * top))
            row_bot.append((cx + nx * bot, y, cz + nz * bot))
        rows.append((row_top, row_bot))
    idx_top, idx_bot = [], []
    for row_top, row_bot in rows:
        it, ib = [], []
        for j in range(nv + 1):
            if j in (0, nv):                    # borde: arriba y abajo comparten vértice
                V.append(row_top[j])
                it.append(len(V) - 1)
                ib.append(len(V) - 1)
            else:
                V.append(row_top[j])
                it.append(len(V) - 1)
                V.append(row_bot[j])
                ib.append(len(V) - 1)
        idx_top.append(it)
        idx_bot.append(ib)
    for i in range(nu):
        for j in range(nv):
            a, b = idx_top[i][j], idx_top[i][j + 1]
            c, d = idx_top[i + 1][j + 1], idx_top[i + 1][j]
            F += [(a, b, c), (a, c, d)]
            a, b = idx_bot[i][j], idx_bot[i][j + 1]
            c, d = idx_bot[i + 1][j + 1], idx_bot[i + 1][j]
            F += [(a, c, b), (a, d, c)]
    # tapa de la base (queda escondida en el centro de la roseta)
    c0 = len(V)
    V.append((0.0, 0.0, 0.0))
    ring = idx_top[0] + idx_bot[0][::-1][1:-1]
    for k in range(len(ring)):
        F.append((c0, ring[(k + 1) % len(ring)], ring[k]))
    return V, F


def _place(V, F, ang, base_r, base_z, scale=1.0):
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for x, y, z in V:
        x, y, z = x * scale, y * scale, z * scale
        out.append(((x + base_r) * ca - y * sa, (x + base_r) * sa + y * ca, z + base_z))
    return out, F


def echeveria(R, z0, n=34, seed=3):
    """Roseta de radio ~R apoyada en z0."""
    rnd = random.Random(seed)
    V, F = [], []
    L_out = R / 0.86
    for k in range(n):
        f = k / float(n - 1)                   # 0 = centro, 1 = afuera
        L = L_out * (0.28 + 0.72 * f ** 0.75)
        W = L * (0.36 + 0.06 * rnd.random())
        T = L * 0.22
        a0 = math.radians(78 - 66 * f ** 0.8 + rnd.uniform(-4, 4))   # adentro: parada
        a1 = a0 + math.radians(18 + 22 * f)                         # punta que sube
        cup = 0.10 + 0.08 * f
        lv, lf = _leaf(L, W, T, a0, min(a1, math.radians(88)), cup)
        ang = k * GOLD + rnd.uniform(-0.05, 0.05)
        pv, pf = _place(lv, lf, ang, R * 0.05 * f, z0 + 2.0 * (1 - f))
        o = len(V)
        V += pv
        F += [(a + o, b + o, c + o) for a, b, c in pf]
    return V, F


# ------------------------------------------------------------------ piedras
def _pebble(cx, cy, cz, a, b, c, rot, rnd, nu=22, nv=12):
    V, F = [], []
    bumps = [(rnd.uniform(0, TAU), rnd.uniform(-1, 1), rnd.uniform(0.04, 0.10)) for _ in range(4)]
    V.append((cx, cy, cz - c))
    for j in range(1, nv):
        ph = math.pi * j / nv - math.pi / 2
        for i in range(nu):
            th = TAU * i / nu
            k = 1.0
            for bt, bz, amp in bumps:
                k += amp * math.cos(th - bt) * math.cos(ph - bz)
            x, y, z = a * math.cos(ph) * math.cos(th) * k, b * math.cos(ph) * math.sin(th) * k, \
                c * math.sin(ph) * k
            cr, sr = math.cos(rot), math.sin(rot)
            V.append((cx + x * cr - y * sr, cy + x * sr + y * cr, cz + z))
    V.append((cx, cy, cz + c))
    top = len(V) - 1
    for i in range(nu):
        F.append((0, 1 + (i + 1) % nu, 1 + i))
    for j in range(nv - 2):
        r0, r1 = 1 + j * nu, 1 + (j + 1) * nu
        for i in range(nu):
            a_, b_ = r0 + i, r0 + (i + 1) % nu
            c_, d_ = r1 + (i + 1) % nu, r1 + i
            F += [(a_, b_, c_), (a_, c_, d_)]
    r0 = 1 + (nv - 2) * nu
    for i in range(nu):
        F.append((top, r0 + i, r0 + (i + 1) % nu))
    return V, F


def pebbles(r_in, z_s, keep_r=0.0, seed=7):
    """Piedritas sobre la tierra (Poisson simple). keep_r: zona libre central (planta)."""
    rnd = random.Random(seed)
    placed = []
    out = {"piedra": ([], []), "arcilla": ([], [])}
    tries = 0
    while tries < 9000:
        tries += 1
        rr = r_in * math.sqrt(rnd.random())
        th = rnd.uniform(0, TAU)
        size = rnd.uniform(2.6, 4.6) * (0.8 if r_in < 30 else 1.0)
        if rr + size * 0.8 > r_in - 0.8 or rr < keep_r:
            continue
        x, y = rr * math.cos(th), rr * math.sin(th)
        if any(math.hypot(x - px, y - py) < (size + ps) * 0.78 for px, py, ps in placed):
            continue
        placed.append((x, y, size))
        kind = "arcilla" if rnd.random() < 0.35 else "piedra"
        a, b, c = size, size * rnd.uniform(0.72, 0.95), size * rnd.uniform(0.55, 0.75)
        pv, pf = _pebble(x, y, z_s + c * 0.55, a, b, c, rnd.uniform(0, TAU), rnd)
        V, F = out[kind]
        o = len(V)
        V += pv
        F += [(p + o, q + o, r + o) for p, q, r in pf]
    return out


def soil(r_in, z_s, n=64):
    V = [(0.0, 0.0, z_s)] + [(r_in * math.cos(TAU * k / n), r_in * math.sin(TAU * k / n), z_s)
                             for k in range(n)]
    V += [(0.0, 0.0, z_s - 3.0)] + [(r_in * math.cos(TAU * k / n), r_in * math.sin(TAU * k / n),
                                     z_s - 3.0) for k in range(n)]
    F = []
    b = n + 1
    for k in range(n):
        k1 = (k + 1) % n
        F.append((0, 1 + k, 1 + k1))
        F.append((b, b + 1 + k1, b + 1 + k))
        F += [(1 + k, b + 1 + k, b + 1 + k1), (1 + k, b + 1 + k1, 1 + k1)]
    return V, F


def build(pot_vertices, seed=3, planta=True):
    """Escena completa para una maceta ya ubicada (z = posición en la foto)."""
    z_top, r_in, z_s = opening(pot_vertices)
    r_in = r_in - 0.6
    out = [("tierra",) + soil(r_in, z_s)]
    R = r_in * 0.92
    keep = R * 0.42 if planta else 0.0
    pb = pebbles(r_in, z_s, keep_r=keep, seed=seed + 4)
    for k in ("piedra", "arcilla"):
        if pb[k][0]:
            out.append((k,) + pb[k])
    if planta:
        out.append(("planta",) + echeveria(R, z_s + 1.0, seed=seed))
    return out


def layer_uv(V, layer_h=0.2, lines_per_tile=16):
    """Coordenadas de textura para las capas de impresión: v avanza 1 cada
    `lines_per_tile` capas; u = ángulo (no importa: las líneas son horizontales)."""
    k = 1.0 / (layer_h * lines_per_tile)
    return [(math.atan2(y, x) / TAU + 0.5, z * k) for x, y, z in V]
