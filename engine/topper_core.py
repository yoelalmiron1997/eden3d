# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
TOPPER PARA TORTAS — texto (una a tres líneas) con palitos, en UNA sola pieza
============================================================================
Se imprime acostado. Siempre sale todo unido:

  1. las líneas de texto (tipografías de engine/fuentes) se dibujan en una grilla fina;
  2. se engordan `contorno` mm (el borde que une las letras, como en los toppers de dos
     colores), se suma el marco (círculo, corazón, flor, rombo o sol) si lo hay;
  3. lo que quede suelto (una tilde, el punto de la i, una palabra aparte) se une a la
     pieza con un puente corto: la pieza final es UNA sola región;
  4. la región se vuelve a contornear (marching squares sobre la distancia firmada, así
     el borde sale suave), se simplifica y se extruye; los palitos (con punta) salen de
     abajo y se meten en la pieza.

Estilos: "simple" (una pieza de un color) o "doble" (base con contorno + letras en
relieve arriba, para imprimir en dos colores: dos objetos en el 3MF como partes de uno).

    construir(opts) -> {"piezas": [(nombre, V, F)], "reporte": {...}}
"""
import math

import mate_fuentes

TAU = 2.0 * math.pi
FUENTES = [
    ("great_vibes", "Great Vibes"), ("dancing_script", "Dancing Script"), ("lobster", "Lobster"),
    ("pacifico", "Pacifico"), ("satisfy", "Satisfy"), ("allura", "Allura"), ("cookie", "Cookie"),
    ("yellowtail", "Yellowtail"), ("kaushan_script", "Kaushan Script"), ("parisienne", "Parisienne"),
    ("alex_brush", "Alex Brush"), ("fredoka", "Fredoka (redondeada)"),
    ("lilita_one", "Lilita One (gruesa)"), ("luckiest_guy", "Luckiest Guy (cómic)"),
    ("archivo_black", "Archivo Black (bloque)"), ("bungee", "Bungee (cartel)"),
]
IDS = [f for f, _ in FUENTES]
MARCOS = [("ninguno", "Sin marco"), ("circulo", "Círculo"), ("corazon", "Corazón"),
          ("flor", "Flor"), ("rombo", "Rombo"), ("sol", "Sol")]
ESTILOS = [("simple", "Un color"), ("doble", "Dos colores (base + letras)")]
DEFECTO = {"lineas": [{"texto": "Feliz", "fuente": "great_vibes", "escala": 1.0},
                      {"texto": "Cumpleaños", "fuente": "great_vibes", "escala": 1.0}],
           "ancho": 140.0, "contorno": 1.2, "grosor": 3.0, "letras": 1.2, "estilo": "simple",
           "marco": "ninguno", "palitos": 2, "largo": 90.0, "calidad": "preview"}
LIMITES = {"ancho": (60.0, 220.0), "contorno": (0.0, 6.0), "grosor": (2.0, 5.0),
           "letras": (0.6, 3.0), "palitos": (1, 2), "largo": (40.0, 140.0), "escala": (0.4, 1.6),
           "lineas": 3, "caracteres": 24}
ANCHO_PALITO = 5.0
PUENTE = 2.4            # mm de ancho de los puentes que unen lo que quedó suelto
MARCO_ANCHO = 3.2


def _f(v, d, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    return max(lo, min(hi, v))


# ===========================================================================
# TEXTO → polígonos (mm, y hacia arriba)
# ===========================================================================
def _linea(texto, fid):
    t, err = mate_fuentes.limpiar(texto, fid)
    if err:
        raise ValueError(err)
    if not t:
        return None
    polys = mate_fuentes.contornos(t, fid)
    pts = [p for P in polys for p in P]
    if not pts:
        return None
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    return {"texto": t, "fuente": fid, "polys": polys, "bbox": (x0, y0, x1, y1)}


def maquetar(lineas, ancho):
    """Apila las líneas centradas (algo encimadas, como los toppers), con la más ancha
    del `ancho` pedido. Devuelve (polígonos en mm, info por línea, caja)."""
    ls = []
    for L in lineas:
        r = _linea(L.get("texto", ""), L.get("fuente") or IDS[0])
        if r:
            r["escala"] = _f(L.get("escala", 1.0), 1.0, *LIMITES["escala"])
            ls.append(r)
    if not ls:
        raise ValueError("Escribí al menos una línea de texto")
    # 1 unidad de fuente = k mm: la línea más ancha (con su escala) mide `ancho`
    k = ancho / max((r["bbox"][2] - r["bbox"][0]) * r["escala"] for r in ls)
    y = 0.0
    out, info = [], []
    abajo_prev, alto_prev = None, None
    for n, r in enumerate(ls):
        x0, y0, x1, y1 = r["bbox"]
        s = k * r["escala"]
        cx = (x0 + x1) / 2.0
        alto = (y1 - y0) * s
        if n:                                  # encimada con la de arriba (como los toppers)
            y = abajo_prev + 0.18 * min(alto, alto_prev)
        dy = y - y1 * s
        for P in r["polys"]:
            out.append([((px - cx) * s, py * s + dy) for px, py in P])
        info.append({"texto": r["texto"], "fuente": r["fuente"], "alto_mm": round(alto, 1),
                     "ancho_mm": round((x1 - x0) * s, 1)})
        abajo_prev, alto_prev = y0 * s + dy, alto
    pts = [p for P in out for p in P]
    ymid = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2.0
    out = [[(x, yy - ymid) for x, yy in P] for P in out]
    pts = [p for P in out for p in P]
    caja = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    return out, info, caja


# ===========================================================================
# MARCOS (contorno de adentro; el marco es un anillo de MARCO_ANCHO por afuera)
# ===========================================================================
def marco(tipo, caja):
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    n = 240
    if tipo == "ninguno":
        return None
    if tipo == "circulo":
        R = max(w / 2.0, h / 2.0 + 6.0)
        return [(R * math.cos(TAU * i / n), R * math.sin(TAU * i / n)) for i in range(n)]
    if tipo == "flor":
        R = max(w / 2.0, h / 2.0 + 6.0) * 0.97
        return [(R * (1 + 0.07 * math.cos(8 * TAU * i / n)) * math.cos(TAU * i / n),
                 R * (1 + 0.07 * math.cos(8 * TAU * i / n)) * math.sin(TAU * i / n)) for i in range(n)]
    if tipo == "sol":
        R = max(w / 2.0, h / 2.0 + 6.0)
        return [(R * (1 + 0.035 * math.cos(28 * TAU * i / n)) * math.cos(TAU * i / n),
                 R * (1 + 0.035 * math.cos(28 * TAU * i / n)) * math.sin(TAU * i / n)) for i in range(n)]
    if tipo == "rombo":
        a = w / 2.0 + h / 2.0
        return [(a, 0.0), (0.0, a), (-a, 0.0), (0.0, -a)]
    if tipo == "corazon":
        pts = []
        for i in range(n):
            t = TAU * i / n
            x = 16 * math.sin(t) ** 3
            yy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((x, yy))
        k = (w / 2.0) / 13.5                   # el texto toca los lados a media altura
        k = max(k, (h / 2.0 + 6.0) / 11.0)
        return [(x * k, (yy + 2.5) * k) for x, yy in pts]
    raise ValueError("marco desconocido: %s" % tipo)


# ===========================================================================
# GRILLA
# ===========================================================================
class Grilla(object):
    def __init__(self, x0, y0, x1, y1, res):
        self.res = res
        self.x0, self.y0 = x0, y0
        self.nx = int(math.ceil((x1 - x0) / res)) + 1
        self.ny = int(math.ceil((y1 - y0) / res)) + 1

    def vacia(self):
        return [bytearray(self.nx) for _ in range(self.ny)]

    def llenar(self, polys, M=None):
        """Relleno nonzero de los polígonos (centros de celda)."""
        M = M if M is not None else self.vacia()
        r, x0, y0 = self.res, self.x0, self.y0
        bordes = []
        for P in polys:
            for a, b in zip(P, P[1:] + P[:1]):
                if a[1] != b[1]:
                    bordes.append((a, b))
        # cubetas por fila para no recorrer todos los bordes en cada fila
        filas = {}
        for e in bordes:
            (ax, ay), (bx, by) = e
            j0 = int(math.floor((min(ay, by) - y0) / r - 0.5)) + 1
            j1 = int(math.floor((max(ay, by) - y0) / r - 0.5))
            for j in range(max(0, j0), min(self.ny - 1, j1) + 1):
                filas.setdefault(j, []).append(e)
        for j, es in filas.items():
            y = y0 + (j + 0.5) * r
            cr = []
            for (ax, ay), (bx, by) in es:
                if (ay > y) != (by > y):
                    cr.append((ax + (y - ay) * (bx - ax) / (by - ay), 1 if by > ay else -1))
            cr.sort()
            w = 0
            fila = M[j]
            for k in range(len(cr) - 1):
                w += cr[k][1]
                if w != 0:
                    i0 = max(0, int(math.ceil((cr[k][0] - x0) / r - 0.5)))
                    i1 = min(self.nx, int(math.ceil((cr[k + 1][0] - x0) / r - 0.5)))
                    if i1 > i0:
                        fila[i0:i1] = b"\x01" * (i1 - i0)
        return M


def _edt1(f, n):
    """Transformada de distancia 1D (Felzenszwalb & Huttenlocher), cuadrados."""
    INF = 1e20
    d = [0.0] * n
    v = [0] * n
    z = [0.0] * (n + 1)
    k = 0
    v[0] = 0
    z[0] = -INF
    z[1] = INF
    for q in range(1, n):
        fq = f[q] + q * q
        while True:
            p = v[k]
            s = (fq - (f[p] + p * p)) / (2.0 * (q - p))
            if s <= z[k]:
                k -= 1
                if k < 0:
                    k = 0
                    v[0] = q
                    z[0] = -INF
                    z[1] = INF
                    break
                continue
            k += 1
            v[k] = q
            z[k] = s
            z[k + 1] = INF
            break
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        p = v[k]
        d[q] = (q - p) * (q - p) + f[p]
    return d


def edt(M, nx, ny, objetivo=1):
    """Distancia al cuadrado (en celdas) de cada celda a la celda más cercana con valor
    `objetivo`."""
    INF = 1e20
    cols = [[0.0] * ny for _ in range(nx)]
    for i in range(nx):
        f = [0.0 if M[j][i] == objetivo else INF for j in range(ny)]
        if any(x == 0.0 for x in f):
            cols[i] = _edt1(f, ny)
        else:
            cols[i] = [INF] * ny
    D = []
    for j in range(ny):
        f = [cols[i][j] for i in range(nx)]
        D.append(_edt1(f, nx))
    return D


def componentes(M, nx, ny):
    """Etiquetas de las regiones conectadas (8 vecinos). -> (etiquetas, cantidad, tamaños)."""
    L = [[0] * nx for _ in range(ny)]
    n = 0
    tam = [0]
    for j in range(ny):
        for i in range(nx):
            if M[j][i] and not L[j][i]:
                n += 1
                c = 0
                pila = [(i, j)]
                L[j][i] = n
                while pila:
                    a, b = pila.pop()
                    c += 1
                    for db in (-1, 0, 1):
                        bb = b + db
                        if 0 <= bb < ny:
                            fila, Lf = M[bb], L[bb]
                            for da in (-1, 0, 1):
                                aa = a + da
                                if 0 <= aa < nx and fila[aa] and not Lf[aa]:
                                    Lf[aa] = n
                                    pila.append((aa, bb))
                tam.append(c)
    return L, n, tam


def capsula(M, g, a, b, ancho):
    """Pinta un puente (segmento grueso) entre los puntos a y b (mm)."""
    r = g.res
    h = ancho / 2.0
    xs, ys = (a[0], b[0]), (a[1], b[1])
    i0 = max(0, int((min(xs) - h - g.x0) / r) - 1)
    i1 = min(g.nx - 1, int((max(xs) + h - g.x0) / r) + 1)
    j0 = max(0, int((min(ys) - h - g.y0) / r) - 1)
    j1 = min(g.ny - 1, int((max(ys) + h - g.y0) / r) + 1)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-12
    for j in range(j0, j1 + 1):
        y = g.y0 + (j + 0.5) * r
        fila = M[j]
        for i in range(i0, i1 + 1):
            x = g.x0 + (i + 0.5) * r
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L2))
            ex, ey = a[0] + t * dx - x, a[1] + t * dy - y
            if ex * ex + ey * ey <= h * h:
                fila[i] = 1


def unir(M, g):
    """Une todas las regiones a la más grande con puentes cortos. -> cantidad de puentes."""
    L, n, tam = componentes(M, g.nx, g.ny)
    if n <= 1:
        return 0
    principal = max(range(1, n + 1), key=lambda k: tam[k])
    puentes = 0
    hechas = {principal}
    for _ in range(n - 1):
        # distancia de cada celda a lo ya unido (EDT con la celda más cercana)
        Mu = [bytearray(1 if L[j][i] in hechas else 0 for i in range(g.nx)) for j in range(g.ny)]
        D = edt(Mu, g.nx, g.ny, 1)
        mejor = None
        for j in range(g.ny):
            Lj, Dj = L[j], D[j]
            for i in range(g.nx):
                k = Lj[i]
                if k and k not in hechas and (mejor is None or Dj[i] < mejor[0]):
                    mejor = (Dj[i], i, j, k)
        if mejor is None:
            break
        _, i, j, k = mejor
        # la celda de lo unido más cercana a (i, j)
        rad = int(math.sqrt(mejor[0])) + 2
        destino = None
        for jj in range(max(0, j - rad), min(g.ny, j + rad + 1)):
            for ii in range(max(0, i - rad), min(g.nx, i + rad + 1)):
                if L[jj][ii] in hechas:
                    d = (ii - i) ** 2 + (jj - j) ** 2
                    if destino is None or d < destino[0]:
                        destino = (d, ii, jj)
        a = (g.x0 + (i + 0.5) * g.res, g.y0 + (j + 0.5) * g.res)
        b = (g.x0 + (destino[1] + 0.5) * g.res, g.y0 + (destino[2] + 0.5) * g.res)
        # el puente entra un poco en cada lado
        dx, dy = b[0] - a[0], b[1] - a[1]
        Ld = math.hypot(dx, dy) or 1.0
        a = (a[0] - dx / Ld * 1.0, a[1] - dy / Ld * 1.0)
        b = (b[0] + dx / Ld * 1.0, b[1] + dy / Ld * 1.0)
        capsula(M, g, a, b, PUENTE)
        puentes += 1
        hechas.add(k)
    return puentes


# ===========================================================================
# CONTORNOS → sólidos
# ===========================================================================
def campo(M, g):
    """Distancia firmada (mm) desde el borde de la región: + adentro."""
    Din = edt(M, g.nx, g.ny, 0)       # adentro: distancia a lo de afuera
    Dout = edt(M, g.nx, g.ny, 1)      # afuera: distancia a lo de adentro
    r = g.res
    return [[(math.sqrt(Din[j][i]) - 0.5) * r if M[j][i] else -(math.sqrt(Dout[j][i]) - 0.5) * r
             for i in range(g.nx)] for j in range(g.ny)]


def lazos(f, g):
    """Marching squares sólo del borde: lazos cerrados con lo de adentro a la izquierda."""
    nx, ny, r = g.nx, g.ny, g.res
    x0, y0 = g.x0 + 0.5 * r, g.y0 + 0.5 * r
    pts = {}

    def P(key):
        if key not in pts:
            k, i, j = key
            if k == "h":
                a, b = f[j][i], f[j][i + 1]
                t = a / (a - b)
                pts[key] = (x0 + (i + t) * r, y0 + j * r)
            else:
                a, b = f[j][i], f[j + 1][i]
                t = a / (a - b)
                pts[key] = (x0 + i * r, y0 + (j + t) * r)
        return key
    sig = {}
    for j in range(ny - 1):
        fj, fj1 = f[j], f[j + 1]
        for i in range(nx - 1):
            fin = (fj[i] > 0, fj[i + 1] > 0, fj1[i + 1] > 0, fj1[i] > 0)
            if fin[0] == fin[1] == fin[2] == fin[3]:
                continue
            e = (("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j))
            silla = fin == (True, False, True, False) or fin == (False, True, False, True)
            if silla and not (fj[i] + fj[i + 1] + fj1[i + 1] + fj1[i] > 0):
                for k in (0, 1, 2, 3):
                    if fin[k]:
                        sig[P(e[k])] = P(e[(k - 1) % 4])
                continue
            # recorre el borde de la celda (antihorario) y une las aristas cortadas
            poly = []
            for k in range(4):
                if fin[k]:
                    poly.append(None)
                if fin[k] != fin[(k + 1) % 4]:
                    poly.append(e[k])
            m = len(poly)
            for k in range(m):
                a_, b_ = poly[k], poly[(k + 1) % m]
                if a_ is not None and b_ is not None:
                    sig[P(a_)] = P(b_)
    out = []
    vistos = set()
    for k0 in list(sig):
        if k0 in vistos:
            continue
        lazo = []
        k = k0
        while k not in vistos and k in sig:
            vistos.add(k)
            lazo.append(pts[k])
            k = sig[k]
        if len(lazo) >= 3:
            out.append(lazo)
    return out


def _area(P):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(P, P[1:] + P[:1]))


def _simplificar(P, eps):
    """Douglas–Peucker en un lazo cerrado."""
    if len(P) < 8:
        return P
    # partir en el punto más lejano del primero
    far = max(range(len(P)), key=lambda i: (P[i][0] - P[0][0]) ** 2 + (P[i][1] - P[0][1]) ** 2)

    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1e-12
        imax, dmax = 0, -1.0
        for i in range(1, len(pts) - 1):
            d = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / L
            if d > dmax:
                imax, dmax = i, d
        if dmax <= eps:
            return [a, b]
        return dp(pts[:imax + 1])[:-1] + dp(pts[imax:])
    A = dp(P[:far + 1])
    B = dp(P[far:] + [P[0]])
    out = A[:-1] + B[:-1]
    return out if len(out) >= 3 else P


def _dentro(p, P):
    x, y = p
    c = False
    for (ax, ay), (bx, by) in zip(P, P[1:] + P[:1]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            c = not c
    return c


def extruir(lazos_, z0, z1):
    """Lazos (afuera antihorario, agujeros horario) → sólidos cerrados entre z0 y z1."""
    from eden_floor import earcut
    afuera = [P for P in lazos_ if _area(P) > 0]
    agujeros = [P for P in lazos_ if _area(P) < 0]
    grupos = [[P, []] for P in sorted(afuera, key=_area)]
    for H in agujeros:
        for G in grupos:                       # el contorno más chico que lo contiene
            if _dentro(H[0], G[0]):
                G[1].append(H)
                break
    V, F = [], []
    for P, hs in grupos:
        idx0 = len(V)
        todos = [P] + hs
        base = []
        for L in todos:
            i0 = len(V)
            V.extend((x, y, z0) for x, y in L)
            V.extend((x, y, z1) for x, y in L)
            base.append((L, i0))
        n0 = len(P)
        tris = earcut(list(P), list(range(idx0, idx0 + n0)),
                      [(list(L), list(range(i0, i0 + len(L)))) for L, i0 in base[1:]])
        for a, b, c in tris:
            F.append((a, c, b))                                # abajo
            F.append((a + _desfase(base, a), b + _desfase(base, b), c + _desfase(base, c)))  # arriba
        for L, i0 in base:
            n = len(L)
            for k in range(n):
                q = (k + 1) % n
                a, b = i0 + k, i0 + q
                F.append((a, b, b + n))
                F.append((a, b + n, a + n))
    return V, F


def _desfase(base, idx):
    """Índice del vértice de arriba que corresponde al de abajo idx."""
    for L, i0 in base:
        if i0 <= idx < i0 + len(L):
            return len(L)
    raise IndexError(idx)


def palito(x, y_arriba, largo, ancho, z0, z1, punta=12.0):
    """Palito con punta (pentágono extruido), de y_arriba hacia abajo."""
    h = ancho / 2.0
    yb = y_arriba - largo
    P = [(x - h, y_arriba), (x - h, yb + punta), (x, yb), (x + h, yb + punta), (x + h, y_arriba)]
    if _area(P) < 0:
        P = P[::-1]
    return extruir([P], z0, z1)


# ===========================================================================
# TODO JUNTO
# ===========================================================================
def opciones(o):
    o = dict(DEFECTO, **(o or {}))
    ls = o.get("lineas") or []
    if not isinstance(ls, list) or not ls:
        raise ValueError("Escribí al menos una línea de texto")
    if len(ls) > LIMITES["lineas"]:
        raise ValueError("El topper puede tener hasta %d líneas" % LIMITES["lineas"])
    lineas = []
    for L in ls:
        L = dict(L) if isinstance(L, dict) else {"texto": str(L)}
        if L.get("fuente") and L["fuente"] not in IDS:
            raise ValueError("Tipografía desconocida: %s" % L["fuente"])
        if len(str(L.get("texto") or "").strip()) > LIMITES["caracteres"]:
            raise ValueError("Cada línea puede tener hasta %d letras" % LIMITES["caracteres"])
        lineas.append(L)
    o["lineas"] = lineas
    for k in ("ancho", "contorno", "grosor", "letras", "largo"):
        o[k] = _f(o.get(k), DEFECTO[k], *LIMITES[k])
    o["palitos"] = int(_f(o.get("palitos"), 2, *LIMITES["palitos"]))
    if o.get("estilo") not in [e for e, _ in ESTILOS]:
        raise ValueError("estilo desconocido: %s" % o.get("estilo"))
    if o.get("marco") not in [m for m, _ in MARCOS]:
        raise ValueError("marco desconocido: %s" % o.get("marco"))
    if o["estilo"] == "doble":
        o["contorno"] = max(o["contorno"], 2.0)     # la base tiene que asomar alrededor
    o["calidad"] = o.get("calidad") if o.get("calidad") in ("preview", "normal") else "preview"
    return o


def construir(opts):
    o = opciones(opts)
    res = 0.32 if o["calidad"] == "preview" else 0.2
    polys, info_lineas, caja = maquetar(o["lineas"], o["ancho"])
    mpoly = marco(o["marco"], caja)
    ancho_txt = o["ancho"]
    for _ in range(6):                         # con marco, el ancho pedido es el del marco
        if not mpoly:
            break
        wf = max(p[0] for p in mpoly) - min(p[0] for p in mpoly) + 2 * MARCO_ANCHO + 1.0
        if wf <= o["ancho"]:
            break
        ancho_txt *= o["ancho"] / wf
        polys, info_lineas, caja = maquetar(o["lineas"], ancho_txt)
        mpoly = marco(o["marco"], caja)
    ext = list(caja)
    if mpoly:
        ext = [min(ext[0], min(p[0] for p in mpoly)), min(ext[1], min(p[1] for p in mpoly)),
               max(ext[2], max(p[0] for p in mpoly)), max(ext[3], max(p[1] for p in mpoly))]
    pad = o["contorno"] + MARCO_ANCHO + 3.0
    g = Grilla(ext[0] - pad, ext[1] - pad, ext[2] + pad, ext[3] + pad, res)
    T = g.llenar(polys)
    # base: letras engordadas + marco
    if o["contorno"] > 0:
        D = edt(T, g.nx, g.ny, 1)
        lim = (o["contorno"] / res + 0.5) ** 2
        S = [bytearray(1 if D[j][i] <= lim else 0 for i in range(g.nx)) for j in range(g.ny)]
    else:
        S = [bytearray(f) for f in T]
    if mpoly:
        A = g.llenar([mpoly])
        Da = edt(A, g.nx, g.ny, 1)
        lim = (MARCO_ANCHO / res + 0.5) ** 2
        for j in range(g.ny):
            Sj, Aj, Dj = S[j], A[j], Da[j]
            for i in range(g.nx):
                if not Aj[i] and Dj[i] <= lim:
                    Sj[i] = 1
    puentes = unir(S, g)
    f = campo(S, g)
    eps = 0.05 if o["calidad"] == "normal" else 0.09
    lz = [_simplificar(P, eps) for P in lazos(f, g)]
    lz = [P for P in lz if abs(_area(P)) > 0.3]
    z1 = o["grosor"]
    Vb, Fb = extruir(lz, 0.0, z1)
    # palitos: salen de lo más bajo de la pieza en su columna y se meten 6 mm
    W = ext[2] - ext[0]
    xs = [0.0] if o["palitos"] == 1 else [-0.26 * W, 0.26 * W]
    palos, info_palos = [], []
    for x in xs:
        i0 = int((x - g.x0) / res)
        # columna cercana donde la pieza tenga material macizo de abajo para clavar el palito
        mejor = None
        for i in range(max(0, i0 - int(10 / res)), min(g.nx, i0 + int(10 / res) + 1)):
            j = next((jj for jj in range(g.ny) if S[jj][i]), None)
            if j is None:
                continue
            run = 0
            while j + run < g.ny and S[j + run][i]:
                run += 1
            maciza = min(run * res, 6.0)
            clave = (-round(maciza, 1), abs(i - i0))
            if mejor is None or clave < mejor[0]:
                mejor = (clave, i, j, maciza)
        _, i, j, maciza = mejor
        x = g.x0 + (i + 0.5) * res
        y_low = g.y0 + j * res + 0.1
        meter = max(1.0, maciza - 0.4)
        palos.append(palito(x, y_low + meter, o["largo"] + meter, ANCHO_PALITO, 0.0, z1))
        info_palos.append({"x": round(x, 3), "arriba": round(y_low + meter, 3),
                           "punta": round(y_low - o["largo"], 3), "adentro_mm": round(meter, 2)})
    for V, F in palos:
        off = len(Vb)
        Vb.extend(V)
        Fb.extend((a + off, b + off, c + off) for a, b, c in F)
    piezas = [("TOPPER", Vb, Fb)]
    if o["estilo"] == "doble":
        fl = campo(T, g)
        ll = [_simplificar(P, eps) for P in lazos(fl, g)]
        ll = [P for P in ll if abs(_area(P)) > 0.2]
        Vl, Fl = extruir(ll, z1 - 0.01, z1 + o["letras"])
        piezas.append(("LETRAS", Vl, Fl))
    xs_ = [v[0] for _, V, _ in piezas for v in V]
    ys_ = [v[1] for _, V, _ in piezas for v in V]
    zs_ = [v[2] for _, V, _ in piezas for v in V]
    rep = {"lineas": info_lineas, "estilo": o["estilo"], "marco": o["marco"],
           "palitos": o["palitos"], "puentes": puentes, "contorno_mm": o["contorno"],
           "grosor_mm": z1, "letras_mm": o["letras"] if o["estilo"] == "doble" else 0.0,
           "medidas_mm": [round(max(xs_) - min(xs_), 1), round(max(ys_) - min(ys_), 1),
                          round(max(zs_) - min(zs_), 2)],
           "triangulos": sum(len(F) for _, _, F in piezas), "res_mm": res, "palos": info_palos}
    return {"piezas": piezas, "reporte": rep, "grilla": g, "region": S}
