# -*- coding: utf-8 -*-
"""Sirve una web armada (modo servidor) y pasa /api/* a server/api.py (como Caddy en el VPS)."""
import functools, sys, urllib.request, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class H(SimpleHTTPRequestHandler):
    api = ""

    def log_message(self, *a):
        pass

    def do_POST(self):
        largo = int(self.headers.get("Content-Length") or 0)
        req = urllib.request.Request(self.api + self.path, data=self.rfile.read(largo), method="POST",
                                     headers={k: v for k, v in self.headers.items() if k.lower() in ("content-type", "authorization")})
        try:
            r = urllib.request.urlopen(req, timeout=200); codigo = r.status
        except urllib.error.HTTPError as e:
            r = e; codigo = e.code
        b = r.read()
        self.send_response(codigo)
        for k, v in r.headers.items():
            if k.lower() not in ("content-length", "connection", "transfer-encoding", "date", "server"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


if __name__ == "__main__":
    sitio, puerto, api = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    H.api = api
    ThreadingHTTPServer(("127.0.0.1", puerto), functools.partial(H, directory=sitio)).serve_forever()
