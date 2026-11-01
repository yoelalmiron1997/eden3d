# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Chapitas para collares en la web (CHA-005)."""
import json

import pytest

from web_helpers import READY_MS

T = "[data-testid=%s]"


def esperar(pg, n):
    pg.wait_for_function("(n) => window.__chapita.builds > n && !window.__chapita.busy", arg=n, timeout=READY_MS)


@pytest.mark.spec("CHA-005")
def test_chapita_en_la_web(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    errores = []
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "chapita.html")
    pg.wait_for_function("window.__chapita && window.__chapita.builds >= 1 && !window.__chapita.busy", timeout=READY_MS)
    s = pg.evaluate("window.__chapita.summary")
    assert s["valid"] and s["sku"] == "Chapita-Hueso-Roma"
    v = pg.evaluate("window.__chapita.viewer")
    assert v["meshes"] == ["CHAPITA"] and v["argolla"]
    assert pg.locator(T % "chk-patitas").is_visible()
    # otra forma y otro nombre
    b = pg.evaluate("window.__chapita.builds")
    pg.locator(T % "forma-gato").click()
    esperar(pg, b)
    assert pg.evaluate("window.__chapita.summary.forma") == "gato"
    assert not pg.locator(T % "chk-patitas").is_visible()
    b = pg.evaluate("window.__chapita.builds")
    pg.locator(T % "inp-nombre").fill("Michi")
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text() == "Chapita-Gato-Michi"
    # dos colores: aparece la malla de las letras y su STL
    b = pg.evaluate("window.__chapita.builds")
    pg.locator(T % "sel-colores").select_option("doble")
    esperar(pg, b)
    assert pg.evaluate("window.__chapita.viewer.meshes") == ["CHAPITA", "LETRAS"]
    assert pg.locator(T % "btn-stl-letras").is_visible()
    for btn, nombre in (("btn-stl", "Chapita-Gato-Michi_CHAPITA.stl"), ("btn-stl-letras", "Chapita-Gato-Michi_LETRAS.stl"),
                        ("btn-3mf", "Chapita-Gato-Michi.3mf")):
        with pg.expect_download(timeout=READY_MS) as dl:
            pg.locator(T % btn).click()
        assert dl.value.suggested_filename == nombre
    assert not errores, errores
    ctx.close()


@pytest.mark.spec("CHA-005")
def test_tarjeta_chapita_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-chapita")
    assert card.is_visible() and "Chapitas para collares" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-chapita]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-chapita").is_visible()
    assert pg.locator(T % "abrir-chapita").get_attribute("href") == "chapita.html"
    ctx.close()
