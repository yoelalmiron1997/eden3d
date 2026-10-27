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
    # el canvas no está vacío: hay píxeles opacos y con variación (se espera a que
    # el visor dibuje algunos cuadros; en equipos sin GPU va a pocos cuadros/s)
    f0 = app.evaluate("window.__eden.viewer.frames")
    app.wait_for_function("(f) => window.__eden.viewer.frames > f + 2", arg=f0, timeout=60_000)
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
    assert app.evaluate("window.__eden.viewer.cut") is True
    app.locator(T % "chk-corte").uncheck()
    assert app.evaluate("window.__eden.viewer.cut") is False


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


def _plant_click(page, pid):
    n = page.evaluate("window.__eden.plantBuilds")
    page.locator(T % ("planta-" + pid)).click(no_wait_after=True)
    page.wait_for_function("(n) => window.__eden.plantBuilds > n", arg=n, timeout=120_000)


@pytest.mark.spec("PLA-005")
def test_plantas_y_cuidados(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1", timeout=120_000)
    # por defecto: echeveria, con ficha y consejo de autorriego con los ml reales
    assert page.evaluate("window.__eden.plants") == ["echeveria"]
    assert page.evaluate("window.__eden.viewer.plantTriangles") > 1000
    assert page.locator(T % "cuidados").is_visible()
    ml = page.evaluate("Math.round(window.__eden.summary.assembly.water_min_wet_ml)")
    assert ("%d ml" % ml) in page.locator(T % "ficha-autorriego").inner_text()
    assert page.locator(T % "ficha-senales" + " tbody tr").count() >= 3
    # combinar: potus + cactus -> pestañas y avisos de compatibilidad
    _plant_click(page, "pothos")
    _plant_click(page, "cereus")
    assert page.locator("#care-tabs button").count() == 3
    compat = page.locator(T % "compatibilidad").inner_text()
    assert "Riego distinto" in compat and "Luz distinta" in compat
    page.locator(T % "tab-pothos").click()
    assert page.locator(T % "ficha-pothos").is_visible()
    # tope de 4: con 4 tipos elegidos, los de otro tipo se bloquean
    _plant_click(page, "sansevieria")
    assert page.locator(T % "planta-ceibo").is_disabled()
    assert not page.locator(T % "planta-lithops").is_disabled()      # mismo tipo: reemplaza
    page.context.close()


@pytest.mark.spec("PLA-006")
def test_una_planta_por_tipo_en_la_web(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1", timeout=120_000)
    for g in ("suculentas", "cactus", "colgantes", "follaje", "arboles_nativos", "arbustos_nativos"):
        assert page.locator(T % ("grupo-" + g)).count() == 1, g
    _plant_click(page, "haworthia")                  # reemplaza a la echeveria
    assert page.evaluate("window.__eden.plants") == ["haworthia"]
    assert page.locator(T % "planta-echeveria").get_attribute("aria-pressed") == "false"
    _plant_click(page, "ceibo")
    _plant_click(page, "jacaranda")                  # reemplaza al ceibo
    assert page.evaluate("window.__eden.plants") == ["haworthia", "jacaranda"]
    assert [g["id"] for g in page.evaluate("window.__eden.viewer.plantGroups")] == ["haworthia", "jacaranda"]
    page.context.close()


@pytest.mark.spec("PLA-008")
def test_tipo_de_tierra(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1", timeout=120_000)
    opciones = page.locator(T % "sel-tierra" + " option").count()
    assert opciones == 7                             # automática + 6 tipos
    # automática: para la echeveria (riego seco) sugiere piedra volcánica
    assert page.evaluate("window.__eden.coberturaUsada") == "volcanica"
    assert "volcánica" in page.locator(T % "tierra-desc").inner_text().lower()
    n = page.evaluate("window.__eden.plantBuilds")
    page.locator(T % "sel-tierra").select_option("corteza")
    page.wait_for_function("(n) => window.__eden.plantBuilds > n", arg=n, timeout=120_000)
    assert page.evaluate("window.__eden.coberturaUsada") == "corteza"
    names = page.evaluate("window.__edenViewer.plants.children.flatMap(g => g.children.map(m => m.name))")
    assert "corteza_pino" in names and "volcanica" not in names
    page.context.close()


@pytest.mark.spec("VIS-004")
def test_escenarios(browser, base_url):
    page = open_app(browser, base_url)
    v = page.evaluate("window.__eden.viewer")
    assert v["groundVisible"] is (not v["lowPower"])    # en bajo consumo no hay sombras
    bg0 = page.evaluate("getComputedStyle(document.querySelector('.stage')).backgroundImage")
    for k, pieza in (("oficina", "escritorio"), ("jardin", "pasto"), ("taller", "banco")):
        page.locator(T % ("escena-" + k)).click(no_wait_after=True)
        v = page.evaluate("window.__eden.viewer")
        assert v["scene"] == k and pieza in v["sceneMeshes"], (k, v["sceneMeshes"])
        assert v["groundVisible"] is False
        assert page.evaluate("getComputedStyle(document.querySelector('.stage')).backgroundImage") != bg0
        assert page.evaluate("window.__edenViewer.sceneGroup.scale.x") > 0.5
    assert "impresora_3d" in page.evaluate("window.__eden.viewer.sceneMeshes")
    page.locator(T % "escena-estudio").click(no_wait_after=True)
    v = page.evaluate("window.__eden.viewer")
    assert v["scene"] == "estudio" and v["sceneMeshes"] == []
    page.context.close()


@pytest.mark.spec("VIS-005")
def test_plantas_nacen_y_se_mueven(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1", timeout=120_000)
    page.wait_for_function("window.__eden.viewer.growing === 0 && window.__eden.viewer.plantGroups.length === 1"
                           " && window.__eden.viewer.plantGroups[0].scale === 1", timeout=60_000)
    n = page.evaluate("window.__eden.plantBuilds")
    page.locator(T % "planta-pothos").click(no_wait_after=True)
    page.wait_for_function("(n) => window.__eden.plantBuilds > n", arg=n, timeout=120_000)
    t0 = page.evaluate("window.__eden.viewer.animTime")
    assert page.evaluate("window.__eden.viewer.born") == ["pothos"], "sólo nace la nueva"
    g = {x["id"]: x for x in page.evaluate("window.__eden.viewer.plantGroups")}
    assert g["echeveria"]["scale"] == 1, "la que ya estaba no vuelve a nacer"
    page.wait_for_function("window.__eden.viewer.plantGroups.every(g => g.scale === 1)", timeout=60_000)
    assert page.evaluate("window.__eden.viewer.animTime") - t0 < 4.5
    # viento: el tiempo avanza y se puede apagar
    w0 = page.evaluate("window.__eden.viewer.wind")
    page.wait_for_timeout(1200)
    assert page.evaluate("window.__eden.viewer.wind") > w0
    page.locator(T % "chk-viento").uncheck(no_wait_after=True)
    page.wait_for_timeout(1200)
    assert page.evaluate("window.__eden.viewer.wind") == 0
    page.context.close()


@pytest.mark.spec("REN-003")
def test_foto_1080x1350(browser, base_url):
    page = open_app(browser, base_url)
    page.locator(T % "escena-jardin").click(no_wait_after=True)
    with page.expect_download() as dl:
        page.locator(T % "btn-foto").click()
    d = dl.value
    assert d.suggested_filename.endswith("_jardin.png")
    data = open(d.path(), "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    assert (w, h) == (1080, 1350)
    assert len(data) > 50_000                        # no es una imagen vacía
    page.context.close()


@pytest.mark.spec("VIS-001")
def test_iluminacion(browser, base_url):
    page = open_app(browser, base_url)
    bg0 = page.evaluate("getComputedStyle(document.querySelector('.stage')).backgroundImage")
    page.locator(T % "luz-noche").click(no_wait_after=True)
    v = page.evaluate("window.__eden.viewer")
    assert v["light"] == "noche" and v["lamp"] > 0
    assert page.evaluate("getComputedStyle(document.querySelector('.stage')).backgroundImage") != bg0
    page.locator(T % "luz-atardecer").click(no_wait_after=True)
    assert page.evaluate("window.__eden.viewer.sunIntensity") > 3
    page.evaluate("""() => { const s = document.querySelector('[data-testid=sl-sol]');
        s.value = 200; s.dispatchEvent(new Event('input')); }""")
    assert page.evaluate("window.__eden.viewer.sunAz") == 200
    page.context.close()


@pytest.mark.spec("VIS-002", "VIS-003")
def test_agua_animada(browser, base_url):
    page = open_app(browser, base_url)
    page.evaluate("window.__edenViewer.setLowPower()")          # VIS-003: modo bajo consumo
    assert page.evaluate("window.__edenViewer.renderer.shadowMap.enabled") is False
    def sample():
        return page.evaluate("""() => { const W = window.__edenViewer.water;
            const a = W.geoms[0].attributes.position.array; return [W.t, a[3*40+2], a[3*700+2], W.level]; }""")
    t0, a0, b0, _ = sample()
    d0 = page.evaluate("window.__edenViewer.stats.drops")
    page.wait_for_timeout(4000)
    t1, a1, b1, _ = sample()
    assert t1 > t0, "el tiempo del agua no avanza"
    assert (a1, b1) != (a0, b0), "la superficie no se mueve"
    relieve = page.evaluate("""() => { const a = window.__edenViewer.water.geoms[0].attributes.position.array;
        let lo = 1e9, hi = -1e9; for (let i = 2; i < a.length; i += 3) { lo = Math.min(lo, a[i]); hi = Math.max(hi, a[i]); }
        return hi - lo; }""")
    assert relieve >= 0.5, "ondas poco visibles: %.2f mm" % relieve
    assert page.evaluate("window.__edenViewer.stats.drops") > d0, "no caen gotas"
    A = page.evaluate("window.__eden.summary.assembly")
    page.locator(T % "agua-min").click(no_wait_after=True)
    page.wait_for_function("(z) => Math.abs(window.__edenViewer.water.level - z) < 0.6",
                           arg=A["water_min_wet_level_mm"], timeout=60_000)
    page.locator(T % "agua-max").click(no_wait_after=True)
    page.wait_for_function("(z) => Math.abs(window.__edenViewer.water.level - z) < 0.6",
                           arg=A["water_level_max_mm"], timeout=60_000)
    page.context.close()
