# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Los 7 generadores montan el historial y lo que guardan existe en su página (HIS-001)."""
import os
import re

import pytest

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web")
PAGINAS = {"macetas": "app", "chapita": "chapita", "banda": "banda", "mate": "mate", "sopa": "sopa",
           "topper": "topper", "trofeo": "trofeo"}
VISTA = {"color", "color-letras", "color-base", "color-detalle", "c-disco", "c-letras", "c-corazon", "c-pelotita",
         "decor", "cobertura", "torta", "torta-tipo", "cut", "slicer", "layer", "explode", "separar", "solucion"}


@pytest.mark.spec("HIS-001")
@pytest.mark.parametrize("pagina", sorted(PAGINAS))
def test_cada_generador_monta_el_historial(pagina):
    js = open(os.path.join(WEB, PAGINAS[pagina] + ".js"), encoding="utf-8").read()
    html = open(os.path.join(WEB, pagina + ".html"), encoding="utf-8").read()
    assert 'import { montarHistorial } from "./historial.js";' in js
    bloque = js[js.index("window.__historial = montarHistorial({"):]
    ids = re.findall(r'"([a-z_0-9-]+)"', bloque.split("controles:", 1)[1].split("\n  extra:")[0].split("\n  refrescar:")[0])
    ids = [i for i in ids if not i.endswith("-")]          # "s-" + k: los sliders que arma la página
    assert ids, pagina
    for i in ids:
        assert 'id="%s"' % i in html, (pagina, i)
        assert i not in VISTA, "%s: %s es de la vista, no del modelo" % (pagina, i)
    for clave in ("generar:", "version: () => state.builds", "ocupado: () => state.busy", "viewer"):
        assert clave in bloque, (pagina, clave)
