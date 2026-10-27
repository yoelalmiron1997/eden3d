# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Componente Grasshopper (Rhino 8, "Python 3 Script")
=============================================================
OBJETIVO
    Usar el motor eden_core.py dentro de Grasshopper: sliders en vivo,
    malla en el viewport, reporte de validación y exportación con un botón.

CÓMO ARMARLO (una vez)
    1. Grasshopper > Maths > Script > "Python 3 Script".
    2. Doble clic > pegar este código.
    3. Zoom sobre el componente, usar (+) para crear ESTAS entradas
       (nombre exacto, Type hint indicado, Item Access):
         lib_path   str    carpeta que contiene eden_core.py
         preset     str    ruta a un .json de colección/variante (opcional)
         height     float  altura mm
         d_max      float  diámetro máximo mm
         wall       float  espesor de pared mm
         waves      int    cantidad de ondas (onda 1)
         amp        float  amplitud mm (onda 1)
         twist      float  vueltas de torsión (onda 1)
         sides      int    lados del polígono (0 = circular)
         quality    str    preview | normal | fine
         saucer     bool   generar plato
         out_dir    str    carpeta de exportación (opcional: por defecto
                           MACETAS_EDEN3D/exportadas)
         export     bool   conectar un Button: exporta al pulsar (siempre en
                           calidad normal, aunque estés en vista previa)
         mode       str    pot | hidden_tray | screw_tray | self_watering
         collection str    (opcional) .json con MUCHOS modelos: `export`
                           los exporta TODOS; el slider `index` elige cuál ver
         index      int    (opcional) slider 0..N-1 para recorrer la colección
       Además, cualquier parámetro del motor puede ser una entrada con su
       mismo nombre, p. ej. drain_pattern (none|single|ring|grid),
       drain_shape (circle|slot), drain_d, drain_count, drain_rings,
       drain_center, d_base, d_mouth, belly, floor.
       y ESTAS salidas: pot, plate, report, params_json
       (plate muestra el plato suelto, el plato oculto o el inserto de
        autorriego según el parámetro `mode`, ya armado en su lugar)
    4. Conectar sliders. Las entradas sin conectar usan el preset/defaults.

NOTAS DE API (RhinoCommon) usadas aquí — todas estándar en Rhino 8:
    Rhino.Geometry.Mesh(), Mesh.Vertices.Add(x,y,z), Mesh.Faces.AddFace(a,b,c),
    Mesh.Normals.ComputeNormals(), Mesh.Compact(), Mesh.IsClosed,
    Mesh.IsValidWithLog() (en Python devuelve (bool, str)).
    Si alguna difiere en tu build, verificala con el Script Editor
    (autocompletado) o en https://developer.rhino3d.com/api/rhinocommon/
"""
import sys
import os
import json
import importlib

import Rhino.Geometry as rg

pot = plate = None
report = ""
params_json = ""


def to_rhino_mesh(res):
    m = rg.Mesh()
    for x, y, z in res["vertices"]:
        m.Vertices.Add(x, y, z)
    for a, b, c in res["faces"]:
        m.Faces.AddFace(a, b, c)
    m.Normals.ComputeNormals()
    m.Compact()
    return m


def _input_names():
    """Nombres de las entradas REALES del componente. En Grasshopper las
    variables del script quedan vivas entre corridas: sin este filtro una
    variable interna con el nombre de un parámetro (p. ej. 'mode') se
    confundiría con una entrada."""
    try:
        return set(p.Name for p in ghenv.Component.Params.Input)   # noqa: F821
    except Exception:
        return None                       # fuera de Grasshopper (pruebas)


_INPUTS = _input_names()


def opt(name):
    """Valor de una entrada si existe y está conectada; si no, None."""
    if _INPUTS is not None and name not in _INPUTS:
        return None
    return globals().get(name, None)


def resolve_lib(path):
    """Acepta la carpeta del motor, una subcarpeta (grasshopper) o el propio
    eden_core.py; limpia espacios, comillas y saltos de línea del Panel.
    Si no lo encuentra, devuelve un diagnóstico de lo que Rhino ve en disco."""
    raw = str(path or "")
    p = raw.replace("\r", "").replace("\n", "").strip().strip('"').strip("'").strip()
    p = os.path.normpath(os.path.expandvars(os.path.expanduser(p))) if p else p
    if p.lower().endswith(".py"):
        p = os.path.dirname(p)
    cands = [p, os.path.dirname(p), os.path.join(p, "eden3d")]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "eden_core.py")):
            return c, None
    # diagnóstico: subir hasta encontrar una carpeta existente y listarla
    diag = ["Texto recibido: %r" % raw]
    probe = p
    while probe and not os.path.isdir(probe) and os.path.dirname(probe) != probe:
        probe = os.path.dirname(probe)
    if probe and os.path.isdir(probe):
        try:
            diag.append("Última carpeta que Rhino SÍ ve: %s" % probe)
            diag.append("Contenido: %s" % ", ".join(sorted(os.listdir(probe))[:40]))
        except Exception as e:
            diag.append("No se pudo listar %s: %s" % (probe, e))
    return None, "\n".join(diag)


try:
    lib_path, diag = resolve_lib(lib_path)
    if not lib_path:
        raise IOError("No encuentro eden_core.py.\n" + diag)
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    import eden_floor
    import eden_core
    importlib.reload(eden_floor)         # recoge cambios del motor sin reiniciar Rhino
    importlib.reload(eden_core)

    # 0) COLECCIÓN: un .json con muchos modelos. El slider `index` elige cuál
    #    se ve; el botón `export` los exporta TODOS (calidad normal).
    #    Con colección, los sliders de forma NO se aplican: lo que ves es
    #    exactamente lo que se exporta (para cambiar algo, editá el .json).
    col_lines = []
    col_P = None
    if opt("collection"):
        import eden_batch
        importlib.reload(eden_batch)
        cpath = eden_core.clean_path(opt("collection"))
        with open(cpath, "r", encoding="utf-8") as fh:
            col = json.load(fh)
        col_opts = col.get("export") or {}
        variants = eden_batch.expand(col)
        if col_opts.get("sizes"):
            variants = [eden_batch.scale_to_size(v, s) for v in variants for s in col_opts["sizes"]]
        if not variants:
            raise ValueError("La colección no tiene variantes: " + cpath)
        idx = int(round(float(opt("index") or 0))) % len(variants)
        col_P = variants[idx]
        col_lines.append("COLECCIÓN: %s  (%d modelos)" % (col.get("collection", os.path.basename(cpath)),
                                                         len(variants)))
        col_lines.append("Viendo %d/%d (index=%d): %s" % (idx + 1, len(variants), idx, col_P["model_id"]))
        if opt("export"):
            od = eden_core.clean_path(opt("out_dir") or "") or \
                os.path.join(os.path.dirname(os.path.dirname(lib_path)), "exportadas")
            ok_n = 0
            for v in variants:
                vv = dict(v, quality="normal")
                try:
                    r_ = eden_core.build_pot(vv)
                    if not r_["report"].get("valid"):
                        col_lines.append("  DESCARTADA %s: %s" % (v["model_id"],
                                         "; ".join(r_["report"]["errors"])[:160]))
                        continue
                    d_ = os.path.join(od, v["model_id"])
                    os.makedirs(d_, exist_ok=True)
                    b_ = os.path.join(d_, v["model_id"])
                    eden_core.write_stl(b_ + ".stl", r_["vertices"], r_["faces"], v["model_id"])
                    eden_core.write_3mf(b_ + ".3mf", r_["vertices"], r_["faces"], v["model_id"])
                    eden_core.save_params(b_ + ".json", r_)
                    pts_ = r_.get("parts") or []
                    if not pts_ and col_opts.get("saucer"):
                        sc_ = eden_core.build_saucer(vv)
                        if sc_["report"].get("valid"):
                            pts_ = [{"name": "PLATO", "vertices": sc_["vertices"], "faces": sc_["faces"]}]
                    for pt_ in pts_:
                        nm_ = "%s-%s" % (v["model_id"], pt_["name"])
                        eden_core.write_stl(b_ + "-" + pt_["name"] + ".stl", pt_["vertices"], pt_["faces"], nm_)
                        eden_core.write_3mf(b_ + "-" + pt_["name"] + ".3mf", pt_["vertices"], pt_["faces"], nm_)
                    ok_n += 1
                    col_lines.append("  OK %s  (%s g PLA%s)" % (v["model_id"], r_["report"].get("mass_g_PLA_100pct"),
                                     " + " + "+".join(p_["name"] for p_ in pts_) if pts_ else ""))
                except Exception as e_:          # una variante rota no corta el lote
                    col_lines.append("  FALLÓ %s: %s" % (v.get("model_id"), e_))
            col_lines.append("EXPORTADOS %d/%d en: %s" % (ok_n, len(variants), od))
        else:
            col_lines.append("Apretá export para exportar los %d modelos (tarda unos minutos)." % len(variants))
        col_lines.append("")

    # 1) parámetros: colección / preset (si hay) + sobrescrituras de los sliders
    if col_P is not None:
        P = dict(col_P)
        if opt("quality"):
            P["quality"] = eden_core.clean_path(opt("quality"))
    else:
        P = eden_core.load_params(preset) if opt("preset") else {}
        if "variants" in P:              # una colección como preset: primera variante
            base = dict(P.get("base", {}))
            base.update(P["variants"][0])
            P = base
    P = eden_core.merge_params(P)
    if col_P is None:                    # sin colección: aplicar sliders
        # Cualquier entrada con el MISMO nombre que un parámetro del motor se aplica
        # (height, d_max, d_base, d_mouth, belly, wall, floor, quality, drain_pattern,
        #  drain_shape, drain_d, drain_count, drain_rings, drain_center, ...).
        for key, default in eden_core.DEFAULTS.items():
            if key == "waves":                # 'waves' = cantidad de ondas (ver abajo)
                continue
            val = opt(key)
            if val is None:
                continue
            if isinstance(default, bool):
                val = str(val).strip().lower() in ("true", "1", "si", "sí", "yes")
            elif isinstance(default, int):
                val = int(round(float(val)))
            elif isinstance(default, float):
                val = float(val)
            else:
                val = str(val).strip()
            P[key] = val
        if not P["waves"]:
            P["waves"] = eden_core.merge_params({"waves": [{}]})["waves"]
        w0 = P["waves"][0]
        if opt("waves") is not None: w0["count"] = int(opt("waves"))
        if opt("amp") is not None:   w0["amp"] = float(opt("amp"))
        if opt("twist") is not None: w0["twist"] = float(opt("twist"))
        if opt("sides") is not None:
            P["polygon_sides"] = int(opt("sides"))
            if P["polygon_sides"] >= 3 and not P.get("polygon_blend"):
                P["polygon_blend"] = 0.5
        # Cualquier entrada con el nombre de un parámetro del motor se aplica sola
        # (drain_pattern, drain_count, drain_d, drain_rings, drain_shape, belly,
        #  d_base, d_mouth, floor, rim, asym, ...). Así no hay que tocar el código
        # para exponer parámetros nuevos: basta con crear la entrada.
        for key in eden_core.DEFAULTS:
            if key in ("waves", "quality", "model_id"):
                continue
            val = opt(key)
            if val is not None:
                default = eden_core.DEFAULTS[key]
                if isinstance(default, bool):
                    val = bool(val) if not isinstance(val, str) else val.strip().lower() in ("1", "true", "si", "sí")
                elif isinstance(default, int):
                    val = int(round(float(val)))
                elif isinstance(default, float):
                    val = float(val)
                else:
                    val = eden_core.clean_path(val) if isinstance(val, str) else val
                P[key] = val
        P = eden_core.merge_params(P)

        # el nombre sigue al modo elegido (evita exportar "OCULTO" con rosca, etc.)
        if opt("mode") is not None:
            suf = {"hidden_tray": "OCULTO", "screw_tray": "ROSCA", "self_watering": "RIEGO"}
            mid = P["model_id"]
            for s_ in suf.values():
                if mid.endswith("-" + s_):
                    mid = mid[: -len(s_) - 1]
            if P.get("mode") in suf:
                mid += "-" + suf[P["mode"]]
            P["model_id"] = mid
        if opt("model_id"):
            P["model_id"] = eden_core.clean_path(opt("model_id"))

    # 2) construir + validar
    res = eden_core.build_pot(P)
    rep = res["report"]
    lines = ["%s  ->  %s" % (P["model_id"], "VÁLIDA" if rep.get("valid") else "INVÁLIDA")]
    lines += ["ERROR: " + e for e in rep["errors"]]
    lines += ["Aviso: " + w for w in rep["warnings"]]
    if rep.get("valid"):
        pot = to_rhino_mesh(res)
        ok, log = pot.IsValidWithLog()
        lines.append("Malla cerrada: %s | válida Rhino: %s" % (pot.IsClosed, ok))
        for k in ("bbox_mm", "mass_g_PLA_100pct", "soil_capacity_ml",
                  "drain_holes", "drain_area_mm2", "drain_area_pct_floor",
                  "overhang_max_deg", "min_convex_radius_mm", "visible_inset_mm",
                  "triangles"):
            if rep.get(k) is not None:
                lines.append("%s: %s" % (k, rep.get(k)))
        A = rep.get("assembly") or {}
        for k, v in A.items():
            lines.append("armado.%s: %s" % (k, v))

        # piezas extra (plato oculto / inserto de autorriego), mostradas ARMADAS
        parts = res.get("parts") or []
        _mode = P.get("mode", "pot")
        if parts:
            part = parts[0]
            pm = to_rhino_mesh(part)
            if _mode in ("hidden_tray", "screw_tray"):
                # el plato queda abajo y la maceta sube a su posición de uso
                pot.Translate(0, 0, A.get("pot_bottom_z_mm", 0) - A.get("pot_drop_on_seat_mm", 0))
            elif _mode == "self_watering":
                pm.Translate(0, 0, P["floor"] + A.get("reservoir_h_mm", 0)
                             - A.get("insert_drop_on_rim_mm", 0))
            plate = pm
            pr = part["report"]
            lines.append("%s: %s | %s g PLA" % (part["name"],
                         "VÁLIDA" if pr.get("valid") else "INVÁLIDA", pr.get("mass_g_PLA_100pct")))
        elif opt("saucer"):
            sc = eden_core.build_saucer(P)
            if sc["report"].get("valid"):
                plate = to_rhino_mesh(sc)
                parts = [{"name": "PLATO", "vertices": sc["vertices"], "faces": sc["faces"]}]
            else:
                lines.append("Plato inválido: %s" % sc["report"]["errors"])

        # 3) exportar: cada pieza apoyada en z=0, lista para el laminador.
        #    Si no hay out_dir se usa <MACETAS_EDEN3D>\exportadas.
        #    Si se está en vista previa, se recalcula en calidad "normal".
        if opt("export") and col_P is None:
            od = eden_core.clean_path(opt("out_dir") or "")
            if not od:
                od = os.path.join(os.path.dirname(os.path.dirname(lib_path)), "exportadas")
            ex = res
            if P.get("quality") == "preview":
                ex = eden_core.build_pot(dict(P, quality="normal"))
                if not ex["report"].get("valid"):
                    lines.append("NO EXPORTADO: en calidad normal es inválida: %s"
                                 % ex["report"]["errors"])
                    ex = None
            if ex is not None:
                ex_parts = ex.get("parts") or [pt for pt in parts if pt["name"] == "PLATO"]
                d = os.path.join(od, P["model_id"])
                os.makedirs(d, exist_ok=True)
                b = os.path.join(d, P["model_id"])
                eden_core.write_stl(b + ".stl", ex["vertices"], ex["faces"], P["model_id"])
                eden_core.write_3mf(b + ".3mf", ex["vertices"], ex["faces"], P["model_id"])
                eden_core.save_params(b + ".json", ex)
                for part in ex_parts:
                    nm = "%s-%s" % (P["model_id"], part["name"])
                    eden_core.write_stl(b + "-" + part["name"] + ".stl", part["vertices"], part["faces"], nm)
                    eden_core.write_3mf(b + "-" + part["name"] + ".3mf", part["vertices"], part["faces"], nm)
                lines.append("EXPORTADO (calidad normal) en: " + d)
    report = "\n".join(col_lines + lines)
    params_json = json.dumps(res["params"], indent=2, ensure_ascii=False)

except Exception as ex:
    import traceback
    report = "FALLO: %s\n%s" % (ex, traceback.format_exc())
