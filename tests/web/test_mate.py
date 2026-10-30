# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Mate con hueco (mate.html) de punta a punta, con el motor real en Pyodide."""
import os

import pytest

from web_helpers import READY_MS, wait_mate as esperar

T = "[data-testid=%s]"
INS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "motor", "insertos")


@pytest.mark.spec("MAT-008")
def test_carga_y_muestra_el_mate(mate_app):
    pg = mate_app
    assert "Listo" in pg.locator(T % "estado").inner_text()
    assert pg.locator(T % "sel-tipo" + " option").count() == 17
    assert pg.locator(T % "sel-inserto" + " option").count() == 4
    assert pg.evaluate("window.__mate.summary.valid")
    vw = pg.evaluate("window.__mate.viewer")
    assert vw["meshes"] == ["MACETA", "INSERTO"]
    assert vw["triangles"] > 10_000
    assert pg.locator(T % "sku").inner_text() == "Mate-IMPERIAL-CLASICO-POLIMERO"
    assert pg.locator(T % "f-pared").inner_text().endswith("mm")
    f0 = pg.evaluate("window.__mate.viewer.frames")
    pg.wait_for_function("(f) => window.__mate.viewer.frames > f + 2", arg=f0, timeout=60_000)
    n = pg.evaluate("""() => {
        const c = document.querySelector('[data-testid=visor] canvas');
        const t = document.createElement('canvas'); t.width = 120; t.height = 90;
        const g = t.getContext('2d'); g.drawImage(c, 0, 0, 120, 90);
        const d = g.getImageData(0, 0, 120, 90).data; let n = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i+3] > 0) n++;
        return n; }""")
    assert n > 1000
    assert not pg.console_errors, pg.console_errors


@pytest.mark.spec("MAT-008")
def test_cambiar_modelo_e_inserto(mate_app):
    pg = mate_app
    b = pg.evaluate("window.__mate.builds")
    pg.select_option(T % "sel-tipo", "cohete")
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text() == "Mate-COHETE-POLIMERO"
    b = pg.evaluate("window.__mate.builds")
    pg.select_option(T % "sel-inserto", "ambos")
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text() == "Mate-COHETE-AMBOS"
    assert "+" in pg.locator(T % "f-inserto").inner_text()
    pg.locator(T % "chk-inserto").uncheck()
    assert pg.evaluate("window.__mate.viewer.inserto") is False
    pg.locator(T % "chk-inserto").check()
    assert pg.evaluate("window.__mate.viewer.inserto") is True
    pg.locator(T % "chk-corte").check()
    assert pg.evaluate("window.__mate.viewer.cut") is True
    pg.locator(T % "chk-corte").uncheck()


@pytest.mark.spec("MAT-009")
def test_descarga_stl(mate_app):
    pg = mate_app
    with pg.expect_download(timeout=READY_MS) as dl:
        pg.locator(T % "btn-stl").click()
    d = dl.value
    assert d.suggested_filename.startswith("Mate-") and d.suggested_filename.endswith(".stl")
    data = open(d.path(), "rb").read()
    n = int.from_bytes(data[80:84], "little")
    assert len(data) == 84 + 50 * n and n > 10_000


@pytest.mark.spec("MAT-009")
def test_sube_stl_propio(mate_app, tmp_path):
    pg = mate_app
    pg.select_option(T % "sel-inserto", "propio")
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "stl-propio").set_input_files(os.path.join(INS, "Polimero_Mate.stl"))
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text().endswith("-PROPIO")
    assert "Listo" in pg.locator(T % "stl-msg").inner_text()
    malo = tmp_path / "caja.stl"
    malo.write_bytes(b"solid caja\nendsolid caja\n")
    pg.locator(T % "stl-propio").set_input_files(str(malo))
    pg.wait_for_function("window.__mate.stl && window.__mate.stl.name === 'caja.stl' && "
                         "window.__mate.stl.error", timeout=60_000)
    assert pg.locator(T % "stl-msg").inner_text()
    assert not pg.console_errors, pg.console_errors


@pytest.mark.spec("MAT-010")
def test_tarjeta_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-mate")
    assert card.is_visible()
    assert "Mate con hueco" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-mate]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-mate").is_visible()
    assert pg.locator(T % "abrir-mate").get_attribute("href") == "mate.html"
    ctx.close()


# ---------------------------------------------------------------- MAT-011..015
@pytest.mark.spec("MAT-011")
def test_nombres_de_insertos_en_la_web(mate_app):
    ops = mate_app.locator(T % "sel-inserto" + " option").all_inner_texts()
    assert ops[:2] == ["Polímero escalonado", "Polímero base"]


@pytest.mark.spec("MAT-012")
def test_marca_del_mate_solo_pro(browser, base_url):
    from web_helpers import open_mate
    pg = open_mate(browser, base_url, role="usuario")
    assert pg.locator(T % "marca-texto").is_disabled()
    assert pg.locator(T % "marca-candado").is_visible()
    assert pg.evaluate("window.__mate.summary.marca.texto") == "Eden3D"
    pg.context.close()
    pg = open_mate(browser, base_url, role="pro")
    assert not pg.locator(T % "marca-texto").is_disabled()
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "marca-texto").fill("TecnoBear")
    pg.locator(T % "marca-aplicar").click()
    esperar(pg, b)
    assert pg.evaluate("window.__mate.summary.marca.texto") == "TecnoBear"
    assert "TecnoBear" in pg.locator(T % "marca-msg").inner_text()
    pg.context.close()


@pytest.mark.spec("MAT-015")
def test_relieve_con_gumball(browser, base_url, tmp_path):
    from web_helpers import open_mate
    pg = open_mate(browser, base_url)
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "deco-texto").click()
    esperar(pg, b)
    v = pg.evaluate("window.__mate.viewer")
    assert v["relieve"] and v["gizmo"] and v["gizmoMode"] == "translate"
    d0 = pg.evaluate("window.__mate.summary.deco")
    assert d0["tipo"] == "texto" and d0["cerrada"]
    # mover: el pivote gira 30° alrededor del mate y sube 6 mm (como arrastrar el gumball)
    b = pg.evaluate("window.__mate.builds")
    pg.evaluate("""() => { const g = window.__mateGizmo, pv = g.object;
        pv.position.applyAxisAngle(new pv.position.constructor(0, 0, 1), Math.PI / 6); pv.position.z += 6;
        g.dispatchEvent({type: 'objectChange'}); g.dispatchEvent({type: 'dragging-changed', value: false}); }""")
    esperar(pg, b)
    d1 = pg.evaluate("window.__mate.summary.deco")
    assert d1["angulo"] == pytest.approx(d0["angulo"] + 30, abs=1)
    assert d1["z"] == pytest.approx(d0["z"] + 6, abs=0.6)
    # girar
    pg.locator(T % "giz-girar").click()
    assert pg.evaluate("window.__mate.viewer.gizmoMode") == "rotate"
    b = pg.evaluate("window.__mate.builds")
    pg.evaluate("""() => { const g = window.__mateGizmo, pv = g.object, Q = pv.quaternion.constructor;
        pv.quaternion.multiply(new Q().setFromAxisAngle(new pv.position.constructor(0, 0, 1), Math.PI / 4));
        g.dispatchEvent({type: 'objectChange'}); g.dispatchEvent({type: 'dragging-changed', value: false}); }""")
    esperar(pg, b)
    assert pg.evaluate("window.__mate.summary.deco.rot") == pytest.approx(45, abs=1)
    # escalar
    pg.locator(T % "giz-escala").click()
    b = pg.evaluate("window.__mate.builds")
    alto0 = pg.evaluate("window.__mate.summary.deco.alto")
    pg.evaluate("""() => { const g = window.__mateGizmo, pv = g.object; pv.scale.set(1.5, 1.5, 1);
        g.dispatchEvent({type: 'objectChange'}); g.dispatchEvent({type: 'dragging-changed', value: false}); }""")
    esperar(pg, b)
    assert pg.evaluate("window.__mate.summary.deco.alto") == pytest.approx(alto0 * 1.5, abs=0.2)
    # SVG
    svg = tmp_path / "logo.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>')
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "deco-svg").click()
    pg.locator(T % "deco-file").set_input_files(str(svg))
    pg.wait_for_function("(n) => window.__mate.builds > n && !window.__mate.busy && "
                         "window.__mate.summary.deco && window.__mate.summary.deco.tipo === 'svg'", arg=b, timeout=READY_MS)
    assert pg.evaluate("window.__mate.viewer.relieve")
    # cuña: se ve y se descarga
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "chk-cuna").check()
    esperar(pg, b)
    assert pg.evaluate("window.__mate.viewer.cuna")
    assert pg.evaluate("window.__mate.summary.cuna.angulo") == 45
    with pg.expect_download(timeout=READY_MS) as dl:
        pg.locator(T % "btn-stl-cuna").click()
    assert dl.value.suggested_filename.endswith("_CUNA.stl")
    assert not pg.console_errors, pg.console_errors
    pg.context.close()


ALTURAS = """() => { const m = window.__mateViewer.model.getObjectByName('RELIEVE');
  const p = m.geometry.attributes.position; let lo = 1e9, hi = -1e9;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const h = Math.hypot(x, y) - window.__matePiel(z, Math.atan2(y, x));
    lo = Math.min(lo, h); hi = Math.max(hi, h); }
  return [lo, hi]; }"""


@pytest.mark.spec("MAT-015")
def test_gumball_reapoya_el_relieve_sobre_la_piel(browser, base_url):
    from web_helpers import open_mate
    pg = open_mate(browser, base_url)
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "sel-tipo").select_option("labio_grueso")
    esperar(pg, b)
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "deco-texto").click()
    esperar(pg, b)
    prof = pg.evaluate("window.__mate.summary.deco.prof")
    lo, hi = pg.evaluate(ALTURAS)
    assert lo == pytest.approx(-0.8, abs=0.05) and hi == pytest.approx(prof, abs=0.05)
    # arrastre hacia el labio (donde el mate cambia de ancho): el relieve sigue pegado
    pg.evaluate("""() => { const g = window.__mateGizmo, pv = g.object;
        g.dispatchEvent({type: 'dragging-changed', value: true});
        pv.position.applyAxisAngle(new pv.position.constructor(0, 0, 1), 0.7); pv.position.z += 30;
        g.dispatchEvent({type: 'objectChange'}); }""")
    lo, hi = pg.evaluate(ALTURAS)
    assert lo == pytest.approx(-0.8, abs=0.05) and hi == pytest.approx(prof, abs=0.05)
    assert pg.evaluate("window.__mate.gizmo.moves") >= 1
    b = pg.evaluate("window.__mate.builds")
    pg.evaluate("() => window.__mateGizmo.dispatchEvent({type: 'dragging-changed', value: false})")
    esperar(pg, b)
    lo, hi = pg.evaluate(ALTURAS)
    assert lo == pytest.approx(-0.8, abs=0.05) and hi == pytest.approx(prof, abs=0.05)
    assert pg.evaluate("window.__mate.summary.deco.z") > 75
    assert not pg.console_errors, pg.console_errors
    pg.context.close()


@pytest.mark.spec("MAT-020")
def test_tipografias_y_medallon_en_la_web(browser, base_url):
    from web_helpers import open_mate
    pg = open_mate(browser, base_url)
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "deco-texto").click()
    esperar(pg, b)
    assert pg.locator(T % "sel-fuente" + " option").count() == 9
    assert pg.evaluate("window.__mate.summary.deco.fuente") == "archivo_black"
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "sel-fuente").select_option("pacifico")
    esperar(pg, b)
    assert pg.evaluate("window.__mate.summary.deco.fuente") == "pacifico"
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "sl-d-grosor").fill("0.8")
    pg.locator(T % "sl-d-grosor").dispatch_event("change")
    esperar(pg, b)
    assert pg.evaluate("window.__mate.summary.deco.grosor") == pytest.approx(0.8)
    b = pg.evaluate("window.__mate.builds")
    pg.locator(T % "chk-medallon").check()
    esperar(pg, b)
    assert "MEDALLON" in pg.evaluate("window.__mate.viewer.meshes")
    assert "juego" in pg.locator(T % "medallon-msg").inner_text()
    with pg.expect_download(timeout=READY_MS) as dl:
        pg.locator(T % "btn-stl-medallon").click()
    assert dl.value.suggested_filename.endswith("_MEDALLON.stl")
    assert not pg.console_errors, pg.console_errors
    pg.context.close()


@pytest.mark.spec("MAT-021")
def test_cebar_el_mate(browser, base_url):
    from web_helpers import open_mate
    pg = open_mate(browser, base_url)
    assert pg.evaluate("window.__mate.viewer.meshes") == ["MACETA", "INSERTO"]
    pg.locator(T % "btn-cebar").click()
    c = pg.evaluate("window.__mate.cebado")
    assert c["playing"] and c["fase"] == "llenar" and c["enEscena"]
    assert "CEBADO" in pg.evaluate("window.__mate.viewer.meshes")
    # recorre las fases con el reloj real (el visor limita cada cuadro a 0,1 s)
    pg.wait_for_function("window.__mate.cebado.tilt > 10", timeout=READY_MS)
    assert pg.evaluate("window.__mate.cebado.fase") == "montañita"
    pg.wait_for_function("window.__mate.cebado.fase === 'cebar'", timeout=READY_MS)
    pg.wait_for_function("window.__mate.cebado.fase === 'listo' && !window.__mate.cebado.playing",
                         timeout=READY_MS)
    c = pg.evaluate("window.__mate.cebado")
    assert c["cebados"] == 1 and c["tilt"] == 0 and c["bombilla"]
    pg.wait_for_function("window.__mate.cebado.vapor", timeout=READY_MS)
    cima = pg.evaluate("""() => { const c = window.__mateCebado; const p = c.yerba.geometry.attributes.position.array;
        let m = -1e9; for (let i = 2; i < p.length; i += 3) m = Math.max(m, p[i]); return m; }""")
    assert c["nivelAgua"] < cima - 5
    assert "Listo" in pg.locator(T % "cebado-fase").inner_text()
    # agua transparente y bombillas como las argentinas
    dif, op = pg.evaluate("""() => { const m = window.__mateViewer.mats.AGUA_MATE; const h = m.color.getHex();
        const c = [(h >> 16) & 255, (h >> 8) & 255, h & 255].map((x) => x / 255);   // sRGB, como se ve
        return [Math.max(...c) - Math.min(...c), m.opacity]; }""")
    assert dif < 0.15 and op < 0.5
    ops = pg.locator(T % "sel-bombilla" + " option").evaluate_all("(o) => o.map((x) => x.value)")
    assert ops == ["resorte", "color", "cuadrada", "cuchara", "pala"]
    assert c["estilo"] == "resorte"
    for e in ("cuchara", "pala"):
        pg.locator(T % "sel-bombilla").select_option(e)
        assert pg.evaluate("window.__mate.cebado.estilo") == e and pg.evaluate("window.__mate.cebado.bombilla")
    # gota y olas en el agua del mate
    g0 = c["gotas"]
    pg.locator(T % "btn-gota").click()
    pg.locator(T % "btn-olas").click()
    assert pg.evaluate("window.__mate.cebado.gotas") == g0 + 1
    # montañita más empinada: el agua queda más baja
    n0 = c["nivelAgua"]
    pg.locator(T % "sl-montanita").fill("60")
    pg.locator(T % "sl-montanita").dispatch_event("change")
    assert pg.evaluate("window.__mate.cebado.alfa") == 60
    assert pg.evaluate("window.__mate.cebado.nivelAgua") < n0
    # separar: el inserto sale con todo adentro
    pg.locator(T % "sl-separar").fill("100")
    pg.locator(T % "sl-separar").dispatch_event("input")
    assert pg.evaluate("window.__mate.cebado.separar") == 1
    assert pg.evaluate("window.__mateViewer.model.getObjectByName('INSERTO').position.z") > 50
    pg.locator(T % "btn-despiece").click()
    pg.wait_for_function("window.__mate.cebado.separar > 0 && window.__mate.cebado.separar < 1", timeout=READY_MS)
    pg.locator(T % "btn-despiece").click()
    # sin yerba ni agua vuelve la escena de siempre
    pg.locator(T % "chk-yerba").uncheck()
    pg.locator(T % "chk-agua").uncheck()
    assert pg.evaluate("window.__mate.viewer.meshes") == ["MACETA", "INSERTO"]
    assert not pg.console_errors, pg.console_errors
    pg.context.close()
