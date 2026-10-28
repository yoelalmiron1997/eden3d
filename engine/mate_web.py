# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
MATE CON HUECO — Puente entre el motor y la página web (mate.html)
==================================================================
Corre dentro del navegador (Pyodide, en un Web Worker) y se testea con CPython
en tests/motor, igual que eden_web.py.

    info()                 -> modelos, insertos y límites para armar los controles
    build(opts)            -> piezas (bytes float32/uint32) + reporte
    export_stl(opts)       -> (nombre, bytes del STL del mate)
    export_3mf(opts)       -> (nombre, bytes del 3MF con licencia en los metadatos)
    analizar_stl(path)     -> qué entendió el motor de un STL de inserto subido

opts = {"tipo": "cohete", "inserto": "polimero" | "adaptador" | "ambos" | "propio",
        "stl_path": "/tmp/inserto.stl", "stl_nombre": "mi_vaso.stl", "holgura": 0.2,
        "pared": 3, "piso": 4, "autoajuste": True, "altura": 0, "diam_max": 0,
        "diam_boca": 0, "calidad": "preview"}
"""
import array
import os
import time

import mate_core as mc
from eden_core import write_3mf_multi, write_stl

LICENSE_NOTE = ("© Eden3D — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta, redistribución o modificación para vender.")


def info():
    return {
        "motor": mc.MATE_VERSION,
        "tipos": [{"id": t["id"], "nombre": t["nombre"], "altura": t["H"], "diam_max": t["Dmax"],
                   "diam_boca": t["Dboca"], "extras": sorted((t.get("extras") or {}).keys())}
                  for t in mc.TIPOS],
        "insertos": [{"id": k, "nombre": n} for k, n in mc.INSERTOS_WEB],
        "limites": dict(mc.LIMITES),
        "license": LICENSE_NOTE,
    }


def _opts(opts):
    o = dict(opts or {})
    path = o.pop("stl_path", None)
    if o.get("inserto") == "propio":
        if not path or not os.path.isfile(path):
            raise ValueError("Subí el STL de tu inserto")
        with open(path, "rb") as fh:
            o["stl_propio"] = fh.read()
    return o


def _pack(V, F):
    pos = array.array("f", [c for v in V for c in v])
    idx = array.array("I", [i for f in F for i in f])
    return pos.tobytes(), idx.tobytes()


def malla_inserto(res):
    """El inserto (sin holgura) en su lugar, para verlo dentro del hueco."""
    canon, _, _ = mc.hueco_de(res["opts"])
    H = res["params"]["H"]
    hundir = res["report"].get("hundir_mm", 0.0)
    rz = mc.colocar_hueco(mc.perfil_hueco(canon, 0.0, hundir, 0.0), H, hundir)
    rows = mc._limpiar_rz([q for q in rz[1:-1]])
    M = 96
    V, F = [], []
    cs = [(mc.math.cos(mc.TAU * k / M), mc.math.sin(mc.TAU * k / M)) for k in range(M)]
    V.append((0.0, 0.0, rz[0][1]))
    cadena = [0]
    for r, z in rows:
        i0 = len(V)
        V.extend((r * c, r * s, z) for c, s in cs)
        cadena.append(list(range(i0, i0 + M)))
    V.append((0.0, 0.0, rz[-1][1]))
    cadena.append(len(V) - 1)
    for A, B in zip(cadena, cadena[1:]):
        mc._coser(F, A, B)
    if mc.mesh_volume(V, F) < 0:
        F = [(a, c, b) for a, b, c in F]
    return V, F


def _resultado(opts):
    o = _opts(opts)
    res = mc.build_mate(o)
    res["opts"] = o
    return res


def build(opts):
    t0 = time.time()
    try:
        res = _resultado(opts)
    except ValueError as e:                 # p. ej. un STL propio que no sirve
        return {"summary": {"valid": False, "errors": [str(e)], "warnings": [],
                            "sku": "—", "seconds": round(time.time() - t0, 2)}, "parts": []}
    rep = dict(res["report"])
    parts = []
    if rep["valid"]:
        pos, idx = _pack(res["V"], res["F"])
        parts.append({"name": "MACETA", "positions": pos, "indices": idx,
                      "vertices": len(res["V"]), "triangles": len(res["F"])})
        Vi, Fi = malla_inserto(res)
        pos, idx = _pack(Vi, Fi)
        parts.append({"name": "INSERTO", "positions": pos, "indices": idx,
                      "vertices": len(Vi), "triangles": len(Fi)})
    rep["seconds"] = round(time.time() - t0, 2)
    return {"summary": rep, "parts": parts}


def _nombre(rep, ext):
    return "%s.%s" % (rep["sku"], ext)


def export_stl(opts):
    o = dict(opts or {})
    o["calidad"] = "normal"
    res = _resultado(o)
    rep = res["report"]
    if not rep["valid"]:
        raise ValueError("; ".join(rep["errors"]) or "modelo inválido")
    name = _nombre(rep, "stl")
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
    write_stl(path, res["V"], res["F"], name="Eden3D Mate (c) Yoel Almiron - uso personal")
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(path)
    except OSError:
        pass
    return name, data


def export_3mf(opts):
    o = dict(opts or {})
    o["calidad"] = "normal"
    res = _resultado(o)
    rep = res["report"]
    if not rep["valid"]:
        raise ValueError("; ".join(rep["errors"]) or "modelo inválido")
    meta = {"Title": rep["sku"], "Designer": "Eden3D",
            "Copyright": "© Eden3D — Yoel Almirón. Todos los derechos reservados.",
            "LicenseTerms": LICENSE_NOTE,
            "Description": "Mate %s con hueco para %s · motor mate %s"
                           % (rep["nombre"], " + ".join(rep["insertos"]), mc.MATE_VERSION),
            "CreationDate": time.strftime("%Y-%m-%d")}
    name = _nombre(rep, "3mf")
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
    write_3mf_multi(path, [(rep["sku"], res["V"], res["F"])], meta)
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(path)
    except OSError:
        pass
    return name, data


def analizar_stl(path):
    """Para la web: valida el STL subido antes de calcular."""
    try:
        with open(path, "rb") as fh:
            canon, inf = mc.perfil_desde_stl(mc.leer_stl(fh.read()))
        return {"ok": True, "info": inf, "error": ""}
    except Exception as e:   # el mensaje le llega a la persona tal cual
        return {"ok": False, "info": None, "error": str(e)}
