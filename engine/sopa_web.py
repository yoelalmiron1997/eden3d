# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
SOPA DE LETRAS 3D — Puente entre el motor y la página web (sopa.html)
=====================================================================
    info()               -> límites y opciones para armar los controles
    build(opts)          -> piezas para el visor (placa / letras / solución) + reporte
    export_3mf(opts)     -> (nombre, bytes) todas las piezas acomodadas en grilla
    export_stl(opts)     -> (nombre, bytes) todas las piezas en un STL

opts = {"palabras": ["mate", "yerba"], "dificultad": "media", "semilla": 1,
        "filas": 0, "cols": 0, "celda": 15, "cama": 220, "piezas_x": 0, "piezas_y": 0,
        "holgura": 0.2, "base": 3, "relieve": 1.2, "lista": True}
"""
import array
import math
import os
import time
import zipfile

import sopa_core as sc

LICENSE_NOTE = ("© Eden3D — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta, redistribución o modificación para vender.")
SEPARACION = 12.0


def info():
    return {"motor": sc.SOPA_VERSION, "limites": dict(sc.LIMITES), "defaults": dict(sc.DEFAULTS),
            "dificultades": [{"id": "facil", "nombre": "Fácil (→ ↓)"},
                             {"id": "media", "nombre": "Media (+ diagonales)"},
                             {"id": "dificil", "nombre": "Difícil (también al revés)"}],
            "camas": [180, 220, 256, 300, 350], "license": LICENSE_NOTE}


def _pack(V, F, dx=0.0, dy=0.0):
    pos = array.array("f", [c for x, y, z in V for c in (x + dx, y + dy, z)])
    idx = array.array("I", [i for f in F for i in f])
    return pos.tobytes(), idx.tobytes()


def _solucion(res):
    """Celdas (fila, col) que forman parte de alguna palabra."""
    out = set()
    for u in res["sopa"]["ubicadas"]:
        for i in range(len(u["palabra"])):
            out.add((u["fila"] + u["df"] * i, u["col"] + u["dc"] * i))
    return out


def _posiciones(res):
    """Dónde va cada pieza en la vista (tablero armado; la lista, abajo)."""
    pos = {}
    for pz in res["piezas"]:
        pos[pz["nombre"]] = (0.0, 0.0)
    lista = [pz for pz in res["piezas"] if pz["nombre"] == "LISTA"]
    if lista:
        h = lista[0]["medidas_mm"][1]
        pos["LISTA"] = (0.0, -(h + 15.0))
    return pos


def build(opts):
    t0 = time.time()
    res = sc.build_sopa(opts)
    rep = dict(res["report"])
    sopa = res["sopa"]
    parts = []
    if rep["valid"]:
        sol = _solucion(res)
        p = res["params"]
        cap = rep["letra_mm"]
        pos = _posiciones(res)
        for pz in res["piezas"]:
            dx, dy = pos[pz["nombre"]]
            pos_, idx = _pack(*pz["placa"], dx=dx, dy=dy)
            parts.append({"name": "MACETA", "pieza": pz["nombre"], "positions": pos_, "indices": idx,
                          "triangles": len(pz["placa"][1])})
            if pz["nombre"] == "LISTA":
                pos_, idx = _pack(*pz["letras"], dx=dx, dy=dy)
                parts.append({"name": "LETRAS", "pieza": pz["nombre"], "positions": pos_,
                              "indices": idx, "triangles": len(pz["letras"][1])})
                continue
            # letras separadas en "de palabra" y "de relleno" para mostrar la solución
            for grupo, cond in (("LETRAS", False), ("SOLUCION", True)):
                V, F = [], []
                for ch, (x, y), (r, c) in pz["celdas"]:
                    if ((r, c) in sol) != cond:
                        continue
                    glif, _ = sc.glifo(ch, cap)
                    for ext, huecos in glif:
                        sc.prisma([(x + a, y + b) for a, b in ext],
                                  [[(x + a, y + b) for a, b in hh] for hh in huecos],
                                  p["base"] - 0.3, p["base"] + p["relieve"], V, F)
                if F:
                    pos_, idx = _pack(V, F, dx, dy)
                    parts.append({"name": grupo, "pieza": pz["nombre"], "positions": pos_,
                                  "indices": idx, "triangles": len(F)})
        if res.get("bloque"):                    # un bloque modelo: la web lo copia en cada letra
            pos_, idx = _pack(*res["bloque"])
            parts.append({"name": "BLOQUE", "pieza": "BLOQUE", "positions": pos_, "indices": idx,
                          "triangles": len(res["bloque"][1])})
    rep["seconds"] = round(time.time() - t0, 2)
    rep["grid"] = sopa["grid"]
    rep["ubicadas"] = sopa["ubicadas"]
    rep["faltan"] = sopa["faltan"]
    rep["piezas_mm"] = {pz["nombre"]: pz["medidas_mm"] for pz in res["piezas"]}
    p = res["params"]
    for u in rep["ubicadas"]:                    # dónde va cada bloque de la palabra (mm)
        u["centros"] = [list(sc.centro_celda(sopa, p, u["fila"] + u["df"] * i, u["col"] + u["dc"] * i))
                        for i in range(len(u["palabra"]))]
    rep["base_mm"] = p["base"]
    return {"summary": rep, "parts": parts}


def _layout(res):
    """Piezas acomodadas en filas sobre la cama (sin encimarse)."""
    cama = res["params"]["cama"]
    out, x, y, fila_h = [], 0.0, 0.0, 0.0
    objetos = [(pz["nombre"], sc.unir(pz["placa"], pz["letras"])) for pz in res["piezas"]]
    if res.get("bloque"):
        for i in range(res["report"]["bloques"]):
            objetos.append(("BLOQUE_%02d" % (i + 1), res["bloque"]))
    for nombre, (V, F) in objetos:
        xs = [v[0] for v in V]
        ys = [v[1] for v in V]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if x > 0 and x + w > max(cama, w) * 1.0 + 1e-6:
            x, y, fila_h = 0.0, y + fila_h + SEPARACION, 0.0
        dx, dy = x - min(xs), y - min(ys)
        out.append(("%s_%s" % (res["report"]["sku"], nombre),
                    [(a + dx, b + dy, c) for a, b, c in V], F))
        x += w + SEPARACION
        fila_h = max(fila_h, h)
    return out


def _resultado(opts):
    res = sc.build_sopa(opts)
    if not res["report"]["valid"]:
        raise ValueError("; ".join(res["report"]["errors"]) or "sopa inválida")
    return res


def export_3mf(opts):
    res = _resultado(opts)
    rep = res["report"]
    objs = _layout(res)
    meta = {"Title": rep["sku"], "Designer": "Eden3D",
            "Copyright": "© Eden3D — Yoel Almirón. Todos los derechos reservados.",
            "LicenseTerms": LICENSE_NOTE,
            "Description": "Sopa de letras %dx%d, %d piezas · motor sopa %s · cambio de color a %.1f mm"
                           % (rep["filas"], rep["cols"], rep["piezas"], sc.SOPA_VERSION,
                              rep["cambio_color_mm"]),
            "CreationDate": time.strftime("%Y-%m-%d")}
    res_xml, items = [], []
    for i, (name, V, F) in enumerate(objs):
        verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in V)
        tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
        res_xml.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices>'
                       '<triangles>%s</triangles></mesh></object>' % (i + 1, _xml(name), verts, tris))
        items.append('<item objectid="%d"/>' % (i + 1))
    md = "".join('<metadata name="%s">%s</metadata>' % (k, _xml(v)) for k, v in meta.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="es-AR" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">%s'
             '<resources>%s</resources><build>%s</build></model>') % (md, "".join(res_xml), "".join(items))
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    name = rep["sku"] + ".3mf"
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(path)
    except OSError:
        pass
    return name, data


def export_stl(opts):
    from eden_core import write_stl
    res = _resultado(opts)
    V, F = [], []
    for _, Vs, Fs in _layout(res):
        o = len(V)
        V.extend(Vs)
        F.extend((a + o, b + o, c + o) for a, b, c in Fs)
    name = res["report"]["sku"] + ".stl"
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
    write_stl(path, V, F, name="Eden3D Sopa (c) Yoel Almiron - uso personal")
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        os.remove(path)
    except OSError:
        pass
    return name, data


def _xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))
