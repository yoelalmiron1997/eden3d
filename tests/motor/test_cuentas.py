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
SQL = open(os.path.join(REPO, "supabase", "esquema.sql"), encoding="utf-8").read().lower()
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
