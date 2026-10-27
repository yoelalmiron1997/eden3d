# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Generador de colecciones y exportación automática
==========================================================
OBJETIVO
    Leer una colección (.json), construir cada variante, validarla,
    descartar las inválidas y exportar STL + 3MF + JSON (+ 3DM y plato).

ENTRADAS
    colección JSON con:
      "base":     parámetros comunes (opcional)
      "variants": lista de {model_id, ...overrides}
      "sweep":    (opcional) barrido {"ruta.param": [valores, ...]}
                  ej. {"waves.0.count": [8,12,16], "waves.0.amp": [2,3,4]}
      "export":   {"stl":true,"3mf":true,"3dm":true,"saucer":true,
                   "sizes":["M"]}   (tamaños comerciales a escalar)
SALIDAS
    carpeta out/<model_id>/ con archivos + collection_report.csv

EJECUCIÓN
    python eden_batch.py colecciones/eden_wave_v1.json out
    (sin Rhino; dependencias opcionales: trimesh+scipy para validar,
     rhino3dm para .3dm)
"""
import sys
import os
import csv
import json
import copy
import itertools
import time

import eden_core as core

try:
    import eden_validate
except Exception:          # trimesh no instalado: se valida sólo con el motor
    eden_validate = None
try:
    import rhino3dm
except Exception:
    rhino3dm = None

# Tamaños comerciales (configurables). d = diámetro máximo, h = altura.
SIZES = {
    "Mini": {"d": 60, "h": 55},
    "S": {"d": 80, "h": 75},
    "M": {"d": 120, "h": 110},
    "L": {"d": 160, "h": 150},
    "XL": {"d": 200, "h": 190},
}
# Espesores por tamaño: más grande = pared y fondo más gruesos
WALL_BY_SIZE = {"Mini": 1.2, "S": 1.2, "M": 1.6, "L": 2.0, "XL": 2.4}


def set_path(d, path, value):
    keys = path.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur[int(k)] if k.isdigit() else cur[k]
    last = keys[-1]
    if last.isdigit():
        cur[int(last)] = value
    else:
        cur[last] = value


def scale_to_size(p, size):
    """Escala proporcionalmente perfil y ondas al tamaño comercial."""
    s = SIZES[size]
    q = copy.deepcopy(p)
    k_d = s["d"] / float(p["d_max"])
    k_h = s["h"] / float(p["height"])
    for key in ("d_base", "d_max", "d_mouth"):
        q[key] = round(p[key] * k_d, 2)
    q["height"] = s["h"]
    for w in q.get("waves", []):
        w["amp"] = round(w["amp"] * k_d, 3)
    q["fade_bottom"] = p.get("fade_bottom", 8) * k_h
    q["fade_top"] = p.get("fade_top", 8) * k_h
    q["wall"] = WALL_BY_SIZE[size]
    q["floor"] = max(1.6, WALL_BY_SIZE[size] * 1.5)
    q["drain_d"] = round(max(6.0, min(16.0, s["d"] * 0.09)), 1) if p.get("drain_d", 1) else 0
    q["model_id"] = "%s-%s" % (p["model_id"], size)
    return q


def expand(collection):
    base = collection.get("base", {})
    out = []
    for v in collection.get("variants", []):
        p = core.merge_params(base)
        for k, val in v.items():
            p[k] = copy.deepcopy(val)
        out.append(core.merge_params(p))
    sweep = collection.get("sweep")
    if sweep:
        keys = list(sweep.keys())
        for i, combo in enumerate(itertools.product(*[sweep[k] for k in keys])):
            p = core.merge_params(base)
            for k, val in zip(keys, combo):
                set_path(p, k, val)
            p["model_id"] = "%s-SW%03d" % (base.get("model_id", "EDEN-SWEEP"), i + 1)
            out.append(p)
    return out


def write_3dm(path, result, name):
    if rhino3dm is None:
        return False
    m = rhino3dm.Mesh()
    for x, y, z in result["vertices"]:
        m.Vertices.Add(x, y, z)
    for a, b, c in result["faces"]:
        m.Faces.AddFace(a, b, c)
    m.Normals.ComputeNormals()
    m.Compact()
    f = rhino3dm.File3dm()
    f.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Millimeters
    attr = rhino3dm.ObjectAttributes()
    attr.Name = name
    # parámetros guardados como User Text del objeto (Rhino: _GetUserText)
    for k, v in result["params"].items():
        attr.SetUserString("eden3d." + k, json.dumps(v, ensure_ascii=False))
    f.Objects.AddMesh(m, attr)
    f.Write(path, 8)
    return True


def export_one(p, out_dir, opts):
    res = core.build_pot(p)
    rep = res["report"]
    row = {"model_id": p["model_id"], "valid": rep.get("valid", False),
           "errors": " | ".join(rep["errors"]), "warnings": " | ".join(rep["warnings"])}
    if not rep.get("valid"):
        return row, None
    if eden_validate is not None and opts.get("validate", True):
        ext = eden_validate.check(res)
        rep["external_check"] = ext
        row.update({"watertight": ext["watertight"], "wall_min": ext["wall_measured_min_mm"],
                    "wall_p5": ext["wall_measured_p5_mm"]})
        if not ext["pass"]:
            row["valid"] = False
            row["errors"] = "Falló validación externa: %s" % json.dumps(ext)
            return row, None
    d = os.path.join(out_dir, p["model_id"])
    os.makedirs(d, exist_ok=True)
    base = os.path.join(d, p["model_id"])
    if opts.get("stl", True):
        core.write_stl(base + ".stl", res["vertices"], res["faces"], p["model_id"])
    if opts.get("3mf", True):
        core.write_3mf(base + ".3mf", res["vertices"], res["faces"], p["model_id"])
    if opts.get("3dm", True):
        write_3dm(base + ".3dm", res, p["model_id"])
    for part in res.get("parts") or []:          # plato oculto / inserto autorriego
        pres = dict(res, vertices=part["vertices"], faces=part["faces"],
                    params=part["params"], report=part["report"])
        if eden_validate is not None and opts.get("validate", True):
            pe = eden_validate.check(pres)
            part["report"]["external_check"] = pe
            if not pe["pass"]:
                row["valid"] = False
                row["errors"] = "Falló validación externa de %s: %s" % (part["name"], json.dumps(pe))
                return row, None
        pb = base + "-" + part["name"]
        nm = p["model_id"] + "-" + part["name"]
        if opts.get("stl", True):
            core.write_stl(pb + ".stl", part["vertices"], part["faces"], nm)
        if opts.get("3mf", True):
            core.write_3mf(pb + ".3mf", part["vertices"], part["faces"], nm)
        if opts.get("3dm", True):
            write_3dm(pb + ".3dm", pres, nm)
        rep[part["name"]] = {k: v for k, v in part["report"].items() if k not in ("errors",)}
    if res.get("parts"):
        row["parts"] = "+".join(pt["name"] for pt in res["parts"])
        row["assembly"] = json.dumps(rep.get("assembly"), ensure_ascii=False)
    if opts.get("saucer", False) and not res.get("parts"):
        sc = core.build_saucer(p)
        if sc["report"].get("valid"):
            core.write_stl(base + "-PLATO.stl", sc["vertices"], sc["faces"], p["model_id"] + "-PLATO")
            core.write_3mf(base + "-PLATO.3mf", sc["vertices"], sc["faces"], p["model_id"] + "-PLATO")
            rep["saucer"] = sc["report"]
        else:
            row["warnings"] += " | Plato inválido: %s" % sc["report"]["errors"]
    core.save_params(base + ".json", res)
    row.update({k: rep.get(k) for k in ("triangles", "volume_cm3", "mass_g_PLA_100pct",
                                         "soil_capacity_ml", "overhang_max_deg",
                                         "min_convex_radius_mm")})
    row["bbox_mm"] = "x".join(str(x) for x in rep["bbox_mm"])
    return row, res


def run(collection_path, out_dir):
    with open(collection_path, "r", encoding="utf-8") as fh:
        col = json.load(fh)
    opts = col.get("export", {})
    variants = expand(col)
    sizes = opts.get("sizes")
    if sizes:
        variants = [scale_to_size(v, s) for v in variants for s in sizes]
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for p in variants:
        t = time.time()
        try:
            row, _ = export_one(p, out_dir, opts)
        except Exception as ex:          # nunca cortar el lote por una variante
            row = {"model_id": p.get("model_id"), "valid": False, "errors": repr(ex)}
        row["seconds"] = round(time.time() - t, 1)
        rows.append(row)
        print("%-32s %s  %s" % (row["model_id"], "OK " if row["valid"] else "DESCARTADA",
                                 row.get("errors", "")[:120]))
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(os.path.join(out_dir, "collection_report.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    ok = sum(1 for r in rows if r["valid"])
    print("\n%d/%d variantes válidas -> %s" % (ok, len(rows), out_dir))
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
