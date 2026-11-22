# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Captcha en la ventana de ingreso (CUE-010) y descargas pedidas al servidor (CUE-013).
Cloudflare, Supabase y el servidor se simulan con rutas de Playwright."""
import json

import pytest

from web_helpers import READY_MS

TURNSTILE = """window.turnstile = {
  render(el, o) { window.__ts = o; setTimeout(() => o.callback('tok-captcha-1'), 30); return 'w1'; },
  reset() { window.__resets = (window.__resets || 0) + 1; setTimeout(() => window.__ts.callback('tok-captcha-2'), 30); } };"""


def _config(page, supabase="", captcha="", api=""):
    """Reemplaza config.js: cuentas, captcha y servidor como en cada despliegue."""
    body = ("export const SUPABASE = %s;\nexport const CAPTCHA = %s;\nexport const API = %s;\n"
            % (json.dumps({"url": supabase, "anonKey": "anon" if supabase else ""}),
               json.dumps({"siteKey": captcha}), json.dumps({"url": api})))
    page.route("**/config.js", lambda r: r.fulfill(content_type="text/javascript", body=body))


@pytest.mark.spec("CUE-010")
def test_captcha_viaja_con_el_ingreso(browser, base_url):
    ctx = browser.new_context()
    pg = ctx.new_page()
    errores = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    # una web con cuentas y captcha configurados (Supabase y Cloudflare de mentira)
    _config(pg, supabase="https://falso.supabase.co", captcha="1x00000000000000000000AA")
    pg.route("https://challenges.cloudflare.com/**", lambda r: r.fulfill(content_type="text/javascript", body=TURNSTILE))
    pedidos = []

    def supabase(route):
        pedidos.append((route.request.url, route.request.post_data or ""))
        if "/auth/v1/token" in route.request.url:
            return route.fulfill(status=400, content_type="application/json",
                                 body='{"error":"invalid_grant","msg":"Invalid login credentials"}')
        route.fulfill(status=200, content_type="application/json", body="{}")
    pg.route("https://falso.supabase.co/**", supabase)
    pg.goto(base_url + "index.html")
    pg.wait_for_selector("[data-testid=btn-ingresar]", timeout=30_000)
    pg.evaluate("import('./auth-ui.js').then((m) => m.openLogin('test'))")
    pg.fill("[data-testid=login-email]", "a@b.com")
    pg.fill("[data-testid=login-pass]", "secreto123")
    pg.click("[data-testid=login-ok]")
    pg.wait_for_function("document.querySelector('#login-msg').textContent.length > 0", timeout=15_000)
    assert "incorrectos" in pg.text_content("#login-msg")
    login = [d for u, d in pedidos if "/auth/v1/token" in u]
    assert login and "tok-captcha-1" in login[0], "el token del captcha tiene que ir en el pedido"
    assert pg.evaluate("window.__ts.sitekey") == "1x00000000000000000000AA"
    assert pg.evaluate("window.__resets") == 1, "cada token sirve una vez: se renueva"
    assert not errores
    ctx.close()


@pytest.mark.spec("CUE-013")
def test_las_descargas_se_piden_al_servidor(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script("window.__EDEN_AUTH_MOCK = %s;" % json.dumps(
        {"role": "usuario", "email": "u@test", "token": "tok-de-prueba"}))
    pg = ctx.new_page()
    _config(pg, api="/api")
    vistos = []

    def servidor(route):
        req = route.request
        vistos.append({"auth": req.headers.get("authorization"), "cuerpo": json.loads(req.post_data)})
        if len(vistos) == 1:
            return route.fulfill(status=200, body=b"PK\x03\x04archivo-de-prueba", headers={
                "Content-Type": "model/3mf", "Content-Disposition": "attachment; filename*=UTF-8''Desde-el-servidor.3mf"})
        route.fulfill(status=429, content_type="application/json",
                      body=json.dumps({"error": "Llegaste al máximo de descargas por hora."}))
    pg.route("**/api/descargar", servidor)
    pg.goto(base_url + "chapita.html")
    pg.wait_for_function("window.__chapita && window.__chapita.builds >= 1 && !window.__chapita.busy", timeout=READY_MS)
    with pg.expect_download() as d:
        pg.click("[data-testid=btn-3mf]")
    assert d.value.suggested_filename == "Desde-el-servidor.3mf"
    v = vistos[0]
    assert v["auth"] == "Bearer tok-de-prueba"
    assert v["cuerpo"]["herramienta"] == "chapita" and v["cuerpo"]["formato"] == "3mf"
    assert v["cuerpo"]["opts"]["nombre"] == pg.evaluate("window.__chapita.builtOpts.nombre")
    pg.click("[data-testid=btn-3mf]")
    pg.wait_for_function("document.querySelector('[data-testid=estado]').textContent.includes('máximo')", timeout=15_000)
    ctx.close()
