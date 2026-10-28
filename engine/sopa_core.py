# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
SOPA DE LETRAS 3D — Generador de sopas de letras para imprimir en 3D
====================================================================
Python puro (corre en el navegador con Pyodide y en CPython para los tests).

1. Arma la sopa: ubica las palabras en la grilla (la dificultad define las
   direcciones) y completa con letras al azar pesadas por frecuencia del español.
2. Tablero 3D: placa base + letras en relieve (fuente de trazos de eden_font).
3. Lo corta en piezas de rompecabezas que encastran: los cortes van entre celdas
   (ninguna letra queda partida) y los encastres (lengüeta redonda) van en la franja
   libre entre dos filas de letras, así nunca pasan por debajo de una letra.
   Cada lado del corte se corre media holgura para que encastre justo.
4. Placa opcional con la lista de palabras.

    generar(palabras, filas, cols, dificultad, semilla) -> sopa
    build_sopa(opts) -> {"piezas": [...], "sopa": {...}, "report": {...}}

Unidades: mm. Z hacia arriba. La celda (0, 0) es la de arriba a la izquierda.
"""
from __future__ import division
import math
import random
import unicodedata

import eden_font
from eden_floor import earcut

SOPA_VERSION = "1.0.0"
PLA_G_CM3 = 1.24
ALFABETO = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
# frecuencia aproximada de letras en español (para rellenar)
FRECUENCIA = {"A": 12.5, "B": 1.4, "C": 4.7, "D": 5.9, "E": 13.7, "F": 0.7, "G": 1.0,
              "H": 0.7, "I": 6.3, "J": 0.4, "K": 0.1, "L": 5.0, "M": 3.2, "N": 6.7,
              "Ñ": 0.3, "O": 8.7, "P": 2.5, "Q": 0.9, "R": 6.9, "S": 8.0, "T": 4.6,
              "U": 3.9, "V": 0.9, "W": 0.1, "X": 0.2, "Y": 0.9, "Z": 0.5}
DIRECCIONES = {
    "facil": [(0, 1), (1, 0)],
    "media": [(0, 1), (1, 0), (1, 1), (-1, 1)],
    "dificil": [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)],
}
NOMBRE_DIR = {(0, 1): "→", (1, 0): "↓", (1, 1): "↘", (-1, 1): "↗", (0, -1): "←",
              (-1, 0): "↑", (-1, -1): "↖", (1, -1): "↙"}
LIMITES = {"celda_min": 10.0, "celda_max": 30.0, "grilla_min": 5, "grilla_max": 24,
           "palabras_max": 40, "cama_min": 80.0, "cama_max": 400.0}
DEFAULTS = {"celda": 15.0, "base": 3.0, "relieve": 1.2, "margen": 6.0, "holgura": 0.2,
            "cama": 220.0, "letra": 0.48, "lista": True, "dificultad": "media",
            "marcadores": True, "ajuste": 0.15, "pared_marcador": 1.6}
PARED_MARCADOR_MIN = 1.2     # mm: con menos, la letra se achica sola
LUZ_VECINAS = 0.3            # mm entre el marcador y las letras de al lado


# ===========================================================================
# 1. LA SOPA
# ===========================================================================
def normalizar(palabra):
    """Mayúsculas, sin acentos (salvo la Ñ) y sólo letras."""
    s = str(palabra or "").strip().upper()
    out = []
    for ch in s:
        if ch == "Ñ":
            out.append(ch)
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        if base in ALFABETO:
            out.append(base)
    return "".join(out)


def limpiar_palabras(palabras):
    """Normaliza, saca repetidas y vacías. Devuelve (limpias, descartadas)."""
    vistas, limpias, descartadas = set(), [], []
    for p in palabras or []:
        n = normalizar(p)
        if len(n) < 2:
            if str(p).strip():
                descartadas.append(str(p).strip())
            continue
        if n in vistas:
            continue
        vistas.add(n)
        limpias.append(n)
    return limpias[:LIMITES["palabras_max"]], descartadas


def tamano_auto(palabras, factor=2.4):
    """Grilla cuadrada donde entran cómodas las palabras."""
    if not palabras:
        return 10
    largo = max(len(p) for p in palabras)
    letras = sum(len(p) for p in palabras)
    n = max(largo + 1, int(math.ceil(math.sqrt(letras * factor))), LIMITES["grilla_min"])
    return min(n, LIMITES["grilla_max"])


def _cabe(grid, w, r, c, dr, dc):
    filas, cols = len(grid), len(grid[0])
    cruces = 0
    for i, ch in enumerate(w):
        rr, cc = r + dr * i, c + dc * i
        if not (0 <= rr < filas and 0 <= cc < cols):
            return -1
        g = grid[rr][cc]
        if g is not None:
            if g != ch:
                return -1
            cruces += 1
    return cruces


SEPARACION_CELDAS = 0.8     # con marcadores: distancia mínima entre dos palabras (en celdas)


def _d_segs(a, b):
    """Distancia entre dos segmentos (r0, c0, r1, c1) de la grilla."""
    def d_pt(px, py, s):
        ax, ay, bx, by = s
        vx, vy = bx - ax, by - ay
        L = vx * vx + vy * vy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
        return math.hypot(px - ax - t * vx, py - ay - t * vy)

    def cruzan(s, q):
        def o(p1, p2, p3):
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
        A, B, C, D = (s[0], s[1]), (s[2], s[3]), (q[0], q[1]), (q[2], q[3])
        return (o(A, B, C) * o(A, B, D) < 0) and (o(C, D, A) * o(C, D, B) < 0)
    if cruzan(a, b):
        return 0.0
    return min(d_pt(a[0], a[1], b), d_pt(a[2], a[3], b), d_pt(b[0], b[1], a), d_pt(b[2], b[3], a))


def generar(palabras, filas=None, cols=None, dificultad="media", semilla=1, separadas=False):
    """Ubica las palabras (las más largas primero; prefiere cruces) y rellena.
    separadas=True (con marcadores): sin letras compartidas y con lugar entre palabras,
    así todos los marcadores pueden estar puestos a la vez."""
    palabras, descartadas = limpiar_palabras(palabras)
    n = tamano_auto(palabras, 3.2 if separadas else 2.4)
    filas = int(filas or n)
    cols = int(cols or n)
    filas = max(LIMITES["grilla_min"], min(LIMITES["grilla_max"], filas))
    cols = max(LIMITES["grilla_min"], min(LIMITES["grilla_max"], cols))
    dirs = DIRECCIONES.get(dificultad, DIRECCIONES["media"])
    rnd = random.Random(semilla)
    mejor = None
    for intento in range(12):              # varios intentos: se queda con el más completo
        grid = [[None] * cols for _ in range(filas)]
        ubicadas, faltan, segs = [], [], []
        for w in sorted(palabras, key=lambda x: (-len(x), x)):
            opciones = []
            for dr, dc in dirs:
                for r in range(filas):
                    for c in range(cols):
                        k = _cabe(grid, w, r, c, dr, dc)
                        if k < 0 or (separadas and k > 0):
                            continue
                        if separadas:
                            sg = (r, c, r + dr * (len(w) - 1), c + dc * (len(w) - 1))
                            if any(_d_segs(sg, q) < SEPARACION_CELDAS for q in segs):
                                continue
                        opciones.append((k, rnd.random(), r, c, dr, dc))
            if not opciones:
                faltan.append(w)
                continue
            opciones.sort(reverse=True)
            # un poco de azar entre las mejores para que no quede todo apilado
            top = [o for o in opciones if o[0] == opciones[0][0]]
            k, _, r, c, dr, dc = rnd.choice(top[:max(1, len(top))]) if rnd.random() < 0.35 \
                else rnd.choice(opciones[:max(1, len(opciones) // 3)])
            for i, ch in enumerate(w):
                grid[r + dr * i][c + dc * i] = ch
            segs.append((r, c, r + dr * (len(w) - 1), c + dc * (len(w) - 1)))
            ubicadas.append({"palabra": w, "fila": r, "col": c, "df": dr, "dc": dc,
                             "dir": NOMBRE_DIR[(dr, dc)]})
        if mejor is None or len(faltan) < len(mejor[2]):
            mejor = (grid, ubicadas, faltan)
        if not faltan:
            break
    grid, ubicadas, faltan = mejor
    letras = list(FRECUENCIA.keys())
    pesos = [FRECUENCIA[x] for x in letras]
    total = sum(pesos)
    for r in range(filas):
        for c in range(cols):
            if grid[r][c] is None:
                x = rnd.random() * total
                for ch, p in zip(letras, pesos):
                    x -= p
                    if x <= 0:
                        grid[r][c] = ch
                        break
                else:
                    grid[r][c] = "A"
    orden = {w: i for i, w in enumerate(palabras)}
    ubicadas.sort(key=lambda u: orden.get(u["palabra"], 0))
    return {"grid": ["".join(f) for f in grid], "filas": filas, "cols": cols,
            "ubicadas": ubicadas, "faltan": faltan, "descartadas": descartadas,
            "dificultad": dificultad if dificultad in DIRECCIONES else "media",
            "semilla": semilla, "separadas": separadas}


def verificar(sopa):
    """Cada palabra ubicada se lee en la grilla en su dirección."""
    g = sopa["grid"]
    for u in sopa["ubicadas"]:
        w = "".join(g[u["fila"] + u["df"] * i][u["col"] + u["dc"] * i]
                    for i in range(len(u["palabra"])))
        if w != u["palabra"]:
            return False
    return True


# ===========================================================================
# 2. GEOMETRÍA 2D
# ===========================================================================
def _area(loop):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


_GLIFO = {}


def glifo(ch, cap):
    """Contornos de una letra centrada en (0,0): [(exterior CCW, [contraformas CW])]
    y la caja (xmin, ymin, xmax, ymax)."""
    key = (ch, round(cap, 3))
    if key not in _GLIFO:
        res = eden_font.outlines(ch, cap, mirror=False)[0]
        xs = [x for e, _ in res for x, _ in e]
        ys = [y for e, _ in res for _, y in e]
        _GLIFO[key] = (res, (min(xs), min(ys), max(xs), max(ys)))
    return _GLIFO[key]


def _arco(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / float(n)),
             cy + r * math.sin(a0 + (a1 - a0) * i / float(n))) for i in range(n + 1)]


def lengueta(u0, e, k):
    """Perfil de la lengüeta (en coordenadas del corte: u a lo largo, v hacia el
    vecino), corrido e mm (negativo = achicada, del lado dueño; positivo = agrandada,
    del lado que la recibe). k = dict con cuello, cabeza y profundidad."""
    a = k["cuello"] + e                     # medio ancho del cuello
    R = k["cabeza"] + e                     # radio de la cabeza
    vc = k["prof"] - k["cabeza"]            # centro de la cabeza (fijo)
    v0 = e                                  # línea de corte corrida
    vn = vc - math.sqrt(max(R * R - a * a, 1e-9))
    ang0 = math.atan2(vn - vc, a)           # derecha del cuello (abajo de la cabeza)
    ang1 = math.pi - ang0                   # izquierda
    pts = [(u0 + a, v0), (u0 + a, vn)]
    arco = _arco(u0, vc, R, ang0, ang1 + (2 * math.pi if ang1 < ang0 else 0), 22)
    pts += arco[1:-1]
    pts += [(u0 - a, vn), (u0 - a, v0)]
    return pts                              # de u creciente a u decreciente (sentido +)


# ===========================================================================
# 3. PIEZAS
# ===========================================================================
def _cortes(n, partes):
    """Índices de celda donde cortar n celdas en 'partes' bloques parejos."""
    return [int(round(n * i / float(partes))) for i in range(partes + 1)]


def plan_piezas(filas, cols, celda, margen, cama):
    """Cuántas piezas por lado para que cada una entre en la cama (con margen)."""
    util = cama - 10.0
    W = cols * celda + 2 * margen
    H = filas * celda + 2 * margen
    # como mínimo 2 × 2: la gracia es que encastre (si la grilla lo permite)
    px = max(2, int(math.ceil(W / util)))
    py = max(2, int(math.ceil(H / util)))
    while px > 1 and cols // px < 2:
        px -= 1
    while py > 1 and filas // py < 2:
        py -= 1
    return px, py


def _choca(rect, cajas):
    x0, y0, x1, y1 = rect
    for a0, b0, a1, b1 in cajas:
        if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
            return True
    return False


def armar_piezas(sopa, p):
    """Contornos 2D de cada pieza + letras que le tocan."""
    filas, cols = sopa["filas"], sopa["cols"]
    cel, m, t = p["celda"], p["margen"], p["holgura"]
    cap = p["letra"] * cel
    px, py = p.get("piezas_x"), p.get("piezas_y")
    if not px or not py:
        px, py = plan_piezas(filas, cols, cel, m, p["cama"])
    px = max(1, min(int(px), cols // 2))
    py = max(1, min(int(py), filas // 2))
    cx_ = _cortes(cols, px)
    cy_ = _cortes(filas, py)
    W, H = cols * cel + 2 * m, filas * cel + 2 * m
    # coordenadas: x hacia la derecha, y hacia arriba; la fila 0 arriba
    X = lambda c: m + c * cel                                  # borde izquierdo de la columna c
    Y = lambda r: H - m - r * cel                              # borde superior de la fila r
    centro = lambda r, c: (X(c) + cel / 2.0, Y(r) - cel / 2.0)
    caja_letra = {}
    for r in range(filas):
        for c in range(cols):
            _, (a0, b0, a1, b1) = glifo(sopa["grid"][r][c], cap)
            x, y = centro(r, c)
            caja_letra[(r, c)] = (x + a0 - 0.3, y + b0 - 0.3, x + a1 + 0.3, y + b1 + 0.3)
    k = {"cuello": 0.075 * cel, "cabeza": 0.16 * cel, "prof": 0.42 * cel}
    rnd = random.Random(1000 + int(sopa.get("semilla") or 0))

    def lengueta_en(i0, i1, fijo, vertical):
        """Lengüetas de un borde interno entre las celdas i0..i1 a lo largo del corte:
        una cada ~3 celdas, alternando el lado, en las franjas libres entre letras.
        Devuelve [(u, signo)]; signo + = hacia +x (vertical) o hacia abajo (horizontal)."""
        validas = {}
        for b in range(i0 + 1, i1):
            u = Y(b) if vertical else X(b)
            for s in (1, -1):
                ext = k["prof"] + t
                ancho = k["cabeza"] + t
                if vertical:
                    xs = (X(fijo), X(fijo) + ext) if s > 0 else (X(fijo) - ext, X(fijo))
                    rect = (xs[0], u - ancho, xs[1], u + ancho)
                    vecinas = [(b - 1, fijo), (b, fijo), (b - 1, fijo - 1), (b, fijo - 1)]
                else:
                    ys = (Y(fijo) - ext, Y(fijo)) if s > 0 else (Y(fijo), Y(fijo) + ext)
                    rect = (u - ancho, ys[0], u + ancho, ys[1])
                    vecinas = [(fijo, b - 1), (fijo, b), (fijo - 1, b - 1), (fijo - 1, b)]
                if not _choca(rect, [caja_letra[q] for q in vecinas if q in caja_letra]):
                    validas.setdefault(b, []).append(s)
        n = max(1, int(round((i1 - i0) / 3.0)))
        elegidas, usadas = [], set()
        primero = 1 if rnd.random() < 0.5 else -1
        for q in range(n):
            meta = i0 + (i1 - i0) * (q + 0.5) / n
            libres = [b for b in validas if all(abs(b - x) >= 2 for x in usadas)]
            if not libres:
                break
            b = min(libres, key=lambda x: (abs(x - meta), x))
            quiero = primero if q % 2 == 0 else -primero
            s = quiero if quiero in validas[b] else validas[b][0]
            usadas.add(b)
            elegidas.append((Y(b) if vertical else X(b), s))
        return elegidas

    # lengüetas de cada borde interno
    lv = {}   # cortes verticales: (indice_corte, bloque_fila) -> (u, signo)  signo + = hacia la derecha
    for i in range(1, px):
        for j in range(py):
            lv[(i, j)] = lengueta_en(cy_[j], cy_[j + 1], cx_[i], True)
    lh = {}   # cortes horizontales: (bloque_col, indice_corte) -> (u, signo)  signo + = hacia abajo
    for i in range(px):
        for j in range(1, py):
            lh[(i, j)] = lengueta_en(cx_[i], cx_[i + 1], cy_[j], False)
    sin_lengueta = sum(1 for v in list(lv.values()) + list(lh.values()) if not v)
    n_lenguetas = sum(len(v) for v in list(lv.values()) + list(lh.values()))

    def lado(P0, cut, eje, sale, tabs):
        """Puntos de un lado de la pieza desde P0 (sentido antihorario).
        cut = coordenada nominal del corte; eje = "x" (corte vertical) o "y";
        sale = +1/-1: hacia dónde queda afuera de la pieza en ese eje;
        tabs = [(u0, dueño)]: dueño = la lengüeta sale de esta pieza."""
        pts = [P0]
        segs = []
        for u0, duenio in tabs or []:
            prof = lengueta(u0, -t / 2.0, k) if duenio else lengueta(u0, t / 2.0, k)
            sv = 1.0 if duenio else -1.0
            seg = [((cut + sale * sv * v, u) if eje == "x" else (u, cut + sale * sv * v))
                   for u, v in prof]
            if math.hypot(seg[-1][0] - P0[0], seg[-1][1] - P0[1]) < \
                    math.hypot(seg[0][0] - P0[0], seg[0][1] - P0[1]):
                seg.reverse()
            segs.append((math.hypot(seg[0][0] - P0[0], seg[0][1] - P0[1]), seg))
        for _, seg in sorted(segs):
            pts += seg
        return pts

    piezas = []
    for j in range(py):
        for i in range(px):
            izq = 0.0 if i == 0 else X(cx_[i]) + t / 2.0
            der = W if i == px - 1 else X(cx_[i + 1]) - t / 2.0
            arr = H if j == 0 else Y(cy_[j]) - t / 2.0
            aba = 0.0 if j == py - 1 else Y(cy_[j + 1]) + t / 2.0
            loop = []
            # abajo (izq -> der): corte j+1; la pieza queda arriba; sg>0 = baja = es de ésta
            tabs = [(u, sg > 0) for u, sg in lh.get((i, j + 1), [])] if j < py - 1 else []
            loop += lado((izq, aba), Y(cy_[j + 1]) if j < py - 1 else 0, "y", -1, tabs)
            # derecha (abajo -> arriba): corte i+1; sg>0 = va a la derecha = es de ésta
            tabs = [(u, sg > 0) for u, sg in lv.get((i + 1, j), [])] if i < px - 1 else []
            loop += lado((der, aba), X(cx_[i + 1]) if i < px - 1 else W, "x", 1, tabs)
            # arriba (der -> izq): corte j; sg<0 = sube = es de ésta
            tabs = [(u, sg < 0) for u, sg in lh.get((i, j), [])] if j > 0 else []
            loop += lado((der, arr), Y(cy_[j]) if j > 0 else H, "y", 1, tabs)
            # izquierda (arriba -> abajo): corte i; sg<0 = va a la izquierda = es de ésta
            tabs = [(u, sg < 0) for u, sg in lv.get((i, j), [])] if i > 0 else []
            loop += lado((izq, arr), X(cx_[i]) if i > 0 else 0, "x", -1, tabs)
            loop = _limpiar(loop)
            rc = [(r, c) for r in range(cy_[j], cy_[j + 1]) for c in range(cx_[i], cx_[i + 1])]
            letras = [(sopa["grid"][r][c], centro(r, c)) for r, c in rc]
            piezas.append({"nombre": "P%d" % (len(piezas) + 1), "i": i, "j": j,
                           "contorno": loop, "letras": letras, "rc": rc})
    info = {"piezas_x": px, "piezas_y": py, "ancho_mm": round(W, 1), "alto_mm": round(H, 1),
            "sin_lengueta": sin_lengueta, "lenguetas": n_lenguetas, "cap_mm": round(cap, 2), "lengueta": k}
    return piezas, info


def _limpiar(loop):
    out = []
    for q in loop:
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 1e-6:
            out.append(q)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    if _area(out) < 0:
        out.reverse()
    return out


# ===========================================================================
# 4. MALLAS 3D
# ===========================================================================
def prisma(ext, huecos, z0, z1, V, F):
    """Extruye un contorno CCW con huecos CW entre z0 y z1 (cerrado, normales afuera)."""
    loops = [ext] + list(huecos)
    abajo, arriba = [], []
    for L in loops:
        i0 = len(V)
        V.extend((x, y, z0) for x, y in L)
        abajo.append(list(range(i0, i0 + len(L))))
        i1 = len(V)
        V.extend((x, y, z1) for x, y in L)
        arriba.append(list(range(i1, i1 + len(L))))
    pts = [(x, y) for L in loops for x, y in L]
    off = [0]
    for L in loops:
        off.append(off[-1] + len(L))
    flat = lambda li: ([pts[off[li] + q] for q in range(len(loops[li]))], list(range(len(loops[li]))))
    tris = earcut(flat(0)[0], list(range(len(ext))),
                  [([(x, y) for x, y in loops[h]], list(range(off[h], off[h + 1])))
                   for h in range(1, len(loops))])
    idx_ab = [i for L in abajo for i in L]
    idx_ar = [i for L in arriba for i in L]
    for a, b, c in tris:
        A, B, C = pts[a], pts[b], pts[c]
        ccw = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]) > 0
        if not ccw:
            b, c = c, b
        F.append((idx_ar[a], idx_ar[b], idx_ar[c]))
        F.append((idx_ab[a], idx_ab[c], idx_ab[b]))
    for L_ab, L_ar in zip(abajo, arriba):
        n = len(L_ab)
        for q in range(n):
            q1 = (q + 1) % n
            F.append((L_ab[q], L_ab[q1], L_ar[q1]))
            F.append((L_ab[q], L_ar[q1], L_ar[q]))


def malla_pieza(pieza, p, cap):
    """Placa + letras en relieve (las letras entran 0,3 mm en la placa)."""
    Vp, Fp = [], []
    prisma(pieza["contorno"], [], 0.0, p["base"], Vp, Fp)
    Vl, Fl = [], []
    for ch, (x, y) in pieza["letras"]:
        res, _ = glifo(ch, cap)
        for ext, huecos in res:
            prisma([(x + a, y + b) for a, b in ext], [[(x + a, y + b) for a, b in h] for h in huecos],
                   p["base"] - 0.3, p["base"] + p["relieve"], Vl, Fl)
    return (Vp, Fp), (Vl, Fl)


def placa_lista(sopa, p, ancho):
    """Placa con la lista de palabras (letras en relieve), del ancho del tablero."""
    palabras = [u["palabra"] for u in sopa["ubicadas"]]
    if not palabras:
        return None
    cap = max(4.0, min(7.0, p["celda"] * 0.4))
    gap = cap * 0.9
    anchos = []
    for w in palabras:
        _, segs_w = eden_font.strokes(w, cap)[0], eden_font.strokes(w, cap)[1]
        anchos.append(segs_w + cap * 0.3)
    col_w = max(anchos) + 2 * gap
    ncol = max(1, int((ancho - 2 * p["margen"]) // col_w))
    nfil = int(math.ceil(len(palabras) / float(ncol)))
    alto = 2 * p["margen"] + nfil * (cap * 1.9)
    W = min(ancho, max(col_w * min(ncol, len(palabras)) + 2 * p["margen"], 60.0))
    Vp, Fp, Vl, Fl = [], [], [], []
    prisma([(0, 0), (W, 0), (W, alto), (0, alto)], [], 0.0, p["base"], Vp, Fp)
    for n, w in enumerate(palabras):
        cx = p["margen"] + (n % ncol) * col_w + col_w / 2.0
        cy = alto - p["margen"] - (n // ncol) * cap * 1.9 - cap * 0.95
        res = eden_font.outlines(w, cap, mirror=False)[0]
        for ext, huecos in res:
            prisma([(cx + a, cy + b) for a, b in ext], [[(cx + a, cy + b) for a, b in h] for h in huecos],
                   p["base"] - 0.3, p["base"] + p["relieve"], Vl, Fl)
    return {"nombre": "LISTA", "placa": (Vp, Fp), "letras": (Vl, Fl), "ancho_mm": round(W, 1),
            "alto_mm": round(alto, 1)}


# ===========================================================================
# 5. MARCADORES: un anillo por palabra que encastra alrededor de sus letras
# ===========================================================================
def centro_celda(sopa, p, r, c):
    cel, m = p["celda"], p["margen"]
    H = sopa["filas"] * cel + 2 * m
    return (m + c * cel + cel / 2.0, H - m - r * cel - cel / 2.0)


def _puntos_letra(sopa, p, cap, r, c):
    res, _ = glifo(sopa["grid"][r][c], cap)
    x, y = centro_celda(sopa, p, r, c)
    return [(x + a, y + b) for ext, _h in res for a, b in ext]


def _d_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def medir_marcador(sopa, p, cap, u):
    """Radio interior (las letras de la palabra adentro + ajuste para que agarre) y
    lugar libre hasta las letras vecinas. Devuelve dict con ri, libre y pared."""
    n = len(u["palabra"])
    celdas = [(u["fila"] + u["df"] * i, u["col"] + u["dc"] * i) for i in range(n)]
    A = centro_celda(sopa, p, *celdas[0])
    B = centro_celda(sopa, p, *celdas[-1])
    propias = set(celdas)
    dentro = 0.0
    for r, c in celdas:
        for x, y in _puntos_letra(sopa, p, cap, r, c):
            dentro = max(dentro, _d_seg(x, y, A[0], A[1], B[0], B[1]))
    ri = dentro + p["ajuste"]
    # letras vecinas: las de la caja que rodea a la palabra (más una celda)
    r0 = max(0, min(r for r, _ in celdas) - 2)
    r1 = min(sopa["filas"] - 1, max(r for r, _ in celdas) + 2)
    c0 = max(0, min(c for _, c in celdas) - 2)
    c1 = min(sopa["cols"] - 1, max(c for _, c in celdas) + 2)
    afuera = 1e9
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if (r, c) in propias:
                continue
            for x, y in _puntos_letra(sopa, p, cap, r, c):
                afuera = min(afuera, _d_seg(x, y, A[0], A[1], B[0], B[1]))
    pared = min(p["pared_marcador"], afuera - LUZ_VECINAS - ri)
    return {"A": A, "B": B, "ri": ri, "pared": pared, "celdas": celdas}


def _capsula(A, B, r, n=18):
    """Contorno CCW de una cápsula de radio r alrededor del segmento AB."""
    ang = math.atan2(B[1] - A[1], B[0] - A[0])
    pts = []
    for i in range(n + 1):                          # semicírculo en B
        a = ang - math.pi / 2 + math.pi * i / n
        pts.append((B[0] + r * math.cos(a), B[1] + r * math.sin(a)))
    for i in range(n + 1):                          # semicírculo en A
        a = ang + math.pi / 2 + math.pi * i / n
        pts.append((A[0] + r * math.cos(a), A[1] + r * math.sin(a)))
    return pts


def marcadores(sopa, p, cap):
    """Un marcador por palabra: anillo con forma de cápsula, apoyado en la base y
    1 mm más alto que las letras. Va puesto sobre la palabra (para la vista)."""
    out = []
    for k, u in enumerate(sopa["ubicadas"]):
        m = medir_marcador(sopa, p, cap, u)
        if m["pared"] <= 0.2:
            continue
        ext = _capsula(m["A"], m["B"], m["ri"] + m["pared"])
        hueco = list(reversed(_capsula(m["A"], m["B"], m["ri"])))
        V, F = [], []
        z0 = p["base"]
        prisma(ext, [hueco], z0, z0 + p["relieve"] + 1.0, V, F)
        out.append({"nombre": "M%d" % (k + 1), "palabra": u["palabra"], "malla": (V, F),
                    "A": m["A"], "B": m["B"],
                    "ri_mm": round(m["ri"], 2), "pared_mm": round(m["pared"], 2),
                    "largo_mm": round(math.hypot(m["B"][0] - m["A"][0], m["B"][1] - m["A"][1])
                                      + 2 * (m["ri"] + m["pared"]), 1),
                    "celdas": m["celdas"]})
    return out


def pared_minima_marcadores(sopa, p, cap):
    if not sopa["ubicadas"]:
        return 99.0
    return min(medir_marcador(sopa, p, cap, u)["pared"] for u in sopa["ubicadas"])


def mesh_volume(V, F):
    s = 0.0
    for a, b, c in F:
        ax, ay, az = V[a]
        bx, by, bz = V[b]
        cx, cy, cz = V[c]
        s += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return s / 6.0


def mesh_check(F):
    seen, dup = set(), 0
    for a, b, c in F:
        for e in ((a, b), (b, c), (c, a)):
            if e in seen:
                dup += 1
            seen.add(e)
    abiertas = sum(1 for (a, b) in seen if (b, a) not in seen)
    return {"closed": dup == 0 and abiertas == 0, "open_edges": abiertas, "bad_edges": dup}


def unir(*mallas):
    V, F = [], []
    for Vs, Fs in mallas:
        o = len(V)
        V.extend(Vs)
        F.extend((a + o, b + o, c + o) for a, b, c in Fs)
    return V, F


def _clamp(v, lo, hi, defecto):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return defecto
    return max(lo, min(hi, v))


def parametros(opts):
    o = dict(opts or {})
    p = dict(DEFAULTS)
    p["celda"] = _clamp(o.get("celda"), LIMITES["celda_min"], LIMITES["celda_max"], DEFAULTS["celda"])
    p["base"] = _clamp(o.get("base"), 1.6, 6.0, DEFAULTS["base"])
    p["relieve"] = _clamp(o.get("relieve"), 0.6, 3.0, DEFAULTS["relieve"])
    p["margen"] = _clamp(o.get("margen"), 3.0, 20.0, DEFAULTS["margen"])
    p["holgura"] = _clamp(o.get("holgura"), 0.0, 0.6, DEFAULTS["holgura"])
    p["cama"] = _clamp(o.get("cama"), LIMITES["cama_min"], LIMITES["cama_max"], DEFAULTS["cama"])
    p["letra"] = _clamp(o.get("letra"), 0.35, 0.6, DEFAULTS["letra"])
    p["lista"] = o.get("lista", True) is not False
    p["marcadores"] = o.get("marcadores", True) is not False
    p["ajuste"] = _clamp(o.get("ajuste"), 0.0, 0.5, DEFAULTS["ajuste"])
    p["letra_pedida"] = p["letra"]
    px, py = o.get("piezas_x"), o.get("piezas_y")
    p["piezas_x"] = int(px) if px and int(px) > 0 else None
    p["piezas_y"] = int(py) if py and int(py) > 0 else None
    return p


def build_sopa(opts=None):
    opts = dict(opts or {})
    p = parametros(opts)
    sopa = generar(opts.get("palabras") or [], opts.get("filas") or None, opts.get("cols") or None,
                   opts.get("dificultad") or "media", int(opts.get("semilla") or 1),
                   separadas=p["marcadores"])
    errores, avisos = [], []
    if not sopa["ubicadas"]:
        errores.append("Agregá al menos una palabra de 2 letras o más")
    if sopa["faltan"]:
        avisos.append("No entraron: %s. Agrandá la grilla o sacá palabras."
                      % ", ".join(sopa["faltan"]))
    if sopa["descartadas"]:
        avisos.append("Se ignoraron: %s" % ", ".join(sopa["descartadas"]))
    # con marcadores: si la pared del marcador no entra entre las letras (diagonales),
    # la letra se achica de a poco hasta que entre
    if p["marcadores"] and sopa["ubicadas"]:
        while p["letra"] > 0.30 and \
                pared_minima_marcadores(sopa, p, p["letra"] * p["celda"]) < PARED_MARCADOR_MIN:
            p["letra"] = round(p["letra"] - 0.02, 3)
        if p["letra"] < p["letra_pedida"] - 1e-9:
            avisos.append("Letra achicada a %.1f mm para que los marcadores entren entre las letras"
                          % (p["letra"] * p["celda"]))
    piezas_2d, info = armar_piezas(sopa, p)
    if info["sin_lengueta"]:
        avisos.append("%d borde(s) sin lengüeta: agrandá la celda o achicá la letra"
                      % info["sin_lengueta"])
    cap = info["cap_mm"]
    piezas = []
    vol = 0.0
    for pz in piezas_2d:
        placa, letras = malla_pieza(pz, p, cap)
        xs = [x for x, _ in pz["contorno"]]
        ys = [y for _, y in pz["contorno"]]
        v = mesh_volume(*placa) + mesh_volume(*letras)
        vol += v
        piezas.append({"nombre": pz["nombre"], "placa": placa, "letras": letras,
                       "celdas": [(ch, xy, rc) for (ch, xy), rc in zip(pz["letras"], pz["rc"])],
                       "contorno": pz["contorno"],
                       "medidas_mm": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)],
                       "volumen_cm3": round(v / 1000.0, 1)})
    if p["lista"] and sopa["ubicadas"]:
        pl = placa_lista(sopa, p, min(info["ancho_mm"], p["cama"] - 10.0))
        if pl:
            pl["medidas_mm"] = [pl["ancho_mm"], pl["alto_mm"]]
            v = mesh_volume(*pl["placa"]) + mesh_volume(*pl["letras"])
            pl["volumen_cm3"] = round(v / 1000.0, 1)
            vol += v
            piezas.append(pl)
    marcs = marcadores(sopa, p, cap) if p["marcadores"] else []
    for mk in marcs:
        vol += mesh_volume(*mk["malla"])
    if p["marcadores"] and len(marcs) < len(sopa["ubicadas"]):
        avisos.append("%d palabra(s) sin marcador: agrandá la celda"
                      % (len(sopa["ubicadas"]) - len(marcs)))
    if marcs and min(mk["pared_mm"] for mk in marcs) < PARED_MARCADOR_MIN:
        avisos.append("Marcadores con pared de %.1f mm: agrandá la celda"
                      % min(mk["pared_mm"] for mk in marcs))
    largos = [mk["largo_mm"] for mk in marcs if mk["largo_mm"] > p["cama"] - 5]
    if largos:
        avisos.append("Hay marcadores más largos que la cama (%.0f mm): ponelos en diagonal"
                      % max(largos))
    entra = all(max(pz["medidas_mm"]) <= p["cama"] - 5 for pz in piezas)
    if not entra:
        avisos.append("Alguna pieza no entra en una cama de %.0f mm" % p["cama"])
    cerradas = all(mesh_check(pz["placa"][1])["closed"] and mesh_check(pz["letras"][1])["closed"]
                   for pz in piezas) and all(mesh_check(mk["malla"][1])["closed"] for mk in marcs)
    n_tab = len([q for q in piezas if q["nombre"] != "LISTA"])
    rep = {
        "sku": "Sopa-%dx%d-%s" % (sopa["filas"], sopa["cols"], sopa["dificultad"].upper()),
        "valid": not errores, "errors": errores, "warnings": avisos,
        "filas": sopa["filas"], "cols": sopa["cols"], "palabras": len(sopa["ubicadas"]),
        "piezas": n_tab, "piezas_x": info["piezas_x"], "piezas_y": info["piezas_y"],
        "lenguetas": info["lenguetas"],
        "tablero_mm": [info["ancho_mm"], info["alto_mm"]], "celda_mm": p["celda"],
        "letra_mm": cap, "holgura_mm": p["holgura"], "cama_mm": p["cama"],
        "cambio_color_mm": p["base"], "peso_g": round(vol / 1000.0 * PLA_G_CM3, 0),
        "volumen_cm3": round(vol / 1000.0, 1), "cerradas": cerradas, "entra_en_cama": entra,
        "marcadores": len(marcs),
        "pared_marcador_mm": round(min([mk["pared_mm"] for mk in marcs] or [0.0]), 2),
        "ajuste_mm": p["ajuste"],
        "motor": SOPA_VERSION,
    }
    return {"piezas": piezas, "sopa": sopa, "report": rep, "params": p, "marcadores": marcs}
