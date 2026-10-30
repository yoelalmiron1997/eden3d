# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
Tipografías para el relieve de texto del mate.

"eden" es la fuente de trazos propia (eden_font); las demás son tipografías libres
convertidas a contornos por tools/fuentes.py (ver fuentes/LICENCIAS.md). Los contornos se
leen de fuentes/<id>.json al lado de este archivo (en la web, el worker los baja sólo
cuando se eligen).
"""
import json
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes")

FUENTES = [
    ("eden", "Eden (trazo)"),
    ("archivo_black", "Archivo Black (bloque)"),
    ("anton", "Anton (condensada)"),
    ("fredoka", "Fredoka (redondeada)"),
    ("lilita_one", "Lilita One (gruesa)"),
    ("russo_one", "Russo One (deportiva)"),
    ("bungee", "Bungee (cartel)"),
    ("luckiest_guy", "Luckiest Guy (cómic)"),
    ("pacifico", "Pacifico (cursiva)"),
]
IDS = [f for f, _ in FUENTES]
DEFECTO = "archivo_black"
MAX_LEN = 30
_CACHE = {}


def ruta(fid):
    return os.path.join(DIR, fid + ".json")


def cargar(fid):
    if fid not in IDS or fid == "eden":
        raise ValueError("Tipografía desconocida: %s" % fid)
    if fid not in _CACHE:
        try:
            with open(ruta(fid), encoding="utf-8") as fh:
                _CACHE[fid] = json.load(fh)
        except (IOError, OSError):
            raise ValueError("No se pudo cargar la tipografía %s" % fid)
    return _CACHE[fid]


def limpiar(texto, fid):
    """(texto limpio, error o None) para una tipografía de contornos."""
    t = " ".join(str(texto or "").split())
    if not t:
        return "", None
    if len(t) > MAX_LEN:
        return t, "El texto puede tener hasta %d caracteres." % MAX_LEN
    g = cargar(fid)["glifos"]
    bad = sorted({c for c in t if c not in g})
    if bad:
        return t, "Estos caracteres no están en la tipografía: %s" % " ".join(bad)
    return t, None


def contornos(texto, fid, espaciado=0.0):
    """Polígonos (em = 1000, y hacia arriba) del texto en la tipografía `fid`."""
    f = cargar(fid)
    g, kern = f["glifos"], f.get("kern", {})
    polys, x, prev = [], 0.0, None
    extra = espaciado * 1000.0
    for ch in texto:
        if prev is not None:
            x += kern.get(prev + ch, 0) + extra
        gl = g[ch]
        for c in gl["c"]:
            polys.append([(x + c[i], float(c[i + 1])) for i in range(0, len(c), 2)])
        x += gl["a"]
        prev = ch
    return polys
