# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Topper para tortas en la web (TOP-005)."""
import json

import pytest

from web_helpers import READY_MS

T = "[data-testid=%s]"


def abrir(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    pg.console_errors = []
    pg.on("console", lambda m: pg.console_errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: pg.console_errors.append(str(e)))
    pg.goto(base_url + "topper.html")
    pg.wait_for_function("window.__topper && window.__topper.builds >= 1 && !window.__topper.busy", timeout=READY_MS)
    return pg


def esperar(pg, n):
    pg.wait_for_function("(n) => window.__topper.builds > n && !window.__topper.busy", arg=n, timeout=READY_MS)


@pytest.mark.spec("TOP-005")
def test_topper_en_la_web(browser, base_url):
    pg = abrir(browser, base_url)
    s = pg.evaluate("window.__topper.summary")
    assert s["valid"] and [l["texto"] for l in s["lineas"]] == ["Feliz", "Cumpleaños"]
    assert {l["fuente"] for l in s["lineas"]} == {"great_vibes"}
    v = pg.evaluate("window.__topper.viewer")
    assert v["meshes"] == ["TOPPER"] and v["torta"] and v["parado"]
    assert "sí" in pg.locator(T % "f-unida").inner_text()
    assert pg.locator(T % "sel-fuente-1" + " option").count() == 16
    # nombre en la línea 3
    b = pg.evaluate("window.__topper.builds")
    pg.locator(T % "linea-3").fill("Sofi")
    esperar(pg, b)
    assert [l["texto"] for l in pg.evaluate("window.__topper.summary.lineas")] == ["Feliz", "Cumpleaños", "Sofi"]
    # dos colores: base + letras
    b = pg.evaluate("window.__topper.builds")
    pg.locator(T % "sel-estilo").select_option("doble")
    esperar(pg, b)
    assert pg.evaluate("window.__topper.viewer.meshes") == ["TOPPER", "LETRAS"]
    assert pg.locator(T % "btn-stl-letras").is_visible() and pg.locator(T % "sl-letras").is_visible()
    # marco
    b = pg.evaluate("window.__topper.builds")
    pg.locator(T % "sel-marco").select_option("corazon")
    esperar(pg, b)
    assert pg.evaluate("window.__topper.summary.marco") == "corazon"
    # plano (como se imprime) y de vuelta en la torta
    pg.locator(T % "chk-torta").uncheck()
    v = pg.evaluate("window.__topper.viewer")
    assert not v["torta"] and not v["parado"]
    pg.locator(T % "chk-torta").check()
    assert pg.evaluate("window.__topper.viewer.parado")
    # descargas
    for btn, fin in (("btn-stl", "_TOPPER.stl"), ("btn-stl-letras", "_LETRAS.stl"), ("btn-3mf", ".3mf")):
        with pg.expect_download(timeout=READY_MS) as dl:
            pg.locator(T % btn).click()
        assert dl.value.suggested_filename.startswith("Topper-Feliz-Cumpleanos-Sofi")
        assert dl.value.suggested_filename.endswith(fin)
    # un carácter que la tipografía no tiene: error en español, sin romper la página
    b = pg.evaluate("window.__topper.builds")
    pg.locator(T % "linea-3").fill("Sofi ☃")
    esperar(pg, b)
    assert "no están en la tipografía" in pg.locator(T % "estado").inner_text()
    assert not pg.console_errors, pg.console_errors
    pg.context.close()


@pytest.mark.spec("TOP-005")
def test_tarjeta_topper_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-topper")
    assert card.is_visible() and "Topper para tortas" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-topper]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-topper").is_visible()
    assert pg.locator(T % "abrir-topper").get_attribute("href") == "topper.html"
    ctx.close()
