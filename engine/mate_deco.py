# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
MATE CON HUECO — Decoración: relieve proyectado, marca en la base y cuña a 45°
=============================================================================
Python puro (corre en el navegador con Pyodide, en CPython y en Grasshopper).

    forma_texto(texto, alto)        -> forma 2D (polígonos) de un texto
    forma_svg(datos, alto)          -> forma 2D de un SVG (rellenos y trazos)
    relieve(forma, filas, M, deco)  -> malla cerrada que sobresale de la piel del mate
    base_grabada(...)               -> tapa de la base con la marca grabada (hundida)
    cuna(...)                       -> soporte que deja el mate inclinado (montañita)

Una "forma" es {"polys": [[(x, y)], ...] (cerrados, regla nonzero o evenodd),
"lineas": [([(x, y)], medio_ancho)], "regla": "nonzero" | "evenodd"} en mm,
centrada en (0, 0) con y hacia arriba.

El relieve se arma sobre una grilla en el plano de la calcomanía (u a lo largo de la
circunferencia, v hacia arriba): marching squares sobre la distancia con signo a la
forma da celdas trianguladas que siguen la curvatura del mate; cada punto se proyecta
a la piel (radio real en ese ángulo y altura) y sale hacia afuera la profundidad
pedida. La cara de abajo queda 0,8 mm adentro de la pared para que el laminador la
una al cuerpo (como las aletas).
"""
from __future__ import division
import math
import re
import xml.etree.ElementTree as ET

import eden_font
from eden_floor import earcut

TAU = 2.0 * math.pi
EMBUTIDO = 0.8          # mm que el relieve entra en la pared (se une al cuerpo)
MAX_SVG_BYTES = 600000
MAX_SEGMENTOS = 12000


# ===========================================================================
# FORMAS 2D
# ===========================================================================
def _bbox(forma):
    """Caja de la forma: polígonos tal cual y trazos con su medio ancho."""
    xs, ys = [], []
    for P in forma["polys"]:
        xs += [p[0] for p in P]
        ys += [p[1] for p in P]
    for L, hw in forma["lineas"]:
        xs += [p[0] - hw for p in L] + [p[0] + hw for p in L]
        ys += [p[1] - hw for p in L] + [p[1] + hw for p in L]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _normalizar(forma, alto):
    """Centra la forma y la escala a `alto` mm de alto."""
    bb = _bbox(forma)
    if not bb:
        raise ValueError("La figura está vacía")
    x0, y0, x1, y1 = bb
    h = max(y1 - y0, 1e-9)
    k = float(alto) / h
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    T = lambda p: ((p[0] - cx) * k, (p[1] - cy) * k)
    return {"polys": [[T(p) for p in P] for P in forma["polys"]],
            "lineas": [([T(p) for p in L], hw * k) for L, hw in forma["lineas"]],
            "regla": forma.get("regla", "nonzero"),
            "ancho": (x1 - x0) * k, "alto": float(alto)}


def forma_texto(texto, alto, fuente=None):
    """Texto en relieve. fuente: "eden" (trazos propios) o una de mate_fuentes.FUENTES."""
    import mate_fuentes
    fid = fuente or mate_fuentes.DEFECTO
    if fid not in mate_fuentes.IDS:
        raise ValueError("Tipografía desconocida: %s" % fid)
    if fid == "eden":
        t, err = eden_font.check(texto)
    else:
        t, err = mate_fuentes.limpiar(texto, fid)
    if err:
        raise ValueError(err)
    if not t:
        raise ValueError("Escribí el texto que querés poner en el mate")
    if fid == "eden":
        loops, _, _, _ = eden_font.outlines(t, 10.0, mirror=False)
        polys = []
        for ext, holes in loops:
            polys.append(list(ext))
            polys.extend(list(h) for h in holes)
    else:
        polys = mate_fuentes.contornos(t, fid)
        if not polys:
            raise ValueError("El texto no tiene letras para poner en relieve")
    return _normalizar({"polys": polys, "lineas": [], "regla": "nonzero"}, alto)


# ---------------------------------------------------------------- SVG
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _mat_mul(A, B):
    a, b, c, d, e, f = A
    g, h, i, j, k, l_ = B
    return (a * g + c * h, b * g + d * h, a * i + c * j, b * i + d * j,
            a * k + c * l_ + e, b * k + d * l_ + f)


def _transform(txt):
    M = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", txt or ""):
        v = [float(x) for x in _NUM.findall(args)]
        if name == "matrix" and len(v) == 6:
            T = tuple(v)
        elif name == "translate":
            T = (1, 0, 0, 1, v[0] if v else 0.0, v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            sx = v[0] if v else 1.0
            sy = v[1] if len(v) > 1 else sx
            T = (sx, 0, 0, sy, 0, 0)
        elif name == "rotate":
            a = math.radians(v[0] if v else 0.0)
            T = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                T = _mat_mul(_mat_mul((1, 0, 0, 1, v[1], v[2]), T), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX":
            T = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            T = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        M = _mat_mul(M, T)
    return M


def _aplicar(M, p):
    a, b, c, d, e, f = M
    return (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)


def _bezier(p0, p1, p2, p3, n=12):
    out = []
    for i in range(1, n + 1):
        t = i / float(n)
        mt = 1 - t
        out.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                    mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def _arco_svg(p0, rx, ry, phi, fa, fs, p1, n=16):
    """Arco elíptico de SVG (parametrización por centro, SVG 1.1 F.6.5)."""
    if rx == 0 or ry == 0:
        return [p1]
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2.0, (p0[1] - p1[1]) / 2.0
    x1 = cp * dx + sp * dy
    y1 = -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx *= math.sqrt(lam)
        ry *= math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        co = -co
    cx1, cy1 = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cp * cx1 - sp * cy1 + (p0[0] + p1[0]) / 2.0
    cy = sp * cx1 + cp * cy1 + (p0[1] + p1[1]) / 2.0

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not fs and dt > 0:
        dt -= TAU
    elif fs and dt < 0:
        dt += TAU
    n = max(4, int(abs(dt) / (TAU / 32)) + 1)
    out = []
    for i in range(1, n + 1):
        t = t1 + dt * i / float(n)
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cp * x - sp * y + cx, sp * x + cp * y + cy))
    return out


def _path(d):
    """Atributo d de <path> -> lista de subtrazos [(puntos, cerrado)]."""
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|" + _NUM.pattern, d or "")
    subs, cur, cmd = [], [], None
    x = y = sx = sy = 0.0
    lc = None                                      # último punto de control (S/T)
    i = 0

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    subs.append((cur, True))
                cur = []
                x, y = sx, sy
                lc = None
                continue
        elif cmd is None:
            raise ValueError("El SVG tiene un trazo mal formado")
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == "M":
            if cur:
                subs.append((cur, False))
            x, y = num() + ox, num() + oy
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "l" if rel else "L"
            lc = None
        elif C == "L":
            x, y = num() + ox, num() + oy
            cur.append((x, y))
            lc = None
        elif C == "H":
            x = num() + (x if rel else 0.0)
            cur.append((x, y))
            lc = None
        elif C == "V":
            y = num() + (y if rel else 0.0)
            cur.append((x, y))
            lc = None
        elif C == "C":
            c1 = (num() + ox, num() + oy)
            c2 = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            cur += _bezier((x, y), c1, c2, p)
            lc = ("C", c2)
            x, y = p
        elif C == "S":
            c1 = (2 * x - lc[1][0], 2 * y - lc[1][1]) if lc and lc[0] == "C" else (x, y)
            c2 = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            cur += _bezier((x, y), c1, c2, p)
            lc = ("C", c2)
            x, y = p
        elif C == "Q":
            q = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            cur += _bezier((x, y), (x + 2 / 3.0 * (q[0] - x), y + 2 / 3.0 * (q[1] - y)),
                           (p[0] + 2 / 3.0 * (q[0] - p[0]), p[1] + 2 / 3.0 * (q[1] - p[1])), p)
            lc = ("Q", q)
            x, y = p
        elif C == "T":
            q = (2 * x - lc[1][0], 2 * y - lc[1][1]) if lc and lc[0] == "Q" else (x, y)
            p = (num() + ox, num() + oy)
            cur += _bezier((x, y), (x + 2 / 3.0 * (q[0] - x), y + 2 / 3.0 * (q[1] - y)),
                           (p[0] + 2 / 3.0 * (q[0] - p[0]), p[1] + 2 / 3.0 * (q[1] - p[1])), p)
            lc = ("Q", q)
            x, y = p
        elif C == "A":
            rx, ry, phi = num(), num(), num()
            fa, fs = int(num()), int(num())
            p = (num() + ox, num() + oy)
            cur += _arco_svg((x, y), rx, ry, phi, fa, fs, p)
            x, y = p
            lc = None
        else:
            i += 1
    if cur:
        subs.append((cur, False))
    return subs


def _estilo(el, heredado):
    st = dict(heredado)
    for k in ("fill", "stroke", "stroke-width", "fill-rule", "display", "visibility"):
        if el.get(k) is not None:
            st[k] = el.get(k).strip()
    for decl in (el.get("style") or "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            st[k.strip()] = v.strip()
    return st


def _num_attr(el, k, d=0.0):
    v = el.get(k)
    if v is None:
        return d
    m = _NUM.search(v)
    return float(m.group(0)) if m else d


def _elipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(TAU * i / n), cy + ry * math.sin(TAU * i / n)) for i in range(n)]


def forma_svg(datos, alto):
    """Rellenos y trazos de un SVG (path, rect, circle, ellipse, polygon, polyline,
    line, con transform y grupos), como forma 2D de `alto` mm de alto."""
    if isinstance(datos, (bytes, bytearray)):
        if len(datos) > MAX_SVG_BYTES:
            raise ValueError("El SVG es muy grande (máx. 600 KB): simplificalo")
        datos = datos.decode("utf-8", "replace")
    try:
        raiz = ET.fromstring(datos)
    except ET.ParseError:
        raise ValueError("El archivo no es un SVG válido")
    polys, lineas = [], []
    regla = {"v": "nonzero"}

    def tag(el):
        return el.tag.split("}")[-1]

    def visitar(el, M, st):
        st = _estilo(el, st)
        if st.get("display") == "none" or st.get("visibility") == "hidden":
            return
        if tag(el) in ("defs", "clipPath", "mask", "symbol", "title", "desc", "metadata", "style", "text"):
            return
        M = _mat_mul(M, _transform(el.get("transform")))
        t = tag(el)
        subs = []
        if t == "path":
            subs = _path(el.get("d"))
        elif t == "rect":
            x, y = _num_attr(el, "x"), _num_attr(el, "y")
            w, h = _num_attr(el, "width"), _num_attr(el, "height")
            if w > 0 and h > 0:
                subs = [([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)]
        elif t == "circle":
            r = _num_attr(el, "r")
            if r > 0:
                subs = [(_elipse(_num_attr(el, "cx"), _num_attr(el, "cy"), r, r), True)]
        elif t == "ellipse":
            rx, ry = _num_attr(el, "rx"), _num_attr(el, "ry")
            if rx > 0 and ry > 0:
                subs = [(_elipse(_num_attr(el, "cx"), _num_attr(el, "cy"), rx, ry), True)]
        elif t in ("polygon", "polyline"):
            v = [float(x) for x in _NUM.findall(el.get("points") or "")]
            pts = list(zip(v[0::2], v[1::2]))
            if len(pts) >= 2:
                subs = [(pts, t == "polygon")]
        elif t == "line":
            subs = [([(_num_attr(el, "x1"), _num_attr(el, "y1")),
                      (_num_attr(el, "x2"), _num_attr(el, "y2"))], False)]
        fill = st.get("fill", "black")
        stroke = st.get("stroke", "none")
        if st.get("fill-rule") == "evenodd":
            regla["v"] = "evenodd"
        escala = math.sqrt(abs(M[0] * M[3] - M[1] * M[2])) or 1.0
        for pts, cerrado in subs:
            P = [_aplicar(M, p) for p in pts]
            if fill not in ("none", "transparent") and len(P) >= 3 and t not in ("line", "polyline"):
                polys.append(P)
            elif fill not in ("none", "transparent") and t == "polyline" and len(P) >= 3:
                polys.append(P)
            if stroke not in ("none", "transparent"):
                sw = float(_NUM.search(st.get("stroke-width", "1")).group(0)) if _NUM.search(
                    st.get("stroke-width", "1")) else 1.0
                L = P + ([P[0]] if cerrado else [])
                if len(L) >= 2:
                    lineas.append((L, sw * escala / 2.0))
        for hijo in list(el):
            visitar(hijo, M, st)

    visitar(raiz, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), {})
    if not polys and not lineas:
        raise ValueError("El SVG no tiene figuras con relleno ni trazos")
    nseg = sum(len(P) for P in polys) + sum(len(L) for L, _ in lineas)
    if nseg > MAX_SEGMENTOS:
        raise ValueError("El SVG tiene demasiados detalles (%d puntos): simplificalo" % nseg)
    # SVG: y hacia abajo -> y hacia arriba
    polys = [[(x, -y) for x, y in P] for P in polys]
    lineas = [([(x, -y) for x, y in L], hw) for L, hw in lineas]
    return _normalizar({"polys": polys, "lineas": lineas, "regla": regla["v"]}, alto)


# ===========================================================================
# CAMPO DE DISTANCIA CON SIGNO Y MARCHING SQUARES
# ===========================================================================
def _dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    dx, dy = px - ax - t * vx, py - ay - t * vy
    return math.sqrt(dx * dx + dy * dy)


def campo(forma, u0, v0, nu, nv, res, rot=0.0, engorde=0.0):
    """f[i][j] > 0 adentro de la forma (rotada `rot` grados), en la grilla
    u = u0 + i·res, v = v0 + j·res. |f| es la distancia al borde (hasta 3·res).
    engorde: mm que se agranda la forma hacia afuera (letras más gruesas)."""
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    R = lambda p: (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)
    polys = [[R(p) for p in P] for P in forma["polys"]]
    lineas = [([R(p) for p in L], hw) for L, hw in forma["lineas"]]
    tope = 3.0 * res + engorde
    segs = []
    for P in polys:
        for a, b in zip(P, P[1:] + P[:1]):
            if a != b:
                segs.append((a[0], a[1], b[0], b[1], 0.0))
    for L, hw in lineas:
        for a, b in zip(L, L[1:]):
            if a != b:
                segs.append((a[0], a[1], b[0], b[1], hw))
    # cubetas para buscar sólo segmentos cercanos
    cel = max(2.0, 4 * res)
    cub = {}
    for s in segs:
        hw = s[4]
        x0, x1 = min(s[0], s[2]) - hw - tope, max(s[0], s[2]) + hw + tope
        y0, y1 = min(s[1], s[3]) - hw - tope, max(s[1], s[3]) + hw + tope
        for a in range(int(math.floor(x0 / cel)), int(math.floor(x1 / cel)) + 1):
            for b in range(int(math.floor(y0 / cel)), int(math.floor(y1 / cel)) + 1):
                cub.setdefault((a, b), []).append(s)
    par = forma.get("regla") == "evenodd"
    f = [[0.0] * nv for _ in range(nu)]
    for j in range(nv):
        y = v0 + j * res
        # cruces de la fila con los bordes rellenos: (x, sentido) ordenados
        cruces = []
        for P in polys:
            for a, b in zip(P, P[1:] + P[:1]):
                if (a[1] > y) != (b[1] > y):
                    x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                    cruces.append((x, 1 if b[1] > a[1] else -1))
        cruces.sort()
        k = 0
        w = 0
        for i in range(nu):
            x = u0 + i * res
            while k < len(cruces) and cruces[k][0] < x:
                w += cruces[k][1] if not par else 1
                k += 1
            dentro_relleno = (w % 2 == 1) if par else (w != 0)
            d_borde = tope
            d_linea = tope
            for s in cub.get((int(math.floor(x / cel)), int(math.floor(y / cel))), ()):
                d = _dist_seg(x, y, s[0], s[1], s[2], s[3])
                if s[4] == 0.0:
                    if d < d_borde:
                        d_borde = d
                else:
                    if d - s[4] < d_linea:
                        d_linea = d - s[4]
            fr = d_borde if dentro_relleno else -d_borde
            fl = -max(-tope, min(tope, d_linea))
            f[i][j] = (max(fr, fl) if lineas else fr) + engorde
    return f


def triangular(f, u0, v0, res):
    """Marching squares: celdas adentro trianguladas (CCW en u-v) y segmentos del
    borde (con el adentro a la izquierda). Los puntos se identifican por clave para
    que las celdas vecinas compartan vértices (malla sin grietas)."""
    nu, nv = len(f), len(f[0])
    puntos = {}

    def P(key):
        if key in puntos:
            return key
        k = key[0]
        if k == "n":
            _, i, j = key
            puntos[key] = (u0 + i * res, v0 + j * res)
        elif k == "h":
            _, i, j = key
            a, b = f[i][j], f[i + 1][j]
            t = a / (a - b)
            puntos[key] = (u0 + (i + t) * res, v0 + j * res)
        elif k == "v":
            _, i, j = key
            a, b = f[i][j], f[i][j + 1]
            t = a / (a - b)
            puntos[key] = (u0 + i * res, v0 + (j + t) * res)
        return key

    tris, bordes = [], []
    for i in range(nu - 1):
        for j in range(nv - 1):
            c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            fin = [f[a][b] > 0 for a, b in c]
            if not any(fin):
                continue
            if all(fin):
                q = [P(("n",) + c[0]), P(("n",) + c[1]), P(("n",) + c[2]), P(("n",) + c[3])]
                tris += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
                continue
            e = [("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j)]
            silla = fin == [True, False, True, False] or fin == [False, True, False, True]
            centro = sum(f[a][b] for a, b in c) / 4.0 > 0
            if silla and not centro:
                # dos esquinas separadas: un triángulo en cada una
                for k in (0, 1, 2, 3):
                    if fin[k]:
                        a_ = P(e[(k - 1) % 4])
                        b_ = P(e[k])
                        n_ = P(("n",) + c[k])
                        tris.append((n_, b_, a_))
                        bordes.append((b_, a_))
                continue
            poly = []
            for k in range(4):
                if fin[k]:
                    poly.append(P(("n",) + c[k]))
                if fin[k] != fin[(k + 1) % 4]:
                    poly.append(P(e[k]))
            n = len(poly)
            for k in range(n):
                a_, b_ = poly[k], poly[(k + 1) % n]
                if a_[0] != "n" and b_[0] != "n":
                    bordes.append((a_, b_))
            if n == 3:
                tris.append(tuple(poly))
            else:
                ck = ("c", i, j)
                xs = [puntos[q] for q in poly]
                puntos[ck] = (sum(p[0] for p in xs) / n, sum(p[1] for p in xs) / n)
                for k in range(n):
                    tris.append((ck, poly[k], poly[(k + 1) % n]))
    return puntos, tris, bordes


def orientar(V, F):
    """Orienta todas las caras igual (vecinas con aristas opuestas) y hacia afuera."""
    F = [list(t) for t in F]
    adj = {}
    for n, (a, b, c) in enumerate(F):
        for e in ((a, b), (b, c), (c, a)):
            adj.setdefault(frozenset(e), []).append(n)
    hecho = [False] * len(F)
    for s0 in range(len(F)):
        if hecho[s0]:
            continue
        hecho[s0] = True
        pila = [s0]
        while pila:
            n = pila.pop()
            a, b, c = F[n]
            for x, y in ((a, b), (b, c), (c, a)):
                for m in adj.get(frozenset((x, y)), ()):
                    if hecho[m]:
                        continue
                    p, q, r = F[m]
                    # la vecina tiene que recorrer la arista al revés (y -> x)
                    if (p, q) == (x, y) or (q, r) == (x, y) or (r, p) == (x, y):
                        F[m] = [p, r, q]
                    hecho[m] = True
                    pila.append(m)
    F = [tuple(t) for t in F]
    if volumen(V, F) < 0:
        F = [(a, c, b) for a, b, c in F]
    return F


def volumen(V, F):
    s = 0.0
    for a, b, c in F:
        ax, ay, az = V[a]
        bx, by, bz = V[b]
        cx, cy, cz = V[c]
        s += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return s / 6.0


# ===========================================================================
# SUPERFICIE DEL MATE
# ===========================================================================
class Piel(object):
    """Radio de la piel exterior en cualquier (z, θ), interpolando las filas."""

    def __init__(self, filas, M):
        self.filas = filas
        self.M = M
        self.zs = [z for z, _ in filas]

    def radio(self, z, th):
        zs, filas, M = self.zs, self.filas, self.M
        z = max(zs[0], min(zs[-1], z))
        lo, hi = 0, len(zs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if zs[mid] <= z:
                lo = mid
            else:
                hi = mid
        t = 0.0 if zs[hi] == zs[lo] else (z - zs[lo]) / (zs[hi] - zs[lo])
        x = (th % TAU) / TAU * M
        k0 = int(math.floor(x)) % M
        k1 = (k0 + 1) % M
        w = x - math.floor(x)
        r0 = filas[lo][1][k0] * (1 - w) + filas[lo][1][k1] * w
        r1 = filas[hi][1][k0] * (1 - w) + filas[hi][1][k1] * w
        return r0 * (1 - t) + r1 * t


DECO_DEF = {"angulo": -90.0, "z": None, "alto": 18.0, "rot": 0.0, "prof": 1.2, "grosor": 0.0}
DECO_LIM = {"alto": (4.0, 120.0), "prof": (0.4, 4.0), "rot": (-180.0, 180.0), "angulo": (-360.0, 360.0),
            "grosor": (0.0, 1.5)}
MEDALLON_DEF = {"diam": 36.0, "prof": 2.5, "holgura": 0.2}
MEDALLON_LIM = {"diam": (16.0, 70.0), "prof": (1.6, 5.0), "holgura": (0.0, 0.8)}


def _f(v, d, lo=None, hi=None):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    if lo is not None:
        v = max(lo, min(hi, v))
    return v


def relieve(forma, filas, M, deco, H, calidad="preview"):
    """Malla cerrada del relieve proyectado en la piel. deco: angulo (° alrededor;
    -90 = frente), z (mm, centro), alto (mm), rot (°), prof (mm que sobresale)."""
    piel = Piel(filas, M)
    th0 = math.radians(_f(deco.get("angulo"), DECO_DEF["angulo"]))
    zc = _f(deco.get("z"), 0.55 * H)
    prof = _f(deco.get("prof"), DECO_DEF["prof"], *DECO_LIM["prof"])
    rot = _f(deco.get("rot"), 0.0, *DECO_LIM["rot"])
    grosor = _f(deco.get("grosor"), 0.0, *DECO_LIM["grosor"])
    R0 = piel.radio(zc, th0)
    res = 0.3 if calidad == "preview" else 0.2
    # caja de la forma rotada
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    bb = _bbox(forma)
    pts = [(x * ca - y * sa, x * sa + y * ca) for x in (bb[0], bb[2]) for y in (bb[1], bb[3])]
    pad = 2 * res + grosor
    u_lo, u_hi = min(p[0] for p in pts) - pad, max(p[0] for p in pts) + pad
    v_lo, v_hi = min(p[1] for p in pts) - pad, max(p[1] for p in pts) + pad
    nu = int(math.ceil((u_hi - u_lo) / res)) + 1
    nv = int(math.ceil((v_hi - v_lo) / res)) + 1
    if nu * nv > 400000:                          # calcomanías gigantes: grilla más gruesa
        res *= math.sqrt(nu * nv / 400000.0)
        nu = int(math.ceil((u_hi - u_lo) / res)) + 1
        nv = int(math.ceil((v_hi - v_lo) / res)) + 1
    f = campo(forma, u_lo, v_lo, nu, nv, res, rot, grosor)
    puntos, tris, bordes = triangular(f, u_lo, v_lo, res)
    if not tris:
        raise ValueError("La figura es muy chica para el relieve: agrandala")
    avisos = []
    zmin, zmax = zc + v_lo, zc + v_hi
    if zmin < 3.0 or zmax > H - 2.0:
        avisos.append("El relieve se sale del alto del mate: bajalo, subilo o achicalo")
    if (u_hi - u_lo) > math.pi * R0:
        raise ValueError("El relieve da más de media vuelta al mate: achicalo")
    idx_top, idx_bot = {}, {}
    V = []
    for key, (u, v) in puntos.items():
        th = th0 + u / R0
        z = zc + v
        r = piel.radio(z, th)
        c, s = math.cos(th), math.sin(th)
        idx_top[key] = len(V)
        V.append(((r + prof) * c, (r + prof) * s, z))
        idx_bot[key] = len(V)
        V.append(((r - EMBUTIDO) * c, (r - EMBUTIDO) * s, z))
    F = []
    for a, b, c in tris:
        F.append((idx_top[a], idx_top[b], idx_top[c]))
        F.append((idx_bot[a], idx_bot[c], idx_bot[b]))
    for a, b in bordes:
        F.append((idx_top[a], idx_bot[a], idx_bot[b]))
        F.append((idx_top[a], idx_bot[b], idx_top[b]))
    F = orientar(V, F)
    info = {"angulo": round(math.degrees(th0), 1), "z": round(zc, 1), "alto": round(forma["alto"], 1),
            "ancho": round(forma["ancho"], 1), "rot": round(rot, 1), "prof": round(prof, 2),
            "triangulos": len(F), "radio": round(R0, 1), "grosor": round(grosor, 2)}
    return (V, F), info, avisos


def radio_forma(forma):
    """Distancia máxima del centro de la forma a su borde (para que entre en un círculo)."""
    r = 0.0
    for P in forma["polys"]:
        for x, y in P:
            r = max(r, math.hypot(x, y))
    for L, hw in forma["lineas"]:
        for x, y in L:
            r = max(r, math.hypot(x, y) + hw)
    return r


# ===========================================================================
# MEDALLÓN ENCASTRABLE: pieza aparte con el diseño, que entra en un bolsillo del mate
# ===========================================================================
def medallon(piel, th0, zc, Rp, plano, paso=0.6, K=96):
    """Disco que va en el bolsillo: atrás plano (a `plano` mm del eje, sobre el rayo th0),
    adelante al ras de la piel original. Eje del disco = dirección radial en th0.
    -> (V, F) cerrada, en su lugar sobre el mate."""
    n = (math.cos(th0), math.sin(th0))
    t = (-math.sin(th0), math.cos(th0))
    J = max(3, int(math.ceil(Rp / paso)))

    def frente(a, b):
        c = piel.radio(zc + b, th0)
        for _ in range(6):
            th = th0 + math.atan2(a, c)
            R = piel.radio(zc + b, th)
            c = math.sqrt(max(R * R - a * a, 1e-6))
        return c

    def P(a, b, c):
        return (c * n[0] + a * t[0], c * n[1] + a * t[1], zc + b)
    V, F = [], []
    cf = len(V)
    V.append(P(0.0, 0.0, frente(0.0, 0.0)))
    cb = len(V)
    V.append(P(0.0, 0.0, plano))
    anillos_f, anillos_b = [], []
    for j in range(1, J + 1):
        rho = Rp * j / float(J)
        af, ab = [], []
        for k in range(K):
            ph = TAU * k / K
            a, b = rho * math.cos(ph), rho * math.sin(ph)
            af.append(len(V))
            V.append(P(a, b, frente(a, b)))
            ab.append(len(V))
            V.append(P(a, b, plano))
        anillos_f.append(af)
        anillos_b.append(ab)
    for k in range(K):
        q = (k + 1) % K
        F.append((cf, anillos_f[0][k], anillos_f[0][q]))
        F.append((cb, anillos_b[0][q], anillos_b[0][k]))
    for A, B in zip(anillos_f, anillos_f[1:]):
        for k in range(K):
            q = (k + 1) % K
            F.append((A[k], B[k], B[q]))
            F.append((A[k], B[q], A[q]))
    for A, B in zip(anillos_b, anillos_b[1:]):
        for k in range(K):
            q = (k + 1) % K
            F.append((A[k], B[q], B[k]))
            F.append((A[k], A[q], B[q]))
    A, B = anillos_f[-1], anillos_b[-1]
    for k in range(K):
        q = (k + 1) % K
        F.append((A[k], B[k], B[q]))
        F.append((A[k], B[q], A[q]))
    return V, orientar(V, F)


def a_cama(V, th0, zc, plano):
    """Lleva una pieza del medallón a la cama: el fondo plano en z = 0, el diseño arriba."""
    n = (math.cos(th0), math.sin(th0))
    t = (-math.sin(th0), math.cos(th0))
    return [(x * t[0] + y * t[1], z - zc, x * n[0] + y * n[1] - plano) for x, y, z in V]


# ===========================================================================
# MARCA GRABADA EN LA BASE
# ===========================================================================
def ubicar_marca(texto, r_libre, cap_max=8.0, cap_min=3.5):
    """Contornos (espejados, se leen desde abajo) del texto más grande que entra en
    el disco r_libre. -> (loops, cap) o (None, None)."""
    cap = cap_max
    while cap >= cap_min - 1e-9:
        loops = eden_font.outlines(texto, cap, mirror=True)[0]
        rmax = max(math.hypot(x, y) for ext, _ in loops for x, y in ext)
        if rmax <= r_libre:
            return loops, cap
        cap -= 0.5
    return None, None


def _abajo(V, F, tris):
    """Agrega los triángulos de un earcut mirando hacia -z (horario visto desde arriba)."""
    tris = list(tris)
    area = 0.0
    for a, b, d in tris:
        A, B, C = V[a], V[b], V[d]
        area += (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
    F.extend((a, d, b) if area > 0 else (a, b, d) for a, b, d in tris)


def base_grabada(V, F, anillo, z0, loops, prof):
    """Tapa de la base (z0, mirando hacia abajo) con las letras hundidas `prof` mm.
    anillo: índices del primer anillo de la piel (en orden CCW visto desde arriba)."""
    ring = [(V[i][0], V[i][1]) for i in anillo]

    def nuevos(pts, z):
        i0 = len(V)
        V.extend((x, y, z) for x, y in pts)
        return list(range(i0, i0 + len(pts)))
    agujeros = []
    for ext, cs in loops:
        e0 = nuevos(ext, z0)
        e1 = nuevos(ext, z0 + prof)
        c0 = [nuevos(c, z0) for c in cs]
        c1 = [nuevos(c, z0 + prof) for c in cs]
        agujeros.append((list(ext), e0))
        # isla de cada contraforma (a ras de la base)
        for c, i0 in zip(cs, c0):
            _abajo(V, F, earcut(list(c), i0, []))
        # fondo de la letra
        _abajo(V, F, earcut(list(ext), e1, [(list(c), i1) for c, i1 in zip(cs, c1)]))
        # paredes del bolsillo
        for L0, L1 in [(e0, e1)] + list(zip(c0, c1)):
            n = len(L0)
            for k in range(n):
                q = (k + 1) % n
                F.append((L0[k], L1[k], L1[q]))
                F.append((L0[k], L1[q], L0[q]))
    abajo = earcut(ring, list(anillo), agujeros)
    # cada llamada a earcut sale con un solo sentido de giro: se decide por el área total
    # (con puntos alineados, como en el facetado, las astillas no tienen signo propio)
    _abajo(V, F, abajo)


# ===========================================================================
# CUÑA (para dejar el mate inclinado y armar la montañita)
# ===========================================================================
def cuna(r_pie, angulo=45.0, holgura=0.4, borde=7.0, prof=5.0, n=96):
    """Disco con la cara de arriba inclinada `angulo` grados y un hueco para el pie
    del mate. -> ((V, F), info). Centro de la base en (0, 0, 0)."""
    a = math.radians(max(5.0, min(45.0, float(angulo))))
    rp = r_pie + holgura
    Rc = rp + borde
    ta = math.tan(a)
    zc = max(3.0 + prof * math.cos(a) + rp * math.sin(a), Rc * ta + 3.0)
    n_ = (-math.sin(a), 0.0, math.cos(a))           # normal del plano inclinado
    e1 = (math.cos(a), 0.0, math.sin(a))             # en el plano, subiendo
    V = []

    def P(x, y, z):
        V.append((x, y, z))
        return len(V) - 1
    base = [P(Rc * math.cos(TAU * k / n), Rc * math.sin(TAU * k / n), 0.0) for k in range(n)]
    arriba = [P(Rc * math.cos(TAU * k / n), Rc * math.sin(TAU * k / n),
                zc + Rc * math.cos(TAU * k / n) * ta) for k in range(n)]
    cen = P(0.0, 0.0, 0.0)
    loc = lambda q: ((q[0] * e1[0] + (q[2] - zc) * e1[2]), q[1])   # coords en el plano
    boca = [P(rp * math.cos(TAU * k / n) * e1[0], rp * math.sin(TAU * k / n),
              zc + rp * math.cos(TAU * k / n) * e1[2]) for k in range(n)]
    fondo = [P(V[i][0] - prof * n_[0], V[i][1], V[i][2] - prof * n_[2]) for i in boca]
    cf = P(-prof * n_[0], 0.0, zc - prof * n_[2])
    F = []
    for k in range(n):
        q = (k + 1) % n
        F.append((cen, base[q], base[k]))
        F += [(base[k], base[q], arriba[q]), (base[k], arriba[q], arriba[k])]
        F += [(boca[k], fondo[k], fondo[q]), (boca[k], fondo[q], boca[q])]
        F.append((cf, fondo[q], fondo[k]))
    tapa = earcut([loc(V[i]) for i in arriba], arriba, [([loc(V[i]) for i in boca], boca)])
    F += [tuple(t) for t in tapa]
    F = orientar(V, F)
    alto = max(v[2] for v in V)
    return (V, F), {"angulo": round(math.degrees(a), 1), "diam_mm": round(2 * Rc, 1),
                    "alto_mm": round(alto, 1), "hueco_diam_mm": round(2 * rp, 1),
                    "prof_hueco_mm": prof}
