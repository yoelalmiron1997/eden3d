# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
TROFEOS PARA EVENTOS — una figura parada sobre una base con el texto del evento
===============================================================================
Dos piezas que encastran, cada una impresa en la posición que mejor sale:

    FIGURA  estrella, llama, rayo, copa, hojas, pelota o un número / letra; se imprime
            acostada (sin soportes) y abajo tiene una espiga que entra en la base. Puede
            llevar un borde en relieve y un texto corto ("1°", "MVP").
    BASE    un bloque (recto o escalonado) con la ranura arriba para la espiga y, al
            frente, el texto del evento en dos líneas, en relieve o grabado. Se imprime parada.

En dos colores los detalles de la figura (DETALLE) y el texto de la base (TEXTO) salen
como piezas aparte (cambio de filamento en la figura / AMS en la base).

    construir(opts) -> {"piezas": [(nombre, V, F)]   para imprimir (cada una en su posición)
                        "armado": [(nombre, V, F)]   el trofeo armado, para el visor
                        "reporte": {...}}
"""
import math
import re

import mate_fuentes
import topper_core as tc

TAU = 2.0 * math.pi
FIGURAS = [("estrella", "Estrella"), ("copa", "Copa"), ("llama", "Llama"), ("rayo", "Rayo"),
           ("hojas", "Hojas"), ("pelota", "Pelota"), ("numero", "Número o letra")]
BASES = [("escalonada", "Escalonada"), ("recta", "Recta")]
TEXTOS = [("relieve", "En relieve"), ("grabado", "Grabado")]
COLORES = [("uno", "Un color"), ("dos", "Dos colores (detalles y texto aparte)")]
DEFECTO = {"figura": "estrella", "caracter": "1", "texto_figura": "", "fuente_figura": "archivo_black",
           "alto": 160.0, "grosor": 8.0, "tallo": 14.0, "borde": 1.6, "relieve": 1.2,
           "base": "escalonada", "base_ancho": 70.0, "base_alto": 32.0, "base_fondo": 40.0,
           "linea1": "CAMPEÓN", "linea2": "Torneo 2026", "fuente": "archivo_black",
           "texto": "relieve", "colores": "uno", "holgura": 0.25, "calidad": "preview"}
LIMITES = {"alto": (90.0, 260.0), "grosor": (5.0, 14.0), "tallo": (0.0, 50.0), "borde": (0.0, 3.0),
           "relieve": (0.6, 2.0), "base_ancho": (40.0, 140.0), "base_alto": (20.0, 60.0),
           "base_fondo": (25.0, 80.0), "holgura": (0.1, 0.5),
           "caracteres1": 22, "caracteres2": 28, "caracteres_figura": 4, "caracteres_numero": 3}
FIGURA_MIN = 40.0       # mm de alto mínimo de la figura (sin tallo)
CAMA = 220.0            # mm: lo que entra en una cama común
MARGEN = 1.2            # mm entre el texto de la figura y el borde
PARED = 4.0             # mm de pared mínima de la base alrededor de la ranura
LETRA_MIN = 4.0


def _f(v, d, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    return max(lo, min(hi, v))


def _texto_limpio(v):
    return " ".join(str(v or "").split())


def opciones(o):
    o = dict(DEFECTO, **(o or {}))
    for k, lista, que in (("figura", FIGURAS, "figura"), ("base", BASES, "base"),
                          ("texto", TEXTOS, "estilo de letra"), ("colores", COLORES, "colores")):
        if o.get(k) not in [x for x, _ in lista]:
            raise ValueError("%s desconocida: %s" % (que.capitalize(), o.get(k)))
    for k in ("fuente", "fuente_figura"):
        if o.get(k) not in tc.IDS:
            raise ValueError("Tipografía desconocida: %s" % o.get(k))
    for k in ("linea1", "linea2", "texto_figura", "caracter"):
        o[k] = _texto_limpio(o.get(k))
    if not o["linea1"] and not o["linea2"]:
        raise ValueError("Escribí el texto de la base (el nombre del evento, el premio…)")
    if len(o["linea1"]) > LIMITES["caracteres1"]:
        raise ValueError("La primera línea puede tener hasta %d caracteres" % LIMITES["caracteres1"])
    if len(o["linea2"]) > LIMITES["caracteres2"]:
        raise ValueError("La segunda línea puede tener hasta %d caracteres" % LIMITES["caracteres2"])
    if len(o["texto_figura"]) > LIMITES["caracteres_figura"]:
        raise ValueError("El texto de la figura puede tener hasta %d caracteres" % LIMITES["caracteres_figura"])
    if o["figura"] == "numero":
        o["caracter"] = o["caracter"].replace(" ", "")
        if not o["caracter"]:
            raise ValueError("Escribí el número o la letra de la figura")
        if len(o["caracter"]) > LIMITES["caracteres_numero"]:
            raise ValueError("La figura puede tener hasta %d números o letras" % LIMITES["caracteres_numero"])
    if o["figura"] in ("numero", "pelota"):
        o["texto_figura"] = ""                       # la figura ya es el texto / lleva su dibujo
    for k in ("alto", "grosor", "tallo", "borde", "relieve", "base_ancho", "base_alto", "base_fondo", "holgura"):
        o[k] = _f(o.get(k), DEFECTO[k], *LIMITES[k])
    o["calidad"] = o.get("calidad") if o.get("calidad") in ("preview", "normal") else "preview"
    if o["alto"] - o["base_alto"] - o["tallo"] < FIGURA_MIN:
        raise ValueError("Con esa base y ese tallo la figura queda de menos de %d mm: subí el alto del trofeo"
                         % FIGURA_MIN)
    return o


# ===========================================================================
# SILUETAS: caminos SVG en una caja de 100 (y para abajo), se dan vuelta y se escalan
# ===========================================================================
def _bezier(p0, p1, p2, p3, n=14):
    out = []
    for k in range(1, n + 1):
        t = k / float(n)
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _camino(d):
    """M, L, H, V, C, Q, Z (absolutos) -> lista de polígonos (y para arriba)."""
    toks = re.findall(r"[MLHVCQZ]|-?\d*\.?\d+", d)
    polys, P, cur, cmd, i = [], [], (0.0, 0.0), None, 0

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v
    while i < len(toks):
        if toks[i] in "MLHVCQZ":
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                if P:
                    polys.append(P)
                P = []
                continue
        if cmd == "M":
            if P:
                polys.append(P)
            cur = (num(), num())
            P = [cur]
            cmd = "L"
        elif cmd == "L":
            cur = (num(), num())
            P.append(cur)
        elif cmd == "H":
            cur = (num(), cur[1])
            P.append(cur)
        elif cmd == "V":
            cur = (cur[0], num())
            P.append(cur)
        elif cmd == "C":
            c1, c2, p = (num(), num()), (num(), num()), (num(), num())
            P.extend(_bezier(cur, c1, c2, p))
            cur = p
        elif cmd == "Q":
            c, p = (num(), num()), (num(), num())
            P.extend(_bezier(cur, (cur[0] + 2 / 3.0 * (c[0] - cur[0]), cur[1] + 2 / 3.0 * (c[1] - cur[1])),
                             (p[0] + 2 / 3.0 * (c[0] - p[0]), p[1] + 2 / 3.0 * (c[1] - p[1])), p))
            cur = p
    if P:
        polys.append(P)
    return [[(x, -y) for x, y in Q] for Q in polys if len(Q) >= 3]


def _orientar(P, ccw=True):
    return P if (tc._area(P) > 0) == ccw else P[::-1]


def _circ(cx, cy, r, n=96):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def _elipse(cx, cy, a, b, n=96):
    return [(cx + a * math.cos(TAU * k / n), cy + b * math.sin(TAU * k / n)) for k in range(n)]


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _estrella(cx, cy, R, r, n=5):
    return [(cx + (r if k % 2 else R) * math.cos(math.pi / 2 + k * math.pi / n),
             cy + (r if k % 2 else R) * math.sin(math.pi / 2 + k * math.pi / n)) for k in range(2 * n)]


def _pentagono(cx, cy, R, giro=90.0):
    return [(cx + R * math.cos(math.radians(giro + 72 * k)), cy + R * math.sin(math.radians(giro + 72 * k)))
            for k in range(5)]


# hasta dónde sube la espiga adentro de la figura (en la copa y las hojas sólo hasta el pie,
# que es ancho: si no, se vería detrás del tallito)
CUELLO = {"copa": 0.06, "hojas": 0.1, "rayo": 0.14}

# cada silueta: (llenos, huecos, centro del texto (x, y), x del pie) en coordenadas SVG (y abajo)
SILUETAS = {
    "llama": (["M50 100C27 100 13 85 15 66C17 51 27 44 29 28C38 38 40 48 38 57"
               "C46 47 52 30 45 2C66 16 83 38 84 61C86 84 71 100 50 100Z",
               "M66 50C70 40 74 34 80 30C86 42 86 52 82 60Z"], [], (50, 74), 50),
    "rayo": (["M60 0L22 58H46L36 100L80 38H55L70 0Z"], [], (51, 49), 40),
    "hojas": (["M52 100C48 64 60 26 90 0C74 30 66 64 64 100Z",
               "M34 100C30 72 38 44 62 18C51 46 46 72 46 100Z",
               "M16 100C13 80 20 60 38 42C30 62 28 80 28 100Z",
               "M10 100H72C72 92 73 86 75 80C54 86 30 87 10 83Z"], [], (42, 92), 42),
    "copa": (["M20 4H80C80 36 70 52 50 56C30 52 20 36 20 4Z", "M45 54H55V78H45Z",
              "M44 76H56C58 78 58 80 56 82H44C42 80 42 78 44 76Z", "M32 81H68L72 96H28Z",
              "M24 6C6 6 4 30 30 40L30 34C14 28 14 12 24 12Z",
              "M76 6C94 6 96 30 70 40L70 34C86 28 86 12 76 12Z"], [], (50, 26), 50),
}


def _silueta(tipo, o):
    """-> (polígonos con orientación: llenos antihorario, huecos horario), centro del texto,
    x del pie, en mm y con la figura de alto H y el pie en y = 0."""
    H = o["alto"] - o["base_alto"] - o["tallo"]
    if tipo == "estrella":
        P = [_estrella(0, 0, 1.0, 0.42)]
        llenos, huecos, centro, pie = P, [], (0.0, -0.06), 0.0
    elif tipo == "pelota":
        llenos, huecos, centro, pie = [_circ(0, 0, 1.0, 160)], [], (0.0, 0.0), 0.0
    elif tipo == "numero":
        P, bb = _texto(o["caracter"], o["fuente_figura"])
        llenos, huecos, centro, pie = P, [], ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2), (bb[0] + bb[2]) / 2
    else:
        ll, hh, (tx, ty), px = SILUETAS[tipo]
        llenos = [Q for d in ll for Q in _camino(d)]
        huecos = [Q for d in hh for Q in _camino(d)]
        centro, pie = (tx, -ty), px
    if tipo != "numero":
        llenos = [_orientar(Q) for Q in llenos]
        huecos = [_orientar(Q, False) for Q in huecos]
    pts = [p for Q in llenos for p in Q]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = H / (y1 - y0)
    T = lambda x, y: ((x - pie) * k, (y - y0) * k)
    polys = [[T(x, y) for x, y in Q] for Q in llenos + huecos]
    return polys, T(*centro), ((x0 - pie) * k, (x1 - pie) * k), H, k, T


def _texto(txt, fid):
    t, err = mate_fuentes.limpiar(txt, fid)
    if err:
        raise ValueError(err)
    P = mate_fuentes.contornos(t, fid)
    pts = [p for Q in P for p in Q]
    if not pts:
        raise ValueError("No hay nada para dibujar en «%s»" % txt)
    return P, (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def _colocar(P, bb, s, cx, cy):
    x0, y0, x1, y1 = bb
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return [[((x - mx) * s + cx, (y - my) * s + cy) for x, y in Q] for Q in P]


def _campo(M, pasadas=2):
    """La máscara como campo ±1 suavizado con [1 2 1]/4 en x e y: el cero cae sobre el
    borde y el contorno sale liso, sin escalerita (mucho más rápido que la distancia).
    Las filas parejas (todo adentro o todo afuera) se comparten y no se recorren."""
    nx = len(M[0])
    NEG, POS = [-1.0] * nx, [1.0] * nx
    f = []
    for r in M:
        c = r.count(1)
        if c == 0:
            f.append(NEG)
        elif c == nx:
            f.append(POS)
        else:
            v = [2.0 * x - 1.0 for x in r]
            for _ in range(pasadas):
                v = [(a + 2 * b + c_) * 0.25 for a, b, c_ in zip([v[0]] + v[:-1], v, v[1:] + [v[-1]])]
            f.append(v)
    ny = len(f)
    for _ in range(pasadas):
        g = []
        for j in range(ny):
            a, b, c_ = f[max(j - 1, 0)], f[j], f[min(j + 1, ny - 1)]
            g.append(b if (a is b and b is c_) else [(x + 2 * y + z) * 0.25 for x, y, z in zip(a, b, c_)])
        f = g
    return f


def _lazos(f, g, eps, amin):
    return [P for P in (tc._simplificar(Q, eps) for Q in tc.lazos(f, g)) if abs(tc._area(P)) > amin]


def _juntar(*mallas):
    V, F = [], []
    for Vm, Fm in mallas:
        off = len(V)
        V += Vm
        F += [(a + off, b + off, c + off) for a, b, c in Fm]
    return V, F


def _caja(x0, y0, z0, x1, y1, z1, hueco=None):
    """Prisma de planta rectangular (con un hueco rectangular pasante opcional)."""
    L = [_rect(x0, y0, x1, y1)]
    if hueco:
        L.append(_rect(*hueco)[::-1])
    return tc.extruir(L, z0, z1)


# ===========================================================================
# LA FIGURA (acostada: x, y en la silueta, z el grosor)
# ===========================================================================
def _figura(o, Ds, wt):
    polys, (tcx, tcy), (fx0, fx1), H, k, T = _silueta(o["figura"], o)
    t, r = o["grosor"], o["relieve"]
    y_pie = Ds + o["tallo"]                         # donde arranca la figura (arriba de la base)
    polys = [[(x, y + y_pie) for x, y in Q] for Q in polys]
    tcy += y_pie
    W = fx1 - fx0
    res = max(0.16, max(W, H) / 520.0) * (1.0 if o["calidad"] == "preview" else 0.62)
    pad = 2.0
    g = tc.Grilla(min(fx0, -wt / 2) - pad, -pad, max(fx1, wt / 2) + pad, y_pie + H + pad, res)
    Fm = g.llenar(polys)                            # sólo la figura (para el borde y el texto)
    # un número de varias cifras: un zócalo abajo une las que quedaron sueltas
    zocalo = None
    _, ncomp, _ = tc.componentes(Fm, g.nx, g.ny)
    if ncomp > 1:
        zocalo = _rect(fx0, y_pie, fx1, y_pie + max(3.0, 0.07 * H))
        g.llenar([zocalo], Fm)
    # la espiga: de la punta de abajo (en la ranura) hasta adentro de la figura
    alto_cuello = y_pie + CUELLO.get(o["figura"], 0.32) * H
    # (lo que entra en la ranura es un prisma exacto, sin el redondeo de la grilla)
    cuello = _rect(-wt / 2, Ds + 0.3, wt / 2, alto_cuello)
    B = [bytearray(f) for f in Fm]
    g.llenar([cuello], B)
    # detalles en relieve sobre la figura: borde, texto corto y el dibujo de la pelota
    Din = tc.edt(Fm, g.nx, g.ny, 0)
    borde = o["borde"]
    T_ = g.vacia()
    if borde > 0:
        lim = (borde / res) ** 2
        for j in range(g.ny):
            Tj, Dj, Fj = T_[j], Din[j], Fm[j]
            for i in range(g.nx):
                if Fj[i] and Dj[i] <= lim:
                    Tj[i] = 1
    dibujo = []
    if o["figura"] == "pelota":
        R = H / 2.0
        cx, cy = 0.0, y_pie + R
        dibujo.append(_pentagono(cx, cy, 0.3 * R))
        for m in range(5):
            a = math.radians(90 + 72 * m)
            v = (cx + 0.3 * R * math.cos(a), cy + 0.3 * R * math.sin(a))
            e = (cx + 0.66 * R * math.cos(a), cy + 0.66 * R * math.sin(a))
            nx_, ny_ = -math.sin(a) * 0.03 * R, math.cos(a) * 0.03 * R
            dibujo.append([(v[0] - nx_, v[1] - ny_), (e[0] - nx_, e[1] - ny_), (e[0] + nx_, e[1] + ny_), (v[0] + nx_, v[1] + ny_)])
            b = math.radians(90 + 36 + 72 * m)
            dibujo.append(_pentagono(cx + 1.02 * R * math.cos(b), cy + 1.02 * R * math.sin(b), 0.36 * R, 90 + 36 + 72 * m + 36))
        g.llenar(dibujo, T_)
    letra = 0.0
    if o["texto_figura"]:
        P, bb = _texto(o["texto_figura"], o["fuente"])
        h0 = bb[3] - bb[1]
        lim_b = ((borde + MARGEN) / res) ** 2

        def entra(alto):
            M = g.llenar(_colocar(P, bb, alto / h0, tcx, tcy))
            for j in range(g.ny):
                Mj = M[j]
                if not any(Mj):
                    continue
                Dj, Fj = Din[j], Fm[j]
                for i in range(g.nx):
                    if Mj[i] and (not Fj[i] or Dj[i] < lim_b):
                        return False
            return True
        lo, hi = 0.5, H
        for _ in range(16):
            mid = (lo + hi) / 2
            if entra(mid):
                lo = mid
            else:
                hi = mid
        letra = lo
        g.llenar(_colocar(P, bb, letra / h0, tcx, tcy), T_)
    # nada de detalle fuera de la figura ni abajo del pie (la espiga entra lisa en la ranura)
    jmin = int((y_pie + 0.6 - g.y0) / res)
    for j in range(g.ny):
        Tj, Fj = T_[j], Fm[j]
        for i in range(g.nx):
            if Tj[i] and (j < jmin or not Fj[i]):
                Tj[i] = 0
    fB = _campo(B)
    eps = 0.03 if o["calidad"] == "normal" else 0.05
    lB = _lazos(fB, g, eps, 0.1)
    hay_detalle = any(any(f) for f in T_)
    lT = _lazos(_campo(T_), g, eps, 0.05) if hay_detalle else []
    Vf, Ff = _juntar(tc.extruir(lB, 0.0, t), tc.extruir([_rect(-wt / 2, 0.0, wt / 2, Ds + 0.8)], 0.0, t))
    Vd, Fd = tc.extruir(lT, t - 0.01, t + r) if lT else ([], [])
    info = {"ancho": fx1 - fx0, "alto": H, "y_pie": y_pie, "letra": letra,
            "zocalo": zocalo is not None, "res": res}
    return (Vf, Ff), (Vd, Fd), info, (g, B, Fm, T_)


# ===========================================================================
# LA BASE (parada: x ancho, y fondo con el frente en -y, z alto)
# ===========================================================================
def _base(o, t):
    BW, BH = o["base_ancho"], o["base_alto"]
    D = max(o["base_fondo"], t + 2 * PARED + 4)
    esc = o["base"] == "escalonada"
    hz = min(8.0, 0.28 * BH) if esc else 0.0         # alto del escalón de abajo
    ext = 5.0 if esc else 0.0
    Ds = min(12.0, BH - hz - 4.0)                    # profundidad de la ranura
    wt = max(10.0, min(30.0, BW - 2 * PARED - 6))    # ancho de la espiga (después se ajusta a la figura)
    return {"BW": BW, "BH": BH, "D": D, "hz": hz, "ext": ext, "Ds": Ds, "wt": wt}


def _malla_base(o, b, wt, t):
    BW, BH, D, hz, ext, Ds = b["BW"], b["BH"], b["D"], b["hz"], b["ext"], b["Ds"]
    c = o["holgura"]
    r = o["relieve"]
    grab = o["texto"] == "grabado"
    rf = r if grab else 0.0                          # en el grabado el frente es otra pieza
    yf = -D / 2.0
    ranura = (-wt / 2 - c, -t / 2 - c, wt / 2 + c, t / 2 + c)
    partes = []
    if hz > 0:
        partes.append(_caja(-BW / 2 - ext, yf - ext, 0.0, BW / 2 + ext, D / 2 + ext, hz))
    z0 = hz - 0.01 if hz > 0 else 0.0
    partes.append(_caja(-BW / 2, yf + rf, z0, BW / 2, D / 2, BH - Ds))
    partes.append(_caja(-BW / 2, yf + rf, BH - Ds - 0.01, BW / 2, D / 2, BH, hueco=ranura))
    # el texto del frente, dibujado en el plano (u = x, v = z)
    P1 = _texto(o["linea1"], o["fuente"]) if o["linea1"] else None
    P2 = _texto(o["linea2"], o["fuente"]) if o["linea2"] else None
    mx, my = 3.5, 2.6
    u0, u1, v0, v1 = -BW / 2 + mx, BW / 2 - mx, hz + my, BH - my
    k2, sep = 0.62, 0.22
    lineas = [x for x in (P1, P2) if x]
    rel = [1.0, k2] if len(lineas) == 2 else [1.0]
    # alto de la línea 1 que entra a lo ancho (cada línea) y a lo alto (todas)
    alto = (v1 - v0) / (sum(rel) + sep * (len(rel) - 1))
    for (P, bb), q in zip(lineas, rel):
        w = (bb[2] - bb[0]) / (bb[3] - bb[1])
        alto = min(alto, (u1 - u0) / (w * q))
    total = alto * (sum(rel) + sep * (len(rel) - 1))
    vc = (v0 + v1) / 2.0
    txt, v = [], vc + total / 2
    for (P, bb), q in zip(lineas, rel):
        h = alto * q
        txt += _colocar(P, bb, h / (bb[3] - bb[1]), 0.0, v - h / 2)
        v -= h + sep * alto
    res = 0.12 if o["calidad"] == "preview" else 0.075
    g = tc.Grilla(-BW / 2 - 1, hz - 1, BW / 2 + 1, BH + 1, res)
    M = g.llenar(txt)
    eps = 0.03 if o["calidad"] == "normal" else 0.04
    fT = _campo(M)
    lT = _lazos(fT, g, eps, 0.03)
    # (u, v, w) -> (x = u, y = yf - w, z = v): w > 0 sale para adelante (es una rotación,
    # las normales siguen para afuera)
    def frente(malla, w0, w1):
        Vm, Fm = tc.extruir(malla, w0, w1)
        return [(u, yf - w, vv) for u, vv, w in Vm], Fm
    if grab:
        cara = _rect(-BW / 2, hz - 0.005 if hz else 0.0, BW / 2, BH)
        fC = [[min(a, -b) for a, b in zip(fa, fb)] for fa, fb in zip(_campo_rect(g, cara), fT)]
        lC = _lazos(fC, g, eps, 0.03)
        partes.append(frente(lC, -r - 0.01, 0.0))           # el frente con las letras hundidas
        letras = frente(lT, -r, 0.0)                         # el relleno (sólo en dos colores)
    else:
        letras = frente(lT, -0.01, r)                        # en relieve, para adelante
    base = _juntar(*partes)
    return base, letras, {"letra": alto, "rf": rf, "grilla": g, "texto": M, "ranura": ranura}


def _campo_rect(g, R):
    """Distancia firmada a un rectángulo (exacta, sin grilla)."""
    (x0, y0), _, (x1, y1), _ = R
    out = []
    for j in range(g.ny):
        y = g.y0 + (j + 0.5) * g.res
        dy = min(y - y0, y1 - y)
        fila = []
        for i in range(g.nx):
            x = g.x0 + (i + 0.5) * g.res
            fila.append(min(dy, x - x0, x1 - x))
        out.append(fila)
    return out


# ===========================================================================
# TODO JUNTO
# ===========================================================================
def construir(opts):
    o = opciones(opts)
    t, r = o["grosor"], o["relieve"]
    b = _base(o, t)
    # la espiga: un tercio de la figura, sin pasarse de la base
    _, _, (fx0, fx1), H, _, _ = _silueta(o["figura"], o)
    wt = max(10.0, min(b["wt"], 0.3 * (fx1 - fx0)))
    (Vf, Ff), (Vd, Fd), fi, (g, B, Fm, Tm) = _figura(o, b["Ds"], wt)
    (Vb, Fb), (Vl, Fl), bi = _malla_base(o, b, wt, t)
    dos = o["colores"] == "dos"
    # piezas para imprimir
    piezas = []
    if dos and Vd:
        piezas += [("FIGURA", Vf, Ff), ("DETALLE", Vd, Fd)]
    else:
        V, F = _juntar((Vf, Ff), (Vd, Fd))
        piezas.append(("FIGURA", V, F))
    con_texto = o["texto"] == "relieve" or dos       # grabado en un color: no hay relleno
    if dos:
        piezas += [("BASE", Vb, Fb), ("TEXTO", Vl, Fl)]
    elif con_texto:
        V, F = _juntar((Vb, Fb), (Vl, Fl))
        piezas.append(("BASE", V, F))
    else:
        piezas.append(("BASE", Vb, Fb))
    # el trofeo armado: la figura parada con la espiga en la ranura, el relieve al frente
    z0 = b["BH"] - b["Ds"]

    def parar(V):
        return [(x, t / 2.0 - z, y + z0) for x, y, z in V]
    # (en el visor los detalles y el texto van siempre aparte, para verlos de su color)
    armado = [("FIGURA", parar(Vf), Ff)]
    if Vd:
        armado.append(("DETALLE", parar(Vd), Fd))
    armado.append(("BASE", Vb, Fb))
    if con_texto:
        armado.append(("TEXTO", Vl, Fl))
    allv = [v for _, V, _ in armado for v in V]
    medidas = [round(max(v[k] for v in allv) - min(v[k] for v in allv), 1) for k in range(3)]
    avisos = []
    if fi["ancho"] > 1.6 * b["BW"] + 2 * b["ext"]:
        avisos.append("La figura es mucho más ancha que la base: puede quedar inestable. Agrandá la base.")
    if max(fi["alto"] + fi["y_pie"], fi["ancho"]) > CAMA:
        avisos.append("La figura acostada mide más de %d mm: fijate que entre en la cama de tu impresora." % CAMA)
    if bi["letra"] < LETRA_MIN:
        avisos.append("El texto de la base queda de %.1f mm: con menos letras o una base más ancha se lee mejor." % bi["letra"])
    if o["texto_figura"] and fi["letra"] < LETRA_MIN:
        avisos.append("El texto de la figura queda de %.1f mm: probá con menos letras." % fi["letra"])
    if fi["zocalo"]:
        avisos.append("Las cifras van unidas por un zócalo abajo, para que la figura sea una sola pieza.")
    ranura = bi["ranura"]
    rep = {"figura": o["figura"], "base": o["base"], "linea1": o["linea1"], "linea2": o["linea2"],
           "texto_figura": o["texto_figura"], "caracter": o["caracter"] if o["figura"] == "numero" else "",
           "fuente": o["fuente"], "texto": o["texto"], "colores": o["colores"],
           "medidas_mm": medidas,
           "figura_mm": [round(fi["ancho"], 1), round(fi["alto"], 1), round(t, 1)],
           "figura_pieza_mm": [round(max(v[0] for v in Vf) - min(v[0] for v in Vf), 1),
                               round(max(v[1] for v in Vf) - min(v[1] for v in Vf), 1)],
           "base_mm": [round(b["BW"] + 2 * b["ext"], 1), round(b["D"] + 2 * b["ext"], 1), round(b["BH"], 1)],
           "espiga_mm": [round(wt, 1), round(t, 1), round(b["Ds"], 1)],
           "ranura_mm": [round(ranura[2] - ranura[0], 2), round(ranura[3] - ranura[1], 2), round(b["Ds"], 1)],
           "holgura_mm": o["holgura"], "tallo_mm": o["tallo"], "relieve_mm": r, "borde_mm": o["borde"],
           "letra_base_mm": round(bi["letra"], 1), "letra_figura_mm": round(fi["letra"], 1),
           "cambio_mm": round(t, 2) if dos and Vd else None,
           "piezas": [p[0] for p in piezas],
           "triangulos": sum(len(F) for _, _, F in piezas), "avisos": avisos}
    return {"piezas": piezas, "armado": armado, "reporte": rep,
            "figura": {"grilla": g, "solido": B, "silueta": Fm, "detalle": Tm, "info": fi},
            "base": {"grilla": bi["grilla"], "texto": bi["texto"], "medidas": b}}
