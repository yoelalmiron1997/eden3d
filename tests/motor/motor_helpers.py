# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Utilidades comunes de los tests de Eden3D.
Correr:  python -m pytest -q tests/motor            (rápido, ~1 min)
         EDEN3D_TODO=1 python -m pytest -q tests/motor   (los 17 diseños)"""
import json
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "engine")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import eden_catalog as ec  # noqa: E402
import eden_core as core  # noqa: E402

CAT_PATH = os.path.join(ROOT, "colecciones", "catalogo_eden3d.json")
_CACHE = {}


def catalog():
    if "cat" not in _CACHE:
        _CACHE["cat"] = ec.load_catalog(CAT_PATH)
    return _CACHE["cat"]


def design_codes():
    codes = [d["code"] for d in catalog()["designs"]]
    if os.environ.get("EDEN3D_TODO"):
        return codes
    return ["ROMBO", "ACANALADO", "PRISMA", "TORSION"]   # muestra representativa


def build(code, size="S", mode="screw_dish_sw", drain="leaf", quality="preview", ovr=None):
    key = (code, size, mode, drain, quality, json.dumps(ovr or {}, sort_keys=True))
    if key not in _CACHE:
        cat = catalog()
        d = ec.find_design(cat, code)
        p = ec.design_params(cat, d, size, mode, drain, quality, ovr or {})
        _CACHE[key] = core.build_pot(p)
    return _CACHE[key]


def assembled_meshes(res):
    """(maceta, plato) como trimesh, en su posición de uso (maceta enroscada)."""
    import trimesh
    A = res["report"]["assembly"]
    lift = A["pot_bottom_z_mm"] - A.get("pot_drop_on_seat_mm", 0.0)
    pot = trimesh.Trimesh(res["vertices"], res["faces"], process=True)
    pot.apply_translation([0, 0, lift])
    part = res["parts"][0]
    dish = trimesh.Trimesh(part["vertices"], part["faces"], process=True)
    return pot, dish


