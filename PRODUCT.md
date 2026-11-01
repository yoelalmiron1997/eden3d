# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
La comunidad del canal de YouTube de TecnoBear (Argentina): gente con impresora 3D, de
principiante a intermedia, que quiere un archivo listo para imprimir sin modelar en CAD.
Entran desde un video o desde el inicio, eligen una herramienta, la personalizan en el
navegador (también desde el celular) y bajan el archivo.

## Product Purpose
TecnoBear ofrece generadores gratuitos online para diseñar, personalizar y preparar
proyectos de impresión 3D. El éxito es que el visitante encuentre la herramienta, la abra
y se lleve un 3MF/STL que imprime bien a la primera.

## Positioning
Cada herramienta tiene un motor paramétrico propio que corre en el navegador (Pyodide) y
garantiza piezas imprimibles: mallas cerradas, encastres con holgura, todo unido en una
pieza. No son plantillas sueltas: el archivo sale calculado para lo que pediste.

## Operating Context
Sitio estático en GitHub Pages (`web/`, armado con `tools/build_site.py`). Páginas:
`index.html` (inicio), `macetas.html`, `mate.html`, `sopa.html`, `topper.html`,
`admin.html`, `calidad/`, `licencia.html`. Cuentas opcionales con Supabase
(`auth.js`, `auth-ui.js`): roles visitante, usuario, pro, admin; si no hay cuentas
configuradas, todo es libre. Modo claro / oscuro / automático (`theme.js`). Tests e2e con
Playwright y specs SDD en `specs/`.

## Capabilities and Constraints
- Seis herramientas: Generador de macetas con autorriego (Impresión 3D), Mate con hueco
  (Impresión 3D), Sopa de letras 3D (Entretenimiento), Topper para tortas
  (Personalización), Chapitas para collares de perros y gatos (Personalización) y
  Trofeos para eventos (Personalización). No se inventan ni se quitan herramientas.
- Usar las herramientas es gratis; para descargar los archivos se crea una cuenta gratis
  (cuando las cuentas están configuradas). Las piezas del plan gratis salen con la marca
  de agua ("Eden3D" grabada).
- Plan Premium para la comunidad (rol Pro): actualizaciones más directas, sin marca de
  agua (la cuenta Pro saca o cambia la marca), render (Foto) y PDF con consideraciones
  de impresión en cada motor para mandar a clientes (bloqueados en el plan gratis,
  permiso `premium`). Colecciones preseteadas: anunciadas como "próximamente", todavía
  no construidas. Se pide por Instagram; no hay precio ni
  pago online definidos: no inventarlos.
- HTML/CSS/JS sin framework, módulos ES; sin dependencias nuevas en el inicio.
- Los `data-testid` existentes son contrato con los tests.

## Brand Commitments
- Nombre: TecnoBear. Lema: "Despertá tu tecnología". Voz: español rioplatense, directa.
- Logo: el isotipo original (silueta amarilla pálida #E9EB9F con dos antenas, sobre
  círculo oscuro). Se usa `web/assets/marca/logo-tecnobear.svg`, calcado a vector del original
  `logo-tecnobear-original.png` (coincide en un 99,4 %; pedido del usuario). No se redibuja, no se
  reinterpreta, no se cambia por emoji ni ícono. El logo no gira: en el navbar y el footer
  está quieto y en el hero flota suave (pedido del usuario).
- Redes reales: YouTube https://www.youtube.com/@TecnoBearARG e Instagram
  https://www.instagram.com/tecnobearr/. No inventar otras.
- Inicio: oscuro por defecto con acentos verde lima y amarillo de la marca (pedido del
  usuario: estilo Industrial Tech / InfraCore, bordes rectos 0–4 px).

## Evidence on Hand
Imágenes reales de cada herramienta renderizadas por los motores en
`web/assets/herramientas/` (`*_v.jpg`, `*_v_450.jpg`, `*.jpg`). No hay testimonios,
cifras de usuarios ni email de contacto: no inventarlos.

## Product Principles
1. El archivo tiene que imprimir bien: la garantía de imprimibilidad es el producto.
2. Todo desde el navegador, sin instalar nada, también en el celular.
3. Gratis para la comunidad; la cuenta sólo para descargar.
4. Cada herramienta nueva entra al catálogo sin rehacer el inicio.

## Accessibility & Inclusion
WCAG AA de contraste, navegación por teclado con foco visible, `prefers-reduced-motion`
respetado, sin scroll horizontal en 390 px.
