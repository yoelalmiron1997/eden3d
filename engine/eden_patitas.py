# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
PATITAS ARTICULADAS — patas y bracitos que se imprimen ya armados (print in place)
=================================================================================
Diseño propio de Eden3D. Cada pata es una cadena de eslabones acostados en la cama,
que salen del pie de la maceta (o del plato, si va en plato). Las bisagras son de
"anillo y barra", sin restas booleanas:

    eslabón k  ...cuerpo══╗ púa ┃  barra (cilindro a lo ancho, a media altura)
                          ╚ púa ┃     ◯  ← anillo (toro) del eslabón k+1 alrededor de la barra
    eslabón k+1                       ◯══cuello══cuerpo...

  * la barra va de púa a púa (puente corto) y el anillo de k+1 la abraza con holgura;
  * el anillo apoya en la cama (va de 0 a t) y el cuello también: nada queda flotando;
  * el cuerpo de k+1 empieza más allá del alcance de las púas, y el cuerpo de k termina
    antes del anillo de k+1: la rodilla gira para abajo y para arriba sin trabarse.

Todo son sólidos cerrados que se superponen (cajas redondeadas, cilindros, toros); el
laminador los une, como las aletas del mate. El soporte de la cadera se mete en la pared
de la pieza ("se fusiona") sin llegar al lado de adentro.

    agregar(res, opciones) -> info     (suma las piezas a la maceta o al plato de res)
    armar(res, opciones)   -> (pieza, cadenas, info) sin tocar res (la web las anima)
"""
import math

TAU = 2.0 * math.pi

TIPOS = [("patas", "Patitas"), ("patas_brazos", "Patitas y bracitos"), ("brazos", "Bracitos")]
PIES = [("bota", "Botitas"), ("pato", "Patas de pato")]
DEFECTO = {"tipo": "patas", "pie": "bota", "eslabones": 3, "holgura": 0.45}
LIMITES = {"eslabones": (2, 5), "holgura": (0.3, 0.7)}
FRENTE = -math.pi / 2          # las patas salen hacia -y (el frente, como el relieve del mate)
PIEZA_PLATO = ("PLATO", "PLATO-INCLINADO", "PLATO-AUTORRIEGO", "PLATO-OCULTO", "PLATO-ROSCA")


# ===========================================================================
# PRIMITIVAS CERRADAS (en el marco local u = a lo largo, v = a lo ancho, w = arriba)
# ===========================================================================
def _vol(V, F):
    s = 0.0
    for a, b, c in F:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = V[a], V[b], V[c]
        s += x1 * (y2 * z3 - z2 * y3) - y1 * (x2 * z3 - z2 * x3) + z1 * (x2 * y3 - y2 * x3)
    return s / 6.0


def _orientar(V, F):
    return [(a, c, b) for a, b, c in F] if _vol(V, F) < 0 else F


def rect_redondo(u0, u1, v0, v1, r, n=5):
    """Rectángulo con esquinas redondeadas (antihorario visto desde arriba)."""
    r = max(0.0, min(r, (u1 - u0) / 2.0 - 1e-3, (v1 - v0) / 2.0 - 1e-3))
    if r <= 1e-3:
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    pts = []
    for cu, cv, a0 in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def prisma(poly, w0, w1):
    """Extrusión vertical de un polígono convexo (antihorario) entre w0 y w1."""
    n = len(poly)
    V = [(u, v, w0) for u, v in poly] + [(u, v, w1) for u, v in poly]
    cu = sum(p[0] for p in poly) / n
    cv = sum(p[1] for p in poly) / n
    V += [(cu, cv, w0), (cu, cv, w1)]
    b, t = 2 * n, 2 * n + 1
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [(b, j, i), (t, n + i, n + j), (i, j, n + j), (i, n + j, n + i)]
    return V, _orientar(V, F)


def cilindro_v(u, w, v0, v1, r, n=24):
    """Cilindro con eje a lo ancho (v), centro (u, w)."""
    V = []
    for v in (v0, v1):
        for k in range(n):
            a = TAU * k / n
            V.append((u + r * math.cos(a), v, w + r * math.sin(a)))
    V += [(u, v0, w), (u, v1, w)]
    c0, c1 = 2 * n, 2 * n + 1
    F = []
    for k in range(n):
        q = (k + 1) % n
        F += [(c0, k, q), (c1, n + q, n + k), (k, n + k, n + q), (k, n + q, q)]
    return V, _orientar(V, F)


def toro_v(u, w, R, r, n=36, m=14):
    """Anillo (toro) con eje a lo ancho (v): queda parado en el plano u–w."""
    V = []
    for i in range(n):
        a = TAU * i / n
        ca, sa = math.cos(a), math.sin(a)
        for j in range(m):
            b = TAU * j / m
            rr = R + r * math.cos(b)
            V.append((u + rr * ca, r * math.sin(b), w + rr * sa))
    F = []
    for i in range(n):
        for j in range(m):
            a0, a1 = i * m + j, i * m + (j + 1) % m
            b0, b1 = ((i + 1) % n) * m + j, ((i + 1) % n) * m + (j + 1) % m
            F += [(a0, b0, b1), (a0, b1, a1)]
    return V, _orientar(V, F)


# ===========================================================================
# MEDIDAS (todo sale del grosor t, que escala con la maceta)
# ===========================================================================
def medidas(D, holgura=0.45, brazo=False):
    t = max(8.0, min(14.0, 0.115 * D))
    if brazo:
        t = max(8.0, 0.8 * t)
    c = float(holgura)
    rr = 0.14 * t                         # tubo del anillo
    Rr = t / 2.0 - rr                     # el anillo va de 0 a t (apoya en la cama)
    rb = Rr - rr - c                      # barra: entra en el agujero del anillo con holgura c
    pe = rb + 0.8                         # las púas pasan un poco más allá de la barra
    pw = 0.3 * t                          # ancho de cada púa
    W = max(1.15 * t, 2 * rr + 2 * c + 2 * pw + 0.6)
    rho_p = math.hypot(pe, t / 2.0)       # alcance de las púas desde el eje
    u_s = rho_p + c                       # donde empieza el cuerpo del eslabón siguiente
    P = max(1.5 * t, u_s + t / 2.0 + c + 0.3 * t)
    return {"t": t, "c": c, "rr": rr, "Rr": Rr, "rb": rb, "pe": pe, "pw": pw, "W": W,
            "rho_p": rho_p, "u_s": u_s, "P": P}


# ===========================================================================
# CADENA (eslabones en el marco local; u = 0 en el eje de la cadera)
# ===========================================================================
def _punta(m, u0, u1, final):
    """Pie o mano al final de la cadena (desde u0, largo u1 - u0)."""
    t, W = m["t"], m["W"]
    if final == "bota":
        return [prisma(rect_redondo(u0, u1 + 0.9 * t, -0.62 * W, 0.62 * W, 0.45 * t, 6), 0.0, t)]
    if final == "pato":                   # pata palmeada: abanico chato con tres dedos
        L = u1 - u0 + 1.1 * t
        poly = []
        for k in range(17):
            a = math.radians(-60 + 120.0 * k / 16)
            rr = L * (0.92 + 0.08 * math.cos(3 * a * 3))
            poly.append((u0 + rr * math.cos(a), rr * math.sin(a) * 0.9))
        poly = [(u0, -0.35 * W)] + poly + [(u0, 0.35 * W)]
        return [prisma(poly, 0.0, 0.5 * t), prisma(rect_redondo(u0 - 0.2, u0 + 0.5 * t, -W / 2, W / 2, 0.2 * t), 0.0, t)]
    if final == "mano":                   # mitón con pulgar
        return [prisma(rect_redondo(u0, u1 + 0.6 * t, -0.55 * W, 0.55 * W, 0.4 * t, 6), 0.0, 0.8 * t),
                prisma(rect_redondo(u0 + 0.2 * t, u0 + 0.75 * t, 0.3 * W, 0.85 * W, 0.2 * t), 0.0, 0.7 * t)]
    if final == "ala":                    # alita de pato
        L = u1 - u0 + 0.9 * t
        poly = [(u0, -0.45 * W), (u0 + 0.5 * L, -0.55 * W), (u0 + L, -0.15 * W), (u0 + L, 0.15 * W),
                (u0 + 0.6 * L, 0.6 * W), (u0, 0.45 * W)]
        return [prisma(poly, 0.0, 0.55 * t)]
    raise ValueError("final desconocido: %s" % final)


def cadena(m, n, final):
    """Eslabones de una pata (o brazo): [{"shells": [...], "eje_u": u del eje de entrada}].
    El eslabón 0 es el soporte de la cadera (púas + barra) y va pegado a la pieza; su
    parte de atrás (u < 0) la completa quien lo pega a la pared."""
    t, c, P, W = m["t"], m["c"], m["P"], m["W"]
    rr, Rr, rb, pe, pw = m["rr"], m["Rr"], m["rb"], m["pe"], m["pw"]
    hw = W / 2.0

    def puas_y_barra(u_eje, u_desde):
        return [prisma(rect_redondo(u_desde, u_eje + pe, -hw, -hw + pw, 0.45 * pw), 0.0, t),
                prisma(rect_redondo(u_desde, u_eje + pe, hw - pw, hw, 0.45 * pw), 0.0, t),
                cilindro_v(u_eje, t / 2.0, -hw + 0.4, hw - 0.4, rb)]
    out = []
    for k in range(1, n + 1):
        u0 = (k - 1) * P                       # eje de entrada (anillo)
        u1 = u0 + P                            # eje de salida (barra del siguiente)
        sh = [toro_v(u0, t / 2.0, Rr, rr),
              prisma(rect_redondo(u0 + Rr - 0.3, u0 + m["u_s"] + 0.3, -rr, rr, 0.3 * rr), 0.0, 0.62 * t)]
        if k < n:
            fin_cuerpo = u1 - t / 2.0 - c
            sh.append(prisma(rect_redondo(u0 + m["u_s"], fin_cuerpo, -hw, hw, 0.25 * t), 0.0, t))
            sh += puas_y_barra(u1, fin_cuerpo - 0.3 * t)
        else:
            sh += _punta(m, u0 + m["u_s"], u0 + m["u_s"] + 0.4 * t, final)
        out.append({"shells": sh, "eje_u": u0})
    return out


# ===========================================================================
# DÓNDE VA Y CÓMO SE PEGA A LA PIEZA
# ===========================================================================
def pieza_de(res):
    """La pieza que toca la mesa: el plato si hay, si no la maceta."""
    for pt in res.get("parts") or []:
        if pt["name"] in PIEZA_PLATO:
            return pt["name"], pt["vertices"], pt["faces"]
    return "MACETA", res["vertices"], res["faces"]


def _pared(V, theta, v_off, t, banda=2.0):
    """u (a lo largo de la cadena) de la cara de afuera de la pared a la altura de la
    cadena: el máximo y el mínimo (por las texturas) entre los vértices de esa franja."""
    U = (math.cos(theta), math.sin(theta))
    Vv = (-math.sin(theta), math.cos(theta))
    us = []
    for x, y, z in V:
        if 0.15 < z < t - 0.15:
            v = x * Vv[0] + y * Vv[1]
            if abs(v - v_off) < banda:
                u = x * U[0] + y * U[1]
                if u > 0:
                    us.append(u)
    if not us:
        raise ValueError("no se encontró la pared de la pieza para las patitas")
    return max(us)


def _mundo(shells, theta, v_off):
    ct, st = math.cos(theta), math.sin(theta)
    out = []
    for V, F in shells:
        out.append(([(u * ct - (v + v_off) * st, u * st + (v + v_off) * ct, w) for u, v, w in V], F))
    return out


def opciones(o):
    o = dict(DEFECTO, **(o or {}))
    if o["tipo"] not in [k for k, _ in TIPOS]:
        raise ValueError("tipo de patitas desconocido: %s" % o["tipo"])
    if o["pie"] not in [k for k, _ in PIES]:
        raise ValueError("pie desconocido: %s" % o["pie"])
    lo, hi = LIMITES["eslabones"]
    o["eslabones"] = max(lo, min(hi, int(o["eslabones"])))
    lo, hi = LIMITES["holgura"]
    o["holgura"] = max(lo, min(hi, float(o["holgura"])))
    return o


def armar(res, o):
    """-> (nombre de la pieza, cadenas, info). Cada cadena: {"nombre", "soporte": shells
    (pegado a la pieza), "eslabones": [{"shells", "eje": (punto, dirección)}]}."""
    o = opciones(o)
    nombre, V, _ = pieza_de(res)
    xs, ys = [v[0] for v in V], [v[1] for v in V]
    D = max(max(xs) - min(xs), max(ys) - min(ys))
    p = res.get("params") or {}
    tex = float(p.get("tex_amp") or 0.0)
    pared = float(p.get("wall") or 1.6)
    pedidos = []
    if o["tipo"] in ("patas", "patas_brazos"):
        m = medidas(D, o["holgura"])
        S = max(m["W"] + 5.0, 0.34 * D)
        pedidos += [("PATA_I", FRENTE, -S / 2.0, m, o["eslabones"], o["pie"]),
                    ("PATA_D", FRENTE, S / 2.0, m, o["eslabones"], o["pie"])]
    if o["tipo"] in ("brazos", "patas_brazos"):
        m = medidas(D, o["holgura"], brazo=True)
        mano = "ala" if o["pie"] == "pato" else "mano"
        pedidos += [("BRAZO_I", math.pi, 0.0, m, 2, mano), ("BRAZO_D", 0.0, 0.0, m, 2, mano)]
    cadenas = []
    for nom, th, voff, m, n, final in pedidos:
        t = m["t"]
        u_out = _pared(V, th, voff, t)
        u_in = u_out - tex - 0.6 * pared           # se mete en la pared sin pasarla
        u_eje = u_out + t / 2.0 + m["c"] + 1.0     # el anillo del primer eslabón no roza la pared
        hw = m["W"] / 2.0
        soporte = [prisma(rect_redondo(u_in, u_out + 1.0, -hw, hw, 0.2 * t), 0.0, t),
                   prisma(rect_redondo(u_in, u_eje + m["pe"], -hw, -hw + m["pw"], 0.45 * m["pw"]), 0.0, t),
                   prisma(rect_redondo(u_in, u_eje + m["pe"], hw - m["pw"], hw, 0.45 * m["pw"]), 0.0, t),
                   cilindro_v(u_eje, t / 2.0, -hw + 0.4, hw - 0.4, m["rb"])]
        esl = []
        for e in cadena(m, n, final):
            sh = [([(u + u_eje, v, w) for u, v, w in Vs], Fs) for Vs, Fs in e["shells"]]
            u = u_eje + e["eje_u"]
            ct, st = math.cos(th), math.sin(th)
            punto = (u * ct - voff * st, u * st + voff * ct, t / 2.0)
            direc = (-st, ct, 0.0)                  # eje de la bisagra: a lo ancho
            esl.append({"shells": _mundo(sh, th, voff), "eje": (punto, direc)})
        cadenas.append({"nombre": nom, "soporte": _mundo(soporte, th, voff), "eslabones": esl,
                        "medidas": {k: round(v, 3) for k, v in m.items()},
                        "angulo": round(math.degrees(th), 1), "desplazamiento": round(voff, 2),
                        "u_pared": round(u_out, 2), "u_eje": round(u_eje, 2)})
    info = {"tipo": o["tipo"], "pie": o["pie"], "eslabones": o["eslabones"], "holgura": o["holgura"],
            "pieza": nombre, "cadenas": [{"nombre": c["nombre"], "eslabones": len(c["eslabones"]),
                                          "grosor_mm": round(c["medidas"]["t"], 2),
                                          "barra_mm": round(2 * c["medidas"]["rb"], 2)}
                                         for c in cadenas]}
    return nombre, cadenas, info


def agregar(res, o):
    """Suma las patitas a la pieza (sólidos superpuestos: el laminador los une)."""
    nombre, cadenas, info = armar(res, o)
    if nombre == "MACETA":
        V, F = res["vertices"], res["faces"]
    else:
        pt = [p for p in res["parts"] if p["name"] == nombre][0]
        V, F = pt["vertices"], pt["faces"]
    for c in cadenas:
        for Vs, Fs in c["soporte"] + [s for e in c["eslabones"] for s in e["shells"]]:
            off = len(V)
            V.extend(Vs)
            F.extend((a + off, b + off, d + off) for a, b, d in Fs)
    res["report"]["patitas"] = info
    return info
