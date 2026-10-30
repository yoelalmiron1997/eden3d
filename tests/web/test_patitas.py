# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Patitas articuladas en macetas.html (PAT-005)."""
import pytest

from web_helpers import READY_MS, open_app, wait_build

T = "[data-testid=%s]"


@pytest.mark.spec("PAT-005")
def test_patitas_en_la_web(browser, base_url):
    pg = open_app(browser, base_url)
    modo0 = pg.locator(T % "sel-modo").input_value()
    assert modo0 != "pot"
    assert pg.locator(T % "sel-patitas" + " option").count() == 4
    assert pg.locator(T % "sel-pies" + " option").count() == 3
    assert pg.locator(T % "sel-pies").input_value() == "zapatilla"
    b = pg.evaluate("window.__eden.builds")
    pg.locator(T % "sel-patitas").select_option("patas_brazos")
    wait_build(pg, b)
    # siempre sin plato: el plato queda en "Sin plato" y bloqueado
    assert pg.locator(T % "sel-modo").input_value() == "pot"
    assert pg.locator(T % "sel-modo").is_disabled()
    assert "SOLA" in pg.evaluate("window.__eden.summary.sku")
    assert "PLATO" not in [p["name"] for p in pg.evaluate("window.__eden.parts")]
    nombres = [p["name"] for p in pg.evaluate("window.__eden.parts")]
    assert {"PATA_I_1", "PATA_I_3", "PATA_D_3", "BRAZO_I_2", "BRAZO_D_2"} <= set(nombres)
    msg = pg.locator(T % "patitas-msg").inner_text()
    assert "base de la maceta" in msg and "0,45 mm" in msg
    p = pg.evaluate("window.__eden.patitas")
    assert [c["nombre"] for c in p["cadenas"]] == ["PATA_I", "PATA_D", "BRAZO_I", "BRAZO_D"]
    assert all(a == 0 for c in p["cadenas"] for a in c["angulos"])       # como sale de la impresora
    # sentada en el borde: estante, patas colgando y brazos arriba
    pg.locator(T % "btn-sentar").click()
    pg.wait_for_function("window.__eden.patitas.k >= 1", timeout=READY_MS)
    p = pg.evaluate("window.__eden.patitas")
    assert p["estante"] and p["alto"] >= 90
    cad = {c["nombre"]: c for c in p["cadenas"]}
    for n in ("PATA_I", "PATA_D"):
        assert 1.0 < cad[n]["angulos"][0] < 1.75                         # ~80° (±12°)
    assert cad["BRAZO_I"]["angulos"][0] > 0.3
    assert "ESTANTE" in [m for m in pg.evaluate(
        "window.__edenViewer.model.children.map((o) => o.name)")]
    # más eslabones y pies de pato: recalcula y sigue sentada
    b = pg.evaluate("window.__eden.builds")
    pg.locator(T % "sel-pies").select_option("pato")
    wait_build(pg, b)
    b = pg.evaluate("window.__eden.builds")
    pg.locator(T % "sl-eslabones").fill("4")
    pg.locator(T % "sl-eslabones").dispatch_event("change")
    wait_build(pg, b)
    p = pg.evaluate("window.__eden.patitas")
    assert [c["eslabones"] for c in p["cadenas"]][:2] == [4, 4] and p["estante"]
    # bajarla del estante
    pg.locator(T % "btn-sentar").click()
    pg.wait_for_function("window.__eden.patitas.k === 0", timeout=READY_MS)
    assert not pg.evaluate("window.__eden.patitas.estante")
    # la descarga trae las patitas pegadas (antes de sacarlas)
    with pg.expect_download(timeout=READY_MS) as dl:
        pg.locator(T % "btn-stl").click()
    assert dl.value.suggested_filename.endswith("_MACETA.stl")
    # sin patitas vuelve el plato que estaba
    b = pg.evaluate("window.__eden.builds")
    pg.locator(T % "sel-patitas").select_option("")
    wait_build(pg, b)
    assert pg.locator(T % "sel-modo").input_value() == modo0
    assert not pg.locator(T % "sel-modo").is_disabled()
    assert not pg.console_errors, pg.console_errors
    pg.context.close()
