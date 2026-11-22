# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
# Imagen de producción: arma la web estática (build_site.py) y la sirve con nginx.
# El motor Python corre en el navegador (Pyodide), así que el servidor no ejecuta Python.
#
#   docker build -t eden3d \
#     --build-arg SUPABASE_URL=https://xxxx.supabase.co \
#     --build-arg SUPABASE_ANON_KEY=eyJ... .
#   docker run -p 8080:80 eden3d

# 1) Dependencias del navegador (pyodide, three, supabase-js, jspdf) desde npm
FROM node:22-alpine AS vendor
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --omit=optional --no-audit --no-fund

# 2) Armado del sitio (solo usa la biblioteca estándar de Python)
FROM python:3.12-alpine AS build
WORKDIR /src
COPY --from=vendor /src/node_modules ./node_modules
COPY tools ./tools
COPY engine ./engine
COPY web ./web
COPY LICENSE THIRD_PARTY_NOTICES.md ./
# Las claves "anon" de Supabase son públicas por diseño; si no se pasan, queda web/config.js
ARG SUPABASE_URL=""
ARG SUPABASE_ANON_KEY=""
ENV SUPABASE_URL=${SUPABASE_URL} SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
RUN python tools/build_site.py --out /site

# 3) Servidor
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /site /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/salud >/dev/null || exit 1
