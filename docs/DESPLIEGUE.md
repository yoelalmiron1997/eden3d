# Despliegue de Eden3D / TecnoBear

## Qué es la app
La **vista previa** corre en el navegador: los generadores (Python) se ejecutan con
Pyodide (WebAssembly), un worker por herramienta. En el VPS, los **archivos para imprimir
(3MF/STL) y los PDF** los genera un servidor propio (`server/api.py`) después de comprobar
la cuenta, así el Premium no se puede habilitar desde la consola del navegador. El login
y los roles están en **Supabase** (servicio aparte, gestionado).

| Capa | Tecnología | Dónde corre |
|---|---|---|
| Vista previa | Python 3.12, solo biblioteca estándar (`engine/*.py`) | Navegador (Pyodide 0.27.7) |
| Descargas y PDF | `server/api.py` (Python, biblioteca estándar) + jsPDF en Node | VPS (contenedor `api`) |
| Interfaz | HTML + JS (módulos ES, sin framework ni bundler) | Navegador |
| Visor 3D | three.js 0.170 | Navegador |
| Login / roles | Supabase (Postgres + Auth + RLS), supabase-js 2.58 | Nube de Supabase |
| Captcha | Cloudflare Turnstile | Cloudflare + Supabase |
| Armado | `tools/build_site.py` + `npm ci` | Build (CI o Docker) |
| Tests | pytest, Playwright/Chromium, trimesh, manifold3d, scipy… | Solo CI |

El sitio armado pesa ~24 MB (14 MB son Pyodide). Con gzip, el `.wasm` baja de 9 a 3,2 MB.

## Contenedores (`docker compose up -d --build`)
- **web** (`Dockerfile`): arma el sitio con `EDEN3D_API=/api` y lo sirve con nginx. En ese
  modo la web **no trae** el código de exportación del motor (`export_3mf`, `export_stl`
  y lo que sólo usaban ellos) ni el armado de los PDF (`guia*.js`, jsPDF).
- **api** (`server/Dockerfile`): recibe `POST /api/descargar` y `POST /api/pdf` con el token
  de la sesión, se lo pregunta a Supabase, lee el rol en `perfiles` y genera el archivo.
  - Sin sesión: 401. Cuenta gratis: descarga con la marca de TecnoBear (la marca propia
    se descarta). Pro/admin: marca propia y PDF.
  - Un pedido a la vez por cuenta, 40 descargas y 20 PDF por hora (admin sin límite),
    y si hay demasiados en cola responde "probá en un minuto".
  - No necesita la clave `service_role`: usa la *anon* y el token del usuario (RLS).
- **caddy**: HTTPS automático; `/api/*` va a `api`, el resto a `web`.

## Paso a paso en el VPS
1. Instalar Docker y apuntar el dominio (registro A) a la IP del VPS.
2. `git clone … && cd eden3d && cp .env.example .env` y completar:
   `DOMINIO`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `TURNSTILE_SITE_KEY`, `EDEN3D_WORKERS`
   (≈ núcleos del VPS).
3. `docker compose up -d --build`
4. Actualizar: `git pull && docker compose up -d --build`

Con 2 vCPU / 2 GB alcanza para empezar: la vista previa no le cuesta nada al servidor;
sólo cada descarga (unos segundos de CPU) y cada PDF.

## Supabase (una vez)
1. **SQL Editor**: volver a correr `supabase/esquema.sql` (agrega los límites del feedback).
2. **Captcha**: en Cloudflare → Turnstile, crear un widget para tu dominio. La *Site Key*
   va en `TURNSTILE_SITE_KEY` (.env y variable del repo para GitHub Pages); la *Secret Key*
   va en Supabase → Authentication → Attack Protection → Enable Captcha → Turnstile.
   Activalo en Supabase **después** de desplegar la web con la Site Key: si no, nadie puede
   ingresar.
3. **Mail**: Authentication → Emails → SMTP Settings con un proveedor propio (Brevo,
   Resend…). El de fábrica manda 2 mails por hora; después subí el límite en Rate Limits.

## GitHub Pages
Sigue funcionando como antes (sin servidor): ahí las descargas y los PDF se generan en el
navegador, así que el Premium se puede saltear. Para los 500 usuarios, usá el VPS.
