# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Puente entre el motor y la página web
==============================================
La web corre este módulo dentro del navegador (Pyodide, en un Web Worker). Las
mismas funciones se testean con CPython en tests/motor, así que lo que se ve en
la web es exactamente lo que valida la suite.

    info()                          -> catálogo para armar los controles
    build(opts)                     -> piezas ubicadas (bytes float32/uint32) + reporte
    export_3mf(opts)                -> (nombre, bytes del 3MF con todas las piezas)

opts = {"design": "ROMBO", "size": "S", "mode": "screw_dish_sw", "drain": "leaf",
        "quality": "preview", "overrides": {"tex_count": 36}}
"""
import array
import io
import json
import os
import time

import eden_catalog as ec
import eden_core as core
import eden_patitas
import eden_plantas

HERE = os.path.dirname(os.path.abspath(__file__))
CAT_PATH = os.path.join(HERE, "colecciones", "catalogo_eden3d.json")
WEB_MODES = ("screw_dish_sw", "screw_dish", "saucer", "pot")
OVERRIDE_KEYS = ("tex_count", "tex_pitch", "tex_amp", "tex_duty", "tex_wob", "ondas",
                 "amp_ondas")
LICENSE_NOTE = ("© Eden3D — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta, redistribución o modificación para vender.")

_CAT = {}


def catalog():
    if "cat" not in _CAT:
        _CAT["cat"] = ec.load_catalog(CAT_PATH)
    return _CAT["cat"]


def info():
    cat = catalog()
    return {
        "brand": cat.get("brand", "Eden3D"),
        "engine": core.ENGINE_VERSION,
        "designs": [{"code": d["code"], "name": d.get("name", d["code"]),
                     "tex_type": d["params"].get("tex_type", "none")} for d in cat["designs"]],
        "modes": [{"code": m, "label": lab} for m, lab, _ in ec.MODES if m in WEB_MODES],
        "drains": [{"code": k, "label": lab} for k, lab, _, _ in ec.DRAINS],
        "sizes": [s for s in ("Mini", "S", "M", "L", "XL")],
        "overrides": list(OVERRIDE_KEYS),
        "license": LICENSE_NOTE,
        "plantas": eden_plantas.catalogo()["plantas"],
        "plantas_fuentes": eden_plantas.catalogo().get("fuentes", {}),
        "materiales": {k: {"rgb": v[0], "brillo": v[1]} for k, v in eden_plantas.MATERIALES.items()},
        "max_plantas": eden_plantas.MAX_PLANTAS,
        "grupos": eden_plantas.catalogo().get("grupos", []),
        "coberturas": [{"id": k, "nombre": v[0], "descripcion": v[1]}
                       for k, v in eden_plantas.COBERTURAS.items()],
        "flex": eden_plantas.FLEX,
        "decor_mats": list(eden_plantas.DECOR_MATS),
        "patitas": {"tipos": [{"id": k, "nombre": n} for k, n in eden_patitas.TIPOS],
                    "pies": [{"id": k, "nombre": n} for k, n in eden_patitas.PIES],
                    "defecto": dict(eden_patitas.DEFECTO),
                    "limites": {k: list(v) for k, v in eden_patitas.LIMITES.items()}},
    }


def _clean_overrides(ov):
    out = {}
    for k, v in (ov or {}).items():
        if k not in OVERRIDE_KEYS:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out[k] = int(v) if k in ("tex_count", "ondas") else round(v, 3)
    return out


def params(opts):
    cat = catalog()
    mode = opts.get("mode") or "screw_dish_sw"
    if opts.get("patitas"):                    # las patitas van siempre sin plato, en la base
        mode = "pot"
    if mode not in WEB_MODES:
        raise ValueError("modo no disponible en la web: %s" % mode)
    d = ec.find_design(cat, opts.get("design") or cat["designs"][0]["code"])
    size = opts.get("size") or "M"
    if size not in ec.SIZES:
        raise ValueError("tamaño desconocido: %s" % size)
    drain = opts.get("drain") or "leaf"
    q = opts.get("quality") or "preview"
    if q not in ("preview", "normal"):
        q = "preview"
    p = ec.design_params(cat, d, size, mode, drain, q, _clean_overrides(opts.get("overrides")))
    if opts.get("brand") is not None:                 # marca personalizada ("" = sin marca)
        import eden_font
        t, err = eden_font.check(opts.get("brand"))
        if err:
            raise ValueError(err)
        p["brand"] = t
    return p


def check_brand(text):
    """Para la web: valida el texto de la marca antes de calcular."""
    import eden_font
    t, err = eden_font.check(text)
    return {"text": t, "error": err, "max_len": eden_font.MAX_LEN,
            "chars": "".join(sorted(eden_font.GLYPHS))}


def _placed(res):
    """[(nombre, V, F, dz)] en posición de uso (la maceta sube sobre el plato)."""
    A = res["report"].get("assembly") or {}
    lift = 0.0
    if res["params"].get("mode") in ("screw_dish", "screw_dish_sw", "saucer"):
        lift = A.get("pot_bottom_z_mm", 0.0) - A.get("pot_drop_on_seat_mm", 0.0)
    out = []
    for nm, V, F in ec.pieces(res):
        out.append((nm, V, F, lift if nm == "MACETA" else 0.0))
    return out


def _pack(V, F, dz=0.0):
    pos = array.array("f", [c for x, y, z in V for c in (x, y, z + dz)])
    idx = array.array("I", [i for f in F for i in f])
    return pos.tobytes(), idx.tobytes()


def mesh_check(F):
    """Malla cerrada y bien orientada, sin dependencias: cada arista dirigida tiene que
    aparecer una sola vez y su opuesta también (como pide un laminador)."""
    seen = set()
    dup = 0
    for a, b, c in F:
        for e in ((a, b), (b, c), (c, a)):
            if e in seen:
                dup += 1
            seen.add(e)
    open_edges = sum(1 for (a, b) in seen if (b, a) not in seen)
    return {"closed": dup == 0 and open_edges == 0, "open_edges": open_edges, "bad_edges": dup}


def build(opts):
    t0 = time.time()
    p = params(opts)
    res = core.build_pot(p)
    rep = res["report"]
    parts = []
    abertura = None
    pat = None
    if rep.get("valid") and opts.get("patitas"):
        pat = _patitas_web(res, opts["patitas"])
    if rep.get("valid"):
        for nm, V, F, dz in _placed(res):
            if nm == "MACETA":
                abertura = eden_plantas.abertura_de([(x, y, z + dz) for x, y, z in V])
                _ABERTURA[p["model_id"] + "|" + p["quality"]] = abertura
            pos, idx = _pack(V, F, dz)
            parts.append({"name": nm, "positions": pos, "indices": idx,
                          "vertices": len(V), "triangles": len(F)})
        if pat:                          # cada eslabón aparte: la web los anima
            for c in pat["cadenas"]:
                for e in c["eslabones"]:
                    pos, idx = _pack(e["V"], e["F"])
                    parts.append({"name": e["parte"], "positions": pos, "indices": idx,
                                  "vertices": len(e["V"]), "triangles": len(e["F"])})
                    del e["V"], e["F"]
        Vw, Fw = core.water_mesh(res)
        if Vw:
            pos, idx = _pack(Vw, Fw)
            parts.append({"name": "AGUA", "positions": pos, "indices": idx,
                          "vertices": len(Vw), "triangles": len(Fw)})
    A = rep.get("assembly") or {}
    keep = ("thread_turns", "thread_engagement_mm", "water_gap_under_pot_mm",
            "water_min_wet_ml", "water_reservoir_ml", "water_over_soil_mm", "tray_h_mm",
            "dish_diameter_mm", "thread", "dish_inner_r0_mm", "dish_flare_deg", "dish_floor_mm",
            "water_level_max_mm", "water_min_wet_level_mm", "pot_bottom_z_mm",
            "pot_drop_on_seat_mm")
    summary = {
        "sku": p["model_id"],
        "valid": bool(rep.get("valid")),
        "errors": list(rep.get("errors", [])),
        "warnings": list(rep.get("warnings", [])),
        "pot_g": rep.get("mass_g_PLA_100pct"),
        "soil_ml": rep.get("soil_capacity_ml"),
        "bbox_mm": rep.get("bbox_mm"),
        "parts_g": {pt["name"]: pt["report"].get("mass_g_PLA_100pct")
                    for pt in res.get("parts") or []},
        "drain_holes": rep.get("drain_holes"),
        "assembly": {k: A[k] for k in keep if k in A},
        "seconds": round(time.time() - t0, 2),
        "engine": core.ENGINE_VERSION,
        "abertura": {k: round(v, 2) for k, v in abertura.items()} if abertura else None,
        "brand": {"text": p.get("brand", ""),
                  "pieces": dict([("MACETA", (rep.get("brand") or {}).get("cap_h_mm"))] +
                                 [(pt["name"], (pt["report"].get("brand") or {}).get("cap_h_mm"))
                                  for pt in res.get("parts") or []])},
    }
    if pat:
        summary["patitas"] = pat
    if opts.get("check") and rep.get("valid"):          # cobertura del administrador
        summary["mesh_check"] = dict([("MACETA", mesh_check(res["faces"]))] +
                                     [(pt["name"], mesh_check(pt["faces"])) for pt in res.get("parts") or []])
    return {"summary": summary, "parts": parts}


_ABERTURA = {}


def _patitas_web(res, o):
    """Patitas para la web: el soporte de la cadera se suma a su pieza (fusionado) y los
    eslabones van aparte, con el eje de cada bisagra para animarlos."""
    nombre, cadenas, info = eden_patitas.armar(res, o)
    if nombre == "MACETA":
        V, F = res["vertices"], res["faces"]
    else:
        pt = [x for x in res["parts"] if x["name"] == nombre][0]
        V, F = pt["vertices"], pt["faces"]
    out = []
    for c in cadenas:
        for Vs, Fs in c["soporte"]:
            off = len(V)
            V.extend(Vs)
            F.extend((a + off, b + off, d + off) for a, b, d in Fs)
        esl = []
        for k, e in enumerate(c["eslabones"]):
            Ve, Fe = [], []
            for Vs, Fs in e["shells"]:
                off = len(Ve)
                Ve.extend(Vs)
                Fe.extend((a + off, b + off, d + off) for a, b, d in Fs)
            (px, py, pz), d = e["eje"]
            esl.append({"parte": "%s_%d" % (c["nombre"], k + 1), "V": Ve, "F": Fe,
                        "eje": [round(px, 3), round(py, 3), round(pz, 3)], "dir": [round(x, 4) for x in d]})
        out.append({"nombre": c["nombre"], "eslabones": esl, "angulo": c["angulo"], "grosor_mm": round(c["medidas"]["t"], 2)})
    res["report"]["patitas"] = info
    info = dict(info)
    info["cadenas"] = out
    info["pieza_archivo"] = ec.PART_FILE.get(nombre, nombre)
    return info


def plants(opts, ids, decor=True, cobertura=None):
    """Plantas (y tierra con su cobertura) para la maceta de opts. Usa la boca de la
    última maceta calculada con esos mismos parámetros (si no, la calcula).
    Cada parte trae "planta" (índice, -1 = tierra/cobertura), "base" (punto donde nace,
    para animarla) y "flex" (cuánto se mueve con el viento)."""
    p = params(opts)
    key = p["model_id"] + "|" + p["quality"]
    if key not in _ABERTURA:
        build(opts)
    ab = _ABERTURA.get(key)
    ids = eden_plantas.limpiar_ids(ids)
    cob = cobertura if cobertura in eden_plantas.COBERTURAS else eden_plantas.cobertura_sugerida(ids)
    parts = []

    def add(mat, V, F, k, base, flex):
        pos, idx = _pack(V, F)
        parts.append({"name": mat, "positions": pos, "indices": idx, "vertices": len(V),
                      "triangles": len(F), "planta": k, "base": list(base), "flex": flex})
    if ab:
        if decor:
            for mat, V, F in eden_plantas.decor(ab, ids, cobertura=cob):
                add(mat, V, F, -1, (0.0, 0.0, ab["z_s"]), 0.0)
        for k, pl in enumerate(eden_plantas.build_por_planta(ids, ab)):
            for mat, V, F in pl["items"]:
                add(mat, V, F, k, pl["base"], pl["flex"])
    return {"parts": parts, "compat": eden_plantas.compatibilidad(ids) if ids else [],
            "ids": ids, "cobertura": cob}


def build_json(opts_json):
    """Atajo para JavaScript: recibe y devuelve JSON (sin los bytes)."""
    r = build(json.loads(opts_json))
    return json.dumps(r["summary"])


def export_3mf(opts):
    """Todas las piezas del SKU en un 3MF (calidad normal), con la licencia en
    los metadatos. Devuelve (nombre_de_archivo, bytes)."""
    o = dict(opts)
    o["quality"] = "normal"
    p = params(o)
    res = core.build_pot(p)
    if not res["report"].get("valid"):
        raise ValueError("; ".join(res["report"].get("errors", [])) or "modelo inválido")
    if o.get("patitas"):
        eden_patitas.agregar(res, o["patitas"])
    meta = {"Title": p["model_id"], "Designer": "Eden3D",
            "Copyright": "© Eden3D — Yoel Almirón. Todos los derechos reservados.",
            "LicenseTerms": LICENSE_NOTE,
            "Description": "%s · motor %s" % (p.get("design_name", ""), core.ENGINE_VERSION),
            "CreationDate": time.strftime("%Y-%m-%d")}
    objs = [("%s_%s" % (p["model_id"], nm), V, F) for nm, V, F in ec.pieces(res)]
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), p["model_id"] + ".3mf")
    core.write_3mf_multi(path, objs, meta)
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(path)
    except OSError:
        pass
    return p["model_id"] + ".3mf", data


def export_stl(opts, part="MACETA"):
    """Una pieza en STL binario (calidad normal). Devuelve (nombre, bytes)."""
    o = dict(opts)
    o["quality"] = "normal"
    p = params(o)
    res = core.build_pot(p)
    if not res["report"].get("valid"):
        raise ValueError("; ".join(res["report"].get("errors", [])) or "modelo inválido")
    if o.get("patitas"):
        eden_patitas.agregar(res, o["patitas"])
    for nm, V, F in ec.pieces(res):
        if nm == part:
            name = "%s_%s.stl" % (p["model_id"], nm)
            path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
            core.write_stl(path, V, F, name="Eden3D (c) Yoel Almiron - uso personal")
            with open(path, "rb") as fh:
                data = fh.read()
            try:
                os.remove(path)
            except OSError:
                pass
            return name, data
    raise ValueError("pieza inexistente: %s" % part)


def selftest_json():
    """El mismo autotest de Grasshopper, para la consola del navegador."""
    import eden_selftest
    buf = io.StringIO()
    ok = eden_selftest.run(catalog(), [catalog()["designs"][0]["code"]], sizes=("S",),
                           log=lambda s: buf.write(s + "\n"))
    return json.dumps({"ok": ok, "log": buf.getvalue()})
