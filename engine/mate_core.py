# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
MATE CON HUECO — Motor de mates imperiales para imprimir en 3D
==============================================================
Python puro (sin numpy ni Rhino): el mismo archivo corre en el navegador
(Pyodide), en CPython para los tests y en Grasshopper.

Genera el cuerpo de un mate (varios modelos) con el hueco exacto de un inserto
(polímero escalonado, polímero base, los dos o un STL propio de revolución) como UNA
malla cerrada, sin booleanas: piel exterior → borde de la boca → pared del hueco
→ fondo del hueco. El mate se agranda solo (autoajuste) hasta tener la pared y
el fondo mínimos pedidos.

    build_mate(opts) -> {"V", "F", "shells", "report", "params"}

opts = {"tipo": "imperial_clasico", "inserto": "polimero", "holgura": 0.2,
        "pared": 3.0, "piso": 4.0, "autoajuste": True, "altura": 0, "diam_max": 0,
        "diam_boca": 0, "hundir": 0, "calidad": "preview", "stl_propio": b"..."}

Unidades: milímetros. Z hacia arriba, eje del mate en (0, 0).
"""
from __future__ import division
import math
import struct

MATE_VERSION = "1.0.0"
TAU = 2.0 * math.pi
PLA_G_CM3 = 1.24
RAMPA_MEDALLON = 1.2   # mm en los que el medallón baja hasta su profundidad

# ---------------------------------------------------------------------------
# INSERTOS: perfil exacto (r, d) desde el centro del fondo cerrado hasta el
# centro de la abertura; d = profundidad desde la abertura (0 = cara del mate).
# Extraídos de Polimero_Mate.stl y Adaptador_Polimero_2.stl (sólidos de revolución).
# ---------------------------------------------------------------------------
INSERTOS = {
    "polimero": {
        "nombre": "Polímero escalonado",
        "perfil": [(0.0, 70.3), (23.35, 70.3), (23.35, 65.8), (25.86, 63.3),
                   (25.86, 45.7), (28.34, 43.3), (28.34, 26.05), (31.12, 23.3),
                   (31.15, 8.0), (31.18, 4.0), (34.92, 4.0), (34.92, 0.0),
                   (0.0, 0.0)],
    },
    "adaptador": {
        "nombre": "Polímero base",
        "perfil": [(0.0, 85.0), (14.5, 85.0), (14.5, 79.0), (28.0, 79.0),
                   (28.0, 20.0), (42.0, 20.0), (42.0, 0.0), (0.0, 0.0)],
    },
}
INSERTOS_WEB = [("polimero", "Polímero escalonado"), ("adaptador", "Polímero base"),
                ("ambos", "Los dos juntos"), ("propio", "Mi archivo STL")]

# ---------------------------------------------------------------------------
# MODELOS: perfil de la panza normalizado (z 0..1, r / Rmax); "boca" = radio de boca.
# extras: anillos (bandas en relieve), aletas, facetas, medallones (zonas rebajadas
# para poner un relieve propio).
# ---------------------------------------------------------------------------
TIPOS = [
    {"id": "imperial_clasico", "nombre": "Imperial clásico", "H": 120.0, "Dmax": 95.0,
     "Dboca": 80.0, "Hpie": 14.0, "Dpie": 70.0, "Dtallo": 48.0, "lineal": False,
     "panza": [(0.0, 0.55), (0.10, 0.84), (0.32, 1.0), (0.56, 0.97), (0.80, 0.88),
               (0.94, "boca"), (1.0, "boca")]},
    {"id": "imperial_camionero", "nombre": "Imperial camionero", "H": 112.0, "Dmax": 108.0,
     "Dboca": 90.0, "Hpie": 12.0, "Dpie": 82.0, "Dtallo": 60.0, "lineal": False,
     "panza": [(0.0, 0.62), (0.12, 0.90), (0.38, 1.0), (0.66, 0.98), (0.90, "boca"),
               (1.0, "boca")]},
    {"id": "imperial_torpedo", "nombre": "Imperial torpedo", "H": 140.0, "Dmax": 90.0,
     "Dboca": 80.0, "Hpie": 14.0, "Dpie": 64.0, "Dtallo": 40.0, "lineal": False,
     "panza": [(0.0, 0.45), (0.16, 0.72), (0.46, 0.95), (0.76, 1.0), (0.93, "boca"),
               (1.0, "boca")]},
    {"id": "imperial_copa", "nombre": "Imperial copa", "H": 150.0, "Dmax": 96.0,
     "Dboca": 82.0, "Hpie": 38.0, "Dpie": 76.0, "Dtallo": 26.0, "lineal": False,
     "panza": [(0.0, 0.30), (0.12, 0.74), (0.40, 1.0), (0.74, 0.97), (0.94, "boca"),
               (1.0, "boca")]},
    {"id": "imperial_pera", "nombre": "Imperial pera", "H": 125.0, "Dmax": 100.0,
     "Dboca": 80.0, "Hpie": 14.0, "Dpie": 72.0, "Dtallo": 50.0, "lineal": False,
     "panza": [(0.0, 0.58), (0.14, 0.92), (0.32, 1.0), (0.56, 0.90), (0.78, 0.82),
               (0.93, "boca"), (1.0, "boca")]},
    {"id": "cilindrico", "nombre": "Moderno cilíndrico", "H": 110.0, "Dmax": 86.0,
     "Dboca": 84.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.90), (0.05, 1.0), (0.95, 1.0), (1.0, "boca")]},
    {"id": "cohete", "nombre": "Cohete", "H": 135.0, "Dmax": 92.0, "Dboca": 84.0,
     "Hpie": 24.0, "Dpie": 22.0, "Dtallo": 22.0, "lineal": False,
     "panza": [(0.0, 0.30), (0.12, 0.72), (0.35, 0.96), (0.60, 1.0), (0.85, 0.97),
               (1.0, "boca")],
     "extras": {"aletas": {"n": 3, "espesor": 6.0, "alcance": 14.0, "alto": 0.45},
                "anillos": [(0.74, 0.98, 2.0)]}},
    {"id": "vaso_redondeado", "nombre": "Vaso redondeado", "H": 105.0, "Dmax": 96.0,
     "Dboca": 86.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.80), (0.03, 0.93), (0.12, 0.995), (0.30, 1.0), (0.70, 0.96),
               (1.0, "boca")],
     "extras": {"medallones": {"n": 1, "radio": 30.0, "z": 0.50, "prof": 1.2}}},
    {"id": "camionero_anillado", "nombre": "Camionero anillado", "H": 120.0, "Dmax": 92.0,
     "Dboca": 88.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 1.0), (0.08, 0.97), (0.35, 0.90), (0.70, 0.93), (0.90, 0.99),
               (1.0, "boca")],
     "extras": {"anillos": [(0.0, 0.05, 1.5), (0.93, 1.0, 1.5)]}},
    {"id": "facetado", "nombre": "Facetado", "H": 110.0, "Dmax": 104.0, "Dboca": 80.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.62), (0.42, 1.0), (1.0, "boca")],
     "extras": {"facetas": {"n": 6, "alternado": True},
                "medallones": {"n": 3, "radio": 14.0, "z": 0.27, "prof": 1.2}}},
    # --- modelos nuevos (fotos de referencia de Yoel, 2026-10-30)
    {"id": "triangular", "nombre": "Triangular", "H": 112.0, "Dmax": 92.0, "Dboca": 92.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.80), (0.04, 0.88), (0.20, 0.93), (0.60, 0.97), (0.90, 1.0),
               (1.0, "boca")],
     "extras": {"lobulos": {"n": 3, "amp": 0.13, "agudo": 1.4}}},
    {"id": "patitas", "nombre": "Con patitas", "H": 118.0, "Dmax": 98.0, "Dboca": 82.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.66), (0.10, 0.80), (0.30, 0.98), (0.48, 1.0), (0.72, 0.90),
               (0.86, 0.82), (0.93, 0.86), (1.0, "boca")],
     "extras": {"lobulos": {"n": 4, "amp": 0.16, "agudo": 3.0, "z1": 0.24, "fase": 0.5},
                "medallones": {"n": 1, "radio": 24.0, "z": 0.55, "prof": 1.2}}},
    {"id": "lowpoly_torcido", "nombre": "Low poly torcido", "H": 116.0, "Dmax": 100.0,
     "Dboca": 96.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.74), (0.18, 0.93), (0.40, 1.0), (0.62, 0.95), (0.84, 0.86),
               (1.0, "boca")],
     "extras": {"poliedro": {"n": 7, "giro": 0.3}}},
    {"id": "vaso_conico", "nombre": "Vaso cónico", "H": 110.0, "Dmax": 90.0, "Dboca": 90.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.80), (1.0, "boca")],
     "extras": {"anillos": [(0.0, 0.08, 2.5)]}},
    {"id": "lowpoly_irregular", "nombre": "Low poly irregular", "H": 118.0, "Dmax": 100.0,
     "Dboca": 84.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.72), (0.22, 0.94), (0.46, 1.0), (0.72, 0.86), (0.88, 0.80),
               (1.0, "boca")],
     "extras": {"poliedro": {"n": 7, "giro": 0.5, "azar_r": 0.07, "azar_th": 0.22,
                             "semilla": 7}}},
    {"id": "labio_grueso", "nombre": "Labio grueso", "H": 112.0, "Dmax": 100.0,
     "Dboca": 84.0, "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.70), (0.06, 0.86), (0.36, 1.0), (0.66, 0.93), (0.80, 0.82),
               (0.84, 0.90), (0.95, 0.90), (1.0, "boca")],
     "extras": {"medallones": {"n": 1, "radio": 16.0, "z": 0.45, "prof": 1.2}}},
    {"id": "rombos", "nombre": "Cubos 3D", "H": 112.0, "Dmax": 92.0, "Dboca": 92.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.88), (0.30, 0.90), (0.70, 0.94), (1.0, "boca")],
     "extras": {"rombos": {"columnas": 10, "alto": 3.0}}},
]
TIPOS_POR_ID = dict((t["id"], t) for t in TIPOS)

LIMITES = {"pared_min": 1.6, "pared_max": 10.0, "piso_min": 2.0, "piso_max": 30.0,
           "holgura_max": 1.5, "hundir_max": 30.0, "escala_max": 3.0}


# ===========================================================================
# PERFILES 2D (plano meridiano r–z)
# ===========================================================================
def _num(v, defecto):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return defecto
    return f if f > 0 else defecto


def catmull_rom(pts, pasos=14):
    """Spline que pasa por los puntos (r, z)."""
    if len(pts) < 3:
        return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(pasos):
            t = k / float(pasos)
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                             for j in range(2)))
    out.append(tuple(pts[-1]))
    return out


def tipo(tid):
    if isinstance(tid, int) or (isinstance(tid, str) and tid.isdigit()):
        return TIPOS[int(tid) % len(TIPOS)]
    if tid not in TIPOS_POR_ID:
        raise ValueError("modelo de mate desconocido: %s" % tid)
    return TIPOS_POR_ID[tid]


def parametros_tipo(tid, H=None, Dmax=None, Dboca=None, Hpie=None, Dpie=None):
    T = tipo(tid)
    p = dict(T)
    p["H"] = _num(H, T["H"])
    p["Dmax"] = _num(Dmax, T["Dmax"])
    p["Dboca"] = _num(Dboca, T["Dboca"])
    p["Hpie"] = T["Hpie"] if (Hpie is None or float(Hpie) < 0) else float(Hpie)
    p["Dpie"] = _num(Dpie, T["Dpie"])
    return p


def _control(p, s):
    H, Hpie = p["H"], p["Hpie"]
    Rmax, Rboca = p["Dmax"] / 2.0 * s, p["Dboca"] / 2.0 * s
    return [((Rboca if tr == "boca" else tr * Rmax), Hpie + tz * (H - Hpie))
            for tz, tr in p["panza"]]


def perfil_mate(p, s=1.0):
    """Perfil exterior denso desde (0, 0) hasta (0, H). s = escala radial."""
    H, Hpie = p["H"], p["Hpie"]
    ctrl = _control(p, s)
    panza = ctrl if p["lineal"] else catmull_rom(ctrl)
    r0 = panza[0][0]
    if Hpie > 0:
        Rpie, Rt = p["Dpie"] / 2.0 * s, p["Dtallo"] / 2.0 * s
        pie = [(0.0, 0.0), (Rpie, 0.0), (Rpie, 0.22 * Hpie), (Rt, 0.70 * Hpie), (Rt, Hpie)]
        if abs(Rt - r0) > 1e-6:
            pie.append((r0, Hpie))
    else:
        pie = [(0.0, 0.0), (r0, 0.0)]
    return pie[:-1] + panza + [(0.0, H)]


def perfil_hueco(canon, holgura=0.0, hundir=0.0, sobre=0.0):
    """Holgura radial (y en el fondo) y extensión de la abertura hasta la cara."""
    dmax = max(d for _, d in canon)
    out = []
    for r, d in canon[:-1]:
        rr = r + holgura if r > 1e-9 else 0.0
        dd = d + holgura if abs(d - dmax) < 1e-6 else d
        out.append((rr, dd))
    r_ab = out[-1][0]
    e = hundir + sobre
    if e > 1e-9:
        out.append((r_ab, -e))
    out.append((0.0, -e))
    return out


def colocar_hueco(perfil_rd, z_tope, hundir=0.0):
    """(r, d) -> (r, z) con la abertura en la boca."""
    return [(r, z_tope - hundir - d) for r, d in perfil_rd]


def envolvente(canons):
    """Hueco único de varios insertos coaxiales que abren en la boca: radio máximo
    a cada profundidad (con escalones y cruces)."""
    if len(canons) == 1:
        return list(canons[0])
    caminos = [list(reversed(c[1:-1])) for c in canons]     # abertura -> fondo

    def ev(cam, d, lado):
        D = cam[-1][1]
        if d < -1e-9 or d > D + 1e-9:
            return 0.0
        idx = [i for i, (r, dd) in enumerate(cam) if abs(dd - d) < 1e-9]
        if idx:
            if lado == "a":
                return cam[idx[0]][0]
            return cam[idx[-1]][0] if d < D - 1e-9 else 0.0
        for (r1, d1), (r2, d2) in zip(cam, cam[1:]):
            if d1 < d < d2:
                return r1 + (d - d1) / (d2 - d1) * (r2 - r1)
        return 0.0

    bps = sorted(set(round(d, 6) for cam in caminos for _, d in cam))
    extra = []
    for b0, b1 in zip(bps, bps[1:]):
        lin = [(ev(c, b0, "b"), ev(c, b1, "a")) for c in caminos]
        for i in range(len(lin)):
            for j in range(i + 1, len(lin)):
                a0, a1 = lin[i]
                c0, c1 = lin[j]
                den = (a1 - a0) - (c1 - c0)
                if abs(den) > 1e-12:
                    t = (c0 - a0) / den
                    if 1e-6 < t < 1 - 1e-6:
                        extra.append(b0 + t * (b1 - b0))
    bps = sorted(set(bps + [round(x, 6) for x in extra]))
    cam = []
    for d in bps:
        ra = max(ev(c, d, "a") for c in caminos)
        rb = max(ev(c, d, "b") for c in caminos)
        cam.append((ra, d))
        if abs(rb - ra) > 1e-9:
            cam.append((rb, d))
    cam = [q for q in cam if not (q[0] < 1e-9 and q[1] < bps[-1] - 1e-9)]
    if cam[-1][0] < 1e-9:
        cam.pop()
    canon = [(0.0, bps[-1])] + list(reversed(cam)) + [(0.0, 0.0)]
    limpio = [canon[0]]
    for q in canon[1:]:
        if abs(q[0] - limpio[-1][0]) > 1e-9 or abs(q[1] - limpio[-1][1]) > 1e-9:
            limpio.append(q)
    return limpio


def _dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def _dentro(px, py, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            if px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                c = not c
    return c


def _muestrear(poly, paso=0.5):
    pts = []
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / paso))
        for k in range(n):
            t = k / float(n)
            pts.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    pts.append(poly[-1])
    return pts


def pared_2d(denso, hueco_rz, H):
    """Pared mínima en el plano meridiano entre el perfil exterior (de (0,0) a
    (0,H)) y el hueco que abre en la boca. Negativo = el hueco se sale."""
    segs = list(zip(denso[:-2], denso[1:-1]))          # sin la tapa (se corta)
    mn = 1e9
    for px, py in _muestrear(hueco_rz, 0.5):
        if px < 1e-6 or py >= H - 1e-6 or py <= 1e-6:
            continue
        d = min(_dist_seg(px, py, a[0], a[1], b[0], b[1]) for a, b in segs)
        if not _dentro(px, py, denso):
            d = -d
        mn = min(mn, d)
    return mn


def piso_2d(hueco_rz):
    return min(z for _, z in hueco_rz)


# ===========================================================================
# STL (lectura de insertos propios)
# ===========================================================================
def leer_stl(data):
    """bytes de un STL (binario o ASCII) -> lista de triángulos."""
    tris = []
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + 50 * n == len(data):
            for i in range(n):
                v = struct.unpack("<12f", data[84 + 50 * i: 84 + 50 * i + 48])
                tris.append(((v[3], v[4], v[5]), (v[6], v[7], v[8]), (v[9], v[10], v[11])))
            return tris
    cur = []
    for linea in data.decode("latin-1").splitlines():
        s = linea.strip().split()
        if len(s) == 4 and s[0].lower() == "vertex":
            cur.append(tuple(float(x) for x in s[1:]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    if not tris:
        raise ValueError("el archivo no parece un STL válido")
    return tris


def volumen_tris(tris):
    v = 0.0
    for a, b, c in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) +
              a[2] * (b[0] * c[1] - b[1] * c[0]))
    return abs(v) / 6.0


def volumen_revolucion(rz):
    v = 0.0
    for i in range(len(rz)):
        r1, z1 = rz[i]
        r2, z2 = rz[(i + 1) % len(rz)]
        v += (z2 - z1) * (r1 * r1 + r1 * r2 + r2 * r2)
    return abs(v) * math.pi / 3.0


def perfil_desde_stl(tris, tol_r=0.1):
    """Reconstruye el perfil exacto de un inserto de revolución (eje Z). La abertura
    es el extremo más ancho. Devuelve (canon, info); lanza ValueError si no sirve."""
    verts = {}
    for t in tris:
        for q in t:
            verts[(round(q[0], 4), round(q[1], 4), round(q[2], 4))] = q
    V = list(verts.values())
    xs = [q[0] for q in V]
    ys = [q[1] for q in V]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    niveles = {}
    for q in V:
        niveles.setdefault(round(q[2], 2), []).append(math.hypot(q[0] - cx, q[1] - cy))
    zk = sorted(niveles)
    if len(zk) < 2:
        raise ValueError("el STL no tiene altura")
    lv = []
    for z in zk:
        rs = niveles[z]
        rmax, rmin = max(rs), min(rs)
        if sum(1 for r in rs if abs(r - rmax) < tol_r) < 8:
            raise ValueError("el STL no es un sólido de revolución sobre el eje Z")
        if rmin < 0.5 or rmax - rmin < tol_r:
            lv.append((z, [rmax]))
        else:
            if sum(1 for r in rs if abs(r - rmin) < tol_r) < 8:
                raise ValueError("el STL no es un sólido de revolución sobre el eje Z")
            lv.append((z, [rmin, rmax]))
    rz = [(0.0, lv[0][0]), (max(lv[0][1]), lv[0][0])]
    for z, rs in lv[1:]:
        if len(rs) == 1:
            rz.append((rs[0], z))
        else:
            prev = rz[-1][0]
            a = min(rs, key=lambda r: abs(r - prev))
            b = rs[0] if a == rs[1] else rs[1]
            rz.append((a, z))
            rz.append((b, z))
    rz.append((0.0, lv[-1][0]))
    limpio = [rz[0]]
    for q in rz[1:]:
        if math.hypot(q[0] - limpio[-1][0], q[1] - limpio[-1][1]) > 1e-6:
            limpio.append(q)
    vm, vr = volumen_tris(tris), volumen_revolucion(limpio)
    if vm <= 0 or abs(vr - vm) / vm > 0.03:
        raise ValueError("el STL no es un sólido de revolución cerrado (volumen %.0f vs %.0f mm³)"
                         % (vm, vr))
    z0, z1 = lv[0][0], lv[-1][0]
    if max(lv[-1][1]) >= max(lv[0][1]):
        canon = [(r, z1 - z) for r, z in limpio]
    else:
        canon = [(r, z - z0) for r, z in reversed(limpio)]
    canon = [(round(r, 4), round(d, 4)) for r, d in canon]
    info = {"volumen_mm3": round(vm, 1), "alto_mm": round(z1 - z0, 2),
            "diam_abertura_mm": round(2 * canon[-2][0], 2), "puntos": len(canon)}
    return canon, info


# ===========================================================================
# SUPERFICIE EXTERIOR (puede no ser de revolución: facetas, medallones)
# ===========================================================================
def _subdividir(rows, paso):
    out = [rows[0]]
    for (r1, z1), (r2, z2) in zip(rows, rows[1:]):
        n = max(1, int(math.ceil(math.hypot(r2 - r1, z2 - z1) / paso)))
        for k in range(1, n + 1):
            t = k / float(n)
            out.append((r1 + t * (r2 - r1), z1 + t * (z2 - z1)))
    return out


def _anillos(rows, anillos, H):
    """Bandas en relieve: suma 'extra' al radio entre z0 y z1 (escalón a 45°)."""
    if not anillos:
        return rows
    out = list(rows)
    for f0, f1, extra in anillos:
        z0, z1 = max(0.0, f0 * H), min(H, f1 * H)
        nuevo = []
        for r, z in out:
            dz = min(z - z0, z1 - z) if z0 > 0 or z1 < H else 1e9
            if z0 <= 0:
                dz = z1 - z
            if z1 >= H:
                dz = z - z0 if z0 > 0 else 1e9
            if z0 - 1e-9 <= z <= z1 + 1e-9:
                k = max(0.0, min(1.0, dz / max(extra, 1e-6))) if dz < 1e8 else 1.0
                nuevo.append((r + extra * k, z))
            else:
                nuevo.append((r, z))
        out = nuevo
    return out


def _seccion_facetas(C, D, t):
    """Sección a la fracción t de una banda entre dos polígonos (antiprisma si
    están girados medio lado): lista de (ángulo, x, y) ordenada."""
    n = len(C)
    pts = []
    for (ac, xc, yc) in C:
        for (ad, xd, yd) in D:
            da = (ad - ac + math.pi) % TAU - math.pi
            if abs(da) <= math.pi / n + 1e-9:
                x, y = xc + t * (xd - xc), yc + t * (yd - yc)
                pts.append((math.atan2(y, x) % TAU, x, y))
    pts.sort()
    out = []
    for q in pts:
        if not out or math.hypot(q[1] - out[-1][1], q[2] - out[-1][2]) > 1e-9:
            out.append(q)
    return out


def _radio_poligono(sec, th):
    """Radio del rayo de ángulo th contra el polígono convexo sec."""
    dx, dy = math.cos(th), math.sin(th)
    m = len(sec)
    best = None
    for i in range(m):
        _, x1, y1 = sec[i]
        _, x2, y2 = sec[(i + 1) % m]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        r = (x1 * ey - y1 * ex) / den
        u = (x1 * dy - y1 * dx) / den
        if r > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = r if best is None else min(best, r)
    return best or 0.0


def _lobulos(filas, M, H, lb):
    """Panza con n lóbulos: r·(1 + amp·g(θ)·w(z)), g = ((1 + cos nθ)/2)^agudo (el primero,
    al frente, o corrido `fase` del período). w = 1 hasta z1·H y baja suave a 0 en los 6 mm siguientes (patitas)."""
    n, amp, ag = int(lb["n"]), float(lb["amp"]), float(lb.get("agudo", 1.0))
    z1 = float(lb.get("z1", 1.0)) * H
    fase = float(lb.get("fase", 0.0)) * TAU / n         # 0.5: entre lóbulos al frente
    g = [((1.0 + math.cos(n * (TAU * k / M + math.pi / 2) - fase * n)) / 2.0) ** ag
         for k in range(M)]
    for z, rs in filas:
        if z <= z1:
            w = 1.0 if z1 >= H else 0.5 * (1.0 + math.cos(math.pi * max(0.0, z - (z1 - 18.0)) / 18.0)) \
                if z > z1 - 18.0 else 1.0
        else:
            w = 0.0
        if w > 0:
            for k in range(M):
                rs[k] *= 1.0 + amp * g[k] * w


def _rombos(filas, M, H, R, rb):
    """Relieve de cubos en perspectiva (tumbling blocks): grilla de hexágonos (punta arriba);
    cada hexágono son tres rombos planos que bajan desde el centro. Se apaga cerca de la
    base y de la boca."""
    ncol, alto = int(rb["columnas"]), float(rb["alto"])
    ancho = TAU * R / ncol                     # ancho de un hexágono (mm)
    lado = ancho / math.sqrt(3.0)
    sq3 = math.sqrt(3.0)
    # vértices "cercanos" a 90°, 210° y 330° (lado 1)
    E = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in (90, 210, 330)]
    pares = [(E[0], E[1]), (E[1], E[2]), (E[2], E[0])]

    def prof(x, y):                            # x, y en unidades de lado
        fila = int(math.floor(y / 1.5 + 0.5))
        mejor = None
        for j in (fila - 1, fila, fila + 1):   # centro más cercano
            off = 0.5 * sq3 if j % 2 else 0.0
            i = math.floor((x - off) / sq3 + 0.5)
            for ii in (i - 1, i, i + 1):
                cx, cy = ii * sq3 + off, 1.5 * j
                d = (x - cx) ** 2 + (y - cy) ** 2
                if mejor is None or d < mejor[0]:
                    mejor = (d, x - cx, y - cy)
        _, px, py = mejor
        for (ax, ay), (bx, by) in pares:
            det = ax * by - ay * bx
            a = (px * by - py * bx) / det
            b = (ax * py - ay * px) / det
            if a >= -1e-9 and b >= -1e-9:
                return min(2.0, a + b)
        return 2.0
    borde = 4.0
    for z, rs in filas:
        w = min(1.0, max(0.0, min(z - 1.0, H - 2.0 - z) / borde))
        if w <= 0:
            continue
        y = z / lado
        for k in range(M):
            x = (k / float(M)) * ncol * sq3
            rs[k] += w * alto * (1.0 - prof(x, y) / 2.0)


def _filas_poliedro(p, s, M, paso, pd):
    """Piel de caras planas: un polígono de n vértices por punto de control (girado `giro`
    medio lado por nivel: torcido; con azar en radio y ángulo: irregular). Entre niveles,
    triángulos planos; cada fila es el corte exacto a su altura."""
    n = int(pd["n"])
    giro = float(pd.get("giro", 0.5)) * TAU / n
    ar, at = float(pd.get("azar_r", 0.0)), float(pd.get("azar_th", 0.0)) * TAU / n
    rnd = __import__("random").Random(int(pd.get("semilla", 1)))
    niveles = []
    for k, (r, z) in enumerate(_control(p, s)):
        R = r / math.cos(math.pi / n)
        pts = []
        for i in range(n):
            th = -math.pi / 2 + k * giro + TAU * i / n + (rnd.uniform(-at, at) if at else 0.0)
            rr = R * (1.0 + (rnd.uniform(-ar, ar) if ar else 0.0))
            pts.append((th % TAU, rr * math.cos(th), rr * math.sin(th), z))
        pts.sort()
        niveles.append([q[1:] for q in pts])
    # triangulación entre niveles: cremallera por ángulo
    tris = []
    for A, B in zip(niveles, niveles[1:]):
        ang = lambda q: math.atan2(q[1], q[0]) % TAU
        i0 = min(range(n), key=lambda i: ang(A[i]))
        j0 = min(range(n), key=lambda j: ang(B[j]))
        i = j = 0
        while i < n or j < n:
            a, a2 = A[(i0 + i) % n], A[(i0 + i + 1) % n]
            b, b2 = B[(j0 + j) % n], B[(j0 + j + 1) % n]
            ta = ang(a2) + (TAU if i + 1 >= n or ang(a2) < ang(A[i0]) else 0.0)
            tb = ang(b2) + (TAU if j + 1 >= n or ang(b2) < ang(B[j0]) else 0.0)
            if j >= n or (i < n and ta <= tb):
                tris.append((a, a2, b))
                i += 1
            else:
                tris.append((a, b2, b))
                j += 1
    zs = [lv[0][2] for lv in niveles]
    filas = []
    for z0, z1 in zip(zs, zs[1:]):
        m = max(1, int(math.ceil((z1 - z0) / paso)))
        for jj in range(0 if not filas else 1, m + 1):
            z = z0 + (z1 - z0) * jj / float(m)
            zc = min(max(z, z0 + 1e-6), z1 - 1e-6)      # corte apenas adentro de la banda
            segs = []
            for t in tris:
                if not (min(q[2] for q in t) <= zc <= max(q[2] for q in t)):
                    continue
                cruces = []
                for u, v in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                    if (u[2] - zc) * (v[2] - zc) < 0:
                        f = (zc - u[2]) / (v[2] - u[2])
                        cruces.append((u[0] + f * (v[0] - u[0]), u[1] + f * (v[1] - u[1])))
                if len(cruces) == 2:
                    segs.append(cruces)
            filas.append((z, [_radio_segs(segs, TAU * k / M) for k in range(M)]))
    return filas


def _radio_segs(segs, th):
    """Radio del rayo de ángulo th contra el contorno (lista de segmentos)."""
    dx, dy = math.cos(th), math.sin(th)
    best = None
    for (x1, y1), (x2, y2) in segs:
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        r = (x1 * ey - y1 * ex) / den
        u = (x1 * dy - y1 * dx) / den
        if r > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = r if best is None else max(best, r)
    return best or 0.0


def filas_exteriores(p, s, M, paso=1.5):
    """Anillos de la piel exterior, de abajo hacia arriba: [(z, [r_k])], con
    r_k el radio en el ángulo 2πk/M. Incluye anillos, facetas y medallones."""
    ex = p.get("extras") or {}
    H = p["H"]
    denso = perfil_mate(p, s)
    if "facetas" in ex:
        n = int(ex["facetas"]["n"])
        alt = ex["facetas"].get("alternado", False)
        phi0 = -math.pi / 2
        secs = []
        for k, (r, z) in enumerate(_control(p, s)):
            R = r / math.cos(math.pi / n)
            off = phi0 + ((math.pi / n) if (alt and k % 2 == 1) else 0.0)
            secs.append((z, [((off + TAU * i / n) % TAU,
                              R * math.cos(off + TAU * i / n), R * math.sin(off + TAU * i / n))
                             for i in range(n)]))
        filas = []
        for (z0, C), (z1, D) in zip(secs, secs[1:]):
            m = max(1, int(math.ceil((z1 - z0) / paso)))
            for j in range(0 if not filas else 1, m + 1):
                t = j / float(m)
                sec = _seccion_facetas(C, D, t)
                filas.append((z0 + t * (z1 - z0),
                              [_radio_poligono(sec, TAU * k / M) for k in range(M)]))
    elif "poliedro" in ex:
        filas = _filas_poliedro(p, s, M, paso, ex["poliedro"])
    else:
        rows = _anillos(_subdividir(denso[1:-1], paso), ex.get("anillos"), H)
        filas = [(z, [r] * M) for r, z in rows]
    if "lobulos" in ex:
        _lobulos(filas, M, H, ex["lobulos"])
    if "rombos" in ex:
        _rombos(filas, M, H, p["Dmax"] / 2.0 * s, ex["rombos"])
    med = ex.get("medallones")
    if med:
        n, rad, prof = int(med["n"]), float(med["radio"]), float(med["prof"])
        zc = float(med["z"]) * H
        angs = [-math.pi / 2 + TAU * k / n for k in range(n)]   # el primero, al frente
        for ang in angs:
            for z, rs in filas:
                if abs(z - zc) >= rad:
                    continue
                for k in range(M):
                    th = TAU * k / M
                    da = (th - ang + math.pi) % TAU - math.pi
                    if abs(da) > math.pi / 2:
                        continue
                    lat = rs[k] * math.sin(da)
                    dist = math.sqrt(lat * lat + (z - zc) ** 2)
                    if dist < rad:          # borde con rampa corta: sin serrucho
                        rs[k] = rs[k] - prof * min(1.0, (rad - dist) / RAMPA_MEDALLON)
    return filas, denso


def perfil_interior(filas):
    """Radio mínimo de cada fila: perfil de revolución inscripto en la piel."""
    return [(min(rs), z) for z, rs in filas]


def _medir(p, s, hueco_canon, holgura, hundir, M=96):
    filas, denso = filas_exteriores(p, s, M)
    ins = [(0.0, 0.0)] + perfil_interior(filas) + [(0.0, p["H"])]
    rz = colocar_hueco(perfil_hueco(hueco_canon, holgura, hundir, 0.0), p["H"], hundir)
    return pared_2d(ins, rz, p["H"]), piso_2d(rz), rz


def autoajustar(p, hueco_canon, holgura, pared, piso, hundir=0.0, activo=True):
    """Ajusta la altura y la escala radial hasta cumplir pared y fondo."""
    p = dict(p)
    log = []
    prof = max(d for _, d in hueco_canon) + holgura + hundir
    if activo and p["H"] < prof + piso:
        log.append("Altura %.0f → %.1f mm para dejar %.1f mm de fondo" % (p["H"], prof + piso, piso))
        p["H"] = prof + piso
    s = 1.0
    w, fondo, rz = _medir(p, s, hueco_canon, holgura, hundir)
    if activo and w < pared:
        lo, hi = 1.0, LIMITES["escala_max"]
        if _medir(p, hi, hueco_canon, holgura, hundir)[0] < pared:
            s = hi
            log.append("Ni agrandando ×%.0f se logra la pared pedida" % hi)
        else:
            for _ in range(22):
                mid = 0.5 * (lo + hi)
                if _medir(p, mid, hueco_canon, holgura, hundir)[0] >= pared:
                    hi = mid
                else:
                    lo = mid
            s = hi
            log.append("Agrandado ×%.3f para %.1f mm de pared" % (s, pared))
        w, fondo, rz = _medir(p, s, hueco_canon, holgura, hundir)
    return p, s, w, fondo, rz, log


# ===========================================================================
# MALLA CERRADA
# ===========================================================================
def _coser(F, A, B):
    """Une dos anillos (listas de índices, mismo largo; o un índice suelto = polo)
    con la orientación del recorrido A -> B."""
    if isinstance(A, int):
        n = len(B)
        for k in range(n):
            F.append((A, B[(k + 1) % n], B[k]))
        return
    if isinstance(B, int):
        n = len(A)
        for k in range(n):
            F.append((A[k], A[(k + 1) % n], B))
        return
    n = len(A)
    for k in range(n):
        k1 = (k + 1) % n
        F.append((A[k], A[k1], B[k1]))
        F.append((A[k], B[k1], B[k]))


def _limpiar_rz(rows):
    out = []
    for q in rows:
        if not out or abs(q[0] - out[-1][0]) > 1e-9 or abs(q[1] - out[-1][1]) > 1e-9:
            out.append(q)
    return out


def malla_mate(filas, hueco_rz, M, marca=None):
    """Cuerpo: centro de la base -> piel (abajo->arriba) -> boca -> hueco
    (arriba->abajo) -> centro del fondo del hueco. Una sola malla cerrada.
    marca = (contornos, profundidad): letras grabadas en la base (en vez del abanico)."""
    V, F = [], []
    cos_ = [math.cos(TAU * k / M) for k in range(M)]
    sin_ = [math.sin(TAU * k / M) for k in range(M)]

    def anillo(z, rs):
        i0 = len(V)
        for k in range(M):
            V.append((rs[k] * cos_[k], rs[k] * sin_[k], z))
        return list(range(i0, i0 + M))

    def polo(z):
        V.append((0.0, 0.0, z))
        return len(V) - 1

    cadena = [] if marca else [polo(filas[0][0])]
    for z, rs in filas:
        cadena.append(anillo(z, rs))
    if marca:
        import mate_deco
        mate_deco.base_grabada(V, F, cadena[0], filas[0][0], marca[0], marca[1])
    cav = _limpiar_rz(list(reversed(hueco_rz[1:-1])))   # abertura -> fondo
    for r, z in cav:
        cadena.append(anillo(z, [r] * M))
    cadena.append(polo(hueco_rz[0][1]))
    for A, B in zip(cadena, cadena[1:]):
        _coser(F, A, B)
    return V, F


def malla_aletas(p, s, filas):
    """Aletas de apoyo (prismas cerrados, se apoyan en la cama)."""
    a = (p.get("extras") or {}).get("aletas")
    if not a:
        return []
    H = p["H"]
    n, t = int(a["n"]), float(a["espesor"])
    Rf = p["Dmax"] / 2.0 * s + float(a["alcance"])
    zt = float(a["alto"]) * H
    r_zt = min((abs(z - zt), min(rs)) for z, rs in filas)[1]
    loc = [(0.0, 0.0), (Rf, 0.0), (Rf, 6.0), (r_zt * 0.85, zt), (0.0, zt * 0.7)]
    shells = []
    for k in range(n):
        ang = TAU * k / n + math.pi / 2
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        V = []
        for side in (-0.5, 0.5):
            for x, z in loc:
                V.append((ux * x + nx * t * side, uy * x + ny * t * side, z))
        m = len(loc)
        F = []
        for i in range(1, m - 1):
            F.append((0, i + 1, i))             # tapa del lado -n
            F.append((m, m + i, m + i + 1))     # tapa del lado +n
        for i in range(m):
            j = (i + 1) % m
            F.append((i, j, m + j))
            F.append((i, m + j, m + i))
        if mesh_volume(V, F) < 0:
            F = [(a_, c, b) for a_, b, c in F]
        shells.append((V, F))
    return shells


def mesh_volume(V, F):
    s = 0.0
    for a, b, c in F:
        ax, ay, az = V[a]
        bx, by, bz = V[b]
        cx, cy, cz = V[c]
        s += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return s / 6.0


def mesh_check(F):
    """Cerrada y bien orientada: cada arista dirigida aparece una vez con su opuesta."""
    seen = set()
    dup = 0
    for a, b, c in F:
        for e in ((a, b), (b, c), (c, a)):
            if e in seen:
                dup += 1
            seen.add(e)
    abiertas = sum(1 for (a, b) in seen if (b, a) not in seen)
    return {"closed": dup == 0 and abiertas == 0, "open_edges": abiertas, "bad_edges": dup}


# ===========================================================================
# API
# ===========================================================================
def hueco_de(opts):
    """(canon, nombres, info_propio) según el inserto pedido."""
    ins = (opts.get("inserto") or "polimero").strip().lower()
    if ins in ("polímero", "0"):
        ins = "polimero"
    if ins == "1":
        ins = "adaptador"
    if ins in ("2", "los dos"):
        ins = "ambos"
    if ins == "polimero" or ins == "adaptador":
        return list(INSERTOS[ins]["perfil"]), [INSERTOS[ins]["nombre"]], None
    if ins == "ambos":
        return (envolvente([INSERTOS["polimero"]["perfil"], INSERTOS["adaptador"]["perfil"]]),
                [INSERTOS["polimero"]["nombre"], INSERTOS["adaptador"]["nombre"]], None)
    if ins == "propio":
        data = opts.get("stl_propio")
        if not data:
            raise ValueError("Subí el STL de tu inserto")
        canon, info = perfil_desde_stl(leer_stl(bytes(data)))
        return canon, [opts.get("stl_nombre") or "Inserto propio"], info
    raise ValueError("inserto desconocido: %s" % ins)


def _clamp(v, lo, hi, defecto):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return defecto
    return max(lo, min(hi, v))


def build_mate(opts=None):
    opts = dict(opts or {})
    T = tipo(opts.get("tipo") or TIPOS[0]["id"])
    holgura = _clamp(opts.get("holgura"), 0.0, LIMITES["holgura_max"], 0.2)
    pared = _clamp(opts.get("pared"), LIMITES["pared_min"], LIMITES["pared_max"], 3.0)
    piso = _clamp(opts.get("piso"), LIMITES["piso_min"], LIMITES["piso_max"], 4.0)
    hundir = _clamp(opts.get("hundir"), 0.0, LIMITES["hundir_max"], 0.0)
    auto = opts.get("autoajuste", True) is not False
    calidad = opts.get("calidad") if opts.get("calidad") in ("preview", "normal") else "preview"
    canon, nombres, info_propio = hueco_de(opts)

    p = parametros_tipo(T["id"], opts.get("altura"), opts.get("diam_max"), opts.get("diam_boca"))
    p, s, w, fondo, rz, log = autoajustar(p, canon, holgura, pared, piso, hundir, auto)

    M = 192 if calidad == "preview" else 288
    ex = p.get("extras") or {}
    if "facetas" in ex:
        n2 = 2 * int(ex["facetas"]["n"])
        M = int(math.ceil(M / float(n2))) * n2
    filas, denso = filas_exteriores(p, s, M, paso=1.5 if calidad == "preview" else 0.8)
    rz = colocar_hueco(perfil_hueco(canon, holgura, hundir, 0.0), p["H"], hundir)
    errores, avisos = [], list(log)
    marca_rep = _marca(opts, filas, avisos)
    V, F = malla_mate(filas, rz, M, marca_rep and (marca_rep.pop("_loops"), marca_rep["prof_mm"]))
    if mesh_volume(V, F) < 0:
        F = [(a, c, b) for a, b, c in F]
    shells = [(V, F)] + malla_aletas(p, s, filas)
    deco_shell, deco_rep = _deco(opts, filas, M, p["H"], calidad, errores, avisos)
    cuna_res = _cuna(opts, filas)

    ins = [(0.0, 0.0)] + perfil_interior(filas) + [(0.0, p["H"])]
    pared_med = pared_2d(ins, rz, p["H"])
    fondo = piso_2d(rz)
    if pared_med < 0:
        errores.append("El hueco se sale del mate: agrandá el diámetro o activá el autoajuste")
    elif pared_med < pared - 0.05:
        avisos.append("Pared de %.1f mm, menos que los %.1f mm pedidos" % (pared_med, pared))
    if fondo < piso - 0.05:
        avisos.append("Fondo de %.1f mm, menos que los %.1f mm pedidos" % (fondo, piso))
    if pared_med < LIMITES["pared_min"] and pared_med >= 0:
        errores.append("Pared de %.1f mm: muy fina para imprimir" % pared_med)
    if ex.get("aletas"):
        avisos.append("Las aletas son piezas que se cruzan con el cuerpo: el laminador las une")

    if deco_shell:
        shells.append(deco_shell)
    Vt, Ft = [], []
    vol = 0.0
    for Vs, Fs in shells:
        off = len(Vt)
        Vt.extend(Vs)
        Ft.extend((a + off, b + off, c + off) for a, b, c in Fs)
        vol += mesh_volume(Vs, Fs)
    xs = [v[0] for v in Vt]
    ys = [v[1] for v in Vt]
    zs = [v[2] for v in Vt]
    ins_id = (opts.get("inserto") or "polimero").strip().lower()
    sku = "Mate-%s-%s" % (T["id"].upper().replace("_", "-"), ins_id.upper())
    rep = {
        "sku": sku, "tipo": T["id"], "nombre": T["nombre"], "insertos": nombres,
        "valid": not errores, "errors": errores, "warnings": avisos,
        "escala": round(s, 3), "altura_mm": round(p["H"], 1),
        "diam_max_mm": round(max(max(xs) - min(xs), max(ys) - min(ys)), 1),
        "diam_boca_mm": round(2 * filas[-1][1][0], 1),
        "bbox_mm": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1),
                    round(max(zs) - min(zs), 1)],
        "pared_mm": round(pared_med, 2), "pared_pedida_mm": pared,
        "fondo_mm": round(fondo, 2), "holgura_mm": holgura, "hundir_mm": hundir,
        "hueco_prof_mm": round(p["H"] - fondo, 1),
        "hueco_diam_mm": round(2 * max(r for r, _ in rz), 1),
        "volumen_cm3": round(vol / 1000.0, 1), "peso_g": round(vol / 1000.0 * PLA_G_CM3, 0),
        "triangulos": len(Ft), "piezas": len(shells),
        "cerrada": all(mesh_check(Fs)["closed"] for _, Fs in shells),
        "motor": MATE_VERSION,
    }
    if info_propio:
        rep["inserto_propio"] = info_propio
    rep["marca"] = marca_rep
    rep["deco"] = deco_rep
    if cuna_res:
        rep["cuna"] = cuna_res[1]
        rep["cerrada"] = rep["cerrada"] and mesh_check(cuna_res[0][1])["closed"]
    return {"V": Vt, "F": Ft, "shells": shells, "report": rep, "params": p,
            "perfil_exterior": denso, "hueco_rz": rz, "deco": deco_shell,
            "cuna": cuna_res[0] if cuna_res else None}


# ===========================================================================
# DECORACIÓN (mate_deco.py): marca en la base, relieve y cuña
# ===========================================================================
MARCA_DEFECTO = "Eden3D"


def _marca(opts, filas, avisos):
    """Marca grabada debajo de la base (la de Eden3D salvo que se pida otra; ""
    = sin marca). Devuelve el reporte con los contornos en "_loops"."""
    import eden_font
    import mate_deco
    texto = opts.get("marca", MARCA_DEFECTO)
    if texto is None:
        texto = MARCA_DEFECTO
    t, err = eden_font.check(texto)
    if err:
        raise ValueError(err)
    if not t:
        return None
    r_libre = min(filas[0][1]) - 3.0
    loops, cap = mate_deco.ubicar_marca(t, r_libre)
    if not loops:
        avisos.append("Marca: \"%s\" no entra en la base, probá un texto más corto" % t)
        return None
    return {"texto": t, "cap_mm": cap, "prof_mm": 0.6, "_loops": loops}


def _deco(opts, filas, M, H, calidad, errores, avisos):
    """Relieve proyectado (texto o SVG). -> (shell o None, reporte o None)."""
    import mate_deco
    d = opts.get("deco") or {}
    tipo_d = d.get("tipo")
    if tipo_d not in ("texto", "svg"):
        return None, None
    alto = mate_deco._f(d.get("alto"), mate_deco.DECO_DEF["alto"], *mate_deco.DECO_LIM["alto"])
    try:
        if tipo_d == "texto":
            forma = mate_deco.forma_texto(d.get("texto") or "", alto)
        else:
            datos = d.get("svg")
            if not datos and d.get("svg_path"):
                with open(d["svg_path"], "rb") as fh:
                    datos = fh.read()
            if not datos:
                raise ValueError("Subí un archivo SVG")
            forma = mate_deco.forma_svg(datos, alto)
        dd = dict(d)
        if dd.get("z") in (None, ""):
            med = ((tipo(opts.get("tipo") or TIPOS[0]["id"]).get("extras") or {}).get("medallones"))
            dd["z"] = (float(med["z"]) if med else 0.55) * H
        shell, info, av = mate_deco.relieve(forma, filas, M, dd, H, calidad)
    except ValueError as e:
        errores.append("Relieve: %s" % e)
        return None, None
    avisos.extend(av)
    info["tipo"] = tipo_d
    if tipo_d == "texto":
        info["texto"] = d.get("texto")
    info["cerrada"] = mesh_check(shell[1])["closed"]
    return shell, info


def _cuna(opts, filas):
    import mate_deco
    c = opts.get("cuna")
    if c is None or c is False:
        return None
    ang = c.get("angulo", 45.0) if isinstance(c, dict) else 45.0
    return mate_deco.cuna(min(filas[0][1]), ang)
