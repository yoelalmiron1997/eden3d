# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Banda de recibida en la web (BAN-004)."""
import json

import pytest

from web_helpers import READY_MS

T = "[data-testid=%s]"


def esperar(pg, n):
    pg.wait_for_function("(n) => window.__banda.builds > n && !window.__banda.busy", arg=n, timeout=READY_MS)


@pytest.mark.spec("BAN-004")
def test_banda_en_la_web(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    errores = []
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "banda.html")
    pg.wait_for_function("window.__banda && window.__banda.builds >= 1 && !window.__banda.busy", timeout=READY_MS)
    s = pg.evaluate("window.__banda.summary")
    assert s["valid"] and s["sku"] == "Banda-ME-RECIBI-130cm", (s, errores)
    assert s["total_discos"] == 8 and s["corazones"] > 10 and s["pelotitas"] > 10
    assert pg.evaluate("window.__banda.viewer.meshes") == ["DISCO", "LETRAS", "CORAZON", "PELOTITA", "HILO"]
    assert "8:" in pg.locator(T % "f-discos").inner_text()
    # otro texto
    b = pg.evaluate("window.__banda.builds")
    pg.locator(T % "inp-texto").fill("lic. ana")
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text() == "Banda-LIC-ANA-130cm"
    # sin separador y sólo pelotitas: no hay corazones
    b = pg.evaluate("window.__banda.builds")
    pg.locator(T % "sel-separador").select_option("nada")
    esperar(pg, b)
    b = pg.evaluate("window.__banda.builds")
    pg.locator(T % "sel-relleno").select_option("pelotitas")
    esperar(pg, b)
    assert pg.evaluate("window.__banda.summary.corazones") == 0
    assert "CORAZON" not in pg.evaluate("window.__banda.viewer.meshes")
    # piezas sueltas: sin hilo
    b = pg.evaluate("window.__banda.builds")
    pg.locator(T % "sec-vista").click() if not pg.locator(T % "modo-piezas").is_visible() else None
    pg.locator(T % "modo-piezas").click()
    esperar(pg, b)
    assert pg.evaluate("window.__banda.summary.vista") == "piezas"
    assert "HILO" not in pg.evaluate("window.__banda.viewer.meshes")
    # color
    pg.locator(T % "sel-color-letras").select_option("#e0457b")
    assert pg.evaluate("window.__banda.viewer.letras") == "#e0457b"
    for btn, nombre in (("btn-3mf", "Banda-LIC-ANA-130cm.3mf"), ("btn-stl", "Banda-LIC-ANA-130cm_STL.zip")):
        with pg.expect_download(timeout=READY_MS) as dl:
            pg.locator(T % btn).click()
        assert dl.value.suggested_filename == nombre
    assert not errores, errores
    ctx.close()


@pytest.mark.spec("BAN-004")
def test_tarjeta_banda_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-banda")
    assert card.is_visible() and "Banda de recibida" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-banda]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-banda").is_visible()
    assert pg.locator(T % "abrir-banda").get_attribute("href") == "banda.html"
    ctx.close()


@pytest.mark.spec("BAN-005")
def test_banda_puesta_y_en_la_pared(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    errores = []
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "banda.html")
    pg.wait_for_function("window.__banda && window.__banda.builds >= 1 && !window.__banda.busy", timeout=READY_MS)
    if not pg.locator(T % "modo-persona").is_visible():
        pg.locator(T % "sec-vista").click()
    for modo, escenario in (("persona", "MANIQUI"), ("pared", "PARED")):
        b = pg.evaluate("window.__banda.builds")
        pg.locator(T % ("modo-" + modo)).click()
        esperar(pg, b)
        e = pg.evaluate("window.__banda.viewer.escena")
        assert e["modo"] == modo and e["total"] == pg.evaluate("window.__banda.summary.cuentas")
        assert pg.evaluate("(n) => !!window.__bandaViewer.model.getObjectByName(n)", escenario)
        assert pg.locator(T % "btn-repetir").is_visible()
        # la soga avanza (la animación corre) y al terminar quedan todas enhebradas
        pg.wait_for_function("window.__bandaEscena.stats.frames > 2", timeout=20_000)
        pg.evaluate("window.__bandaEscena.terminar()")
        e = pg.evaluate("window.__banda.viewer.escena")
        assert e["fase"] == "lista" and e["enhebradas"] == e["total"]
        assert pg.evaluate("!!window.__bandaViewer.model.getObjectByName('HILO')")
        pg.locator(T % "btn-repetir").click()
        assert pg.evaluate("window.__bandaEscena.stats.fase") == "enhebrando"
    b = pg.evaluate("window.__banda.builds")
    pg.locator(T % "modo-collar").click()
    esperar(pg, b)
    assert pg.evaluate("window.__banda.viewer.escena.modo") is None
    assert not pg.locator(T % "btn-repetir").is_visible()
    assert not errores, errores
    ctx.close()
