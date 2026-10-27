# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Fondo con patrones de drenaje
======================================
OBJETIVO
    Construir el fondo de la maceta (cara superior, cara inferior y paredes
    de cada agujero) con cualquier patrón de agujeros, manteniendo la malla
    cerrada. Python puro: funciona dentro de Rhino/Grasshopper y fuera.

PARÁMETROS (en el dict de la maceta)
    drain_pattern  "none" | "single" | "ring" | "grid"
    drain_shape    "circle" | "slot" | "leaf"
                   slot = ranura radial redondeada
                   leaf = hoja apuntando hacia afuera, opcionalmente partida
                          por una nervadura central (dos medias hojas)
    drain_d        diámetro del agujero (o ancho de la ranura), mm
    drain_count    agujeros del anillo interior (pattern "ring")
    drain_rings    cantidad de anillos concéntricos (1-3)
    drain_center   True = agujero central además del anillo
    drain_center_d diámetro del agujero central (0 = igual a drain_d)
    drain_spacing  paso entre centros (pattern "grid"), mm
    drain_slot_len largo de la ranura o de la hoja, mm (0 = 3 × drain_d)
    drain_leaf_vein ancho de la nervadura central de la hoja, mm (0 = sin)
    drain_leaf_tilt giro de cada hoja respecto del radio, grados (molinete)

CONTENIDO
    earcut()              triangulación de polígono con agujeros (port de
                          mapbox/earcut, ISC), sin dependencias
    hole_layout()         genera los polígonos de los agujeros
    check_layout()        valida margen a la pared y separación entre agujeros
"""
import math

TAU = 2.0 * math.pi


# ---------------------------------------------------------------------------
# PATRONES
# ---------------------------------------------------------------------------
def _seg(d):
    """Segmentos para un círculo de diámetro d (cuerda ~0,6 mm)."""
    return max(16, int(math.ceil(math.pi * d / 0.6)))


def circle(cx, cy, d):
    r, n = d / 2.0, _seg(d)
    # pequeño giro distinto por agujero: evita vértices alineados entre agujeros
    # (earcut generaría triángulos de área cero)
    ph = ((0.371 * cx + 0.733 * cy) % 1.0) * TAU / n
    return [(cx + r * math.cos(TAU * k / n + ph), cy + r * math.sin(TAU * k / n + ph))
            for k in range(n)]


def slot(cx, cy, w, length, ang):
    """Ranura tipo estadio de ancho w y largo total `length`, orientada en `ang`."""
    r = w / 2.0
    half = max(length / 2.0 - r, 0.0)
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    n = max(8, _seg(w) // 2)
    pts = []
    for end, a0 in ((1, -math.pi / 2), (-1, math.pi / 2)):
        ex, ey = cx + end * half * ux, cy + end * half * uy
        for k in range(n + 1):
            a = a0 + math.pi * k / n
            pts.append((ex + r * (math.cos(a) * ux + math.sin(a) * vx),
                        ey + r * (math.cos(a) * uy + math.sin(a) * vy)))
    return pts


def leaf(cx, cy, w, length, ang, vein=0.0):
    """Hoja de ancho máximo w y largo `length`, con la base hacia el centro de
    la maceta y la punta hacia afuera (dirección `ang`). Perfil:
        semiancho(s) ∝ s^0.6 · (1 - s)^1.1,  s = 0 base … 1 punta
    (más ancha cerca de la base, punta afinada). Si vein > 0 devuelve DOS
    medias hojas separadas por una nervadura de ese ancho."""
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    a, b = 0.6, 1.1
    s_max = a / (a + b)
    norm = (s_max ** a) * ((1 - s_max) ** b)
    n = max(24, int(math.ceil(length / 0.5)))

    def half_w(sv):
        return (w / 2.0) * (sv ** a) * ((1 - sv) ** b) / norm

    def to_xy(along, across):
        x0 = cx - ux * length / 2.0
        y0 = cy - uy * length / 2.0
        return (x0 + ux * along + vx * across, y0 + uy * along + vy * across)

    if vein <= 0:
        right = [to_xy(length * k / n, -half_w(k / float(n))) for k in range(0, n + 1)]
        left = [to_xy(length * k / n, half_w(k / float(n))) for k in range(n - 1, 0, -1)]
        return [right + left]
    g = vein / 2.0
    ks = [k for k in range(n + 1) if half_w(k / float(n)) > g + 0.5]
    if len(ks) < 3:
        return []
    halves = []
    for side in (1, -1):
        outer = [to_xy(length * k / n, side * half_w(k / float(n))) for k in ks]
        # borde de la nervadura: recta de 2 puntos (puntos colineales intermedios
        # harían que earcut genere triángulos de área cero)
        inner = [to_xy(length * ks[-1] / n, side * g), to_xy(length * ks[0] / n, side * g)]
        poly = outer + inner
        if side == -1:
            poly.reverse()
        halves.append(poly)
    return halves


def _hole(p, cx, cy):
    """Polígonos de UN agujero (una hoja con nervadura son dos polígonos)."""
    d = float(p.get("drain_d", 8.0))
    shape = p.get("drain_shape", "circle")
    ang = math.atan2(cy, cx) if (cx or cy) else 0.0
    if shape == "slot":
        return [slot(cx, cy, d, float(p.get("drain_slot_len", 3 * d)), ang)]
    if shape == "leaf":
        ang += math.radians(float(p.get("drain_leaf_tilt", 0.0) or 0.0))
        return leaf(cx, cy, d, float(p.get("drain_slot_len", 3 * d)), ang,
                    float(p.get("drain_leaf_vein", 2.0) or 0.0))
    return [circle(cx, cy, d)]


def hole_layout(p, r_avail):
    """Lista de polígonos (agujeros) dentro de un disco útil de radio r_avail.
    Cada agujero se desplaza una fracción de micrón distinta para que nunca
    haya tres vértices exactamente alineados (earcut daría triángulos nulos)."""
    holes = _hole_layout(p, r_avail)
    return [[(x, y + ((j * 0.6180339) % 1.0) * 2e-3) for x, y in h]
            for j, h in enumerate(holes)]


def _hole_layout(p, r_avail):
    pat = p.get("drain_pattern", "ring")
    d = float(p.get("drain_d", 0) or 0)
    if pat == "none" or d <= 0:
        return []
    if pat == "single":
        return [circle(0.0, 0.0, d)]
    ext = d / 2.0
    if p.get("drain_shape", "circle") in ("slot", "leaf"):
        ext = float(p.get("drain_slot_len", 3 * d)) / 2.0
    holes = []
    if pat == "ring":
        rings = max(1, min(3, int(p.get("drain_rings", 1))))
        center = bool(p.get("drain_center", True))
        dc = float(p.get("drain_center_d", 0) or 0) or d     # agujero central (mecha)
        keep = float(p.get("drain_keepout", 0) or 0)          # zona central ocupada (rosca)
        if keep > 0:
            center = False
        if p.get("drain_shape", "circle") in ("slot", "leaf"):
            # piezas radiales: la base de la pieza arranca después del centro
            r_in = (dc / 2.0 + 2.5 if center else max(4.0, keep + 2.0)) + ext
        else:
            r_in = (dc / 2.0 + ext + 2.5) if center else ext + max(4.0, keep + 2.0)
        r_out = r_avail - ext
        count0 = max(3, int(p.get("drain_count", 6)))
        if center:
            holes.append(circle(0.0, 0.0, dc))
        # anillos repartidos entre ~45 % y el borde útil: el agua se junta
        # contra la pared, así que el anillo exterior va cerca del borde
        r_first = max(r_in, r_out * (0.85 if rings == 1 else 0.5))
        for j in range(rings):
            rr = r_out if rings == 1 else r_first + (r_out - r_first) * j / (rings - 1)
            if rings == 1:
                rr = r_first
            cnt = int(round(count0 * rr / r_first))
            off = (math.pi / cnt) * (j % 2)
            for k in range(cnt):
                a = TAU * k / cnt + off
                holes.extend(_hole(p, rr * math.cos(a), rr * math.sin(a)))
        return holes
    if pat == "grid":
        s = float(p.get("drain_spacing", 3.0 * d))
        rows = int(r_avail // (s * 0.866)) + 1
        for i in range(-rows, rows + 1):
            y = i * s * 0.866
            x0 = (s / 2.0) * (i % 2)
            cols = int(r_avail // s) + 1
            for j in range(-cols - 1, cols + 1):
                x = x0 + j * s
                if math.hypot(x, y) + ext <= r_avail:
                    holes.extend(_hole(p, x, y))
        return holes
    raise ValueError("drain_pattern desconocido: %s" % pat)


def check_layout(holes, r_limit, min_gap=1.6):
    """Errores si un agujero toca la pared o si dos agujeros quedan muy juntos."""
    errs = []
    for h in holes:
        if max(math.hypot(x, y) for x, y in h) > r_limit + 0.01:
            errs.append("Un agujero de drenaje queda a menos del margen de la pared")
            break
    boxes = [(min(x for x, _ in h), max(x for x, _ in h),
              min(y for _, y in h), max(y for _, y in h)) for h in holes]
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = boxes[i], boxes[j]
            if a[1] + min_gap < b[0] or b[1] + min_gap < a[0] or \
               a[3] + min_gap < b[2] or b[3] + min_gap < a[2]:
                continue
            dmin = min(math.hypot(x1 - x2, y1 - y2) for x1, y1 in holes[i] for x2, y2 in holes[j])
            if dmin < min_gap:
                errs.append("Agujeros de drenaje a %.1f mm (< %.1f mm): reducí cantidad o diámetro"
                            % (dmin, min_gap))
                return errs
    return errs


def polygon_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


# ---------------------------------------------------------------------------
# EARCUT (port de mapbox/earcut, licencia ISC) — polígono con agujeros
# ---------------------------------------------------------------------------
class _N(object):
    __slots__ = ("i", "x", "y", "prev", "next", "steiner")

    def __init__(self, i, x, y):
        self.i, self.x, self.y = i, x, y
        self.prev = self.next = None
        self.steiner = False


def _area(p, q, r):
    return (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)


def _eq(a, b):
    return a.x == b.x and a.y == b.y


def _insert(i, x, y, last):
    p = _N(i, x, y)
    if last is None:
        p.prev = p.next = p
    else:
        p.next = last.next
        p.prev = last
        last.next.prev = p
        last.next = p
    return p


def _remove(p):
    p.next.prev = p.prev
    p.prev.next = p.next


def _linked(pts, idx, clockwise):
    s = 0.0
    n = len(pts)
    for k in range(n):
        x1, y1 = pts[k - 1]
        x2, y2 = pts[k]
        s += (x1 - x2) * (y2 + y1)
    last = None
    order = range(n) if clockwise == (s > 0) else range(n - 1, -1, -1)
    for k in order:
        last = _insert(idx[k], pts[k][0], pts[k][1], last)
    if last is not None and _eq(last, last.next):
        _remove(last)
        last = last.next
    return last


def _filter(start, end=None):
    if start is None:
        return start
    if end is None:
        end = start
    p = start
    while True:
        again = False
        if not p.steiner and (_eq(p, p.next) or _area(p.prev, p, p.next) == 0):
            _remove(p)
            p = end = p.prev
            if p is p.next:
                break
            again = True
        else:
            p = p.next
        if not again and p is end:
            break
    return end


def _pit(ax, ay, bx, by, cx, cy, px, py):
    return ((cx - px) * (ay - py) >= (ax - px) * (cy - py) and
            (ax - px) * (by - py) >= (bx - px) * (ay - py) and
            (bx - px) * (cy - py) >= (cx - px) * (by - py))


def _is_ear(ear):
    a, b, c = ear.prev, ear, ear.next
    if _area(a, b, c) >= 0:
        return False
    x0, x1 = min(a.x, b.x, c.x), max(a.x, b.x, c.x)
    y0, y1 = min(a.y, b.y, c.y), max(a.y, b.y, c.y)
    p = c.next
    while p is not a:
        if (x0 <= p.x <= x1 and y0 <= p.y <= y1 and
                _pit(a.x, a.y, b.x, b.y, c.x, c.y, p.x, p.y) and
                _area(p.prev, p, p.next) >= 0):
            return False
        p = p.next
    return True


def _sign(v):
    return 1 if v > 0 else (-1 if v < 0 else 0)


def _on_seg(p, q, r):
    return min(p.x, r.x) <= q.x <= max(p.x, r.x) and min(p.y, r.y) <= q.y <= max(p.y, r.y)


def _intersects(p1, q1, p2, q2):
    o1, o2 = _sign(_area(p1, q1, p2)), _sign(_area(p1, q1, q2))
    o3, o4 = _sign(_area(p2, q2, p1)), _sign(_area(p2, q2, q1))
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_seg(p1, p2, q1): return True
    if o2 == 0 and _on_seg(p1, q2, q1): return True
    if o3 == 0 and _on_seg(p2, p1, q2): return True
    if o4 == 0 and _on_seg(p2, q1, q2): return True
    return False


def _locally_inside(a, b):
    if _area(a.prev, a, a.next) < 0:
        return _area(a, b, a.next) >= 0 and _area(a, a.prev, b) >= 0
    return _area(a, b, a.prev) < 0 or _area(a, a.next, b) < 0


def _middle_inside(a, b):
    p, inside = a, False
    px, py = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
    while True:
        if ((p.y > py) != (p.next.y > py)) and p.next.y != p.y and \
                (px < (p.next.x - p.x) * (py - p.y) / (p.next.y - p.y) + p.x):
            inside = not inside
        p = p.next
        if p is a:
            break
    return inside


def _intersects_poly(a, b):
    p = a
    while True:
        if (p.i != a.i and p.next.i != a.i and p.i != b.i and p.next.i != b.i and
                _intersects(p, p.next, a, b)):
            return True
        p = p.next
        if p is a:
            return False


def _valid_diag(a, b):
    return (a.next.i != b.i and a.prev.i != b.i and not _intersects_poly(a, b) and
            ((_locally_inside(a, b) and _locally_inside(b, a) and _middle_inside(a, b) and
              (_area(a.prev, a, b.prev) or _area(a, b.prev, b))) or
             (_eq(a, b) and _area(a.prev, a, a.next) > 0 and _area(b.prev, b, b.next) > 0)))


def _split(a, b):
    a2, b2 = _N(a.i, a.x, a.y), _N(b.i, b.x, b.y)
    an, bp = a.next, b.prev
    a.next = b; b.prev = a
    a2.next = an; an.prev = a2
    b2.next = a2; a2.prev = b2
    bp.next = b2; b2.prev = bp
    return b2


def _cure(start, tris):
    p = start
    while True:
        a, b = p.prev, p.next.next
        if not _eq(a, b) and _intersects(a, p, p.next, b) and \
                _locally_inside(a, b) and _locally_inside(b, a):
            tris.append((a.i, p.i, b.i))
            _remove(p)
            _remove(p.next)
            p = start = b
        p = p.next
        if p is start:
            break
    return _filter(p)


def _split_earcut(start, tris):
    a = start
    while True:
        b = a.next.next
        while b is not a.prev:
            if a.i != b.i and _valid_diag(a, b):
                c = _split(a, b)
                a = _filter(a, a.next)
                c = _filter(c, c.next)
                _earcut_linked(a, tris, 0)
                _earcut_linked(c, tris, 0)
                return
            b = b.next
        a = a.next
        if a is start:
            return


def _earcut_linked(ear, tris, pss):
    if ear is None:
        return
    stop = ear
    while ear.prev is not ear.next:
        prev, nxt = ear.prev, ear.next
        if _is_ear(ear):
            tris.append((prev.i, ear.i, nxt.i))
            _remove(ear)
            ear = nxt.next
            stop = nxt.next
            continue
        ear = nxt
        if ear is stop:
            if pss == 0:
                _earcut_linked(_filter(ear), tris, 1)
            elif pss == 1:
                _earcut_linked(_cure(_filter(ear), tris), tris, 2)
            else:
                _split_earcut(ear, tris)
            break


def _leftmost(start):
    p = left = start
    while True:
        if p.x < left.x or (p.x == left.x and p.y < left.y):
            left = p
        p = p.next
        if p is start:
            return left


def _sector_contains(m, p):
    return _area(m.prev, m, p.prev) < 0 and _area(p.next, m, m.next) < 0


def _bridge(hole, outer):
    p = outer
    hx, hy = hole.x, hole.y
    qx, m = -float("inf"), None
    while True:
        if hy <= p.y and hy >= p.next.y and p.next.y != p.y:
            x = p.x + (hy - p.y) * (p.next.x - p.x) / (p.next.y - p.y)
            if x <= hx and x > qx:
                qx = x
                m = p if p.x < p.next.x else p.next
                if x == hx:
                    return m
        p = p.next
        if p is outer:
            break
    if m is None:
        return None
    stop, mx, my, tmin = m, m.x, m.y, float("inf")
    p = m
    while True:
        if hx >= p.x >= mx and hx != p.x and _pit(hx if hy < my else qx, hy, mx, my,
                                                    qx if hy < my else hx, hy, p.x, p.y):
            tan = abs(hy - p.y) / (hx - p.x)
            if _locally_inside(p, hole) and (tan < tmin or (tan == tmin and (
                    p.x > m.x or (p.x == m.x and _sector_contains(m, p))))):
                m, tmin = p, tan
        p = p.next
        if p is stop:
            break
    return m


def earcut(outer_pts, outer_idx, holes):
    """outer_pts/outer_idx: contorno exterior (puntos 2D e índices de vértice).
    holes: lista de (pts, idx). Devuelve triángulos como tuplas de índices."""
    tris = []
    node = _linked(outer_pts, outer_idx, True)
    if node is None or node.next is node.prev:
        return tris
    queue = []
    for pts, idx in holes:
        lst = _linked(pts, idx, False)
        if lst is lst.next:
            lst.steiner = True
        queue.append(_leftmost(lst))
    queue.sort(key=lambda n: n.x)
    for h in queue:
        br = _bridge(h, node)
        if br is not None:
            rev = _split(br, h)
            _filter(rev, rev.next)
            node = _filter(br, br.next)
    _earcut_linked(node, tris, 0)
    return tris
