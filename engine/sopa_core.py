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
5. Bloques para marcar: todos iguales, uno por letra (tantos como la palabra más
   larga). Cada bloque encastra en cualquier letra: agarra la letra por arriba y por
   abajo (todas miden lo mismo de alto). Se ponen sobre la palabra encontrada y se
   reusan; como son iguales, no delatan las palabras.

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
DEFAULTS = {"celda": 15.0, "base": 4.5, "relieve": 1.2, "margen": 6.0, "holgura": 0.2,
            "cama": 220.0, "letra": 0.45, "lista": True, "dificultad": "media",
            "bloques": True, "ajuste": 0.1}
PARED_BLOQUE = 1.4           # mm
LUZ_LATERAL = 0.4            # mm a cada costado de la letra más ancha (no aprieta)
LUZ_VECINAS = 0.3            # mm entre el bloque y las letras de al lado


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


def generar(palabras, filas=None, cols=None, dificultad="media", semilla=1):
    """Ubica las palabras (las más largas primero; prefiere cruces) y rellena."""
    palabras, descartadas = limpiar_palabras(palabras)
    n = tamano_auto(palabras)
    filas = int(filas or n)
    cols = int(cols or n)
    filas = max(LIMITES["grilla_min"], min(LIMITES["grilla_max"], filas))
    cols = max(LIMITES["grilla_min"], min(LIMITES["grilla_max"], cols))
    dirs = DIRECCIONES.get(dificultad, DIRECCIONES["media"])
    rnd = random.Random(semilla)
    mejor = None
    for intento in range(12):              # varios intentos: se queda con el más completo
        grid = [[None] * cols for _ in range(filas)]
        ubicadas, faltan = [], []
        for w in sorted(palabras, key=lambda x: (-len(x), x)):
            opciones = []
            for dr, dc in dirs:
                for r in range(filas):
                    for c in range(cols):
                        k = _cabe(grid, w, r, c, dr, dc)
                        if k < 0:
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
            "semilla": semilla}


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


def _glifo_crudo(ch, cap):
    res = eden_font.outlines(ch, cap, mirror=False)[0]
    ys = [y for e, _ in res for _, y in e]
    return res, min(ys), max(ys)


def glifo(ch, cap):
    """Contornos de una letra centrada en (0,0): [(exterior CCW, [contraformas CW])]
    y la caja (xmin, ymin, xmax, ymax). Todas las letras del tablero miden lo mismo de
    alto (la de la H): la Ñ y la Q se aplastan un poco para que el tilde y la cola no
    sobresalgan. Así un mismo bloque agarra cualquier letra por arriba y por abajo."""
    key = (ch, round(cap, 3))
    if key not in _GLIFO:
        res, y0, y1 = _glifo_crudo(ch, cap)
        _, h0, h1 = _glifo_crudo("H", cap)
        if abs(y0 - h0) > 1e-4 or abs(y1 - h1) > 1e-4:     # misma altura que la H, exacta
            k = (h1 - h0) / (y1 - y0)
            f = lambda pts: [(x, h0 + (y - y0) * k) for x, y in pts]
            res = [(f(e), [f(h) for h in hs]) for e, hs in res]
        xs = [x for e, _ in res for x, _ in e]
        dx = -(min(xs) + max(xs)) / 2.0          # centrada por la tinta, no por el avance
        dy = -(h0 + h1) / 2.0                    # y en alto (todas con la altura de la H)
        g = lambda pts: [(x + dx, y + dy) for x, y in pts]
        res = [(g(e), [g(h) for h in hs]) for e, hs in res]
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
    del lado que la recibe). k = dict con cuello, cabeza, profundidad y filete.
    El cuello arranca con filetes redondeados (sin esquinas vivas que se quiebren)."""
    a = k["cuello"] + e                     # medio ancho del cuello
    R = k["cabeza"] + e                     # radio de la cabeza
    vc = k["prof"] - k["cabeza"]            # centro de la cabeza (fijo)
    v0 = e                                  # línea de corte corrida
    f = max(0.0, k.get("filete", 0.0) - e)  # filete en la base del cuello
    vn = vc - math.sqrt(max(R * R - a * a, 1e-9))
    ang0 = math.atan2(vn - vc, a)           # derecha del cuello (abajo de la cabeza)
    ang1 = math.pi - ang0                   # izquierda
    if f > 1e-6:
        # cuarto de círculo cóncavo: de la línea de corte (u0+a+f, v0) al cuello (u0+a, v0+f)
        pts = _arco(u0 + a + f, v0 + f, f, -math.pi / 2, -math.pi, 6)
    else:
        pts = [(u0 + a, v0)]
    pts += [(u0 + a, vn)]
    arco = _arco(u0, vc, R, ang0, ang1 + (2 * math.pi if ang1 < ang0 else 0), 26)
    pts += arco[1:-1]
    pts += [(u0 - a, vn)]
    if f > 1e-6:
        pts += _arco(u0 - a - f, v0 + f, f, 0.0, -math.pi / 2, 6)
    else:
        pts += [(u0 - a, v0)]
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
    # Lengüeta robusta: la más grande que entra entre las letras (con 0,4 mm de aire),
    # cabeza 1,5 veces el cuello (traba) y filetes en la base del cuello. Se calcula
    # aparte para cortes verticales (la lengüeta va entre letras de arriba y abajo) y
    # horizontales (entre letras de izquierda y derecha).
    anchos = [glifo(ch, cap)[1] for ch in set(c for fila in sopa["grid"] for c in fila)]
    w_max = max(b[2] - b[0] for b in anchos)
    h_max = max(b[3] - b[1] for b in anchos)

    def medida(libre):
        R = max(0.12 * cel, min(0.25 * cel, libre / 2.0 - t - 0.4))
        return {"cabeza": R, "cuello": R / 1.55, "prof": 2.0 * R + 0.22 * cel, "filete": 0.6 * R / 1.55}
    k_v = medida(cel - h_max - 0.6)          # corte vertical: lugar entre letras en y
    k_h = medida(cel - w_max - 0.6)          # corte horizontal: lugar entre letras en x
    k = k_v
    rnd = random.Random(1000 + int(sopa.get("semilla") or 0))

    def lengueta_en(i0, i1, fijo, vertical):
        k = k_v if vertical else k_h
        """Lengüetas de un borde interno entre las celdas i0..i1 a lo largo del corte:
        una cada ~3 celdas, alternando el lado, donde haya lugar entre las letras (se
        busca cada 0,5 mm a lo largo del corte, no sólo en el borde de las celdas).
        Devuelve [(u, signo)]; signo + = hacia +x (vertical) o hacia abajo (horizontal)."""
        ext = k["prof"] + t
        ancho = max(k["cabeza"], k["cuello"] + k["filete"]) + t
        lo = (Y(i1) if vertical else X(i0)) + ancho + 0.5
        hi = (Y(i0) if vertical else X(i1)) - ancho - 0.5
        validas = []
        u = lo
        while u <= hi + 1e-9:
            # celdas a los dos lados del corte que la lengüeta puede tocar
            b0 = int(((Y(i0) - u) if vertical else (u - X(i0))) // cel) + i0
            for s in (1, -1):
                if vertical:
                    xs = (X(fijo), X(fijo) + ext) if s > 0 else (X(fijo) - ext, X(fijo))
                    rect = (xs[0], u - ancho, xs[1], u + ancho)
                    vecinas = [(b, c) for b in (b0 - 1, b0, b0 + 1) for c in (fijo, fijo - 1)]
                else:
                    ys = (Y(fijo) - ext, Y(fijo)) if s > 0 else (Y(fijo), Y(fijo) + ext)
                    rect = (u - ancho, ys[0], u + ancho, ys[1])
                    vecinas = [(r, b) for b in (b0 - 1, b0, b0 + 1) for r in (fijo, fijo - 1)]
                if not _choca(rect, [caja_letra[q] for q in vecinas if q in caja_letra]):
                    validas.append((u, s))
            u += 0.5
        n = max(1, int(round((i1 - i0) / 3.0)))
        largo = (i1 - i0) * cel
        elegidas = []
        primero = 1 if rnd.random() < 0.5 else -1
        u_ini = Y(i0) if vertical else X(i0)
        for q in range(n):
            meta = u_ini + (-1 if vertical else 1) * largo * (q + 0.5) / n
            quiero = primero if q % 2 == 0 else -primero
            libres = [(uu, ss) for uu, ss in validas
                      if all(abs(uu - x) >= 2 * ancho + cel for x, _ in elegidas)]
            if not libres:
                break
            uu, ss = min(libres, key=lambda c: (abs(c[0] - meta) + (0 if c[1] == quiero else cel * 0.6), c[0]))
            elegidas.append((uu, ss))
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
        kk = k_v if eje == "x" else k_h
        for u0, duenio in tabs or []:
            prof = lengueta(u0, -t / 2.0, kk) if duenio else lengueta(u0, t / 2.0, kk)
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
            "sin_lengueta": sin_lengueta, "lenguetas": n_lenguetas, "cap_mm": round(cap, 2), "lengueta": min((k_v, k_h), key=lambda q: q["cuello"]),
            "lengueta_v": k_v, "lengueta_h": k_h}
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


# 5. BLOQUES: uno por letra, iguales, que encastran en cualquier letra
# ===========================================================================
def centro_celda(sopa, p, r, c):
    cel, m = p["celda"], p["margen"]
    H = sopa["filas"] * cel + 2 * m
    return (m + c * cel + cel / 2.0, H - m - r * cel - cel / 2.0)


def _puntos_letra(sopa, p, cap, r, c):
    res, _ = glifo(sopa["grid"][r][c], cap)
    x, y = centro_celda(sopa, p, r, c)
    return [(x + a, y + b) for ext, _h in res for a, b in ext]


def _rect_redondeado(w, h, r, n=6):
    """Contorno CCW de un rectángulo w × h centrado en el origen, esquinas de radio r."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def medidas_bloque(p, cap):
    """Hueco del bloque: tan alto como las letras + el ajuste arriba y abajo (agarra)
    y tan ancho como la letra más ancha + una luz a cada costado."""
    w = h = 0.0
    for ch in ALFABETO:
        _, (x0, y0, x1, y1) = glifo(ch, cap)
        w, h = max(w, x1 - x0), max(h, y1 - y0)
    iw = w + 2 * LUZ_LATERAL
    ih = h + 2 * p["ajuste"]
    return {"hueco": (iw, ih), "afuera": (iw + 2 * PARED_BLOQUE, ih + 2 * PARED_BLOQUE),
            "pared": PARED_BLOQUE, "alto_letra": h, "ancho_letra": w}


def malla_bloque(p, cap, z0=0.0):
    """El bloque centrado en el origen: marco redondeado, 1 mm más alto que las letras."""
    m = medidas_bloque(p, cap)
    (iw, ih), (ow, oh) = m["hueco"], m["afuera"]
    ext = _rect_redondeado(ow, oh, 0.6 + PARED_BLOQUE)
    hueco = list(reversed(_rect_redondeado(iw, ih, 0.6)))
    V, F = [], []
    prisma(ext, [hueco], z0, z0 + p["relieve"] + 1.0, V, F)
    return V, F


def bloques_necesarios(sopa):
    return max([len(u["palabra"]) for u in sopa["ubicadas"]] or [0])


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
    p["base"] = _clamp(o.get("base"), 3.0, 6.0, DEFAULTS["base"])   # < 3 mm las lengüetas se quiebran
    p["relieve"] = _clamp(o.get("relieve"), 0.6, 3.0, DEFAULTS["relieve"])
    p["margen"] = _clamp(o.get("margen"), 3.0, 20.0, DEFAULTS["margen"])
    p["holgura"] = _clamp(o.get("holgura"), 0.0, 0.6, DEFAULTS["holgura"])
    p["cama"] = _clamp(o.get("cama"), LIMITES["cama_min"], LIMITES["cama_max"], DEFAULTS["cama"])
    p["letra"] = _clamp(o.get("letra"), 0.35, 0.6, DEFAULTS["letra"])
    p["lista"] = o.get("lista", True) is not False
    p["bloques"] = o.get("bloques", o.get("marcadores", True)) is not False
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
                   opts.get("dificultad") or "media", int(opts.get("semilla") or 1))
    errores, avisos = [], []
    if not sopa["ubicadas"]:
        errores.append("Agregá al menos una palabra de 2 letras o más")
    if sopa["faltan"]:
        avisos.append("No entraron: %s. Agrandá la grilla o sacá palabras."
                      % ", ".join(sopa["faltan"]))
    if sopa["descartadas"]:
        avisos.append("Se ignoraron: %s" % ", ".join(sopa["descartadas"]))
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
    bloque = None
    n_bloques = bloques_necesarios(sopa) if p["bloques"] else 0
    if n_bloques:
        mb = medidas_bloque(p, cap)
        bloque = malla_bloque(p, cap)
        vol += mesh_volume(*bloque) * n_bloques
        if max(mb["afuera"]) > p["celda"] - 1.0:
            avisos.append("El bloque (%.1f × %.1f mm) casi no entra en la celda: achicá la letra"
                          % mb["afuera"])
    entra = all(max(pz["medidas_mm"]) <= p["cama"] - 5 for pz in piezas)
    if not entra:
        avisos.append("Alguna pieza no entra en una cama de %.0f mm" % p["cama"])
    cerradas = all(mesh_check(pz["placa"][1])["closed"] and mesh_check(pz["letras"][1])["closed"]
                   for pz in piezas) and (bloque is None or mesh_check(bloque[1])["closed"])
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
        "bloques": n_bloques,
        "bloque_mm": [round(x, 2) for x in medidas_bloque(p, cap)["afuera"]] if n_bloques else None,
        "hueco_bloque_mm": [round(x, 2) for x in medidas_bloque(p, cap)["hueco"]] if n_bloques else None,
        "ajuste_mm": p["ajuste"],
        "motor": SOPA_VERSION,
    }
    return {"piezas": piezas, "sopa": sopa, "report": rep, "params": p, "bloque": bloque}
