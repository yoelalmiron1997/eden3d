# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Tests de punta a punta de Eden3D Studio (GitHub Pages)."""
import io
import zipfile

import pytest

from web_helpers import open_app, wait_build

T = "[data-testid=%s]"


@pytest.mark.spec("WEB-001")
def test_carga_el_catalogo(app):
    """El motor carga, el selector tiene los 17 diseños y no hay errores de consola."""
    assert "Listo" in app.locator(T % "estado").inner_text()
    assert app.locator(T % "sel-diseno" + " option").count() == 17
    assert app.locator(T % "sel-modo").input_value() == "screw_dish_sw"
    assert not app.console_errors, app.console_errors


@pytest.mark.spec("WEB-002", "PER-003")
def test_el_visor_dibuja_la_maceta(app):
    st = app.evaluate("window.__eden")
    assert st["meshes"] == ["MACETA", "PLATO", "AGUA"]
    assert st["triangles"] > 10_000
    assert app.first_model_seconds < 90, "primer modelo en %.0f s" % app.first_model_seconds
    # el canvas no está vacío: hay píxeles opacos y con variación
    stats = app.evaluate("""() => {
        const c = document.querySelector('[data-testid=visor] canvas');
        const t = document.createElement('canvas'); t.width = 120; t.height = 90;
        const g = t.getContext('2d'); g.drawImage(c, 0, 0, 120, 90);
        const d = g.getImageData(0, 0, 120, 90).data; let n = 0, s = 0, s2 = 0;
        for (let i = 0; i < d.length; i += 4) { if (d[i+3] > 0) { n++; const l = d[i] + d[i+1] + d[i+2]; s += l; s2 += l*l; } }
        return { n, var: n ? s2 / n - (s / n) ** 2 : 0 };
    }""")
    assert stats["n"] > 1000 and stats["var"] > 50, stats


@pytest.mark.spec("WEB-003")
def test_reporte_del_autorriego(app):
    assert app.locator(T % "sku").inner_text() == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS"
    assert "4 vueltas" in app.locator(T % "f-rosca").inner_text()
    assert app.locator(T % "f-luz").inner_text().endswith("mm")
    assert app.locator(T % "f-agua-min").inner_text().endswith("ml")
    assert "tierra en remojo" in app.locator(T % "f-agua-max").inner_text()


@pytest.mark.spec("WEB-007")
def test_vista_de_corte(app):
    app.locator(T % "chk-corte").check()
    assert app.evaluate("window.__eden.cut") is True
    app.locator(T % "chk-corte").uncheck()
    assert app.evaluate("window.__eden.cut") is False


@pytest.mark.spec("WEB-004", "LIC-002")
def test_descarga_3mf(app):
    with app.expect_download(timeout=180_000) as dl:
        app.locator(T % "btn-3mf").click()
    d = dl.value
    assert d.suggested_filename == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS.3mf"
    data = open(d.path(), "rb").read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8")
    assert model.count("<object ") == 2
    assert 'name="Copyright"' in model and "Eden3D" in model


@pytest.mark.spec("WEB-008")
def test_descarga_stl(app):
    app.wait_for_function("!window.__eden.busy")
    with app.expect_download(timeout=180_000) as dl:
        app.locator(T % "btn-stl").click()
    assert dl.value.suggested_filename == "Eden3D-ROMBO-S-AUTORRIEGO-HOJAS_MACETA.stl"
    head = open(dl.value.path(), "rb").read(80)
    assert b"Eden3D" in head


@pytest.mark.spec("WEB-005")
def test_slider_cambia_el_diseno(browser, base_url):
    page = open_app(browser, base_url)
    tris0 = page.evaluate("window.__eden.triangles")
    n = page.evaluate("window.__eden.builds")
    page.evaluate("""() => { const s = document.querySelector('[data-testid=sl-tex_count]');
        s.value = 36; s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); }""")
    wait_build(page, n)
    assert page.locator(T % "sku").inner_text().endswith("-N36")
    assert page.evaluate("window.__eden.triangles") != tris0
    page.context.close()


@pytest.mark.spec("WEB-006")
def test_celular(browser, base_url):
    page = open_app(browser, base_url, viewport=(390, 844))
    over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert over <= 0, "scroll horizontal de %d px" % over
    visor = page.locator(T % "visor").bounding_box()
    panel = page.locator("section.panel").bounding_box()
    assert visor["y"] < panel["y"]
    btn = page.locator(T % "btn-3mf")
    btn.scroll_into_view_if_needed()
    assert btn.is_visible()
    page.context.close()


@pytest.mark.spec("LIC-001")
def test_licencia_en_la_web(app, base_url):
    assert "Todos los derechos reservados" in app.locator(T % "licencia").inner_text()
    p = app.context.new_page()
    p.goto(base_url + "licencia.html")
    txt = p.locator(T % "licencia-texto").inner_text()
    assert "Todos los derechos reservados" in txt and "Ley 11.723" in txt
    p.close()


@pytest.mark.spec("QA-002")
def test_tablero_de_calidad(browser, base_url, site_dir):
    """Con un data.json de muestra la página muestra gate, KPIs y la matriz."""
    import json
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")
    sys.path.insert(0, tools)
    import spec_matrix
    specs = os.path.join(os.path.dirname(tools), "specs")
    data = spec_matrix.build(specs, [])
    data_path = os.path.join(site_dir, "calidad", "data.json")
    existed = os.path.isfile(data_path)
    if not existed:
        with open(data_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    try:
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        p = ctx.new_page()
        p.goto(base_url + "calidad/")
        p.wait_for_function("!!window.__calidad")
        d = p.evaluate("window.__calidad")
        assert p.locator(T % "q-gate").inner_text().strip()
        assert p.locator(T % "q-matriz" + " tr.spec").count() == len(d["specs"])
        first = d["specs"][0]["id"]
        p.locator(T % ("spec-" + first)).click()
        assert p.locator('tr.det[data-for="%s"]' % first).is_visible()
        assert "Criterio" in p.locator('tr.det[data-for="%s"]' % first).inner_text()
        ctx.close()
    finally:
        if not existed:
            os.remove(data_path)
