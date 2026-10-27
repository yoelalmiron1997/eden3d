# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Plantas 3D para la vista y la foto (no se exportan para imprimir)
==========================================================================
Generadores procedurales de las plantas más comunes en maceta, en Python puro
(corre igual en Rhino, en el navegador con Pyodide y en los tests):

    catalogo()                 -> fichas de cuidado (colecciones/plantas.json)
    build(ids, abertura, seed) -> [(material, V, F)] ya ubicadas en la boca de la maceta
    compatibilidad(ids)        -> avisos si se combinan plantas con cuidados distintos

abertura = {"r_in": radio interior a la altura de la tierra, "z_s": z de la tierra,
            "z_top": z del borde, "r_out": radio exterior máximo, "z_bot": base}
Cada generador arma la planta con base en (0, 0, 0) y "huella" de radio R.
"""
import json
import math
import os
import random

TAU = 2.0 * math.pi
GOLD = math.radians(137.508)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "colecciones", "plantas.json")
MAX_PLANTAS = 4

# material -> color (RGB) y brillo, compartido por la web y Rhino
MATERIALES = {
    "verde_suculenta": ((132, 168, 140), 0.35),
    "verde_oscuro": ((52, 92, 62), 0.30),
    "verde_aloe": ((120, 150, 112), 0.30),
    "verde_sanse": ((58, 98, 60), 0.35),
    "borde_sanse": ((196, 186, 92), 0.30),
    "verde_cactus": ((78, 128, 76), 0.20),
    "verde_jade": ((78, 132, 70), 0.55),
    "verde_potus": ((84, 150, 64), 0.50),
    "perla": ((112, 158, 88), 0.40),
    "lithops": ((176, 160, 132), 0.15),
    "lithops_top": ((150, 134, 108), 0.15),
    "espinas": ((236, 230, 214), 0.10),
    "flor": ((226, 112, 160), 0.20),
    "tallo": ((96, 120, 70), 0.20),
    "tronco": ((112, 92, 66), 0.10),
    "banda": ((226, 226, 214), 0.10),
    # nativas
    "verde_hoja": ((74, 120, 58), 0.30),
    "verde_claro": ((118, 158, 72), 0.25),
    "verde_yerba": ((46, 98, 50), 0.55),
    "verde_arrayan": ((40, 78, 44), 0.50),
    "verde_pasto": ((116, 136, 82), 0.20),
    "verde_cardon": ((96, 128, 84), 0.15),
    "flor_roja": ((200, 28, 36), 0.30),
    "flor_violeta": ((136, 104, 196), 0.20),
    "flor_rosa": ((222, 104, 168), 0.25),
    "flor_amarilla": ((246, 196, 40), 0.15),
    "flor_blanca": ((246, 244, 236), 0.15),
    "pluma": ((238, 230, 210), 0.05),
    "corteza_canela": ((190, 104, 58), 0.20),
    "corteza_gris": ((120, 108, 96), 0.08),
    # coberturas de la tierra
    "tierra": ((88, 64, 46), 0.0),
    "tierra_oscura": ((52, 38, 28), 0.0),
    "piedra": ((228, 222, 210), 0.05),
    "arcilla": ((172, 108, 72), 0.05),
    "leca": ((168, 96, 60), 0.10),
    "corteza_pino": ((122, 70, 40), 0.05),
    "volcanica": ((112, 52, 40), 0.0),
    "volcanica_negra": ((48, 44, 42), 0.05),
    "musgo": ((86, 120, 52), 0.0),
}

# materiales que no son de la planta (no se mueven con el viento)
DECOR_MATS = ("tierra", "tierra_oscura", "piedra", "arcilla", "leca", "corteza_pino",
              "volcanica", "volcanica_negra", "musgo")

# cobertura de la tierra: id -> (nombre, descripción)
COBERTURAS = {
    "piedra_blanca": ("Piedritas blancas", "Canto rodado blanco con algunas bolitas de arcilla."),
    "tierra": ("Tierra negra", "Sustrato universal a la vista, sin cobertura."),
    "leca": ("Arcilla expandida", "Bolitas de LECA: aireadas y livianas, ideales con autorriego."),
    "corteza": ("Corteza de pino", "Chips de corteza: guardan humedad, para plantas de riego frecuente."),
    "volcanica": ("Piedra volcánica", "Grava roja y negra: drena rápido, ideal para cactus y suculentas."),
    "musgo": ("Musgo", "Cobertura verde que mantiene la humedad de la superficie."),
}
COBERTURA_SUGERIDA = {"seco": "volcanica", "medio": "piedra_blanca", "humedo": "musgo"}


# ===================================================================== datos
_CACHE = {}


def catalogo():
    if "cat" not in _CACHE:
        with open(DATA, encoding="utf-8") as fh:
            _CACHE["cat"] = json.load(fh)
    return _CACHE["cat"]


def ficha(pid):
    for p in catalogo()["plantas"]:
        if p["id"] == pid:
            return p
    raise KeyError("planta desconocida: %s" % pid)


def _y(nombres):
    """'A', 'A y B', 'A, B y C'."""
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def compatibilidad(ids):
    """Avisos al combinar plantas en la misma maceta (mismo sustrato y riego)."""
    ids = list(dict.fromkeys(ids))
    out = []
    if len(ids) > MAX_PLANTAS:
        out.append({"nivel": "error", "texto": "Elegí hasta %d plantas por maceta." % MAX_PLANTAS})
    fs = [ficha(i) for i in ids[:MAX_PLANTAS]]
    if len(fs) < 2:
        return out
    orden_r = {"seco": 0, "medio": 1, "humedo": 2}
    orden_l = {"sol": 0, "brillante": 1, "media": 2}
    rs = {f["id"]: orden_r[f["grupo_riego"]] for f in fs}
    ls = {f["id"]: orden_l[f["grupo_luz"]] for f in fs}
    nom = {f["id"]: f["nombre"] for f in fs}
    if max(rs.values()) - min(rs.values()) >= 1:
        secas = [nom[i] for i, v in rs.items() if v == 0]
        otras = [nom[i] for i, v in rs.items() if v > 0]
        out.append({"nivel": "alerta" if max(rs.values()) - min(rs.values()) >= 2 else "aviso",
                    "texto": "Riego distinto: %s necesita%s secarse entre riegos y %s quiere%s "
                             "tierra más húmeda. En la misma maceta va a sufrir alguna: mejor en "
                             "macetas separadas." % (_y(secas), "n" if len(secas) > 1 else "",
                                                     _y(otras), "n" if len(otras) > 1 else "")})
    if max(ls.values()) - min(ls.values()) >= 2:
        sol = [nom[i] for i, v in ls.items() if v == 0]
        sombra = [nom[i] for i, v in ls.items() if v == 2]
        out.append({"nivel": "alerta",
                    "texto": "Luz distinta: %s %s sol directo y %s %s luz media. No hay un lugar "
                             "que les venga bien a %s." % (
                                 _y(sol), "piden" if len(sol) > 1 else "pide", _y(sombra),
                                 "prefieren" if len(sombra) > 1 else "prefiere",
                                 "las dos" if len(fs) == 2 else "todas")})
    tipos = [f["tipo"] for f in fs]
    if sum("Cactus" in t for t in tipos) >= 1 and all(f["grupo_riego"] == "seco" for f in fs):
        out.append({"nivel": "aviso", "texto": "Combinando cactus: usá sustrato muy mineral para todas "
                                              "y regá según la más sensible al exceso de agua."})
    if not out:
        out.append({"nivel": "ok", "texto": "Combinación compatible: comparten riego y luz."})
    return out


# ===================================================================== mallas
class Mesh(object):
    def __init__(self):
        self.parts = {}

    def add(self, mat, V, F):
        Vs, Fs = self.parts.setdefault(mat, ([], []))
        o = len(Vs)
        Vs.extend(V)
        Fs.extend((a + o, b + o, c + o) for a, b, c in F)

    def items(self):
        return [(m, V, F) for m, (V, F) in self.parts.items() if F]


def _rot(V, yaw=0.0, pitch=0.0, roll=0.0, t=(0.0, 0.0, 0.0), s=1.0):
    """Escala, gira (roll X, pitch Y, yaw Z) y traslada."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    out = []
    for x, y, z in V:
        x, y, z = x * s, y * s, z * s
        y, z = y * cr - z * sr, y * sr + z * cr
        x, z = x * cp + z * sp, -x * sp + z * cp
        x, y = x * cy - y * sy, x * sy + y * cy
        out.append((x + t[0], y + t[1], z + t[2]))
    return out


def ellipsoid(a, b, c, nu=14, nv=9, bump=None):
    """Elipsoide cerrado centrado en el origen. bump(theta, phi) -> factor."""
    V = [(0.0, 0.0, -c)]
    for j in range(1, nv):
        ph = math.pi * j / nv - math.pi / 2
        for i in range(nu):
            th = TAU * i / nu
            k = bump(th, ph) if bump else 1.0
            V.append((a * math.cos(ph) * math.cos(th) * k, b * math.cos(ph) * math.sin(th) * k,
                      c * math.sin(ph) * k))
    V.append((0.0, 0.0, c))
    top = len(V) - 1
    F = [(0, 1 + (i + 1) % nu, 1 + i) for i in range(nu)]
    for j in range(nv - 2):
        r0, r1 = 1 + j * nu, 1 + (j + 1) * nu
        for i in range(nu):
            a_, b_ = r0 + i, r0 + (i + 1) % nu
            c_, d_ = r1 + (i + 1) % nu, r1 + i
            F += [(a_, b_, c_), (a_, c_, d_)]
    r0 = 1 + (nv - 2) * nu
    F += [(top, r0 + i, r0 + (i + 1) % nu) for i in range(nu)]
    return V, F


def lathe(profile, n=32, rmod=None):
    """Sólido de revolución cerrado: profile = [(r, z)] de abajo hacia arriba
    (r del primero y del último se cierran con un punto central)."""
    V = [(0.0, 0.0, profile[0][1])]
    for r, z in profile:
        for i in range(n):
            th = TAU * i / n
            k = rmod(th, z) if rmod else 1.0
            V.append((r * k * math.cos(th), r * k * math.sin(th), z))
    V.append((0.0, 0.0, profile[-1][1]))
    top = len(V) - 1
    F = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    for j in range(len(profile) - 1):
        r0, r1 = 1 + j * n, 1 + (j + 1) * n
        for i in range(n):
            a_, b_ = r0 + i, r0 + (i + 1) % n
            c_, d_ = r1 + (i + 1) % n, r1 + i
            F += [(a_, b_, c_), (a_, c_, d_)]
    r0 = 1 + (len(profile) - 1) * n
    F += [(top, r0 + i, r0 + (i + 1) % n) for i in range(n)]
    return V, F


def tube(path, radius, n=8):
    """Tubo cerrado a lo largo de path [(x,y,z)]; radius: número o lista."""
    rs = radius if isinstance(radius, (list, tuple)) else [radius] * len(path)
    V, rings = [], []
    up = (0.0, 0.0, 1.0)
    for k, p in enumerate(path):
        q0 = path[max(k - 1, 0)]
        q1 = path[min(k + 1, len(path) - 1)]
        t = (q1[0] - q0[0], q1[1] - q0[1], q1[2] - q0[2])
        L = math.sqrt(sum(c * c for c in t)) or 1.0
        t = tuple(c / L for c in t)
        ref = up if abs(t[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = (t[1] * ref[2] - t[2] * ref[1], t[2] * ref[0] - t[0] * ref[2], t[0] * ref[1] - t[1] * ref[0])
        Lu = math.sqrt(sum(c * c for c in u)) or 1.0
        u = tuple(c / Lu for c in u)
        w = (t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0])
        ring = []
        for i in range(n):
            a = TAU * i / n
            ca, sa = math.cos(a) * rs[k], math.sin(a) * rs[k]
            V.append((p[0] + u[0] * ca + w[0] * sa, p[1] + u[1] * ca + w[1] * sa,
                      p[2] + u[2] * ca + w[2] * sa))
            ring.append(len(V) - 1)
        rings.append(ring)
    F = []
    for a_r, b_r in zip(rings, rings[1:]):
        for i in range(n):
            a, b = a_r[i], a_r[(i + 1) % n]
            c, d = b_r[(i + 1) % n], b_r[i]
            F += [(a, b, c), (a, c, d)]
    for ring, p, flip in ((rings[0], path[0], True), (rings[-1], path[-1], False)):
        V.append(p)
        cidx = len(V) - 1
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            F.append((cidx, b, a) if flip else (cidx, a, b))
    return V, F


def leaf(L, width, thick, a0, a1, cup=0.1, nu=16, nv=8, droop=0.0):
    """Hoja carnosa genérica: crece en +X y se curva de a0 a a1 (ángulo sobre la
    horizontal). width(t)/thick(t) en mm; droop baja la punta (hojas arqueadas)."""
    pts, angs = [(0.0, 0.0)], [a0]
    x = z = 0.0
    for i in range(1, nu + 1):
        t = i / float(nu)
        a = a0 + (a1 - a0) * t ** 1.3 - droop * t * t
        x += math.cos(a) * L / nu
        z += math.sin(a) * L / nu
        pts.append((x, z))
        angs.append(a)
    V, F, top, bot = [], [], [], []
    for i in range(nu + 1):
        t = i / float(nu)
        cx, cz = pts[i]
        nx, nz = -math.sin(angs[i]), math.cos(angs[i])
        w = max(width(t), 0.05)
        th = max(thick(t), 0.08)
        rt, rb = [], []
        for j in range(nv + 1):
            s = -1.0 + 2.0 * j / nv
            e = math.sqrt(max(0.0, 1.0 - s * s))
            lift = cup * w * s * s
            if j in (0, nv):
                V.append((cx + nx * lift, s * w, cz + nz * lift))
                rt.append(len(V) - 1)
                rb.append(len(V) - 1)
                continue
            V.append((cx + nx * (th * 0.5 * e + lift), s * w, cz + nz * (th * 0.5 * e + lift)))
            rt.append(len(V) - 1)
            V.append((cx + nx * (-th * 0.5 * e + lift), s * w, cz + nz * (-th * 0.5 * e + lift)))
            rb.append(len(V) - 1)
        top.append(rt)
        bot.append(rb)
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]
            F += [(a, b, c), (a, c, d)]
            a, b, c, d = bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]
            F += [(a, c, b), (a, d, c)]
    V.append((0.0, 0.0, 0.0))
    c0 = len(V) - 1
    ring = top[0] + bot[0][::-1][1:-1]
    for k in range(len(ring)):
        F.append((c0, ring[(k + 1) % len(ring)], ring[k]))
    return V, F


def _clean(V, F):
    """Saca triángulos de área ~0 (puntas colapsadas)."""
    out = []
    for a, b, c in F:
        A, B, C = V[a], V[b], V[c]
        ux, uy, uz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
        vx, vy, vz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        if nx * nx + ny * ny + nz * nz > 1e-12:
            out.append((a, b, c))
    return V, out


# ===================================================================== plantas
def _rosette(m, rnd, R, n, Lf, Wf, Tf, ang_in, ang_out, curl, mat, width_fn=None,
             droop=0.0, spread=0.05):
    L_out = R / max(math.cos(math.radians(ang_out)) * 0.9, 0.25)
    for k in range(n):
        f = k / float(max(n - 1, 1))                        # 0 centro -> 1 afuera
        L = L_out * Lf(f)
        a0 = math.radians(ang_in + (ang_out - ang_in) * f ** 0.8 + rnd.uniform(-4, 4))
        a1 = a0 + math.radians(curl(f))
        W = L * Wf
        T = L * Tf
        shape = width_fn or (lambda t: math.sin(math.pi * min(1.0, 0.15 + 0.85 * t) ** 0.85)
                             * (1 - t ** 6))
        V, F = leaf(L, lambda t, W=W, g=shape: W * g(t), lambda t, T=T: T * (1 - t) ** 0.6,
                    a0, max(-1.2, min(a1, math.radians(88))), cup=0.12, droop=droop)
        ang = k * GOLD + rnd.uniform(-0.06, 0.06)
        m.add(mat, *_clean(_rot(V, yaw=ang, t=(R * spread * f * math.cos(ang),
                                               R * spread * f * math.sin(ang), 1.5 * (1 - f))), F))


def p_echeveria(m, R, ctx, rnd):
    _rosette(m, rnd, R, 34, lambda f: 0.30 + 0.70 * f ** 0.75, 0.40, 0.22, 78, 14,
             lambda f: 16 + 22 * f, "verde_suculenta")


def p_haworthia(m, R, ctx, rnd):
    tri = lambda t: (1 - t) ** 0.9 * min(1.0, 3.5 * t + 0.3)
    _rosette(m, rnd, R, 26, lambda f: 0.45 + 0.55 * f, 0.30, 0.34, 72, 34,
             lambda f: 10 + 8 * f, "verde_oscuro", width_fn=tri)
    # bandas blancas: puntitos en la cara externa de las hojas exteriores
    for k in range(10, 26):
        f = k / 25.0
        ang = k * GOLD
        L = R / 0.85 * (0.45 + 0.55 * f)
        a = math.radians(72 + (34 - 72) * f ** 0.8)
        for s in (0.25, 0.4, 0.55, 0.7):
            x, z = math.cos(a) * L * s, math.sin(a) * L * s
            off = -0.17 * L * (1 - s)
            V, F = ellipsoid(0.12 * L * (1 - s) + 0.5, 0.55, 0.35, 8, 5)
            V = _rot(V, pitch=-a, t=(x - math.sin(a) * off * 0.2, 0, z + off * 0.1))
            m.add("banda", *_clean(_rot(V, yaw=ang), F))


def p_aloe(m, R, ctx, rnd):
    tri = lambda t: (1 - t) ** 0.8 * min(1.0, 2.5 * t + 0.5)
    _rosette(m, rnd, R * 0.75, 12, lambda f: 0.65 + 0.55 * f, 0.20, 0.13, 82, 52,
             lambda f: -12 - 10 * f, "verde_aloe", width_fn=tri)


def p_sansevieria(m, R, ctx, rnd):
    n = 7
    sword = lambda t: math.sin(math.pi * min(1.0, 0.2 + 0.8 * t) ** 0.5) * (1 - t ** 2.2)
    for k in range(n):
        ang = TAU * k / n + rnd.uniform(-0.3, 0.3)
        L = R * rnd.uniform(2.4, 3.3)
        W = L * 0.11
        a0 = math.radians(rnd.uniform(78, 86))
        V, F = leaf(L, lambda t, W=W: W * sword(t), lambda t: 0.9 + 0.6 * (1 - t), a0,
                    math.radians(89), cup=0.25, nu=22, nv=8)
        rr = R * 0.28 * math.sqrt(rnd.random())
        tt = rnd.uniform(0, TAU)
        V = _rot(V, roll=rnd.uniform(-0.2, 0.2), yaw=ang, t=(rr * math.cos(tt), rr * math.sin(tt), 0))
        m.add("verde_sanse", *_clean(V, F))


def _areoles(m, rnd, pts, size, mat="espinas"):
    for (x, y, z) in pts:
        V, F = ellipsoid(size, size, size * 0.8, 7, 4)
        m.add(mat, *_clean(_rot(V, t=(x, y, z)), F))


def p_cereus(m, R, ctx, rnd):
    ribs = 7
    for col, (h, rad, ox, oy) in enumerate(((3.1 * R, 0.34 * R, 0.0, 0.0),
                                            (2.0 * R, 0.26 * R, 0.45 * R, 0.2 * R),
                                            (1.4 * R, 0.22 * R, -0.4 * R, 0.35 * R))):
        prof = [(rad * 0.8, 0.0)] + [(rad * (1 - 0.02 * i), h * i / 14.0) for i in range(1, 14)] + \
               [(rad * math.cos(math.pi / 2 * i / 5.0), h + rad * 0.9 * math.sin(math.pi / 2 * i / 5.0))
                for i in range(1, 6)]
        prof[-1] = (0.01, prof[-1][1])
        rm = lambda th, z: 1.0 + 0.14 * math.cos(ribs * th)
        V, F = lathe(prof, 56, rm)
        m.add("verde_cactus", *_clean(_rot(V, yaw=col * 0.4, t=(ox, oy, 0)), F))
        pts = []
        for r in range(ribs):
            th = TAU * r / ribs + col * 0.4
            z = rad * 0.6
            while z < h:
                rr = rad * 1.14 + 0.4
                pts.append((ox + rr * math.cos(th), oy + rr * math.sin(th), z))
                z += rad * 0.55
        _areoles(m, rnd, pts, max(0.7, rad * 0.07))


def p_mammillaria(m, R, ctx, rnd):
    rad = 0.78 * R
    h = 2.0 * rad
    nb = 89
    tips = []
    for k in range(nb):                      # tubérculos en espiral (filotaxis)
        f = (k + 0.5) / nb
        ph = math.asin(1 - 2 * f * 0.92)     # de arriba hacia abajo
        th = k * GOLD
        tips.append((th, ph))

    def bump(th, ph):
        best = 0.0
        for bt, bp in tips:
            d = math.acos(max(-1.0, min(1.0, math.sin(ph) * math.sin(bp) +
                                         math.cos(ph) * math.cos(bp) * math.cos(th - bt))))
            best = max(best, math.exp(-(d / 0.11) ** 2))
        return 1.0 + 0.10 * best
    V, F = ellipsoid(rad, rad, h * 0.5, 40, 24, bump)
    V = [(x, y, z + h * 0.5) for x, y, z in V]
    m.add("verde_cactus", *_clean(V, F))
    pts = []
    for th, ph in tips:
        rr = 1.12
        pts.append((rad * rr * math.cos(ph) * math.cos(th), rad * rr * math.cos(ph) * math.sin(th),
                    h * 0.5 + h * 0.5 * rr * math.sin(ph)))
    _areoles(m, rnd, pts, max(0.6, rad * 0.035))
    for k in range(9):                       # corona de flores
        th = TAU * k / 9 + rnd.uniform(-0.1, 0.1)
        ph = math.radians(58)
        V, F = ellipsoid(rad * 0.09, rad * 0.09, rad * 0.06, 10, 6)
        m.add("flor", *_clean(_rot(V, t=(rad * 1.02 * math.cos(ph) * math.cos(th),
                                         rad * 1.02 * math.cos(ph) * math.sin(th),
                                         h * 0.5 + h * 0.5 * 1.02 * math.sin(ph))), F))


def p_opuntia(m, R, ctx, rnd):
    pads = [((0.0, 0.0, 0.62 * R), 0.0, 0.0, 1.0)]
    pads += [((-0.32 * R, 0.0, 1.55 * R), 0.0, -0.42, 0.72), ((0.34 * R, 0.0, 1.5 * R), 0.0, 0.38, 0.68),
             ((0.05 * R, 0.0, 2.15 * R), 0.0, 0.08, 0.55)]
    for (x, y, z), yaw, tilt, s in pads:
        a, b, c = 0.46 * R * s, 0.09 * R * s, 0.62 * R * s
        V, F = ellipsoid(a, b, c, 24, 14)
        yy = yaw + rnd.uniform(-0.25, 0.25)
        m.add("verde_cactus", *_clean(_rot(V, pitch=tilt, yaw=yy, t=(x, y, z)), F))
        pts = []
        for i in range(-2, 3):
            for j in range(-3, 4):
                u, v = i * 0.35, j * 0.27
                if u * u + v * v > 0.85:
                    continue
                for side in (-1, 1):
                    pts.append((u * a, side * b * math.sqrt(max(0.0, 1 - u * u - v * v)) * 1.05, v * c))
        pts = _rot(pts, pitch=tilt, yaw=yy, t=(x, y, z))
        _areoles(m, rnd, pts, max(0.6, R * 0.025))


def p_crassula(m, R, ctx, rnd):
    h = 0.9 * R
    trunk = [(0, 0, 0), (0.02 * R, 0, h * 0.4), (-0.03 * R, 0.02 * R, h * 0.8), (0, 0, h)]
    m.add("tronco", *tube(trunk, [0.16 * R, 0.14 * R, 0.12 * R, 0.1 * R], 10))
    nb = 5
    for k in range(nb):
        ang = TAU * k / nb + rnd.uniform(-0.3, 0.3)
        z0 = h * rnd.uniform(0.55, 0.95)
        L = R * rnd.uniform(0.55, 0.8)
        end = (L * math.cos(ang), L * math.sin(ang), z0 + L * rnd.uniform(0.4, 0.8))
        mid = (end[0] * 0.5, end[1] * 0.5, (z0 + end[2]) * 0.5 - 0.05 * R)
        m.add("tronco", *tube([(0, 0, z0), mid, end], [0.08 * R, 0.065 * R, 0.05 * R], 8))
        for j in range(8):                     # hojas ovaladas en pares
            pair = j // 2
            side = 1 if j % 2 else -1
            t = 0.55 + 0.15 * pair
            px = mid[0] + (end[0] - mid[0]) * t * 1.3
            py = mid[1] + (end[1] - mid[1]) * t * 1.3
            pz = mid[2] + (end[2] - mid[2]) * t * 1.3 + 0.05 * R * pair
            V, F = ellipsoid(0.17 * R, 0.065 * R, 0.11 * R, 14, 8)
            V = _rot(V, pitch=-0.6 - 0.2 * pair, yaw=ang + side * 1.2 + pair * 0.8,
                     t=(px, py, pz))
            m.add("verde_jade", *_clean(V, F))


def _hanging_path(ctx, ang, depth, rnd, start_r=0.0):
    """Tallo que sale de la tierra, pasa el borde y cae por afuera de la maceta
    (coordenadas de la planta: z=0 es la tierra)."""
    r_in, r_out = ctx["r_in"], ctx["r_out"]
    over = ctx["z_top"] - ctx["z_s"] + 2.5               # altura del borde sobre la tierra
    drop = -(ctx["z_s"] - ctx["z_bot"]) * depth
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    ctrl = [(start_r, 0.0), (r_in * 0.65, over * 0.9), (r_in + 2.0, over + 1.5),
            (r_out + 3.5, over * 0.4), (r_out + 5.0, drop * 0.5), (r_out + 4.0 + rnd.uniform(-2, 2), drop)]
    for i in range(len(ctrl) - 1):
        (r0, z0), (r1, z1) = ctrl[i], ctrl[i + 1]
        for k in range(6):
            t = k / 6.0
            r = r0 + (r1 - r0) * t
            z = z0 + (z1 - z0) * t
            pts.append((r * ca, r * sa, z))
    pts.append((ctrl[-1][0] * ca, ctrl[-1][0] * sa, ctrl[-1][1]))
    return pts


def _resample(path, step):
    out = [path[0]]
    acc = 0.0
    for a, b in zip(path, path[1:]):
        L = math.dist(a, b)
        while acc + L >= step and L > 0:
            t = (step - acc) / L
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
            out.append(a)
            L = math.dist(a, b)
            acc = 0.0
        acc += L
    return out


def p_senecio(m, R, ctx, rnd):
    pr = max(2.4, R * 0.075)
    for k in range(9):
        ang = TAU * k / 9 + rnd.uniform(-0.2, 0.2)
        path = _hanging_path(ctx, ang, rnd.uniform(0.3, 0.85), rnd, start_r=R * 0.2)
        m.add("tallo", *tube(path, 0.45, 5))
        for i, p in enumerate(_resample(path, pr * 2.3)[1:]):
            V, F = ellipsoid(pr, pr, pr * 1.05, 10, 7)
            m.add("perla", *_clean(_rot(V, t=(p[0] + rnd.uniform(-0.5, 0.5),
                                               p[1] + rnd.uniform(-0.5, 0.5), p[2])), F))
    # mata central de perlas sobre la tierra
    for k in range(40):
        rr = R * 0.6 * math.sqrt(rnd.random())
        th = rnd.uniform(0, TAU)
        V, F = ellipsoid(pr, pr, pr, 10, 7)
        m.add("perla", *_clean(_rot(V, t=(rr * math.cos(th), rr * math.sin(th),
                                           pr + rnd.uniform(0, 2.5 * pr))), F))


def heart_leaf(size, thick=0.7, n=28):
    """Hoja acorazonada fina (cerrada), en el plano XZ mirando +Y, punta hacia +Z."""
    out = []
    for i in range(n):
        t = TAU * i / n
        x = 16 * math.sin(t) ** 3
        z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((x / 17.0 * size * 0.5, -z / 17.0 * size * 0.5 + size * 0.35))
    V = [(0.0, thick * 0.5, size * 0.35), (0.0, -thick * 0.5, size * 0.35)]
    for x, z in out:
        V.append((x, 0.0, z))
    F = []
    for i in range(n):
        a, b = 2 + i, 2 + (i + 1) % n
        F += [(0, a, b), (1, b, a)]
    return V, F


def p_pothos(m, R, ctx, rnd):
    for k in range(6):
        ang = TAU * k / 6 + rnd.uniform(-0.25, 0.25)
        path = _hanging_path(ctx, ang, rnd.uniform(0.4, 0.85), rnd, start_r=R * 0.15)
        m.add("tallo", *tube(path, 0.9, 6))
        pts = _resample(path, R * 0.42)
        for i, p in enumerate(pts[1:]):
            size = R * rnd.uniform(0.38, 0.5)
            V, F = heart_leaf(size)
            side = 1 if i % 2 else -1
            V = _rot(V, pitch=math.radians(180 + rnd.uniform(-35, 35)),
                     yaw=ang + side * 1.1 + rnd.uniform(-0.3, 0.3),
                     roll=rnd.uniform(-0.4, 0.4), t=p)
            m.add("verde_potus", *_clean(V, F))
    for k in range(7):                          # hojas paradas en el centro
        ang = k * GOLD
        size = R * rnd.uniform(0.45, 0.6)
        V, F = heart_leaf(size)
        V = _rot(V, pitch=math.radians(rnd.uniform(-25, 25)), yaw=ang,
                 t=(R * 0.2 * math.cos(ang), R * 0.2 * math.sin(ang), R * rnd.uniform(0.3, 0.7)))
        m.add("verde_potus", *_clean(V, F))
        m.add("tallo", *tube([(0, 0, 0), (R * 0.2 * math.cos(ang), R * 0.2 * math.sin(ang),
                                          R * rnd.uniform(0.3, 0.6))], 0.8, 5))


def p_lithops(m, R, ctx, rnd):
    n = 5
    for k in range(n):
        if k == 0:
            cx = cy = 0.0
        else:
            a = TAU * (k - 1) / (n - 1) + rnd.uniform(-0.3, 0.3)
            cx, cy = 0.52 * R * math.cos(a), 0.52 * R * math.sin(a)
        s = R * rnd.uniform(0.22, 0.3)
        yaw = rnd.uniform(0, TAU)
        for side in (-1, 1):                   # dos hojas fusionadas con la fisura
            V, F = ellipsoid(s * 0.55, s * 0.95, s * 0.9, 18, 12)
            V = [(x, y, min(z, s * 0.5)) for x, y, z in V]
            V = _rot(V, yaw=yaw, t=(cx + side * s * 0.6 * math.cos(yaw), cy + side * s * 0.6 *
                                    math.sin(yaw), s * 0.25))
            m.add("lithops", *_clean(V, F))


# ===================================================================== nativas
def _pad(m, rnd, c, a, b, h, mat, leaves=None, n_leaf=0, leaf_size=1.0):
    """Mata de follaje (estilo bonsái): elipsoide abollado + hojitas en la superficie."""
    bumps = [(rnd.uniform(0, TAU), rnd.uniform(-0.8, 1.2), rnd.uniform(0.08, 0.16)) for _ in range(6)]

    def bump(th, ph):
        k = 1.0
        for bt, bp, amp in bumps:
            k += amp * math.cos(th - bt) * math.cos(ph - bp)
        return k
    V, F = ellipsoid(a, b, h, 16, 9, bump)
    m.add(mat, *_clean(_rot(V, yaw=rnd.uniform(0, TAU), t=c), F))
    for _ in range(n_leaf):
        th = rnd.uniform(0, TAU)
        ph = rnd.uniform(-0.2, 1.2)
        p = (c[0] + a * 0.95 * math.cos(ph) * math.cos(th), c[1] + b * 0.95 * math.cos(ph) * math.sin(th),
             c[2] + h * 0.95 * math.sin(ph))
        L = leaf_size * rnd.uniform(0.8, 1.2)
        V, F = leaf(L, lambda t, L=L: 0.28 * L * math.sin(math.pi * t) + 0.02, lambda t: 0.25,
                    ph * 0.6, ph * 0.6 + 0.3, cup=0.05, nu=4, nv=2)
        m.add(leaves or mat, *_clean(_rot(V, yaw=th, t=p), F))


def _blossoms(m, rnd, c, a, b, h, n, mat, size, shape=(1.0, 1.0, 0.8), only_top=False):
    """Flores (o pompones) sobre la superficie de una mata."""
    for _ in range(n):
        th = rnd.uniform(0, TAU)
        ph = rnd.uniform(0.15 if only_top else -0.3, 1.3)
        s = size * rnd.uniform(0.75, 1.2)
        V, F = ellipsoid(s * shape[0], s * shape[1], s * shape[2], 8, 5)
        p = (c[0] + a * 1.02 * math.cos(ph) * math.cos(th), c[1] + b * 1.02 * math.cos(ph) * math.sin(th),
             c[2] + h * 1.02 * math.sin(ph))
        m.add(mat, *_clean(_rot(V, yaw=th, pitch=-ph * 0.5, t=p), F))


def _tree(m, rnd, R, h, trunk_r, n_br, trunk_mat, pad_mat, leaf_mat=None, flower_mat=None,
          n_flowers=0, flower_size=1.0, spread=1.0, pad_scale=1.0, base_flare=1.0, n_leaf=10,
          flower_shape=(1.0, 1.0, 0.8)):
    """Árbol joven / bonsái: tronco algo curvo, ramas y matas de follaje con flores."""
    lean = rnd.uniform(-0.12, 0.12) * R
    trunk = [(0, 0, 0), (lean * 0.4, 0.04 * R, h * 0.3), (lean, -0.03 * R, h * 0.62), (lean * 0.7, 0, h)]
    radii = [trunk_r * base_flare, trunk_r * 0.85, trunk_r * 0.68, trunk_r * 0.5]
    m.add(trunk_mat, *tube(trunk, radii, 12))
    if base_flare > 1.2:                                # base engrosada (ombú)
        V, F = lathe([(trunk_r * base_flare * 1.25, 0.0), (trunk_r * base_flare * 1.1, h * 0.06),
                      (trunk_r * base_flare * 0.8, h * 0.16), (trunk_r * 0.8, h * 0.3), (0.01, h * 0.32)], 18,
                     lambda th, z: 1.0 + 0.12 * math.sin(5 * th) * max(0.0, 1 - z / (h * 0.3)))
        m.add(trunk_mat, *_clean(V, F))
    tops = [(lean * 0.7, 0.0, h)]
    for k in range(n_br):
        ang = TAU * k / n_br + rnd.uniform(-0.35, 0.35)
        t0 = rnd.uniform(0.5, 0.85)
        z0 = h * t0
        x0 = lean * t0
        L = R * spread * rnd.uniform(0.55, 0.8)
        end = (x0 + L * math.cos(ang), L * math.sin(ang), z0 + L * rnd.uniform(0.25, 0.6))
        mid = ((x0 + end[0]) * 0.5, end[1] * 0.5, (z0 + end[2]) * 0.5 - 0.04 * R)
        m.add(trunk_mat, *tube([(x0, 0, z0), mid, end], [trunk_r * 0.45, trunk_r * 0.32, trunk_r * 0.2], 7))
        tops.append(end)
    for k, (x, y, z) in enumerate(tops):
        a = R * pad_scale * rnd.uniform(0.32, 0.42) * (1.25 if k == 0 else 1.0)
        hh = a * rnd.uniform(0.45, 0.6)
        c = (x, y, z + hh * 0.35)
        _pad(m, rnd, c, a, a * rnd.uniform(0.8, 1.0), hh, pad_mat, leaf_mat, n_leaf, R * 0.12)
        if flower_mat and n_flowers:
            _blossoms(m, rnd, c, a, a * 0.9, hh, n_flowers, flower_mat, flower_size, flower_shape)


def p_ceibo(m, R, ctx, rnd):
    _tree(m, rnd, R, 1.7 * R, 0.13 * R, 4, "tronco", "verde_hoja", "verde_claro", None,
          spread=1.0, pad_scale=0.85)
    # racimos de flores rojas en las puntas (flores alargadas, tipo cresta de gallo)
    for _ in range(7):
        th = rnd.uniform(0, TAU)
        rr = R * rnd.uniform(0.35, 0.75)
        base = (rr * math.cos(th), rr * math.sin(th), 1.7 * R + R * rnd.uniform(0.0, 0.35))
        for j in range(6):
            s = R * 0.065
            V, F = ellipsoid(s * 0.55, s * 0.5, s * 1.4, 8, 6)
            V = _rot(V, pitch=rnd.uniform(-0.6, 0.6), yaw=rnd.uniform(0, TAU),
                     t=(base[0] + rnd.uniform(-1, 1) * s, base[1] + rnd.uniform(-1, 1) * s, base[2] + j * s * 1.1))
            m.add("flor_roja", *_clean(V, F))


def p_jacaranda(m, R, ctx, rnd):
    _tree(m, rnd, R, 1.9 * R, 0.11 * R, 5, "corteza_gris", "verde_claro", "verde_hoja", "flor_violeta",
          n_flowers=26, flower_size=0.07 * R, spread=1.1, pad_scale=0.85, n_leaf=8,
          flower_shape=(0.8, 0.8, 1.3))


def p_ombu(m, R, ctx, rnd):
    _tree(m, rnd, R, 1.35 * R, 0.16 * R, 5, "corteza_gris", "verde_hoja", "verde_oscuro", None,
          spread=1.15, pad_scale=1.0, base_flare=1.9, n_leaf=14)


def p_lapacho(m, R, ctx, rnd):
    _tree(m, rnd, R, 1.8 * R, 0.11 * R, 4, "corteza_gris", "flor_rosa", "verde_claro", "flor_rosa",
          n_flowers=30, flower_size=0.06 * R, spread=1.0, pad_scale=0.8, n_leaf=4,
          flower_shape=(0.9, 0.9, 1.4))


def p_arrayan(m, R, ctx, rnd):
    _tree(m, rnd, R, 1.6 * R, 0.13 * R, 4, "corteza_canela", "verde_arrayan", "verde_arrayan",
          "flor_blanca", n_flowers=10, flower_size=0.04 * R, spread=0.95, pad_scale=0.85, n_leaf=12)


def p_yerba_mate(m, R, ctx, rnd):
    """Arbusto de varios tallos con hojas ovaladas brillantes."""
    for k in range(5):
        ang = TAU * k / 5 + rnd.uniform(-0.3, 0.3)
        h = R * rnd.uniform(1.2, 1.7)
        lean = R * rnd.uniform(0.25, 0.5)
        path = [(0, 0, 0), (lean * 0.3 * math.cos(ang), lean * 0.3 * math.sin(ang), h * 0.45),
                (lean * math.cos(ang), lean * math.sin(ang), h)]
        m.add("tronco", *tube(path, [0.06 * R, 0.045 * R, 0.03 * R], 7))
        for j in range(9):
            t = 0.3 + 0.7 * j / 8.0
            p = (lean * math.cos(ang) * t ** 1.5, lean * math.sin(ang) * t ** 1.5, h * t)
            V, F = ellipsoid(0.17 * R, 0.075 * R, 0.018 * R + 0.3, 12, 6)
            V = _rot(V, pitch=-rnd.uniform(0.2, 0.7), yaw=ang + (j % 2 * 2 - 1) * 1.2 + rnd.uniform(-0.4, 0.4),
                     t=(p[0] + 0.1 * R * math.cos(ang + (j % 2 * 2 - 1) * 1.2),
                        p[1] + 0.1 * R * math.sin(ang + (j % 2 * 2 - 1) * 1.2), p[2]))
            m.add("verde_yerba", *_clean(V, F))


def p_cortadera(m, R, ctx, rnd):
    """Mata de hojas finas arqueadas y plumeros blancos."""
    narrow = lambda t: math.sin(math.pi * min(1.0, 0.1 + 0.9 * t) ** 0.6) * (1 - t ** 3)
    for k in range(34):
        ang = k * GOLD + rnd.uniform(-0.1, 0.1)
        L = R * rnd.uniform(1.3, 2.0)
        W = R * 0.03
        V, F = leaf(L, lambda t, W=W: W * narrow(t), lambda t: 0.35, math.radians(rnd.uniform(62, 86)),
                    math.radians(rnd.uniform(10, 50)), cup=0.3, nu=12, nv=4, droop=rnd.uniform(0.2, 0.9))
        rr = R * 0.12 * math.sqrt(rnd.random())
        tt = rnd.uniform(0, TAU)
        m.add("verde_pasto", *_clean(_rot(V, yaw=ang, t=(rr * math.cos(tt), rr * math.sin(tt), 0)), F))
    for k in range(4):
        ang = TAU * k / 4 + rnd.uniform(-0.4, 0.4)
        h = R * rnd.uniform(2.1, 2.6)
        off = R * 0.18
        top = (off * math.cos(ang), off * math.sin(ang), h)
        m.add("tallo", *tube([(0, 0, 0), (top[0] * 0.5, top[1] * 0.5, h * 0.5), top], 0.6, 5))
        for j in range(5):
            s = R * 0.12 * (1 - j * 0.12)
            V, F = ellipsoid(s * 0.55, s * 0.55, s * 1.3, 10, 7,
                             lambda th, ph: 1.0 + 0.08 * math.sin(7 * th + 3 * ph))
            m.add("pluma", *_clean(_rot(V, pitch=0.15 * math.cos(ang), roll=0.15 * math.sin(ang),
                                        t=(top[0] * (1 + j * 0.06), top[1] * (1 + j * 0.06),
                                           h + j * s * 0.9)), F))


def p_espinillo(m, R, ctx, rnd):
    """Arbusto ramoso de follaje fino con pompones amarillos y espinas."""
    _tree(m, rnd, R, 1.2 * R, 0.08 * R, 6, "tronco", "verde_claro", "verde_claro", "flor_amarilla",
          n_flowers=16, flower_size=0.06 * R, spread=1.0, pad_scale=0.7, n_leaf=6,
          flower_shape=(1.0, 1.0, 1.0))
    for _ in range(26):                                   # espinas blancas en el tronco
        z = R * rnd.uniform(0.15, 1.1)
        th = rnd.uniform(0, TAU)
        r0 = 0.07 * R
        a = (r0 * math.cos(th), r0 * math.sin(th), z)
        b = ((r0 + 0.12 * R) * math.cos(th), (r0 + 0.12 * R) * math.sin(th), z + 0.03 * R)
        m.add("espinas", *tube([a, b], [0.012 * R + 0.15, 0.1], 4))


def p_cardon(m, R, ctx, rnd):
    """Cardón joven: columna acanalada con brazos de candelabro."""
    ribs = 12
    rad = 0.3 * R
    h = 2.6 * R
    rm = lambda th, z: 1.0 + 0.08 * math.cos(ribs * th)

    def column(x, y, z0, hh, rr, yaw):
        prof = [(rr * 0.85, 0.0)] + [(rr, hh * i / 12.0) for i in range(1, 12)] + \
               [(rr * math.cos(math.pi / 2 * i / 5.0), hh + rr * 0.8 * math.sin(math.pi / 2 * i / 5.0))
                for i in range(1, 6)]
        prof[-1] = (0.01, prof[-1][1])
        V, F = lathe(prof, 60, rm)
        m.add("verde_cardon", *_clean(_rot(V, yaw=yaw, t=(x, y, z0)), F))
        pts = []
        for r in range(ribs):
            th = TAU * r / ribs + yaw
            z = rr * 0.5
            while z < hh:
                pts.append((x + (rr * 1.08 + 0.3) * math.cos(th), y + (rr * 1.08 + 0.3) * math.sin(th), z0 + z))
                z += rr * 0.45
        _areoles(m, rnd, pts, max(0.5, rr * 0.06))
    column(0, 0, 0, h, rad, 0.0)
    for side, zf in ((1, 0.42), (-1, 0.58)):            # brazos: codo horizontal y suben
        ang = rnd.uniform(-0.3, 0.3) + (0 if side > 0 else math.pi)
        z0 = h * zf
        ra = rad * 0.7
        out = rad + ra * 1.6
        elbow = [(rad * 0.6 * math.cos(ang), rad * 0.6 * math.sin(ang), z0),
                 (out * 0.75 * math.cos(ang), out * 0.75 * math.sin(ang), z0 + ra * 0.2),
                 (out * math.cos(ang), out * math.sin(ang), z0 + ra * 1.1)]
        m.add("verde_cardon", *tube(elbow, ra, 14))
        column(out * math.cos(ang), out * math.sin(ang), z0 + ra * 0.9, h * (0.55 - 0.1 * zf), ra, ang)
    V, F = ellipsoid(rad * 0.35, rad * 0.35, rad * 0.3, 10, 6)   # flor blanca en la punta
    m.add("flor_blanca", *_clean(_rot(V, t=(rad * 0.3, 0, h + rad * 0.75)), F))


GENERADORES = {
    "echeveria": p_echeveria, "haworthia": p_haworthia, "aloe": p_aloe,
    "sansevieria": p_sansevieria, "cereus": p_cereus, "mammillaria": p_mammillaria,
    "opuntia": p_opuntia, "crassula": p_crassula, "senecio": p_senecio, "pothos": p_pothos,
    "lithops": p_lithops,
    "ceibo": p_ceibo, "jacaranda": p_jacaranda, "ombu": p_ombu, "yerba_mate": p_yerba_mate,
    "cortadera": p_cortadera, "lapacho": p_lapacho, "espinillo": p_espinillo, "cardon": p_cardon,
    "arrayan": p_arrayan,
}

# qué tanto se mueve con el viento (0 rígida .. 1 muy flexible)
FLEX = {"cereus": 0.12, "mammillaria": 0.05, "opuntia": 0.1, "cardon": 0.08, "lithops": 0.0,
        "haworthia": 0.25, "echeveria": 0.3, "aloe": 0.35, "sansevieria": 0.35, "crassula": 0.45,
        "ombu": 0.5, "arrayan": 0.6, "ceibo": 0.7, "lapacho": 0.7, "jacaranda": 0.8,
        "espinillo": 0.7, "yerba_mate": 0.8, "senecio": 1.0, "pothos": 1.0, "cortadera": 1.0}


def layout(n, r_in):
    """Posiciones (x, y, R) para n plantas dentro de la boca de radio r_in."""
    if n <= 1:
        return [(0.0, 0.0, 0.92 * r_in)]
    if n == 2:
        return [(-0.48 * r_in, 0.0, 0.46 * r_in), (0.48 * r_in, 0.0, 0.46 * r_in)]
    k = 0.52 if n == 3 else 0.56
    Rk = 0.44 if n == 3 else 0.38
    a0 = math.pi / 2 if n == 3 else math.pi / 4
    return [(k * r_in * math.cos(a0 + TAU * i / n), k * r_in * math.sin(a0 + TAU * i / n),
             Rk * r_in) for i in range(n)]


def limpiar_ids(ids):
    """Sin repetidas, sólo conocidas, una por grupo (la última elegida gana) y hasta 4."""
    out, grupos = [], {}
    for i in dict.fromkeys(ids or []):
        if i not in GENERADORES:
            continue
        g = ficha(i).get("grupo", i)
        if g in grupos:
            out.remove(grupos[g])
        grupos[g] = i
        out.append(i)
    return out[:MAX_PLANTAS]


def build_por_planta(ids, abertura, seed=3):
    """Cada planta por separado: [{"id", "base": (x, y, z), "flex", "items": [(mat, V, F)]}].
    base es el punto de la tierra donde nace (pivote para animarla en la web)."""
    ids = [i for i in dict.fromkeys(ids) if i in GENERADORES][:MAX_PLANTAS]
    out = []
    for k, ((x, y, R), pid) in enumerate(zip(layout(len(ids), abertura["r_in"]), ids)):
        rnd = random.Random(seed * 101 + k * 7 + sum(map(ord, pid)))
        sub = Mesh()
        GENERADORES[pid](sub, R, dict(abertura), rnd)
        if ficha(pid).get("colgante"):          # las colgantes ya vienen en coordenadas de la boca
            x, y = x * 0.3, y * 0.3
        z = abertura["z_s"]
        items = [(mat, [(vx + x, vy + y, vz + z) for vx, vy, vz in V], F) for mat, V, F in sub.items()]
        out.append({"id": pid, "base": (x, y, z), "flex": FLEX.get(pid, 0.5), "items": items})
    return out


def build(ids, abertura, seed=3):
    """Plantas elegidas, ubicadas en la boca. -> [(material, V, F)]."""
    m = Mesh()
    for p in build_por_planta(ids, abertura, seed):
        for mat, V, F in p["items"]:
            m.add(mat, V, F)
    return m.items()


def abertura_de(V):
    """Boca de la maceta (ya ubicada) a partir de sus vértices."""
    import eden_escena
    z_top, r_in, z_s = eden_escena.opening(V)
    return {"r_in": r_in - 0.6, "z_s": z_s, "z_top": z_top,
            "r_out": max(math.hypot(x, y) for x, y, _ in V),
            "z_bot": min(v[2] for v in V)}


def cobertura_sugerida(ids):
    """Cobertura que mejor acompaña el riego de las plantas elegidas."""
    ids = [i for i in ids if i in GENERADORES]
    if not ids:
        return "piedra_blanca"
    orden = ["seco", "medio", "humedo"]
    rs = sorted(orden.index(ficha(i)["grupo_riego"]) for i in ids)
    return COBERTURA_SUGERIDA[orden[rs[0]]]        # manda la más sensible al exceso de agua


def _granos(r_in, z_s, avoid, seed, size, kinds, shape, gap=0.78, nu=14, nv=8, sink=0.55):
    """Granos sueltos sobre la tierra (Poisson simple). kinds: [(material, prob)];
    shape(rnd, size) -> (a, b, c)."""
    import eden_escena
    rnd = random.Random(seed)
    placed = []
    out = {k: ([], []) for k, _ in kinds}
    for _ in range(9000):
        rr = r_in * math.sqrt(rnd.random())
        th = rnd.uniform(0, TAU)
        sz = rnd.uniform(*size) * (0.8 if r_in < 30 else 1.0)
        a, b, c = shape(rnd, sz)
        if rr + max(a, b) * 1.45 > r_in - 0.5:          # 1.45: abolladuras del grano
            continue
        x, y = rr * math.cos(th), rr * math.sin(th)
        if any(math.hypot(x - ax, y - ay) < ar + a * 1.2 for ax, ay, ar in avoid):
            continue
        if any(math.hypot(x - px, y - py) < (sz + ps) * gap for px, py, ps in placed):
            continue
        placed.append((x, y, sz))
        u, acc, kind = rnd.random(), 0.0, kinds[-1][0]
        for k, pr in kinds:
            acc += pr
            if u < acc:
                kind = k
                break
        pv, pf = eden_escena._pebble(x, y, z_s + c * sink, a, b, c, rnd.uniform(0, TAU), rnd, nu, nv)
        V, F = out[kind]
        o = len(V)
        V += pv
        F += [(p + o, q + o, r + o) for p, q, r in pf]
    return [(k, V, F) for k, (V, F) in out.items() if F]


def decor(abertura, ids, seed=7, cobertura=None):
    """Tierra y cobertura alrededor de las plantas. -> [(material, V, F)].
    cobertura: una de COBERTURAS (None = la sugerida para esas plantas)."""
    import eden_escena
    r_in, z_s = abertura["r_in"], abertura["z_s"]
    ids = [i for i in dict.fromkeys(ids) if i in GENERADORES][:MAX_PLANTAS]
    cob = cobertura if cobertura in COBERTURAS else cobertura_sugerida(ids)
    out = [("tierra_oscura" if cob in ("tierra", "musgo") else "tierra",) + eden_escena.soil(r_in, z_s)]
    avoid = [(x, y, R * (0.45 if ficha(pid).get("colgante") else 0.55))
             for (x, y, R), pid in zip(layout(len(ids), r_in), ids)]
    if cob == "piedra_blanca":
        pb = eden_escena.pebbles(r_in, z_s, seed=seed, avoid=avoid)
        out += [(k,) + pb[k] for k in ("piedra", "arcilla") if pb[k][0]]
    elif cob == "tierra":                      # grumos chicos de la misma tierra
        out += _granos(r_in, z_s, [(x, y, R * 0.4) for x, y, R in avoid], seed, (0.9, 1.8),
                       [("tierra_oscura", 0.7), ("tierra", 0.3)],
                       lambda rnd, s: (s, s * rnd.uniform(0.7, 1.0), s * 0.45), gap=1.1, nu=8, nv=5, sink=0.3)
    elif cob == "leca":
        out += _granos(r_in, z_s, avoid, seed, (2.6, 3.8), [("leca", 1.0)],
                       lambda rnd, s: (s, s * rnd.uniform(0.9, 1.0), s * rnd.uniform(0.85, 0.95)), gap=0.95)
    elif cob == "corteza":
        out += _granos(r_in, z_s, avoid, seed, (3.5, 6.0), [("corteza_pino", 1.0)],
                       lambda rnd, s: (s, s * rnd.uniform(0.5, 0.75), s * 0.22), gap=0.72, sink=0.2)
    elif cob == "volcanica":
        out += _granos(r_in, z_s, avoid, seed, (1.8, 3.2), [("volcanica", 0.65), ("volcanica_negra", 0.35)],
                       lambda rnd, s: (s, s * rnd.uniform(0.6, 0.9), s * rnd.uniform(0.5, 0.75)), gap=0.8, nu=9, nv=6)
    elif cob == "musgo":                       # almohadones bajos y abollados
        out += _granos(r_in, z_s, [(x, y, R * 0.35) for x, y, R in avoid], seed, (3.5, 6.0), [("musgo", 1.0)],
                       lambda rnd, s: (s, s * rnd.uniform(0.8, 1.0), s * 0.38), gap=0.62, sink=0.15)
    return out
