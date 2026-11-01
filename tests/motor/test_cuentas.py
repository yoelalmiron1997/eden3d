# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Reglas de las cuentas: el esquema de Supabase (RLS) y que el repo no guarde claves."""
import json
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_TODO = open(os.path.join(REPO, "supabase", "esquema.sql"), encoding="utf-8").read().lower()
SQL, SQL_FB = SQL_TODO.split("-- feedback de la comunidad", 1)        # cuentas y roles | feedback
AUTH_JS = open(os.path.join(REPO, "web", "auth.js"), encoding="utf-8").read()


@pytest.mark.spec("CUE-003")
def test_rls_y_roles():
    assert "alter table public.perfiles enable row level security" in SQL
    assert "default 'usuario'" in SQL
    assert re.search(r"check \(rol in \('usuario', 'pro', 'admin'\)\)", SQL)
    # sólo un admin actualiza roles; no hay política de insert/delete para usuarios
    upd = re.search(r'create policy "admin cambia roles" on public.perfiles\s+for update using \(public.es_admin\(\)\) '
                    r'with check \(public.es_admin\(\)\)', SQL)
    assert upd, "falta la política de update sólo para admin"
    assert "for insert" not in SQL and "for delete" not in SQL and "for all" not in SQL
    assert "after insert on auth.users" in SQL and "nuevo_perfil" in SQL
    assert "no podés quitarte el rol de administrador" in SQL


@pytest.mark.spec("CUE-003")
def test_los_roles_de_la_web_coinciden_con_la_base():
    roles_js = set(re.findall(r"^\s{2}(\w+): \{ label:", AUTH_JS, re.M))
    assert roles_js == {"visitante", "usuario", "pro", "admin"}
    assert set(re.findall(r"'(usuario|pro|admin)'", SQL)) == roles_js - {"visitante"}
    assert "service_role" not in AUTH_JS


@pytest.mark.spec("CUE-003")
def test_el_repo_no_guarda_claves_secretas():
    """La clave de la web es la 'anon' (pública): nunca la service_role."""
    import base64
    cfg = open(os.path.join(REPO, "web", "config.js"), encoding="utf-8").read()
    for tok in re.findall(r"eyJ[\w-]+\.([\w-]+)\.[\w-]+", cfg):
        payload = json.loads(base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4)))
        assert payload["role"] == "anon", payload
    assert "service_role" not in cfg.replace("NUNCA poner acá la clave service_role", "")


@pytest.mark.spec("CUE-001")
def test_la_config_sale_de_las_variables(tmp_path):
    nm = os.path.join(REPO, "node_modules")
    if not os.path.isdir(nm):
        pytest.skip("sin node_modules")
    env = dict(os.environ, SUPABASE_URL="https://ejemplo.supabase.co", SUPABASE_ANON_KEY="clave-publica")
    out = tmp_path / "site"
    subprocess.check_call([sys.executable, os.path.join(REPO, "tools", "build_site.py"), "--out", str(out)],
                          env=env, stdout=subprocess.DEVNULL)
    cfg = (out / "config.js").read_text(encoding="utf-8")
    data = json.loads(cfg.split("SUPABASE = ")[1].rstrip().rstrip(";"))
    assert data == {"url": "https://ejemplo.supabase.co", "anonKey": "clave-publica"}
    assert (out / "vendor" / "supabase" / "supabase.js").is_file()
    for page in ("index.html", "macetas.html", "admin.html"):
        assert (out / page).is_file()


@pytest.mark.spec("CUE-009")
def test_feedback_con_rls():
    for t in ("feedback", "feedback_respuestas", "feedback_votos"):
        assert "create table if not exists public.%s" % t in SQL_FB
        assert "alter table public.%s enable row level security" % t in SQL_FB
        pols = re.findall(r'create policy "[^"]+" on public\.%s\s+for (\w+) to authenticated (using|with check) \(([^;]*)\);' % t, SQL_FB)
        por = {}
        for accion, _, cond in pols:
            por.setdefault(accion, []).append(cond)
        assert por["select"] == ["true"], t
        assert por["insert"] and all("autor = auth.uid()" in c for c in por["insert"]), t
        assert por["delete"] and all(c.startswith("autor = auth.uid()") for c in por["delete"]), t
        # nada "for all" ni políticas para anónimos
        assert "for all" not in SQL_FB and " to anon" not in SQL_FB
    # el estado sólo lo cambia el admin; nadie más actualiza
    upd = re.findall(r'on public\.(\w+)\s+for update to authenticated using \(([^)]*\))\) with check \(([^)]*\))\)', SQL_FB)
    assert upd == [("feedback", "public.es_admin()", "public.es_admin()")], upd
    assert "estado = 'abierto'" in SQL_FB                      # se crea siempre abierto
    assert "check (tipo in ('idea', 'error', 'comentario'))" in SQL_FB
    assert "char_length(texto) between 3 and 1000" in SQL_FB
    assert "on delete cascade" in SQL_FB and "primary key (feedback_id, autor)" in SQL_FB


@pytest.mark.spec("CUE-009")
def test_las_herramientas_del_feedback_coinciden():
    js = open(os.path.join(REPO, "web", "feedback.js"), encoding="utf-8").read()
    m = re.search(r"export const HERRAMIENTAS = \{([^}]*)\}", js)
    web = set(re.findall(r"(\w+):", m.group(1)))
    base = set(re.findall(r"'(\w+)'", re.search(r"check \(herramienta in \(([^)]*)\)\)", SQL_FB).group(1)))
    assert web == base == {"general", "macetas", "mate", "sopa", "topper", "chapita", "trofeo"}
