# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
CHAPITAS PARA COLLARES (perros y gatos) — una placa con forma, argolla y el nombre
==================================================================================
Se imprime acostada. La forma (hueso, gato, corazón, círculo, óvalo o pescado) lleva
arriba una argolla con su agujero para la argollita del collar; el nombre (y una segunda
línea opcional, por ejemplo el teléfono) va en el centro, del tamaño más grande que entra
sin pisar el borde ni las patitas.

    Letras en "relieve" (arriba de la base) o "grabado" (hundidas en la placa).
    Colores: "uno"; "doble" (relieve en dos alturas: pausa y cambio de filamento a mano);
    "ams" (misma altura: las letras de color en las últimas capas, para AMS / multicolor).

Usa la grilla, los contornos suaves y la extrusión del motor del topper.

    construir(opts) -> {"piezas": [(nombre, V, F)], "reporte": {...}}
"""
import math

import mate_fuentes
import topper_core as tc

TAU = 2.0 * math.pi
FORMAS = [("hueso", "Hueso"), ("gato", "Gato"), ("corazon", "Corazón"), ("circulo", "Círculo"),
          ("ovalo", "Óvalo"), ("pescado", "Pescado")]
TEXTOS = [("relieve", "En relieve"), ("grabado", "Grabado")]
COLORES = [("uno", "Un color"), ("doble", "Dos colores · dos alturas (cambio a mano)"),
           ("ams", "Dos colores · misma altura (AMS / multicolor)")]
CON_PATITAS = ("hueso", "ovalo")
DEFECTO = {"forma": "hueso", "nombre": "Roma", "linea2": "", "fuente": "lilita_one", "ancho": 45.0,
           "grosor": 3.0, "relieve": 1.0, "texto": "relieve", "colores": "uno", "borde": 1.4,
           "patitas": True, "agujero": 4.5, "calidad": "preview"}
LIMITES = {"ancho": (28.0, 70.0), "grosor": (2.0, 5.0), "relieve": (0.6, 2.0), "borde": (0.0, 3.0),
           "agujero": (3.0, 7.0), "caracteres": 14, "caracteres2": 18}
MARGEN = 1.2            # mm entre las letras y el borde o las patitas
LETRA_MIN = 4.0         # mm: más chica, la letra no se lee bien impresa


def _f(v, d, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    return max(lo, min(hi, v))


def opciones(o):
    o = dict(DEFECTO, **(o or {}))
    if o.get("forma") not in [k for k, _ in FORMAS]:
        raise ValueError("forma desconocida: %s" % o.get("forma"))
    if o.get("texto") not in [k for k, _ in TEXTOS]:
        raise ValueError("estilo de letra desconocido: %s" % o.get("texto"))
    if o.get("colores") not in [k for k, _ in COLORES]:
        raise ValueError("colores desconocidos: %s" % o.get("colores"))
    if o["texto"] == "grabado" and o["colores"] == "doble":
        o["colores"] = "ams"                     # grabado en dos colores = relleno al ras
    if o.get("fuente") not in tc.IDS:
        raise ValueError("Tipografía desconocida: %s" % o.get("fuente"))
    o["nombre"] = " ".join(str(o.get("nombre") or "").split())
    o["linea2"] = " ".join(str(o.get("linea2") or "").split())
    if not o["nombre"]:
        raise ValueError("Escribí el nombre de tu mascota")
    if len(o["nombre"]) > LIMITES["caracteres"]:
        raise ValueError("El nombre puede tener hasta %d letras" % LIMITES["caracteres"])
    if len(o["linea2"]) > LIMITES["caracteres2"]:
        raise ValueError("La segunda línea puede tener hasta %d caracteres" % LIMITES["caracteres2"])
    for k in ("ancho", "grosor", "relieve", "borde", "agujero"):
        o[k] = _f(o.get(k), DEFECTO[k], *LIMITES[k])
    o["relieve"] = min(o["relieve"], o["grosor"] - 0.8) if o["colores"] == "ams" or o["texto"] == "grabado" else o["relieve"]
    o["patitas"] = bool(o.get("patitas")) and o["forma"] in CON_PATITAS
    o["calidad"] = o.get("calidad") if o.get("calidad") in ("preview", "normal") else "preview"
    return o


# ===========================================================================
# FORMAS (mm, centradas, antihorario) y dónde va el texto
# ===========================================================================
def _circ(cx, cy, r, n=96):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def _elipse(cx, cy, a, b, n=120):
    return [(cx + a * math.cos(TAU * k / n), cy + b * math.sin(TAU * k / n)) for k in range(n)]


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def forma(tipo, W):
    """-> (polígonos que se unen, centro del texto (x, y), patitas [(x, y, tamaño)]),
    escalado para que la chapita mida justo W de ancho."""
    polys, (tx, ty), pat = _forma(tipo, W)
    xs = [p[0] for Q in polys for p in Q]
    k = W / (max(xs) - min(xs))
    mx = (max(xs) + min(xs)) / 2.0
    polys = [[((x - mx) * k, y * k) for x, y in Q] for Q in polys]
    return polys, ((tx - mx) * k, ty * k), [((x - mx) * k, y * k, d * k) for x, y, d in pat]


def _forma(tipo, W):
    if tipo == "hueso":
        H = 0.54 * W
        r = 0.26 * H                        # radio de las cuatro bolitas
        cxs, cys = W / 2 - r, H / 2 - r
        polys = [_rect(-cxs, -0.27 * H, cxs, 0.27 * H)] + [_circ(sx * cxs, sy * cys, r) for sx in (-1, 1) for sy in (-1, 1)]
        return polys, (0.0, 0.0), [(cxs + 0.05 * r, cys + 0.02 * r, 1.25 * r), (-cxs - 0.05 * r, -cys - 0.02 * r, 1.25 * r)]
    if tipo == "gato":
        R = 0.4 * W
        oreja = 0.22 * W
        polys = [_circ(0, 0, R),
                 [(-0.40 * W, 0.05 * W), (-0.08 * W, 0.30 * W), (-0.34 * W, 0.30 * W + oreja)],
                 [(0.40 * W, 0.05 * W), (0.34 * W, 0.30 * W + oreja), (0.08 * W, 0.30 * W)]]
        return polys, (0.0, -0.02 * W), []
    if tipo == "corazon":
        k = W / 32.0
        pts = []
        for i in range(160):
            t = TAU * i / 160
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((x * k, y * k))
        return [pts], (0.0, -0.06 * W), []          # el centro del corazón, lejos del ojal
    if tipo == "circulo":
        return [_circ(0, 0, W / 2, 140)], (0.0, 0.0), []
    if tipo == "ovalo":
        H = 0.6 * W
        r = H / 2
        polys = [_rect(-W / 2 + r, -r, W / 2 - r, r), _circ(-W / 2 + r, 0, r), _circ(W / 2 - r, 0, r)]
        return polys, (0.0, 0.0), [(-W / 2 + 0.62 * r, 0.0, 0.62 * r), (W / 2 - 0.62 * r, 0.0, 0.62 * r)]
    if tipo == "pescado":
        cuerpo = _elipse(-0.08 * W, 0, 0.36 * W, 0.25 * W)
        cola = [(0.12 * W, -0.09 * W), (0.5 * W, -0.26 * W), (0.42 * W, 0.0), (0.5 * W, 0.26 * W), (0.12 * W, 0.09 * W)]
        return [cuerpo, cola], (-0.1 * W, 0.0), []
    raise ValueError("forma desconocida: %s" % tipo)


def patita(cx, cy, d):
    """Huella de pata (almohadilla + 4 deditos) de diámetro d, un poco inclinada."""
    s = d / 2.0
    polys = [_elipse(cx, cy - 0.22 * s, 0.52 * s, 0.42 * s, 60)]
    for ang, rr in ((-58, 0.2), (-22, 0.22), (22, 0.22), (58, 0.2)):
        a = math.radians(90 + ang)
        polys.append(_elipse(cx + 0.62 * s * math.cos(a), cy + 0.62 * s * math.sin(a) - 0.05 * s, rr * s, rr * 1.2 * s, 36))
    return polys


def _texto(txt, fid):
    t, err = mate_fuentes.limpiar(txt, fid)
    if err:
        raise ValueError(err)
    P = mate_fuentes.contornos(t, fid)
    pts = [p for Q in P for p in Q]
    return P, (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def _colocar(P, bb, s, cx, cy):
    x0, y0, x1, y1 = bb
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return [[((x - mx) * s + cx, (y - my) * s + cy) for x, y in Q] for Q in P]


def _suavizar(f, pasadas=2):
    """Filtro [1 2 1]/4 en x e y sobre la distancia firmada: saca la escalerita de la grilla
    y el contorno sale liso (las paredes de la chapita no quedan rayadas)."""
    ny, nx = len(f), len(f[0])
    for _ in range(pasadas):
        f = [[(r[max(i - 1, 0)] + 2 * r[i] + r[min(i + 1, nx - 1)]) * 0.25 for i in range(nx)] for r in f]
        f = [[(f[max(j - 1, 0)][i] + 2 * f[j][i] + f[min(j + 1, ny - 1)][i]) * 0.25 for i in range(nx)]
             for j in range(ny)]
    return f


# ===========================================================================
# TODO JUNTO
# ===========================================================================
def construir(opts):
    o = opciones(opts)
    W = o["ancho"]
    polys, (tcx, tcy), lugares = forma(o["forma"], W)
    pts = [p for Q in polys for p in Q]
    ext = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
    res = 0.12 if o["calidad"] == "preview" else 0.07
    # argolla arriba al centro: un ojal de 2,2 mm de pared alrededor del agujero
    ra = o["agujero"] / 2.0
    re = ra + 2.2
    g0 = tc.Grilla(ext[0] - 2, ext[1] - 2, ext[2] + 2, ext[3] + 2, res)
    F0 = g0.llenar(polys)
    i0 = int((0.0 - g0.x0) / res)
    techo = max(j for j in range(g0.ny) if F0[j][i0])
    y_techo = g0.y0 + (techo + 1) * res
    ay = y_techo + re - 0.8 * re                      # el ojal se encima con la forma
    ojal = _circ(0.0, ay, re)
    agujero = _circ(0.0, ay, ra, 60)
    ext[3] = max(ext[3], ay + re)
    pad = 2.0
    g = tc.Grilla(ext[0] - pad, ext[1] - pad, ext[2] + pad, ext[3] + pad, res)
    B = g.llenar(polys + [ojal])
    Hh = g.llenar([agujero])
    for j in range(g.ny):
        Bj, Hj = B[j], Hh[j]
        for i in range(g.nx):
            if Hj[i]:
                Bj[i] = 0
    # distancia de cada celda al afuera de la placa (para el borde y para que entre el texto)
    Din = tc.edt(B, g.nx, g.ny, 0)
    # el borde en relieve sigue el contorno (no en el grabado)
    borde = o["borde"] if o["texto"] == "relieve" else 0.0
    # patitas
    PAT = []
    for x, y, d in (lugares if o["patitas"] else []):
        PAT += patita(x, y, d)
    Pm = g.llenar(PAT) if PAT else [bytearray(g.nx) for _ in range(g.ny)]
    Dp = tc.edt(Pm, g.nx, g.ny, 1) if PAT else None
    # la zona del ojal no es para letras
    zona_ojal = g.llenar([_circ(0.0, ay, re + MARGEN)])
    lim_borde = ((borde + MARGEN) / res) ** 2
    lim_pat = (MARGEN / res) ** 2

    def entra(polys_txt):
        M = g.llenar(polys_txt)
        for j in range(g.ny):
            Mj = M[j]
            if not any(Mj):
                continue
            Dj, Zj = Din[j], zona_ojal[j]
            Dpj = Dp[j] if Dp else None
            for i in range(g.nx):
                if Mj[i] and (Dj[i] < lim_borde or Zj[i] or (Dpj is not None and Dpj[i] < lim_pat)):
                    return False
        return True

    # texto: el nombre lo más grande que entre (y la segunda línea, al 55 % de alto)
    P1, bb1 = _texto(o["nombre"], o["fuente"])
    h1 = bb1[3] - bb1[1]
    P2, bb2 = (_texto(o["linea2"], o["fuente"]) if o["linea2"] else (None, None))
    k2, sep = 0.55, 0.18

    def maquetar(alto):
        s1 = alto / h1
        if P2 is None:
            return _colocar(P1, bb1, s1, tcx, tcy)
        alto2 = k2 * alto
        s2 = alto2 / (bb2[3] - bb2[1])
        total = alto + sep * alto + alto2
        y1 = tcy + total / 2 - alto / 2
        y2 = tcy - total / 2 + alto2 / 2
        return _colocar(P1, bb1, s1, tcx, y1) + _colocar(P2, bb2, s2, tcx, y2)
    lo, hi = 1.0, (ext[3] - ext[1])
    for _ in range(18):
        mid = (lo + hi) / 2
        if entra(maquetar(mid)):
            lo = mid
        else:
            hi = mid
    alto = lo
    TXT = maquetar(alto)
    T = g.llenar(TXT + PAT)
    # lo que va de color / en relieve: letras, patitas y el borde
    if borde > 0:
        lim = (borde / res) ** 2
        for j in range(g.ny):
            Tj, Dj, Bj = T[j], Din[j], B[j]
            for i in range(g.nx):
                if Bj[i] and Dj[i] <= lim:
                    Tj[i] = 1
    for j in range(g.ny):                                   # nada fuera de la placa ni en el agujero
        Tj, Bj = T[j], B[j]
        for i in range(g.nx):
            if Tj[i] and not Bj[i]:
                Tj[i] = 0
    fB = _suavizar(tc.campo(B, g))
    fT = _suavizar(tc.campo(T, g))
    eps = 0.03 if o["calidad"] == "normal" else 0.05
    lazos = lambda f, amin: [P for P in (tc._simplificar(Q, eps) for Q in tc.lazos(f, g)) if abs(tc._area(P)) > amin]
    lB, lT = lazos(fB, 0.08), lazos(fT, 0.04)
    h, r = o["grosor"], o["relieve"]
    piezas = []
    if o["texto"] == "relieve" and o["colores"] != "ams":
        Vb, Fb = tc.extruir(lB, 0.0, h)
        Vt, Ft = tc.extruir(lT, h - 0.01, h + r)
        if o["colores"] == "uno":
            off = len(Vb)
            piezas = [("CHAPITA", Vb + Vt, Fb + [(a + off, b + off, c + off) for a, b, c in Ft])]
        else:
            piezas = [("CHAPITA", Vb, Fb), ("LETRAS", Vt, Ft)]
    else:
        # al ras (AMS) o grabado: la base hasta h - r y, arriba, la placa sin las letras
        zc = h - r
        fr = [[min(a, -b) for a, b in zip(fa, fb)] for fa, fb in zip(fB, fT)]
        lR = lazos(fr, 0.04)
        Vb, Fb = tc.extruir(lB, 0.0, zc)
        Vr, Fr = tc.extruir(lR, zc - 0.01, h)
        off = len(Vb)
        Vb, Fb = Vb + Vr, Fb + [(a + off, b + off, c + off) for a, b, c in Fr]
        if o["colores"] == "ams":
            Vt, Ft = tc.extruir(lT, zc, h)
            piezas = [("CHAPITA", Vb, Fb), ("LETRAS", Vt, Ft)]
        else:
            piezas = [("CHAPITA", Vb, Fb)]
    xs = [v[0] for _, V, _ in piezas for v in V]
    ys = [v[1] for _, V, _ in piezas for v in V]
    zs = [v[2] for _, V, _ in piezas for v in V]
    avisos = []
    if alto < LETRA_MIN:
        avisos.append("La letra queda de %.1f mm: con un nombre más corto, otra tipografía o una chapita más grande se lee mejor" % alto)
    rep = {"forma": o["forma"], "nombre": o["nombre"], "linea2": o["linea2"], "fuente": o["fuente"],
           "texto": o["texto"], "colores": o["colores"], "patitas": o["patitas"], "borde_mm": borde,
           "letra_mm": round(alto, 1), "agujero_mm": round(o["agujero"], 1),
           "grosor_mm": h, "relieve_mm": r,
           "cambio_mm": round(h, 2) if (o["texto"] == "relieve" and o["colores"] == "doble") else None,
           "capa_color_mm": round(r, 2) if o["colores"] == "ams" else None,
           "medidas_mm": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), round(max(zs) - min(zs), 2)],
           "triangulos": sum(len(F) for _, _, F in piezas), "res_mm": res, "avisos": avisos,
           "ojal": {"x": 0.0, "y": round(ay, 3), "r_agujero": ra, "r_ojal": re}}
    return {"piezas": piezas, "reporte": rep, "grilla": g, "placa": B, "letras": T}
