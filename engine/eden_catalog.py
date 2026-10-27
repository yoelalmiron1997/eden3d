# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Catálogo, nomenclatura y exportación simple
====================================================
Un diseño del catálogo + modo + drenaje + tamaño = un SKU:

    Eden3D-<DISEÑO>-<TAMAÑO>-<MODO>-<DRENAJE>
    p. ej. Eden3D-ROMBO-M-AUTORRIEGO-HOJAS

Cada SKU se exporta en  exportadas/Eden3D-<DISEÑO>/ :
    <SKU>.3mf           TODAS las piezas en un solo archivo (abrir y laminar)
    <SKU>_MACETA.stl    cada pieza suelta, apoyada en z=0
    <SKU>_PLATO.stl
    <SKU>.json          parámetros + reporte (reproduce el modelo exacto)
y se agrega/actualiza una fila en exportadas/Eden3D_indice.csv.
Corre igual en Rhino 8 (Grasshopper) y en Python normal.
"""
import os
import csv
import json
import copy
import time

import eden_core as core

MODES = [  # (código interno, etiqueta en Grasshopper, código del SKU)
    ("screw_dish_sw", "Autorriego con rosca", "AUTORRIEGO"),
    ("screw_dish", "Plato inclinado con rosca", "ROSCA"),
    ("saucer", "Plato apoyado", "PLATO"),
    ("pot", "Sin plato", "SOLA"),
    ("hidden_tray", "Plato oculto (encastre)", "OCULTO"),
    ("screw_tray", "Plato oculto con rosca", "ROSCA-OCULTA"),
    ("self_watering", "Inserto de autorriego", "INSERTO"),
]
DRAINS = [  # (código interno, etiqueta, código SKU, parámetros)
    ("leaf", "Hojas", "HOJAS", {"drain_pattern": "ring", "drain_shape": "leaf", "drain_d": 10.0,
                                "drain_count": 6, "drain_center": True, "drain_leaf_vein": 2.0}),
    ("circle", "Circular", "CIRCULAR", {"drain_pattern": "ring", "drain_shape": "circle",
                                        "drain_d": 7.0, "drain_count": 6, "drain_center": True}),
    ("slot", "Ranuras", "RANURAS", {"drain_pattern": "ring", "drain_shape": "slot", "drain_d": 5.0,
                                    "drain_count": 8, "drain_center": True}),
    ("none", "Sin drenaje", "CERRADA", {"drain_pattern": "none", "drain_d": 0.0}),
]
# tamaños: M = tamaño original del diseño; el resto escala parejo (sin deformar)
SIZES = {"Mini": 65.0, "S": 90.0, "M": None, "L": 150.0, "XL": 185.0}
WALL_BY_SIZE = {"Mini": 1.2, "S": 1.2, "M": None, "L": 2.0, "XL": 2.4}
PART_FILE = {"PLATO": "PLATO", "PLATO-INCLINADO": "PLATO", "PLATO-AUTORRIEGO": "PLATO",
             "PLATO-OCULTO": "PLATO", "PLATO-ROSCA": "PLATO", "INSERTO": "INSERTO"}


def mode_code(mode):
    for m, _, c in MODES:
        if m == mode:
            return c
    return mode.upper()


def drain_code(d):
    for k, _, c, _ in DRAINS:
        if k == d:
            return c
    return d.upper()


def label_to_mode(label):
    s = str(label or "").strip()
    for m, lab, c in MODES:
        if s in (m, lab, c):
            return m
    return None


def label_to_drain(label):
    s = str(label or "").strip()
    for k, lab, c, _ in DRAINS:
        if s.lower() in (k, lab.lower(), c.lower()):
            return k
    return None


def load_catalog(path):
    with open(core.clean_path(path), "r", encoding="utf-8") as fh:
        cat = json.load(fh)
    codes = [d["code"] for d in cat.get("designs", [])]
    if len(set(codes)) != len(codes):
        raise ValueError("Hay códigos de diseño repetidos en el catálogo")
    return cat


def find_design(cat, code_or_name):
    s = str(code_or_name or "").strip()
    for d in cat["designs"]:
        if s in (d["code"], d.get("name"), "%s · %s" % (d["code"], d.get("name", ""))):
            return d
    return cat["designs"][0]


def sku(code, size, mode, drain, brand="Eden3D"):
    return "%s-%s-%s-%s-%s" % (brand, code, size, mode_code(mode), drain_code(drain))


def scale_params(p, size):
    """Escala pareja (diámetros, alto, relieves y pasos) al tamaño comercial."""
    target = SIZES.get(size)
    if not target:
        return p
    q = copy.deepcopy(p)
    k = target / float(p["d_max"])
    for key in ("d_base", "d_max", "d_mouth", "height", "fade_bottom", "fade_top",
                "tex_pitch", "tex_scale", "tex_amp", "lowpoly_jitter"):
        if key in q and q[key] is not None:
            q[key] = round(float(q[key]) * k, 3)
    for w in q.get("waves", []):
        w["amp"] = round(float(w["amp"]) * k, 3)
    if WALL_BY_SIZE.get(size):
        q["wall"] = WALL_BY_SIZE[size]
        q["floor"] = max(1.6, WALL_BY_SIZE[size] * 1.5)
    if "drain_d" in q:
        q["drain_d"] = round(max(5.0, min(14.0, float(q["drain_d"]) * k)), 1)
    return q


OVR_CODE = {"tex_count": "N", "tex_pitch": "P", "tex_amp": "A", "tex_duty": "D", "tex_wob": "W",
            "ondas": "O", "amp_ondas": "H"}


def override_tag(ov):
    """Sufijo corto para el nombre cuando se tocaron los sliders del patrón."""
    if not ov:
        return ""
    parts = []
    for k in sorted(ov):
        v = ov[k]
        v = ("%d" % v) if float(v).is_integer() else ("%g" % v)
        parts.append(OVR_CODE.get(k, k[:2].upper()) + v)
    return "-" + "".join(parts).replace(".", "")


def apply_overrides(p, ov):
    """Ajustes del patrón (sliders). 'ondas' y 'amp_ondas' tocan la 1.ª onda radial."""
    for k, v in (ov or {}).items():
        if k in ("ondas", "amp_ondas"):
            w = [x for x in p.get("waves", []) if x.get("type", "radial") == "radial"]
            if w:
                w[0]["count" if k == "ondas" else "amp"] = int(v) if k == "ondas" else float(v)
            continue
        p[k] = v
    return p


def design_params(cat, design, size="M", mode="screw_dish_sw", drain="leaf", quality="normal",
                  overrides=None):
    p = dict(cat.get("base", {}))
    p.update(copy.deepcopy(design["params"]))
    apply_overrides(p, overrides)
    for k, _, _, extra in DRAINS:
        if k == drain:
            p.update(extra)
    p["mode"] = mode
    p["quality"] = quality
    p["brand"] = cat.get("brand", "Eden3D")
    p = scale_params(p, size)
    p["model_id"] = sku(design["code"], size, mode, drain, p["brand"]) + override_tag(overrides)
    if overrides:
        p["overrides"] = dict(overrides)
    p["design_code"] = design["code"]
    p["design_name"] = design.get("name", design["code"])
    return p


def export_matrix(cat, mode_sel=None, drain_sel=None, size_sel=None):
    """Combinaciones a exportar: lo elegido, o la matriz del catálogo ("todos")."""
    ex = cat.get("export", {})
    modes = [mode_sel] if mode_sel else ex.get("modes", ["saucer", "screw_dish_sw"])
    drains = [drain_sel] if drain_sel else ex.get("drains", ["leaf", "circle"])
    sizes = [size_sel] if size_sel else ex.get("sizes", ["M"])
    return [(m, d, s) for s in sizes for m in modes for d in drains]


def pieces(res):
    """[(nombre de archivo, vértices, caras)] apoyadas en z=0."""
    out = [("MACETA", res["vertices"], res["faces"])]
    for pt in res.get("parts") or []:
        out.append((PART_FILE.get(pt["name"], pt["name"]), pt["vertices"], pt["faces"]))
    return out


def export_set(res, out_root, write_stl=True):
    """Escribe un SKU completo. Devuelve la lista de archivos."""
    p = res["params"]
    code = p.get("design_code", "DISENO")
    brand = p.get("brand", "Eden3D") or "Eden3D"
    folder = os.path.join(out_root, "%s-%s" % (brand, code))
    os.makedirs(folder, exist_ok=True)
    base = os.path.join(folder, p["model_id"])
    files = []
    pcs = pieces(res)
    meta = {"Title": p["model_id"], "Designer": brand, "Copyright": "© %s" % brand,
            "Description": "%s · %s · motor %s" % (p.get("design_name", code),
                                                   mode_code(p.get("mode", "pot")),
                                                   core.ENGINE_VERSION),
            "CreationDate": time.strftime("%Y-%m-%d")}
    core.write_3mf_multi(base + ".3mf", [("%s_%s" % (p["model_id"], nm), V, F)
                                         for nm, V, F in pcs], meta)
    files.append(base + ".3mf")
    if write_stl:
        for nm, V, F in pcs:
            path = "%s_%s.stl" % (base, nm)
            core.write_stl(path, V, F, "%s %s_%s" % (brand, p["model_id"], nm))
            files.append(path)
    core.save_params(base + ".json", res)
    files.append(base + ".json")
    return files


INDEX_COLS = ["sku", "diseno", "tamano", "modo", "drenaje", "ajustes", "valido", "g_maceta", "g_plato",
              "ml_tierra", "ml_agua", "alto_mm", "diametro_mm", "marca", "fecha", "errores"]


def index_row(res):
    p, rep = res["params"], res["report"]
    parts = res.get("parts") or []
    A = rep.get("assembly") or {}
    return {"sku": p["model_id"], "diseno": p.get("design_code"),
            "tamano": p["model_id"].split("-")[2] if p["model_id"].count("-") >= 4 else "",
            "ajustes": override_tag(p.get("overrides")).lstrip("-"),
            "modo": mode_code(p.get("mode", "pot")),
            "drenaje": drain_code(p.get("drain_shape", "") if p.get("drain_pattern") != "none"
                                  else "none"),
            "valido": "SI" if rep.get("valid") else "NO",
            "g_maceta": rep.get("mass_g_PLA_100pct"),
            "g_plato": parts[0]["report"].get("mass_g_PLA_100pct") if parts else "",
            "ml_tierra": rep.get("soil_capacity_ml"),
            "ml_agua": A.get("water_reservoir_ml", ""),
            "alto_mm": (rep.get("bbox_mm") or ["", "", ""])[2],
            "diametro_mm": (rep.get("bbox_mm") or [""])[0],
            "marca": (rep.get("brand") or {}).get("text", ""),
            "fecha": time.strftime("%Y-%m-%d %H:%M"),
            "errores": " | ".join(rep.get("errors", []))[:300]}


def update_index(out_root, rows):
    """Agrega o reemplaza filas (por SKU) en exportadas/Eden3D_indice.csv."""
    path = os.path.join(out_root, "Eden3D_indice.csv")
    old = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                old[r.get("sku")] = r
    for r in rows:
        old[r["sku"]] = r
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_COLS, extrasaction="ignore")
        w.writeheader()
        for k in sorted(old):
            w.writerow(old[k])
    return path


def run(cat_path, out_root, codes=None, mode=None, drain=None, size=None, log=print,
        overrides=None):
    """Exporta diseños del catálogo (todos o `codes`) según la matriz."""
    cat = load_catalog(cat_path)
    rows, ok = [], 0
    for d in cat["designs"]:
        if codes and d["code"] not in codes:
            continue
        for m, dr, s in export_matrix(cat, mode, drain, size):
            p = design_params(cat, d, s, m, dr, "normal", overrides)
            t = time.time()
            try:
                res = core.build_pot(p)
            except Exception as ex:
                res = {"params": p, "report": {"valid": False, "errors": [repr(ex)]}, "parts": []}
            if res["report"].get("valid"):
                export_set(res, out_root, write_stl=bool(cat.get("export", {}).get("stl", False)))
                ok += 1
                log("OK         %-44s %5.1fs" % (p["model_id"], time.time() - t))
            else:
                log("DESCARTADO %-44s %s" % (p["model_id"], "; ".join(res["report"]["errors"])[:140]))
            rows.append(index_row(res))
    update_index(out_root, rows)
    log("%d/%d exportados en %s" % (ok, len(rows), out_root))
    return rows


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("uso: python eden_catalog.py colecciones/catalogo_eden3d.json exportadas [CODIGO ...]")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
