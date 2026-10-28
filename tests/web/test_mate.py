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
    assert pg.locator(T % "sel-tipo" + " option").count() == 10
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
