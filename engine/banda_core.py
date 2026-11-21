# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
BANDA DE RECIBIDA — collar de cuentas con un texto ("ME ♥ RECIBÍ" o el que quieras)
===================================================================================
Las piezas salen del modelo original en Rhino (Collar_ME_RECIBI):

    DISCO     Ø 38 × 14 mm, borde redondeado arriba (r 3) y chanfle + redondeo abajo; una letra
              incrustada 1 mm en cada cara (la de abajo espejada, así se lee al darlo vuelta)
              y el agujero del hilo Ø 7 de lado a lado, a media altura.
    LETRAS    las incrustaciones (de otro color, partes del mismo objeto para AMS).
    CORAZON   corazón "inflado" de 44 × 40 × 16 mm con el agujero de lado a lado, a la altura
              donde el corazón es más ancho.
    PELOTITA  esfera de Ø 22 achatada a 14 mm de alto, con el agujero vertical.

Todo escala con el diámetro del disco. Sin booleanas: cada cuerpo con agujero transversal
(disco y corazón) se arma como un "campo de alturas" en y sobre el plano x-z: para cada
(x, z) la pieza ocupa [ybot, ytop] menos el agujero [yh - w, yh + w] (w > 0 sólo en la franja
del agujero); cuatro hojas (arriba, abajo y las dos mitades del tubo) se cosen en sus bordes
y se tapan con las caras de arriba y de abajo (con el bolsillo de la letra en el disco).

    construir(opts) -> {"collar": [...], "piezas": {...}, "reporte": {...}}
"""
import math

import mate_fuentes
from eden_floor import earcut

TAU = 2.0 * math.pi
VERSION = "1.0.0"

# --- medidas del modelo original (mm, para un disco de Ø 38) ---------------------------
D0 = 38.0
H_DISCO = 14.0
FILETE_ARRIBA = 3.0          # redondeo del borde de arriba
CHANFLE_ABAJO = 0.95         # chanfle a 45° del borde de abajo (pata de elefante)
FILETE_ABAJO = 2.3           # redondeo entre el chanfle y la pared
LETRA = 18.0                 # alto de la mayúscula
CORAZON_W = 43.3             # ancho del corazón a media altura
CORAZON_T = 16.0
CORAZON_CARA = 0.88          # las caras del corazón son el 88 % del contorno del medio
PELOTITA_D = 22.0
PELOTITA_H = 14.0

SEPARADORES = [("corazon", "Corazón"), ("pelotita", "Pelotita"), ("nada", "Nada")]
RELLENOS = [("alternado", "Pelotita y corazón"), ("corazones", "Sólo corazones"),
            ("pelotitas", "Sólo pelotitas")]
CARAS = [("dos", "Letra en las dos caras"), ("una", "Letra en una cara")]
FUENTES = [("archivo_black", "Archivo Black (bloque)"), ("anton", "Anton (condensada)"),
           ("russo_one", "Russo One (deportiva)"), ("lilita_one", "Lilita One (gruesa)"),
           ("fredoka", "Fredoka (redondeada)"), ("bungee", "Bungee (cartel)"),
           ("luckiest_guy", "Luckiest Guy (cómic)")]
IDS = [f for f, _ in FUENTES]
DEFECTO = {"texto": "ME RECIBÍ", "separador": "corazon", "relleno": "alternado", "largo": 130.0,
           "diametro": 38.0, "agujero": 7.0, "caras": "dos", "profundidad": 1.0,
           "fuente": "archivo_black", "calidad": "preview"}
LIMITES = {"largo": (60.0, 180.0), "diametro": (26.0, 46.0), "agujero": (3.0, 9.0),
           "profundidad": (0.6, 2.0), "letras": 24}
HUECO = 0.6        # mm entre cuentas en el hilo (el collar armado)
MARGEN_LETRA = 1.6  # mm entre la letra y el borde plano del disco


def _f(v, d, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    if v != v:
        return d
    return max(lo, min(hi, v))


def _quitar_tilde_si_falta(ch, glifos):
    if ch in glifos:
        return ch
    import unicodedata
    base = unicodedata.normalize("NFKD", ch)[0]
    return base if base in glifos else None


def opciones(o):
    o = dict(DEFECTO, **(o or {}))
    for k, lista in (("separador", SEPARADORES), ("relleno", RELLENOS), ("caras", CARAS)):
        if o.get(k) not in [i for i, _ in lista]:
            raise ValueError("opción desconocida (%s): %s" % (k, o.get(k)))
    if o.get("fuente") not in IDS:
        raise ValueError("Tipografía desconocida: %s" % o.get("fuente"))
    for k in ("largo", "diametro", "agujero", "profundidad"):
        o[k] = _f(o.get(k), DEFECTO[k], *LIMITES[k])
    o["calidad"] = o.get("calidad") if o.get("calidad") in ("preview", "normal") else "preview"
    texto = " ".join(str(o.get("texto") or "").split()).upper()
    if not texto:
        raise ValueError("Escribí el texto de la banda (por ejemplo ME RECIBÍ)")
    letras = [c for c in texto if c != " "]
    if len(letras) > LIMITES["letras"]:
        raise ValueError("El texto puede tener hasta %d letras (sin contar los espacios)" % LIMITES["letras"])
    g = mate_fuentes.cargar(o["fuente"])["glifos"]
    malas = sorted({c for c in letras if _quitar_tilde_si_falta(c, g) is None})
    if malas:
        raise ValueError("Estos caracteres no están en la tipografía: %s" % " ".join(malas))
    o["texto"] = texto
    s = o["diametro"] / D0
    o["escala"] = s
    # el agujero tiene que dejar pared hasta el bolsillo de la letra (1,2 mm) y en la pelotita
    h = H_DISCO * s
    tope = 2.0 * (h / 2.0 - o["profundidad"] * (2 if o["caras"] == "dos" else 1) / 2.0 - 1.2)
    tope = min(tope, 2.0 * (h / 2.0 - o["profundidad"] - 1.2), PELOTITA_D * s * 0.5)
    o["agujero_pedido"] = o["agujero"]
    o["agujero"] = round(max(LIMITES["agujero"][0], min(o["agujero"], tope)), 2)
    return o


# ===========================================================================
# GEOMETRÍA BÁSICA
# ===========================================================================
def _area(loop):
    a = 0.0
    n = len(loop)
    for i in range(n):
        x1, y1 = loop[i]
        x2, y2 = loop[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _dentro(pt, loop):
    x, y = pt
    c = False
    n = len(loop)
    for i in range(n):
        x1, y1 = loop[i]
        x2, y2 = loop[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def soldar(V, F, tol=1e-6):
    """Une vértices repetidos y saca los triángulos que quedan degenerados."""
    q = 1.0 / tol
    mapa, V2, idx = {}, [], []
    for v in V:
        k = (round(v[0] * q), round(v[1] * q), round(v[2] * q))
        j = mapa.get(k)
        if j is None:
            j = len(V2)
            mapa[k] = j
            V2.append(v)
        idx.append(j)
    F2 = []
    for a, b, c in F:
        a, b, c = idx[a], idx[b], idx[c]
        if a != b and b != c and a != c:
            F2.append((a, b, c))
    return V2, F2


def _tri_poligono(ext, huecos):
    """Triangula un polígono (exterior CCW, huecos CW o lo que sea) -> (pts, tris CCW)."""
    ext = list(ext)
    if _area(ext) < 0:
        ext.reverse()
    hs = []
    for h in huecos:
        h = list(h)
        if _area(h) > 0:
            h.reverse()
        hs.append(h)
    pts = ext + [p for h in hs for p in h]
    off = len(ext)
    holes = []
    for h in hs:
        holes.append((h, list(range(off, off + len(h)))))
        off += len(h)
    tris = earcut(ext, list(range(len(ext))), holes)
    out = []
    for a, b, c in tris:
        A, B, C = pts[a], pts[b], pts[c]
        if (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]) < 0:
            b, c = c, b
        out.append((a, b, c))
    return pts, out


def _cara(ext, huecos, z, arriba, V, F):
    pts, tris = _tri_poligono(ext, huecos)
    i0 = len(V)
    V.extend((x, y, z) for x, y in pts)
    for a, b, c in tris:
        F.append((i0 + a, i0 + b, i0 + c) if arriba else (i0 + a, i0 + c, i0 + b))


def _pared(loop, z0, z1, afuera_izq, V, F):
    """Pared vertical a lo largo de un lazo; normal hacia la izquierda del recorrido si
    afuera_izq, si no hacia la derecha."""
    n = len(loop)
    i0 = len(V)
    V.extend((x, y, z0) for x, y in loop)
    V.extend((x, y, z1) for x, y in loop)
    for q in range(n):
        q1 = (q + 1) % n
        a0, b0, a1, b1 = i0 + q, i0 + q1, i0 + n + q, i0 + n + q1
        if afuera_izq:
            F.append((a0, b1, b0))
            F.append((a0, a1, b1))
        else:
            F.append((a0, b0, b1))
            F.append((a0, b1, a1))


def prisma(regiones, z0, z1):
    """Extruye regiones [(exterior, [huecos])] entre z0 y z1 -> malla cerrada (V, F)."""
    V, F = [], []
    for ext, huecos in regiones:
        ext = ext if _area(ext) > 0 else ext[::-1]
        _cara(ext, huecos, z1, True, V, F)
        _cara(ext, huecos, z0, False, V, F)
        _pared(ext, z0, z1, False, V, F)
        for h in huecos:
            h = h if _area(h) > 0 else h[::-1]
            _pared(h, z0, z1, True, V, F)
    return soldar(V, F)


# ===========================================================================
# LETRAS
# ===========================================================================
def _limpiar(loop, tol=1e-4):
    out = []
    for p in loop:
        if not out or abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) <= tol and abs(out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def jerarquia(polys):
    """Polígonos sueltos (exteriores y contraformas en cualquier sentido) -> regiones
    [(exterior CCW, [huecos CW])] por profundidad de anidado (par = relleno)."""
    polys = [p for p in (_limpiar(q) for q in polys) if len(p) >= 3 and abs(_area(p)) > 1e-6]
    prof = []
    for i, p in enumerate(polys):
        d = 0
        for j, q in enumerate(polys):
            if i != j and abs(_area(q)) > abs(_area(p)) and _dentro(p[0], q):
                d += 1
        prof.append(d)
    regiones = []
    for i, p in enumerate(polys):
        if prof[i] % 2:
            continue
        ext = p if _area(p) > 0 else p[::-1]
        huecos = []
        for j, q in enumerate(polys):
            if prof[j] == prof[i] + 1 and _dentro(q[0], p):
                huecos.append(q if _area(q) < 0 else q[::-1])
        regiones.append((ext, huecos))
    return regiones


_LETRAS = {}


def letra(ch, fid, alto, radio_max):
    """Regiones de una letra con la mayúscula de `alto` mm y el cuerpo centrado en (0, 0);
    los acentos quedan arriba. Si no entra en el círculo de `radio_max`, se achica."""
    key = (ch, fid, round(alto, 3), round(radio_max, 3))
    if key in _LETRAS:
        return _LETRAS[key]
    f = mate_fuentes.cargar(fid)
    g = f["glifos"]
    c = _quitar_tilde_si_falta(ch, g)
    cap = float(f.get("cap") or 700)
    polys = mate_fuentes.contornos(c, fid)
    xs = [x for P in polys for x, _ in P]
    mx = (min(xs) + max(xs)) / 2.0
    s = alto / cap
    pts = [((x - mx) * s, (y - cap / 2.0) * s) for P in polys for x, y in P]
    rmax = max(math.hypot(x, y) for x, y in pts) if pts else 1.0
    if rmax > radio_max:
        # se achica y se baja apenas para que el acento también entre
        k = radio_max / rmax
        s *= k
    polys = [[((x - mx) * s, (y - cap / 2.0) * s) for x, y in P] for P in polys]
    reg = jerarquia(polys)
    _LETRAS[key] = (reg, s * cap)
    return _LETRAS[key]


def espejo_y(regiones):
    out = []
    for ext, huecos in regiones:
        out.append(([(x, -y) for x, y in ext][::-1], [[(x, -y) for x, y in h][::-1] for h in huecos]))
    return out


# ===========================================================================
# CUERPO CON AGUJERO TRANSVERSAL (campo de alturas en y)
# ===========================================================================
def _filas(T, zc, ra, n_band, n_fuera, extra=()):
    """Alturas de las filas: densas en la franja del agujero (zc ± ra, con seno, así el
    tubo sale redondo) y en los bordes."""
    zs = set()
    for k in range(n_band + 1):
        zs.add(round(zc + ra * math.sin(-math.pi / 2 + math.pi * k / n_band), 9))
    lo, hi = zc - ra, zc + ra
    for a, b in ((0.0, lo), (hi, T)):
        m = max(2, int(math.ceil(n_fuera * (b - a) / T)))
        for k in range(m + 1):
            # coseno: más filas cerca de las caras (bordes redondeados)
            t = 0.5 - 0.5 * math.cos(math.pi * k / m)
            zs.add(round(a + (b - a) * t, 9))
    for z in extra:
        if 0 < z < T and not (lo - 1e-6 < z < hi + 1e-6):
            zs.add(round(z, 9))
    return sorted(zs)


def _x_corte(f_y, y_obj, x_lo, x_hi):
    """Mayor x en [x_lo, x_hi] con f_y(x) >= y_obj (f_y decrece hacia x_hi)."""
    for _ in range(48):
        m = (x_lo + x_hi) / 2.0
        if f_y(m) >= y_obj:
            x_lo = m
        else:
            x_hi = m
    return x_lo


def cuerpo_agujero(T, filas, xmax, ytop, ybot, x_pico_top, x_pico_bot, yh, zc, ra, ncol,
                   tapa_arriba, tapa_abajo):
    """Malla cerrada de un cuerpo con un agujero cilíndrico a lo largo de x.

    xmax(z): medio ancho de la sección a la altura z (ahí ytop = ybot = yh).
    ytop(x, z) / ybot(x, z): bordes de la sección (simétricos en x).
    x_pico_*(z): desde dónde ytop / ybot decrecen / crecen hacia xmax (para buscar el corte
    con el agujero). tapa_*(loop): -> [(huecos, bolsillo)] arma la cara de arriba / abajo con
    el contorno de esa altura (devuelve la malla de la tapa)."""
    V, F = [], []
    cols = [math.sin(-math.pi / 2 + math.pi * j / ncol) for j in range(ncol + 1)]
    n = len(filas)

    def w_de(z):
        if abs(z - zc) >= ra - 1e-6:
            return 0.0
        return math.sqrt(ra * ra - (z - zc) ** 2)

    sup, inf, tsup, tinf = [], [], [], []      # filas de índices de cada hoja
    banda = []
    for k, z in enumerate(filas):
        X = xmax(z)
        w = w_de(z)
        en_banda = abs(z - zc) <= ra + 1e-6
        if w > 0:
            xu = _x_corte(lambda x: ytop(x, z), yh + w, x_pico_top(z), X)
            xl = _x_corte(lambda x: -ybot(x, z), -(yh - w), x_pico_bot(z), X)
        else:
            xu = xl = X
        ru, rl, rtu, rtl = [], [], [], []
        for j, s in enumerate(cols):
            borde = j in (0, ncol)
            x = xu * s
            y = (yh + w) if borde else max(ytop(abs(x), z), yh + w)
            ru.append(len(V))
            V.append((x, y, z))
            x = xl * s
            y = (yh - w) if borde else min(ybot(abs(x), z), yh - w)
            rl.append(len(V))
            V.append((x, y, z))
            if en_banda:
                rtu.append(len(V))
                V.append((xu * s, yh + w, z))
                rtl.append(len(V))
                V.append((xl * s, yh - w, z))
        sup.append(ru)
        inf.append(rl)
        if en_banda:
            banda.append(k)
            tsup.append(rtu)
            tinf.append(rtl)

    def coser(R, normal_mas_y):
        for k in range(len(R) - 1):
            A, B = R[k], R[k + 1]
            for j in range(ncol):
                a, b, c, d = A[j], A[j + 1], B[j + 1], B[j]
                if normal_mas_y:
                    F.append((a, c, b))
                    F.append((a, d, c))
                else:
                    F.append((a, b, c))
                    F.append((a, c, d))
    coser(sup, True)
    coser(inf, False)
    coser(tsup, False)
    coser(tinf, True)
    # tapas: el contorno es la fila de arriba (U) ida y la de abajo (L) vuelta
    for k, arriba in ((n - 1, True), (0, False)):
        loop = [V[i][:2] for i in sup[k]] + [V[i][:2] for i in inf[k][-2:0:-1]]
        z = filas[k]
        fn = tapa_arriba if arriba else tapa_abajo
        Vt, Ft = fn(loop, z)
        o = len(V)
        V.extend(Vt)
        F.extend((a + o, b + o, c + o) for a, b, c in Ft)
    return soldar(V, F, 1e-7)


def _tapa(regiones_letra, profundidad, arriba):
    """Cara plana con el bolsillo de la letra (si hay)."""
    def fn(loop, z):
        V, F = [], []
        loop = loop if _area(loop) > 0 else loop[::-1]
        if not regiones_letra:
            _cara(loop, [], z, arriba, V, F)
            return V, F
        zf = z - profundidad if arriba else z + profundidad
        _cara(loop, [ext for ext, _ in regiones_letra], z, arriba, V, F)
        for ext, huecos in regiones_letra:
            for h in huecos:                   # islas (contraformas) a la altura de la cara
                _cara(h[::-1], [], z, arriba, V, F)
            _cara(ext, huecos, zf, arriba, V, F)  # piso del bolsillo
            z0, z1 = (zf, z) if arriba else (z, zf)
            _pared(ext, z0, z1, True, V, F)
            for h in huecos:
                hh = h if _area(h) > 0 else h[::-1]
                _pared(hh, z0, z1, False, V, F)
        return V, F
    return fn


# ===========================================================================
# PIEZAS
# ===========================================================================
def perfil_disco(s):
    """Radio del disco en función de z (y la lista de alturas de los quiebres)."""
    R, H = D0 * s / 2.0, H_DISCO * s
    ft, fb, ch = FILETE_ARRIBA * s, FILETE_ABAJO * s, CHANFLE_ABAJO * s
    # abajo: chanfle a 45° tangente al redondeo de radio fb con centro (R - fb, zb)
    zb = fb + ch * 0.9
    zt_b = zb - fb * math.sqrt(0.5)                       # punto de tangencia (45°)
    r0 = (R - fb + fb * math.sqrt(0.5)) - zt_b           # radio del chanfle en z = 0

    def r(z):
        if z >= H - ft:
            d = z - (H - ft)
            return R - ft + math.sqrt(max(ft * ft - d * d, 0.0))
        if z >= zb:
            return R
        if z >= zt_b:
            d = zb - z
            return R - fb + math.sqrt(max(fb * fb - d * d, 0.0))
        return r0 + z
    quiebres = [zt_b, zb, H - ft] + [H - ft + ft * math.sin(math.pi / 2 * k / 6) for k in range(1, 6)] \
        + [zb - fb * math.cos(math.pi / 4 * k / 3) for k in range(1, 3)]
    return r, quiebres, r0, R - ft


def malla_disco(ch, o):
    s, ra = o["escala"], o["agujero"] / 2.0
    H = H_DISCO * s
    r, quiebres, r_abajo, r_arriba = perfil_disco(s)
    q = o["calidad"] == "normal"
    alto = LETRA * s
    reg, alto_real = letra(ch, o["fuente"], alto, min(r_abajo, r_arriba) - MARGEN_LETRA * s)
    prof = o["profundidad"]
    reg_abajo = espejo_y(reg) if o["caras"] == "dos" else []
    filas = _filas(H, H / 2.0, ra, 24 if q else 14, 22 if q else 12, quiebres)
    V, F = cuerpo_agujero(
        H, filas, r,
        lambda x, z: math.sqrt(max(r(z) ** 2 - x * x, 0.0)),
        lambda x, z: -math.sqrt(max(r(z) ** 2 - x * x, 0.0)),
        lambda z: 0.0, lambda z: 0.0, 0.0, H / 2.0, ra, 72 if q else 44,
        _tapa(reg, prof, True), _tapa(reg_abajo, prof, False))
    letras = []
    Vl, Fl = prisma(reg, H - prof, H)
    letras.append((Vl, Fl))
    if reg_abajo:
        letras.append(prisma(reg_abajo, 0.0, prof))
    VL, FL = [], []
    for Vx, Fx in letras:
        o2 = len(VL)
        VL.extend(Vx)
        FL.extend((a + o2, b + o2, c + o2) for a, b, c in Fx)
    return (V, F), (VL, FL), round(alto_real, 2)


# contorno del corazón del modelo original (cara de abajo), mitad derecha de la punta
# (y = 0 es la altura donde es más ancho: ahí pasa el agujero); se escala a ancho 1
_CORAZON_DER = [
    (0.0, -25.12), (0.57, -24.71), (1.32, -23.80), (2.13, -22.94), (2.93, -22.08), (3.74, -21.21),
    (4.54, -20.34), (5.34, -19.47), (6.14, -18.60), (6.95, -17.74), (7.75, -16.87), (8.55, -16.00),
    (9.36, -15.13), (10.16, -14.26), (10.96, -13.40), (11.76, -12.53), (12.57, -11.66),
    (13.37, -10.79), (14.17, -9.92), (14.97, -9.06), (15.78, -8.19), (16.58, -7.32), (17.37, -6.44),
    (18.06, -5.48), (18.64, -4.45), (19.09, -3.36), (19.42, -2.23), (19.61, -1.06), (19.67, 0.12),
    (19.58, 1.30), (19.37, 2.46), (19.01, 3.59), (18.53, 4.67), (17.93, 5.68), (17.22, 6.62),
    (16.40, 7.47), (15.48, 8.22), (14.49, 8.86), (13.43, 9.38), (12.31, 9.77), (11.16, 10.03),
    (9.98, 10.16), (8.80, 10.14), (7.63, 9.99), (6.48, 9.71), (5.38, 9.29), (4.33, 8.75),
    (3.35, 8.09), (2.45, 7.33), (1.61, 6.50), (0.52, 6.05), (0.0, 6.02)]


def _corazon_bordes():
    """Bordes de arriba y abajo del contorno (medio corazón, x >= 0) normalizado a ancho 1."""
    W = 2.0 * max(x for x, _ in _CORAZON_DER)
    pts = [(x / W, y / W) for x, y in _CORAZON_DER]
    i_max = max(range(len(pts)), key=lambda i: pts[i][0])
    abajo = pts[:i_max + 1]                       # de la punta al costado (x creciente)
    arriba = pts[i_max:][::-1]                    # del centro (hendidura) al costado
    # el punto más ancho: y del agujero = 0 (corrijo el redondeo)
    xm, ym = pts[i_max]
    abajo = [(x, y - ym) for x, y in abajo]
    arriba = [(x, y - ym) for x, y in arriba]
    return abajo, arriba, xm


def _interp(seq, x):
    if x <= seq[0][0]:
        return seq[0][1]
    for (x0, y0), (x1, y1) in zip(seq, seq[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
            return y0 + (y1 - y0) * t
    return seq[-1][1]


def malla_corazon(o):
    s, ra = o["escala"], o["agujero"] / 2.0
    W, T = CORAZON_W * s, CORAZON_T * s
    abajo, arriba, xm = _corazon_bordes()
    q = o["calidad"] == "normal"
    i_pico = max(range(len(arriba)), key=lambda i: arriba[i][1])
    x_pico = arriba[i_pico][0]

    def k(z):                                     # "inflado": elipse entre cara y cara
        u = (z - T / 2.0) / (T / 2.0)
        return CORAZON_CARA + (1 - CORAZON_CARA) * math.sqrt(max(1 - u * u, 0.0))

    def xmax(z):
        return xm * W * k(z)

    def ytop(x, z):
        sc = W * k(z)
        return sc * _interp(arriba, min(abs(x) / sc, xm))

    def ybot(x, z):
        sc = W * k(z)
        return sc * _interp(abajo, min(abs(x) / sc, xm))
    filas = _filas(T, T / 2.0, ra, 24 if q else 14, 26 if q else 14)
    return cuerpo_agujero(T, filas, xmax, ytop, ybot, lambda z: x_pico * W * k(z), lambda z: 0.0,
                          0.0, T / 2.0, ra, 96 if q else 56, _tapa([], 0, True), _tapa([], 0, False))


def revolucion(perfil, M):
    """Revoluciona un perfil cerrado [(r, z)] (sentido antihorario en r-z) alrededor de z."""
    V, F = [], []
    n = len(perfil)
    for i in range(M):
        a = TAU * i / M
        c, sn = math.cos(a), math.sin(a)
        V.extend((r * c, r * sn, z) for r, z in perfil)
    for i in range(M):
        i1 = (i + 1) % M
        for j in range(n):
            j1 = (j + 1) % n
            a, b, c, d = i * n + j, i * n + j1, i1 * n + j1, i1 * n + j
            F.append((a, d, c))
            F.append((a, c, b))
    return soldar(V, F)


def malla_pelotita(o):
    s, ra = o["escala"], o["agujero"] / 2.0
    R, h = PELOTITA_D * s / 2.0, PELOTITA_H * s
    q = o["calidad"] == "normal"
    zc = h / 2.0
    a = math.asin(min(1.0, (h / 2.0) / R))
    rc = R * math.cos(a)
    m = 28 if q else 16
    arco = [(R * math.cos(-a + 2 * a * t / m), zc + R * math.sin(-a + 2 * a * t / m)) for t in range(m + 1)]
    perfil = [(ra, 0.0), (rc, 0.0)] + arco[1:-1] + [(rc, h), (ra, h)]
    return revolucion(perfil, 72 if q else 40)


# ===========================================================================
# EL COLLAR
# ===========================================================================
def secuencia(o):
    """Lista de cuentas en orden: ("letra", ch) / ("corazon",) / ("pelotita",) y cuántas
    son de texto (las del texto van seguidas, centradas adelante)."""
    palabras = o["texto"].split(" ")
    txt = []
    for i, p in enumerate(palabras):
        if i and o["separador"] != "nada":
            txt.append((o["separador"], None))
        txt.extend(("letra", c) for c in p)
    return txt


def largo_de(tipo, o):
    """Lo que ocupa cada cuenta a lo largo del hilo (mm)."""
    s = o["escala"]
    if tipo == "letra":
        return D0 * s
    if tipo == "corazon":
        return CORAZON_W * s
    return PELOTITA_H * s


def armar(o):
    txt = secuencia(o)
    L = o["largo"] * 10.0
    hueco = HUECO * o["escala"]
    l_txt = sum(largo_de(t, o) + hueco for t, _ in txt)
    lp, lc = largo_de("pelotita", o) + hueco, largo_de("corazon", o) + hueco
    resto = L - l_txt
    rell = []
    if o["relleno"] == "alternado":
        # pelotita, corazón, …, pelotita (las puntas junto al texto son pelotitas)
        m = max(0, int(round((resto - lp) / (lp + lc))))
        rell = [("pelotita", None)]
        for _ in range(m):
            rell += [("corazon", None), ("pelotita", None)]
    else:
        t = "corazon" if o["relleno"] == "corazones" else "pelotita"
        n = max(1, int(round(resto / (lc if t == "corazon" else lp))))
        rell = [(t, None)] * n
    total = l_txt + sum(largo_de(t, o) + hueco for t, _ in rell)
    return txt, rell, total, l_txt


def _rot(V, ang, cx, cy, dz=0.0, eje_x_a_z=False):
    """Coloca una pieza: (opcional) gira x->z (pelotita de costado), rota `ang` y traslada."""
    c, s = math.cos(ang), math.sin(ang)
    out = []
    for x, y, z in V:
        if eje_x_a_z:
            x, y, z = z, y, -x
        out.append((c * x - s * y + cx, s * x + c * y + cy, z + dz))
    return out


def _centrar_z(V, zc):
    return [(x, y, z - zc) for x, y, z in V]


def construir(opts):
    o = opciones(opts)
    s = o["escala"]
    txt, rell, total, l_txt = armar(o)
    if l_txt > 0.62 * total:
        raise ValueError("El texto es muy largo para un collar de %d cm: hacelo más largo, achicá las "
                         "cuentas o acortá el texto" % round(o["largo"]))
    # piezas únicas
    piezas = {}
    letras_mm = {}
    for t, ch in txt:
        if t == "letra" and ("DISCO", ch) not in piezas:
            cuerpo, inc, alto = malla_disco(ch, o)
            piezas[("DISCO", ch)] = cuerpo
            piezas[("LETRAS", ch)] = inc
            letras_mm[ch] = alto
    usa = {t for t, _ in txt + rell}
    if "corazon" in usa:
        piezas[("CORAZON", None)] = malla_corazon(o)
    if "pelotita" in usa:
        piezas[("PELOTITA", None)] = malla_pelotita(o)
    # el collar acostado: el hilo es un círculo de largo `total`, el texto adelante
    Rc = total / TAU
    hueco = HUECO * s
    H, T, Rp = H_DISCO * s, CORAZON_T * s, PELOTITA_D * s / 2.0
    sube = Rp                                    # la pelotita de costado apoya en la mesa
    orden = txt + rell
    # el texto centrado adelante (ángulo -90°, del lado de la cámara y donde cuelga al
    # ponérselo), de izquierda a derecha: sentido antihorario, con la parte de arriba de las
    # letras hacia el centro (hacia el cuello)
    pos = []
    acum = 0.0
    for t, ch in orden:
        l = largo_de(t, o)
        pos.append(acum + l / 2.0)
        acum += l + hueco
    mitad_txt = (pos[len(txt) - 1] + pos[0]) / 2.0 if txt else 0.0
    collar = []
    for (t, ch), p in zip(orden, pos):
        phi = -math.pi / 2 + (p - mitad_txt) / Rc
        cx, cy = Rc * math.cos(phi), Rc * math.sin(phi)
        ang = phi + math.pi / 2                   # x local = tangente, y local = hacia el centro
        if t == "letra":
            collar.append({"pieza": "DISCO", "letra": ch, "x": cx, "y": cy, "ang": ang, "z": sube - H / 2.0})
        elif t == "corazon":
            collar.append({"pieza": "CORAZON", "letra": None, "x": cx, "y": cy, "ang": ang, "z": sube - T / 2.0})
        else:
            collar.append({"pieza": "PELOTITA", "letra": None, "x": cx, "y": cy, "ang": ang, "z": sube, "costado": True})
    cuenta = {}
    for t, ch in orden:
        k = ("DISCO", ch) if t == "letra" else ((t.upper(), None))
        cuenta[k] = cuenta.get(k, 0) + 1
    discos = sorted([(ch, n) for (p, ch), n in cuenta.items() if p == "DISCO"], key=lambda e: txt.index(("letra", e[0])))
    avisos = []
    if o["agujero"] < o["agujero_pedido"] - 1e-6:
        avisos.append("El agujero se achicó a %.1f mm para que quede pared hasta la letra" % o["agujero"])
    if s < 0.8:
        avisos.append("Con cuentas tan chicas, imprimí las letras con capa de 0,12 mm para que se lean bien")
    medidas = {}
    for (nombre, ch), (V, F) in piezas.items():
        if nombre == "LETRAS":
            continue
        xs, ys, zs = [v[0] for v in V], [v[1] for v in V], [v[2] for v in V]
        medidas[nombre] = [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), round(max(zs) - min(zs), 1)]
    rep = {"texto": o["texto"], "separador": o["separador"], "relleno": o["relleno"], "caras": o["caras"],
           "fuente": o["fuente"], "diametro_mm": round(D0 * s, 1), "agujero_mm": o["agujero"],
           "profundidad_mm": o["profundidad"], "largo_cm": round(total / 10.0, 1),
           "largo_pedido_cm": o["largo"], "diametro_collar_mm": round(2 * Rc, 0),
           "hilo_cm": int(math.ceil(total / 10.0 + 25)),
           "discos": [{"letra": ch, "cantidad": n} for ch, n in discos],
           "total_discos": sum(n for _, n in discos),
           "corazones": cuenta.get(("CORAZON", None), 0), "pelotitas": cuenta.get(("PELOTITA", None), 0),
           "cuentas": len(orden), "letra_mm": round(max(letras_mm.values()) if letras_mm else 0, 1),
           "medidas_mm": medidas, "avisos": avisos, "escala": round(s, 3)}
    return {"collar": collar, "piezas": piezas, "reporte": rep, "opciones": o, "radio": Rc, "sube": sube}


def colocar(item, piezas):
    """Malla de una cuenta en su lugar del collar (DISCO trae también sus LETRAS)."""
    out = []
    if item["pieza"] == "DISCO":
        for nombre in ("DISCO", "LETRAS"):
            V, F = piezas[(nombre, item["letra"])]
            out.append((nombre, _rot(V, item["ang"], item["x"], item["y"], item["z"]), F))
    elif item["pieza"] == "CORAZON":
        V, F = piezas[("CORAZON", None)]
        out.append(("CORAZON", _rot(V, item["ang"], item["x"], item["y"], item["z"]), F))
    else:
        V, F = piezas[("PELOTITA", None)]
        V = _centrar_z(V, max(v[2] for v in V) / 2.0)
        out.append(("PELOTITA", _rot(V, item["ang"], item["x"], item["y"], item["z"], eje_x_a_z=True), F))
    return out


def hilo(Rc, z, r, n=180, m=10):
    """El hilo: un toro fino por el centro de los agujeros."""
    V, F = [], []
    for i in range(n):
        a = TAU * i / n
        for j in range(m):
            b = TAU * j / m
            rr = Rc + r * math.cos(b)
            V.append((rr * math.cos(a), rr * math.sin(a), z + r * math.sin(b)))
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(m):
            j1 = (j + 1) % m
            a0, b0, a1, b1 = i * m + j, i * m + j1, i1 * m + j, i1 * m + j1
            F.append((a0, a1, b1))
            F.append((a0, b1, b0))
    return V, F


def unir(mallas):
    V, F = [], []
    for Vx, Fx in mallas:
        o = len(V)
        V.extend(Vx)
        F.extend((a + o, b + o, c + o) for a, b, c in Fx)
    return V, F


def mesh_volume(V, F):
    vol = 0.0
    for a, b, c in F:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = V[a], V[b], V[c]
        vol += (x1 * (y2 * z3 - y3 * z2) - x2 * (y1 * z3 - y3 * z1) + x3 * (y1 * z2 - y2 * z1)) / 6.0
    return vol


def mesh_check(F):
    """Cada arista dirigida una vez y con su opuesta: cerrada y orientada."""
    aristas = {}
    for a, b, c in F:
        for e in ((a, b), (b, c), (c, a)):
            aristas[e] = aristas.get(e, 0) + 1
    abiertas = sum(1 for (a, b) in aristas if (b, a) not in aristas)
    dobles = sum(1 for n in aristas.values() if n > 1)
    return {"abiertas": abiertas, "dobles": dobles, "ok": abiertas == 0 and dobles == 0}
