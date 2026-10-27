# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""E2E de la web: arma el sitio (o usa EDEN3D_SITE), lo sirve en un puerto local
y abre Chromium con Playwright. El motor corre de verdad (Pyodide)."""
import functools
import http.server
import os
import subprocess
import sys
import tempfile
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from web_helpers import open_app  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map,
                          **{".wasm": "application/wasm", ".js": "text/javascript",
                             ".mjs": "text/javascript", ".json": "application/json"})

    def log_message(self, *a):
        pass


@pytest.fixture(scope="session")
def site_dir():
    d = os.environ.get("EDEN3D_SITE")
    if d and os.path.isfile(os.path.join(d, "index.html")):
        return d
    d = os.path.join(tempfile.mkdtemp(prefix="eden3d_site_"), "site")
    subprocess.check_call([sys.executable, os.path.join(REPO, "tools", "build_site.py"),
                           "--out", d])
    return d


@pytest.fixture(scope="session")
def base_url(site_dir):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                          functools.partial(_Handler, directory=site_dir))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield "http://127.0.0.1:%d/" % srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # WebGL por software en servidores sin GPU (CI)
    return {**browser_type_launch_args,
            "args": ["--use-gl=swiftshader", "--enable-unsafe-swiftshader",
                     "--ignore-gpu-blocklist"]}


@pytest.fixture(scope="session")
def app(browser, base_url):
    """Una sola página cargada para los tests que no cambian el estado."""
    import time
    t0 = time.time()
    page = open_app(browser, base_url)
    page.first_model_seconds = time.time() - t0
    _SESSION_CONTEXTS.add(page.context)
    yield page
    page.context.close()


_SESSION_CONTEXTS = set()


@pytest.fixture(autouse=True)
def _cerrar_paginas(request):
    """Si un test falla antes de cerrar su página, se cierra igual: una página con el
    visor andando en WebGL por software frena a todos los tests que siguen."""
    yield
    if "browser" not in request.fixturenames:
        return
    browser = request.getfixturevalue("browser")
    if "app" in request.fixturenames:
        _SESSION_CONTEXTS.add(request.getfixturevalue("app").context)
    for ctx in list(browser.contexts):
        if ctx not in _SESSION_CONTEXTS:
            ctx.close()
