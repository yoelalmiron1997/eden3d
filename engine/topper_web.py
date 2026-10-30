# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
TOPPER PARA TORTAS — Puente entre el motor y la página web (topper.html)
=======================================================================
    info()                 -> tipografías, marcos, estilos y límites
    build(opts)            -> piezas para el visor + reporte
    export_stl(opts, pieza) -> (nombre, bytes)  pieza: "TOPPER" o "LETRAS"
    export_3mf(opts)       -> (nombre, bytes)  base y letras como partes de UN objeto
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

TOPPER_VERSION = "1.0.0"
LICENSE_NOTE = ("© Eden3D — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta, redistribución o modificación para vender.")


def info():
    return {"motor": TOPPER_VERSION,
            "fuentes": [{"id": f, "nombre": n} for f, n in tc.FUENTES],
            "marcos": [{"id": k, "nombre": n} for k, n in tc.MARCOS],
            "estilos": [{"id": k, "nombre": n} for k, n in tc.ESTILOS],
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
    t0 = time.time()
    try:
        r = tc.construir(opts)
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
    rep.update({"valid": True, "errors": [], "warnings": avisos, "sku": _sku(opts),
                "seconds": round(time.time() - t0, 2), "motor": TOPPER_VERSION})
    return {"summary": rep, "parts": parts}


def _sku(opts):
    o = tc.opciones(opts)
    txt = "-".join(str(L.get("texto") or "") for L in o["lineas"])
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9]+", "-", txt).strip("-")[:40] or "TOPPER"
    return "Topper-%s" % txt


def _normal(opts):
    o = dict(opts or {})
    o["calidad"] = "normal"
    return o


def export_stl(opts, pieza="TOPPER"):
    o = _normal(opts)
    r = tc.construir(o)
    for nombre, V, F in r["piezas"]:
        if nombre == pieza:
            name = "%s_%s.stl" % (_sku(o), nombre)
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
    """Un solo objeto con sus partes (base y, en dos colores, las letras), ya encastradas:
    en el laminador se le asigna un filamento a cada parte."""
    o = _normal(opts)
    r = tc.construir(o)
    sku = _sku(o)
    meta = {"Title": sku, "Designer": "Eden3D",
            "Copyright": "© Eden3D — Yoel Almirón. Todos los derechos reservados.",
            "LicenseTerms": LICENSE_NOTE, "Application": "Eden3D Topper %s" % TOPPER_VERSION,
            "CreationDate": time.strftime("%Y-%m-%d")}
    allv = [v for _, V, _ in r["piezas"] for v in V]
    cx = (min(v[0] for v in allv) + max(v[0] for v in allv)) / 2.0
    cy = (min(v[1] for v in allv) + max(v[1] for v in allv)) / 2.0
    res, comps = [], []
    for i, (nombre, V, F) in enumerate(r["piezas"]):
        verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % (x - cx, y - cy, z) for x, y, z in V)
        tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices>'
                   '<triangles>%s</triangles></mesh></object>' % (i + 1, _xml(nombre), verts, tris))
        comps.append('<component objectid="%d"/>' % (i + 1))
    oid = len(r["piezas"]) + 1
    res.append('<object id="%d" type="model" name="%s"><components>%s</components></object>'
               % (oid, _xml(sku), "".join(comps)))
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s'
             '<resources>%s</resources><build><item objectid="%d" '
             'transform="1 0 0 0 1 0 0 0 1 128 128 0"/></build></model>') % (md, "".join(res), oid)
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
