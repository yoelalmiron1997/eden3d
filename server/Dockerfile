# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
# Servidor de descargas (server/api.py): el motor en Python 3.12 y los PDF con jsPDF en Node.
#   docker build -f server/Dockerfile -t tecnobear-api .
#   docker run -e SUPABASE_URL=… -e SUPABASE_ANON_KEY=… -p 8000:8000 tecnobear-api

# jsPDF (la misma versión que usa la web, del package-lock)
FROM node:22-slim AS pdf
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund && mkdir -p /out && cp -r node_modules /out/node_modules \
 && cd /out && rm -rf node_modules/pyodide node_modules/three

FROM python:3.12-slim
# Node para los PDF: el mismo binario de la imagen oficial (las dos son Debian bookworm)
COPY --from=pdf /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY --from=pdf /out/node_modules ./node_modules
COPY engine ./engine
COPY server/api.py server/pdf.mjs ./server/
# sólo lo que arma los PDF; package.json marca los .js como módulos ES para Node
COPY web/guia.js web/guia-impresion.js web/care.js ./web/
RUN echo '{"type":"module"}' > web/package.json \
 && rm -rf engine/renders engine/__pycache__ \
 && useradd --system --uid 10001 --home /app tecnobear \
 && python -m compileall -q engine server
USER tecnobear
ENV PYTHONUNBUFFERED=1 TMPDIR=/tmp EDEN3D_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=2)" || exit 1
CMD ["python", "server/api.py"]
