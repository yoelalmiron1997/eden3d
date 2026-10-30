# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
Convierte tipografías libres (OFL / Apache) a contornos compactos para el relieve del mate.

    python tools/fuentes.py --origen <carpeta con los .woff/.ttf>

Las fuentes salen de los paquetes npm @fontsource/<nombre> (archivo files/<nombre>-latin-
<peso>-normal.woff). Escribe engine/fuentes/<id>.json: em = 1000, contornos ya aplanados
(curvas → segmentos de ~8 unidades), avance de cada letra y kerning básico (tabla kern o
pares de GPOS formato 1). Se usan con la regla "nonzero", como las fuentes TrueType/CFF.
Las licencias van en engine/fuentes/LICENCIAS.md.
"""
import argparse
import json
import math
import os

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "engine", "fuentes")

# id, nombre en la web, archivo, licencia, autor
FUENTES = [
    ("archivo_black", "Archivo Black (bloque)", "archivo-black-latin-400-normal.woff", "OFL-1.1",
     "Omnibus-Type"),
    ("anton", "Anton (condensada)", "anton-latin-400-normal.woff", "OFL-1.1", "Vernon Adams"),
    ("fredoka", "Fredoka (redondeada)", "fredoka-latin-700-normal.woff", "OFL-1.1",
     "Milena Brandão, Hafontia"),
    ("lilita_one", "Lilita One (gruesa)", "lilita-one-latin-400-normal.woff", "OFL-1.1",
     "Juan Montoreano"),
    ("russo_one", "Russo One (deportiva)", "russo-one-latin-400-normal.woff", "OFL-1.1",
     "Jovanny Lemonad"),
    ("bungee", "Bungee (cartel)", "bungee-latin-400-normal.woff", "OFL-1.1", "David Jonathan Ross"),
    ("luckiest_guy", "Luckiest Guy (cómic)", "luckiest-guy-latin-400-normal.woff", "Apache-2.0",
     "Astigmatic"),
    ("pacifico", "Pacifico (cursiva)", "pacifico-latin-400-normal.woff", "OFL-1.1",
     "Vernon Adams, Jacques Le Bailly, Botjo Nikoltchev, Ani Petrova"),
]

CHARS = (" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
         "abcdefghijklmnopqrstuvwxyz{|}~¡¿°ºª´ÁÉÍÓÚÜÑáéíóúüñ")
TOL = 8.0            # unidades (em 1000) por segmento de curva (≈0,1 mm en una letra de 13 mm)


class Aplanar(BasePen):
    def __init__(self, glyphset, k):
        BasePen.__init__(self, glyphset)
        self.k = k
        self.contornos = []
        self.cur = None

    def _p(self, p):
        return (p[0] * self.k, p[1] * self.k)

    def _moveTo(self, p):
        self.cur = [self._p(p)]
        self.contornos.append(self.cur)

    def _lineTo(self, p):
        self.cur.append(self._p(p))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        p1, p2, p3 = self._p(p1), self._p(p2), self._p(p3)
        largo = math.dist(p0, p1) + math.dist(p1, p2) + math.dist(p2, p3)
        n = max(2, int(math.ceil(largo / TOL)))
        for i in range(1, n + 1):
            t = i / float(n)
            m = 1 - t
            self.cur.append(tuple(m ** 3 * p0[j] + 3 * m * m * t * p1[j] + 3 * m * t * t * p2[j] +
                                  t ** 3 * p3[j] for j in range(2)))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        p1, p2 = self._p(p1), self._p(p2)
        n = max(2, int(math.ceil((math.dist(p0, p1) + math.dist(p1, p2)) / TOL)))
        for i in range(1, n + 1):
            t = i / float(n)
            m = 1 - t
            self.cur.append(tuple(m * m * p0[j] + 2 * m * t * p1[j] + t * t * p2[j] for j in range(2)))

    def _closePath(self):
        if self.cur and len(self.cur) > 1 and math.dist(self.cur[0], self.cur[-1]) < 1e-6:
            self.cur.pop()
        self.cur = None

    _endPath = _closePath


def _kerning(font, cmap, k):
    pares = {}
    inv = {}
    for ch in CHARS:
        g = cmap.get(ord(ch))
        if g:
            inv.setdefault(g, []).append(ch)
    if "kern" in font:
        for t in font["kern"].kernTables:
            for (a, b), v in t.kernTable.items():
                for ca in inv.get(a, ()):
                    for cb in inv.get(b, ()):
                        pares[ca + cb] = round(v * k)
    if "GPOS" in font and font["GPOS"].table.LookupList:
        for lk in font["GPOS"].table.LookupList.Lookup:
            for st in lk.SubTable:
                if lk.LookupType == 9:
                    st = st.ExtSubTable
                if getattr(st, "LookupType", lk.LookupType) != 2 or st.Format != 1:
                    continue
                cov = st.Coverage.glyphs
                for gi, ps in zip(cov, st.PairSet):
                    for pv in ps.PairValueRecord:
                        v = getattr(pv.Value1, "XAdvance", 0) if pv.Value1 else 0
                        if not v:
                            continue
                        for ca in inv.get(gi, ()):
                            for cb in inv.get(pv.SecondGlyph, ()):
                                pares.setdefault(ca + cb, round(v * k))
    return {p: v for p, v in pares.items() if v}


def convertir(path, fid, nombre, licencia, autor):
    font = TTFont(path)
    k = 1000.0 / font["head"].unitsPerEm
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    hmtx = font["hmtx"]
    glifos = {}
    for ch in CHARS:
        g = cmap.get(ord(ch))
        if not g:
            continue
        pen = Aplanar(gs, k)
        gs[g].draw(pen)
        cs = [[v for p in c for v in (round(p[0]), round(p[1]))] for c in pen.contornos if len(c) >= 3]
        glifos[ch] = {"a": round(hmtx[g][0] * k), "c": cs}
    os2 = font["OS/2"]
    cap = getattr(os2, "sCapHeight", 0) or 700
    return {"id": fid, "nombre": nombre, "licencia": licencia, "autor": autor,
            "cap": round(cap * k), "asc": round(os2.sTypoAscender * k),
            "desc": round(os2.sTypoDescender * k), "glifos": glifos,
            "kern": _kerning(font, cmap, k)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", required=True)
    a = ap.parse_args()
    os.makedirs(DEST, exist_ok=True)
    for fid, nombre, arch, lic, autor in FUENTES:
        path = None
        for raiz, _, files in os.walk(a.origen):
            if arch in files:
                path = os.path.join(raiz, arch)
                break
        if not path:
            raise SystemExit("falta %s" % arch)
        d = convertir(path, fid, nombre, lic, autor)
        out = os.path.join(DEST, fid + ".json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
        print("%-14s %3d glifos %4d pares  %6.1f KB" % (fid, len(d["glifos"]), len(d["kern"]),
                                                       os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
