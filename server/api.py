# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
Servidor de descargas de TecnoBear (VPS)
========================================
La vista previa se sigue calculando en el navegador, pero los archivos para imprimir
(3MF / STL) y los PDF salen de acá, después de comprobar la cuenta en Supabase:

    POST /api/descargar   cuenta gratis o Pro    → 3MF / STL / ZIP
    POST /api/pdf         sólo Pro o admin       → PDF (consideraciones o guía)
    GET  /api/salud                               → "ok"

Cada pedido trae el token de la sesión (Authorization: Bearer …). El servidor se lo
pregunta a Supabase (/auth/v1/user) y lee el rol en public.perfiles con ese mismo
token (las reglas RLS dejan que cada uno lea su perfil), así que no necesita la clave
service_role. Sin Pro, la marca personalizada se descarta: el archivo sale con la marca
de TecnoBear aunque alguien la haya cambiado en la página.

Sólo biblioteca estándar. El motor corre en procesos aparte (uno por núcleo), con
límites por cuenta y un tope de pedidos en espera. Variables:
    SUPABASE_URL, SUPABASE_ANON_KEY   (obligatorias)
    EDEN3D_WORKERS  procesos del motor (por defecto, los núcleos)
    EDEN3D_PORT     puerto (8000)
"""
import base64
import concurrent.futures as cf
import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ENGINE = os.environ.get("EDEN3D_ENGINE", os.path.join(RAIZ, "engine"))
WEB = os.environ.get("EDEN3D_WEB", os.path.join(RAIZ, "web"))
PDF_JS = os.path.join(AQUI, "pdf.mjs")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()
WORKERS = int(os.environ.get("EDEN3D_WORKERS") or os.cpu_count() or 2)
PUERTO = int(os.environ.get("EDEN3D_PORT", "8000"))

MODULOS = {"macetas": "eden_web", "banda": "banda_web", "chapita": "chapita_web", "mate": "mate_web",
           "sopa": "sopa_web", "topper": "topper_web", "trofeo": "trofeo_web"}
PIEZA_POR_DEFECTO = {"macetas": "MACETA", "chapita": "CHAPITA", "mate": "MATE", "topper": "TOPPER", "trofeo": "FIGURA"}
MARCA = {"macetas": "brand", "mate": "marca"}          # parámetro de la marca personalizada (Pro)
ROLES = {"usuario": {"descargar"}, "pro": {"descargar", "marca", "premium"},
         "admin": {"descargar", "marca", "premium", "sin_limite"}}

MAX_JSON = 64 * 1024                  # opciones del modelo
MAX_CUERPO = 24 * 1024 * 1024         # con archivos (STL propio del mate) o fotos del PDF
MAX_STL = 15 * 1024 * 1024
MAX_SVG = 600 * 1024
POR_HORA = {"descargar": 40, "pdf": 20}
TIMEOUT_MOTOR = 150
TIMEOUT_PDF = 60


class Error(Exception):
    def __init__(self, codigo, msg):
        super().__init__(msg)
        self.codigo, self.msg = codigo, msg


# ------------------------------------------------------------------ cuentas (Supabase)
_cache = {}
_cache_lock = threading.Lock()


def _supabase(ruta, token):
    req = urllib.request.Request(SUPABASE_URL + ruta, headers={
        "apikey": SUPABASE_ANON_KEY, "Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Error(401, "Tu sesión venció: volvé a ingresar.")
        raise Error(502, "No se pudo comprobar tu cuenta. Probá de nuevo en un rato.")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise Error(502, "No se pudo comprobar tu cuenta. Probá de nuevo en un rato.")


def cuenta(token):
    """(id, rol) de la sesión. Se recuerda 60 s para no consultar en cada clic."""
    if not token or len(token) > 4096:
        raise Error(401, "Ingresá con tu cuenta para descargar.")
    clave = hashlib.sha256(token.encode()).hexdigest()
    ahora = time.time()
    with _cache_lock:
        c = _cache.get(clave)
        if c and c[0] > ahora:
            return c[1]
    u = _supabase("/auth/v1/user", token)
    uid = u.get("id") if isinstance(u, dict) else None
    if not uid:
        raise Error(401, "Ingresá con tu cuenta para descargar.")
    filas = _supabase("/rest/v1/perfiles?select=rol&id=eq." + urllib.parse.quote(uid), token)
    rol = filas[0].get("rol") if filas else "usuario"
    rol = rol if rol in ROLES else "usuario"
    with _cache_lock:
        if len(_cache) > 5000:
            _cache.clear()
        _cache[clave] = (ahora + 60, (uid, rol))
    return uid, rol


# ------------------------------------------------------------------ límites por cuenta
_uso = {}
_ocupados = set()
_uso_lock = threading.Lock()


class Turno:
    """Un pedido a la vez por cuenta y un máximo por hora (los admin no tienen límite)."""

    def __init__(self, uid, rol, tipo):
        self.uid, self.libre = uid, "sin_limite" in ROLES[rol]
        self.tipo = tipo

    def __enter__(self):
        if self.libre:
            return self
        ahora = time.time()
        with _uso_lock:
            if self.uid in _ocupados:
                raise Error(429, "Ya estamos armando otro archivo tuyo: esperá a que termine.")
            hist = [t for t in _uso.get((self.uid, self.tipo), []) if t > ahora - 3600]
            if len(hist) >= POR_HORA[self.tipo]:
                raise Error(429, "Llegaste al máximo de descargas por hora. Probá de nuevo en un rato.")
            hist.append(ahora)
            _uso[(self.uid, self.tipo)] = hist
            _ocupados.add(self.uid)
        return self

    def __exit__(self, *a):
        if not self.libre:
            with _uso_lock:
                _ocupados.discard(self.uid)


# ------------------------------------------------------------------ motor (en otro proceso)
def _limpiar(o, prof=0):
    """Opciones del cliente: sin rutas de archivos (las pone el servidor) y acotadas."""
    if prof > 6:
        raise ValueError("opciones demasiado anidadas")
    if isinstance(o, dict):
        return {str(k): _limpiar(v, prof + 1) for k, v in o.items()
                if not str(k).endswith("_path") and not str(k).startswith("__")}
    if isinstance(o, list):
        if len(o) > 2000:
            raise ValueError("lista demasiado larga")
        return [_limpiar(v, prof + 1) for v in o]
    if isinstance(o, str) and len(o) > 2000:
        raise ValueError("texto demasiado largo")
    if o is None or isinstance(o, (bool, int, float, str)):
        return o
    raise ValueError("valor inválido")


def generar(herramienta, formato, opts, pieza, archivos):
    """Corre en un proceso del pool: (nombre, bytes)."""
    if ENGINE not in sys.path:
        sys.path.insert(0, ENGINE)
    mod = __import__(MODULOS[herramienta])
    tmp = []
    try:
        if herramienta == "mate":
            if archivos.get("stl") and opts.get("inserto") == "propio":
                fd, ruta = tempfile.mkstemp(suffix=".stl")
                os.write(fd, archivos["stl"]); os.close(fd); tmp.append(ruta)
                opts["stl_path"] = ruta
            deco = opts.get("deco")
            if isinstance(deco, dict) and deco.get("tipo") == "svg" and archivos.get("svg"):
                fd, ruta = tempfile.mkstemp(suffix=".svg")
                os.write(fd, archivos["svg"]); os.close(fd); tmp.append(ruta)
                opts["deco"] = dict(deco, svg_path=ruta)
        if formato == "3mf":
            nombre, datos = mod.export_3mf(opts)
        elif herramienta in PIEZA_POR_DEFECTO:
            nombre, datos = mod.export_stl(opts, pieza or PIEZA_POR_DEFECTO[herramienta])
        else:
            nombre, datos = mod.export_stl(opts)
        return str(nombre), bytes(datos)
    finally:
        for r in tmp:
            try:
                os.remove(r)
            except OSError:
                pass


_pool = None
_espera = threading.BoundedSemaphore(WORKERS * 4)    # pedidos en curso + en cola


def pool():
    global _pool
    if _pool is None:
        _pool = cf.ProcessPoolExecutor(max_workers=WORKERS, mp_context=mp.get_context("spawn"),
                                       max_tasks_per_child=40)
    return _pool


def descargar(cuerpo, rol):
    herramienta = cuerpo.get("herramienta")
    formato = cuerpo.get("formato")
    if herramienta not in MODULOS or formato not in ("3mf", "stl"):
        raise Error(400, "Pedido inválido.")
    try:
        opts = _limpiar(cuerpo.get("opts") or {})
    except ValueError as e:
        raise Error(400, "Opciones inválidas: %s." % e)
    if not isinstance(opts, dict) or len(json.dumps(opts)) > MAX_JSON:
        raise Error(400, "Opciones inválidas.")
    if herramienta in MARCA and "marca" not in ROLES[rol]:
        opts.pop(MARCA[herramienta], None)                  # sin Pro: la marca de TecnoBear
    pieza = cuerpo.get("pieza")
    if pieza is not None and (not isinstance(pieza, str) or len(pieza) > 40):
        raise Error(400, "Pieza inválida.")
    archivos = {}
    for k, tope in (("stl", MAX_STL), ("svg", MAX_SVG)):
        v = (cuerpo.get("archivos") or {}).get(k)
        if v:
            try:
                archivos[k] = base64.b64decode(v, validate=True)
            except (ValueError, TypeError):
                raise Error(400, "Archivo adjunto inválido.")
            if len(archivos[k]) > tope:
                raise Error(413, "El archivo adjunto es demasiado grande.")
    if not _espera.acquire(blocking=False):
        raise Error(503, "Hay mucha gente descargando ahora mismo. Probá de nuevo en un minuto.")
    try:
        fut = pool().submit(generar, herramienta, formato, opts, pieza, archivos)
        try:
            return fut.result(timeout=TIMEOUT_MOTOR)
        except cf.TimeoutError:
            fut.cancel()
            raise Error(504, "El modelo tardó demasiado en generarse. Probá con menos detalle.")
        except ValueError as e:
            raise Error(422, str(e) or "Con estas medidas el modelo no se puede imprimir.")
        except cf.process.BrokenProcessPool:
            global _pool
            _pool = None
            raise Error(500, "El motor se reinició. Probá de nuevo.")
    finally:
        _espera.release()


def pdf(cuerpo):
    tipo = cuerpo.get("tipo")
    if tipo not in ("consideraciones", "guia"):
        raise Error(400, "Pedido inválido.")
    if tipo == "consideraciones":
        if cuerpo.get("herramienta") not in ("chapita", "banda", "mate", "topper", "sopa", "trofeo"):
            raise Error(400, "Pedido inválido.")
        if not isinstance(cuerpo.get("summary"), dict):
            raise Error(400, "Pedido inválido.")
    elif not isinstance(cuerpo.get("datos"), dict) or not isinstance(cuerpo["datos"].get("summary"), dict):
        raise Error(400, "Pedido inválido.")
    for clave in ("foto",):
        f = cuerpo.get(clave)
        if f is not None and not (isinstance(f, str) and f.startswith("data:image/jpeg;base64,")):
            raise Error(400, "La foto tiene que ser JPEG.")
    if not _espera.acquire(blocking=False):
        raise Error(503, "Hay mucha gente descargando ahora mismo. Probá de nuevo en un minuto.")
    try:
        r = subprocess.run(["node", PDF_JS], input=json.dumps(cuerpo).encode("utf-8"),
                           capture_output=True, timeout=TIMEOUT_PDF, env=dict(os.environ, EDEN3D_WEB=WEB))
    except subprocess.TimeoutExpired:
        raise Error(504, "El PDF tardó demasiado. Probá de nuevo.")
    finally:
        _espera.release()
    if r.returncode != 0 or not r.stdout.startswith(b"%PDF"):
        sys.stderr.write("pdf: %s\n" % r.stderr.decode("utf-8", "replace")[-2000:])
        raise Error(500, "No se pudo armar el PDF.")
    paginas = r.stdout.count(b"/Type /Page\n") or r.stdout.count(b"/Type /Page ") or 1
    s = cuerpo.get("summary") or cuerpo["datos"]["summary"]
    sku = "".join(c for c in str(s.get("sku", "TecnoBear")) if c.isalnum() or c in "-_")[:80] or "TecnoBear"
    nombre = "%s_%s.pdf" % (sku, "guia" if tipo == "guia" else "consideraciones")
    return nombre, r.stdout, paginas


# ------------------------------------------------------------------ HTTP
class Manejador(BaseHTTPRequestHandler):
    server_version = "TecnoBear"
    timeout = 30                       # socket: corta conexiones que no mandan nada
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.headers.get("X-Forwarded-For", self.client_address[0]), fmt % a))

    def _json(self, codigo, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _archivo(self, nombre, datos, extra=None):
        tipo = {"3mf": "model/3mf", "stl": "model/stl", "zip": "application/zip",
                "pdf": "application/pdf"}.get(nombre.rsplit(".", 1)[-1].lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Content-Disposition", "attachment; filename*=UTF-8''%s" % urllib.parse.quote(nombre))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path.rstrip("/") in ("/api/salud", "/salud"):
            return self._json(200, {"ok": True})
        self._json(404, {"error": "No existe."})

    def do_POST(self):
        ruta = self.path.split("?", 1)[0].rstrip("/")
        if ruta.startswith("/api"):
            ruta = ruta[4:]
        try:
            if ruta not in ("/descargar", "/pdf"):
                raise Error(404, "No existe.")
            largo = int(self.headers.get("Content-Length") or 0)
            if largo <= 0 or largo > MAX_CUERPO:
                raise Error(413, "Pedido demasiado grande.")
            try:
                cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise Error(400, "Pedido inválido.")
            if not isinstance(cuerpo, dict):
                raise Error(400, "Pedido inválido.")
            auth = self.headers.get("Authorization", "")
            uid, rol = cuenta(auth[7:].strip() if auth.lower().startswith("bearer ") else "")
            if ruta == "/descargar":
                with Turno(uid, rol, "descargar"):
                    nombre, datos = descargar(cuerpo, rol)
                return self._archivo(nombre, datos)
            if "premium" not in ROLES[rol]:
                raise Error(403, "El PDF es parte del plan Premium.")
            with Turno(uid, rol, "pdf"):
                nombre, datos, paginas = pdf(cuerpo)
            return self._archivo(nombre, datos, {"X-Paginas": str(paginas), "Access-Control-Expose-Headers": "X-Paginas"})
        except Error as e:
            self._json(e.codigo, {"error": e.msg})
        except Exception as e:                       # noqa: BLE001 — nunca dejar colgado al cliente
            sys.stderr.write("error: %r\n" % e)
            self._json(500, {"error": "Algo falló en el servidor. Probá de nuevo."})


def main():
    if not (SUPABASE_URL and SUPABASE_ANON_KEY):
        sys.exit("Faltan SUPABASE_URL y SUPABASE_ANON_KEY")
    srv = ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador)
    srv.daemon_threads = True
    srv.request_queue_size = 64
    print("TecnoBear API en :%d · %d procesos del motor" % (PUERTO, WORKERS), flush=True)
    try:
        srv.serve_forever()
    finally:
        if _pool:
            _pool.shutdown(cancel_futures=True)


if __name__ == "__main__":
    main()
