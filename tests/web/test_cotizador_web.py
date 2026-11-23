# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Cotizador en la página (COT-003): sin cuenta, con precio y moneda de cada uno."""
import re

import pytest

from web_helpers import READY_MS


def _num(txt):
    """'1.234,5 g' → 1234.5"""
    return float(re.sub(r"[^\d,]", "", txt).replace(",", "."))


@pytest.mark.spec("COT-003")
def test_cotizar_chapita(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="es-AR")
    pg = ctx.new_page()
    errores = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(base_url + "chapita.html")
    pg.wait_for_function("window.__chapita && window.__chapita.builds >= 1 && !window.__chapita.busy", timeout=READY_MS)
    pg.click("[data-testid=btn-cotizar]")
    pg.wait_for_selector("[data-testid=cot-gramos]", timeout=60_000)
    g_pla = _num(pg.inner_text("[data-testid=cot-gramos]"))
    assert 1 < g_pla < 20
    assert pg.input_value("[data-testid=cot-moneda]") == "ARS"          # navegador en es-AR
    assert not pg.locator("[data-testid=cot-costo]").count()             # sin precio, sin costo
    pg.fill("[data-testid=cot-precio]", "20000")
    costo = pg.inner_text("[data-testid=cot-costo]")
    assert "$" in costo and abs(_num(costo) - g_pla / 1000 * 20000) < 1.5
    # ABS es más liviano que PLA; más relleno, más gramos; 10 unidades, 10 veces más
    pg.select_option("[data-testid=cot-material]", "ABS")
    assert _num(pg.inner_text("[data-testid=cot-gramos]")) < g_pla
    pg.select_option("[data-testid=cot-material]", "PLA")
    pg.fill("[data-testid=cot-relleno]", "100")
    pg.dispatch_event("[data-testid=cot-relleno]", "input")
    assert _num(pg.inner_text("[data-testid=cot-gramos]")) >= g_pla
    pg.fill("[data-testid=cot-relleno]", "15")
    pg.dispatch_event("[data-testid=cot-relleno]", "input")
    pg.fill("[data-testid=cot-unidades]", "10")
    assert abs(_num(pg.inner_text("[data-testid=cot-gramos]")) - g_pla * 10) <= max(1, g_pla * 0.02 * 10)
    pg.select_option("[data-testid=cot-moneda]", "USD")
    assert "US$" in pg.inner_text("[data-testid=cot-costo]") or "USD" in pg.inner_text("[data-testid=cot-costo]")
    # si cambia el modelo con el panel abierto, se vuelve a medir
    antes = pg.evaluate("window.__cotizador.ultimo.total")
    pg.keyboard.press("Escape")
    pg.evaluate("""() => { const i = document.querySelector('#ancho');
      i.value = +i.max; i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); }""")
    pg.click("[data-testid=btn-generar]")
    pg.wait_for_function("window.__chapita.builds >= 2 && !window.__chapita.busy", timeout=READY_MS)
    pg.click("[data-testid=btn-cotizar]")
    pg.wait_for_function(f"window.__cotizador.ultimo && Math.abs(window.__cotizador.ultimo.total - {antes}) > 0.01", timeout=60_000)
    # la configuración queda guardada (las unidades vuelven a 1)
    pg.reload()
    pg.wait_for_function("window.__chapita && window.__chapita.builds >= 1", timeout=READY_MS)
    pg.click("[data-testid=btn-cotizar]")
    assert pg.input_value("[data-testid=cot-precio]") == "20000"
    assert pg.input_value("[data-testid=cot-moneda]") == "USD"
    assert pg.input_value("[data-testid=cot-unidades]") == "1"
    assert not errores
    ctx.close()


@pytest.mark.spec("COT-003")
def test_cotizar_banda_detalla_las_piezas(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="es-AR")
    pg = ctx.new_page()
    pg.goto(base_url + "banda.html")
    pg.wait_for_function("window.__banda && window.__banda.builds >= 1 && !window.__banda.busy", timeout=READY_MS)
    pg.click("[data-testid=btn-cotizar]")
    pg.wait_for_selector("[data-testid=cot-gramos]", timeout=60_000)
    txt = pg.inner_text("[data-testid=cot-resultado]")
    assert "Corazon" in txt and "Pelotita" in txt and "color 2" in txt
    assert "m de filamento" in txt
    ctx.close()
