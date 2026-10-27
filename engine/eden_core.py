# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Motor paramétrico de macetas (núcleo)
==============================================

OBJETIVO
    Generar macetas imprimibles en FDM como mallas cerradas (watertight) a
    partir de un diccionario de parámetros. Es el núcleo común a todas las
    familias "de revolución deformada" (Wave, Spiral, Twist, Origami
    facetada, Elegance, Tulip de borde ondulado...).

POR QUÉ PYTHON PURO
    No usa numpy ni Rhino. El MISMO archivo funciona:
      * dentro de Rhino 8 / Grasshopper (componente "Python 3 Script"),
      * en CPython normal (Windows/Mac/Linux) para lotes y exportación
        automática sin abrir Rhino.

ARQUITECTURA (módulos del motor)
    M1 forma base ......... profile_radius(), shape_factor()
    M2 deformación ........ deformation()   (ondas radiales, helicoidales,
                                             verticales, interferencia,
                                             asimetría, torsión progresiva)
    M3 patrón superficial . (en esta versión: ondas/facetas; perforaciones,
                             escamas y Voronoi van como generadores aparte)
    M4 construcción física  build_pot()     (pared interior por offset,
                                             fondo, drenaje, borde, chaflán)
    M5 exportación ........ write_stl(), write_3mf(), save_params()
    Validación ............ validate_*()   (errores bloquean, avisos informan)

ENTRADAS   dict de parámetros (ver DEFAULTS). Unidades: milímetros.
SALIDAS    dict {"vertices", "faces", "report", "params"}
"""

from __future__ import division
import math
import json
import struct
import zipfile
import copy
import os

ENGINE_VERSION = "0.4.0"
DEBUG = None   # dict para inspeccionar funciones internas en pruebas
TAU = 2.0 * math.pi
PLA_DENSITY = 1.24  # g/cm3

# ---------------------------------------------------------------------------
# PARÁMETROS POR DEFECTO  (EDEN-Wave M base)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "model_id": "EDEN-Wave-M-00",
    "family": "wave",
    # --- M1 forma base -----------------------------------------------------
    "height": 110.0,       # altura total (incluye el borde)
    "d_base": 84.0,        # diámetro del perfil en la base
    "d_max": 120.0,        # diámetro máximo del perfil (sin ondas)
    "d_mouth": 114.0,      # diámetro del perfil en la boca
    "belly": 0.68,         # posición relativa (0-1) del diámetro máximo
    "polygon_sides": 0,    # 0 = circular; N = sección poligonal
    "polygon_blend": 0.0,  # 0 círculo ... 1 polígono puro
    "polygon_twist": 0.0,  # vueltas de giro del polígono en toda la altura
    "polygon_round": 0.12, # radio de esquina (fracción del radio)
    # --- M2 deformación ----------------------------------------------------
    "waves": [
        {"type": "radial", "count": 12, "amp": 3.0, "phase": 0.0,
         "twist": 0.0, "twist_power": 1.0, "sharp": 1.0,
         "amp_top": 1.0, "amp_power": 1.0},
    ],
    "asym": 0.0,           # 0..0.9 modula la amplitud alrededor
    "asym_angle": 0.0,     # grados
    "fade_bottom": 8.0,    # mm en que las ondas nacen desde la base
    "fade_top": 8.0,       # mm en que las ondas mueren antes del borde
    # --- M4 construcción física -------------------------------------------
    "wall": 1.6,           # espesor de pared (normal a la superficie)
    "floor": 2.4,          # espesor de fondo
    "rim": "round",        # "round" | "flat"
    "chamfer": 0.6,        # chaflán anti "pata de elefante"
    "drain_d": 7.0,        # diámetro de cada agujero / ancho de ranura (0 = sin)
    "drain_pattern": "ring",   # "none" | "single" | "ring" | "grid"
    "drain_shape": "circle",   # "circle" | "slot" (ranura radial) | "leaf" (hoja)
    "drain_count": 6,      # agujeros del primer anillo
    "drain_rings": 1,      # anillos concéntricos (1-3)
    "drain_center": True,  # agujero central además del anillo
    "drain_spacing": 0.0,  # paso de la grilla (0 = 3 × drain_d)
    "drain_slot_len": 0.0, # largo de ranura u hoja (0 = 3 × drain_d)
    "drain_leaf_vein": 2.0,  # nervadura central de la hoja, mm (0 = hoja entera)
    "drain_leaf_tilt": 0.0,  # giro de las hojas, grados (efecto molinete)
    # --- perfil de onda (se aplica a las ondas que no traen "profile") ------
    "wave_profile": "",    # "" = senoidal | "rib" (acanalado convexo Japandi)
                           # | "flute" (canales cóncavos)
    "wave_duty": 0.92,     # fracción del período ocupada por la nervadura/canal
    # --- superficie visible (eden_surface) ---------------------------------
    "lowpoly_cols": 0,     # facetas alrededor (0 = desactivado)
    "lowpoly_rows": 6,     # bandas de facetas en altura
    "lowpoly_stagger": True,
    "lowpoly_jitter": 0.0, # desorden de vértices, mm
    "lowpoly_seed": 1,
    "tex_type": "none",    # "none" | "rope" | "knit" | "stone" | "bubbles"
    "tex_amp": 1.2,        # profundidad del relieve, mm (siempre hacia afuera)
    "tex_count": 24,       # repeticiones alrededor
    "tex_pitch": 8.0,      # paso vertical, mm
    "tex_scale": 10.0,     # grano de la piedra, mm
    "tex_seed": 7,
    "tex_duty": 0.3,       # costillas: ancho de la costilla (fracción del período)
    "tex_wob": 0.3,        # costillas onduladas/arcos: ondulación (en períodos)
    # --- sistema de piezas --------------------------------------------------
    "mode": "pot",         # "pot" | "hidden_tray" (plato oculto a presión)
                           # | "screw_tray" (plato enroscable) | "self_watering"
    "tray_h": 0.0,         # altura del plato oculto (0 = auto)
    "tray_wall": 2.4,      # pared del plato oculto
    "tray_floor": 1.6,
    "tray_clear": 0.4,     # holgura radial maceta-plato
    "tray_reservoir": 6.0, # luz entre fondo del plato y fondo de la maceta
    "thread_pitch": 4.0,   # plato enroscable: paso de rosca, mm
    "thread_depth": 1.0,   # profundidad de rosca, mm (flancos <= 45°)
    "thread_clear": 0.5,   # holgura radial entre roscas, mm
    "thread_turns": 3.0,   # vueltas de rosca
    "dish_gap": 4.0,       # plato inclinado: luz radial entre maceta y plato, mm
    "dish_tilt": 12.0,     # plato inclinado: inclinación del borde, grados
    "dish_low": 0.0,       # altura del borde bajo (0 = auto)
    "dish_reservoir": 0.0, # luz de agua bajo la maceta (0 = auto: 2 mm; el agua pasa
                           # por debajo y entra por los agujeros de drenaje)
    "dish_turns": 4.0,     # vueltas de rosca del perno central (se ajusta a la altura)
    "dish_water": 0.0,     # autorriego: profundidad de agua sobre la base de la
                           # maceta con el plato lleno (0 = auto: 12 mm o 14 % de H)
    "dish_channels": 6,    # canales de agua a través del asiento y la rosca
    "sw_reservoir": 0.0,   # altura del depósito de agua (0 = auto)
    "sw_gap": 1.2,         # holgura entre inserto y cubremaceta
    "sw_wick_d": 12.0,     # agujero central para la mecha
    # --- calidad de malla --------------------------------------------------
    "brand": "Eden3D",     # marca grabada en la base de cada pieza ("" = sin marca)
    "brand_size": 6.0,     # altura de mayúscula, mm (se achica sola si no entra)
    "brand_depth": 0.6,    # profundidad del grabado, mm (3 capas de 0,2)
    "quality": "normal",   # "preview" | "normal" | "fine"
}

QUALITY = {
    # (muestras por onda, mínimo de muestras angulares, paso vertical mm)
    "preview": (10, 96, 3.0),
    "normal": (24, 240, 1.0),
    "fine": (36, 360, 0.5),
}

# Límites de fabricación FDM (PLA, boquilla 0,4)
LIMITS = {
    "wall_min": 0.8,          # 2 perímetros
    "floor_min": 0.8,
    "overhang_deg": 45.0,
    "drain_margin": 3.0,      # mm entre agujero y pared interior
    "drain_gap": 1.6,         # mm mínimos entre agujeros
    "stability_ratio": 0.45,  # d_base / altura mínimo recomendado
}


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
def merge_params(user=None):
    """Combina DEFAULTS con los parámetros del usuario (copia profunda)."""
    p = copy.deepcopy(DEFAULTS)
    if user:
        for k, v in user.items():
            p[k] = copy.deepcopy(v)
    # completar campos faltantes de cada onda
    base_wave = {"type": "radial", "count": 0, "amp": 0.0, "phase": 0.0,
                 "twist": 0.0, "twist_power": 1.0, "sharp": 1.0,
                 "amp_top": 1.0, "amp_power": 1.0, "n_theta": 0}
    full = []
    for w in p.get("waves", []) or []:
        ww = dict(base_wave)
        ww.update(w)
        full.append(ww)
    p["waves"] = full
    return p


def smoothstep(x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * (3.0 - 2.0 * x)


def hermite(p0, p1, m0, m1, s):
    s2 = s * s
    s3 = s2 * s
    return ((2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0
            + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1)


# ---------------------------------------------------------------------------
# M1 — FORMA BASE
# ---------------------------------------------------------------------------
def profile_radius(p, t):
    """Radio del perfil de revolución para t = z/H en [0,1].
    Dos tramos Hermite con tangente horizontal en el vientre (belly):
    perfil suave, sin puntos de inflexión bruscos."""
    rb, rmax, rm = p["d_base"] / 2.0, p["d_max"] / 2.0, p["d_mouth"] / 2.0
    b = min(max(p["belly"], 0.0), 1.0)
    if b <= 1e-3:          # el máximo está en la base
        return hermite(rmax, rm, 0.0, 1.5 * (rm - rmax), t)
    if b >= 1.0 - 1e-3:    # el máximo está en la boca (cono / tulipa)
        return hermite(rb, rmax, 1.5 * (rmax - rb), 0.0, t)
    if t <= b:
        s = t / b
        return hermite(rb, rmax, 1.5 * (rmax - rb), 0.0, s)
    s = (t - b) / (1.0 - b)
    return hermite(rmax, rm, 0.0, 1.5 * (rm - rmax), s)


def shape_factor(p, theta, t):
    """Factor de sección (1 = círculo). Mezcla círculo / polígono de esquinas
    redondeadas, girable con la altura. Las esquinas vivas generarían una
    arista que la pared interior no puede copiar con espesor constante, por
    eso el polígono siempre tiene radio de esquina (polygon_round, fracción
    del radio)."""
    n = int(p.get("polygon_sides", 0) or 0)
    blend = float(p.get("polygon_blend", 0.0) or 0.0)
    if n < 3 or blend <= 0.0:
        return 1.0
    rc = min(max(float(p.get("polygon_round", 0.12)), 0.01), 0.9)
    th = theta - TAU * p.get("polygon_twist", 0.0) * t
    sector = TAU / n
    phi = abs((th % sector) - sector / 2.0)          # 0 = centro de la cara
    half = math.pi / n
    apo = math.cos(half)                              # apotema (circunradio 1)
    # polígono interior (apotema apo-rc) + círculo rc  = polígono redondeado
    a_in = apo - rc
    if a_in * math.tan(phi) <= a_in * math.tan(half) and math.tan(phi) * apo <= a_in * math.tan(half):
        poly = apo / math.cos(phi)
    else:
        cdist = a_in / math.cos(half)                 # centro del arco de esquina
        ux, uy = math.cos(phi), math.sin(phi)
        cx, cy = cdist * math.cos(half), cdist * math.sin(half)
        b = ux * cx + uy * cy
        poly = b + math.sqrt(max(b * b - cdist * cdist + rc * rc, 0.0))
    return (1.0 - blend) + blend * poly


# ---------------------------------------------------------------------------
# M2 — DEFORMACIÓN
# ---------------------------------------------------------------------------
def deformation(p, theta, z, H):
    """Desplazamiento radial (mm) en (theta, z)."""
    t = z / H
    env = smoothstep(z / max(p["fade_bottom"], 1e-6)) * \
        smoothstep((H - z) / max(p["fade_top"], 1e-6))
    if env == 0.0:
        return 0.0
    off = 0.0
    for w in p["waves"]:
        amp = w["amp"]
        if amp == 0.0:
            continue
        gain = 1.0 + (w["amp_top"] - 1.0) * (t ** w["amp_power"])
        prof = w.get("profile") or p.get("wave_profile") or ""
        duty = float(w.get("duty", p.get("wave_duty", 0.92)))
        if w["type"] == "radial":
            ang = w["count"] * (theta + TAU * w["twist"] * (t ** w["twist_power"])) \
                + math.radians(w["phase"])
            c = _profile_wave(ang, prof, duty) if prof else _shape_wave(math.cos(ang), w["sharp"])
            off += amp * gain * c
        elif w["type"] == "vertical":
            ang = TAU * w["count"] * t + math.radians(w["phase"])
            c = _profile_wave(ang, prof, duty) if prof else math.cos(ang)
            if w.get("n_theta", 0):
                c *= math.cos(w["n_theta"] * theta)
            off += amp * gain * c
        else:
            raise ValueError("Tipo de onda desconocido: %s" % w["type"])
    if p.get("asym", 0.0):
        off *= 1.0 + p["asym"] * math.cos(theta - math.radians(p.get("asym_angle", 0.0)))
    return off * env


def _profile_wave(ang, prof, duty):
    """Perfiles de nervadura en [-1, 1] para un ángulo de fase `ang`.
    rib   : nervaduras convexas redondeadas separadas por un surco en V
            (look Japandi / "ribbed"). El surco es cóncavo: no pliega la pared.
    flute : canales cóncavos con lomos suaves.
    Ambos tienen pendiente finita en los bordes: con pendiente infinita la
    curvatura se dispara al afinar la malla y la pared interior se pliega.
    duty  : fracción del período que ocupa la nervadura o el canal."""
    u = ((ang / math.pi + 1.0) % 2.0) - 1.0        # -1 … 1, cresta en 0
    d = min(max(duty, 0.3), 1.0)
    q = u / d
    if prof == "rib":
        # arco coseno: lomo redondeado, flancos de pendiente FINITA que se
        # encuentran en un surco en V (cóncavo, no pliega la pared interior)
        return 2.0 * math.cos(0.5 * math.pi * q) - 1.0 if abs(q) < 1 else -1.0
    if prof == "flute":
        # canal de coseno elevado: transición suave al lomo (curvatura acotada)
        return 1.0 - (1.0 + math.cos(math.pi * q)) if abs(q) < 1 else 1.0
    raise ValueError("wave profile desconocido: %s (usar rib o flute)" % prof)


def _shape_wave(c, sharp):
    """Perfil de la onda. sharp = 1 senoidal; > 1 crestas y valles angostos
    con flancos planos; < 1 onda "cuadrada" suave (tanh), sin cúspides,
    para que la curvatura quede acotada y la pared interior no se pliegue."""
    if sharp == 1.0:
        return c
    if sharp > 1.0:
        return math.copysign(abs(c) ** sharp, c)
    k = 3.0 * (1.0 / max(sharp, 0.05) - 1.0)
    return math.tanh(k * c) / math.tanh(k)


def outer_radius(p, theta, z, H_body):
    """Superficie BASE lisa (perfil × sección + ondas). Sin low poly ni textura."""
    t = min(max(z / H_body, 0.0), 1.0)
    return profile_radius(p, t) * shape_factor(p, theta, t) + deformation(p, theta, z, H_body)


def _smin(a, b, k):
    """Mínimo suave (redondea la esquina con radio ~k)."""
    if k <= 0:
        return min(a, b)
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k / 4.0


def _fresh(name):
    """Módulo hermano, recargado sólo si su archivo cambió (Rhino guarda los
    módulos en memoria; recargar siempre borraba las cachés y costaba ~1 s)."""
    import importlib
    import os
    import sys
    mod = sys.modules.get(name) or importlib.import_module(name)
    try:
        mt = os.path.getmtime(mod.__file__)
    except Exception:
        mt = None
    if getattr(mod, "_eden_mtime", "nunca") not in ("nunca", mt):
        mod = importlib.reload(mod)
    mod._eden_mtime = mt
    return mod


def _load_surface_module():
    return _fresh("eden_surface")


def make_surface(p):
    """Devuelve las funciones de superficie del diseño completo (coordenadas de
    la maceta armada, z desde la base):
        rb(θ, z)  superficie base lisa  -> de acá sale la pared interior
        ro(θ, z)  superficie visible    -> base + low poly + textura
        inset     cuánto puede quedar ro por DEBAJO de rb (facetas = cuerdas);
                  la pared interior se retira esa distancia extra
        Hp        altura de referencia del perfil"""
    es = _load_surface_module()
    Hp = float(p["height"]) - (float(p["wall"]) / 2.0 if p["rim"] == "round" else 0.0)

    _rbm = {}

    def rb(th, z):                       # memo: la malla vuelve a pedir los mismos puntos
        k = (th, z)
        v = _rbm.get(k)
        if v is None:
            v = _rbm[k] = outer_radius(p, th, z, Hp)
        return v

    lp = es.LowPoly(p, rb, Hp) if int(p.get("lowpoly_cols", 0) or 0) >= 3 else None
    tex = es.Texture(p, float(p["d_max"]) / 2.0)

    def env(z):
        return smoothstep(z / max(p["fade_bottom"], 1e-6)) * \
            smoothstep((Hp - z) / max(p["fade_top"], 1e-6))

    _rom = {}

    def ro(th, z):
        k = (th, z)
        r = _rom.get(k)
        if r is not None:
            return r
        r = lp.radius(th, z) if lp else rb(th, z)
        if tex.active:
            e = env(z)
            if e > 0:
                r += tex.amp * e * tex.height(th, z)
        _rom[k] = r
        return r

    inset = 0.0
    if lp:
        for i in range(61):
            z = Hp * i / 60.0
            for k in range(240):
                th = TAU * k / 240.0
                inset = max(inset, rb(th, z) - ro(th, z))
        inset += 0.05
    return {"rb": rb, "ro": ro, "inset": inset, "Hp": Hp, "lowpoly": lp, "tex": tex}


# ---------------------------------------------------------------------------
# RESOLUCIÓN
# ---------------------------------------------------------------------------
def resolution(p, surf=None):
    per_wave, min_n, dz = QUALITY.get(p.get("quality", "normal"), QUALITY["normal"])
    maxc = 0
    for w in p["waves"]:
        if w["amp"] != 0:
            c = w["count"] if w["type"] == "radial" else w.get("n_theta", 0)
            maxc = max(maxc, int(c))
    n = max(min_n, per_wave * maxc)
    if surf is not None:
        tn, tdz = surf["tex"].resolution()
        fac = {"preview": 0.5, "normal": 1.0, "fine": 1.4}.get(p.get("quality"), 1.0)
        n = max(n, int(tn * fac))
        dz = min(dz, max(tdz / fac, 0.35))
        if surf["lowpoly"] is not None:
            cols = surf["lowpoly"].cols
            n = max(n, cols * 16)
    n = min(n, 1440)
    sides = int(p.get("polygon_sides", 0) or 0)
    if sides >= 3 and p.get("polygon_blend", 0) > 0:
        n = int(math.ceil(n / float(sides)) * sides)   # vértices en las aristas
    if maxc:
        n = int(math.ceil(n / float(maxc)) * maxc)
    return n, dz


# ---------------------------------------------------------------------------
# M4 — CONSTRUCCIÓN FÍSICA
# ---------------------------------------------------------------------------
def _build_piece(p, rb, ro, z0, z1, wall, floor_t, rim, chamfer, inset, n, dz,
                 report, wall_extra=None, drain=None, inner_fn=None, fine=None,
                 top_fn=None, brand=None, feature=None):
    """Construye UNA pieza sólida y cerrada entre las alturas z0 y z1 (en
    coordenadas de la maceta armada). La pieza se devuelve con su base en z=0.
        rb/ro       superficie base y visible: f(θ, z_armado)
        wall        espesor nominal; la pared interior sale de rb desplazada
                    (wall + inset + wall_extra(z)) por la normal 3D real
        drain       dict de parámetros de drenaje (None = fondo cerrado)
        inner_fn    f(θ, z_armado, w) -> radio interior exacto (low poly) o None
                    para usar el desplazamiento por la normal de rb
        top_fn      (z_keep, f(θ)) borde superior INCLINADO: arriba de z_keep
                    (armado) cada columna termina en f(θ) en vez de z1; las
                    superficies se evalúan en la altura real (corte exacto)
        brand       dict de marca grabada en la cara de apoyo (o None)
        feature     superficies extra centradas en el fondo (rosca central):
                    {"top"|"bottom": {"rings": [...], "apex": (x,y,z)|None}}"""
    rim_round = rim == "round"
    H_loc = z1 - z0
    Hb = H_loc - (wall / 2.0 if rim_round else 0.0)
    thetas = [TAU * k / n for k in range(n)]
    ch = min(float(chamfer or 0.0), floor_t * 0.8)
    nz = max(8, int(math.ceil((Hb - floor_t) / dz)))
    zs = [0.0] + ([ch] if ch > 0 else []) + \
         [floor_t + (Hb - floor_t) * i / nz for i in range(nz + 1)]
    i_floor = 2 if ch > 0 else 1
    if fine:                                       # franja con filas finas (roscas)
        fz0, fz1, fdz = fine
        k_ = 0
        extra = []
        while True:
            zf = fz0 - z0 + k_ * fdz
            if zf > fz1 - z0:
                break
            if floor_t + 0.05 < zf < Hb - 0.05:
                extra.append(zf)
            k_ += 1
        head = zs[:i_floor + 1]
        body = sorted(set([round(z, 6) for z in zs[i_floor + 1:] + extra]))
        body = [z for z in body if z > floor_t + 0.02]
        zs = head + body
        if abs(zs[-1] - Hb) > 1e-6:
            zs.append(Hb)
    if top_fn is not None:                         # borde inclinado: alturas por columna
        zk = top_fn[0] - z0
        tops = [min(top_fn[1](th) - z0, Hb) for th in thetas]
        if min(tops) < zk + 1.0 or zk < floor_t + 0.5:
            report["errors"].append("Borde inclinado demasiado bajo para la pieza")
            return None
        ZC = [[z if z <= zk else zk + (z - zk) * (tops[k] - zk) / max(Hb - zk, 1e-9)
               for k in range(n)] for z in zs]
    else:
        ZC = [[z] * n for z in zs]
    Rb = [[rb(th, ZC[i][k] + z0) for k, th in enumerate(thetas)] for i in range(len(zs))]
    Ro = [[ro(th, ZC[i][k] + z0) for k, th in enumerate(thetas)] for i in range(len(zs))]
    if ch > 0:
        Ro[0] = [r - ch for r in Ro[0]]

    inner_rings, curv_min, fold_where = [], float("inf"), None
    ratio_min = float("inf")
    h = TAU / n
    last = len(zs) - 1
    off_max = 0.0
    for i in range(i_floor, len(zs)):
        im, ip = max(i - 1, i_floor), min(i + 1, last)
        w_here = wall + inset + (wall_extra(zs[i] + z0) if wall_extra else 0.0)
        off_max = max(off_max, w_here)
        ring = []
        for k in range(n):
            zik = ZC[i][k]
            dz_c = max(ZC[ip][k] - ZC[im][k], 1e-9)
            if inner_fn is not None:
                w_lp = wall + (wall_extra(zik + z0) if wall_extra else 0.0)
                r_in = inner_fn(thetas[k], zik + z0, w_lp)
                if r_in is not None:
                    zz = floor_t if i == i_floor else zik
                    ring.append((r_in * math.cos(thetas[k]), r_in * math.sin(thetas[k]), zz))
                    continue
            kp, km = (k + 1) % n, (k - 1) % n
            r = Rb[i][k]
            r_t = (Rb[i][kp] - Rb[i][km]) / (2 * h)
            r_tt = (Rb[i][kp] - 2 * r + Rb[i][km]) / (h * h)
            r_z = (Rb[ip][k] - Rb[im][k]) / dz_c
            if im < i < ip:
                # derivadas con espaciado DESPAREJO (filas finas de roscas)
                h1, h2 = max(zik - ZC[im][k], 1e-9), max(ZC[ip][k] - zik, 1e-9)
                r_zz = 2.0 * ((Rb[ip][k] - r) / h2 - (r - Rb[im][k]) / h1) / (h1 + h2)
                r_tz = (Rb[ip][kp] - Rb[ip][km] - Rb[im][kp] + Rb[im][km]) / (2 * h * dz_c)
            else:
                r_zz = r_tz = 0.0
            (n_r, n_t, n_z), k_convex = _local_normal_curvature(r, r_t, r_tt, r_z, r_zz, r_tz)
            if k_convex > 0 and im < i < ip:
                rho = 1.0 / k_convex
                ratio = rho / w_here               # pliegue si la cresta < 1,25 × espesor local
                if ratio < ratio_min:
                    ratio_min, curv_min, fold_where = ratio, rho, (round(zik + z0, 1), k)
            th = thetas[k]
            ct, st = math.cos(th), math.sin(th)
            x = r * ct - w_here * (n_r * ct - n_t * st)
            y = r * st - w_here * (n_r * st + n_t * ct)
            z = zik - w_here * n_z
            if i == i_floor:
                z = floor_t
            elif i == last:
                z = zik
            ring.append((x, y, z))
        inner_rings.append(ring)

    if ratio_min < 1.25:
        zf = fold_where[0]
        hint = "Reducí amplitud/cantidad de ondas o el espesor."
        if zf < float(p.get("fade_bottom", 0)) + 2 or zf > float(p["height"]) - float(p.get("fade_top", 0)) - 2:
            hint = ("El pliegue está donde nacen/terminan las ondas: subí fade_bottom/fade_top "
                    "(12 mm suele alcanzar) o bajá la amplitud.")
        report["errors"].append(
            "Pliegue de pared interior: cresta con radio %.2f mm < 1.25×espesor en z=%s. %s"
            % (curv_min, zf, hint))
    elif p.get("quality") == "preview" and ratio_min < 1.25 * 1.35:
        report["warnings"].append(
            "Vista previa al límite (cresta %.2f mm): al exportar en calidad normal el "
            "chequeo de pliegue puede rechazarla. Probá con un poco menos de amplitud."
            % curv_min)
    for ring in inner_rings:
        prev = None
        bad = False
        for (x, y, z) in ring + ring[:1]:
            a = math.atan2(y, x)
            if prev is not None and (a - prev) % TAU > math.pi:
                report["errors"].append("Anillo interior autointersectado en z=%.1f" % (z + z0))
                bad = True
                break
            prev = a
        if bad:
            break
    if report["errors"]:
        return None

    V, F = [], []

    def add_ring(pts):
        start = len(V)
        V.extend(pts)
        return list(range(start, start + len(pts)))

    path = []
    for i, z in enumerate(zs):
        path.append(add_ring([(Ro[i][k] * math.cos(thetas[k]),
                               Ro[i][k] * math.sin(thetas[k]), ZC[i][k]) for k in range(n)]))
    out_top = [V[j] for j in path[-1]]
    in_top = inner_rings[-1]
    if rim_round:
        segs = 8
        for s in range(1, segs):
            a = math.pi * s / segs
            ring = []
            for k in range(n):
                ox, oy, oz = out_top[k]
                ix, iy, iz = in_top[k]
                cx, cy, cz = (ox + ix) / 2, (oy + iy) / 2, (oz + iz) / 2
                half = math.hypot(ox - ix, oy - iy) / 2.0
                ring.append((cx + math.cos(a) * (ox - cx), cy + math.cos(a) * (oy - cy),
                             cz + math.sin(a) * half))
            path.append(add_ring(ring))
    for ring in reversed(inner_rings):
        path.append(add_ring(ring))
    for a_, b_ in zip(path[:-1], path[1:]):
        _strip(F, a_, b_, n)
    dp = dict(p)
    if drain is None:
        dp.update({"drain_pattern": "none", "drain_d": 0.0})
    else:
        dp.update(drain)
    info = _build_floor(dp, V, F, path[0], path[-1], floor_t, report, brand=brand,
                        feature=feature)
    if report["errors"]:
        return None
    return {"V": V, "F": F, "inner_rings": inner_rings, "Ro": Ro, "Rb": Rb, "zs": zs,
            "thetas": thetas, "curv_min": curv_min, "drain": info, "chamfer": ch,
            "floor_t": floor_t, "z0": z0, "wall_max": off_max}


def _finish(piece, report, name, stride=1):
    """Métricas comunes de una pieza."""
    V, F = piece["V"], piece["F"]
    vol = mesh_volume(V, F)
    report["triangles"] = len(F)
    report["vertices"] = len(V)
    report["volume_cm3"] = round(vol / 1000.0, 2)
    report["mass_g_PLA_100pct"] = round(vol / 1000.0 * PLA_DENSITY, 1)
    xs = [v[0] for v in V]; ys = [v[1] for v in V]; zz = [v[2] for v in V]
    report["bbox_mm"] = [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2),
                         round(max(zz) - min(zz), 2)]
    report["min_convex_radius_mm"] = None if piece["curv_min"] == float("inf") \
        else round(piece["curv_min"], 2)
    report.update(piece["drain"] or {"drain_holes": 0})
    oh = overhang_stats(V, F, z_ignore=piece["chamfer"] + 1e-6, stride=stride)
    report.update(oh)
    if oh["overhang_max_deg"] > LIMITS["overhang_deg"] + 5 or oh["overhang_area_pct_over45"] > 0.5:
        report["warnings"].append(
            "%s: voladizo máx. %.0f° (%.1f%% del área > 45°). Revisar en el laminador." %
            (name, oh["overhang_max_deg"], oh["overhang_area_pct_over45"]))
    report["valid"] = not report["errors"]


def _brand(p):
    t = str(p.get("brand", "") or "").strip()
    if not t:
        return None
    return {"text": t, "size": float(p.get("brand_size", 6.0)),
            "depth": float(p.get("brand_depth", 0.6))}


def _ring_radii(ring):
    return [math.hypot(x, y) for x, y, _ in ring]


def water_mesh(res, level=None, n=96):
    """Volumen de agua del plato (para verlo en Grasshopper): tronco de cono que
    sigue la pared interior del plato desde el piso hasta `level` (z armado;
    None = plato lleno). La maceta lo tapa donde corresponde. -> (V, F)"""
    A = (res.get("report") or {}).get("assembly") or {}
    if "dish_inner_r0_mm" not in A:
        return [], []
    tf = float(A["dish_floor_mm"])
    z1 = float(level if level is not None else A["water_level_max_mm"])
    t = math.tan(math.radians(A.get("dish_flare_deg", 6.0)))
    r0 = A["dish_inner_r0_mm"] - 0.05
    r1 = r0 + (z1 - tf) * t
    V = [(0.0, 0.0, tf), (0.0, 0.0, z1)]
    for z, r in ((tf, r0), (z1, r1)):
        for k in range(n):
            a = TAU * k / n
            V.append((r * math.cos(a), r * math.sin(a), z))
    F = []
    for k in range(n):
        k1 = (k + 1) % n
        b0, b1, u0, u1 = 2 + k, 2 + k1, 2 + n + k, 2 + n + k1
        F += [(0, b1, b0), (1, u0, u1), (b0, b1, u1), (b0, u1, u0)]
    return V, F


def _STRIDE(p):
    """En vista previa el voladizo se estima con 1 de cada 4 triángulos."""
    return 4 if p.get("quality") == "preview" else 1


def _poly_area(pts):
    """Área de un polígono (shoelace), mm²."""
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def build_pot(user_params=None):
    """Construye el diseño. Devuelve la pieza principal (la maceta) y, según
    `mode`, piezas adicionales en result["parts"]:
        pot            maceta sola (como siempre)
        hidden_tray    maceta + plato oculto que continúa la forma exterior
        self_watering  cubremaceta-depósito + inserto con mecha"""
    p = merge_params(user_params)
    errors, warnings = validate_params(p)
    report = {"model_id": p["model_id"], "engine": ENGINE_VERSION,
              "errors": errors, "warnings": warnings}
    fail = {"vertices": [], "faces": [], "report": report, "params": p, "parts": []}
    if errors:
        report["valid"] = False
        return fail
    try:
        surf = make_surface(p)
    except ValueError as ex:
        report["errors"].append(str(ex))
        report["valid"] = False
        return fail
    rb, ro, inset, Hp = surf["rb"], surf["ro"], surf["inset"], surf["Hp"]
    H = float(p["height"])
    wall, floor_t = float(p["wall"]), float(p["floor"])
    n, dz = resolution(p, surf)
    report["visible_inset_mm"] = round(inset, 2)
    mode = str(p.get("mode", "pot") or "pot").strip().lower()
    drain = {}           # usa los parámetros de drenaje del diseño
    parts = []

    lp = surf["lowpoly"]
    lp_inner = (lambda th, z, w: lp.inner_radius(th, z, w)) if lp else None

    if mode == "pot":
        pc = _build_piece(p, rb, ro, 0.0, H, wall, floor_t, p["rim"], p["chamfer"],
                          inset, n, dz, report, drain=drain, inner_fn=lp_inner, brand=_brand(p))
        if pc is None:
            report["valid"] = False
            return fail
        _finish(pc, report, "Maceta", _STRIDE(p))
        report["soil_capacity_ml"] = round(cavity_volume(pc["inner_rings"], floor_t) / 1000.0, 0)
        report["footprint_max_r_mm"] = round(max(pc["Ro"][0]), 2)

    elif mode == "hidden_tray":
        # --- plato oculto -------------------------------------------------
        # El plato continúa la forma exterior (ondas, facetas, textura) pero su
        # interior es CIRCULAR, y la espiga de la maceta también: encastra con
        # cualquier diseño y en cualquier giro. Asiento cónico a 45° (imprime
        # sin soportes y centra solo). Entre fondos queda un depósito de agua.
        tw, tf = float(p["tray_wall"]), float(p["tray_floor"])
        cl, res_h = float(p["tray_clear"]), float(p["tray_reservoir"])
        h_t = float(p["tray_h"] or 0) or min(30.0, max(16.0, 0.2 * H))
        c_fl = max(0.6, tw - 1.0)                 # asiento a 45° en el borde del plato
        z_c = h_t - c_fl
        z_pb = tf + res_h                         # fondo de la maceta (armada)
        if z_c - z_pb < 4.0:
            report["errors"].append("Plato oculto muy bajo: subí tray_h o bajá tray_reservoir")
        if tw < 1.6:
            report["errors"].append("tray_wall mínimo 1,6 mm")
        if report["errors"]:
            report["valid"] = False
            return fail
        n_s = 360
        zt = [h_t * i / 40.0 for i in range(41)]
        tbl = []                                  # radio interior circular del plato
        for z in zt:
            rmin = min(rb(TAU * k / n_s, z) for k in range(n_s)) - inset
            dz_ = 0.5
            slope = abs(min(rb(0.0, z + dz_), rb(0.0, z)) - min(rb(0.0, max(z - dz_, 0)), rb(0.0, z))) / dz_
            tbl.append((z, rmin - tw * math.sqrt(1.0 + slope * slope)))

        def lerp_tbl(z):
            if z <= tbl[0][0]:
                return tbl[0][1]
            for (za, ra), (zb_, rb_) in zip(tbl, tbl[1:]):
                if za <= z <= zb_:
                    return ra + (rb_ - ra) * (z - za) / max(zb_ - za, 1e-9)
            return tbl[-1][1]

        def tray_inner(th, z, w):                 # interior del plato (circular + asiento)
            return lerp_tbl(min(z, z_c)) + max(0.0, z - z_c)

        # la maceta entra desde arriba: la espiga no puede ser más ancha que el
        # punto más angosto del plato por encima (mínimo acumulado hacia arriba)
        zs_run = [h_t * i / 80.0 for i in range(81) if h_t * i / 80.0 <= z_c] + [z_c]
        run_tbl, m_ = [], float("inf")
        for z in reversed(zs_run):
            m_ = min(m_, lerp_tbl(z))
            run_tbl.append((z, m_))
        run_tbl.reverse()

        def run_min(z):
            if z <= run_tbl[0][0]:
                return run_tbl[0][1]
            for (za, ra), (zb_, rb_) in zip(run_tbl, run_tbl[1:]):
                if za <= z <= zb_:
                    return ra + (rb_ - ra) * (z - za) / max(zb_ - za, 1e-9)
            return run_tbl[-1][1]

        def r_spigot(z):                          # espiga + cono de 45° de la maceta
            if z < z_c:
                return run_min(z) - cl
            return run_min(z_c) - cl + (z - z_c)

        k_r = 2.5 * wall

        def rb_pot(th, z):
            return _smin(rb(th, z), r_spigot(z), k_r)

        r_max_ht = max(rb(TAU * k / n_s, h_t) for k in range(n_s))
        z_rv = z_c + (r_max_ht - r_spigot(z_c)) + k_r     # arriba de esto, forma completa

        L_b = max(3.0, 2.0 * inset)               # transición suave liso -> visible (<45°)

        def blend_vis(z):
            return smoothstep((z - z_rv) / L_b)

        def ro_pot(th, z):
            b = rb_pot(th, z)
            return b + blend_vis(z) * (ro(th, z) - rb(th, z))

        def pot_inner(th, z, w):
            """Interior facetado exacto donde se ven las facetas; en la
            transición se mezcla con el interior liso en la misma proporción
            que la superficie exterior (espesor >= w en todo el tramo)."""
            if lp is None or z < z_rv:
                return None
            w = wall                              # espesor nominal (no el reducido de la zona lisa)
            bv = blend_vis(z)
            r_lp = lp.inner_radius(th, z, w)
            if r_lp is None:
                return None
            b, bp = rb(th, z), rb_pot(th, z)
            # misma mezcla que la cara exterior: ro_pot = (1-bv)·bp + bv·(ro - (b - bp))
            return (1.0 - bv) * (bp - 1.1 * w) + bv * (r_lp - (b - bp))

        def pot_extra(z):                         # margen de facetas sólo donde se ven
            return -inset * (1.0 - blend_vis(z))

        pc = _build_piece(p, rb_pot, ro_pot, z_pb, H, wall, floor_t, p["rim"], p["chamfer"],
                          inset, n, dz, report, drain=drain, inner_fn=pot_inner,
                          wall_extra=pot_extra, brand=_brand(p))
        if pc is None:
            report["valid"] = False
            return fail
        _finish(pc, report, "Maceta", _STRIDE(p))
        report["soil_capacity_ml"] = round(cavity_volume(pc["inner_rings"], floor_t) / 1000.0, 0)

        trep = {"model_id": p["model_id"] + "-PLATO-OCULTO", "errors": [], "warnings": []}
        tc = _build_piece(p, rb, ro, 0.0, h_t, tw, tf, "flat", p["chamfer"], inset, n,
                          max(dz, 0.5), trep, drain=None, inner_fn=tray_inner, brand=_brand(p))
        if tc is None:
            report["errors"] += ["Plato oculto: " + e for e in trep["errors"]]
            report["valid"] = False
            return fail
        _finish(tc, trep, "Plato oculto", _STRIDE(p))
        gap_min = float("inf")                    # holgura real medida en las mallas
        for ring in tc["inner_rings"]:
            zA = ring[0][2]
            if zA < z_pb + 0.5 or zA > h_t - 0.05:
                continue
            for (x, y, _) in ring[::3]:
                th = math.atan2(y, x)
                gap_min = min(gap_min, math.hypot(x, y) - rb_pot(th, zA))
        trep["fit_gap_min_mm"] = round(gap_min, 3) if gap_min < float("inf") else None
        if gap_min < 0.12:
            report["errors"].append("La maceta no entra en el plato oculto (holgura %.2f mm): "
                                    "subí tray_clear" % gap_min)
            report["valid"] = False
            return fail
        wr = [r for r in tc["inner_rings"] if r[0][2] <= z_pb + 0.01]
        trep["water_reservoir_ml"] = round(cavity_volume(wr, tf) / 1000.0, 0) if len(wr) > 1 else 0
        report["assembly"] = {"tray_h_mm": round(h_t, 1), "pot_bottom_z_mm": round(z_pb, 1),
                              "seat": "cono 45°", "fit_gap_min_mm": trep["fit_gap_min_mm"],
                              "pot_drop_on_seat_mm": round(cl, 2),
                              "water_reservoir_ml": trep["water_reservoir_ml"]}
        parts.append({"name": "PLATO-OCULTO", "vertices": tc["V"], "faces": tc["F"],
                      "report": trep,
                      "params": dict(p, wall=tw, floor=tf, drain_d=0.0, drain_pattern="none",
                                     model_id=trep["model_id"])})

    elif mode == "screw_tray":
        # --- plato ENROSCABLE ---------------------------------------------
        # Abajo: espiga cilíndrica con rosca macho (maceta) y rosca hembra
        # (plato). Arriba de la rosca, el plato se abre a 45° y sigue su forma
        # exterior con pared tray_wall; la maceta lo acompaña con holgura, así
        # por fuera sólo se ve la línea de unión. Tope final: cono de 45° que
        # apoya en el chaflán del borde del plato. Rosca derecha, flancos
        # suaves <= 45° (imprime parado sin soportes).
        tw, tf = float(p["tray_wall"]), float(p["tray_floor"])
        res_h = float(p["tray_reservoir"])
        cl_s = float(p["tray_clear"])
        P_ = float(p["thread_pitch"])
        th_h = float(p["thread_depth"])
        th_cl = float(p["thread_clear"])
        turns = float(p["thread_turns"])
        h_t = float(p["tray_h"] or 0) or min(36.0, max(24.0, 0.26 * H))
        F_ = 1.5 * th_h / 0.85                     # flanco: pendiente máx 0,85
        if 2 * F_ + 0.3 > P_:
            report["errors"].append("Rosca: con profundidad %.1f mm el paso mínimo es %.1f mm"
                                    % (th_h, 2 * F_ + 0.3))
        ch_e = 1.0                                 # chaflán del borde (asiento)
        z_pb = tf + res_h
        z_th0 = z_pb + 1.0
        fade_f = 0.8 * P_                          # abocardado superior de la hembra
        k_r = 2.5 * wall
        # cuánto espacio hay: rosca + abocardado + cono de 45° + asiento
        room = h_t - ch_e - 2.0 - fade_f - z_th0
        if room / P_ < turns:
            turns = math.floor(room / P_ * 4.0) / 4.0
            if turns >= 1.75:
                report["warnings"].append("Rosca reducida a %.2f vueltas por la altura del plato"
                                          % turns)
        if turns < 1.75:
            report["errors"].append("Plato enroscable muy bajo para una rosca firme (mín. 1,75 "
                                    "vueltas): subí tray_h o bajá tray_reservoir")
        L_th = turns * P_
        z_th1 = z_th0 + L_th
        z_bt = z_th1 + fade_f                      # tope del cilindro roscado
        n_s = 360
        si_tbl = []                                # interior del plato que sigue la forma
        for i in range(61):
            z = h_t * i / 60.0
            rmin = min(rb(TAU * k / n_s, z) for k in range(n_s)) - inset
            slope = max(abs(rb(TAU * k / 48.0, min(z + 0.5, h_t)) - rb(TAU * k / 48.0, max(z - 0.5, 0.0)))
                        for k in range(48))          # pendiente máxima alrededor
            si_tbl.append((z, rmin - tw * math.sqrt(1.0 + slope * slope)))

        def _lerp(tbl, z):
            if z <= tbl[0][0]:
                return tbl[0][1]
            for (za, ra), (zb_, rb_) in zip(tbl, tbl[1:]):
                if za <= z <= zb_:
                    return ra + (rb_ - ra) * (z - za) / max(zb_ - za, 1e-9)
            return tbl[-1][1]

        run_tbl, m_ = [], float("inf")             # mínimo hacia arriba (la maceta baja)
        for z, r in reversed(si_tbl):
            m_ = min(m_, r)
            run_tbl.append((z, m_))
        run_tbl.reverse()
        Rs = _lerp(run_tbl, tf) - th_h - th_cl     # raíz de la rosca: el plato es más angosto abajo
        if Rs < 15:
            report["errors"].append("Base muy chica para una rosca: subí d_base")
        if report["errors"]:
            report["valid"] = False
            return fail

        def si(z):                                 # interior del plato (forma + chaflán)
            if z >= h_t - ch_e:
                return _lerp(si_tbl, h_t - ch_e) + (z - (h_t - ch_e))
            return _lerp(si_tbl, z)

        def tprof(u):                              # trapecio suave en [0,1], período 1
            x = (u % 1.0) * P_
            crest = (P_ - 2 * F_) / 2.0
            if x < F_:
                return smoothstep(x / F_)
            if x < F_ + crest:
                return 1.0
            if x < 2 * F_ + crest:
                return 1.0 - smoothstep((x - F_ - crest) / F_)
            return 0.0

        def th_env(z):                             # macho: entrada suave, salida corta
            return smoothstep((z - z_th0) / (1.5 * P_)) * smoothstep((z_th1 - z) / (0.6 * P_))

        def env_f(z):                              # hembra: completa hasta arriba del macho
            return smoothstep((z_bt - z) / fade_f)

        def thread(th, z):
            e = th_env(z)
            if e <= 0:
                return 0.0
            return th_h * e * tprof(z / P_ - th / TAU)

        r_bore = Rs + th_cl + th_h

        def tin_c(z):                              # interior circular del plato (arriba de la rosca)
            return max(r_bore, min(r_bore + (z - z_bt), si(z)))

        def tray_inner(th, z, w):
            if z <= z_bt:
                return Rs + th_cl + th_h * (1.0 - env_f(z) * (1.0 - tprof(z / P_ - th / TAU)))
            return tin_c(z)

        r_e = tin_c(h_t)                           # borde superior interior real del plato
        rt_tbl, m_ = [], float("inf")              # mínimo hacia arriba del interior
        for i in range(60, -1, -1):
            z = z_bt + (h_t - z_bt) * i / 60.0
            m_ = min(m_, tin_c(z))
            rt_tbl.append((z, m_))
        rt_tbl.reverse()

        # El cono de la maceta corre PARALELO al interior del plato, cl_s por
        # dentro, y nace directo de la espiga (sin escalón). La maceta apoya en
        # el borde superior del plato tras bajar cl_s (cabe en el juego axial
        # de la rosca), igual que el plato oculto.
        z_c0 = z_bt - (r_bore - cl_s - Rs)

        def rb_pot(th, z):
            core = Rs + thread(th, z)
            if z <= z_c0:
                return core
            cone = Rs + (z - z_c0)
            follow = _lerp(rt_tbl, min(max(z, z_bt), h_t)) - cl_s
            seat = r_e - cl_s + (z - h_t)
            body = max(core, _smin(cone, follow, k_r), seat)
            return _smin(rb(th, z), body, k_r)

        r_max_ht = max(rb(TAU * k / n_s, h_t) for k in range(n_s))
        z_rv = h_t + (r_max_ht - r_e) + k_r
        L_b = max(3.0, 2.0 * inset)

        def blend_vis(z):
            return smoothstep((z - z_rv) / L_b)

        def ro_pot(th, z):
            b = rb_pot(th, z)
            return b + blend_vis(z) * (ro(th, z) - rb(th, z))

        def pot_inner(th, z, w):
            if z <= z_c0:                          # la rosca es macizo: interior cilíndrico
                return Rs - wall
            if lp is None or z < z_rv:
                return None
            bv = blend_vis(z)
            r_lp = lp.inner_radius(th, z, wall)
            if r_lp is None:
                return None
            b, bp = rb(th, z), rb_pot(th, z)
            return (1.0 - bv) * (bp - 1.1 * wall) + bv * (r_lp - (b - bp))

        def pot_extra(z):
            return -inset * (1.0 - blend_vis(z))

        fine = (z_th0 - 1.0, z_bt + 1.0, min(dz, P_ / 14.0))
        if DEBUG is not None:
            DEBUG.update(dict(rb_pot=rb_pot, tray_inner=tray_inner, z_bt=z_bt, z_th0=z_th0,
                                    z_th1=z_th1, Rs=Rs, r_e=r_e, si=si, h_t=h_t, run=lambda z: _lerp(run_tbl, z)))
        pc = _build_piece(p, rb_pot, ro_pot, z_pb, H, wall, floor_t, p["rim"], p["chamfer"],
                          inset, n, dz, report, drain=drain, inner_fn=pot_inner,
                          wall_extra=pot_extra, fine=fine, brand=_brand(p))
        if pc is None:
            report["valid"] = False
            return fail
        _finish(pc, report, "Maceta", _STRIDE(p))
        report["soil_capacity_ml"] = round(cavity_volume(pc["inner_rings"], floor_t) / 1000.0, 0)

        trep = {"model_id": p["model_id"] + "-PLATO-ROSCA", "errors": [], "warnings": []}
        tc = _build_piece(p, rb, ro, 0.0, h_t, tw, tf, "flat", p["chamfer"], inset, n,
                          max(dz, 0.5), trep, drain=None, inner_fn=tray_inner, fine=fine, brand=_brand(p))
        if tc is None:
            report["errors"] += ["Plato enroscable: " + e for e in trep["errors"]]
            report["valid"] = False
            return fail
        _finish(tc, trep, "Plato enroscable", _STRIDE(p))
        gap_min, overlap = float("inf"), 0.0
        for ring in tc["inner_rings"]:
            zA = ring[0][2]
            if zA < z_pb + 0.3 or zA > h_t - 0.05:
                continue
            seat_zone = abs(math.hypot(ring[0][0], ring[0][1]) - (r_e + (zA - h_t))) < 0.05
            for (x, y, _) in ring[::2]:
                th = math.atan2(y, x)
                g = math.hypot(x, y) - rb_pot(th, zA)
                if seat_zone:
                    overlap = min(overlap, g)      # en el asiento: contacto, nunca penetración
                else:
                    gap_min = min(gap_min, g)
        trep["fit_gap_min_mm"] = round(gap_min, 3) if gap_min < float("inf") else None
        if gap_min < 0.2 or overlap < -0.02:
            report["errors"].append("Maceta y plato se tocan (holgura %.2f mm): subí "
                                    "thread_clear o tray_clear" % min(gap_min, overlap))
            report["valid"] = False
            return fail
        wr = [r for r in tc["inner_rings"] if r[0][2] <= z_pb + 0.01]
        trep["water_reservoir_ml"] = round(cavity_volume(wr, tf) / 1000.0, 0) if len(wr) > 1 else 0
        report["assembly"] = {"tray_h_mm": round(h_t, 1), "pot_bottom_z_mm": round(z_pb, 1),
                              "thread": "derecha, paso %.1f mm, %.2f vueltas, prof. %.1f mm"
                                        % (P_, turns, th_h),
                              "thread_diameter_mm": round(2 * (Rs + th_h), 1),
                              "fit_gap_min_mm": trep["fit_gap_min_mm"],
                              "pot_drop_on_seat_mm": round(cl_s, 2),
                              "seat": "cono 45° sobre el borde del plato",
                              "water_reservoir_ml": trep["water_reservoir_ml"]}
        parts.append({"name": "PLATO-ROSCA", "vertices": tc["V"], "faces": tc["F"],
                      "report": trep,
                      "params": dict(p, wall=tw, floor=tf, drain_d=0.0, drain_pattern="none",
                                     model_id=trep["model_id"])})

    elif mode in ("screw_dish", "screw_dish_sw"):
        # --- plato INCLINADO enroscable (+ autorriego) ----------------------
        # El plato es un cuenco con borde cortado en plano inclinado y un
        # PERNO central con rosca macho; la maceta (diseño intacto) lleva en
        # el centro del fondo una CAMPANA con rosca hembra y techo cónico de
        # 45°. Se enrosca hasta que la punta cónica del perno apoya en el techo
        # (asiento autocentrante). La base de la maceta queda a `dish_reservoir`
        # (2 mm) del piso del plato: con apenas agua en el plato, la base y sus
        # agujeros de drenaje quedan SUMERGIDOS y la tierra se moja por
        # capilaridad (riego por abajo). Autorriego = borde bajo más alto, para
        # que el agua cubra `dish_water` mm de la maceta.
        sw = mode == "screw_dish_sw"
        tw, tf = float(p["tray_wall"]), max(float(p["tray_floor"]), 2.0)
        res_h = float(p["dish_reservoir"] or 0) or 2.0
        cl_s = float(p["tray_clear"])
        P_ = float(p["thread_pitch"])
        th_h = float(p["thread_depth"])
        th_cl = float(p["thread_clear"])
        turns_req = float(p.get("dish_turns") or p["thread_turns"])
        gap_d = float(p["dish_gap"])
        tube_w = 2.0
        F_ = 1.5 * th_h / 0.85
        if 2 * F_ + 0.3 > P_:
            report["errors"].append("Rosca: con profundidad %.1f mm el paso mínimo es %.1f mm"
                                    % (th_h, 2 * F_ + 0.3))
        r_base = min(rb(TAU * k / 360.0, 0.0) for k in range(360)) - inset
        Rp = max(8.0, min(12.0, 0.27 * r_base))   # raíz de la rosca del perno
        r_smax = Rp + th_cl + th_h                  # fondo de la rosca hembra
        r_to = r_smax + tube_w                      # exterior de la campana
        # la campana (rosca hembra + techo) no debe pasar del 60 % de la altura
        L_max = 0.6 * H - (0.414 * tube_w + r_to) - 1.0 - 0.8 * P_
        turns = min(turns_req, math.floor(L_max / P_ * 4.0) / 4.0)
        if turns < turns_req:
            report["warnings"].append("Rosca: %.2f vueltas (pediste %.2f; no entran por la "
                                      "altura de la maceta)" % (turns, turns_req))
        L_th = turns * P_
        z_s0 = 1.0 + L_th + 0.8 * P_                # campana recta (z local de la maceta)
        z_pb = tf + res_h                           # fondo de la maceta (armada)
        if r_to + 6.0 > r_base - wall:
            report["errors"].append("Base muy chica para la rosca central: subí d_base")
        if turns < 2.0:
            report["errors"].append("Maceta muy baja para la rosca central (%.2f vueltas)"
                                    % turns)
        if report["errors"]:
            report["valid"] = False
            return fail

        def tprof(u):
            x = (u % 1.0) * P_
            crest = (P_ - 2 * F_) / 2.0
            if x < F_:
                return smoothstep(x / F_)
            if x < F_ + crest:
                return 1.0
            if x < 2 * F_ + crest:
                return 1.0 - smoothstep((x - F_ - crest) / F_)
            return 0.0

        zm0, zm1 = z_pb + 1.0, z_pb + 1.0 + L_th    # rosca macho (perno, armado)

        def male(th, z):
            e = smoothstep((z - zm0) / (1.2 * P_)) * smoothstep((zm1 - z) / (0.6 * P_))
            return Rp + (th_h * e * tprof(z / P_ - th / TAU) if e > 0 else 0.0)

        def female(th, zl):                         # campana (z local de la maceta)
            e = smoothstep((z_s0 - zl) / (0.8 * P_))
            r = Rp + th_cl + th_h * (1.0 - e * (1.0 - tprof((zl + z_pb) / P_ - th / TAU)))
            return r + max(0.0, 1.0 - zl)           # chaflán de entrada

        n_f = max(144, min(n, 360))
        th_f = [TAU * k / n_f for k in range(n_f)]

        def ring(rfun, z):
            return [(rfun(t) * math.cos(t), rfun(t) * math.sin(t), z) for t in th_f]
        fdz = P_ / 12.0
        # campana: interior (desde la cara de apoyo) y exterior (desde el fondo interior)
        zl, b_rings = 0.0, []
        while zl < z_s0:
            b_rings.append(ring(lambda t: female(t, zl), zl))
            zl += fdz
        b_rings.append(ring(lambda t: r_smax, z_s0))
        for k in range(1, 8):                       # techo cónico 45°
            rr = r_smax * (1.0 - k / 8.0)
            b_rings.append(ring(lambda t: rr, z_s0 + (r_smax - rr)))
        b_apex = (0.0, 0.0, z_s0 + r_smax)
        z_o = z_s0 + 0.414 * tube_w                 # exterior paralelo al techo
        t_rings = [ring(lambda t: r_to, floor_t), ring(lambda t: r_to, z_o)]
        for k in range(1, 8):
            rr = r_to * (1.0 - k / 8.0)
            t_rings.append(ring(lambda t: rr, z_o + (r_to - rr)))
        t_apex = (0.0, 0.0, z_o + r_to)
        socket = {"bottom": {"rings": b_rings, "apex": b_apex},
                  "top": {"rings": t_rings, "apex": t_apex}}
        # perno del plato (armado): cilindro + rosca + punta cónica paralela al techo
        z_tip0 = z_pb + z_s0 + (r_smax - Rp) - cl_s
        p_rings, z_ = [], tf
        while z_ < z_tip0 - 1e-6:
            p_rings.append(ring(lambda t: male(t, z_), z_))
            z_ = min(z_ + (fdz if zm0 - 1 <= z_ <= zm1 + 1 else 2.0), z_tip0)
        p_rings.append(ring(lambda t: Rp, z_tip0))
        for k in range(1, 8):
            rr = Rp * (1.0 - k / 8.0)
            p_rings.append(ring(lambda t: rr, z_tip0 + (Rp - rr)))
        post = {"top": {"rings": p_rings, "apex": (0.0, 0.0, z_tip0 + Rp)}}

        dp = dict(drain)
        dp["drain_keepout"] = r_to + 0.5
        pc = _build_piece(p, rb, ro, 0.0, H, wall, floor_t, p["rim"], p["chamfer"],
                          inset, n, dz, report, drain=dp, inner_fn=lp_inner,
                          brand=_brand(p), feature=socket)
        if pc is None:
            report["valid"] = False
            return fail
        _finish(pc, report, "Maceta", _STRIDE(p))
        socket_ml = math.pi * r_to ** 2 * (z_o - floor_t) + math.pi * r_to ** 2 * r_to / 3.0
        report["soil_capacity_ml"] = round((cavity_volume(pc["inner_rings"], floor_t)
                                            - socket_ml) / 1000.0, 0)

        # --- cuenco ----------------------------------------------------------
        tilt = math.radians(float(p["dish_tilt"]))
        flare = math.radians(6.0)
        w_d = float(p.get("dish_water") or 0) or (max(12.0, 0.14 * H) if sw
                                                  else max(6.0, 0.07 * H))
        z_low = float(p["dish_low"] or 0) or (z_pb + w_d + 2.0)   # 2 mm de margen
        need = 0.0                                   # R0 tal que R_wi(z) >= maceta + luz
        z_ = z_pb
        while z_ <= z_low + 2 * 110 * math.tan(tilt) + 1.0:
            r_ = max(ro(TAU * k / 180.0, z_ - z_pb) for k in range(180))
            need = max(need, r_ + gap_d - (z_ - tf) * math.tan(flare))
            z_ += 0.5
        R0 = need

        def r_wi(z):
            return R0 + max(z - tf, 0.0) * math.tan(flare)
        dz_tilt = 2.0 * (r_wi(z_low + 30) + tw) * math.tan(tilt)
        z_high = z_low + dz_tilt
        z_mid = (z_low + z_high) / 2.0

        def top(th):                                 # alto atrás (+Y), bajo adelante
            return z_mid + 0.5 * dz_tilt * math.sin(th)

        def dish_out(th, z):
            return r_wi(z) + tw / math.cos(flare)

        def dish_inner(th, z, w):
            return r_wi(z)
        name = "PLATO-AUTORRIEGO" if sw else "PLATO-INCLINADO"
        trep = {"model_id": p["model_id"] + "-" + name, "errors": [], "warnings": []}
        bigb = _brand(p)
        if bigb:
            bigb["size"] = bigb["size"] * 1.5
        n_d = max(360, min(n, 720))
        tc = _build_piece(p, dish_out, dish_out, 0.0, z_high, tw, tf, "flat", p["chamfer"], 0.0,
                          n_d, 1.0, trep, drain=None, inner_fn=dish_inner,
                          top_fn=(z_pb + 1.0, top), brand=bigb, feature=post)
        if tc is None:
            report["errors"] += ["Plato: " + e for e in trep["errors"]]
            report["valid"] = False
            return fail
        _finish(tc, trep, "Plato inclinado", _STRIDE(p))
        # holgura de la rosca (armado, maceta ya apoyada: baja cl_s)
        g_th = float("inf")
        for k in range(0, 360, 3):
            t = TAU * k / 360.0
            z_ = zm0
            while z_ <= zm1:
                g_th = min(g_th, female(t, z_ - z_pb + cl_s) - male(t, z_))
                z_ += 0.2
        g_wall = min(r_wi(z_) - max(ro(TAU * k / 90.0, z_ - z_pb + cl_s) for k in range(90))
                     for z_ in [z_pb + 0.5 * i for i in range(int((z_high - z_pb) / 0.5))])
        trep["fit_gap_min_mm"] = round(min(g_th, g_wall), 3)
        if g_th < 0.15 or g_wall < 1.0:
            report["errors"].append("Maceta y plato se tocan (rosca %.2f mm, pared %.2f mm)"
                                    % (g_th, g_wall))
            report["valid"] = False
            return fail
        # agua: el nivel útil llega hasta 2 mm bajo el borde bajo
        z_w = z_low - 2.0

        def pot_area(zl):                            # sección de la maceta (z local)
            return _poly_area([(ro(TAU * k / 120.0, zl) * math.cos(TAU * k / 120.0),
                                ro(TAU * k / 120.0, zl) * math.sin(TAU * k / 120.0))
                               for k in range(120)])

        def water_ml(level):
            v, z_ = 0.0, tf
            while z_ < level - 1e-9:
                h_ = min(0.5, level - z_)
                zc = z_ + h_ / 2.0
                a_ = math.pi * r_wi(zc) ** 2
                if zc < z_tip0:
                    a_ -= math.pi * Rp ** 2           # perno
                if zc >= z_pb:
                    a_ -= pot_area(zc - z_pb + cl_s)  # maceta sumergida
                v += a_ * h_
                z_ += h_
            return v / 1000.0
        water = water_ml(z_w) * 1000.0
        # la tierra se apoya sobre el piso interior: "mojada" = agua 2 mm por
        # encima de ese piso (entra por los drenajes y la tierra la chupa)
        z_soil = z_pb - cl_s + floor_t
        z_wet = z_soil + 2.0
        report["assembly"] = {"tray_h_mm": round(z_high, 1), "dish_low_mm": round(z_low, 1),
                              "dish_tilt_deg": float(p["dish_tilt"]),
                              "dish_diameter_mm": round(2 * dish_out(0, z_high), 1),
                              "pot_bottom_z_mm": round(z_pb, 1),
                              "thread": "perno central derecho Ø%.0f mm, paso %.1f, %.2f vueltas"
                                        % (2 * (Rp + th_h), P_, turns),
                              "thread_gap_mm": round(g_th, 2),
                              "pot_dish_gap_mm": round(g_wall, 2),
                              "fit_gap_min_mm": trep["fit_gap_min_mm"],
                              "pot_drop_on_seat_mm": round(cl_s, 2),
                              "seat": "punta cónica del perno en el techo de la campana",
                              "water_reservoir_ml": round(water / 1000.0, 0),
                              "water_level_max_mm": round(z_w, 1),
                              "water_over_pot_base_mm": round(z_w - (z_pb - cl_s), 1),
                              "water_over_soil_mm": round(z_w - z_soil, 1),
                              "water_min_wet_ml": round(water_ml(z_wet), 0),
                              "water_min_wet_level_mm": round(z_wet, 1),
                              "pot_floor_top_z_mm": round(z_soil, 2),
                              "water_gap_under_pot_mm": round(res_h - cl_s, 2),
                              "drains_submerged_from_ml": round(water_ml(z_pb - cl_s + 0.5),
                                                                0),
                              "socket_radius_mm": round(r_to, 2),
                              "dish_inner_r0_mm": round(R0, 3),
                              "dish_flare_deg": 6.0,
                              "dish_floor_mm": tf,
                              "pot_floor_radius_mm": round(r_base - wall, 2),
                              "thread_turns": turns,
                              "thread_engagement_mm": round(L_th, 1),
                              "socket_height_mm": round(z_o + r_to, 1)}
        parts.append({"name": name, "vertices": tc["V"], "faces": tc["F"], "report": trep,
                      "params": dict(p, wall=tw, floor=tf, drain_d=0.0, drain_pattern="none",
                                     model_id=trep["model_id"])})

    elif mode == "saucer":
        pc = _build_piece(p, rb, ro, 0.0, H, wall, floor_t, p["rim"], p["chamfer"],
                          inset, n, dz, report, drain=drain, inner_fn=lp_inner, brand=_brand(p))
        if pc is None:
            report["valid"] = False
            return fail
        _finish(pc, report, "Maceta", _STRIDE(p))
        report["soil_capacity_ml"] = round(cavity_volume(pc["inner_rings"], floor_t) / 1000.0, 0)
        sc = build_saucer(p)
        srep = sc["report"]
        srep["model_id"] = p["model_id"] + "-PLATO"
        if not srep.get("valid"):
            report["errors"].append("Plato: %s" % srep["errors"])
            report["valid"] = False
            return fail
        report["assembly"] = {"saucer_diameter_mm": srep["bbox_mm"][0],
                              "pot_bottom_z_mm": float(sc["params"]["floor"])}
        parts.append({"name": "PLATO", "vertices": sc["vertices"], "faces": sc["faces"],
                      "report": srep, "params": sc["params"]})

    elif mode == "self_watering":
        gap = float(p["sw_gap"])
        res_h = float(p["sw_reservoir"] or 0) or min(35.0, max(18.0, 0.22 * H))
        oc = _build_piece(p, rb, ro, 0.0, H, wall, floor_t, "flat", p["chamfer"],
                          inset, n, dz, report, drain=None, inner_fn=lp_inner, brand=_brand(p))
        if oc is None:
            report["valid"] = False
            return fail
        _finish(oc, report, "Cubremaceta", _STRIDE(p))
        # perfil circular del inserto = radio mínimo de la cavidad - holgura
        tbl = []
        for ring in oc["inner_rings"]:
            zA = sum(v[2] for v in ring) / len(ring)
            tbl.append((zA, min(_ring_radii(ring)) - gap))
        tbl.sort()
        # el inserto entra desde arriba: a cada altura no puede ser más ancho
        # que el punto más angosto de la cavidad POR ENCIMA (mínimo acumulado)
        run_min = float("inf")
        for i in range(len(tbl) - 1, -1, -1):
            run_min = min(run_min, tbl[i][1])
            tbl[i] = (tbl[i][0], run_min)
        rim_in_min = min(_ring_radii(oc["inner_rings"][-1]))
        z_ib = floor_t + res_h
        fh = gap + min(1.0, wall - 0.4)                 # el labio apoya sobre el borde
        z_top = H + fh + wall / 2.0

        def r_cav(z):
            if z <= tbl[0][0]:
                return tbl[0][1]
            for (za, ra), (zb, rbb) in zip(tbl, tbl[1:]):
                if za <= z <= zb:
                    return ra + (rbb - ra) * (z - za) / max(zb - za, 1e-9)
            return tbl[-1][1]

        def rb_ins(th, z):
            if z <= H:
                return r_cav(min(z, H))
            return min(r_cav(H) + (z - H), rim_in_min + fh - gap)

        irep = {"model_id": p["model_id"] + "-INSERTO", "errors": [], "warnings": []}
        idrain = {"drain_pattern": "ring", "drain_shape": "circle", "drain_center": True,
                  "drain_d": 5.0, "drain_count": 6, "drain_rings": 1}
        ic = _build_piece(p, rb_ins, rb_ins, z_ib, z_top, wall, floor_t, "round", 0.4,
                          0.0, max(96, n // 2), dz, irep, drain=idrain)
        if ic is None:
            report["errors"] += ["Inserto: " + e for e in irep["errors"]]
            report["valid"] = False
            return fail
        # agrandar el agujero central para la mecha: se reconstruye con agujero mayor
        if float(p["sw_wick_d"]) > 5.0:
            irep2 = {"model_id": irep["model_id"], "errors": [], "warnings": []}
            ic2 = _build_piece(p, rb_ins, rb_ins, z_ib, z_top, wall, floor_t, "round", 0.4,
                               0.0, max(96, n // 2), dz, irep2,
                               drain=_wick_drain(p, rb_ins, z_ib, floor_t, wall))
            if ic2 is not None:
                ic, irep = ic2, irep2
        _finish(ic, irep, "Inserto", _STRIDE(p))
        irep["soil_capacity_ml"] = round(cavity_volume(ic["inner_rings"], floor_t) / 1000.0, 0)
        res_ml = 0.0
        prev = None
        for ring in oc["inner_rings"]:
            zA = sum(v[2] for v in ring) / len(ring)
            if zA > z_ib:
                break
            a = abs(sum(x1 * y2 - x2 * y1 for (x1, y1, _), (x2, y2, _) in zip(ring, ring[1:] + ring[:1]))) / 2.0
            if prev:
                res_ml += (a + prev[1]) / 2.0 * (zA - prev[0])
            prev = (zA, a)
        report["assembly"] = {"reservoir_h_mm": round(res_h, 1),
                              "water_reservoir_ml": round(res_ml / 1000.0, 0),
                              "insert_gap_mm": gap, "lip_over_rim_mm": round(fh, 2),
                              "insert_drop_on_rim_mm": round(gap, 2),
                              "wick_hole_mm": float(p["sw_wick_d"])}
        report["soil_capacity_ml"] = irep["soil_capacity_ml"]
        pc = oc
        parts.append({"name": "INSERTO", "vertices": ic["V"], "faces": ic["F"], "report": irep,
                      "params": dict(p, wall=wall, floor=floor_t, model_id=irep["model_id"],
                                     drain_d=5.0, drain_pattern="ring")})
    else:
        report["errors"].append("mode desconocido: %s (pot | hidden_tray | screw_tray | "
                                "self_watering)" % mode)
        report["valid"] = False
        return fail

    for part in parts:
        if not part["report"].get("valid", True):
            report["errors"].append("%s inválido: %s" % (part["name"], part["report"]["errors"]))
    report["valid"] = not report["errors"]
    report["parts"] = [pt["name"] for pt in parts]
    return {"vertices": pc["V"], "faces": pc["F"], "report": report, "params": p,
            "parts": parts}


def _wick_drain(p, rb_ins, z_ib, floor_t, wall):
    """Fondo del inserto: agujero central grande (mecha) + anillo de agujeros
    chicos para que el agua sobrante baje al depósito."""
    return {"drain_pattern": "ring", "drain_shape": "circle", "drain_center": True,
            "drain_d": 5.0, "drain_count": 6, "drain_rings": 1,
            "drain_center_d": float(p["sw_wick_d"])}


def _local_normal_curvature(r, r_t, r_tt, r_z, r_zz, r_tz):
    """Normal exterior unitaria (en el marco local e_r, e_θ, e_z) y mayor
    curvatura principal CONVEXA (1/mm) de S(θ,z) = (r cosθ, r sinθ, z).
    Se evalúa en θ = 0; vale para cualquier θ por invariancia a la rotación."""
    Su = (r_t, r, 0.0)                    # ∂S/∂θ
    Sv = (r_z, 0.0, 1.0)                  # ∂S/∂z
    Suu = (r_tt - r, 2 * r_t, 0.0)
    Suv = (r_tz, r_z, 0.0)
    Svv = (r_zz, 0.0, 0.0)
    nx = Su[1] * Sv[2] - Su[2] * Sv[1]
    ny = Su[2] * Sv[0] - Su[0] * Sv[2]
    nz = Su[0] * Sv[1] - Su[1] * Sv[0]
    L_ = math.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / L_, ny / L_, nz / L_
    if nx < 0:                            # orientar hacia afuera (+e_r)
        nx, ny, nz = -nx, -ny, -nz
    dot = lambda A, B: A[0] * B[0] + A[1] * B[1] + A[2] * B[2]
    nn = (nx, ny, nz)
    E, F_, G = dot(Su, Su), dot(Su, Sv), dot(Sv, Sv)
    L, M, N = dot(Suu, nn), dot(Suv, nn), dot(Svv, nn)
    det = E * G - F_ * F_
    Hm = (E * N - 2 * F_ * M + G * L) / (2 * det)   # curvatura media
    K = (L * N - M * M) / det                        # curvatura gaussiana
    disc = math.sqrt(max(Hm * Hm - K, 0.0))
    k_min = Hm - disc        # negativa = convexa (cilindro: -1/r)
    return nn, max(0.0, -k_min)


def _tri_z(F, V, a, b, c, up):
    """Triángulo plano con normal +Z (up=True) o -Z."""
    (ax, ay, _), (bx, by, _), (cx, cy, _) = V[a], V[b], V[c]
    cz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    F.append((a, b, c) if (cz > 0) == up else (a, c, b))


def _unwrap(angles):
    out = [angles[0]]
    for a in angles[1:]:
        while a <= out[-1]:
            a += TAU
        while a - out[-1] > TAU:
            a -= TAU
        out.append(a)
    return out


def _zipper(F, V, A, B, up):
    """Une dos anillos cerrados de distinta cantidad de vértices (anillo plano)."""
    n, m = len(A), len(B)
    aA = _unwrap([math.atan2(V[i][1], V[i][0]) for i in A])
    aB = _unwrap([math.atan2(V[i][1], V[i][0]) for i in B])
    shift = aA[0] - aB[0]
    while shift > math.pi:
        shift -= TAU
    while shift < -math.pi:
        shift += TAU
    aB = [x + shift for x in aB]   # mismo origen angular
    aA.append(aA[0] + TAU)
    aB.append(aB[0] + TAU)
    i = j = 0
    while i < n or j < m:
        if i < n and (j >= m or aA[i + 1] <= aB[j + 1]):
            _tri_z(F, V, A[i], A[(i + 1) % n], B[j % m], up)
            i += 1
        else:
            _tri_z(F, V, A[i % n], B[(j + 1) % m], B[j % m], up)
            j += 1


def _build_floor(p, V, F, ring_bot, ring_top, floor_t, report, brand=None, feature=None):
    """Fondo: anillo exterior -> círculo auxiliar -> placa con agujeros (earcut),
    arriba (z=floor_t) y abajo (z=0), más las paredes de cada agujero."""
    ef = _fresh("eden_floor")
    r_in_min = min(math.hypot(V[i][0], V[i][1]) for i in ring_top)
    r_bot_min = min(math.hypot(V[i][0], V[i][1]) for i in ring_bot)
    rc = min(r_in_min, r_bot_min) - 0.8                   # círculo auxiliar (dentro de ambos)
    r_limit = r_in_min - LIMITS["drain_margin"]
    q = dict(p)
    if not q.get("drain_spacing"):
        q["drain_spacing"] = 3.0 * float(q.get("drain_d", 0) or 0)
    if not q.get("drain_slot_len"):
        q["drain_slot_len"] = 3.0 * float(q.get("drain_d", 0) or 0)
    if q.get("drain_shape") in ("leaf", "slot") and q.get("drain_pattern", "ring") == "ring" \
            and float(q.get("drain_d", 0) or 0) > 0:
        # base chica (espiga de rosca, maceta mini): las hojas se acortan solas
        dc = float(q.get("drain_center_d", 0) or 0) or float(q["drain_d"])
        keep = float(q.get("drain_keepout", 0) or 0)
        r0 = dc / 2.0 + 2.5 if (q.get("drain_center", True) and keep <= 0) \
            else max(4.0, keep + 2.0)
        max_len = r_limit - r0 - 0.3
        if float(q["drain_slot_len"]) > max_len:
            if max_len < 2.0 * 4.0:
                report["errors"].append("La base es muy chica para drenaje en hojas: usá "
                                        "drain_shape circle")
                return {}
            q["drain_slot_len"] = round(max_len, 1)
            q["drain_d"] = min(float(q["drain_d"]), round(max_len / 2.4, 1))
            report["warnings"].append("Drenaje: hojas ajustadas a %.1f × %.1f mm para entrar "
                                      "en la base" % (q["drain_slot_len"], q["drain_d"]))
    try:
        holes = ef.hole_layout(q, r_limit)
    except ValueError as ex:
        report["errors"].append(str(ex))
        return {}
    if p.get("drain_pattern") != "none" and float(p.get("drain_d", 0) or 0) > 0:
        if float(p["drain_d"]) < 3.0:
            report["errors"].append("Agujeros de %.1f mm: mínimo 3 mm (se tapan con tierra)"
                                    % p["drain_d"])
        if p.get("drain_shape") == "leaf":
            half = (float(p["drain_d"]) - float(p.get("drain_leaf_vein", 0) or 0)) / 2.0
            if float(p.get("drain_leaf_vein", 0) or 0) > 0 and half < 2.5:
                report["errors"].append(
                    "Hojas muy finas: cada media hoja mide %.1f mm de ancho (mín. 2,5). "
                    "Subí drain_d o bajá drain_leaf_vein" % half)
        if not holes:
            report["errors"].append("El patrón de drenaje no entra en la base: "
                                    "reducí diámetro, cantidad o anillos")
    report["errors"].extend(ef.check_layout(holes, r_limit, LIMITS["drain_gap"]))
    if report["errors"]:
        return {}

    m = max(96, int(math.ceil(TAU * rc / 1.2)))
    circ2d = [(rc * math.cos(TAU * k / m), rc * math.sin(TAU * k / m)) for k in range(m)]

    # marca grabada en la cara de apoyo (se lee mirando la base desde abajo)
    glyphs, b_depth = None, 0.0
    if brand and str(brand.get("text", "")).strip():
        fnt = _fresh("eden_font")
        b_depth = min(float(brand.get("depth", 0.6)), floor_t - 0.9)
        if b_depth < 0.3:
            report["warnings"].append("Marca no grabada: fondo de %.1f mm muy fino" % floor_t)
        else:
            avoid = list(holes)
            if feature and feature.get("bottom"):
                avoid.append([(x, y) for x, y, _ in feature["bottom"]["rings"][0]])
            try:
                pl = fnt.place(str(brand["text"]).strip(), rc - 1.2, avoid,
                               cap_h=float(brand.get("size", 6.0)),
                               min_cap=float(brand.get("min_size", 3.5)))
            except ValueError as ex:
                pl = None
                report["warnings"].append(str(ex))
            if pl is None:
                report["warnings"].append("Marca: no entra en la base sin pisar el drenaje")
            else:
                glyphs = pl[0]
                report["brand"] = {"text": str(brand["text"]).strip(), "cap_h_mm": pl[1],
                                   "depth_mm": round(b_depth, 2),
                                   "pos": [round(pl[2][0], 1), round(pl[2][1], 1), pl[2][2]]}

    def add(pts, z):
        start = len(V)
        V.extend((x, y, z) for x, y in pts)
        return list(range(start, start + len(pts)))

    c_top, c_bot = add(circ2d, floor_t), add(circ2d, 0.0)
    _zipper(F, V, ring_top, c_top, True)
    _zipper(F, V, ring_bot, c_bot, False)
    h_top = [add(h, floor_t) for h in holes]
    h_bot = [add(h, 0.0) for h in holes]
    # superficies de la pieza central (rosca): anillos + vértice final
    f_idx = {}
    for side in ("top", "bottom"):
        ft_ = (feature or {}).get(side)
        if not ft_:
            continue
        rings = [add([(x, y) for x, y, _ in r_], 0.0) for r_ in ft_["rings"]]
        for r_, ids in zip(ft_["rings"], rings):
            for (x, y, z), i in zip(r_, ids):
                V[i] = (x, y, z)
        f_idx[side] = rings
        sgn = 1.0 if side == "top" else -1.0      # arriba: normales hacia afuera/arriba

        def _score(tri):
            nx, ny, nz = _normal(V[tri[0]], V[tri[1]], V[tri[2]])
            cx = (V[tri[0]][0] + V[tri[1]][0] + V[tri[2]][0]) / 3.0
            cy = (V[tri[0]][1] + V[tri[1]][1] + V[tri[2]][1]) / 3.0
            L = math.hypot(cx, cy) or 1.0
            return sgn * ((nx * cx + ny * cy) / L + nz)
        for A_, B_ in zip(rings, rings[1:]):
            tmp = []
            _strip(tmp, A_, B_, len(A_))
            if sum(_score(t) for t in tmp) < 0:
                tmp = [(t[0], t[2], t[1]) for t in tmp]
            F.extend(tmp)
        if ft_.get("apex") is not None:
            ia = len(V)
            V.append(tuple(ft_["apex"]))
            last = rings[-1]
            tmp = [(last[k], last[(k + 1) % len(last)], ia) for k in range(len(last))]
            if sum(_score(t) for t in tmp) < 0:
                tmp = [(t[0], t[2], t[1]) for t in tmp]
            F.extend(tmp)
    top_holes = [(h, it) for h, it in zip(holes, h_top)]
    bot_holes = [(h, ib) for h, ib in zip(holes, h_bot)]
    if "top" in f_idx:
        top_holes.append(([(x, y) for x, y, _ in feature["top"]["rings"][0]], f_idx["top"][0]))
    if "bottom" in f_idx:
        bot_holes.append(([(x, y) for x, y, _ in feature["bottom"]["rings"][0]],
                          f_idx["bottom"][0]))
    for a, b, c in _fix_degenerate(ef.earcut(circ2d, c_top, top_holes), V):
        _tri_z(F, V, a, b, c, True)                                    # cara interior
    if glyphs is None:
        for a, b, c in _fix_degenerate(ef.earcut(circ2d, c_bot, bot_holes), V):
            _tri_z(F, V, a, b, c, False)                               # cara de apoyo
    else:
        g0 = [(add(ext, 0.0), [add(c, 0.0) for c in cs]) for ext, cs in glyphs]
        g1 = [(add(ext, b_depth), [add(c, b_depth) for c in cs]) for ext, cs in glyphs]
        hole_list = bot_holes + [(ext, gi[0]) for (ext, cs), gi in zip(glyphs, g0)]
        for a, b, c in _fix_degenerate(ef.earcut(circ2d, c_bot, hole_list), V):
            _tri_z(F, V, a, b, c, False)                               # cara de apoyo
        for (ext, cs), (e0, c0s), (e1, c1s) in zip(glyphs, g0, g1):
            for c, ci in zip(cs, c0s):                                 # islas (contraformas)
                for a, b, d in _fix_degenerate(ef.earcut(c, ci, []), V):
                    _tri_z(F, V, a, b, d, False)
            for a, b, d in _fix_degenerate(ef.earcut(ext, e1, list(zip(cs, c1s))), V):
                _tri_z(F, V, a, b, d, False)                           # techo del grabado
            # paredes: exterior CCW y contraformas CW -> la izquierda es el hueco
            for loop, l0, l1 in [(ext, e0, e1)] + list(zip(cs, c0s, c1s)):
                k_n = len(loop)
                for k in range(k_n):
                    k1 = (k + 1) % k_n
                    ex_, ey_ = loop[k1][0] - loop[k][0], loop[k1][1] - loop[k][1]
                    want = (-ey_, ex_)
                    for tri in ((l0[k], l0[k1], l1[k1]), (l0[k], l1[k1], l1[k])):
                        nx, ny, _ = _normal(V[tri[0]], V[tri[1]], V[tri[2]])
                        F.append(tri if nx * want[0] + ny * want[1] > 0
                                 else (tri[0], tri[2], tri[1]))
    # paredes de los agujeros: la normal apunta hacia el vacío del agujero.
    # Se orienta con el sentido de giro del polígono (robusto también en
    # formas alargadas o no convexas, como hojas y ranuras).
    for h, ht, hb in zip(holes, h_top, h_bot):
        ccw = ef.polygon_area(h) > 0
        k_n = len(h)
        for k in range(k_n):
            k1 = (k + 1) % k_n
            ex_, ey_ = h[k1][0] - h[k][0], h[k1][1] - h[k][1]
            want = (-ey_, ex_) if ccw else (ey_, -ex_)      # hacia el interior del agujero
            for tri in ((ht[k], ht[k1], hb[k1]), (ht[k], hb[k1], hb[k])):
                nx, ny, _ = _normal(V[tri[0]], V[tri[1]], V[tri[2]])
                if nx * want[0] + ny * want[1] > 0:
                    F.append(tri)
                else:
                    F.append((tri[0], tri[2], tri[1]))
    area_holes = sum(abs(ef.polygon_area(h)) for h in holes)
    return {"drain_holes": len(holes),
            "drain_area_mm2": round(area_holes, 1),
            "drain_area_pct_floor": round(100.0 * area_holes / (math.pi * r_in_min ** 2), 1)}


def _fix_degenerate(tris, V):
    """earcut puede dejar triángulos de área nula (3 puntos alineados) junto
    a los puentes entre contornos. Se elimina cada uno partiendo en dos al
    vecino que comparte su lado largo (la malla sigue cerrada)."""
    tris = [tuple(t) for t in tris]
    for _ in range(len(tris)):
        bad = None
        for t in tris:
            (ax, ay, _), (bx, by, _), (cx, cy, _) = V[t[0]], V[t[1]], V[t[2]]
            if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) < 1e-9:
                bad = t
                break
        if bad is None:
            return tris
        P = [V[i] for i in bad]
        # vértice del medio = el que no es extremo del lado más largo
        best, mid = -1.0, None
        for k in range(3):
            i, j = (k + 1) % 3, (k + 2) % 3
            L = (P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2
            if L > best:
                best, mid = L, k
        m = bad[mid]
        p_, q_ = bad[(mid + 1) % 3], bad[(mid + 2) % 3]
        tris.remove(bad)
        for t in tris:
            if p_ in t and q_ in t:
                d = [x for x in t if x not in (p_, q_)][0]
                tris.remove(t)
                tris.extend([(p_, m, d), (m, q_, d)])
                break
    return tris


def _strip(F, A, B, n):
    """Une dos anillos con normales hacia afuera del sólido."""
    for k in range(n):
        k1 = (k + 1) % n
        F.append((A[k], A[k1], B[k1]))
        F.append((A[k], B[k1], B[k]))


# ---------------------------------------------------------------------------
# PLATO COMPATIBLE (reutiliza el mismo motor)
# ---------------------------------------------------------------------------
def build_saucer(pot_params, clearance=2.5, lip=14.0, flare_deg=12.0,
                 wall=None, floor=1.6, echo_waves=True):
    """Genera un plato cuyo interior deja `clearance` mm alrededor de la huella
    de la maceta. Repite (atenuadas) las ondas radiales para coherencia de marca."""
    pp = merge_params(pot_params)
    wall = wall or pp["wall"]
    H_body = pp["height"] - (pp["wall"] / 2.0 if pp["rim"] == "round" else 0.0)
    n = 720
    ro = make_surface(pp)["ro"]
    foot = max(ro(TAU * k / n, z)
               for k in range(n) for z in (0.0, min(lip, H_body * 0.3)))
    amp = 0.0
    waves = []
    if echo_waves:
        for w in pp["waves"]:
            if w["type"] == "radial" and w["amp"] > 0:
                amp = min(1.2, w["amp"] * 0.4)
                waves = [{"type": "radial", "count": w["count"], "amp": amp,
                          "phase": w["phase"]}]
                break
    r_in = foot + clearance
    d_base = 2.0 * (r_in + wall + amp)
    d_mouth = d_base + 2.0 * lip * math.tan(math.radians(flare_deg))
    sp = {
        "model_id": pp["model_id"] + "-PLATO", "family": "saucer",
        "height": lip, "d_base": d_base, "d_max": d_mouth, "d_mouth": d_mouth,
        "belly": 1.0, "waves": waves, "fade_bottom": 3.0, "fade_top": 3.0,
        "wall": wall, "floor": floor, "rim": "round", "chamfer": 0.4,
        "drain_d": 0.0, "drain_pattern": "none", "quality": pp["quality"],
        "polygon_sides": pp.get("polygon_sides", 0),
        "polygon_blend": pp.get("polygon_blend", 0) * 0.5,
        "brand": pp.get("brand", "Eden3D"), "brand_size": float(pp.get("brand_size", 6.0)) * 1.5,
        "brand_depth": pp.get("brand_depth", 0.6),
    }
    res = build_pot(sp)
    res["report"]["pot_footprint_r_mm"] = round(foot, 2)
    res["report"]["clearance_mm"] = clearance
    return res


# ---------------------------------------------------------------------------
# VALIDACIÓN
# ---------------------------------------------------------------------------
def validate_params(p):
    e, w = [], []
    H, wall, fl = p["height"], p["wall"], p["floor"]
    if p["wall"] < LIMITS["wall_min"]:
        e.append("Pared %.2f mm < mínimo FDM %.1f mm" % (wall, LIMITS["wall_min"]))
    if fl < LIMITS["floor_min"]:
        e.append("Fondo %.2f mm < mínimo %.1f mm" % (fl, LIMITS["floor_min"]))
    h_min = 6 if p.get("family") == "saucer" else 20
    if H < h_min or H > 400:
        e.append("Altura fuera de rango (%d–400 mm)" % h_min)
    for k in ("d_base", "d_max", "d_mouth"):
        if p[k] < 20:
            e.append("%s demasiado chico" % k)
    if p["d_max"] < max(p["d_base"], p["d_mouth"]) and 0.0 < p["belly"] < 1.0:
        w.append("d_max menor que base o boca: el perfil tendrá un estrangulamiento")
    amp_total = sum(abs(x["amp"]) for x in p["waves"])
    rmin = min(p["d_base"], p["d_mouth"], p["d_max"]) / 2.0
    if amp_total > 0.25 * rmin:
        e.append("Amplitud total de ondas %.1f mm excesiva para radio %.1f mm" % (amp_total, rmin))
    elif amp_total > 0.12 * rmin:
        w.append("Amplitud alta: verificar espesor real y limpieza superficial")
    if (p.get("drain_d", 0) or 0) <= 0 or p.get("drain_pattern") == "none":
        if p.get("family") != "saucer":
            w.append("Sin drenaje: sólo apta como cubremaceta")
    if p["d_base"] / H < LIMITS["stability_ratio"]:
        w.append("Base angosta (d_base/altura = %.2f): riesgo de vuelco" % (p["d_base"] / H))
    if p["d_mouth"] < 0.6 * p["d_max"]:
        w.append("Boca cerrada: dificulta trasplantar")
    if abs(wall / 0.4 - round(wall / 0.4)) > 0.05:
        w.append("Pared %.2f no es múltiplo de 0,4: el laminador dejará huecos o relleno" % wall)
    if p["fade_top"] < 3:
        w.append("Ondas casi hasta el borde: el labio puede quedar irregular")
    if p["rim"] not in ("round", "flat"):
        e.append("rim debe ser 'round' o 'flat'")
    return e, w


def mesh_volume(V, F):
    s = 0.0
    for a, b, c in F:
        ax, ay, az = V[a]; bx, by, bz = V[b]; cx, cy, cz = V[c]
        s += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return s / 6.0


def cavity_volume(inner_rings, z0):
    """Volumen útil de tierra (integración de áreas de anillos interiores)."""
    areas, zs = [], []
    for ring in inner_rings:
        a = 0.0
        for (x1, y1, _), (x2, y2, _) in zip(ring, ring[1:] + ring[:1]):
            a += x1 * y2 - x2 * y1
        areas.append(abs(a) / 2.0)
        zs.append(ring[0][2])
    v = 0.0
    for i in range(1, len(areas)):
        v += (areas[i] + areas[i - 1]) / 2.0 * (zs[i] - zs[i - 1])
    return v


def overhang_stats(V, F, z_ignore=1e-6, stride=1):
    """Ángulo de voladizo medido desde la vertical (0 = pared vertical,
    90 = techo horizontal). Ignora la cara de apoyo y el chaflán inferior."""
    worst, area_over, area_tot = 0.0, 0.0, 0.0
    lim = math.sin(math.radians(LIMITS["overhang_deg"]))
    for a, b, c in (F[::stride] if stride > 1 else F):
        A, B, C = V[a], V[b], V[c]
        if A[2] <= z_ignore and B[2] <= z_ignore and C[2] <= z_ignore:
            continue
        ux, uy, uz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
        vx, vy, vz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        L = math.sqrt(nx * nx + ny * ny + nz * nz)
        if L == 0:
            continue
        area_tot += L / 2
        nzn = nz / L
        if nzn < 0:
            if -nzn > lim:
                area_over += L / 2
            worst = max(worst, math.degrees(math.asin(min(1.0, -nzn))))
    return {"overhang_max_deg": round(worst, 1),
            "overhang_area_pct_over45": round(100 * area_over / max(area_tot, 1e-9), 2)}


# ---------------------------------------------------------------------------
# M5 — EXPORTACIÓN (sin dependencias)
# ---------------------------------------------------------------------------
def _normal(A, B, C):
    ux, uy, uz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
    vx, vy, vz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / L, ny / L, nz / L


def write_stl(path, V, F, name="EDEN3D"):
    """STL binario en milímetros."""
    with open(path, "wb") as fh:
        header = ("%s | Eden3D motor %s | mm" % (name, ENGINE_VERSION)).encode("ascii", "replace")
        fh.write(header[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(F)))
        for a, b, c in F:
            A, B, C = V[a], V[b], V[c]
            fh.write(struct.pack("<12fH", *(_normal(A, B, C) + A + B + C + (0,))))


def write_3mf(path, V, F, name="EDEN3D"):
    """3MF básico (Core spec), unidades milímetros."""
    verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in V)
    tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">%s</metadata>'
             '<metadata name="Designer">Eden3D</metadata>'
             '<metadata name="Copyright">© Eden3D</metadata>'
             '<resources><object id="1" type="model" name="%s"><mesh>'
             '<vertices>%s</vertices><triangles>%s</triangles>'
             '</mesh></object></resources>'
             '<build><item objectid="1"/></build></model>') % (name, name, verts, tris)
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def write_3mf_multi(path, objects, meta=None):
    """3MF con VARIAS piezas (objetos separados) acomodadas una al lado de la
    otra sobre la cama, con metadatos de marca. objects = [(nombre, V, F)]."""
    meta = meta or {}
    res, items, x_cursor = [], [], 0.0
    for i, (name, V, F) in enumerate(objects):
        xs = [v[0] for v in V]
        ys = [v[1] for v in V]
        w = max(xs) - min(xs)
        cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        tx = x_cursor + w / 2.0 - cx
        x_cursor += w + 12.0
        verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in V)
        tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices>'
                   '<triangles>%s</triangles></mesh></object>' % (i + 1, _xml(name), verts, tris))
        items.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>'
                     % (i + 1, tx, -cy))
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s'
             '<resources>%s</resources><build>%s</build></model>') % (md, "".join(res), "".join(items))
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def _xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def save_params(path, result):
    data = {"brand": result["params"].get("brand", "Eden3D"), "engine": ENGINE_VERSION,
            "params": result["params"], "report": result["report"]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def clean_path(text):
    """Limpia una ruta pegada en un Panel de Grasshopper: quita saltos de línea,
    caracteres invisibles (p. ej. marcas de dirección U+202A que Windows agrega
    al copiar rutas), espacios y comillas en los extremos."""
    import unicodedata
    s = "".join(ch for ch in str(text or "")
                if unicodedata.category(ch) not in ("Cc", "Cf", "Zl", "Zp"))
    return s.strip().strip('"').strip("'").strip()


def load_params(path_or_text):
    """Acepta ruta a .json o texto JSON. Si el JSON es una exportación
    previa (con clave 'params'), reproduce exactamente ese diseño."""
    raw = str(path_or_text)
    if raw.strip().startswith("{"):
        txt = raw
    else:
        path = clean_path(raw)
        if not os.path.isfile(path):
            raise IOError("No encuentro el preset. Texto recibido (con caracteres "
                          "ocultos visibles): %s" % ascii(raw))
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
    d = json.loads(txt)
    return d.get("params", d)
