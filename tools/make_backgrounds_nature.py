# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Fondos de naturaleza DESENFOCADOS para los renders de Eden3D (1080×1350, 4:5).
Todo dibujado por código (sin fotos de terceros): bosque con sol y mesa de
madera, hojas con bokeh verde y suelo de musgo oscuro.
USO: python tools/make_backgrounds_nature.py renders/fondos/naturaleza
Escribe también fondos.json (dónde apoya la maceta y si el texto va claro u oscuro).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1350


# --------------------------------------------------------------------------- util
def rgb_f(img):
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def vgrad(stops):
    """Gradiente vertical: stops = [(y_frac, (r,g,b)), ...]."""
    ys = np.linspace(0, 1, H)[:, None]
    out = np.zeros((H, 1, 3), np.float32)
    ps = [s[0] for s in stops]
    for c in range(3):
        out[:, 0, c] = np.interp(ys[:, 0], ps, [s[1][c] / 255.0 for s in stops])
    return np.repeat(out, W, axis=1)


def radial(cx, cy, r, power=2.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return np.clip(1.0 - d, 0, 1) ** power


def screen(a, b):
    return 1 - (1 - a) * (1 - b)


def layer(draw_fn, blur, size=(W, H)):
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    if blur:
        lay = lay.filter(ImageFilter.GaussianBlur(blur))
    return lay


def over(base_arr, lay):
    b = to_img(base_arr).convert("RGBA")
    return rgb_f(Image.alpha_composite(b, lay))


def bokeh(rnd, n, cx, cy, spread, rmin, rmax, cols, amin, amax, blur, ring=True):
    def fn(d):
        for _ in range(n):
            a = rnd.uniform(0, 2 * math.pi)
            rr = abs(rnd.gauss(0, 1)) * spread
            x, y = cx + math.cos(a) * rr * 1.2, cy + math.sin(a) * rr * 0.8
            r = rnd.uniform(rmin, rmax)
            c = cols[rnd.randrange(len(cols))]
            al = int(255 * rnd.uniform(amin, amax))
            d.ellipse([x - r, y - r, x + r, y + r], fill=c + (al,))
            if ring:                         # borde apenas más brillante (lente)
                d.ellipse([x - r, y - r, x + r, y + r], outline=c + (min(255, al + 15),),
                          width=max(1, int(r * 0.08)))
    return layer(fn, blur)


def grade(a, lift=0.0, warm=(1, 1, 1), sat=1.0, gamma=1.0):
    g = a.mean(axis=2, keepdims=True)
    a = g + (a - g) * sat
    a = a * np.array(warm, np.float32)
    a = np.clip(a, 0, 1) ** gamma
    return a * (1 - lift) + lift


def grain(a, rnd, amt=0.012):
    n = np.random.default_rng(rnd.randrange(1 << 30)).normal(0, amt, (H, W, 1)).astype(np.float32)
    return a + n


def vignette(a, k=0.35):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return a * (1 - k * d[..., None] ** 2.2)


# --------------------------------------------------------------------- mesa madera
def wood_planks(rnd, tw=1400, th=900, n=7, base=(150, 136, 118)):
    """Textura plana de tablones (vetas a lo largo de Y)."""
    rng = np.random.default_rng(rnd.randrange(1 << 30))
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    out = np.zeros((th, tw, 3), np.float32)
    bw = tw / n
    for i in range(n):
        x0, x1 = int(i * bw), int((i + 1) * bw)
        sub = slice(x0, x1)
        u = (xx[:, sub] - x0) / bw
        tone = rng.uniform(0.82, 1.08)
        c = np.array(base, np.float32) / 255.0 * tone
        # vetas: ruido 1D a lo ancho, estirado a lo largo con ondulación suave
        k = rng.uniform(0, 100)
        wob = 6 * np.sin(yy[:, sub] / rng.uniform(70, 140) + k) + \
            3 * np.sin(yy[:, sub] / rng.uniform(25, 45) + 2 * k)
        xg = (xx[:, sub] + wob)
        fine = 0.5 + 0.5 * np.sin(xg * rng.uniform(0.55, 0.8) + 3 * np.sin(xg * 0.05 + k))
        med = 0.5 + 0.5 * np.sin(xg * rng.uniform(0.12, 0.2) + k)
        v = 0.86 + 0.08 * med + 0.06 * fine
        # grietas finas
        for _ in range(rng.integers(2, 5)):
            cx = rng.uniform(0.15, 0.85)
            crack = np.exp(-((u - cx - 0.01 * np.sin(yy[:, sub] / 30.0 + k)) ** 2) / 0.00002)
            ys0 = rng.uniform(0, th * 0.7)
            mask = (yy[:, sub] > ys0) & (yy[:, sub] < ys0 + rng.uniform(80, 400))
            v = v - 0.35 * crack * mask
        # nudos
        for _ in range(rng.integers(0, 2)):
            kx, ky = rng.uniform(0.3, 0.7), rng.uniform(0.1, 0.9) * th
            d = np.sqrt(((u - kx) * bw / 10.0) ** 2 + ((yy[:, sub] - ky) / 22.0) ** 2)
            v = v - 0.25 * np.exp(-d ** 2) + 0.05 * np.sin(d * 6) * np.exp(-d / 3)
        # borde del tablón (bisel oscuro) + desgaste claro
        edge = np.clip(np.minimum(u, 1 - u) * bw / 7.0, 0, 1)
        v = v * (0.45 + 0.55 * edge)
        out[:, sub, :] = (c[None, None, :] * v[..., None])
        # rendija entre tablones
        out[:, max(x0, x1 - 6):x1, :] = np.array([0.12, 0.10, 0.08])
    out = out * (1 + rng.normal(0, 0.025, (th, tw, 1)).astype(np.float32))
    return np.clip(out, 0, 1)


def perspective_coeffs(src, dst):
    """Coeficientes para Image.transform(PERSPECTIVE): dst -> src."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, np.float64), np.array(B, np.float64)).tolist()


def table(a, rnd, y_top, base=(150, 136, 118), light=(1.0, 0.97, 0.88), far_blur=5):
    tex = wood_planks(rnd, base=base)
    th_, tw_ = tex.shape[:2]
    timg = to_img(tex)
    # tablones que corren hacia el fondo (convergen arriba)
    dst = [(-0.30 * W, H), (1.30 * W, H), (1.04 * W, y_top), (-0.04 * W, y_top)]
    src = [(0, th_), (tw_, th_), (tw_, 0), (0, 0)]
    co = perspective_coeffs(src, dst)
    warped = timg.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(int(x), int(y)) for x, y in dst], fill=255)
    wa = rgb_f(warped)
    # luz: el fondo de la mesa recibe el contraluz del sol
    ys = np.linspace(0, 1, H)[:, None, None]
    t = np.clip((ys - y_top / H) / (1 - y_top / H), 0, 1)
    wa = wa * (1.25 - 0.5 * t) * np.array(light, np.float32)
    wa = wa + 0.18 * np.clip(1 - t * 6, 0, 1) * np.array([1.0, 0.9, 0.6])   # borde con sol
    # desenfoque del tablón lejano (profundidad de campo)
    wb = rgb_f(to_img(wa).filter(ImageFilter.GaussianBlur(far_blur)))
    dof = np.clip(1 - t * 3.0, 0, 1) ** 1.5
    wa = wa * (1 - dof) + wb * dof
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    m = np.asarray(mask, np.float32)[..., None] / 255.0
    return a * (1 - m) + wa * m


# --------------------------------------------------------------------- escenas
def scene_forest_table(seed, warm=False):
    rnd = __import__("random").Random(seed)
    sun = (W * rnd.uniform(0.40, 0.58), H * 0.30)
    a = vgrad([(0, (196, 214, 150)), (0.35, (226, 226, 160)), (0.55, (150, 178, 90)),
               (0.75, (92, 128, 52)), (1, (60, 86, 36))])
    # copa del bosque (manchas verdes, muy desenfocadas)
    def foliage(d):
        for _ in range(900):
            x, y = rnd.uniform(-80, W + 80), rnd.uniform(-80, H * 0.62)
            if math.hypot(x - sun[0], (y - sun[1]) * 1.3) < rnd.uniform(120, 230):
                continue                      # hueco donde entra el sol
            r = rnd.uniform(18, 70)
            g = rnd.randint(95, 175)
            c = (int(g * rnd.uniform(0.45, 0.7)), g, int(g * rnd.uniform(0.2, 0.4)))
            d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=c + (rnd.randint(90, 200),))
    a = over(a, layer(foliage, 22))
    # troncos en 3 planos (los lejanos más claros y borrosos)
    for depth, (cnt, blur, col, wmin, wmax) in enumerate(((7, 16, (96, 112, 70), 12, 26),
                                                          (5, 9, (62, 70, 44), 22, 40),
                                                          (3, 6, (40, 44, 30), 38, 64))):
        def trunks(d):
            for _ in range(cnt):
                x = rnd.uniform(0.02, 0.98) * W
                if abs(x - sun[0]) < 70:
                    x += 140
                w0 = rnd.uniform(wmin, wmax)
                yb = H * rnd.uniform(0.60, 0.66)
                pts_l, pts_r = [], []
                for k in range(13):
                    y = -40 + (yb + 40) * k / 12.0
                    bend = 10 * math.sin(k / 3.0 + x)
                    ww = w0 * (0.75 + 0.25 * k / 12.0)
                    pts_l.append((x + bend - ww / 2, y)); pts_r.append((x + bend + ww / 2, y))
                d.polygon(pts_l + pts_r[::-1], fill=col + (235,))
                for _ in range(rnd.randint(1, 3)):          # ramas
                    y = rnd.uniform(0.05, 0.4) * H
                    s = rnd.choice((-1, 1))
                    d.line([(x, y), (x + s * rnd.uniform(60, 160), y - rnd.uniform(40, 120))],
                           fill=col + (200,), width=max(2, int(w0 * 0.25)))
        a = over(a, layer(trunks, blur))
    # suelo de pasto con manchas de sol y un sendero
    def grass(d):
        for _ in range(500):
            x, y = rnd.uniform(-50, W + 50), rnd.uniform(H * 0.58, H * 0.78)
            r = rnd.uniform(20, 60)
            g = rnd.randint(120, 200)
            sunlit = rnd.random() < 0.35
            c = (int(g * (0.75 if sunlit else 0.5)), g, int(g * (0.3 if sunlit else 0.22)))
            d.ellipse([x - r * 1.8, y - r * 0.35, x + r * 1.8, y + r * 0.35],
                      fill=c + (rnd.randint(80, 180),))
        d.polygon([(W * 0.55, H * 0.60), (W * 0.62, H * 0.60), (W * 0.95, H * 0.78),
                   (W * 0.72, H * 0.78)], fill=(196, 190, 160, 150))
    a = over(a, layer(grass, 12))
    # sol: halo + rayos suaves + bokeh
    glow = radial(*sun, r=W * 0.55, power=1.6)[..., None]
    core_ = radial(*sun, r=W * 0.16, power=1.2)[..., None]
    sunc = np.array([1.0, 0.95, 0.72], np.float32)
    a = screen(a, glow * 0.75 * sunc)
    a = screen(a, core_ * 1.0 * np.array([1, 1, 0.92], np.float32))
    a = over(a, bokeh(rnd, 45, sun[0], sun[1], W * 0.25, 10, 34,
                      [(255, 250, 210), (240, 255, 190), (255, 236, 170)], 0.06, 0.28, 4))
    a = over(a, bokeh(rnd, 25, W / 2, H * 0.32, W * 0.45, 14, 44,
                      [(210, 240, 160), (190, 230, 140)], 0.04, 0.14, 6))
    y_top = H * 0.70
    a = table(a, rnd, y_top, base=(160, 146, 126) if not warm else (170, 140, 110),
              light=(1.0, 0.97, 0.88) if not warm else (1.06, 0.95, 0.80))
    if warm:
        a = grade(a, warm=(1.06, 0.98, 0.84), sat=1.05)
    a = vignette(grain(a, rnd), 0.25)
    return a, {"suelo": 0.815, "tema": "claro"}


def leaf_shape(d, x, y, L, ang, col, vein, serr=True):
    pts = []
    for i in range(41):
        t = i / 40.0
        w = L * 0.36 * math.sin(math.pi * t) ** 0.85
        if serr:
            w *= 1 + 0.06 * (1 if i % 2 else -1)
        pts.append((t * L, w))
    pts += [(t * L, -w * 0.95) for t, w in
            [(i / 40.0, L * 0.36 * math.sin(math.pi * i / 40.0) ** 0.85 *
              ((1 + 0.06 * (1 if i % 2 else -1)) if serr else 1)) for i in range(40, -1, -1)]]
    ca, sa = math.cos(ang), math.sin(ang)
    P = [(x + u * ca - v * sa, y + u * sa + v * ca) for u, v in pts]
    d.polygon(P, fill=col)
    # media hoja más clara (luz rasante) para dar volumen
    half = [(x + u * ca - v * sa, y + u * sa + v * ca) for u, v in pts[:41]] + [(x + L * ca, y + L * sa)]
    d.polygon(half, fill=tuple(min(255, int(c * 1.12)) for c in col[:3]) + (col[3],))
    d.line([(x, y), (x + L * ca, y + L * sa)], fill=vein, width=2)
    for k in range(1, 7):                         # nervaduras
        t = k / 7.5
        bx, by = x + t * L * ca, y + t * L * sa
        for s in (-1, 1):
            ex, ey = bx + L * 0.22 * math.cos(ang + s * 0.9), by + L * 0.22 * math.sin(ang + s * 0.9)
            d.line([(bx, by), (ex, ey)], fill=vein, width=1)


def scene_leaves_bokeh(seed):
    rnd = __import__("random").Random(seed)
    a = vgrad([(0, (120, 160, 70)), (0.4, (70, 110, 40)), (0.75, (40, 70, 28)), (1, (30, 50, 22))])
    a = screen(a, radial(W * 0.78, H * 0.10, W * 0.7, 1.8)[..., None] *
               np.array([0.75, 0.85, 0.45], np.float32))
    a = over(a, bokeh(rnd, 170, W / 2, H * 0.4, W * 0.55, 20, 80,
                      [(170, 210, 110), (120, 170, 70), (200, 230, 150), (90, 140, 50)],
                      0.10, 0.40, 10, ring=False))
    a = over(a, bokeh(rnd, 45, W * 0.6, H * 0.3, W * 0.5, 16, 50,
                      [(235, 245, 225), (250, 255, 235)], 0.10, 0.38, 5))

    def branches(d):
        for _ in range(3):
            y0, y1 = rnd.uniform(0.15, 0.6) * H, rnd.uniform(0.15, 0.6) * H
            amp, ph = rnd.uniform(20, 60), rnd.uniform(0, 6)
            pts = [(x, y0 + (y1 - y0) * x / W + amp * math.sin(x / 260.0 + ph))
                   for x in range(-50, W + 60, 20)]
            d.line(pts, fill=(36, 48, 28, 190), width=rnd.randint(6, 12))
    a = over(a, layer(branches, 12))

    def leaves(d):
        spots = [(W * 0.10, H * 0.30), (W * 0.90, H * 0.52)]
        for sx, sy in spots:
            # ramita que sostiene las hojas
            d.line([(sx - 160, sy + 60), (sx, sy), (sx + 140, sy - 50)], fill=(70, 80, 50, 230),
                   width=4)
            for _ in range(rnd.randint(3, 5)):
                g = rnd.randint(140, 200)
                col = (int(g * 0.60), g, int(g * 0.40), 235)
                vein = (int(g * 0.72), min(255, g + 18), int(g * 0.52), 235)
                leaf_shape(d, sx + rnd.uniform(-110, 110), sy + rnd.uniform(-40, 40),
                           rnd.uniform(110, 170), rnd.uniform(0, 2 * math.pi), col, vein)
    a = over(a, layer(leaves, 9.0))                 # hojas fuera de foco
    # suelo musgoso para apoyar la maceta (nítido cerca de la línea de apoyo)
    yg = H * 0.76

    def moss(d):
        d.rectangle([0, yg, W, H], fill=(62, 92, 36, 255))
        for _ in range(2200):
            x, y = rnd.uniform(-30, W + 30), rnd.uniform(yg - 10, H + 20)
            r = rnd.uniform(6, 18) * (0.6 + (y - yg) / (H - yg))
            g = rnd.randint(85, 125)
            c = (int(g * rnd.uniform(0.55, 0.7)), g, int(g * 0.32))
            d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=c + (170,))
    ml = layer(moss, 0)
    ml_b = ml.filter(ImageFilter.GaussianBlur(10))
    yy = np.linspace(0, 1, H)[:, None]
    near = np.clip(1 - np.abs(yy * H - H * 0.83) / (H * 0.10), 0, 1)
    mix = Image.fromarray((near * 255).astype(np.uint8)).resize((W, H))
    ml = Image.composite(ml.filter(ImageFilter.GaussianBlur(2.5)), ml_b, mix)
    edge = Image.fromarray((np.clip((yy * H - yg) / 40.0, 0, 1) * 255).astype(np.uint8)).resize((W, H))
    ml.putalpha(Image.fromarray(np.minimum(np.asarray(ml.split()[3]), np.asarray(edge))))
    a = over(a, ml)
    a = grade(a, warm=(1.0, 1.02, 0.95), sat=1.05)
    a = vignette(grain(a, rnd), 0.30)
    return a, {"suelo": 0.83, "tema": "claro"}


def scene_dark_moss(seed):
    rnd = __import__("random").Random(seed)
    a = vgrad([(0, (16, 26, 18)), (0.5, (22, 36, 24)), (0.68, (34, 44, 26)), (1, (20, 22, 14))])
    a = over(a, bokeh(rnd, 40, W / 2, H * 0.35, W * 0.55, 30, 110,
                      [(40, 80, 50), (60, 100, 60), (30, 60, 40)], 0.25, 0.6, 22, ring=False))
    a = over(a, bokeh(rnd, 6, W * 0.75, H * 0.25, W * 0.2, 25, 60,
                      [(110, 40, 30), (90, 50, 30)], 0.15, 0.35, 18, ring=False))
    a = screen(a, radial(W * 0.5, H * 0.62, W * 0.6, 2.0)[..., None] *
               np.array([0.20, 0.26, 0.14], np.float32))
    yg = H * 0.68

    def litter(d):
        d.rectangle([0, yg, W, H], fill=(52, 50, 30, 255))
        for _ in range(2400):
            x, y = rnd.uniform(-30, W + 30), rnd.uniform(yg, H + 20)
            r = rnd.uniform(7, 22) * (0.5 + (y - yg) / (H - yg))
            kind = rnd.random()
            if kind < 0.35:                   # hojas secas
                c = (rnd.randint(110, 160), rnd.randint(80, 115), rnd.randint(40, 60))
            elif kind < 0.85:                 # musgo
                g = rnd.randint(70, 140)
                c = (int(g * 0.6), g, int(g * 0.3))
            else:
                c = (rnd.randint(40, 70), rnd.randint(35, 55), rnd.randint(25, 40))
            ang = rnd.uniform(0, math.pi)
            dx, dy = r * math.cos(ang), r * 0.45 * math.sin(ang) + r * 0.3
            d.ellipse([x - abs(dx) - 2, y - dy, x + abs(dx) + 2, y + dy], fill=c + (150,))
    ml = layer(litter, 0)
    yy = np.linspace(0, 1, H)[:, None]
    sharp = np.clip(1 - np.abs(yy * H - H * 0.80) / (H * 0.07), 0, 1)
    blurs = [ml.filter(ImageFilter.GaussianBlur(b)) for b in (2.2, 7, 16)]
    m1 = Image.fromarray((sharp * 255).astype(np.uint8)).resize((W, H))
    mid = Image.fromarray((np.clip(1 - np.abs(yy * H - H * 0.80) / (H * 0.16), 0, 1) * 255)
                          .astype(np.uint8)).resize((W, H))
    ml = Image.composite(blurs[1], blurs[2], mid)
    ml = Image.composite(blurs[0], ml, m1)
    edge = Image.fromarray((np.clip((yy * H - yg) / 70.0, 0, 1) * 255).astype(np.uint8)).resize((W, H))
    ml.putalpha(Image.fromarray(np.minimum(np.asarray(ml.split()[3]), np.asarray(edge))))
    a = over(a, ml)
    # luz cálida rasante sobre el suelo
    a = screen(a, radial(W * 0.45, H * 0.78, W * 0.55, 1.6)[..., None] *
               np.array([0.30, 0.22, 0.10], np.float32))
    a = vignette(grain(a, rnd, 0.015), 0.45)
    return a, {"suelo": 0.80, "tema": "oscuro"}


# --------------------------------------------------------------- interior con sol
def table_horizontal(a, rnd, y_top, base=(232, 186, 132), blur_far=4.0):
    """Mesa de madera con tablas paralelas a la cámara (veta de izquierda a derecha),
    en perspectiva: las tablas se ven más finas hacia el fondo."""
    rng = np.random.default_rng(rnd.randrange(1 << 30))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip((yy - y_top) / (H - y_top), 0, 1)           # 0 = fondo de la mesa
    depth = 1.0 / (0.25 + 1.6 * t)                            # distancia relativa
    u = xx / W                                                # a lo largo de la veta
    v = np.cumsum(np.ones(H, np.float32) / np.maximum(1.0 / (0.25 + 1.6 * np.linspace(0, 1, H)), 1e-3))
    # coordenada "física" hacia el fondo (integral de la profundidad)
    rows = np.zeros(H, np.float32)
    acc = 0.0
    for y in range(H):
        tt = max(0.0, (y - y_top) / (H - y_top))
        acc += 1.0 / (0.25 + 1.6 * tt) ** -1 if False else (0.25 + 1.6 * tt) ** -1
        rows[y] = acc
    d = rows[:, None] * np.ones((1, W), np.float32) / 150.0    # tablas anchas
    plank = np.floor(d)
    frac = d - plank
    tone = 0.85 + 0.2 * np.sin(plank * 12.9898) ** 2
    # veta: ruido muy estirado a lo largo (vetas largas e irregulares)
    def streaks(cols, rows_, amp_blur):
        n = rng.random((rows_, cols)).astype(np.float32)
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        im = im.filter(ImageFilter.GaussianBlur(amp_blur))
        x = np.asarray(im, np.float32) / 255.0
        return (x - x.mean()) / (x.std() + 1e-6)
    n1 = streaks(6, H // 3, 1.2)
    n2 = streaks(24, H, 0.6)
    val = tone * (0.86 + 0.06 * n1 + 0.03 * n2)
    seam = np.clip(np.minimum(frac, 1 - frac) * 60.0 / np.maximum(1.0 / depth, 1e-3) * 0.25, 0, 1)
    val = val * (0.80 + 0.20 * seam ** 0.6)
    col = np.array(base, np.float32)[None, None, :] / 255.0 * val[..., None]
    # sol cálido que entra de la derecha + brillo suave de la madera
    sun = np.clip(0.75 + 0.45 * (xx / W) - 0.25 * (1 - t), 0.5, 1.25)
    col = col * sun[..., None] * np.array([1.04, 0.99, 0.90], np.float32)
    wb = rgb_f(to_img(col).filter(ImageFilter.GaussianBlur(blur_far)))
    dof = np.maximum(np.clip(1 - t * 2.2, 0, 1) ** 1.3, np.clip((t - 0.7) * 2.5, 0, 1) * 0.7)[..., None]
    col = col * (1 - dof) + wb * dof
    m = np.clip((yy - y_top) / 2.0, 0, 1)[..., None]
    return a * (1 - m) + col * m


def scene_interior(seed, detalle=False):
    rnd = __import__("random").Random(seed)
    # pared cálida con luz de ventana (manchas diagonales suaves)
    a = vgrad([(0, (232, 216, 192)), (0.5, (240, 226, 202)), (0.7, (226, 206, 178))])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for k in range(3):
        x0 = W * (0.45 + 0.2 * k)
        band = np.exp(-(((xx - x0) + (yy - H * 0.3) * 0.55) / (55 + 25 * k)) ** 2)
        a = screen(a, band[..., None] * np.array([0.30, 0.24, 0.12], np.float32) * (0.8 - 0.2 * k))
    a = a * (0.80 + 0.28 * (xx / W))[..., None]               # luz desde la derecha
    # hojas de una planta grande, muy desenfocadas, arriba a la izquierda
    def leaves(d):
        for _ in range(14):
            x, y = rnd.uniform(-80, W * 0.35), rnd.uniform(-60, H * 0.45)
            L = rnd.uniform(120, 230)
            ang = rnd.uniform(0, 2 * math.pi)
            g = rnd.randint(60, 110)
            col = (int(g * 0.55), g, int(g * 0.40), 245)
            leaf_shape(d, x, y, L, ang, col, col, serr=False)
        for _ in range(4):                      # tallos
            x = rnd.uniform(0, W * 0.3)
            d.line([(x, H * 0.62), (x + rnd.uniform(-60, 60), -20)], fill=(70, 80, 50, 220), width=6)
    a = over(a, layer(leaves, 16 if not detalle else 26))
    # caja / libro desenfocado a la izquierda sobre la mesa
    def props(d):
        d.rectangle([W * 0.02, H * 0.56, W * 0.20, H * 0.68], fill=(214, 196, 168, 255))
        d.rectangle([W * 0.02, H * 0.56, W * 0.20, H * 0.575], fill=(236, 222, 198, 255))
        d.rectangle([W * 0.88, H * 0.50, W * 1.02, H * 0.68], fill=(70, 52, 40, 230))
    a = over(a, layer(props, 10 if not detalle else 22))
    y_top = H * 0.66
    a = table_horizontal(a, rnd, y_top, blur_far=4.0 if not detalle else 9.0)
    if detalle:
        a = rgb_f(to_img(a).filter(ImageFilter.GaussianBlur(5)))
    a = grade(a, warm=(1.03, 1.0, 0.94), sat=1.02)
    a = vignette(grain(a, rnd, 0.010), 0.28)
    return a, {"suelo": 0.80, "tema": "claro"}


SCENES = {
    "interior_sol": lambda: scene_interior(13),
    "interior_sol_detalle": lambda: scene_interior(13, detalle=True),
    "bosque_mesa": lambda: scene_forest_table(21),
    "bosque_mesa_dorado": lambda: scene_forest_table(57, warm=True),
    "hojas_bokeh": lambda: scene_leaves_bokeh(5),
    "musgo_oscuro": lambda: scene_dark_moss(9),
}


def main(out):
    os.makedirs(out, exist_ok=True)
    meta = {}
    for name, fn in SCENES.items():
        a, m = fn()
        p = os.path.join(out, name + ".jpg")
        to_img(a).save(p, quality=92, optimize=True)
        meta[name] = dict(m, blur=0)
        print(p)
    with open(os.path.join(out, "fondos.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    return meta


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "renders/fondos/naturaleza")
