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
DEFECTO = {"lineas": [{"texto": "Feliz", "fuente": "great_vibes", "escala": 1.0},
                      {"texto": "Cumpleaños", "fuente": "great_vibes", "escala": 1.0}],
           "ancho": 140.0, "contorno": 0.8, "grosor": 3.0, "letras": 1.2, "estilo": "simple",
           "marco": "ninguno", "palitos": 2, "largo": 90.0, "calidad": "preview"}
LIMITES = {"ancho": (60.0, 220.0), "contorno": (0.0, 6.0), "grosor": (2.0, 5.0),
           "letras": (0.6, 3.0), "palitos": (1, 2), "largo": (40.0, 140.0), "escala": (0.4, 1.6),
           "lineas": 3, "caracteres": 24}
ANCHO_PALITO = 5.0
PUENTE = 2.4            # mm de ancho de los puentes que unen lo que quedó suelto
SOLAPE = 0.30           # encimado de una línea con la de arriba si no hay perfil (de su alto)
ENCIMADO = 0.0          # fracción de las columnas comunes en las que las líneas se cruzan
PENETRA = 1.0           # mm extra que se enciman donde se tocan
CIERRE = 0.8            # mm: cierra las luces entre letras sin engordarlas
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


def maquetar(lineas, ancho, por_linea=False):
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
    out, info, grupos = [], [], []
    abajo_prev, alto_prev, prev = None, None, None
    for n, r in enumerate(ls):
        x0, y0, x1, y1 = r["bbox"]
        s = k * r["escala"]
        cx = (x0 + x1) / 2.0
        alto = (y1 - y0) * s
        dy = -y1 * s
        propios = [[((px - cx) * s, py * s + dy) for px, py in P] for P in r["polys"]]
        if n:
            # se apoya en la de arriba: se sube hasta que se enciman las letras que se
            # cruzan (las colas y los palos altos), no las panzas de las letras
            y = abajo_prev + _subir(prev, propios, abajo_prev, min(alto, alto_prev))
            propios = [[(px, py + y) for px, py in P] for P in propios]
            dy += y
        out.extend(propios)
        grupos.append(propios)
        info.append({"texto": r["texto"], "fuente": r["fuente"], "alto_mm": round(alto, 1),
                     "ancho_mm": round((x1 - x0) * s, 1)})
        abajo_prev, alto_prev, prev = y0 * s + dy, alto, propios
    pts = [p for P in out for p in P]
    ymid = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2.0
    out = [[(x, yy - ymid) for x, yy in P] for P in out]
    pts = [p for P in out for p in P]
    caja = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    if por_linea:
        grupos = [[[(x, yy - ymid) for x, yy in P] for P in G] for G in grupos]
        return out, info, caja, grupos
    return out, info, caja


def _perfiles(polys, r=0.5):
    """Por columna de r mm (alineadas en x = 0): (x de la columna, y más bajo, y más alto)."""
    xs = [p[0] for P in polys for p in P]
    ys = [p[1] for P in polys for p in P]
    i0 = int(math.floor(min(xs) / r)) - 1
    g = Grilla(i0 * r, min(ys) - r, max(xs) + r, max(ys) + r, r)
    M = g.llenar(polys)
    out = {}
    for i in range(g.nx):
        js = [j for j in range(g.ny) if M[j][i]]
        if js:
            out[i0 + i] = (g.y0 + js[0] * r, g.y0 + (js[-1] + 1) * r)
    return out


def _subir(arriba, abajo, y_tope, alto_min):
    """Cuánto subir la línea `abajo` (con su techo en y = 0) por encima de `y_tope` (el piso
    de la de arriba) para que se enciman sólo las letras que se cruzan: el ENCIMADO % de
    las columnas comunes se toca, más PENETRA mm; nunca más de la mitad del alto."""
    pa, pb = _perfiles(arriba), _perfiles(abajo)
    luces = sorted(pa[c][0] - (pb[c][1] + y_tope) for c in pa if c in pb)
    if not luces:
        return SOLAPE * alto_min
    k = luces[min(len(luces) - 1, int(ENCIMADO * len(luces)))]
    return max(0.4, min(0.5 * alto_min, k + PENETRA))


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


APOYOS_MIN = 2           # puntos de apoyo entre una línea y la de abajo
APOYO_ANCHO = 3.0        # mm de cada pilar entre líneas


def _contactos(arriba, abajo, g, i0, i1):
    """Columnas (i0..i1) donde la línea de arriba toca a la de abajo, agrupadas en tramos;
    y por columna la luz (mm) entre las dos (0 si se tocan, None si alguna no tiene nada)."""
    luz = []
    for i in range(i0, i1 + 1):
        ja = next((j for j in range(g.ny) if arriba[j][i]), None)        # lo más bajo de arriba
        jb = next((j for j in range(g.ny - 1, -1, -1) if abajo[j][i]), None)  # lo más alto de abajo
        if ja is None or jb is None:
            luz.append(None)
        else:
            luz.append(max(0.0, (ja - jb - 1) * g.res))
    tramos, t0 = [], None
    for k, d in enumerate(luz + [None]):
        if d == 0.0 and t0 is None:
            t0 = k
        elif d != 0.0 and t0 is not None:
            tramos.append((i0 + t0, i0 + k - 1))
            t0 = None
    return tramos, luz


def reforzar_lineas(M, g, lineas):
    """Entre cada línea y la de abajo deja al menos APOYOS_MIN apoyos separados (tramos
    de contacto de 1 mm o más, o pilares nuevos en las columnas de menos luz)."""
    out = []
    minimo = max(1, int(round(1.0 / g.res)))
    for n in range(len(lineas) - 1):
        A, B = lineas[n], lineas[n + 1]
        colA = [i for i in range(g.nx) if any(A[j][i] for j in range(g.ny))]
        colB = [i for i in range(g.nx) if any(B[j][i] for j in range(g.ny))]
        if not colA or not colB:
            continue
        i0, i1 = max(colA[0], colB[0]), min(colA[-1], colB[-1])
        if i1 - i0 < 4:
            continue
        tramos, luz = _contactos(A, B, g, i0, i1)
        buenos = [t for t in tramos if t[1] - t[0] + 1 >= minimo]
        agregados = 0
        # se quiere un apoyo en cada tercio del ancho común; donde no hay, un pilar
        ancho = i1 - i0
        for frac in ((0.25, 0.75) if len(buenos) < APOYOS_MIN else ()):
            c = i0 + int(frac * ancho)
            if any(t[0] - 0.12 * ancho <= c <= t[1] + 0.12 * ancho for t in buenos):
                continue
            ventana = range(max(i0, c - int(0.15 * ancho)), min(i1, c + int(0.15 * ancho)) + 1)
            cand = [(luz[i - i0], abs(i - c), i) for i in ventana if luz[i - i0] is not None]
            if not cand:
                continue
            d, _, i = min(cand)
            if d > 0.0:
                ja = next(j for j in range(g.ny) if A[j][i])
                jb = next(j for j in range(g.ny - 1, -1, -1) if B[j][i])
                x = g.x0 + (i + 0.5) * g.res
                capsula(M, g, (x, g.y0 + (jb - 1.5) * g.res), (x, g.y0 + (ja + 2.5) * g.res), APOYO_ANCHO)
                agregados += 1
                buenos.append((i, i))
        comun_mm = (i1 - i0 + 1) * g.res
        ancho_max = max([(t[1] - t[0] + 1) * g.res for t in tramos if t[1] - t[0] + 1 >= minimo] or [0.0])
        out.append({"lineas": [n + 1, n + 2], "contactos": len([t for t in tramos if t[1] - t[0] + 1 >= minimo]),
                    "agregados": agregados, "apoyos": len(buenos), "contacto_max_mm": round(ancho_max, 1),
                    "ancho_comun_mm": round(comun_mm, 1)})
    return out


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
        # piezas de más de 6 mm: un segundo apoyo, lejos del primero
        celdas = [(ii, jj) for jj in range(g.ny) for ii in range(g.nx) if L[jj][ii] == k]
        ext = max(max(c[0] for c in celdas) - min(c[0] for c in celdas),
                  max(c[1] for c in celdas) - min(c[1] for c in celdas)) * g.res
        if ext >= 6.0:
            sep = max(6.0, 0.35 * ext) / g.res
            otro = None
            for ii, jj in celdas:
                if (ii - i) ** 2 + (jj - j) ** 2 >= sep * sep:
                    d = D[jj][ii]
                    if otro is None or d < otro[0]:
                        otro = (d, ii, jj)
            if otro and math.sqrt(otro[0]) * g.res <= 3 * math.sqrt(mejor[0]) * g.res + 4.0:
                d2, ii, jj = otro
                rad = int(math.sqrt(d2)) + 2
                dest = None
                for y_ in range(max(0, jj - rad), min(g.ny, jj + rad + 1)):
                    for x_ in range(max(0, ii - rad), min(g.nx, ii + rad + 1)):
                        if L[y_][x_] in hechas:
                            dd = (x_ - ii) ** 2 + (y_ - jj) ** 2
                            if dest is None or dd < dest[0]:
                                dest = (dd, x_, y_)
                if dest:
                    a2 = (g.x0 + (ii + 0.5) * g.res, g.y0 + (jj + 0.5) * g.res)
                    b2 = (g.x0 + (dest[1] + 0.5) * g.res, g.y0 + (dest[2] + 0.5) * g.res)
                    dx, dy = b2[0] - a2[0], b2[1] - a2[1]
                    Ld = math.hypot(dx, dy) or 1.0
                    capsula(M, g, (a2[0] - dx / Ld, a2[1] - dy / Ld), (b2[0] + dx / Ld, b2[1] + dy / Ld), PUENTE)
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
# HUECOS DE LAS LETRAS (la panza de la a, el ojo de la e): el contorno no los tapa
# ===========================================================================
def afuera(M, g):
    """1 en el fondo que llega al borde de la grilla (4 vecinos); el resto del fondo son
    huecos encerrados por las letras."""
    nx, ny = g.nx, g.ny
    A = [bytearray(nx) for _ in range(ny)]
    pila = []
    for i in range(nx):
        for j in (0, ny - 1):
            if not M[j][i] and not A[j][i]:
                A[j][i] = 1
                pila.append((i, j))
    for j in range(ny):
        for i in (0, nx - 1):
            if not M[j][i] and not A[j][i]:
                A[j][i] = 1
                pila.append((i, j))
    while pila:
        i, j = pila.pop()
        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < nx and 0 <= b < ny and not A[b][a] and not M[b][a]:
                A[b][a] = 1
                pila.append((a, b))
    return A


def engordar(T, g, c, cierre=CIERRE, A=None):
    """Contorno de c mm alrededor de las letras: cierra primero las luces entre letras
    (cierre morfológico) para unirlas sin engordarlas de más; los huecos de las letras
    quedan abiertos."""
    if c <= 0:
        return [bytearray(f) for f in T]
    r = g.res
    D = edt(T, g.nx, g.ny, 1)
    lim = ((c + cierre) / r + 0.5) ** 2
    G = [bytearray(1 if D[j][i] <= lim else 0 for i in range(g.nx)) for j in range(g.ny)]
    E = edt(G, g.nx, g.ny, 0)                   # se le saca el cierre de vuelta
    lim2 = (cierre / r) ** 2
    A = afuera(T, g) if A is None else A
    S = [bytearray(1 if (T[j][i] or (E[j][i] > lim2 and A[j][i])) else 0 for i in range(g.nx))
         for j in range(g.ny)]
    return S


def huecos_abiertos(T, S, g, A=None):
    """Cuántos huecos de las letras (de 0,5 mm² o más) siguen abiertos en la pieza S, y
    cuántos hay."""
    A = afuera(T, g) if A is None else A
    H = [bytearray(1 if (not T[j][i] and not A[j][i]) else 0 for i in range(g.nx)) for j in range(g.ny)]
    L, n, tam = componentes(H, g.nx, g.ny)
    minimo = 0.5 / (g.res * g.res)
    total = abiertos = 0
    vistos = set()
    for j in range(g.ny):
        for i in range(g.nx):
            k = L[j][i]
            if k and k not in vistos:
                vistos.add(k)
                if tam[k] >= minimo:
                    total += 1
    abiertos_k = set()
    for j in range(g.ny):
        for i in range(g.nx):
            k = L[j][i]
            if k and tam[k] >= minimo and not S[j][i]:
                abiertos_k.add(k)
    abiertos = len(abiertos_k)
    return abiertos, total


# ===========================================================================
# TODO JUNTO
# ===========================================================================
COLORES = [("simple", "Un color"),
           ("doble", "Dos colores · dos alturas (cambio de filamento a mano)"),
           ("ams", "Dos colores · misma altura (AMS / multicolor)")]
ESTILOS = COLORES
ESTILOS_NUM = [("lleno", "Solo el número"), ("estrellas", "Con estrellas"),
               ("corazones", "Con corazones"), ("corona", "Con corona"), ("anios", "Con «años»")]
DEFECTO_NUM = {"numero": "1", "fuente": "luckiest_guy", "estilo": "estrellas", "alto": 60.0,
               "palitos": 1}
LIMITES_NUM = {"alto": (30.0, 120.0), "cifras": 3}


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
    _comunes(o)
    if o.get("marco") not in [m for m, _ in MARCOS]:
        raise ValueError("marco desconocido: %s" % o.get("marco"))
    return o


def _comunes(o):
    for k in ("ancho", "contorno", "grosor", "letras", "largo"):
        o[k] = _f(o.get(k), DEFECTO[k], *LIMITES[k])
    o["palitos"] = int(_f(o.get("palitos"), 2, *LIMITES["palitos"]))
    if o.get("estilo") not in [e for e, _ in COLORES]:
        raise ValueError("estilo desconocido: %s" % o.get("estilo"))
    if o["estilo"] != "simple":
        o["contorno"] = max(o["contorno"], 2.0)     # la base tiene que asomar alrededor
    if o["estilo"] == "ams":                        # las letras de color: las últimas capas
        o["letras"] = min(o["letras"], o["grosor"] - 0.8)
    o["calidad"] = o.get("calidad") if o.get("calidad") in ("preview", "normal") else "preview"


def opciones_numero(opts):
    """El número de años: lo propio en opts["numero"]; contorno, grosor, colores y largo
    de los palitos, los del topper."""
    base = dict(DEFECTO, **(opts or {}))
    n = dict(DEFECTO_NUM, **(base.get("numero") or {}))
    o = {k: base.get(k) for k in ("contorno", "grosor", "letras", "largo", "estilo", "calidad", "ancho")}
    o["lineas"] = []
    txt = "".join(str(n.get("numero") or "").split())
    if not txt.isdigit() or not 1 <= len(txt) <= LIMITES_NUM["cifras"]:
        raise ValueError("Poné los años con números (1 a %d cifras)" % LIMITES_NUM["cifras"])
    o["numero"] = txt
    if n.get("fuente") not in IDS:
        raise ValueError("Tipografía desconocida: %s" % n.get("fuente"))
    o["fuente"] = n["fuente"]
    if n.get("estilo") not in [e for e, _ in ESTILOS_NUM]:
        raise ValueError("estilo de número desconocido: %s" % n.get("estilo"))
    o["deco"] = n["estilo"]
    o["alto"] = _f(n.get("alto"), DEFECTO_NUM["alto"], *LIMITES_NUM["alto"])
    o["palitos"] = n.get("palitos", 1)
    _comunes(o)
    return o


def _pieza(polys, grupos, mpoly, o, ext, nombres=("TOPPER", "LETRAS")):
    """Lo común del topper y del número: grilla, contorno (sin tapar los huecos), marco,
    apoyos entre líneas, puentes, contornos suaves, palitos y las partes de color."""
    res = 0.32 if o["calidad"] == "preview" else 0.2
    pad = o["contorno"] + CIERRE + MARCO_ANCHO + 3.0
    g = Grilla(ext[0] - pad, ext[1] - pad, ext[2] + pad, ext[3] + pad, res)
    T = g.llenar(polys)
    fondo = afuera(T, g)
    S = engordar(T, g, o["contorno"], A=fondo)
    if mpoly:
        A = g.llenar([mpoly])
        Da = edt(A, g.nx, g.ny, 1)
        lim = (MARCO_ANCHO / res + 0.5) ** 2
        for j in range(g.ny):
            Sj, Aj, Dj = S[j], A[j], Da[j]
            for i in range(g.nx):
                if not Aj[i] and Dj[i] <= lim:
                    Sj[i] = 1
    # cada línea con la de abajo: al menos dos apoyos separados (no un solo puntito)
    lineas_m = []
    if len(grupos) > 1:
        for G in grupos:
            Li = g.llenar(G)
            if o["contorno"] > 0:
                Dl = edt(Li, g.nx, g.ny, 1)
                lim = (o["contorno"] / res + 0.5) ** 2
                Li = [bytearray(1 if Dl[j][i] <= lim else 0 for i in range(g.nx)) for j in range(g.ny)]
            lineas_m.append(Li)
    apoyos = reforzar_lineas(S, g, lineas_m)
    puentes = unir(S, g)
    f = campo(S, g)
    eps = 0.05 if o["calidad"] == "normal" else 0.09
    lz = [_simplificar(P, eps) for P in lazos(f, g)]
    lz = [P for P in lz if abs(_area(P)) > 0.3]
    z1 = o["grosor"]
    ams = o["estilo"] == "ams"
    zc = z1 - o["letras"] if ams else z1           # hasta dónde va la base entera
    Vb, Fb = extruir(lz, 0.0, zc)
    palos = _palitos(S, g, o, ext)
    for p in palos:
        V, F = palito(p["x"], p["arriba"], p["arriba"] - p["punta"], ANCHO_PALITO, 0.0, z1)
        p.pop("_", None)
        off = len(Vb)
        Vb.extend(V)
        Fb.extend((a + off, b + off, c + off) for a, b, c in F)
    piezas = []
    if o["estilo"] != "simple":
        fl = campo(T, g)
        ll = [_simplificar(P, eps) for P in lazos(fl, g)]
        ll = [P for P in ll if abs(_area(P)) > 0.2]
        if ams:
            # el borde (la base sin las letras) completa las últimas capas, al ras de las
            # letras: su distancia firmada es min(adentro de la pieza, afuera de las letras),
            # así el borde de cada letra cae justo donde el de la parte de las letras
            fr = [[min(a, -b) for a, b in zip(fa, fb)] for fa, fb in zip(f, fl)]
            lr = [_simplificar(P, eps) for P in lazos(fr, g)]
            lr = [P for P in lr if abs(_area(P)) > 0.2]
            Vr, Fr = extruir(lr, zc - 0.01, z1)
            off = len(Vb)
            Vb.extend(Vr)
            Fb.extend((a + off, b + off, c + off) for a, b, c in Fr)
            Vl, Fl = extruir(ll, zc, z1)
        else:
            Vl, Fl = extruir(ll, z1 - 0.01, z1 + o["letras"])
        piezas = [(nombres[0], Vb, Fb), (nombres[1], Vl, Fl)]
    else:
        piezas = [(nombres[0], Vb, Fb)]
    xs_ = [v[0] for _, V, _ in piezas for v in V]
    ys_ = [v[1] for _, V, _ in piezas for v in V]
    zs_ = [v[2] for _, V, _ in piezas for v in V]
    abiertos, huecos = huecos_abiertos(T, S, g, fondo)
    rep = {"estilo": o["estilo"], "palitos": len(palos),
           "puentes": puentes + sum(a["agregados"] for a in apoyos),
           "apoyos": apoyos, "contorno_mm": o["contorno"], "grosor_mm": z1,
           "letras_mm": o["letras"] if o["estilo"] != "simple" else 0.0,
           "cambio_mm": round(z1, 2) if o["estilo"] == "doble" else None,
           "capa_color_mm": round(o["letras"], 2) if ams else None,
           "huecos": huecos, "huecos_abiertos": abiertos,
           "medidas_mm": [round(max(xs_) - min(xs_), 1), round(max(ys_) - min(ys_), 1),
                          round(max(zs_) - min(zs_), 2)],
           "triangulos": sum(len(F) for _, _, F in piezas), "res_mm": res, "palos": palos}
    return {"piezas": piezas, "reporte": rep, "grilla": g, "region": S, "letras": T}


def _palitos(S, g, o, ext):
    """Los palitos bajan todos hasta la misma punta: `largo` mm por debajo de lo más bajo
    de la pieza. Se clavan en material macizo cerca de abajo (en un corazón, cerca de la
    punta; no en los costados, que quedan altos)."""
    res = g.res
    jmin = next(j for j in range(g.ny) if any(S[j]))
    jmax = max(j for j in range(g.ny) if any(S[j]))
    ymin = g.y0 + jmin * res
    tope = max(8.0, 0.2 * (jmax - jmin) * res)       # cuánto más arriba puede arrancar uno
    cols = [i for i in range(g.nx) if any(S[j][i] for j in range(g.ny))]
    W = (cols[-1] - cols[0]) * res
    centro = g.x0 + (cols[0] + cols[-1] + 1) * 0.5 * res
    n = int(o["palitos"])
    xs = [centro] if n == 1 else [centro - 0.3 * W, centro + 0.3 * W]
    out = []
    for x in xs:
        elegido = None
        for _ in range(14):
            i0 = int((x - g.x0) / res)
            mejor = None
            for i in range(max(0, i0 - int(8 / res)), min(g.nx, i0 + int(8 / res) + 1)):
                j = next((jj for jj in range(jmin, g.ny) if S[jj][i]), None)
                if j is None or (j - jmin) * res > tope:
                    continue
                run = 0
                while j + run < g.ny and S[j + run][i]:
                    run += 1
                maciza = min(run * res, 6.0)
                clave = (-round(maciza, 1), abs(i - i0))
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, i, j, maciza)
            if mejor and mejor[3] >= 1.6:
                elegido = mejor
                break
            elegido = elegido or mejor
            x = centro + (x - centro) * 0.82        # más cerca del centro (la punta del corazón)
        if elegido is None:
            raise ValueError("No encontré dónde clavar el palito")
        _, i, j, maciza = elegido
        x = g.x0 + (i + 0.5) * res
        y_low = g.y0 + j * res + 0.1
        meter = max(1.0, maciza - 0.4)
        out.append({"x": round(x, 3), "arriba": round(y_low + meter, 3),
                    "punta": round(ymin - o["largo"], 3), "adentro_mm": round(meter, 2),
                    "desde_abajo_mm": round(y_low - ymin, 2)})
    return out


def construir(opts):
    o = opciones(opts)
    polys, info_lineas, caja, grupos = maquetar(o["lineas"], o["ancho"], True)
    mpoly = marco(o["marco"], caja)
    ancho_txt = o["ancho"]
    for _ in range(6):                         # con marco, el ancho pedido es el del marco
        if not mpoly:
            break
        wf = max(p[0] for p in mpoly) - min(p[0] for p in mpoly) + 2 * MARCO_ANCHO + 1.0
        if wf <= o["ancho"]:
            break
        ancho_txt *= o["ancho"] / wf
        polys, info_lineas, caja, grupos = maquetar(o["lineas"], ancho_txt, True)
        mpoly = marco(o["marco"], caja)
    ext = list(caja)
    if mpoly:
        ext = [min(ext[0], min(p[0] for p in mpoly)), min(ext[1], min(p[1] for p in mpoly)),
               max(ext[2], max(p[0] for p in mpoly)), max(ext[3], max(p[1] for p in mpoly))]
    r = _pieza(polys, grupos, mpoly, o, ext)
    r["reporte"].update({"lineas": info_lineas, "marco": o["marco"]})
    return r


# ----------------------------------------------------------------- número de años
def estrella(cx, cy, R, puntas=5, adentro=0.45, giro=0.0):
    out = []
    for k in range(2 * puntas):
        a = math.pi / 2 + giro + k * math.pi / puntas
        r = R if k % 2 == 0 else R * adentro
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def corazoncito(cx, cy, R, n=72):
    out = []
    for k in range(n):
        t = TAU * k / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((cx + x * R / 16.0, cy + (y + 2.5) * R / 16.0))
    return out


def circulo(cx, cy, R, n=40):
    return [(cx + R * math.cos(TAU * k / n), cy + R * math.sin(TAU * k / n)) for k in range(n)]


def corona(cx, yb, w, h):
    """Corona de tres puntas con bolitas, apoyada en yb."""
    a = w / 2.0
    P = [(cx - a, yb), (cx + a, yb), (cx + a, yb + h), (cx + a * 0.5, yb + 0.5 * h),
         (cx, yb + h * 1.05), (cx - a * 0.5, yb + 0.5 * h), (cx - a, yb + h)]
    bol = [circulo(cx - a, yb + h, 0.13 * h), circulo(cx, yb + h * 1.05, 0.15 * h),
           circulo(cx + a, yb + h, 0.13 * h)]
    return [P] + bol


def construir_numero(opts):
    o = opciones_numero(opts)
    t, err = mate_fuentes.limpiar(o["numero"], o["fuente"])
    if err:
        raise ValueError(err)
    P = mate_fuentes.contornos(t, o["fuente"])
    pts = [p for Q in P for p in Q]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    s = o["alto"] / (y1 - y0)
    cx = (x0 + x1) / 2.0
    dig = [[((x - cx) * s, (y - y0) * s) for x, y in Q] for Q in P]
    w, h = (x1 - x0) * s, o["alto"]
    X0, X1 = -w / 2.0, w / 2.0
    deco, grupos = [], None
    bordes = [p for Q in dig for p in Q]

    def pegar(x, y, R):
        """Corre el adorno hacia el número hasta que lo pise (no queda colgando)."""
        q = min(bordes, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        d = math.hypot(x - q[0], y - q[1])
        if d <= 0.55 * R:
            return x, y
        k = 0.55 * R / d
        return q[0] + (x - q[0]) * k, q[1] + (y - q[1]) * k
    lugares = [(X1 + 0.05 * h, 0.9 * h, 0.2 * h, 0.15), (X0 - 0.05 * h, 0.62 * h, 0.14 * h, -0.2),
               (X1 + 0.08 * h, 0.28 * h, 0.11 * h, 0.3)]
    if o["deco"] == "estrellas":
        for x, y, R, gi in lugares:
            x, y = pegar(x, y, R)
            deco.append(estrella(x, y, R, giro=gi))
    elif o["deco"] == "corazones":
        for x, y, R, _ in lugares:
            x, y = pegar(x, y, R)
            deco.append(corazoncito(x, y, R))
    elif o["deco"] == "corona":
        cw = max(0.78 * w, 0.6 * h)
        deco = corona(0.0, 0.97 * h, cw, 0.36 * h)
    polys = dig + deco
    if o["deco"] == "anios":
        A = mate_fuentes.contornos("años", "great_vibes")
        apts = [p for Q in A for p in Q]
        ax0, ax1 = min(p[0] for p in apts), max(p[0] for p in apts)
        ay0, ay1 = min(p[1] for p in apts), max(p[1] for p in apts)
        sa = max(1.15 * w, 1.1 * h) / (ax1 - ax0)
        acx = (ax0 + ax1) / 2.0
        anios = [[((x - acx) * sa, (y - ay1) * sa) for x, y in Q] for Q in A]
        sube = _subir(polys, anios, 0.0, min(h, (ay1 - ay0) * sa))
        anios = [[(x, y + sube) for x, y in Q] for Q in anios]
        grupos = [polys, anios]
        polys = polys + anios
    allp = [p for Q in polys for p in Q]
    ext = [min(p[0] for p in allp), min(p[1] for p in allp), max(p[0] for p in allp), max(p[1] for p in allp)]
    r = _pieza(polys, grupos or [polys], None, o, ext, ("NUMERO", "NUMERO_LETRAS"))
    r["reporte"].update({"numero": o["numero"], "fuente": o["fuente"], "deco": o["deco"],
                         "alto_mm": round(h, 1)})
    return r
