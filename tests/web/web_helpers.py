# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Ayudas de los tests e2e."""
import json
READY_MS = 180_000


def open_app(browser, base_url, viewport=(1360, 900), role=None, path="macetas.html", users=None):
    """Abre el generador. role = None (simula la web sin cuentas configuradas, descarga
    libre) o "visitante" / "usuario" / "pro" / "admin" con un login simulado (sólo localhost)."""
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              accept_downloads=True)
    if True:
        mock = {"role": role or "sin-cuentas", "email": "%s@eden3d.test" % role}
        if users:
            mock["users"] = users
        ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps(mock))
    page = ctx.new_page()
    page.console_errors = []
    page.on("console", lambda m: page.console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.console_errors.append(str(e)))
    page.goto(base_url + path)
    if path == "macetas.html":
        page.wait_for_function("window.__eden && window.__eden.builds >= 1 && !window.__eden.busy",
                               timeout=READY_MS)
    return page


def wait_build(page, before):
    page.wait_for_function("(n) => window.__eden.builds > n && !window.__eden.busy", arg=before,
                           timeout=READY_MS)


def open_mate(browser, base_url, viewport=(1360, 900)):
    """Abre mate.html (Mate con hueco) y espera el primer mate."""
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps({"role": "sin-cuentas"}))
    page = ctx.new_page()
    page.console_errors = []
    page.on("console", lambda m: page.console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.console_errors.append(str(e)))
    page.goto(base_url + "mate.html")
    page.wait_for_function("window.__mate && window.__mate.builds >= 1 && !window.__mate.busy",
                           timeout=READY_MS)
    return page


def wait_mate(page, before):
    page.wait_for_function("(n) => window.__mate.builds > n && !window.__mate.busy", arg=before,
                           timeout=READY_MS)
