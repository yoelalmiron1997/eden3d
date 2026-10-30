# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Arma la página estática para GitHub Pages en una carpeta (por defecto _site/).

    python tools/build_site.py --out _site [--node-modules node_modules]

  * copia web/ (configurador + página de calidad);
  * copia los módulos del motor que corren en el navegador a py/ con un
    manifest versionado (hash del contenido, para no quedar con caché vieja);
  * copia Pyodide y three.js desde node_modules a vendor/ con sus licencias;
  * genera licencia.html a partir de LICENSE y el .nojekyll.
"""
import argparse
import hashlib
import html
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
WEB_MODULES = ["eden_core.py", "eden_surface.py", "eden_floor.py", "eden_font.py",
               "eden_catalog.py", "eden_web.py", "eden_selftest.py", "eden_escena.py",
               "eden_plantas.py", "colecciones/catalogo_eden3d.json",
               "colecciones/plantas.json", "mate_core.py", "mate_web.py", "mate_deco.py",
               "sopa_core.py", "sopa_web.py"]
PYODIDE_FILES = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip",
                 "pyodide-lock.json"]
PYODIDE_NOTICE = """Pyodide 0.27.7 — Mozilla Public License 2.0 (MPL-2.0)
Código fuente: https://github.com/pyodide/pyodide
Texto de la licencia: https://www.mozilla.org/en-US/MPL/2.0/
Estos archivos se distribuyen sin modificaciones. No forman parte de la Obra de Eden3D.
"""


def build(out, node_modules):
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(ROOT, "web"), out)
    # motor
    h = hashlib.sha256()
    pyd = os.path.join(out, "py")
    for rel in WEB_MODULES:
        src = os.path.join(ENGINE, rel)
        dst = os.path.join(pyd, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        with open(src, "rb") as fh:
            h.update(fh.read())
    version = h.hexdigest()[:10]
    with open(os.path.join(pyd, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": version, "files": WEB_MODULES}, fh, indent=1)
    # bibliotecas de terceros
    vp = os.path.join(out, "vendor", "pyodide")
    os.makedirs(vp, exist_ok=True)
    for f in PYODIDE_FILES:
        shutil.copy2(os.path.join(node_modules, "pyodide", f), os.path.join(vp, f))
    with open(os.path.join(vp, "LICENSE-MPL-2.0.txt"), "w", encoding="utf-8") as fh:
        fh.write(PYODIDE_NOTICE)
    vt = os.path.join(out, "vendor", "three")
    os.makedirs(os.path.join(vt, "addons", "controls"), exist_ok=True)
    shutil.copy2(os.path.join(node_modules, "three", "build", "three.module.js"), vt)
    shutil.copy2(os.path.join(node_modules, "three", "build", "three.core.js"), vt) \
        if os.path.isfile(os.path.join(node_modules, "three", "build", "three.core.js")) else None
    for ctl in ("OrbitControls.js", "TransformControls.js"):     # TransformControls: gumball
        shutil.copy2(os.path.join(node_modules, "three", "examples", "jsm", "controls", ctl),
                     os.path.join(vt, "addons", "controls"))
    os.makedirs(os.path.join(vt, "addons", "environments"), exist_ok=True)
    shutil.copy2(os.path.join(node_modules, "three", "examples", "jsm", "environments",
                              "RoomEnvironment.js"), os.path.join(vt, "addons", "environments"))
    shutil.copy2(os.path.join(node_modules, "three", "LICENSE"), os.path.join(vt, "LICENSE"))
    vs = os.path.join(out, "vendor", "supabase")
    os.makedirs(vs, exist_ok=True)
    shutil.copy2(os.path.join(node_modules, "@supabase", "supabase-js", "dist", "umd", "supabase.js"), vs)
    shutil.copy2(os.path.join(node_modules, "@supabase", "supabase-js", "LICENSE"), os.path.join(vs, "LICENSE"))
    # login: la URL y la clave pública de Supabase salen de las variables del repo
    url, key = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if url and key:
        with open(os.path.join(out, "config.js"), "w", encoding="utf-8") as fh:
            fh.write("// generado por tools/build_site.py desde las variables del repositorio\n"
                     "export const SUPABASE = %s;\n" % json.dumps({"url": url, "anonKey": key}))
    vj = os.path.join(out, "vendor", "jspdf")
    os.makedirs(vj, exist_ok=True)
    shutil.copy2(os.path.join(node_modules, "jspdf", "dist", "jspdf.umd.min.js"), vj)
    shutil.copy2(os.path.join(node_modules, "jspdf", "LICENSE"), os.path.join(vj, "LICENSE"))
    # licencia legible en la web
    with open(os.path.join(ROOT, "LICENSE"), encoding="utf-8") as fh:
        lic = fh.read()
    with open(os.path.join(out, "licencia.html"), "w", encoding="utf-8") as fh:
        fh.write("""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Licencia · Eden3D</title>
<script>try{var t=localStorage.getItem("tb-tema");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}</script>
<link rel="stylesheet" href="style.css"></head><body><header class="top"><a class="brand" href="./">
<span class="pill">Eden3D</span><span class="brand-sub">Studio</span></a></header>
<main style="max-width:860px;margin:0 auto;padding:20px 16px"><pre data-testid="licencia-texto"
style="white-space:pre-wrap;font:14px/1.5 ui-monospace,Consolas,monospace">%s</pre></main></body></html>"""
                 % html.escape(lic))
    open(os.path.join(out, ".nojekyll"), "w").close()
    os.makedirs(os.path.join(out, "calidad"), exist_ok=True)
    return version


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "_site"))
    ap.add_argument("--node-modules", default=os.path.join(ROOT, "node_modules"))
    a = ap.parse_args()
    print("sitio en %s (motor %s)" % (a.out, build(a.out, a.node_modules)))
