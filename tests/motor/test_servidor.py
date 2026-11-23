# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Servidor de descargas (server/api.py) contra un Supabase de mentira, el build en modo
servidor, el captcha en el build y los límites del feedback en la base."""
import base64
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL = open(os.path.join(REPO, "supabase", "esquema.sql"), encoding="utf-8").read().lower()


def _puerto():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _esperar(url, t=20):
    fin = time.time() + t
    while time.time() < fin:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("no levantó " + url)


@pytest.fixture(scope="module")
def api():
    ps, pa = _puerto(), _puerto()
    web = tempfile.mkdtemp(prefix="tb_api_web_")
    for f in ("guia.js", "guia-impresion.js", "care.js"):
        shutil.copy2(os.path.join(REPO, "web", f), web)
    with open(os.path.join(web, "package.json"), "w") as fh:
        fh.write('{"type":"module"}')
    procs = [subprocess.Popen([sys.executable, os.path.join(REPO, "tests", "servidor", "supabase_falso.py"), str(ps)])]
    env = dict(os.environ, SUPABASE_URL="http://127.0.0.1:%d" % ps, SUPABASE_ANON_KEY="anon-falsa",
               EDEN3D_PORT=str(pa), EDEN3D_WORKERS="2", EDEN3D_WEB=web)
    procs.append(subprocess.Popen([sys.executable, os.path.join(REPO, "server", "api.py")], env=env))
    base = "http://127.0.0.1:%d/api" % pa
    _esperar(base + "/salud")
    yield base
    for p in procs:
        p.terminate()
    shutil.rmtree(web, ignore_errors=True)


def post(base, ruta, cuerpo, tok=None):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(base + ruta, data=json.dumps(cuerpo).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


CHAPITA = {"herramienta": "chapita", "formato": "3mf", "opts": {"nombre": "Roma"}}


@pytest.mark.spec("CUE-012")
def test_sin_sesion_no_descarga(api):
    assert post(api, "/descargar", CHAPITA)[0] == 401
    assert post(api, "/descargar", CHAPITA, "token-inventado")[0] == 401
    assert post(api, "/descargar", {**CHAPITA, "herramienta": "../engine"}, "tok-usuario")[0] == 400


@pytest.mark.spec("CUE-012")
def test_cuenta_gratis_baja_el_3mf(api):
    c, h, b = post(api, "/descargar", CHAPITA, "tok-usuario")
    assert c == 200, b[:200]
    assert "Chapita" in h["Content-Disposition"] and h["Content-Disposition"].endswith(".3mf")
    assert zipfile.is_zipfile(io.BytesIO(b))


@pytest.mark.spec("CUE-012")
def test_la_marca_propia_es_solo_pro(api):
    base = post(api, "/descargar", {"herramienta": "macetas", "formato": "stl", "opts": {}}, "tok-usuario")[2]
    pedido = {"herramienta": "macetas", "formato": "stl", "opts": {"brand": "MI MARCA"}}
    gratis = post(api, "/descargar", pedido, "tok-usuario")
    pro = post(api, "/descargar", pedido, "tok-pro")
    assert gratis[0] == pro[0] == 200
    assert gratis[2] == base, "sin Pro la marca propia tiene que descartarse"
    assert pro[2] != base, "con Pro la marca propia va en el archivo"


@pytest.mark.spec("CUE-012")
def test_las_rutas_del_cliente_se_ignoran(api):
    c, _, b = post(api, "/descargar", {"herramienta": "mate", "formato": "stl",
                                       "opts": {"inserto": "propio", "stl_path": "/etc/passwd"}}, "tok-usuario")
    assert c == 422 and "passwd" not in b.decode()


@pytest.mark.spec("CUE-012")
def test_pdf_solo_con_pro(api):
    sys.path.insert(0, os.path.join(REPO, "engine"))
    import chapita_web
    s = chapita_web.build({"nombre": "Roma"})["summary"]
    pedido = {"tipo": "consideraciones", "herramienta": "chapita", "summary": s}
    assert post(api, "/pdf", pedido, "tok-usuario")[0] == 403
    if not shutil.which("node"):
        pytest.skip("sin Node no se puede armar el PDF")
    c, h, b = post(api, "/pdf", pedido, "tok-pro")
    assert c == 200 and b.startswith(b"%PDF") and h["X-Paginas"] == "1"


@pytest.mark.spec("CUE-012")
def test_un_pedido_a_la_vez_por_cuenta(api):
    res = []
    hilos = [threading.Thread(target=lambda: res.append(post(api, "/descargar",
             {"herramienta": "macetas", "formato": "3mf", "opts": {}}, "tok-pro")[0])) for _ in range(3)]
    for t in hilos:
        t.start()
    for t in hilos:
        t.join()
    assert sorted(res)[0] == 200 and 429 in res


@pytest.mark.spec("CUE-012")
def test_build_en_modo_servidor_sin_exportacion(tmp_path):
    out = tmp_path / "sitio"
    env = dict(os.environ, EDEN3D_API="/api")
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "TURNSTILE_SITE_KEY"):
        env.pop(k, None)
    subprocess.check_call([sys.executable, os.path.join(REPO, "tools", "build_site.py"), "--out", str(out)], env=env)
    assert 'export const API = {"url": "/api"}' in (out / "config.js").read_text(encoding="utf-8")
    assert not (out / "guia.js").exists() and not (out / "guia-impresion.js").exists()
    assert not (out / "vendor" / "jspdf").exists()
    for f in (out / "py").glob("*_web.py"):
        txt = f.read_text(encoding="utf-8")
        assert "def export_3mf" not in txt and "def export_stl" not in txt, f.name
        compile(txt, f.name, "exec")
    # el motor podado sigue armando la vista previa
    cod = ("import sys; sys.path.insert(0, %r); import chapita_web, eden_web; "
           "assert chapita_web.build({'nombre': 'Roma'})['summary']['valid']; "
           "assert eden_web.build({})['summary']; "
           "assert chapita_web.cotizar({'nombre': 'Roma'})['piezas']" % str(out / "py"))   # el cotizador sigue andando
    subprocess.check_call([sys.executable, "-c", cod])


@pytest.mark.spec("CUE-010")
def test_captcha_en_el_build(tmp_path):
    out = tmp_path / "sitio"
    env = dict(os.environ, TURNSTILE_SITE_KEY="1x00000000000000000000AA", SUPABASE_URL="https://x.supabase.co",
               SUPABASE_ANON_KEY="anon")
    subprocess.check_call([sys.executable, os.path.join(REPO, "tools", "build_site.py"), "--out", str(out)], env=env)
    cfg = (out / "config.js").read_text(encoding="utf-8")
    assert 'export const CAPTCHA = {"siteKey": "1x00000000000000000000AA"}' in cfg
    auth = open(os.path.join(REPO, "web", "auth.js"), encoding="utf-8").read()
    assert auth.count("conCaptcha(") == 3      # ingreso, registro y recuperación


@pytest.mark.spec("CUE-011")
def test_limites_del_feedback_en_la_base():
    bloque = SQL.split("límites anti-spam del feedback", 1)[1]
    assert "create table if not exists public.feedback_envios" in bloque
    assert "alter table public.feedback_envios enable row level security" in bloque
    assert not re.search(r"create policy[^;]*on public\.feedback_envios", SQL), "sin políticas: la web no lo lee"
    assert "security definer" in bloque
    assert "when 'feedback' then 10 else 30" in bloque and "interval '24 hours'" in bloque
    assert "interval '15 seconds'" in bloque and "public.es_admin()" in bloque
    assert "new.creado := now()" in bloque
    for t in ("feedback", "feedback_respuestas"):
        assert "create trigger limite_feedback before insert on public.%s" % t in bloque
    fb = open(os.path.join(REPO, "web", "feedback.js"), encoding="utf-8").read()
    assert "limite_feedback: tope" in fb and "limite_feedback: espera" in fb
