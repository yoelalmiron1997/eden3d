# -*- coding: utf-8 -*-
"""Supabase de mentira para probar server/api.py: tokens fijos → cuentas con rol."""
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CUENTAS = {"tok-usuario": ("00000000-0000-0000-0000-00000000000a", "usuario"),
           "tok-pro": ("00000000-0000-0000-0000-00000000000b", "pro"),
           "tok-admin": ("00000000-0000-0000-0000-00000000000c", "admin")}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        tok = self.headers.get("Authorization", "")[7:]
        if self.headers.get("apikey") != "anon-falsa" or tok not in CUENTAS:
            return self._r(401, {"msg": "invalid JWT"})
        uid, rol = CUENTAS[tok]
        if self.path.startswith("/auth/v1/user"):
            return self._r(200, {"id": uid})
        if self.path.startswith("/rest/v1/perfiles") and uid in self.path:
            return self._r(200, [{"rol": rol}])
        self._r(404, {})

    def _r(self, c, o):
        b = json.dumps(o).encode()
        self.send_response(c); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
