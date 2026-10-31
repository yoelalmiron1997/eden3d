# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
TOPPER PARA TORTAS — Puente entre el motor y la página web (topper.html)
=======================================================================
    info()                 -> tipografías, marcos, estilos y límites
    build(opts)            -> piezas para el visor + reporte
    build_numero(opts)     -> el número de años (opts["numero"]) para el visor + reporte
    export_stl(opts, pieza) -> (nombre, bytes)  pieza: TOPPER, LETRAS, NUMERO o NUMERO_LETRAS
    export_3mf(opts)       -> (nombre, bytes)  topper (y número, si está activo): cada uno UN
                              objeto con sus partes de color ya encastradas
    check_texto(text, fuente) -> texto limpio o error para esa tipografía

opts = {"lineas": [{"texto": "Feliz", "fuente": "great_vibes", "escala": 1}, ...],
        "ancho": 140, "contorno": 1.2, "grosor": 3, "letras": 1.2, "estilo": "simple",
        "marco": "ninguno", "palitos": 2, "largo": 90, "calidad": "preview"}
"""
import array
import os
import re
import time
import unicodedata
import zipfile

import mate_fuentes
import topper_core as tc

TOPPER_VERSION = "1.1.0"
LICENSE_NOTE = ("© Eden3D — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta, redistribución o modificación para vender.")


def info():
    return {"motor": TOPPER_VERSION,
            "fuentes": [{"id": f, "nombre": n} for f, n in tc.FUENTES],
            "marcos": [{"id": k, "nombre": n} for k, n in tc.MARCOS],
            "estilos": [{"id": k, "nombre": n} for k, n in tc.COLORES],
            "estilos_numero": [{"id": k, "nombre": n} for k, n in tc.ESTILOS_NUM],
            "defecto_numero": dict(tc.DEFECTO_NUM),
            "defecto": {k: v for k, v in tc.DEFECTO.items()},
            "limites": {k: (list(v) if isinstance(v, tuple) else v) for k, v in tc.LIMITES.items()},
            "license": LICENSE_NOTE}


def check_texto(text, fuente):
    try:
        t, err = mate_fuentes.limpiar(text, fuente)
    except ValueError as e:
        t, err = str(text or ""), str(e)
    if not err and len(t) > tc.LIMITES["caracteres"]:
        err = "Cada línea puede tener hasta %d letras" % tc.LIMITES["caracteres"]
    return {"text": t, "error": err}


def _pack(V, F):
    pos = array.array("f", [c for v in V for c in v])
    idx = array.array("I", [i for f in F for i in f])
    return pos.tobytes(), idx.tobytes()


def build(opts):
    return _build(tc.construir, opts, _sku(opts) if _ok(opts) else "—")


def build_numero(opts):
    try:
        sku = _sku_numero(opts)
    except ValueError:
        sku = "—"
    return _build(tc.construir_numero, opts, sku)


def _ok(opts):
    try:
        tc.opciones(opts)
        return True
    except ValueError:
        return False


def _build(fn, opts, sku):
    t0 = time.time()
    try:
        r = fn(opts)
    except ValueError as e:
        return {"summary": {"valid": False, "errors": [str(e)], "warnings": [], "sku": "—",
                            "seconds": round(time.time() - t0, 2)}, "parts": []}
    parts = []
    for nombre, V, F in r["piezas"]:
        pos, idx = _pack(V, F)
        parts.append({"name": nombre, "positions": pos, "indices": idx,
                      "vertices": len(V), "triangles": len(F)})
    rep = dict(r["reporte"])
    avisos = []
    if rep["puentes"]:
        avisos.append("Agregué %d puente%s para que todo quede unido" %
                      (rep["puentes"], "" if rep["puentes"] == 1 else "s"))
    if rep.get("huecos") and rep.get("huecos_abiertos", 0) < rep["huecos"]:
        avisos.append("Quedaron tapados %d huecos chiquitos de las letras" % (rep["huecos"] - rep["huecos_abiertos"]))
    rep.update({"valid": True, "errors": [], "warnings": avisos, "sku": sku,
                "seconds": round(time.time() - t0, 2), "motor": TOPPER_VERSION})
    return {"summary": rep, "parts": parts}


def _sku(opts):
    o = tc.opciones(opts)
    txt = "-".join(str(L.get("texto") or "") for L in o["lineas"])
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9]+", "-", txt).strip("-")[:40] or "TOPPER"
    return "Topper-%s" % txt


def _sku_numero(opts):
    return "Numero-%s" % tc.opciones_numero(opts)["numero"]


def _numero_activo(opts):
    n = (opts or {}).get("numero")
    return isinstance(n, dict) and bool(n.get("activo"))


def _piezas(o, pieza):
    if pieza.startswith("NUMERO"):
        return _sku_numero(o), tc.construir_numero(o)
    return _sku(o), tc.construir(o)


def _normal(opts):
    o = dict(opts or {})
    o["calidad"] = "normal"
    return o


def export_stl(opts, pieza="TOPPER"):
    o = _normal(opts)
    sku, r = _piezas(o, pieza)
    for nombre, V, F in r["piezas"]:
        if nombre == pieza:
            name = "%s_%s.stl" % (sku, nombre)
            path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
            from eden_core import write_stl
            write_stl(path, V, F, name="Eden3D Topper (c) Yoel Almiron - uso personal")
            with open(path, "rb") as fh:
                data = fh.read()
            os.remove(path)
            return name, data
    raise ValueError("Esa pieza no existe en este topper: %s" % pieza)


def _xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def export_3mf(opts):
    """El topper (y el número, si está activo): cada uno es UN objeto con sus partes (base
    y, en dos colores, las letras) ya encastradas; en el laminador se le asigna un filamento
    a cada parte. Van uno al lado del otro en la cama."""
    o = _normal(opts)
    sku = _sku(o)
    objetos = [(sku, tc.construir(o))]
    if _numero_activo(o):
        objetos.append((_sku_numero(o), tc.construir_numero(o)))
        sku = "%s-%s" % (sku, tc.opciones_numero(o)["numero"])
    meta = {"Title": sku, "Designer": "Eden3D",
            "Copyright": "© Eden3D — Yoel Almirón. Todos los derechos reservados.",
            "LicenseTerms": LICENSE_NOTE, "Application": "Eden3D Topper %s" % TOPPER_VERSION,
            "CreationDate": time.strftime("%Y-%m-%d")}
    res, items = [], []
    oid = 0
    anchos = []
    for nombre_obj, r in objetos:
        allv = [v for _, V, _ in r["piezas"] for v in V]
        anchos.append((min(v[0] for v in allv), max(v[0] for v in allv),
                       (min(v[1] for v in allv) + max(v[1] for v in allv)) / 2.0))
    total = sum(b - a for a, b, _ in anchos) + 10.0 * (len(anchos) - 1)
    x = 128.0 - total / 2.0
    for (nombre_obj, r), (a, b, cy) in zip(objetos, anchos):
        comps = []
        for nombre, V, F in r["piezas"]:
            oid += 1
            verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % (vx - (a + b) / 2.0, vy - cy, vz)
                            for vx, vy, vz in V)
            tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
            res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices>'
                       '<triangles>%s</triangles></mesh></object>' % (oid, _xml(nombre), verts, tris))
            comps.append('<component objectid="%d"/>' % oid)
        oid += 1
        res.append('<object id="%d" type="model" name="%s"><components>%s</components></object>'
                   % (oid, _xml(nombre_obj), "".join(comps)))
        items.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f 128 0"/>' % (oid, x + (b - a) / 2.0))
        x += (b - a) + 10.0
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s'
             '<resources>%s</resources><build>%s</build></model>') % (md, "".join(res), "".join(items))
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    name = sku + ".3mf"
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    with open(path, "rb") as fh:
        data = fh.read()
    os.remove(path)
    return name, data
