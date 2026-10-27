# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Ayudas de los tests e2e."""
READY_MS = 180_000


def open_app(browser, base_url, viewport=(1360, 900)):
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              accept_downloads=True)
    page = ctx.new_page()
    page.console_errors = []
    page.on("console", lambda m: page.console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.console_errors.append(str(e)))
    page.goto(base_url)
    page.wait_for_function("window.__eden && window.__eden.builds >= 1 && !window.__eden.busy",
                           timeout=READY_MS)
    return page


def wait_build(page, before):
    page.wait_for_function("(n) => window.__eden.builds > n && !window.__eden.busy", arg=before,
                           timeout=READY_MS)
