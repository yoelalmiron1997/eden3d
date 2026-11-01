# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
CHAPITAS PARA COLLARES — Puente entre el motor y la página web (chapita.html)
=============================================================================
    info()                  -> formas, tipografías, estilos y límites
    build(opts)             -> piezas para el visor + reporte
    export_stl(opts, pieza) -> (nombre, bytes)   pieza: CHAPITA o LETRAS
    export_3mf(opts)        -> (nombre, bytes)   UN objeto con sus partes de color
"""
import array
import os
import re
import time
import unicodedata
import zipfile

import chapita_core as cc
import topper_core as tc

VERSION = "1.0.0"
LICENSE_NOTE = ("© TecnoBear — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta o redistribución del archivo.")


def info():
    return {"motor": VERSION,
            "formas": [{"id": k, "nombre": n} for k, n in cc.FORMAS],
            "textos": [{"id": k, "nombre": n} for k, n in cc.TEXTOS],
            "colores": [{"id": k, "nombre": n} for k, n in cc.COLORES],
            "fuentes": [{"id": f, "nombre": n} for f, n in tc.FUENTES],
            "con_patitas": list(cc.CON_PATITAS),
            "defecto": dict(cc.DEFECTO),
            "limites": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cc.LIMITES.items()},
            "license": LICENSE_NOTE}


def _pack(V, F):
    return array.array("f", [c for v in V for c in v]).tobytes(), array.array("I", [i for f in F for i in f]).tobytes()


def _sku(opts):
    o = cc.opciones(opts)
    txt = unicodedata.normalize("NFKD", o["nombre"]).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9]+", "-", txt).strip("-")[:24] or "Mascota"
    return "Chapita-%s-%s" % (o["forma"].capitalize(), txt)


def build(opts):
    t0 = time.time()
    try:
        r = cc.construir(opts)
        sku = _sku(opts)
    except ValueError as e:
        return {"summary": {"valid": False, "errors": [str(e)], "warnings": [], "sku": "—",
                            "seconds": round(time.time() - t0, 2)}, "parts": []}
    parts = []
    for nombre, V, F in r["piezas"]:
        pos, idx = _pack(V, F)
        parts.append({"name": nombre, "positions": pos, "indices": idx, "vertices": len(V), "triangles": len(F)})
    rep = dict(r["reporte"])
    rep.update({"valid": True, "errors": [], "warnings": rep.pop("avisos"), "sku": sku,
                "seconds": round(time.time() - t0, 2), "motor": VERSION})
    return {"summary": rep, "parts": parts}


def _normal(opts):
    o = dict(opts or {})
    o["calidad"] = "normal"
    return o


def _tmp(name):
    return os.path.join(os.environ.get("TMPDIR", "/tmp"), name)


def export_stl(opts, pieza="CHAPITA"):
    o = _normal(opts)
    r = cc.construir(o)
    for nombre, V, F in r["piezas"]:
        if nombre == pieza:
            name = "%s_%s.stl" % (_sku(o), nombre)
            from eden_core import write_stl
            path = _tmp(name)
            write_stl(path, V, F, name="TecnoBear Chapita (c) Yoel Almiron - uso personal")
            with open(path, "rb") as fh:
                data = fh.read()
            os.remove(path)
            return name, data
    raise ValueError("Esa pieza no existe en esta chapita: %s" % pieza)


def _xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def export_3mf(opts):
    """Un objeto con sus partes (placa y, en dos colores, las letras) ya encastradas: en el
    laminador se le asigna un filamento a cada parte."""
    o = _normal(opts)
    r = cc.construir(o)
    sku = _sku(o)
    meta = {"Title": sku, "Designer": "TecnoBear", "Copyright": "© TecnoBear — Yoel Almirón.",
            "LicenseTerms": LICENSE_NOTE, "Application": "TecnoBear Chapitas %s" % VERSION,
            "CreationDate": time.strftime("%Y-%m-%d")}
    allv = [v for _, V, _ in r["piezas"] for v in V]
    cx = (min(v[0] for v in allv) + max(v[0] for v in allv)) / 2.0
    cy = (min(v[1] for v in allv) + max(v[1] for v in allv)) / 2.0
    res, comps = [], []
    for i, (nombre, V, F) in enumerate(r["piezas"]):
        verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % (x - cx, y - cy, z) for x, y, z in V)
        tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>'
                   % (i + 1, _xml(nombre), verts, tris))
        comps.append('<component objectid="%d"/>' % (i + 1))
    oid = len(r["piezas"]) + 1
    res.append('<object id="%d" type="model" name="%s"><components>%s</components></object>' % (oid, _xml(sku), "".join(comps)))
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s<resources>%s</resources>'
             '<build><item objectid="%d" transform="1 0 0 0 1 0 0 0 1 128 128 0"/></build></model>') % (md, "".join(res), oid)
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    name = sku + ".3mf"
    path = _tmp(name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    with open(path, "rb") as fh:
        data = fh.read()
    os.remove(path)
    return name, data
