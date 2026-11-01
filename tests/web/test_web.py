# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Tests de punta a punta de Eden3D Studio (GitHub Pages)."""
import io
import math
import zipfile

import pytest

from web_helpers import READY_MS, open_app, wait_build

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
        ctx.add_init_script('window.__EDEN_AUTH_MOCK = {"role": "admin", "email": "admin@eden3d.test"};')
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
    for k, pieza in (("oficina", "escritorio"), ("taller", "banco")):
        page.locator(T % ("escena-" + k)).click(no_wait_after=True)
        v = page.evaluate("window.__eden.viewer")
        assert v["scene"] == k and pieza in v["sceneMeshes"], (k, v["sceneMeshes"])
        assert v["groundVisible"] is False
        assert page.evaluate("getComputedStyle(document.querySelector('.stage')).backgroundImage") != bg0
        assert page.evaluate("window.__edenViewer.sceneGroup.scale.x") > 0.5
    assert "impresora_3d" in page.evaluate("window.__eden.viewer.sceneMeshes")
    # jardín: mesa de madera con texturas y foto real desenfocada atrás, cámara baja
    y0 = page.evaluate("window.__edenViewer.camera.position.y - window.__edenViewer.controls.target.y")
    page.locator(T % "escena-jardin").click(no_wait_after=True)
    page.wait_for_function("window.__eden.viewer.panoLoaded", timeout=60_000)
    assert "mesa_jardin" in page.evaluate("window.__eden.viewer.sceneMeshes")
    assert page.evaluate("""() => { const m = window.__edenViewer.sceneGroup.getObjectByName('mesa_jardin').material;
        return !!(m.map && m.normalMap && m.roughnessMap); }""")
    bg = page.evaluate("""() => { const s = window.__edenViewer.scene;
        return [s.background && s.background.image ? s.background.image.width : 0, s.backgroundBlurriness]; }""")
    assert bg[0] >= 2048 and bg[1] > 0.05
    y1 = page.evaluate("window.__edenViewer.camera.position.y - window.__edenViewer.controls.target.y")
    assert y1 < y0 * 0.75, "en el jardín la cámara baja"
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
    # interactiva: con la maceta separada, tocar el agua hace caer una gota que salpica
    page.evaluate("""() => { const s = document.querySelector('[data-testid=sl-separar]');
        s.value = 100; s.dispatchEvent(new Event('input')); }""")
    page.wait_for_timeout(600)
    xy = page.evaluate("""() => { const v = window.__edenViewer, W = v.water;
        const r = W.radiusAt(W.level) * 0.55;
        // punto del agua del lado de la cámara
        const cam = W.top.worldToLocal(v.camera.position.clone());
        const a = Math.atan2(cam.y, cam.x);
        const p = W.top.localToWorld(new v.camera.position.constructor(r * Math.cos(a), r * Math.sin(a), W.level));
        p.project(v.camera);
        const b = v.renderer.domElement.getBoundingClientRect();
        return [b.left + (p.x + 1) / 2 * b.width, b.top + (1 - p.y) / 2 * b.height]; }""")
    i0 = page.evaluate("window.__edenViewer.water.stats.impacts")
    page.mouse.click(xy[0], xy[1])
    assert page.evaluate("window.__eden.viewer.taps") == 1, "tocar el agua no tiró una gota"
    page.wait_for_function("(n) => window.__edenViewer.water.stats.impacts > n", arg=i0, timeout=20_000)
    assert page.evaluate("window.__edenViewer.water.stats.energy") > 0
    # lluvia y olas
    d1 = page.evaluate("window.__edenViewer.water.stats.drops")
    page.locator(T % "chk-lluvia").check(no_wait_after=True)
    page.wait_for_function("(n) => window.__edenViewer.water.stats.drops > n + 5", arg=d1, timeout=20_000)
    page.locator(T % "chk-lluvia").uncheck(no_wait_after=True)
    page.locator(T % "btn-olas").click(no_wait_after=True)
    assert page.evaluate("window.__edenViewer.water.slosh") > 1.5
    A = page.evaluate("window.__eden.summary.assembly")
    page.locator(T % "agua-min").click(no_wait_after=True)
    page.wait_for_function("(z) => Math.abs(window.__edenViewer.water.level - z) < 0.6",
                           arg=A["water_min_wet_level_mm"], timeout=60_000)
    page.locator(T % "agua-max").click(no_wait_after=True)
    page.wait_for_function("(z) => Math.abs(window.__edenViewer.water.level - z) < 0.6",
                           arg=A["water_level_max_mm"], timeout=60_000)
    page.context.close()


@pytest.mark.spec("VIS-006")
def test_separar_piezas(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1", timeout=120_000)
    def mover(v):
        page.evaluate("""(v) => { const s = document.querySelector('[data-testid=sl-separar]');
            s.value = v; s.dispatchEvent(new Event('input')); }""", v)
    H = page.evaluate("""() => { const g = window.__edenViewer.model.getObjectByName('MACETA').geometry;
        g.computeBoundingBox(); return g.boundingBox.max.z - g.boundingBox.min.z; }""")
    mover(100)
    v = page.evaluate("window.__eden.viewer")
    assert v["explodeOffset"] > 0.8 * H
    assert page.evaluate("window.__edenViewer.model.getObjectByName('MACETA').position.z") == v["explodeOffset"]
    assert page.evaluate("window.__edenViewer.model.getObjectByName('PLATO').position.z") == 0
    assert page.evaluate("window.__edenViewer.plants.position.y") == v["explodeOffset"]
    # escalonado: tierra por encima de la maceta y plantas por encima de la tierra
    zs = page.evaluate("""() => window.__edenViewer.plants.children.map(g => [g.userData.k, g.position.z - g.userData.base[2]])""")
    soil = [z for k, z in zs if k < 0][0]
    plant = [z for k, z in zs if k >= 0][0]
    assert 0 < soil < plant
    page.wait_for_timeout(300)
    labels = page.evaluate("window.__eden.viewer.labels")
    for t in ("Maceta", "Plato con rosca", "Agua de reserva", "Echeveria"):
        assert t in labels, (t, labels)
    mover(0)
    assert page.evaluate("window.__eden.viewer.explodeOffset") == 0
    # loop: se separa y se vuelve a armar sola
    page.locator(T % "btn-despiece").click(no_wait_after=True)
    page.wait_for_function("window.__eden.viewer.explode > 0.95", timeout=30_000)
    page.wait_for_function("window.__eden.viewer.explode < 0.05", timeout=30_000)
    assert page.evaluate("window.__edenViewer.controls.autoRotate") is True
    page.locator(T % "btn-despiece").click(no_wait_after=True)
    assert page.evaluate("window.__eden.viewer.loop") is False
    page.context.close()


@pytest.mark.spec("VIS-007")
def test_modo_slicer(browser, base_url):
    page = open_app(browser, base_url)
    page.locator(T % "chk-slicer").check(no_wait_after=True)
    s = page.evaluate("window.__eden.viewer.slicer")
    assert s["on"] and s["part"] == "MACETA"
    assert s["layers"] == math.ceil(s["height"] / 0.2 - 1e-6)
    assert s["layer"] == s["layers"] and s["segments"] > 50
    assert page.evaluate("window.__edenViewer.model.visible") is False
    page.evaluate("""() => { const s = document.querySelector('[data-testid=sl-capa]');
        s.value = 10; s.dispatchEvent(new Event('input')); }""")
    s = page.evaluate("window.__eden.viewer.slicer")
    assert s["layer"] == 10 and abs(s["z"] - 2.0) < 1e-6 and abs(s["clip"] - 2.0) < 0.01
    assert s["segments"] > 50, "la capa 10 tiene contorno"
    assert "10 / " in page.locator("#o-layer").inner_text()
    page.locator(T % "slicer-plato").click(no_wait_after=True)
    assert page.evaluate("window.__eden.viewer.slicer.part") == "PLATO"
    page.evaluate("""() => { const s = document.querySelector('[data-testid=sl-capa]');
        s.value = 1; s.dispatchEvent(new Event('input')); }""")
    page.locator(T % "btn-capas").click(no_wait_after=True)
    h0 = page.evaluate("window.__eden.viewer.slicer.head")
    page.wait_for_function("window.__eden.viewer.slicer.layer > 5", timeout=30_000)
    s = page.evaluate("window.__eden.viewer.slicer")
    assert s["playing"] and s["head"] != h0, "el cabezal se mueve"
    assert abs(s["head"][2] - s["z"]) < 0.5, "la boquilla está en la capa que imprime"
    assert page.evaluate("!!window.__edenViewer.scene.getObjectByName('CABEZAL')")
    page.locator(T % "chk-slicer").uncheck(no_wait_after=True)
    assert page.evaluate("window.__edenViewer.model.visible") is True
    assert page.evaluate("window.__eden.viewer.slicer.on") is False
    page.context.close()


@pytest.mark.spec("WEB-009")
def test_guia_pdf(app):
    page = app
    page.wait_for_function("window.__eden.plantBuilds >= 1 && !window.__eden.busy", timeout=120_000)
    with page.expect_download() as dl:
        page.locator(T % "btn-pdf").click()
    d = dl.value
    assert d.suggested_filename == page.evaluate("window.__eden.summary.sku") + "_guia.pdf"
    data = open(d.path(), "rb").read()
    assert data[:5] == b"%PDF-"
    assert page.evaluate("window.__eden.lastPdf.pages") >= 2
    A = page.evaluate("window.__eden.summary.assembly")
    for txt in ("usar el autorriego", "Echeveria", "Cuidado de la maceta",
                "%d ml" % round(A["water_min_wet_ml"]), "%d ml" % round(A["water_reservoir_ml"])):
        assert txt.encode("cp1252") in data, txt
    assert b"/Subtype /Image" in data, "lleva la foto"


@pytest.mark.spec("WEB-010")
def test_celular_simple(browser, base_url):
    page = open_app(browser, base_url, viewport=(390, 844))
    y = {k: page.locator(sel).bounding_box()["y"] for k, sel in
         (("visor", T % "visor"), ("panel", "section.panel"), ("cuidados", T % "cuidados"))}
    assert y["visor"] < y["panel"] < y["cuidados"]
    for sec in ("ambiente", "vista", "impresion"):
        lg = page.locator(T % ("sec-" + sec))
        assert lg.get_attribute("aria-expanded") == "false", sec
    assert page.locator(T % "sl-separar").is_hidden()
    page.locator(T % "sec-vista").click()
    assert page.locator(T % "sec-vista").get_attribute("aria-expanded") == "true"
    assert page.locator(T % "sl-separar").is_visible()
    largos = page.evaluate("""() => [...document.querySelectorAll('section.panel button:not(.chip)')]
        .map(b => b.textContent.trim()).filter(t => t.length > 14)""")
    assert not largos, largos
    # ficha: lo esencial visible y el resto plegado
    assert page.locator(T % "ficha-autorriego").is_visible()
    assert page.locator(T % "ficha-senales").is_hidden()
    page.locator(T % "ficha-mas" + " summary").click()
    assert page.locator(T % "ficha-senales").is_visible()
    page.context.close()


# ---------------------------------------------------------------- regresión y cuentas
@pytest.mark.spec("WEB-011")
def test_cambio_de_modelo_mientras_calcula(browser, base_url):
    page = open_app(browser, base_url)
    page.wait_for_function("window.__eden.plantBuilds >= 1 && !window.__eden.busy", timeout=120_000)
    n = page.evaluate("window.__eden.builds")
    page.locator(T % "sel-tamano").select_option("M")           # empieza a calcular
    page.wait_for_function("window.__eden.busy", timeout=10_000)
    page.locator(T % "sel-diseno").select_option("TORSION")     # cambio en medio del cálculo
    page.wait_for_function("(n) => window.__eden.builds >= n + 2 && !window.__eden.busy", arg=n, timeout=240_000)
    assert page.evaluate("window.__eden.summary.sku").startswith("Eden3D-TORSION-M-")
    assert page.locator(T % "sku").inner_text().startswith("Eden3D-TORSION-M-")
    p0 = page.evaluate("window.__eden.plantBuilds")
    page.wait_for_function("(p) => window.__eden.plantBuilds > p - 1 && !window.__eden.busy", arg=p0, timeout=120_000)
    page.wait_for_timeout(500)
    zs = page.evaluate("window.__eden.summary.abertura.z_s")
    tierra = page.evaluate("window.__edenViewer.plants.children.find(g => g.userData.k < 0).userData.base[2]")
    assert abs(tierra - zs) < 0.05, "la tierra es de otra maceta"


@pytest.mark.spec("WEB-012")
def test_home_tecnobear(browser, base_url):
    page = open_app(browser, base_url, path="")
    assert " ".join(page.locator(T % "home-titulo").inner_text().lower().split()) == "herramientas para crear en 3d"
    page.wait_for_function("(() => { const e = document.querySelector('[data-testid=tool-imagen]');"
                           " return e.complete && e.naturalWidth > 0 && e.currentSrc.includes('macetas_v'); })()", timeout=15_000)
    pop = page.locator(T % "popup-macetas")
    pop.wait_for(state="visible", timeout=10_000)              # primera visita: se abre solo
    assert "generador de macetas" in pop.inner_text().lower()
    pop.locator("[data-close]").last.click()
    assert not pop.is_visible()
    page.reload()
    page.wait_for_timeout(1200)
    assert not pop.is_visible(), "en la segunda visita no se abre solo"
    page.locator(T % "tool-macetas").click()
    assert pop.is_visible()
    page.locator(T % "abrir-macetas").click()
    page.wait_for_url("**/macetas.html")
    page.context.close()


@pytest.mark.spec("CUE-001")
def test_ingresar_y_salir(browser, base_url):
    page = open_app(browser, base_url, role="visitante")
    page.evaluate("window.__EDEN_AUTH_MOCK.loginRole = 'pro'")
    page.locator(T % "btn-ingresar").click()
    dlg = page.locator(T % "login")
    assert dlg.is_visible()
    page.locator(T % "login-email").fill("ana@eden3d.test")
    page.locator(T % "login-pass").fill("secreto123")
    page.locator(T % "login-ok").click()
    page.wait_for_function("window.__eden.auth.role === 'pro'", timeout=10_000)
    assert not dlg.is_visible()
    page.locator(T % "btn-cuenta").click()                        # el menú de la cuenta
    assert page.locator(T % "rol").inner_text() == "Pro"
    page.locator(T % "btn-salir").click()
    page.wait_for_function("window.__eden.auth.role === 'visitante'", timeout=10_000)
    assert page.locator(T % "btn-ingresar").is_visible()
    page.context.close()


@pytest.mark.spec("CUE-001")
def test_sin_cuentas_configuradas_descarga_libre(app):
    a = app.evaluate("window.__eden.auth")
    assert a["configured"] is False and a["perms"]["download"] is True
    assert app.locator("#account").inner_text().strip() == ""


@pytest.mark.spec("CUE-002")
def test_visitante_tiene_que_ingresar_para_descargar(browser, base_url):
    page = open_app(browser, base_url, role="visitante")
    downloads = []
    page.on("download", lambda d: downloads.append(d))
    page.locator(T % "btn-stl").click()
    assert page.locator(T % "login").is_visible()
    assert "descargar" in page.locator("#login-why").inner_text()
    page.wait_for_timeout(800)
    assert not downloads
    page.context.close()
    page = open_app(browser, base_url, role="usuario")
    with page.expect_download(timeout=180_000) as dl:
        page.locator(T % "btn-stl").click()
    assert dl.value.suggested_filename.endswith("_MACETA.stl")
    page.context.close()


@pytest.mark.spec("MAR-003")
def test_marca_solo_para_pro(browser, base_url):
    page = open_app(browser, base_url, role="usuario")
    assert page.locator(T % "marca-texto").is_disabled()
    assert page.locator(T % "marca-candado").is_visible()
    page.context.close()

    page = open_app(browser, base_url, role="pro")
    assert not page.locator(T % "marca-texto").is_disabled()
    assert not page.locator(T % "marca-candado").is_visible()
    n = page.evaluate("window.__eden.builds")
    page.locator(T % "marca-texto").fill("Hola €")
    page.locator(T % "marca-aplicar").click()
    page.wait_for_function("document.querySelector('[data-testid=marca-msg]').textContent.includes('€')", timeout=10_000)
    assert page.evaluate("window.__eden.builds") == n, "un texto inválido no recalcula"
    page.locator(T % "marca-texto").fill("TecnoBear")
    page.locator(T % "marca-aplicar").click()
    page.wait_for_function("(n) => window.__eden.builds > n && !window.__eden.busy", arg=n, timeout=180_000)
    b = page.evaluate("window.__eden.summary.brand")
    assert b["text"] == "TecnoBear" and any(b["pieces"].values())
    assert "TecnoBear" in page.locator(T % "marca-msg").inner_text()
    page.locator(T % "btn-cuenta").click()
    page.locator(T % "btn-salir").click()                       # sin cuenta vuelve a Eden3D
    page.wait_for_function("window.__eden.summary.brand.text === 'Eden3D' && !window.__eden.busy", timeout=180_000)
    assert page.locator(T % "marca-texto").input_value() == "Eden3D"
    page.context.close()


@pytest.mark.spec("CUE-004")
def test_panel_admin(browser, base_url):
    page = open_app(browser, base_url, role="usuario", path="admin.html")
    page.locator(T % "admin-denegado").wait_for(state="visible", timeout=10_000)
    page.context.close()

    users = [{"id": "mock", "email": "admin@eden3d.test", "rol": "admin", "creado": "2026-10-01T10:00:00Z"},
             {"id": "u2", "email": "ana@eden3d.test", "rol": "usuario", "creado": "2026-10-20T10:00:00Z"}]
    page = open_app(browser, base_url, role="admin", path="admin.html", users=users)
    page.locator(T % "admin-usuarios").wait_for(state="visible", timeout=10_000)
    assert page.locator('[data-testid="rol-admin@eden3d.test"]').is_disabled(), "no se cambia el propio rol"
    page.locator('[data-testid="rol-ana@eden3d.test"]').select_option("pro")
    page.wait_for_function("document.getElementById('users-msg').textContent.includes('ahora es Pro')")
    # cobertura de la marca: un diseño, tamaño S
    page.locator(T % "tab-cobertura").click()
    page.wait_for_function("window.__edenAdmin.engineReady", timeout=180_000)
    page.locator(T % "cov-texto").fill("Ñandú 2026")
    page.locator(T % "cov-disenos").select_option("ROMBO")
    page.locator(T % "cov-correr").click()
    page.wait_for_function("document.querySelector('[data-testid=cov-estado]').textContent.includes('macetas OK')",
                           timeout=240_000)
    rows = page.evaluate("window.__edenAdmin.cov.rows")
    assert len(rows) == 1 and rows[0]["ok"] and rows[0]["closed"], rows
    assert rows[0]["plato"] >= 3.5
    with page.expect_download() as dl:
        page.locator(T % "cov-csv").click()
    assert dl.value.suggested_filename == "cobertura_marca_Ñandú_2026.csv"
    page.context.close()



@pytest.mark.spec("WEB-013")
def test_modo_claro_y_oscuro(browser, base_url):
    page = open_app(browser, base_url, path="")
    page.locator(T % "popup-macetas").wait_for(state="visible", timeout=10_000)
    page.keyboard.press("Escape")
    btn = page.locator(T % "btn-tema")
    assert btn.is_visible() and btn.get_attribute("data-tema") == "dark"          # oscuro por defecto
    fondo = lambda: page.evaluate("getComputedStyle(document.body).backgroundColor")
    oscuro = fondo()
    btn.click()                                                                   # un solo botón: alterna
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    assert btn.get_attribute("data-tema") == "light" and fondo() != oscuro
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "light", "se recuerda"
    page.locator(T % "btn-tema").click()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark" and fondo() == oscuro
    # en una herramienta, el mismo botón y los mismos colores
    page.goto(base_url + "sopa.html")
    assert page.locator(T % "btn-tema").get_attribute("data-tema") == "dark"
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(9, 14, 15)"
    page.locator(T % "btn-tema").click()
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") != "rgb(9, 14, 15)"
    page.context.close()


@pytest.mark.spec("CUE-005")
def test_calidad_solo_admin(browser, base_url):
    for role, ve in (("visitante", False), ("usuario", False), ("admin", True)):
        page = open_app(browser, base_url, role=role, path="")
        page.wait_for_function("document.querySelector('[data-testid=btn-tema]')")
        assert page.locator(T % "link-calidad").is_visible() is ve, role
        page.goto(base_url + "calidad/")
        page.wait_for_function("!document.getElementById('q-main').hidden || !document.getElementById('q-denegado').hidden")
        assert page.locator(T % "q-denegado").is_visible() is (not ve), role
        assert page.locator("#q-main").is_visible() is ve, role
        page.context.close()
    page = open_app(browser, base_url, path="")                 # sin cuentas configuradas
    assert not page.locator(T % "link-calidad").is_visible()
    page.context.close()


def open_css():
    import os
    return open(os.path.join(os.path.dirname(__file__), "..", "..", "web", "home.css"), encoding="utf-8").read()


@pytest.mark.spec("WEB-014")
def test_inicio_catalogo_buscador_y_filtros(browser, base_url):
    page = open_app(browser, base_url, path="", role="visitante")
    page.evaluate("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    page.reload()
    rutas = {h: page.locator(T % ("ir-" + h)).get_attribute("href") for h in ("macetas", "mate", "sopa", "topper")}
    assert rutas == {"macetas": "macetas.html", "mate": "mate.html", "sopa": "sopa.html", "topper": "topper.html"}
    assert page.locator(T % "indice" + " a").count() == 4
    visibles = lambda: page.locator(".tb-card:not([hidden])").count()
    assert visibles() == 4 and page.locator(T % "contador").inner_text() == "4"
    page.locator(T % "filtro-impresion").click()
    assert visibles() == 2 and page.locator(T % "filtro-impresion").get_attribute("aria-pressed") == "true"
    page.locator(T % "buscar").fill("polimero")                  # sin tilde, con filtro: sólo el mate
    assert visibles() == 1 and page.locator(T % "contador").inner_text() == "1"
    page.locator(T % "filtro-entretenimiento").click()
    assert visibles() == 0 and page.locator(T % "sin-resultados").is_visible()
    page.locator("#tb-limpiar").click()
    assert visibles() == 4 and not page.locator(T % "sin-resultados").is_visible()
    # logo original: no gira; el del navbar quieto y el del hero flota
    anim = lambda t: page.evaluate("(e) => getComputedStyle(e).animationName", page.locator(T % t).element_handle())
    for t in ("logo-nav", "logo-hero"):
        assert page.locator(T % t).get_attribute("src") == "assets/marca/logo-tecnobear.svg"
    assert anim("logo-nav") == "none" and anim("logo-hero") == "tb-flota"
    assert "rotate(360" not in open_css()
    # planes: Premium por Instagram, "Crear cuenta gratis" abre el registro
    assert page.locator(T % "plan-premium").is_visible()
    premium = page.locator(T % "plan-premium").inner_text().lower()
    assert "actualizaciones más directas" in premium and "sin marca de agua" in premium
    assert "render y pdf con consideraciones" in premium and "colecciones preseteadas" in premium
    assert "sin render ni pdf" in page.locator(T % "plan-gratis").inner_text().lower()
    assert page.locator(T % "plan-premium-cta").get_attribute("href") == "https://www.instagram.com/tecnobearr/"
    cta = page.locator(T % "plan-gratis-cta")
    assert "crear cuenta gratis" in cta.inner_text().lower()
    cta.click()
    assert page.locator(T % "login").is_visible()
    assert page.locator("#login-title").inner_text().lower() == "crear cuenta"
    page.keyboard.press("Escape")
    # redes reales
    assert page.locator(T % "red-youtube").get_attribute("href") == "https://www.youtube.com/@TecnoBearARG"
    assert page.locator(T % "red-instagram").get_attribute("href") == "https://www.instagram.com/tecnobearr/"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator(T % "ir-topper").click()
    page.wait_for_url("**/topper.html")
    assert not page.console_errors, page.console_errors
    page.context.close()


@pytest.mark.spec("WEB-014")
def test_inicio_celular_y_tablet(browser, base_url):
    for w, h in ((390, 844), (768, 1024)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        ctx.add_init_script("window.__EDEN_AUTH_MOCK = {role: 'visitante'};"
                            "try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
        page = ctx.new_page()
        page.goto(base_url)
        page.wait_for_function("document.querySelectorAll('.tb-card').length === 4")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), w
        assert page.evaluate("getComputedStyle(document.querySelector('.tb-iso-hero')).animationName") == "none"
        menu = page.locator("#tb-menu")
        assert not menu.is_visible()
        page.locator(T % "btn-menu").click()
        assert menu.is_visible() and page.locator(T % "btn-menu").get_attribute("aria-expanded") == "true"
        page.keyboard.press("Escape")
        assert not menu.is_visible()
        assert page.locator(T % "btn-ingresar").is_visible() and page.locator(T % "btn-tema").is_visible()
        ctx.close()


@pytest.mark.spec("WEB-014")
def test_herramientas_con_el_encabezado_nuevo(browser, base_url):
    for path in ("macetas.html", "mate.html", "sopa.html", "topper.html"):
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script("window.__EDEN_AUTH_MOCK = {role: 'visitante'};")
        page = ctx.new_page()
        page.goto(base_url + path)
        logo = page.locator(T % "link-home" + " img")
        assert logo.get_attribute("src") == "assets/marca/logo-tecnobear.svg", path
        assert page.locator(T % "btn-tema").is_visible() and page.locator(T % "btn-ingresar").is_visible()
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), path
        ctx.close()


@pytest.mark.spec("WEB-015")
def test_pantalla_de_carga_de_cada_motor(browser, base_url):
    # la pantalla puede durar muy poco: se anota cómo era en el momento en que aparece
    espia = """
      window.__carga = null;
      new MutationObserver((ms, obs) => {
        const el = document.querySelector('[data-testid=carga]');
        if (!el || window.__carga) return;
        const t = el.querySelector('.carga-titulo');
        window.__carga = { pieza: el.querySelectorAll('svg .carga-pieza').length,
          cabezal: el.querySelectorAll('.carga-cabezal').length, barra: el.querySelectorAll('.carga-barra').length,
          punteros: getComputedStyle(el).pointerEvents, titulo: t ? t.getBoundingClientRect().width : -1 };
        obs.disconnect();
      }).observe(document, { childList: true, subtree: true });
    """
    estados = {"macetas.html": "__eden", "mate.html": "__mate", "sopa.html": "__sopa", "topper.html": "__topper"}
    for path, st in estados.items():
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        ctx.add_init_script(espia)
        page = ctx.new_page()
        errores = []
        page.on("pageerror", lambda e: errores.append(str(e)))
        page.goto(base_url + path)
        page.wait_for_function("window.__carga", timeout=10_000)
        c = page.evaluate("window.__carga")
        assert c["pieza"] == 1 and c["cabezal"] == 1 and c["barra"] == 1, (path, c)
        assert c["punteros"] == "none", (path, c)          # no bloquea clics
        assert c["titulo"] <= 1, (path, c)                 # sólo la impresora y la barra (texto para lectores)
        page.wait_for_function("window.%s && window.%s.builds >= 1" % (st, st), timeout=READY_MS)
        # se va sola: se desvanece (carga-lista) y se saca del visor
        page.wait_for_function("!document.querySelector('[data-testid=carga]:not(.carga-lista)')", timeout=10_000)
        assert not errores, (path, errores)
        ctx.close()


@pytest.mark.spec("WEB-016")
def test_render_y_pdf_solo_premium(browser, base_url):
    estados = {"macetas.html": "__eden", "mate.html": "__mate", "sopa.html": "__sopa", "topper.html": "__topper"}
    for path, st in estados.items():
        # cuenta gratis: candado "Pro" y aviso, sin descargas
        page = open_app(browser, base_url, role="usuario", path=path)
        page.wait_for_function("window.%s && window.%s.builds >= 1 && !window.%s.busy" % (st, st, st), timeout=READY_MS)
        bajadas = []
        page.on("download", lambda d: bajadas.append(d))
        for btn in ("btn-foto", "btn-pdf"):
            b = page.locator(T % btn)
            assert b.locator(".badge-pro").is_visible(), (path, btn)
            b.click()
            dlg = page.locator(T % "premium")
            assert dlg.is_visible(), (path, btn)
            assert page.locator(T % "premium-quiero").get_attribute("href") == "https://www.instagram.com/tecnobearr/"
            dlg.locator("[data-close]").click()
        page.wait_for_timeout(500)
        assert not bajadas, path
        page.context.close()
        # cuenta Pro: foto y PDF
        page = open_app(browser, base_url, role="pro", path=path)
        page.wait_for_function("window.%s && window.%s.builds >= 1 && !window.%s.busy" % (st, st, st), timeout=READY_MS)
        assert not page.locator(T % "btn-foto" + " .badge-pro").is_visible()
        with page.expect_download(timeout=READY_MS) as dl:
            page.locator(T % "btn-foto").click()
        assert dl.value.suggested_filename.endswith(".png")
        if path != "macetas.html":                     # la guía de las macetas tiene su test (WEB-009)
            with page.expect_download(timeout=READY_MS) as dl:
                page.locator(T % "btn-pdf").click()
            sku = page.evaluate("window.%s.summary.sku" % st)
            assert dl.value.suggested_filename == sku + "_consideraciones.pdf"
            data = open(dl.value.path(), "rb").read()
            assert data[:5] == b"%PDF-" and b"/Subtype /Image" in data
        assert not page.console_errors, (path, page.console_errors)
        page.context.close()


@pytest.mark.spec("CUE-006")
def test_perfil_con_foto(browser, base_url, tmp_path):
    from PIL import Image
    foto = tmp_path / "yo.png"
    Image.new("RGB", (300, 200), (200, 40, 40)).save(foto)
    page = open_app(browser, base_url, role="usuario", path="")
    page.evaluate("try { localStorage.setItem('tb-popup-macetas', '1') } catch (e) {}")
    page.reload()
    cuenta = page.locator(T % "btn-cuenta")
    assert cuenta.inner_text().strip() == "U"                         # sin nombre: la inicial del email
    cuenta.click()
    assert page.locator(T % "menu-cuenta").is_visible()
    page.locator(T % "btn-perfil").click()
    dlg = page.locator(T % "perfil")
    assert dlg.is_visible()
    page.locator(T % "perfil-nombre").fill("Yoel")
    page.locator(T % "perfil-apellido").fill("Almirón")
    page.locator(T % "perfil-nacimiento").fill("1997-05-20")
    page.locator(T % "perfil-foto").set_input_files(str(foto))
    page.wait_for_function("document.querySelector('#perfil-cara img')")
    page.locator(T % "perfil-guardar").click()
    assert not dlg.is_visible()
    # el botón de la cuenta muestra la foto (96 × 96) y el menú el nombre
    page.wait_for_function("document.querySelector('[data-testid=btn-cuenta] img')")
    size = page.evaluate("(() => { const i = document.querySelector('[data-testid=btn-cuenta] img'); return [i.naturalWidth, i.naturalHeight]; })()")
    assert size == [96, 96]
    cuenta.click()
    assert "Yoel Almirón" in page.locator(T % "menu-cuenta").inner_text()
    page.locator(T % "btn-perfil").click()
    assert page.locator(T % "perfil-nacimiento").input_value() == "1997-05-20"
    assert not page.console_errors, page.console_errors
    page.context.close()
