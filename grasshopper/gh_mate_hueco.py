# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
MOTOR MATE IMPERIAL  -  componente Script de Grasshopper (Python)
=================================================================
Genera cuerpos de mate imperial (varios tipos) o usa un mate propio
(Brep / Mesh / archivo STL) y le resta los huecos de insertos:
  - "polimero"  : Polimero_Mate (vaso de polimero)      -> perfil exacto incluido
  - "adaptador" : Adaptador_Polimero_2                   -> perfil exacto incluido
  - cualquier ruta a un .stl propio (si es de revolucion se convierte
    a NURBS exacto; si no, se resta como malla)

Compatible con Rhino 8 (Script / Python 3) y Rhino 7 (GhPython).
Unidades: milimetros.

ENTRADAS (nombre exacto | acceso | ejemplo)
  Tipo        item  0..5         tipo de mate generado (ver TIPOS)
  Altura      item  120          altura total (0/vacio = valor del tipo)
  DiamMax     item  95           diametro maximo de la panza
  DiamBoca    item  80           diametro exterior de la boca
  AltPie      item  14           altura del pie (-1 = la del tipo, 0 = sin pie)
  DiamPie     item  70           diametro de la base del pie
  MateCustom  item  geometria    Brep o Mesh propio (anula el generador)
  MateSTL     item  "C:/..stl"   STL propio del mate (anula el generador)
  Huecos      LIST  polimero     "polimero", "adaptador", 0, 1 o ruta .stl
  Abertura    LIST  0            0 = abre en la boca, 1 = abre en la base
  Hundir      LIST  0            mm que el hueco se mete por debajo de la cara
  Holgura     item  0.2          holgura radial para que entre el inserto (mm)
  ParedMin    item  3            pared minima deseada (mm)
  PisoMin     item  4            espesor minimo de fondo (mm)
  AutoAjuste  item  True         agranda el mate generado hasta cumplir paredes
  Ejecutar    item  True         hace la booleana (desactivar mientras se edita)
  ExportarSTL item  "C:/..stl"   si tiene ruta, guarda el resultado en STL

SALIDAS
  Mate, Huecos, Resultado, Perfiles, Info, Pared, Piso
"""
from __future__ import print_function, division
import math
import os
import struct

# ---------------------------------------------------------------------------
# PERFILES EXACTOS DE LOS INSERTOS (extraidos de los STL entregados)
# Formato canonico: lista (r, d) desde el centro del fondo cerrado hasta el
# centro de la abertura. d = profundidad medida desde la abertura (0 = cara).
# ---------------------------------------------------------------------------
INSERTOS = {
    "polimero": {
        "nombre": "Polimero_Mate (POLIMERO)",
        "perfil": [(0.0, 70.3), (23.35, 70.3), (23.35, 65.8), (25.86, 63.3),
                   (25.86, 45.7), (28.34, 43.3), (28.34, 26.05), (31.12, 23.3),
                   (31.15, 8.0), (31.18, 4.0), (34.92, 4.0), (34.92, 0.0),
                   (0.0, 0.0)],
    },
    "adaptador": {
        "nombre": "Adaptador_Polimero_2",
        "perfil": [(0.0, 85.0), (14.5, 85.0), (14.5, 79.0), (28.0, 79.0),
                   (28.0, 20.0), (42.0, 20.0), (42.0, 0.0), (0.0, 0.0)],
    },
}
ALIAS = {"0": "polimero", "1": "adaptador", "polimero": "polimero",
         "polímero": "polimero", "adaptador": "adaptador"}
AMBOS = ("2", "ambos", "los dos", "polimero+adaptador")

# ---------------------------------------------------------------------------
# TIPOS DE MATE (perfil de la panza normalizado: (z 0..1, r / Rmax))
# "boca" = usa el radio de boca. Agregar tipos nuevos es copiar un bloque.
# ---------------------------------------------------------------------------
TIPOS = [
    {"nombre": "Imperial Clasico", "H": 120.0, "Dmax": 95.0, "Dboca": 80.0,
     "Hpie": 14.0, "Dpie": 70.0, "Dtallo": 48.0, "lineal": False,
     "panza": [(0.0, 0.55), (0.10, 0.84), (0.32, 1.0), (0.56, 0.97),
               (0.80, 0.88), (0.94, "boca"), (1.0, "boca")]},
    {"nombre": "Imperial Camionero", "H": 112.0, "Dmax": 108.0, "Dboca": 90.0,
     "Hpie": 12.0, "Dpie": 82.0, "Dtallo": 60.0, "lineal": False,
     "panza": [(0.0, 0.62), (0.12, 0.90), (0.38, 1.0), (0.66, 0.98),
               (0.90, "boca"), (1.0, "boca")]},
    {"nombre": "Imperial Torpedo", "H": 140.0, "Dmax": 90.0, "Dboca": 80.0,
     "Hpie": 14.0, "Dpie": 64.0, "Dtallo": 40.0, "lineal": False,
     "panza": [(0.0, 0.45), (0.16, 0.72), (0.46, 0.95), (0.76, 1.0),
               (0.93, "boca"), (1.0, "boca")]},
    {"nombre": "Imperial Copa", "H": 150.0, "Dmax": 96.0, "Dboca": 82.0,
     "Hpie": 38.0, "Dpie": 76.0, "Dtallo": 26.0, "lineal": False,
     "panza": [(0.0, 0.30), (0.12, 0.74), (0.40, 1.0), (0.74, 0.97),
               (0.94, "boca"), (1.0, "boca")]},
    {"nombre": "Imperial Pera", "H": 125.0, "Dmax": 100.0, "Dboca": 80.0,
     "Hpie": 14.0, "Dpie": 72.0, "Dtallo": 50.0, "lineal": False,
     "panza": [(0.0, 0.58), (0.14, 0.92), (0.32, 1.0), (0.56, 0.90),
               (0.78, 0.82), (0.93, "boca"), (1.0, "boca")]},
    {"nombre": "Moderno Cilindrico", "H": 110.0, "Dmax": 86.0, "Dboca": 84.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.90), (0.05, 1.0), (0.95, 1.0), (1.0, "boca")]},
    # ---- modelos con detalles (aletas, anillos, facetas, medallones) ----
    {"nombre": "Cohete", "H": 135.0, "Dmax": 92.0, "Dboca": 84.0,
     "Hpie": 24.0, "Dpie": 22.0, "Dtallo": 22.0, "lineal": False,
     "panza": [(0.0, 0.30), (0.12, 0.72), (0.35, 0.96), (0.60, 1.0),
               (0.85, 0.97), (1.0, "boca")],
     "extras": {"aletas": {"n": 3, "espesor": 6.0, "alcance": 14.0, "alto": 0.45},
                "anillos": [(0.74, 0.98, 2.0)]}},
    {"nombre": "Vaso Redondeado", "H": 105.0, "Dmax": 96.0, "Dboca": 86.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 0.80), (0.03, 0.93), (0.12, 0.995), (0.30, 1.0),
               (0.70, 0.96), (1.0, "boca")],
     "extras": {"medallones": {"n": 1, "radio": 30.0, "z": 0.50, "prof": 1.2}}},
    {"nombre": "Camionero Anillado", "H": 120.0, "Dmax": 92.0, "Dboca": 88.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": False,
     "panza": [(0.0, 1.0), (0.08, 0.97), (0.35, 0.90), (0.70, 0.93),
               (0.90, 0.99), (1.0, "boca")],
     "extras": {"anillos": [(0.0, 0.05, 1.5), (0.93, 1.0, 1.5)]}},
    {"nombre": "Facetado", "H": 110.0, "Dmax": 104.0, "Dboca": 80.0,
     "Hpie": 0.0, "Dpie": 0.0, "Dtallo": 0.0, "lineal": True,
     "panza": [(0.0, 0.62), (0.42, 1.0), (1.0, "boca")],
     "extras": {"facetas": {"n": 6, "alternado": True},
                "medallones": {"n": 3, "radio": 22.0, "z": 0.24, "prof": 1.2}}},
]

SOBREPASO = 1.5      # mm que el hueco sobresale de la cara (booleanas limpias)
SOBREPASO_MALLA = 0.05


# ===========================================================================
# NUCLEO GEOMETRICO PURO (sin Rhino) - testeable fuera de Grasshopper
# ===========================================================================
def _num(v, defecto):
    try:
        if v is None:
            return defecto
        f = float(v)
        return f if f > 0 else defecto
    except Exception:
        return defecto


def _lista(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [x for x in v if x is not None]
    try:
        return [x for x in list(v) if x is not None] if not isinstance(v, str) else [v]
    except Exception:
        return [v]


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


def parametros_tipo(tipo, H=None, Dmax=None, Dboca=None, Hpie=None, Dpie=None):
    T = TIPOS[int(tipo) % len(TIPOS)]
    p = dict(T)
    p["H"] = _num(H, T["H"])
    p["Dmax"] = _num(Dmax, T["Dmax"])
    p["Dboca"] = _num(Dboca, T["Dboca"])
    # AltPie: vacio o negativo = el del tipo; 0 = sin pie
    p["Hpie"] = T["Hpie"] if (Hpie is None or float(Hpie) < 0) else float(Hpie)
    p["Dpie"] = _num(Dpie, T["Dpie"])
    return p


def perfil_mate(p, s=1.0):
    """Devuelve (pie_pts, panza_pts, tapa_pts) en (r, z) y el perfil denso
    completo desde (0,0) hasta (0,H). s = escala radial."""
    H, Hpie = p["H"], p["Hpie"]
    Rmax, Rboca = p["Dmax"] / 2.0 * s, p["Dboca"] / 2.0 * s
    Hc = H - Hpie
    ctrl = []
    for tz, tr in p["panza"]:
        r = Rboca if tr == "boca" else tr * Rmax
        ctrl.append((r, Hpie + tz * Hc))
    if p["lineal"]:
        panza = ctrl
    else:
        panza = catmull_rom(ctrl)
    r0 = panza[0][0]
    if Hpie > 0:
        Rpie, Rt = p["Dpie"] / 2.0 * s, p["Dtallo"] / 2.0 * s
        pie = [(0.0, 0.0), (Rpie, 0.0), (Rpie, 0.22 * Hpie),
               (Rt, 0.70 * Hpie), (Rt, Hpie)]
        if abs(Rt - r0) > 1e-6:
            pie.append((r0, Hpie))
    else:
        pie = [(0.0, 0.0), (r0, 0.0)]
    tapa = [(Rboca, H), (0.0, H)]
    denso = pie[:-1] + panza + tapa[1:]
    return pie, panza, tapa, denso


def perfil_hueco(canon, holgura=0.0, hundir=0.0, sobre=SOBREPASO):
    """Aplica holgura y extension de abertura. Devuelve (r, d) con d<0 fuera."""
    dmax = max(d for _, d in canon)
    out = []
    for r, d in canon[:-1]:              # sin el ultimo punto (centro abertura)
        rr = r + holgura if r > 1e-9 else 0.0
        dd = d + holgura if abs(d - dmax) < 1e-6 else d
        out.append((rr, dd))
    r_ab = out[-1][0]
    e = hundir + sobre
    out.append((r_ab, -e))
    out.append((0.0, -e))
    return out


def colocar_hueco(perfil_rd, abertura, z_tope, z_base, hundir=0.0):
    """(r, d) -> (r, z) mundo."""
    if int(abertura) == 1:
        return [(r, z_base + hundir + d) for r, d in perfil_rd]
    return [(r, z_tope - hundir - d) for r, d in perfil_rd]


def _dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    qx, qy = ax + t * vx, ay + t * vy
    return math.hypot(px - qx, py - qy)


def _dentro(px, py, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < xi:
                c = not c
    return c


def _muestrear(poly, paso=0.5):
    pts = []
    for i in range(len(poly) - 1):
        (x1, y1), (x2, y2) = poly[i], poly[i + 1]
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / paso))
        for k in range(n):
            t = k / float(n)
            pts.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    pts.append(poly[-1])
    return pts


def pared_2d(denso, huecos_rz, aberturas, H):
    """Pared minima exacta (plano meridiano) entre perfil del mate y huecos.
    Negativo = el hueco se sale del mate."""
    poly = list(denso)                         # cerrado por el eje
    segs = [(poly[i], poly[i + 1]) for i in range(len(poly) - 1)]
    minimo = 1e9
    for rz, ab in zip(huecos_rz, aberturas):
        excl = 0 if int(ab) == 1 else len(segs) - 1   # cara por donde abre
        for (px, py) in _muestrear(rz, 0.5):
            if px < 1e-6 or py >= H - 1e-6 or py <= 1e-6:
                continue      # fuera del mate o justo sobre la cara de abertura
            d = min(_dist_seg(px, py, a[0], a[1], b[0], b[1])
                    for j, (a, b) in enumerate(segs) if j != excl)
            if not _dentro(px, py, poly):
                d = -d
            minimo = min(minimo, d)
    return minimo


def piso_2d(huecos_rz, aberturas, H):
    v = 1e9
    for rz, ab in zip(huecos_rz, aberturas):
        zs = [z for r, z in rz if 0 - 1e-6 <= z <= H + 1e-6]
        if not zs:
            continue
        v = min(v, min(zs) if int(ab) == 0 else H - max(zs))
    return v


def autoajustar(p, canons, aberturas, hundires, holgura, pared, piso, activo=True):
    """Ajusta altura y escala radial del mate generado para cumplir paredes."""
    log = []
    p = dict(p)
    ex = p.get("extras") or {}
    kchk = 1.0
    if "facetas" in ex:          # chequeo conservador: el poligono se mete hacia adentro
        kchk = math.cos(math.pi / (2.0 * ex["facetas"]["n"]))
    if "medallones" in ex:       # el medallon come pared: se suma su profundidad
        pared = pared + ex["medallones"]["prof"]
    if activo:
        for c, hu in zip(canons, hundires):
            prof = max(d for _, d in c) + holgura + hu
            if p["H"] < prof + piso:
                log.append("Altura %.1f -> %.1f (fondo)" % (p["H"], prof + piso))
                p["H"] = prof + piso

    def evaluar(s):
        _, _, _, denso = perfil_mate(p, s * kchk)
        rzs = [colocar_hueco(perfil_hueco(c, holgura, hu), ab, p["H"], 0.0, hu)
               for c, ab, hu in zip(canons, aberturas, hundires)]
        return pared_2d(denso, rzs, aberturas, p["H"]), rzs, denso

    s = 1.0
    w, rzs, denso = evaluar(1.0)
    if activo and w < pared:
        lo, hi = 1.0, 3.0
        if evaluar(hi)[0] < pared:
            log.append("AVISO: ni escalando x3 se logra la pared pedida")
            s = hi
        else:
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                if evaluar(mid)[0] >= pared:
                    hi = mid
                else:
                    lo = mid
            s = hi
        log.append("Escala radial x%.3f (DiamMax %.1f, DiamBoca %.1f)" %
                   (s, p["Dmax"] * s, p["Dboca"] * s))
        if s > 1.3 and p["Hpie"] > 0 and 1 in [int(a) for a in aberturas]:
            log.append("SUGERENCIA: el hueco abre por la base y choca con el pie; "
                       "proba AltPie = 0 o un DiamPie mayor")
        w, rzs, denso = evaluar(s)
    return p, s, w, rzs, denso, log


# ---------------------------------------------------------------- STL --------
def leer_stl(ruta):
    """Devuelve lista de triangulos ((x,y,z),(x,y,z),(x,y,z))."""
    with open(ruta, "rb") as f:
        data = f.read()
    tris = []
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + 50 * n == len(data):
            for i in range(n):
                v = struct.unpack("<12f", data[84 + 50 * i: 84 + 50 * i + 48])
                tris.append(((v[3], v[4], v[5]), (v[6], v[7], v[8]),
                             (v[9], v[10], v[11])))
            return tris
    txt = data.decode("latin-1")
    cur = []
    for linea in txt.splitlines():
        s = linea.strip().split()
        if len(s) == 4 and s[0].lower() == "vertex":
            cur.append(tuple(float(x) for x in s[1:]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    return tris


def volumen_tris(tris):
    v = 0.0
    for a, b, c in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) +
              a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return abs(v)


def volumen_revolucion(rz):
    v = 0.0
    n = len(rz)
    for i in range(n):
        r1, z1 = rz[i]
        r2, z2 = rz[(i + 1) % n]
        v += (z2 - z1) * (r1 * r1 + r1 * r2 + r2 * r2)
    return abs(v) * math.pi / 3.0


def perfil_desde_stl(tris, tol_r=0.1):
    """Intenta reconstruir el perfil de revolucion (eje Z). Devuelve
    (canon, info) o (None, motivo)."""
    verts = {}
    for t in tris:
        for p in t:
            verts[(round(p[0], 4), round(p[1], 4), round(p[2], 4))] = p
    V = list(verts.values())
    xs = [p[0] for p in V]; ys = [p[1] for p in V]; zs = [p[2] for p in V]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    niveles = {}
    for p in V:
        niveles.setdefault(round(p[2], 2), []).append(math.hypot(p[0] - cx, p[1] - cy))
    zk = sorted(niveles)
    if len(zk) < 2:
        return None, "sin altura"
    lv = []
    for z in zk:
        rs = niveles[z]
        rmax, rmin = max(rs), min(rs)
        nmax = sum(1 for r in rs if abs(r - rmax) < tol_r)
        if nmax < 8:
            return None, "no es de revolucion (z=%.2f)" % z
        if rmin < 0.5 or rmax - rmin < tol_r:
            lv.append((z, [rmax]))
        else:
            nmin = sum(1 for r in rs if abs(r - rmin) < tol_r)
            if nmin < 8:
                return None, "no es de revolucion (z=%.2f)" % z
            lv.append((z, [rmin, rmax]))
    rz = [(0.0, lv[0][0]), (max(lv[0][1]), lv[0][0])]
    for z, rs in lv[1:]:
        prev = rz[-1][0]
        if len(rs) == 1:
            rz.append((rs[0], z))
        else:
            a = min(rs, key=lambda r: abs(r - prev))
            b = rs[0] if a == rs[1] else rs[1]
            rz.append((a, z)); rz.append((b, z))
    rz.append((0.0, lv[-1][0]))
    # limpiar puntos colineales repetidos
    limpio = [rz[0]]
    for q in rz[1:]:
        if math.hypot(q[0] - limpio[-1][0], q[1] - limpio[-1][1]) > 1e-6:
            limpio.append(q)
    vm, vr = volumen_tris(tris), volumen_revolucion(limpio)
    if vm <= 0 or abs(vr - vm) / vm > 0.03:
        return None, "volumen no coincide (%.0f vs %.0f)" % (vm, vr)
    z0, z1 = lv[0][0], lv[-1][0]
    r_ini, r_fin = max(lv[0][1]), max(lv[-1][1])
    if r_fin >= r_ini:           # abertura arriba (extremo mas ancho)
        canon = [(r, z1 - z) for r, z in limpio]
    else:                        # abertura abajo
        canon = [(r, z - z0) for r, z in reversed(limpio)]
    return canon, "revolucion exacta, centro (%.2f, %.2f), vol %.0f mm3" % (cx, cy, vm)


def resolver_huecos(lista):
    """Devuelve [(etiqueta, canon o None, tris o None, info)]."""
    res = []
    expandida = []
    for item in lista:
        k = str(item).strip().strip('"')
        if k.lower() in AMBOS:
            expandida += ["polimero", "adaptador"]
        elif k:
            expandida.append(k)
    for k in expandida:
        clave = ALIAS.get(k.lower())
        if clave:
            I = INSERTOS[clave]
            res.append((I["nombre"], I["perfil"], None, "perfil exacto incluido"))
            continue
        if os.path.isfile(k):
            tris = leer_stl(k)
            canon, info = perfil_desde_stl(tris)
            res.append((os.path.basename(k), canon, tris, info))
        else:
            res.append((k, None, None, "ERROR: no existe el archivo"))
    return res


def escribir_stl(ruta, tris):
    with open(ruta, "wb") as f:
        f.write(b"MotorMate STL".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            f.write(struct.pack("<12fH", n[0] / L, n[1] / L, n[2] / L,
                                a[0], a[1], a[2], b[0], b[1], b[2],
                                c[0], c[1], c[2], 0))


# ===========================================================================
# PARTE RHINO / GRASSHOPPER
# ===========================================================================
try:
    import Rhino
    import Rhino.Geometry as rg
    EN_RHINO = True
except ImportError:
    EN_RHINO = False


if EN_RHINO:
    import System
    from System.Collections.Generic import List as _NetList

    class _NL(object):
        """NetList[T](items) compatible con IronPython y pythonnet."""
        def __getitem__(self, T):
            def crear(items):
                L = _NetList[T]()
                for x in items:
                    L.Add(x)
                return L
            return crear
    NetList = _NL()

    def _tol():
        try:
            return Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        except Exception:
            return 0.01

    def _geom(g):
        """Acepta Brep, Extrusion, Mesh, SubD o Guid (GhPython ghdoc)."""
        if g is None:
            return None
        if isinstance(g, System.Guid):
            try:
                import rhinoscriptsyntax as rs
                g = rs.coercegeometry(g)
            except Exception:
                return None
        if isinstance(g, rg.Extrusion):
            g = g.ToBrep()
        if isinstance(g, rg.SubD):
            g = rg.Brep.CreateFromSubD(g)
        return g

    def malla_desde_tris(tris):
        m = rg.Mesh()
        for a, b, c in tris:
            i = m.Vertices.Count
            m.Vertices.Add(a[0], a[1], a[2])
            m.Vertices.Add(b[0], b[1], b[2])
            m.Vertices.Add(c[0], c[1], c[2])
            m.Faces.AddFace(i, i + 1, i + 2)
        m.Vertices.CombineIdentical(True, True)
        m.Normals.ComputeNormals()
        m.Compact()
        return m

    def tris_desde_malla(m):
        m = m.DuplicateMesh()
        m.Faces.ConvertQuadsToTriangles()
        out = []
        for f in m.Faces:
            a, b, c = m.Vertices[f.A], m.Vertices[f.B], m.Vertices[f.C]
            out.append(((a.X, a.Y, a.Z), (b.X, b.Y, b.Z), (c.X, c.Y, c.Z)))
        return out

    def a_malla(g):
        if isinstance(g, rg.Mesh):
            return g
        mp = rg.MeshingParameters()
        mp.Tolerance = 0.02
        mp.MinimumEdgeLength = 0.0001
        mp.MaximumEdgeLength = 3.0
        mp.JaggedSeams = False
        mp.SimplePlanes = True
        partes = rg.Mesh.CreateFromBrep(g, mp)
        m = rg.Mesh()
        for p in partes:
            m.Append(p)
        m.Vertices.CombineIdentical(True, True)
        m.Normals.ComputeNormals()
        m.Compact()
        return m

    def revolver(segmentos, cx, cy, rot_deg=0.0):
        """segmentos: lista de curvas en plano XZ local (x=r). Devuelve Brep."""
        crvs = rg.Curve.JoinCurves(NetList[rg.Curve](segmentos), 0.001)
        crv = crvs[0]
        eje = rg.Line(rg.Point3d(cx, cy, -1000), rg.Point3d(cx, cy, 1000))
        rs_ = rg.RevSurface.Create(crv, eje)
        b = rg.Brep.CreateFromRevSurface(rs_, False, False)
        try:
            b.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
        except Exception:
            pass
        if not b.IsSolid:
            capado = b.CapPlanarHoles(_tol())
            if capado is not None:
                b = capado
        if rot_deg:
            b.Rotate(math.radians(rot_deg), rg.Vector3d.ZAxis, rg.Point3d(cx, cy, 0))
        if b.IsSolid and b.SolidOrientation == rg.BrepSolidOrientation.Inward:
            b.Flip()
        return b

    def P(r, z, cx, cy):
        return rg.Point3d(cx + r, cy, z)

    def brep_mate(pie, panza, tapa, cx, cy):
        segs = []
        for i in range(len(pie) - 1):
            segs.append(rg.LineCurve(P(pie[i][0], pie[i][1], cx, cy),
                                     P(pie[i + 1][0], pie[i + 1][1], cx, cy)))
        pts = [P(r, z, cx, cy) for r, z in panza]
        if len(pts) > 2:
            segs.append(rg.Curve.CreateInterpolatedCurve(NetList[rg.Point3d](pts), 3))
        else:
            segs.append(rg.PolylineCurve(NetList[rg.Point3d](pts)))
        segs.append(rg.LineCurve(P(tapa[0][0], tapa[0][1], cx, cy),
                                 P(tapa[1][0], tapa[1][1], cx, cy)))
        return revolver(segs, cx, cy), segs

    def r_en(z, denso):
        """Radio exterior del perfil a la altura z."""
        r = 0.0
        for (r1, z1), (r2, z2) in zip(denso[:-1], denso[1:]):
            lo, hi = min(z1, z2), max(z1, z2)
            if lo - 1e-9 <= z <= hi + 1e-9:
                t = 0.0 if hi - lo < 1e-9 else (z - z1) / (z2 - z1)
                r = max(r, r1 + t * (r2 - r1))
        return r

    def solido_cerrado(b):
        if b is None:
            return None
        if not b.IsSolid:
            c = b.CapPlanarHoles(_tol())
            if c is not None:
                b = c
        if b.IsSolid and b.SolidOrientation == rg.BrepSolidOrientation.Inward:
            b.Flip()
        return b

    def detalles_mate(p, s, denso, cx, cy):
        """Devuelve (cuerpo_nuevo o None, sumar[], restar[], log[])."""
        ex = p.get("extras") or {}
        H = p["H"]
        Rmax = p["Dmax"] / 2.0 * s
        nuevo, sumar, restar, log = None, [], [], []
        eje = rg.Point3d(cx, cy, 0)

        # --- facetas: cuerpo poligonal (loft recto de poligonos) ---
        if "facetas" in ex:
            n = int(ex["facetas"]["n"])
            alt = ex["facetas"].get("alternado", False)
            ctrl = []
            for tz, tr in p["panza"]:
                r = (p["Dboca"] / 2.0 * s) if tr == "boca" else tr * Rmax
                ctrl.append((r, p["Hpie"] + tz * (H - p["Hpie"])))
            secciones = []
            for k, (r, z) in enumerate(ctrl):
                R = r / math.cos(math.pi / n)          # apotema = r
                off = (math.pi / n) if (alt and k % 2 == 1) else 0.0
                pts = [rg.Point3d(cx + R * math.cos(off + 2 * math.pi * i / n),
                                  cy + R * math.sin(off + 2 * math.pi * i / n), z)
                       for i in range(n + 1)]
                secciones.append(rg.PolylineCurve(NetList[rg.Point3d](pts)))
            lofts = rg.Brep.CreateFromLoft(NetList[rg.Curve](secciones), rg.Point3d.Unset,
                                           rg.Point3d.Unset, rg.LoftType.Straight, False)
            if lofts and len(lofts) > 0:
                nuevo = solido_cerrado(lofts[0])
                log.append("Facetado: %d caras%s" % (n, " alternadas" if alt else ""))

        # --- anillos / bandas en relieve ---
        for f0, f1, extra in ex.get("anillos", []):
            # 0.4 mm adentro de base y boca: evita caras coplanares en la union
            z0, z1 = max(0.4, f0 * H), min(H - 0.4, f1 * H)
            zs = [z0 + (z1 - z0) * i / 10.0 for i in range(11)]
            fuera = [P(r_en(z, denso) + extra, z, cx, cy) for z in zs]
            dentro = [P(max(1.0, r_en(z, denso) - 2.0), z, cx, cy) for z in reversed(zs)]
            pts = fuera + dentro + [fuera[0]]
            crv = rg.PolylineCurve(NetList[rg.Point3d](pts))
            rs_ = rg.RevSurface.Create(crv, rg.Line(rg.Point3d(cx, cy, -10), rg.Point3d(cx, cy, 10)))
            b = solido_cerrado(rg.Brep.CreateFromRevSurface(rs_, False, False))
            if b:
                sumar.append(b)
        if ex.get("anillos"):
            log.append("Anillos en relieve: %d (para guarda / color)" % len(ex["anillos"]))

        # --- aletas (tipo cohete) ---
        if "aletas" in ex:
            a = ex["aletas"]
            n, t = int(a["n"]), float(a["espesor"])
            Rf = Rmax + float(a["alcance"])
            zt = float(a["alto"]) * H
            loc = [(0.0, 0.0), (Rf, 0.0), (Rf, 6.0), (r_en(zt, denso) * 0.85, zt),
                   (0.0, zt * 0.7), (0.0, 0.0)]
            for k in range(n):
                ang = 2 * math.pi * k / n + math.pi / 2
                u = rg.Vector3d(math.cos(ang), math.sin(ang), 0)
                nrm = rg.Vector3d(-u.Y, u.X, 0)
                pts = [rg.Point3d(cx, cy, 0) + u * x + rg.Vector3d(0, 0, z) - nrm * (t / 2.0)
                       for x, z in loc]
                crv = rg.PolylineCurve(NetList[rg.Point3d](pts))
                srf = rg.Surface.CreateExtrusion(crv, nrm * t)
                if srf:
                    b = solido_cerrado(srf.ToBrep())
                    if b:
                        sumar.append(b)
            log.append("Aletas: %d (apoyo)" % n)

        # --- medallones rebajados (para relieves / logos propios) ---
        if "medallones" in ex:
            m = ex["medallones"]
            n, rad, prof = int(m["n"]), float(m["radio"]), float(m["prof"])
            zc = float(m["z"]) * H
            rr = r_en(zc, denso)
            off = 0.0
            if "facetas" in ex:
                nf = int(ex["facetas"]["n"])
                off = math.pi / nf                      # centro de cara
            for k in range(n):
                ang = off + 2 * math.pi * k / n - math.pi / 2
                d = rg.Vector3d(math.cos(ang), math.sin(ang), 0)
                pl = rg.Plane(rg.Point3d(cx, cy, zc) + d * (rr - prof), d)
                cil = rg.Cylinder(rg.Circle(pl, rad), 40.0)
                restar.append(cil.ToBrep(True, True))
            log.append("Medallones rebajados: %d de R%.0f x %.1f mm" % (n, rad, prof))
        return nuevo, sumar, restar, log

    def brep_hueco(rz, cx, cy):
        pts = [P(r, z, cx, cy) for r, z in rz]
        segs = [rg.LineCurve(pts[i], pts[i + 1]) for i in range(len(pts) - 1)
                if pts[i].DistanceTo(pts[i + 1]) > 1e-6]
        return revolver(segs, cx, cy, rot_deg=7.0), segs

    def colocar_malla(tris, abertura, cx, cy, z_tope, z_base, hundir):
        m = malla_desde_tris(tris)
        bb = m.GetBoundingBox(True)
        c = bb.Center
        # extremo mas ancho = abertura
        def ancho(zref):
            r = 0.0
            for v in m.Vertices:
                if abs(v.Z - zref) < 1.0:
                    r = max(r, math.hypot(v.X - c.X, v.Y - c.Y))
            return r
        abre_arriba = ancho(bb.Max.Z) >= ancho(bb.Min.Z)
        quiere_arriba = int(abertura) == 0
        if abre_arriba != quiere_arriba:
            m.Rotate(math.pi, rg.Vector3d.XAxis, c)   # girar 180 (sin espejar)
        bb = m.GetBoundingBox(True)
        if quiere_arriba:
            dz = (z_tope - hundir + SOBREPASO_MALLA) - bb.Max.Z
        else:
            dz = (z_base + hundir - SOBREPASO_MALLA) - bb.Min.Z
        m.Translate(rg.Vector3d(cx - bb.Center.X, cy - bb.Center.Y, dz))
        return m

    def sin_cara_abertura(mate, abertura, z_tope, z_base):
        """Copia del mate sin la cara plana por donde abre el hueco
        (esa cara se corta, no es pared)."""
        if not isinstance(mate, rg.Brep):
            return mate
        zc = z_base if int(abertura) == 1 else z_tope
        dup = mate.DuplicateBrep()
        for i in range(dup.Faces.Count - 1, -1, -1):
            bb = dup.Faces[i].GetBoundingBox(True)
            if abs(bb.Min.Z - zc) < 0.01 and abs(bb.Max.Z - zc) < 0.01:
                dup.Faces.RemoveAt(i)
        return dup

    def pared_3d(mate, hueco, abertura, z_tope, z_base):
        medir = sin_cara_abertura(mate, abertura, z_tope, z_base)
        hm = a_malla(hueco) if not isinstance(hueco, rg.Mesh) else hueco
        n = hm.Vertices.Count
        paso = max(1, n // 1500)
        tol = _tol()
        mn = 1e9
        for i in range(0, n, paso):
            v = rg.Point3d(hm.Vertices[i])
            if int(abertura) == 0 and v.Z > z_tope - 0.6:
                continue
            if int(abertura) == 1 and v.Z < z_base + 0.6:
                continue
            cp = medir.ClosestPoint(v)
            d = v.DistanceTo(cp)
            if not mate.IsPointInside(v, tol, False):
                d = -d
            mn = min(mn, d)
        return mn

    def main(g):
        log = []
        tol = _tol()
        holgura = float(g.get("Holgura") or 0.0)
        pared = _num(g.get("ParedMin"), 3.0)
        piso = _num(g.get("PisoMin"), 4.0)
        auto = True if g.get("AutoAjuste") is None else bool(g.get("AutoAjuste"))
        ejecutar = True if g.get("Ejecutar") is None else bool(g.get("Ejecutar"))

        lista = _lista(g.get("Huecos")) or ["polimero"]
        aberturas = _lista(g.get("Abertura"))
        hundires = _lista(g.get("Hundir"))
        huecos_def = resolver_huecos(lista)
        n = len(huecos_def)
        ab = [int(aberturas[min(i, len(aberturas) - 1)]) if aberturas else 0 for i in range(n)]
        hu = [float(hundires[min(i, len(hundires) - 1)]) if hundires else 0.0 for i in range(n)]

        for (nom, canon, tris, info) in huecos_def:
            log.append("Hueco '%s': %s" % (nom, info))

        # ---------------- MATE ----------------
        mate = _geom(g.get("MateCustom"))
        ruta_mate = g.get("MateSTL")
        perfiles = []
        generado = False
        facetado = False
        cortes = []
        if mate is None and ruta_mate and os.path.isfile(str(ruta_mate)):
            mate = malla_desde_tris(leer_stl(str(ruta_mate)))
            log.append("Mate desde STL: %s" % os.path.basename(str(ruta_mate)))
        if mate is None:
            generado = True
            p = parametros_tipo(g.get("Tipo") or 0, g.get("Altura"), g.get("DiamMax"),
                                g.get("DiamBoca"), g.get("AltPie"), g.get("DiamPie"))
            log.append("Tipo: %s" % p["nombre"])
            idx_rev = [i for i, h in enumerate(huecos_def) if h[1] is not None]
            p, s, w, rzs, denso, alog = autoajustar(
                p, [huecos_def[i][1] for i in idx_rev], [ab[i] for i in idx_rev],
                [hu[i] for i in idx_rev], holgura, pared, piso, auto)
            log += alog
            pie, panza, tapa, denso = perfil_mate(p, s)
            mate, segs = brep_mate(pie, panza, tapa, 0.0, 0.0)
            perfiles += segs
            cx, cy, z_tope, z_base = 0.0, 0.0, p["H"], 0.0
            nuevo, sumar, cortes, dlog = detalles_mate(p, s, denso, cx, cy)
            log += dlog
            if nuevo is not None:
                mate = nuevo
                facetado = True
            if sumar:
                u = rg.Brep.CreateBooleanUnion(NetList[rg.Brep]([mate] + sumar), tol)
                if u and len(u) > 0:
                    mate = u[0]
                else:                       # reintento de a una pieza
                    fallas = 0
                    for b in sumar:
                        u = rg.Brep.CreateBooleanUnion(NetList[rg.Brep]([mate, b]), tol)
                        if u and len(u) > 0:
                            mate = u[0]
                        else:
                            fallas += 1
                    if fallas:
                        log.append("AVISO: %d detalle(s) no se pudieron unir al cuerpo" % fallas)
        else:
            bb = mate.GetBoundingBox(True)
            cx, cy = bb.Center.X, bb.Center.Y
            z_tope, z_base = bb.Max.Z, bb.Min.Z
            log.append("Mate propio: eje en (%.2f, %.2f), z %.2f..%.2f" % (cx, cy, z_base, z_tope))

        # ---------------- HUECOS ----------------
        huecos = []
        rz_2d, ab_2d = [], []
        for i, (nom, canon, tris, info) in enumerate(huecos_def):
            if canon is not None:
                rz = colocar_hueco(perfil_hueco(canon, holgura, hu[i]), ab[i], z_tope, z_base, hu[i])
                b, segs = brep_hueco(rz, cx, cy)
                huecos.append(b); perfiles += segs
                rz_2d.append(rz); ab_2d.append(ab[i])
            elif tris is not None:
                if holgura:
                    log.append("  (holgura no aplicada a '%s': malla no revolucion)" % nom)
                huecos.append(colocar_malla(tris, ab[i], cx, cy, z_tope, z_base, hu[i]))

        # ---------------- CONTROL DE PAREDES ----------------
        pared_med, piso_med = None, None
        if generado and len(rz_2d) == len(huecos) and not facetado:
            pared_med = pared_2d(denso, rz_2d, ab_2d, z_tope)
            piso_med = piso_2d(rz_2d, ab_2d, z_tope)
        elif huecos:
            pared_med = min(pared_3d(mate, h, ab[i], z_tope, z_base) for i, h in enumerate(huecos))
        if pared_med is not None:
            estado = "OK" if pared_med >= pared - 1e-3 else ("SE SALE DEL MATE" if pared_med < 0 else "FINA")
            log.append("Pared minima: %.2f mm (%s, pedida %.1f)" % (pared_med, estado, pared))
        if piso_med is not None and piso_med < 1e8:
            log.append("Fondo minimo: %.2f mm" % piso_med)

        # ---------------- BOOLEANA ----------------
        resultado = None
        restas = huecos + cortes
        if ejecutar and huecos:
            todo_brep = isinstance(mate, rg.Brep) and all(isinstance(h, rg.Brep) for h in restas)
            if todo_brep:
                r = rg.Brep.CreateBooleanDifference(NetList[rg.Brep]([mate]),
                                                    NetList[rg.Brep](restas), tol)
                if r and len(r) > 0:
                    resultado = list(r)
                else:
                    log.append("Booleana Brep fallo -> reintento con mallas")
                    todo_brep = False
            if not todo_brep:
                r = rg.Mesh.CreateBooleanDifference(NetList[rg.Mesh]([a_malla(mate)]),
                                                    NetList[rg.Mesh]([a_malla(h) for h in restas]))
                if r and len(r) > 0:
                    resultado = list(r)
            if resultado:
                vol = 0.0
                for x in resultado:
                    try:
                        vol += x.GetVolume()
                    except Exception:
                        pass
                log.append("Booleana OK - volumen %.1f cm3 (%.0f g en PLA aprox.)" %
                           (vol / 1000.0, vol / 1000.0 * 1.24))
            else:
                log.append("ERROR: la booleana no devolvio resultado")
        elif not ejecutar:
            log.append("Ejecutar = False (solo vista previa)")

        # ---------------- EXPORTAR ----------------
        ruta = g.get("ExportarSTL")
        if resultado and ruta:
            ruta = str(ruta)
            if not ruta.lower().endswith(".stl"):
                ruta += ".stl"
            tris = []
            for x in resultado:
                tris += tris_desde_malla(a_malla(x))
            escribir_stl(ruta, tris)
            log.append("Exportado: %s (%d triangulos)" % (ruta, len(tris)))

        return mate, huecos, resultado, perfiles, "\n".join(log), pared_med, piso_med

    _g = globals()
    Mate, Huecos, Resultado, Perfiles, Info, Pared, Piso = main(_g)
