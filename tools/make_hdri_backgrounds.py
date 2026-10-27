# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Fondo panorámico del escenario Jardín a partir de un HDRI de Poly Haven (CC0).

    python tools/make_hdri_backgrounds.py chinese_garden_2k.hdr web/assets/escenarios

Fuente: "Chinese Garden" de Poly Haven (https://polyhaven.com/a/chinese_garden),
licencia CC0. Copia usada: https://raw.githubusercontent.com/gkjohnson/3d-demo-data/main/hdri/chinese_garden_2k.hdr
Se convierte a JPEG (tono ACES) para que pese poco en la web, y se calcula la
dirección del sol para alinear la luz del visor con la foto.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image


def read_hdr(path):
    """Radiance .hdr (RLE nuevo) -> float32 HxWx3."""
    d = open(path, "rb").read()
    i = 0
    while True:
        j = d.index(b"\n", i)
        line = d[i:j]
        i = j + 1
        if line.startswith((b"-Y", b"+Y")):
            p = line.split()
            H, W = int(p[1]), int(p[3])
            break
    out = np.zeros((H, W, 4), np.uint8)
    b = np.frombuffer(d, np.uint8)
    pos = i
    for y in range(H):
        assert b[pos] == 2 and b[pos + 1] == 2, "formato RLE no soportado"
        pos += 4
        for c in range(4):
            x = 0
            while x < W:
                n = int(b[pos])
                pos += 1
                if n > 128:
                    n -= 128
                    out[y, x:x + n, c] = b[pos]
                    pos += 1
                else:
                    out[y, x:x + n, c] = b[pos:pos + n]
                    pos += n
                x += n
    e = out[..., 3].astype(np.int32)
    f = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    return out[..., :3].astype(np.float32) * f[..., None]


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def main(src, out_dir, name="jardin_chino", exposure=1.15):
    hdr = read_hdr(src)
    H, W, _ = hdr.shape
    lum = hdr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    y, x = np.unravel_index(np.argmax(lum), lum.shape)
    # equirectangular: u -> azimut, v -> elevación (convención de three.js)
    az = (x / W) * 360.0
    el = 90.0 - (y / H) * 180.0
    ldr = aces(hdr * exposure / max(float(np.median(lum)) * 3.0, 1e-6))
    img = (ldr ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
    os.makedirs(out_dir, exist_ok=True)
    Image.fromarray(img).save(os.path.join(out_dir, name + ".jpg"), quality=86, optimize=True,
                              progressive=True)
    meta = {"fuente": "Poly Haven — Chinese Garden (CC0)", "url": "https://polyhaven.com/a/chinese_garden",
            "sol_u": round(x / W, 4), "sol_v": round(y / H, 4), "sol_elev_deg": round(el, 1)}
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(meta)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
