# Despliegue de Eden3D / TecnoBear

## Qué es la app
Un **sitio estático**. El servidor solo entrega archivos: los generadores (Python) corren
**en el navegador** con Pyodide (WebAssembly), en un worker por herramienta. El login y los
roles están en **Supabase** (servicio aparte, gestionado).

| Capa | Tecnología | Dónde corre |
|---|---|---|
| Motor de modelos | Python 3.12, solo biblioteca estándar (`engine/*.py`) | Navegador (Pyodide 0.27.7) |
| Interfaz | HTML + JS (módulos ES, sin framework ni bundler) | Navegador |
| Visor 3D | three.js 0.170 | Navegador |
| PDF | jsPDF 4.2 | Navegador |
| Login / roles | Supabase (Postgres + Auth + RLS), supabase-js 2.58 | Nube de Supabase |
| Armado | `tools/build_site.py` (Python, biblioteca estándar) + `npm ci` | Build (CI o Docker) |
| Tests | pytest, Playwright/Chromium, trimesh, manifold3d, scipy… | Solo CI |

El sitio armado pesa ~24 MB (14 MB son Pyodide). Con gzip, el `.wasm` baja de 9 a 3,2 MB.

## Con Docker
```bash
cp .env.example .env    # DOMINIO, SUPABASE_URL, SUPABASE_ANON_KEY
docker compose up -d --build
```
- `Dockerfile`: 3 etapas (node → npm ci, python → build_site, nginx → sirve). Imagen final ≈ 75 MB (nginx alpine + 24 MB de sitio).
- `deploy/nginx.conf`: tipo MIME del wasm, gzip, caché larga en `vendor/ fonts/ assets/`
  y `no-cache` en html/js/py (cada deploy se ve al instante). `/salud` para el healthcheck.
- `deploy/Caddyfile`: HTTPS automático (Let's Encrypt) delante de nginx.

Solo la imagen, sin compose: `docker build -t eden3d . && docker run -p 8080:80 eden3d`.

## Actualizar en el VPS
```bash
git pull && docker compose up -d --build
```

## Supabase
Sigue en supabase.com: en el VPS no hace falta. Las claves *anon* van al build (son públicas);
la *service_role* nunca va al servidor web. Ver `docs/SUPABASE.md`.
