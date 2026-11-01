# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Trofeos para eventos en la web (TRO-005)."""
import json

import pytest

from web_helpers import READY_MS

T = "[data-testid=%s]"


def esperar(pg, n):
    pg.wait_for_function("(n) => window.__trofeo.builds > n && !window.__trofeo.busy", arg=n, timeout=READY_MS)


@pytest.mark.spec("TRO-005")
def test_trofeo_en_la_web(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    errores = []
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "trofeo.html")
    pg.wait_for_function("window.__trofeo && window.__trofeo.builds >= 1 && !window.__trofeo.busy", timeout=READY_MS)
    s = pg.evaluate("window.__trofeo.summary")
    assert s["valid"] and s["sku"] == "Trofeo-Estrella-CAMPEON"
    assert s["linea1"] == "CAMPEÓN" and s["linea2"] == "Torneo 2026"
    v = pg.evaluate("window.__trofeo.viewer")
    assert v["meshes"] == ["FIGURA", "DETALLE", "BASE", "TEXTO"] and v["triangles"] > 1000
    assert pg.locator(T % "inp-texto-figura").is_visible() and not pg.locator(T % "inp-caracter").is_visible()
    assert not pg.locator(T % "btn-stl-detalle").is_visible()
    # número: aparece su campo y se esconde el texto de la figura
    b = pg.evaluate("window.__trofeo.builds")
    pg.locator(T % "figura-numero").click()
    esperar(pg, b)
    assert pg.evaluate("window.__trofeo.summary.figura") == "numero"
    assert pg.locator(T % "inp-caracter").is_visible() and not pg.locator(T % "inp-texto-figura").is_visible()
    b = pg.evaluate("window.__trofeo.builds")
    pg.locator(T % "inp-caracter").fill("2")
    esperar(pg, b)
    assert pg.evaluate("window.__trofeo.summary.caracter") == "2"
    # otra figura y otro texto
    b = pg.evaluate("window.__trofeo.builds")
    pg.locator(T % "figura-copa").click()
    esperar(pg, b)
    b = pg.evaluate("window.__trofeo.builds")
    pg.locator(T % "inp-linea1").fill("Mejor arquero")
    esperar(pg, b)
    assert pg.locator(T % "sku").inner_text() == "Trofeo-Copa-Mejor-arquero"
    # dos colores: los STL del detalle y del texto
    b = pg.evaluate("window.__trofeo.builds")
    pg.locator(T % "sel-colores").select_option("dos")
    esperar(pg, b)
    assert pg.evaluate("window.__trofeo.summary.piezas") == ["FIGURA", "DETALLE", "BASE", "TEXTO"]
    assert pg.locator(T % "btn-stl-detalle").is_visible() and pg.locator(T % "btn-stl-texto").is_visible()
    sku = "Trofeo-Copa-Mejor-arquero"
    for btn, nombre in (("btn-stl-figura", sku + "_FIGURA.stl"), ("btn-stl-base", sku + "_BASE.stl"),
                        ("btn-stl-texto", sku + "_TEXTO.stl"), ("btn-3mf", sku + ".3mf")):
        with pg.expect_download(timeout=READY_MS) as dl:
            pg.locator(T % btn).click()
        assert dl.value.suggested_filename == nombre
    assert not errores, errores
    ctx.close()


@pytest.mark.spec("TRO-005")
def test_tarjeta_trofeo_en_el_inicio(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    pg.goto(base_url)
    card = pg.locator(T % "tool-trofeo")
    assert card.is_visible() and "Trofeos para eventos" in card.inner_text()
    pg.wait_for_function("document.querySelector('[data-testid=tool-imagen-trofeo]').naturalWidth > 0")
    card.click()
    assert pg.locator(T % "popup-trofeo").is_visible()
    assert pg.locator(T % "abrir-trofeo").get_attribute("href") == "trofeo.html"
    ctx.close()
