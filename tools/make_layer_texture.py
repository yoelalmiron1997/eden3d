# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Textura de relieve (bump) de las capas de impresión FDM: 16 capas por mosaico.
USO: python tools/make_layer_texture.py renders/texturas/capas_fdm2.png"""
import sys
import os
import numpy as np
from PIL import Image, ImageFilter

W_, H_, N = 512, 512, 16


def main(out):
    rng = np.random.default_rng(5)
    y = (np.arange(H_) + 0.5) / H_ * N
    frac = y - np.floor(y)
    x = frac * 2 - 1
    bead = np.sqrt(np.clip(1 - x ** 2, 0, 1)) ** 0.6           # cordón redondeado
    h = np.repeat(bead[:, None], W_, axis=1)
    # variación sutil de cada capa y "fibras" a lo largo
    line = np.floor(y).astype(int)
    jit = rng.normal(0, 0.05, N)[line][:, None]
    fib = rng.normal(0, 1, (H_, W_ // 32))
    fib = np.asarray(Image.fromarray(((fib - fib.min()) / np.ptp(fib) * 255).astype(np.uint8))
                     .resize((W_, H_), Image.BICUBIC), np.float32) / 255.0 - 0.5
    h = h * (0.92 + jit) + 0.06 * fib
    h = (h - h.min()) / np.ptp(h)
    # rango acotado: relieve sutil (y si el render la usara como color, casi blanco)
    h = 0.90 + 0.10 * h
    img = Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    img.save(out)
    return out


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "renders/texturas/capas_fdm2.png"))
