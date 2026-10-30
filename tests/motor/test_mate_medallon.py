# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Mate: modelos lisos (MAT-017), tipografías (MAT-018) y medallón encastrable (MAT-019)."""
import io
import json
import math
import os
import zipfile

import pytest

import mate_core as mc
import mate_deco as md
import mate_fuentes as mf
import mate_web

TAU = 2.0 * math.pi
_CACHE = {}


def mate(tipo, calidad="normal", **deco):
    d = dict({"tipo": "texto", "texto": "10", "fuente": "russo_one", "medallon": {}}, **deco)
    key = (tipo, calidad, json.dumps(d, sort_keys=True))
    if key not in _CACHE:
        _CACHE[key] = mc.build_mate({"tipo": tipo, "inserto": "polimero", "deco": d, "calidad": calidad})
    return _CACHE[key]


def tallada(r, calidad="normal"):
    """La piel del mate con el bolsillo (como quedó en la malla)."""
    p = r["params"]
    return mc.filas_exteriores(p, r["report"]["escala"], r["M"], paso=0.8 if calidad == "normal" else 1.5)[0]


# ----------------------------------------------------------------- MAT-017
@pytest.mark.spec("MAT-017")
def test_ningun_modelo_trae_circulos():
    for T in mc.TIPOS:
        assert "medallones" not in (T.get("extras") or {}), T["id"]


@pytest.mark.spec("MAT-017")
@pytest.mark.parametrize("tid", ["vaso_redondeado", "labio_grueso"])
def test_modelos_de_revolucion_lisos(tid):
    p = mc.parametros_tipo(tid)
    for z, rs in mc.filas_exteriores(p, 1.0, 96)[0]:
        assert max(rs) - min(rs) < 1e-9


@pytest.mark.spec("MAT-017")
@pytest.mark.parametrize("tid", ["patitas", "facetado"])
def test_frente_sin_rebajes(tid):
    p = mc.parametros_tipo(tid)
    fs = mc.filas_exteriores(p, 1.0, 96)[0]
    # comparado con la misma piel calculada sin ningún extra de rebaje: idéntica
    q = dict(p, extras={k: v for k, v in (p.get("extras") or {}).items() if k != "medallones"})
    assert fs == mc.filas_exteriores(q, 1.0, 96)[0]


# ----------------------------------------------------------------- MAT-018
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÁÉÍÓÚÑáéíóúñ"


@pytest.mark.spec("MAT-018")
def test_tipografias_completas_y_con_licencia():
    assert len(mf.FUENTES) == 9 and mf.IDS[0] == "eden" and mf.DEFECTO == "archivo_black"
    lic = open(os.path.join(mf.DIR, "LICENCIAS.md"), encoding="utf-8").read()
    for fid in mf.IDS[1:]:
        f = mf.cargar(fid)
        falta = [c for c in LETRAS if c not in f["glifos"]]
        assert not falta, (fid, falta)
        assert f["licencia"] in ("OFL-1.1", "Apache-2.0")
        assert fid + ".json" in lic and f["licencia"].split("-")[0] in lic.replace("Open Font", "OFL")
    assert [f["id"] for f in mate_web.info()["deco"]["fuentes"]] == mf.IDS


@pytest.mark.spec("MAT-018")
@pytest.mark.parametrize("fid", [f for f, _ in mf.FUENTES])
def test_relieve_cerrado_en_cada_tipografia(fid):
    r = mc.build_mate({"tipo": "cilindrico", "inserto": "polimero",
                       "deco": {"tipo": "texto", "texto": "Mate 10", "fuente": fid, "alto": 12}})
    rep = r["report"]
    assert rep["valid"] and rep["cerrada"], rep["errors"]
    assert rep["deco"]["fuente"] == fid and rep["deco"]["cerrada"]


def area(forma):
    a = 0.0
    for P in forma["polys"]:
        a += sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1])) / 2.0
    return abs(a)


@pytest.mark.spec("MAT-018")
def test_la_gruesa_cubre_mas_que_la_de_trazos():
    def cubierto(fid):
        f = md.forma_texto("MATE", 12, fid)
        res = 0.2
        bb = md._bbox(f)
        nu, nv = int((bb[2] - bb[0]) / res) + 3, int((bb[3] - bb[1]) / res) + 3
        g = md.campo(f, bb[0] - res, bb[1] - res, nu, nv, res)
        return sum(1 for col in g for v in col if v > 0) * res * res / (f["ancho"] * 12.0)
    assert cubierto("archivo_black") > 1.3 * cubierto("eden")


@pytest.mark.spec("MAT-018")
def test_caracter_fuera_de_la_tipografia():
    with pytest.raises(ValueError) as e:
        md.forma_texto("Hola ☃", 10, "anton")
    assert "no están en la tipografía" in str(e.value)
    assert mate_web.check_texto("Hola ☃", "anton")["error"]
    assert mate_web.check_texto("  Ñandú  ", "bungee") == {"text": "Ñandú", "error": None,
                                                         "max_len": mf.MAX_LEN}


@pytest.mark.spec("MAT-018")
def test_grosor_engorda_el_relieve():
    def medida(g):
        r = mc.build_mate({"tipo": "cilindrico", "inserto": "polimero",
                           "deco": {"tipo": "texto", "texto": "TEXTO", "alto": 12, "grosor": g}})
        V = r["deco"][0]
        zs = [v[2] for v in V]
        angs = [math.atan2(v[1], v[0]) for v in V]
        R = r["report"]["deco"]["radio"]
        return (max(angs) - min(angs)) * R, max(zs) - min(zs)
    a0, h0 = medida(0.0)
    a1, h1 = medida(1.0)
    assert a1 - a0 == pytest.approx(2.0, abs=0.3)
    assert h1 - h0 == pytest.approx(2.0, abs=0.3)


# ----------------------------------------------------------------- MAT-019
MODELOS_MED = ["vaso_redondeado", "imperial_clasico", "facetado", "patitas", "lowpoly_torcido", "rombos"]


@pytest.mark.spec("MAT-019")
@pytest.mark.parametrize("tid", MODELOS_MED)
def test_medallon_encastra_sin_chocar(tid):
    r = mate(tid)
    rep = r["report"]
    assert rep["valid"] and rep["cerrada"], rep["errors"]
    info = rep["medallon"]
    for V, F in r["medallon"]["shells"]:
        assert mc.mesh_check(F)["closed"] and mc.mesh_volume(V, F) > 0
    filas, M = tallada(r), r["M"]
    disco = r["medallon"]["shells"][0][0]
    peor = max(mc._radio_en(filas, M, z, math.atan2(y, x)) - math.hypot(x, y) for x, y, z in disco)
    assert peor < 0.01                                 # ninguna parte de la pieza dentro de la pared
    assert info["juego_mm"][0] == pytest.approx(0.2)
    assert info["juego_mm"][1] <= 0.2 + 0.8
    # el relieve ya no se suma al mate: va en la pieza
    assert len(r["shells"]) == 1 + (1 if (mc.tipo(tid).get("extras") or {}).get("aletas") else 0)


@pytest.mark.spec("MAT-019")
@pytest.mark.parametrize("tid", ["vaso_redondeado", "facetado"])
def test_bolsillo_tiene_el_diametro_y_la_profundidad(tid):
    r = mate(tid)
    info = r["report"]["medallon"]
    filas, M = tallada(r), r["M"]
    th0, zc, plano = math.radians(info["angulo"]), info["z"], info["plano_mm"]
    Rb = info["diam_mm"] / 2.0
    p = r["params"]
    orig = mc.filas_exteriores(dict(p, extras={k: v for k, v in p["extras"].items() if k != "bolsillo"}),
                               r["report"]["escala"], M, paso=0.8)[0]
    for k in range(72):
        ph = TAU * k / 72
        for rho in (0.0, 0.5 * Rb, Rb - 0.05):
            a, b = rho * math.cos(ph), rho * math.sin(ph)
            th = th0 + math.atan2(a, plano)
            piso = math.hypot(plano, a)
            # adentro del diámetro pedido, a la altura del fondo, no hay pared del mate
            assert mc._radio_en(filas, M, zc + b, th) <= piso + 0.02
            # y el bolsillo tiene al menos la profundidad pedida
            assert mc._radio_en(orig, M, zc + b, th) - piso >= info["prof_mm"] - 0.05


@pytest.mark.spec("MAT-019")
def test_diseno_entra_en_el_disco():
    r = mate("vaso_redondeado", texto="TecnoBear", alto=30)
    info = r["report"]["medallon"]
    assert r["report"]["deco"]["ajustado"]
    Rp = info["diam_pieza_mm"] / 2.0
    th0, zc = math.radians(info["angulo"]), info["z"]
    n, t = (math.cos(th0), math.sin(th0)), (-math.sin(th0), math.cos(th0))
    V = r["medallon"]["shells"][1][0]
    lat = max(math.hypot(x * t[0] + y * t[1], z - zc) for x, y, z in V)
    assert lat < Rp


@pytest.mark.spec("MAT-019")
def test_pieza_plana_en_la_cama_y_descargas():
    o = {"tipo": "vaso_redondeado", "inserto": "polimero",
         "deco": {"tipo": "texto", "texto": "10", "medallon": {"diam": 30, "holgura": 0.3}}}
    r = mc.build_mate(dict(o, calidad="normal"))
    cama = r["medallon"]["cama"]
    zs = [v[2] for V, _ in cama for v in V]
    assert min(zs) == pytest.approx(0.0, abs=1e-6)
    disco = cama[0][0]
    abajo = [v for v in disco if abs(v[2]) < 1e-6]
    assert len(abajo) > 0.4 * len(disco)               # toda la cara de atrás apoya en z = 0
    assert max(math.hypot(v[0], v[1]) for v in disco) == pytest.approx(15.0 - 0.3, abs=0.01)
    name, data = mate_web.export_stl(o, "MEDALLON")
    assert name.endswith("_MEDALLON.stl") and len(data) > 84
    name, data = mate_web.export_3mf(o)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        modelo = z.read("3D/3dmodel.model").decode("utf-8")
    assert "_MEDALLON" in modelo
    with pytest.raises(ValueError):
        mate_web.export_stl(dict(o, deco={"tipo": "texto", "texto": "10"}), "MEDALLON")


@pytest.mark.spec("MAT-019")
def test_web_partes_con_medallon():
    r = mate_web.build({"tipo": "imperial_clasico", "inserto": "polimero",
                        "deco": {"tipo": "texto", "texto": "10", "medallon": {}}})
    assert [p["name"] for p in r["parts"]] == ["MACETA", "RELIEVE", "MEDALLON", "INSERTO"]
    piel = r["summary"]["piel"]
    assert len(piel["r"]) == len(piel["z"]) * piel["m"]
