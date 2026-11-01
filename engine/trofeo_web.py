# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
TROFEOS PARA EVENTOS — Puente entre el motor y la página web (trofeo.html)
==========================================================================
    info()                  -> figuras, bases, tipografías, estilos y límites
    build(opts)             -> el trofeo armado para el visor + reporte
    export_stl(opts, pieza) -> (nombre, bytes)   pieza: FIGURA, DETALLE, BASE o TEXTO
    export_3mf(opts)        -> (nombre, bytes)   la figura acostada y la base parada,
                                                 cada una con sus partes de color
"""
import array
import os
import re
import time
import unicodedata
import zipfile

import topper_core as tc
import trofeo_core as tr

VERSION = "1.0.0"
LICENSE_NOTE = ("© TecnoBear — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta o redistribución del archivo.")


def info():
    return {"motor": VERSION,
            "figuras": [{"id": k, "nombre": n} for k, n in tr.FIGURAS],
            "bases": [{"id": k, "nombre": n} for k, n in tr.BASES],
            "textos": [{"id": k, "nombre": n} for k, n in tr.TEXTOS],
            "colores": [{"id": k, "nombre": n} for k, n in tr.COLORES],
            "fuentes": [{"id": f, "nombre": n} for f, n in tc.FUENTES],
            "defecto": dict(tr.DEFECTO),
            "limites": {k: (list(v) if isinstance(v, tuple) else v) for k, v in tr.LIMITES.items()},
            "license": LICENSE_NOTE}


def _pack(V, F):
    return array.array("f", [c for v in V for c in v]).tobytes(), array.array("I", [i for f in F for i in f]).tobytes()


def _sku(opts):
    o = tr.opciones(opts)
    txt = unicodedata.normalize("NFKD", o["linea1"] or o["linea2"]).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9]+", "-", txt).strip("-")[:24] or "Evento"
    return "Trofeo-%s-%s" % (o["figura"].capitalize(), txt)


def build(opts):
    t0 = time.time()
    try:
        r = tr.construir(opts)
        sku = _sku(opts)
    except ValueError as e:
        return {"summary": {"valid": False, "errors": [str(e)], "warnings": [], "sku": "—",
                            "seconds": round(time.time() - t0, 2)}, "parts": []}
    parts = []
    for nombre, V, F in r["armado"]:
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


def export_stl(opts, pieza="FIGURA"):
    o = _normal(opts)
    r = tr.construir(o)
    for nombre, V, F in r["piezas"]:
        if nombre == pieza:
            name = "%s_%s.stl" % (_sku(o), nombre)
            from eden_core import write_stl
            path = _tmp(name)
            write_stl(path, V, F, name="TecnoBear Trofeo (c) Yoel Almiron - uso personal")
            with open(path, "rb") as fh:
                data = fh.read()
            os.remove(path)
            return name, data
    raise ValueError("Esa pieza no existe en este trofeo: %s" % pieza)


def _xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def export_3mf(opts):
    """Dos objetos en la cama, cada uno en la posición en que se imprime: la figura acostada
    (con su DETALLE de color como parte) y la base parada (con su TEXTO)."""
    o = _normal(opts)
    r = tr.construir(o)
    sku = _sku(o)
    meta = {"Title": sku, "Designer": "TecnoBear", "Copyright": "© TecnoBear — Yoel Almirón.",
            "LicenseTerms": LICENSE_NOTE, "Application": "TecnoBear Trofeos %s" % VERSION,
            "CreationDate": time.strftime("%Y-%m-%d")}
    grupos = [("FIGURA", ("FIGURA", "DETALLE")), ("BASE", ("BASE", "TEXTO"))]
    por_nombre = {n: (V, F) for n, V, F in r["piezas"]}
    res, items, oid = [], [], 0
    x_libre = 0.0
    for titulo, nombres in grupos:
        partes = [(n, por_nombre[n]) for n in nombres if n in por_nombre]
        allv = [v for _, (V, _) in partes for v in V]
        x0, x1 = min(v[0] for v in allv), max(v[0] for v in allv)
        cy = (min(v[1] for v in allv) + max(v[1] for v in allv)) / 2.0
        comps = []
        for n, (V, F) in partes:
            oid += 1
            verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % (x - x0, y - cy, z) for x, y, z in V)
            tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
            res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>'
                       % (oid, _xml(n), verts, tris))
            comps.append('<component objectid="%d"/>' % oid)
        oid += 1
        res.append('<object id="%d" type="model" name="%s"><components>%s</components></object>'
                   % (oid, _xml("%s_%s" % (sku, titulo)), "".join(comps)))
        items.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f 128 0"/>' % (oid, 20 + x_libre))
        x_libre += (x1 - x0) + 12.0
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s<resources>%s</resources>'
             '<build>%s</build></model>') % (md, "".join(res), "".join(items))
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
