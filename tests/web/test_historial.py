# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Deshacer / rehacer (HIS-001), De cero (HIS-002) y vista inicial (HIS-003)."""
import pytest

from web_helpers import READY_MS


def _abrir(browser, base_url, pagina, var):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errores = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + pagina + ".html")
    pg.wait_for_function(f"window.{var} && window.{var}.builds >= 1 && !window.{var}.busy && window.__historial.pasos >= 1",
                         timeout=READY_MS)
    return ctx, pg, errores


def _esperar(pg, var, n):
    pg.wait_for_function(f"window.{var}.builds >= {n} && !window.{var}.busy", timeout=READY_MS)
    pg.wait_for_timeout(400)


def _slider(pg, var, id_, valor):
    n = pg.evaluate(f"window.{var}.builds") + 1
    pg.evaluate(f"""() => {{ const e = document.getElementById('{id_}'); e.value = '{valor}';
        e.dispatchEvent(new Event('input', {{ bubbles: true }})); e.dispatchEvent(new Event('change', {{ bubbles: true }})); }}""")
    _esperar(pg, var, n)


def _clic(pg, var, sel):
    n = pg.evaluate(f"window.{var}.builds") + 1
    pg.click(sel)
    _esperar(pg, var, n)


def _tecla(pg, var, tecla):
    n = pg.evaluate(f"window.{var}.builds") + 1
    pg.keyboard.press(tecla)
    _esperar(pg, var, n)


@pytest.mark.spec("HIS-001", "HIS-002", "HIS-003")
def test_historial_chapita(browser, base_url):
    ctx, pg, errores = _abrir(browser, base_url, "chapita", "__chapita")
    clave = lambda: pg.evaluate("window.__historial.capturar().clave")
    activo = lambda t: pg.evaluate(f"!document.querySelector('[data-testid={t}]').disabled")
    c0 = clave()
    assert not activo("btn-deshacer") and not activo("btn-rehacer") and not activo("btn-de-cero")
    _slider(pg, "__chapita", "ancho", "60")
    c1 = clave()
    otra = pg.evaluate("[...document.querySelectorAll('#formas button[data-forma]')].map(b => b.dataset.forma)"
                       ".find(f => f !== window.__historial.capturar().x.forma)")
    _clic(pg, "__chapita", f"[data-testid=forma-{otra}]")
    c2 = clave()
    assert len({c0, c1, c2}) == 3 and pg.evaluate("window.__historial.pasos") == 3
    _clic(pg, "__chapita", "[data-testid=btn-deshacer]")
    assert clave() == c1 and activo("btn-rehacer")
    _clic(pg, "__chapita", "[data-testid=btn-deshacer]")
    assert clave() == c0 and pg.input_value("#ancho") == "45" and not activo("btn-deshacer")
    _clic(pg, "__chapita", "[data-testid=btn-rehacer]")
    assert clave() == c1
    pg.click("body", position={"x": 5, "y": 5})
    _tecla(pg, "__chapita", "Control+y")
    assert clave() == c2 and pg.evaluate("window.__historial.capturar().x.forma") == otra
    _tecla(pg, "__chapita", "Control+z")
    assert clave() == c1
    # un cambio nuevo descarta lo que se podía rehacer
    _slider(pg, "__chapita", "ancho", "50")
    assert not activo("btn-rehacer") and pg.evaluate("window.__historial.pasos") == 3
    # De cero: los datos de arranque, como un paso que se puede deshacer
    c3 = clave()
    _clic(pg, "__chapita", "[data-testid=btn-de-cero]")
    assert clave() == c0 and not activo("btn-de-cero")
    _tecla(pg, "__chapita", "Control+z")
    assert clave() == c3
    # en un campo de texto Ctrl+Z deshace lo escrito, no el modelo
    pos = pg.evaluate("window.__historial.posicion")
    nombre = pg.input_value("#nombre")
    pg.click("#nombre")
    pg.keyboard.press("End")
    pg.keyboard.type("XY")
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(300)
    assert pg.input_value("#nombre") == nombre and pg.evaluate("window.__historial.posicion") == pos
    # vista inicial: después de mover la cámara, "Inicio" vuelve al encuadre del modelo
    pg.click("[data-testid=vista-arriba]")
    pg.click("[data-testid=vista-girar]")
    pg.wait_for_timeout(1200)
    V = "window.__chapitaViewer"
    assert pg.evaluate(f"{V}.camera.position.distanceTo({V}.encuadre.pos)") > 1
    pg.click("[data-testid=vista-inicio]")
    pg.wait_for_timeout(1500)
    assert pg.evaluate(f"{V}.camera.position.distanceTo({V}.encuadre.pos) + {V}.controls.target.distanceTo({V}.encuadre.target)") < 0.5
    assert pg.evaluate(f"{V}.controls.autoRotate") is False
    assert pg.get_attribute("[data-testid=vista-girar]", "aria-pressed") == "false"
    assert not errores
    ctx.close()


@pytest.mark.spec("HIS-001")
def test_historial_mate_relieve(browser, base_url):
    ctx, pg, errores = _abrir(browser, base_url, "mate", "__mate")
    _clic(pg, "__mate", "#deco-tipo [data-t=texto]")
    assert pg.evaluate("window.__mate.viewer.relieve")
    _slider(pg, "__mate", "pared", "6")
    _clic(pg, "__mate", "[data-testid=btn-deshacer]")
    assert pg.evaluate("window.__mate.viewer.relieve") and pg.evaluate("window.__mate.deco.tipo") == "texto"
    _clic(pg, "__mate", "[data-testid=btn-deshacer]")
    assert not pg.evaluate("window.__mate.viewer.relieve") and pg.evaluate("window.__mate.deco.tipo") == ""
    assert pg.evaluate("document.getElementById('deco-ui').hidden")
    _clic(pg, "__mate", "[data-testid=btn-rehacer]")
    assert pg.evaluate("window.__mate.viewer.relieve") and not pg.evaluate("document.getElementById('deco-ui').hidden")
    assert not errores
    ctx.close()
