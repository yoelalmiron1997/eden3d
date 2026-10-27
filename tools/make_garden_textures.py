# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Texturas de la mesa de madera del escenario Jardín (todo por código, sin fotos):
color, relieve (normal map) y rugosidad de tablas de madera envejecida al aire libre.

    python tools/make_garden_textures.py web/assets/escenarios
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

S = 1024
RNG = np.random.default_rng(11)


def noise(h, w, scale, octaves=5, aniso=(1.0, 1.0)):
    """Ruido fractal (suma de ruido de valor interpolado), aniso estira las vetas."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh = max(2, int(h / scale * aniso[0] * 2 ** o))
        gw = max(2, int(w / scale * aniso[1] * 2 ** o))
        g = RNG.random((gh, gw)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(img, np.float32) / 255.0)
        tot += amp
        amp *= 0.5
    return out / tot


def main(out):
    os.makedirs(out, exist_ok=True)
    n_planks = 6
    ph = S // n_planks
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    plank = np.minimum((yy // ph).astype(int), n_planks - 1)
    v = (yy % ph) / ph                       # posición dentro de la tabla
    # vetas: ruido muy estirado a lo largo (x) + anillos que ondulan
    grain = noise(S, S, 64, 6, aniso=(6.0, 0.25))
    rings = np.sin((v * 5 + noise(S, S, 300, 4, aniso=(1.0, 0.4)) * 9 + plank * 1.7) * np.pi * 2) * 0.5 + 0.5
    fibers = noise(S, S, 3, 3, aniso=(10.0, 0.04))
    wood = 0.45 * grain + 0.3 * rings ** 4 + 0.25 * fibers
    # nudos
    knots = np.zeros((S, S), np.float32)
    for _ in range(7):
        cx, cy = RNG.uniform(0, S), RNG.integers(0, n_planks) * ph + RNG.uniform(0.25, 0.75) * ph
        r = RNG.uniform(6, 14)
        d = np.sqrt(((xx - cx) / 2.2) ** 2 + (yy - cy) ** 2)
        knots = np.maximum(knots, np.clip(1 - d / (r * 2.2), 0, 1) ** 1.5)
    wood = np.clip(wood + knots * 0.8, 0, 1)
    # cada tabla con su tono; desgaste gris (madera al sol) en manchas
    tint = RNG.uniform(0.85, 1.1, n_planks)[plank]
    weather = np.clip(noise(S, S, 180, 4) * 1.6 - 0.45, 0, 1)
    base = np.array([150, 104, 66], np.float32) / 255
    dark = np.array([88, 56, 34], np.float32) / 255
    grey = np.array([150, 140, 128], np.float32) / 255
    col = base[None, None] * (1 - wood[..., None]) + dark[None, None] * wood[..., None]
    col = col * tint[..., None]
    col = col * (1 - 0.55 * weather[..., None]) + grey[None, None] * 0.55 * weather[..., None]
    # juntas entre tablas y bordes gastados
    edge = np.minimum(v, 1 - v) * ph
    gap = np.clip((edge - 1.5) / 4.0, 0, 1)
    col *= (0.12 + 0.88 * gap[..., None] ** 0.6)
    # clavos
    for p in range(n_planks):
        for x in (S * 0.08, S * 0.92):
            for k in (0.3, 0.7):
                d = np.hypot(xx - x, yy - (p + k) * ph)
                col *= (1 - 0.6 * np.clip(1 - d / 4.0, 0, 1))[..., None]
    col = np.clip(col * (0.92 + 0.16 * noise(S, S, 8, 2)[..., None]), 0, 1)
    Image.fromarray((col ** (1 / 1.0) * 255).astype(np.uint8)).save(os.path.join(out, "madera_color.jpg"), quality=88)
    # relieve -> normal map
    height = 0.6 * grain + 0.25 * rings + 0.3 * knots
    height = height * gap - (1 - gap) * 1.5
    gy, gx = np.gradient(height * 6.0)
    nrm = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, "madera_normal.jpg"), quality=90)
    rough = np.clip(0.62 + 0.25 * weather + 0.1 * grain - 0.15 * (1 - gap), 0, 1)
    Image.fromarray((rough * 255).astype(np.uint8)).save(os.path.join(out, "madera_rugosidad.jpg"), quality=88)
    print("texturas en", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "web/assets/escenarios")
