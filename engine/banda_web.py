# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
BANDA DE RECIBIDA — Puente entre el motor y la página web (banda.html)
======================================================================
    info()                 -> opciones, tipografías y límites
    build(opts)            -> piezas para el visor (el collar armado o las piezas sueltas) + reporte
    export_3mf(opts)       -> (nombre, bytes)  todas las cuentas; cada disco con sus letras como partes
    export_stl(opts)       -> (nombre, bytes)  un ZIP con un STL por pieza distinta y un LEEME
"""
import array
import io
import math
import os
import re
import time
import unicodedata
import zipfile

import banda_core as bc
import mate_fuentes
import cotizador

VERSION = bc.VERSION
LICENSE_NOTE = ("© TecnoBear — Yoel Almirón. Diseño protegido: uso personal y no comercial. "
                "Prohibida la venta o redistribución del archivo.")
SEPARACION = 6.0        # mm entre piezas en la cama
CAMA = 256.0


def info():
    return {"motor": VERSION,
            "separadores": [{"id": k, "nombre": n} for k, n in bc.SEPARADORES],
            "rellenos": [{"id": k, "nombre": n} for k, n in bc.RELLENOS],
            "caras": [{"id": k, "nombre": n} for k, n in bc.CARAS],
            "fuentes": [{"id": f, "nombre": n} for f, n in bc.FUENTES],
            "defecto": dict(bc.DEFECTO),
            "limites": {k: (list(v) if isinstance(v, tuple) else v) for k, v in bc.LIMITES.items()},
            "license": LICENSE_NOTE}


def _pack(V, F):
    return (array.array("f", [c for v in V for c in v]).tobytes(),
            array.array("I", [i for f in F for i in f]).tobytes())


def _nombre_letra(ch):
    t = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
    extra = "" if t == ch else "_tilde" if ch not in "Ññ" else "_enie"
    t = re.sub(r"[^A-Za-z0-9]", "", t) or "simbolo%d" % ord(ch)
    return t + extra


def _sku(o):
    t = unicodedata.normalize("NFKD", o["texto"]).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")[:28] or "Texto"
    return "Banda-%s-%dcm" % (t, int(round(o["largo"])))


def _sobre_mesa(V):
    z0 = min(v[2] for v in V)
    return [(x, y, z - z0) for x, y, z in V]


def cama(lado, grosor=1.6, r=8.0, n=10):
    """Cama de impresora (placa de lado x lado mm, esquinas redondeadas) bajo z = 0."""
    import math as _m
    h = lado / 2.0
    pts = []
    for cx, cy, a0 in ((h - r, h - r, 0), (-h + r, h - r, 90), (-h + r, -h + r, 180), (h - r, -h + r, 270)):
        for k in range(n + 1):
            a = _m.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * _m.cos(a), cy + r * _m.sin(a)))
    return bc.prisma([(pts, [])], -grosor, 0.0)


def piezas_sueltas(r):
    """Una de cada pieza distinta, como se imprimen, acomodadas y centradas sobre una cama de
    impresora (la de la A1 mini, 180 mm; si no entran, una de 256 mm)."""
    out = []
    orden = [k for k in r["piezas"] if k[0] == "DISCO"]
    orden += [k for k in (("CORAZON", None), ("PELOTITA", None)) if k in r["piezas"]]
    n = len(orden)
    cols = max(2, int(math.ceil(math.sqrt(n))))
    filas = int(math.ceil(n / float(cols)))
    paso = max(max(v[0] for v in V) - min(v[0] for v in V) for k, (V, F) in r["piezas"].items()) + SEPARACION
    for i, k in enumerate(orden):
        V, F = r["piezas"][k]
        xs, ys = [v[0] for v in V], [v[1] for v in V]
        c, f = i % cols, i // cols
        en_fila = min(cols, n - f * cols)                 # la última fila, centrada
        dx = (c - (en_fila - 1) / 2.0) * paso - (min(xs) + max(xs)) / 2.0
        dy = ((filas - 1) / 2.0 - f) * paso - (min(ys) + max(ys)) / 2.0
        out.append((k[0], [(a + dx, b + dy, z) for a, b, z in V], F))
        if k[0] == "DISCO":
            Vl, Fl = r["piezas"][("LETRAS", k[1])]
            out.append(("LETRAS", [(a + dx, b + dy, z) for a, b, z in Vl], Fl))
    lado = 180.0 if max(cols, filas) * paso + 10 <= 180.0 else max(256.0, max(cols, filas) * paso + 20)
    Vc, Fc = cama(lado)
    out.append(("CAMA", Vc, Fc))
    return out

VISTAS_ANIMADAS = ("persona", "pared")


def cuentas(r):
    """Para las vistas animadas (puesta en una persona, colgada en la pared): una malla por
    pieza distinta en el "marco de la cuenta" (el agujero sobre el eje x, centrado en el
    origen; la cara con la letra hacia +z y la parte de arriba de la letra hacia +y) y la
    secuencia de cuentas en el hilo. La página las reparte sobre el recorrido del hilo.
    -> (parts [(nombre, V, F)], secuencia [{pieza, letra, largo}])"""
    s = r["opciones"]["escala"]
    zc = {"DISCO": bc.H_DISCO * s / 2.0, "LETRAS": bc.H_DISCO * s / 2.0, "CORAZON": bc.CORAZON_T * s / 2.0}
    parts = []
    for (nombre, ch), (V, F) in r["piezas"].items():
        if nombre == "PELOTITA":
            V = bc._centrar_z(V, max(v[2] for v in V) / 2.0)
            V = [(z, y, -x) for x, y, z in V]          # el agujero (z) pasa a x
        else:
            V = [(x, y, z - zc[nombre]) for x, y, z in V]
        parts.append(("%s#%s" % (nombre, ch or ""), V, F))
    sec = []
    for it in r["collar"]:
        t = "letra" if it["pieza"] == "DISCO" else it["pieza"].lower()
        sec.append({"pieza": it["pieza"], "letra": it["letra"] or "", "largo": round(bc.largo_de(t, r["opciones"]), 3)})
    return parts, sec


def build(opts):
    t0 = time.time()
    o = dict(opts or {})
    vista = o.pop("vista", "collar")
    try:
        r = bc.construir(o)
    except ValueError as e:
        return {"summary": {"valid": False, "errors": [str(e)], "warnings": [], "sku": "—",
                            "seconds": round(time.time() - t0, 2)}, "parts": []}
    if vista in VISTAS_ANIMADAS:
        unicas, sec = cuentas(r)
        parts = []
        for nombre, V, F in unicas:
            pos, idx = _pack(V, F)
            parts.append({"name": nombre, "positions": pos, "indices": idx, "vertices": len(V), "triangles": len(F)})
        rep = dict(r["reporte"])
        s = r["opciones"]["escala"]
        rep.update({"valid": True, "errors": [], "warnings": rep.pop("avisos"), "sku": _sku(r["opciones"]),
                    "seconds": round(time.time() - t0, 2), "motor": VERSION, "vista": vista,
                    "triangulos": sum(p["triangles"] for p in parts),
                    "secuencia": sec, "n_texto": len(bc.secuencia(r["opciones"])),
                    "hueco_mm": round(bc.HUECO * s, 3), "hilo_r_mm": round(r["opciones"]["agujero"] * 0.36, 3),
                    "grosor_mm": round(bc.PELOTITA_D * s, 3), "largo_mm": round(r["reporte"]["largo_cm"] * 10.0, 1)})
        return {"summary": rep, "parts": parts}
    grupos = {}
    if vista == "piezas":
        for nombre, V, F in piezas_sueltas(r):
            grupos.setdefault(nombre, []).append((V, F))
    else:
        for item in r["collar"]:
            for nombre, V, F in bc.colocar(item, r["piezas"]):
                grupos.setdefault(nombre, []).append((V, F))
        s = r["opciones"]["escala"]
        grupos["HILO"] = [bc.hilo(r["radio"], r["sube"], r["opciones"]["agujero"] * 0.36, 240, 10)]
    parts = []
    for nombre in ("DISCO", "LETRAS", "CORAZON", "PELOTITA", "HILO", "CAMA"):
        if nombre not in grupos:
            continue
        V, F = bc.unir(grupos[nombre])
        pos, idx = _pack(V, F)
        parts.append({"name": nombre, "positions": pos, "indices": idx, "vertices": len(V), "triangles": len(F)})
    rep = dict(r["reporte"])
    rep.update({"valid": True, "errors": [], "warnings": rep.pop("avisos"), "sku": _sku(r["opciones"]),
                "seconds": round(time.time() - t0, 2), "motor": VERSION, "vista": vista,
                "triangulos": sum(p["triangles"] for p in parts)})
    return {"summary": rep, "parts": parts}


def _normal(opts):
    o = dict(opts or {})
    o.pop("vista", None)
    o["calidad"] = "normal"
    return o


def _xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _malla_xml(oid, nombre, V, F):
    verts = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in V)
    tris = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % f for f in F)
    return ('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles>'
            '</mesh></object>' % (oid, _xml(nombre), verts, tris))


def lista_impresion(r):
    """[(nombre, [(parte, V, F)], cantidad)]: cada pieza distinta, centrada y apoyada."""
    out = []
    for k in [k for k in r["piezas"] if k[0] == "DISCO"]:
        ch = k[1]
        V, F = r["piezas"][k]
        Vl, Fl = r["piezas"][("LETRAS", ch)]
        n = next(d["cantidad"] for d in r["reporte"]["discos"] if d["letra"] == ch)
        out.append(("Disco_%s" % _nombre_letra(ch), [("DISCO", V, F), ("LETRAS", Vl, Fl)], n))
    for k, nombre, clave in ((("CORAZON", None), "Corazon", "corazones"), (("PELOTITA", None), "Pelotita", "pelotitas")):
        if k in r["piezas"] and r["reporte"][clave]:
            V, F = r["piezas"][k]
            out.append((nombre, [(k[0], V, F)], r["reporte"][clave]))
    return out


def cotizar(opts):
    """Todas las cuentas del collar (cada disco con su cantidad) medidas para el cotizador."""
    o = _normal(opts)
    o["calidad"] = o.get("cotizar_calidad", "preview")    # para gramos alcanza la vista previa
    r = bc.construir(o)
    piezas = []
    for nombre, partes, cant in lista_impresion(r):
        g = nombre.replace("_", " ").replace(" tilde", " con tilde")
        for parte, V, F in partes:
            piezas.append(cotizador.pieza(g if parte != "LETRAS" else g + " · letra", V, F, cantidad=cant,
                                          color=2 if parte == "LETRAS" else 1, grupo=g))
    return cotizador.resultado(piezas, _sku(r["opciones"]), ["El hilo o la cinta del collar no se imprime."])


def export_3mf(opts):
    """Todas las cuentas del collar: cada pieza distinta se define una vez y se repite en
    la cama; los discos son un objeto con dos partes (disco y letras) para asignarles
    filamento en el laminador."""
    o = _normal(opts)
    r = bc.construir(o)
    sku = _sku(r["opciones"])
    meta = {"Title": sku, "Designer": "TecnoBear", "Copyright": "© TecnoBear — Yoel Almirón.",
            "LicenseTerms": LICENSE_NOTE, "Application": "TecnoBear Banda de recibida %s" % VERSION,
            "Description": "Collar '%s' de %.0f cm: %d discos, %d corazones, %d pelotitas"
                           % (r["reporte"]["texto"], r["reporte"]["largo_cm"], r["reporte"]["total_discos"],
                              r["reporte"]["corazones"], r["reporte"]["pelotitas"]),
            "CreationDate": time.strftime("%Y-%m-%d")}
    res, items, oid = [], [], 0
    lista = lista_impresion(r)
    x = y = fila = 0.0
    for nombre, partes, cant in lista:
        allv = [v for _, V, _ in partes for v in V]
        cx = (min(v[0] for v in allv) + max(v[0] for v in allv)) / 2.0
        cy = (min(v[1] for v in allv) + max(v[1] for v in allv)) / 2.0
        w = max(v[0] for v in allv) - min(v[0] for v in allv)
        h = max(v[1] for v in allv) - min(v[1] for v in allv)
        comps = []
        for parte, V, F in partes:
            oid += 1
            res.append(_malla_xml(oid, "%s_%s" % (nombre, parte), [(a - cx, b - cy, c) for a, b, c in V], F))
            comps.append('<component objectid="%d"/>' % oid)
        if len(partes) > 1:
            oid += 1
            res.append('<object id="%d" type="model" name="%s"><components>%s</components></object>'
                       % (oid, _xml(nombre), "".join(comps)))
        for _ in range(cant):
            if x > 0 and x + w > CAMA:
                x, y, fila = 0.0, y + fila + SEPARACION, 0.0
            items.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>'
                         % (oid, x + w / 2.0, y + h / 2.0))
            x += w + SEPARACION
            fila = max(fila, h)
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
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return sku + ".3mf", buf.getvalue()


def _stl_bytes(V, F, nombre):
    import struct
    out = io.BytesIO()
    head = ("TecnoBear Banda (c) Yoel Almiron - uso personal - %s" % nombre).encode("ascii", "ignore")[:80]
    out.write(head.ljust(80, b" "))
    out.write(struct.pack("<I", len(F)))
    for a, b, c in F:
        A, B, C = V[a], V[b], V[c]
        ux, uy, uz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
        wx, wy, wz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln, A[0], A[1], A[2], B[0], B[1], B[2],
                              C[0], C[1], C[2], 0))
    return out.getvalue()


def export_stl(opts):
    """ZIP con un STL por pieza distinta (los discos y sus letras por separado) y un LEEME
    con cuántas imprimir de cada una."""
    o = _normal(opts)
    r = bc.construir(o)
    rep = r["reporte"]
    sku = _sku(r["opciones"])
    buf = io.BytesIO()
    leeme = ["Banda de recibida '%s' - %.0f cm" % (rep["texto"], rep["largo_cm"]), "",
             "Cuántas imprimir de cada pieza:"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, partes, cant in lista_impresion(r):
            for parte, V, F in partes:
                fn = "%s.stl" % nombre if parte != "LETRAS" else "%s_letras.stl" % nombre
                z.writestr(fn, _stl_bytes(V, F, fn))
            leeme.append("  %-22s x %d%s" % (nombre, cant, "  (+ sus letras, de otro color)" if len(partes) > 1 else ""))
        leeme += ["", "Hilo o elástico de hasta Ø %.1f mm, unos %d cm (con lo que hace falta para atarlo)."
                  % (rep["agujero_mm"] - 1.0, rep["hilo_cm"]),
                  "Las letras se imprimen juntas con su disco (misma posición): en el laminador cargá los dos "
                  "STL como partes de un mismo objeto y asignales un filamento a cada uno.", "", LICENSE_NOTE]
        z.writestr("LEEME.txt", "\r\n".join(leeme))
    return sku + "_STL.zip", buf.getvalue()
