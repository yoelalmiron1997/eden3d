# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Marca grabada ("Eden3D") para la cara de apoyo
=======================================================
Fuente de trazos propia (sin dependencias, corre igual en Rhino 8 y en Python):
cada letra es un conjunto de polilíneas; el texto se "engorda" con un campo de
distancias y se contornea con marching squares. Resultado: contornos cerrados
(exteriores CCW + contraformas CW) listos para grabar con earcut.

    outlines(text, cap_h, mirror=True) -> [(exterior, [contraformas]), ...]
    place(text, r_free, holes, ...)    -> ubicación que no pisa los drenajes

Las letras se espejan en X para que se lean bien mirando la base desde abajo.
"""
import math

TAU = 2.0 * math.pi
_CACHE = {}


def _arc(cx, cy, rx, ry, a0, a1, steps=14):
    """Arco de elipse de a0 a a1 (grados, cualquier sentido)."""
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / float(steps))
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


# Altura de mayúscula = 10 unidades; altura x = 7; descendentes hasta -3 y acentos
# hasta 12,6. (ancho, [polilíneas])
def _circ(cx, cy, rx, ry, steps=24):
    return _arc(cx, cy, rx, ry, 0, 360, steps)


def _dot(x, y):
    return [(x, y), (x, y + 0.4)]


GLYPHS = {
    # --------------------------------------------------------------- mayúsculas
    "A": (6.0, [[(0, 0), (3, 10), (6, 0)], [(1.1, 3.5), (4.9, 3.5)]]),
    "B": (6.4, [[(0, 0), (0, 10), (3.4, 10)] + _arc(3.4, 7.55, 2.45, 2.45, 90, -90, 12) + [(0, 5.1)],
                [(3.4, 5.1), (3.8, 5.1)] + _arc(3.8, 2.55, 2.55, 2.55, 90, -90, 12) + [(0, 0)]]),
    "C": (6.2, [_arc(3.3, 5, 3.3, 5, 45, 315, 22)]),
    "D": (6.6, [[(0, 0), (0, 10), (2.2, 10)] + _arc(2.2, 5, 4.4, 5, 90, -90, 18) + [(0, 0)]]),
    "E": (6.0, [[(6, 10), (0, 10), (0, 0), (6, 0)], [(0, 5), (4.8, 5)]]),
    "F": (5.6, [[(5.6, 10), (0, 10), (0, 0)], [(0, 5), (4.5, 5)]]),
    "G": (6.6, [_arc(3.3, 5, 3.3, 5, 40, 350, 22) + [(6.55, 4.4), (3.8, 4.4)]]),
    "H": (6.0, [[(0, 0), (0, 10)], [(6, 0), (6, 10)], [(0, 5), (6, 5)]]),
    "I": (2.0, [[(1, 0), (1, 10)]]),
    "J": (5.4, [[(5, 10), (5, 2.8)] + _arc(2.5, 2.8, 2.5, 2.8, 0, -180, 12)]),
    "K": (6.0, [[(0, 0), (0, 10)], [(6, 10), (0, 3.6)], [(2.1, 5.8), (6, 0)]]),
    "L": (5.4, [[(0, 10), (0, 0), (5.4, 0)]]),
    "M": (7.4, [[(0, 0), (0, 10), (3.7, 2.6), (7.4, 10), (7.4, 0)]]),
    "N": (6.2, [[(0, 0), (0, 10), (6.2, 0), (6.2, 10)]]),
    "O": (6.8, [_circ(3.4, 5, 3.4, 5, 28)]),
    "P": (6.0, [[(0, 0), (0, 10), (3.4, 10)] + _arc(3.4, 7.4, 2.6, 2.6, 90, -90, 12) + [(0, 4.8)]]),
    "Q": (6.8, [_circ(3.4, 5, 3.4, 5, 28), [(4.2, 2.4), (6.9, -0.6)]]),
    "R": (6.0, [[(0, 0), (0, 10), (3.4, 10)] + _arc(3.4, 7.4, 2.6, 2.6, 90, -90, 12) + [(0, 4.8)],
                [(3.0, 4.8), (6.0, 0)]]),
    "S": (6.0, [_arc(3, 7.5, 2.8, 2.5, 20, 270, 14) + _arc(3, 2.5, 3, 2.5, 90, -170, 14)]),
    "T": (6.0, [[(0, 10), (6, 10)], [(3, 10), (3, 0)]]),
    "U": (6.0, [[(0, 10), (0, 3)] + _arc(3, 3, 3, 3, 180, 360, 14) + [(6, 10)]]),
    "V": (6.4, [[(0, 10), (3.2, 0), (6.4, 10)]]),
    "W": (8.4, [[(0, 10), (2.1, 0), (4.2, 7.2), (6.3, 0), (8.4, 10)]]),
    "X": (6.0, [[(0, 10), (6, 0)], [(0, 0), (6, 10)]]),
    "Y": (6.0, [[(0, 10), (3, 5), (6, 10)], [(3, 5), (3, 0)]]),
    "Z": (6.0, [[(0, 10), (6, 10), (0, 0), (6, 0)]]),
    # --------------------------------------------------------------- minúsculas
    "a": (6.0, [_circ(3, 3.5, 3, 3.5, 22), [(6, 7), (6, 0)]]),
    "b": (6.0, [[(0, 10), (0, 0)], _circ(3, 3.5, 3, 3.5, 22)]),
    "c": (6.0, [_arc(3.2, 3.5, 3.2, 3.5, 40, 320, 18)]),
    "d": (6.0, [_circ(3, 3.5, 3, 3.5, 24), [(6, 10), (6, 0)]]),
    "e": (6.0, [[(0.1, 3.5), (6, 3.5)] + _arc(3, 3.5, 3, 3.5, 0, 315, 22)]),
    "f": (4.4, [[(1.8, 0), (1.8, 8)] + _arc(3.6, 8, 1.8, 2, 180, 40, 8), [(0, 7), (4, 7)]]),
    "g": (6.0, [_circ(3, 3.5, 3, 3.5, 22), [(6, 7), (6, -0.5)] + _arc(3, -0.5, 3, 2.5, 0, -160, 10)]),
    "h": (6.0, [[(0, 10), (0, 0)], [(0, 4.2)] + _arc(3, 4.2, 3, 2.8, 180, 0, 12) + [(6, 0)]]),
    "i": (2.0, [[(1, 0), (1, 7)], _dot(1, 9.2)]),
    "j": (3.4, [[(2.6, 7), (2.6, -1)] + _arc(0.9, -1, 1.7, 2, 0, -150, 8), _dot(2.6, 9.2)]),
    "k": (5.4, [[(0, 10), (0, 0)], [(5.1, 7), (0, 2.6)], [(1.9, 4.2), (5.4, 0)]]),
    "l": (2.0, [[(1, 10), (1, 0)]]),
    "m": (9.6, [[(0, 0), (0, 7)], [(0, 4.5)] + _arc(2.4, 4.5, 2.4, 2.5, 180, 0, 10) + [(4.8, 0)],
                [(4.8, 4.5)] + _arc(7.2, 4.5, 2.4, 2.5, 180, 0, 10) + [(9.6, 0)]]),
    "n": (6.0, [[(0, 0), (0, 7)], [(0, 4.2)] + _arc(3, 4.2, 3, 2.8, 180, 0, 12) + [(6, 0)]]),
    "o": (6.0, [_circ(3, 3.5, 3, 3.5, 24)]),
    "p": (6.0, [[(0, 7), (0, -3)], _circ(3, 3.5, 3, 3.5, 22)]),
    "q": (6.0, [_circ(3, 3.5, 3, 3.5, 22), [(6, 7), (6, -3)]]),
    "r": (4.6, [[(0, 0), (0, 7)], [(0, 4)] + _arc(3, 4, 3, 3, 180, 60, 8)]),
    "s": (5.2, [_arc(2.6, 5.3, 2.4, 1.7, 10, 270, 10) + _arc(2.6, 1.7, 2.6, 1.7, 90, -190, 10)]),
    "t": (4.4, [[(1.8, 9), (1.8, 1.5)] + _arc(3.5, 1.5, 1.7, 1.5, 180, 300, 6), [(0, 7), (4, 7)]]),
    "u": (6.0, [[(0, 7), (0, 3)] + _arc(3, 3, 3, 3, 180, 360, 12) + [(6, 7)], [(6, 7), (6, 0)]]),
    "v": (6.0, [[(0, 7), (3, 0), (6, 7)]]),
    "w": (8.4, [[(0, 7), (2.1, 0), (4.2, 5), (6.3, 0), (8.4, 7)]]),
    "x": (5.6, [[(0, 7), (5.6, 0)], [(0, 0), (5.6, 7)]]),
    "y": (6.0, [[(0, 7), (3.1, 0)], [(6, 7), (2, -3)]]),
    "z": (5.6, [[(0, 7), (5.6, 7), (0, 0), (5.6, 0)]]),
    # --------------------------------------------------------------- números
    "0": (6.0, [_circ(3, 5, 3, 5, 26)]),
    "1": (4.0, [[(0.5, 8), (2.5, 10), (2.5, 0)]]),
    "2": (6.0, [_arc(3, 7, 3, 3, 160, -30, 12) + [(0, 0), (6, 0)]]),
    "3": (6.0, [_arc(3, 7.6, 2.7, 2.4, 160, -90, 14),
                _arc(3, 2.8, 3.0, 2.8, 90, -160, 16)]),
    "4": (6.0, [[(4.5, 0), (4.5, 10), (0, 3), (6, 3)]]),
    "5": (6.0, [[(5.6, 10), (0.6, 10), (0.3, 5.7)] + _arc(3, 3.2, 3, 3.2, 125, -150, 14)]),
    "6": (6.0, [_arc(3.4, 5.2, 3.4, 4.8, 75, 180, 8) + [(0, 3)], _circ(3, 3, 3, 3, 20)]),
    "7": (6.0, [[(0, 10), (6, 10), (2, 0)]]),
    "8": (6.0, [_circ(3, 7.6, 2.5, 2.4, 18), _circ(3, 2.7, 3, 2.7, 20)]),
    "9": (6.0, [_circ(3, 7, 3, 3, 20), [(6, 7)] + _arc(2.6, 5, 3.4, 5, 0, -105, 8)]),
    # --------------------------------------------------------------- signos
    " ": (3.0, []),
    "-": (4.0, [[(0.5, 5), (3.5, 5)]]),
    "_": (6.0, [[(0, -1.5), (6, -1.5)]]),
    ".": (1.4, [_dot(0.7, 0)]),
    ",": (1.6, [[(1.0, 0.6), (0.2, -1.8)]]),
    ":": (1.4, [_dot(0.7, 0), _dot(0.7, 5.6)]),
    "!": (1.6, [[(0.8, 10), (0.8, 3.2)], _dot(0.8, 0)]),
    "?": (5.6, [_arc(2.8, 7.5, 2.6, 2.5, 160, -60, 10) + [(2.8, 3.2)], _dot(2.8, 0)]),
    "'": (1.4, [[(0.7, 10), (0.7, 7.4)]]),
    "/": (4.6, [[(0, 0), (4.6, 10)]]),
    "+": (5.0, [[(0, 4.5), (5, 4.5)], [(2.5, 2), (2.5, 7)]]),
    "#": (6.4, [[(1.8, 0), (2.8, 10)], [(4.2, 0), (5.2, 10)], [(0.4, 3.3), (6.4, 3.3)], [(0, 6.7), (6, 6.7)]]),
    "(": (3.4, [_arc(4.2, 5, 3.6, 6.2, 125, 235, 10)]),
    ")": (3.4, [_arc(-0.8, 5, 3.6, 6.2, 55, -55, 10)]),
    "&": (7.0, [[(7, 0)] + [(1.6, 6.4)] + _arc(2.9, 8.1, 1.7, 1.9, 220, -40, 10) + [(1.2, 4.1)]
                + _arc(3.0, 2.4, 2.8, 2.4, 140, 330, 12) + [(6.4, 4.2)]]),
    "@": (9.0, [_circ(4.6, 4.2, 1.9, 2.2, 14), [(6.5, 6.4), (6.5, 2.6)] + _arc(7.6, 2.6, 1.1, 1.1, 180, 360, 6)
                + _arc(4.6, 4.2, 4.1, 4.6, 5, 330, 22)]),
}

# acentos y diéresis (agudo, tilde, diéresis) sobre letras ya dibujadas
for _base, _acc in (("a", "á"), ("e", "é"), ("o", "ó"), ("u", "ú")):
    _w, _p = GLYPHS[_base]
    GLYPHS[_acc] = (_w, _p + [[(_w / 2 - 0.6, 8.9), (_w / 2 + 1.0, 10.9)]])
GLYPHS["í"] = (2.4, [[(1, 0), (1, 7)], [(0.6, 8.9), (2.2, 10.9)]])
for _base, _acc in (("A", "Á"), ("E", "É"), ("O", "Ó"), ("U", "Ú")):
    _w, _p = GLYPHS[_base]
    GLYPHS[_acc] = (_w, _p + [[(_w / 2 - 0.6, 11.3), (_w / 2 + 1.0, 13.0)]])
GLYPHS["Í"] = (2.6, [[(1, 0), (1, 10)], [(0.6, 11.3), (2.2, 13.0)]])
GLYPHS["ñ"] = (6.0, GLYPHS["n"][1] + [[(0.6, 8.6), (2.0, 9.6), (4.0, 8.6), (5.4, 9.6)]])
GLYPHS["Ñ"] = (6.2, GLYPHS["N"][1] + [[(0.6, 11.0), (2.1, 12.2), (4.1, 11.0), (5.6, 12.2)]])
GLYPHS["ü"] = (6.0, GLYPHS["u"][1] + [_dot(1.6, 9.0), _dot(4.4, 9.0)])
GLYPHS["Ü"] = (6.0, GLYPHS["U"][1] + [_dot(1.6, 11.4), _dot(4.4, 11.4)])

MAX_LEN = 20


def check(text):
    """Valida un texto de marca: devuelve (texto limpio, error o None)."""
    t = " ".join(str(text or "").split())
    if not t:
        return "", None
    if len(t) > MAX_LEN:
        return t, "La marca puede tener hasta %d caracteres." % MAX_LEN
    bad = sorted({c for c in t if c not in GLYPHS})
    if bad:
        return t, "Estos caracteres no se pueden grabar: %s" % " ".join(bad)
    return t, None


def strokes(text, cap_h, tracking=2.6):
    """Segmentos (x0,y0,x1,y1) en mm, centrados en el origen."""
    k = cap_h / 10.0
    segs, x = [], 0.0
    for ch in text:
        if ch not in GLYPHS:
            raise ValueError("La marca usa un carácter sin dibujo: %r (disponibles: %s)"
                             % (ch, "".join(sorted(GLYPHS))))
        w, polys = GLYPHS[ch]
        for pl in polys:
            for (a, b), (c, d) in zip(pl, pl[1:]):
                segs.append(((x + a) * k, b * k, (x + c) * k, d * k))
        x += w + tracking
    width = (x - tracking) * k
    return [(a - width / 2.0, b - cap_h / 2.0, c - width / 2.0, d - cap_h / 2.0)
            for a, b, c, d in segs], width


def extents(segs, cap_h):
    """(y mínima, y máxima) de los trazos centrados (descendentes y acentos incluidos)."""
    if not segs:
        return -cap_h / 2.0, cap_h / 2.0
    ys = [v for s in segs for v in (s[1], s[3])]
    return min(min(ys), -cap_h / 2.0), max(max(ys), cap_h / 2.0)


def _dist_seg(px, py, s):
    ax, ay, bx, by = s
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    dx, dy = px - ax - t * vx, py - ay - t * vy
    return math.sqrt(dx * dx + dy * dy)


def stroke_distance(px, py, segs):
    return min(_dist_seg(px, py, s) for s in segs) if segs else 1e9


def _area(loop):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _inside(pt, loop):
    x, y = pt
    c = False
    n = len(loop)
    for i in range(n):
        x1, y1 = loop[i]
        x2, y2 = loop[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    ax, ay = pts[0]
    bx, by = pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1e-12
    best, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / L
        if d > best:
            best, idx = d, i
    if best <= eps:
        return [pts[0], pts[-1]]
    return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)


def _simplify_loop(loop, eps):
    if len(loop) < 8:
        return loop
    h = len(loop) // 2
    a = _rdp(loop[:h + 1], eps)
    b = _rdp(loop[h:] + loop[:1], eps)
    out = a[:-1] + b[:-1]
    return out if len(out) >= 3 else loop


def outlines(text, cap_h, stroke_ratio=0.17, res=None, mirror=True):
    """Contornos del texto engordado. Devuelve [(exterior, [contraformas])],
    exterior en sentido antihorario y contraformas en horario (ya espejado)."""
    key = (text, round(cap_h, 3), stroke_ratio, mirror)
    if key in _CACHE:
        return _CACHE[key]
    segs, width = strokes(text, cap_h)
    hw = cap_h * stroke_ratio / 2.0
    res = res or max(0.06, min(0.14, hw / 4.0))
    pad = hw + 3 * res
    ylo, yhi = extents(segs, cap_h)
    x0, y0 = -width / 2.0 - pad, ylo - pad
    nx = int(math.ceil((width + 2 * pad) / res)) + 1
    ny = int(math.ceil((yhi - ylo + 2 * pad) / res)) + 1
    # campo f = hw - distancia (positivo dentro); por columnas para acotar
    f = [[0.0] * ny for _ in range(nx)]
    for i in range(nx):
        px = x0 + i * res
        near = [s for s in segs if min(s[0], s[2]) - hw - res <= px <= max(s[0], s[2]) + hw + res]
        for j in range(ny):
            py = y0 + j * res
            f[i][j] = hw - (min(_dist_seg(px, py, s) for s in near) if near else 1e9)

    def P(i, j):
        return (x0 + i * res, y0 + j * res)

    def edge_pt(key):
        kind, i, j = key
        if kind == "h":                         # (i,j)-(i+1,j)
            fa, fb = f[i][j], f[i + 1][j]
            t = fa / (fa - fb)
            return (x0 + (i + t) * res, y0 + j * res)
        fa, fb = f[i][j], f[i][j + 1]
        t = fa / (fa - fb)
        return (x0 + i * res, y0 + (j + t) * res)

    adj = {}

    def link(a, b):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = f[i][j] > 0, f[i + 1][j] > 0, f[i + 1][j + 1] > 0, f[i][j + 1] > 0
            idx = (a << 0) | (b << 1) | (c << 2) | (d << 3)
            if idx in (0, 15):
                continue
            E_b, E_r, E_t, E_l = ("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j)
            cross = {1: [(E_l, E_b)], 2: [(E_b, E_r)], 3: [(E_l, E_r)], 4: [(E_r, E_t)],
                     6: [(E_b, E_t)], 7: [(E_l, E_t)], 8: [(E_t, E_l)], 9: [(E_t, E_b)],
                     11: [(E_t, E_r)], 12: [(E_r, E_l)], 13: [(E_r, E_b)], 14: [(E_b, E_l)]}
            if idx in (5, 10):
                center = (f[i][j] + f[i + 1][j] + f[i + 1][j + 1] + f[i][j + 1]) / 4.0 > 0
                if (idx == 5) == center:
                    pairs = [(E_l, E_t), (E_b, E_r)]
                else:
                    pairs = [(E_l, E_b), (E_t, E_r)]
            else:
                pairs = cross[idx]
            for e1, e2 in pairs:
                link(e1, e2)

    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [], None, start
        while True:
            seen.add(cur)
            loop.append(edge_pt(cur))
            nb = adj[cur]
            nxt = nb[0] if nb[0] != prev else (nb[1] if len(nb) > 1 else nb[0])
            prev, cur = cur, nxt
            if cur == start or cur in seen:
                break
        if len(loop) >= 3:
            loop = _simplify_loop(loop, res * 0.25)
            if mirror:
                loop = [(-x, y) for x, y in loop]
            loops.append(loop)
    # anidamiento: profundidad par = exterior (CCW), impar = contraforma (CW)
    info = []
    for L in loops:
        depth = sum(1 for M in loops if M is not L and _inside(L[0], M))
        info.append(depth)
    result = []
    for L, dpt in zip(loops, info):
        if dpt % 2 == 0:
            ext = L if _area(L) > 0 else L[::-1]
            holes = []
            for M, dm in zip(loops, info):
                if dm == dpt + 1 and _inside(M[0], L):
                    holes.append(M if _area(M) < 0 else M[::-1])
            result.append((ext, holes))
    _CACHE[key] = (result, segs, hw, width)
    return _CACHE[key]


def _transform(loops_pack, cx, cy, ang):
    ca, sa = math.cos(ang), math.sin(ang)

    def T(p):
        x, y = p
        return (cx + x * ca - y * sa, cy + x * sa + y * ca)
    return [([T(p) for p in ext], [[T(p) for p in h] for h in holes]) for ext, holes in loops_pack]


def _seg_dist_pts(p, a, b):
    return _dist_seg(p[0], p[1], (a[0], a[1], b[0], b[1]))


def _hole_pts(holes, step=0.6):
    """Vértices densificados de todos los agujeros + un punto interior de cada uno."""
    pts = []
    for h in holes:
        pts.extend(_densify(h, step))
    return pts


def _seg_index(segs, cell=2.0):
    grid = {}
    for s in segs:
        i0, i1 = int(math.floor(min(s[0], s[2]) / cell)), int(math.floor(max(s[0], s[2]) / cell))
        for i in range(i0 - 1, i1 + 2):
            grid.setdefault(i, []).append(s)
    return grid, cell


def _near_strokes(lx, ly, idx, lim):
    grid, cell = idx
    cand = grid.get(int(math.floor(lx / cell)), ())
    for s in cand:
        if _dist_seg(lx, ly, s) < lim:
            return True
    return False


def place(text, r_free, holes, cap_h=6.0, min_cap=3.5, gap=1.2):
    """Busca dónde grabar el texto dentro del disco r_free sin acercarse a
    menos de `gap` mm de ningún agujero. Prueba centro, desplazamientos y
    giros (texto recto); si no entra, lo curva sobre un arco cerca del borde.
    Achica la letra hasta min_cap. Devuelve (contornos, cap_h, posición) o None."""
    hp = _hole_pts(holes)
    inner = [(sum(p[0] for p in h) / len(h), sum(p[1] for p in h) / len(h)) for h in holes]
    size = cap_h
    while size >= min_cap - 1e-9:
        pack, segs, hw, width = outlines(text, size, mirror=False)
        idx = _seg_index(segs)
        half_w = width / 2.0 + hw
        ylo, yhi = extents(segs, size)
        half_h = max(-ylo, yhi) + hw              # incluye descendentes y acentos
        lim = hw + gap
        for ang_deg in (0, 90, 30, 150, 60, 120):
            ang = math.radians(ang_deg)
            ca, sa = math.cos(ang), math.sin(ang)
            for k in range(0, 60):
                off = 0.5 * ((k + 1) // 2) * (1 if k % 2 else -1)
                cx, cy = -off * sa, off * ca
                if any(math.hypot(cx + sx * half_w * ca - sy * half_h * sa,
                                  cy + sx * half_w * sa + sy * half_h * ca) > r_free
                       for sx in (-1, 1) for sy in (-1, 1)):
                    continue

                def local(q):
                    x, y = q[0] - cx, q[1] - cy
                    return (-(x * ca + y * sa), -x * sa + y * ca)     # (espejado)
                ok = True
                for q in hp + inner:
                    lx, ly = local(q)
                    if abs(lx) > half_w + gap or abs(ly) > half_h + gap:
                        continue
                    if _near_strokes(lx, ly, idx, lim):
                        ok = False
                        break
                if ok:                      # el texto tampoco puede quedar DENTRO de un agujero
                    for s_ in segs[::5]:
                        lx, ly = s_[0], s_[1]
                        wx = cx - lx * ca - ly * sa
                        wy = cy - lx * sa + ly * ca
                        if any(_inside((wx, wy), h) for h in holes):
                            ok = False
                            break
                if ok:
                    cand = _transform(outlines(text, size)[0], cx, cy, ang)
                    return cand, size, (round(cx, 1), round(cy, 1), ang_deg)
        size -= 0.5
    return place_arc(text, r_free, holes, hp, inner, cap_h, min_cap, gap)


def _clean(loop, tol=2e-3):
    """Quita puntos repetidos o alineados (earcut los descartaría y quedarían
    uniones en T en la malla)."""
    changed = True
    pts = list(loop)
    while changed and len(pts) > 3:
        changed = False
        out = []
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(cross) < tol or (abs(b[0] - a[0]) < 1e-9 and abs(b[1] - a[1]) < 1e-9):
                changed = True
                continue
            out.append(b)
        pts = out
    return pts


def _densify(loop, step):
    out = []
    for a, b in zip(loop, loop[1:] + loop[:1]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(math.ceil(L / step)))
        for i in range(k):
            out.append((a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k))
    return out


def place_arc(text, r_free, holes, hp, inner, cap_h, min_cap, gap):
    """Texto curvado sobre un arco cerca del borde de la base (cuando el centro
    está ocupado por el drenaje, p. ej. la flor de hojas)."""
    size = cap_h
    while size >= min_cap - 1e-9:
        pack, segs, hw, width = outlines(text, size, mirror=False)
        idx = _seg_index(segs)
        ylo, yhi = extents(segs, size)
        half_h = max(-ylo, yhi) + hw              # incluye descendentes y acentos
        R = r_free - half_h - 0.2
        if R - half_h < 5 or width / R > math.pi:
            size -= 0.5
            continue
        lim = hw + gap
        band = [q for q in hp + inner
                if R - half_h - gap <= math.hypot(q[0], q[1]) <= R + half_h + gap]
        polar = [(math.atan2(q[1], -q[0]), math.hypot(q[0], q[1])) for q in band]
        span = (width / 2.0 + hw + gap) / max(R - half_h, 1.0)
        for k in range(72):
            phi = TAU * k / 72.0 - math.pi / 2.0          # empezar abajo (frente)
            ok = True
            for a, rr in polar:
                da = (a - phi + math.pi) % TAU - math.pi
                if abs(da) > span:
                    continue
                if _near_strokes(da * R, R - rr, idx, lim):
                    ok = False
                    break
            if not ok:
                continue

            def M(p):
                # mirando la base desde abajo: texto derecho al frente, con la
                # parte de arriba de las letras hacia el centro
                a = phi + p[0] / R
                rr = R - p[1]
                return (-rr * math.cos(a), rr * math.sin(a))
            fixed = []
            for e, cs in pack:
                e2 = _clean([M(p) for p in _densify(e, 0.5)])
                c2 = [_clean([M(p) for p in _densify(c, 0.5)]) for c in cs]
                e2 = e2 if _area(e2) > 0 else e2[::-1]
                fixed.append((e2, [c if _area(c) < 0 else c[::-1] for c in c2]))
            return fixed, size, (round(R, 1), 0.0, round(math.degrees(phi), 1))
        size -= 0.5
    return None
