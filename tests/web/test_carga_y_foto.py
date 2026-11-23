# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Arranque temprano del motor y precarga desde el inicio (PER-004); foto supermuestreada
y completa aun en bajos recursos (REN-004)."""
import base64
import io
import json

import pytest
from PIL import Image

from web_helpers import READY_MS


@pytest.mark.spec("PER-004")
def test_el_inicio_precarga_el_motor(browser, base_url):
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(base_url + "index.html")
    pg.wait_for_function("document.querySelectorAll('link[rel=prefetch]').length >= 6", timeout=20_000)
    hrefs = pg.evaluate("[...document.querySelectorAll('link[rel=prefetch]')].map(l => l.getAttribute('href'))")
    assert "vendor/pyodide/pyodide.asm.wasm" in hrefs and "vendor/three/three.module.js" in hrefs
    ctx.close()


@pytest.mark.spec("PER-004", "REN-004")
def test_motor_temprano_y_foto_de_calidad(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    pg = ctx.new_page()
    errores = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "chapita.html")
    # el <head> ya creó el worker antes de que corran los módulos; la página lo tomó
    assert pg.evaluate("window.__motor === undefined || window.__motor === null || !!window.__motor.w")
    pg.wait_for_function("window.__chapita && window.__chapita.builds >= 1 && !window.__chapita.busy", timeout=READY_MS)
    assert pg.evaluate("window.__motor") is None, "la página tiene que tomar el worker del <head>"
    v = "window.__chapitaViewer"
    # que la calidad adaptativa no cambie el modo en medio de la prueba (CI sin placa de video)
    pg.evaluate(f"{v}.__bajar = {v}.setLowPower; {v}.setLowPower = () => {{}}")
    # en CI el navegador dibuja por software y ahí la foto sale como siempre (sería lentísima):
    # primero se comprueba eso y después se prueba el camino de un equipo con placa de video
    assert pg.evaluate(f"{v}.photo(300, 200).width") == 300
    if pg.evaluate(f"{v}.porSoftware"):
        assert pg.evaluate(f"{v}.ultimaFoto.escala") == 1 and pg.evaluate(f"{v}.ultimaFoto.completa") is False
        pg.evaluate(f"{v}.porSoftware = false")
    for bajo in (False, True):
        if bajo:
            pg.evaluate(f"{v}.__bajar.call({v})")
        estado = f"[{v}.renderer.shadowMap.enabled, {v}.renderer.domElement.width, {v}.ground.visible, !!{v}.scene.environment]"
        antes = pg.evaluate(estado)
        url = pg.evaluate(f"{v}.photo(600, 400, 'image/jpeg').url")
        info = pg.evaluate(f"{v}.ultimaFoto")
        assert info["width"] == 600 and info["height"] == 400 and info["escala"] == 2
        # en CI (sin placa de video) el visor puede haber pasado solo a bajos recursos
        assert info["completa"] is pg.evaluate(f"!!{v}.lowPower")
        im = Image.open(io.BytesIO(base64.b64decode(url.split(",")[1])))
        assert im.size == (600, 400)
        despues = pg.evaluate(estado)
        assert despues == antes, "el visor vuelve a quedar como estaba"
    assert not errores
    ctx.close()
