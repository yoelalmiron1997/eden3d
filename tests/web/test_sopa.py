# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Sopa de letras 3D (sopa.html) de punta a punta, con el motor real en Pyodide."""
import io
import zipfile

import pytest

from web_helpers import READY_MS, wait_sopa

T = "[data-testid=%s]"


@pytest.mark.spec("SOP-007")
def test_carga_y_arma_la_sopa(sopa_app):
    pg = sopa_app
    assert "Listo" in pg.locator(T % "estado").inner_text()
    assert pg.evaluate("window.__sopa.summary.valid")
    vw = pg.evaluate("window.__sopa.viewer")
    assert {"MACETA", "LETRAS"} <= set(vw["meshes"])
    assert len([p for p in vw["piezas"] if p != "LISTA"]) >= 4
    s = pg.evaluate("window.__sopa.summary")
    assert pg.locator(T % "tabla" + " tr").count() == s["filas"]
    assert pg.locator(T % "lista-palabras" + " button").count() == len(s["ubicadas"])
    assert "encastres" in pg.locator(T % "f-piezas").inner_text()
    assert not pg.console_errors, pg.console_errors


@pytest.mark.spec("SOP-007")
def test_cambiar_palabras_y_ver_solucion(sopa_app):
    pg = sopa_app
    b = pg.evaluate("window.__sopa.builds")
    pg.fill(T % "palabras", "perro\ngato\ncarpincho\nñandú\nhornero")
    wait_sopa(pg, b)
    s = pg.evaluate("window.__sopa.summary")
    assert sorted(u["palabra"] for u in s["ubicadas"]) == ["CARPINCHO", "GATO", "HORNERO", "PERRO", "ÑANDU"]
    pg.locator(T % "btn-ver-solucion").click()
    assert pg.locator(T % "tabla" + ".sol").count() == 1
    assert pg.locator(T % "tabla" + " td.w").count() >= 20
    assert pg.evaluate("window.__sopa.viewer.solucion") == "#e8562a"
    pg.locator(T % "btn-ver-solucion").click()
    pg.fill(T % "sl-separar", "80")
    pg.dispatch_event(T % "sl-separar", "input")
    assert pg.evaluate("window.__sopa.viewer.separacion") > 5
    b = pg.evaluate("window.__sopa.builds")
    pg.locator(T % "btn-mezclar").click()
    wait_sopa(pg, b)
    assert pg.evaluate("window.__sopa.summary.grid") != s["grid"]
    assert not pg.console_errors, pg.console_errors


@pytest.mark.spec("SOP-008")
def test_descarga_3mf(sopa_app):
    pg = sopa_app
    with pg.expect_download(timeout=READY_MS) as dl:
        pg.locator(T % "btn-3mf").click()
    d = dl.value
    assert d.suggested_filename.startswith("Sopa-") and d.suggested_filename.endswith(".3mf")
    with zipfile.ZipFile(io.BytesIO(open(d.path(), "rb").read())) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert model.count("<object ") == pg.evaluate("window.__sopa.summary.piezas") + 1


@pytest.mark.spec("SOP-008")
def test_tarjeta_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-sopa")
    assert card.is_visible() and "Sopa de letras" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-sopa]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-sopa").is_visible()
    assert pg.locator(T % "abrir-sopa").get_attribute("href") == "sopa.html"
    ctx.close()
