# Herramientas de TecnoBear · Eden3D Studio

[![Calidad y GitHub Pages](https://github.com/yoelalmiron1997/eden3d/actions/workflows/calidad.yml/badge.svg)](https://github.com/yoelalmiron1997/eden3d/actions/workflows/calidad.yml)

Configurador web de **macetas paramétricas para impresión 3D (FDM, PLA)** de Eden3D:
elegís diseño, tamaño, plato con autorriego y drenaje, lo ves en 3D y bajás el 3MF.

* **20 plantas en 3D**, agrupadas por tipo (**una por tipo**, hasta 4 por maceta):
  * suculentas: echeveria, haworthia, aloe, jade, lithops;
  * cactus: cactus columnar, mammillaria, opuntia y **cardón**;
  * colgantes: rosario, potus; follaje: sansevieria;
  * **nativas argentinas**: ceibo, jacarandá, ombú, lapacho y arrayán (árboles, como
    ejemplar joven o bonsái), yerba mate, cortadera y espinillo/aromo.

  Cada una trae su **ficha de cuidados** (luz, riego por estación, cómo usar el
  autorriego con los ml de tu maceta, sustrato, plagas, señales de problemas y
  toxicidad para mascotas con fuente) y aviso si combinás plantas con cuidados distintos.
* Las plantas **nacen** desde la tierra al elegirlas y se **mueven con el viento**
  según qué tan flexibles son.
* **Tipo de tierra**: piedritas blancas, tierra negra, arcilla expandida, corteza de
  pino, piedra volcánica o musgo (por defecto, la sugerida para el riego de la planta).
* **Escenarios**: estudio, oficina, **jardín** (mesa de madera al aire libre con una
  foto real de jardín desenfocada atrás, de Poly Haven, CC0) y taller de trabajo, con **iluminación** ajustable (estudio,
  mañana, atardecer, noche) y dirección del sol.
* **Agua interactiva** en el plato de autorriego: olas, vaivén y una simulación de
  ondas; tocás el agua y cae una gota que salpica, y hay lluvia y "hacer olas".
* **Despiece animado**: plato, agua, maceta, tierra y plantas se separan y se vuelven
  a armar en loop, con el nombre de cada pieza.
* **Impresión 3D**: la maceta o el plato sobre la cama de la impresora, capa por capa
  (0,2 mm), con el cabezal recorriendo el contorno de cada capa.
* **Guía de uso en PDF**: foto, medidas, cómo usar el autorriego con los ml reales,
  cuidados de cada planta y de la pieza de PLA.
* Panel con textos cortos y secciones plegables, pensado para el celular.
* **Foto** de producto 1080×1350 (formato Instagram) con un clic.

* **Cuentas y roles** (Supabase): usuario, **Pro** (paquete extra: cambia el texto de
  la marca de agua) y **admin** (panel `admin.html` con roles y cobertura de la marca
  en cada maceta). Configuración: [docs/SUPABASE.md](docs/SUPABASE.md).
* **Marca de agua personalizada**: texto libre (letras, números, acentos, ñ y signos)
  grabado en la base; un test arma los 17 diseños con textos de prueba y verifica que
  ninguna pieza se rompa.

### Mate con hueco

Segunda herramienta: **mates imperiales para imprimir en 3D con el hueco exacto del
inserto** (`web/mate.html`, motor `engine/mate_core.py`).

* **10 modelos**: imperial clásico, camionero, torpedo, copa y pera, moderno
  cilíndrico, **cohete** (con aletas y banda para la guarda), **vaso redondeado** (con
  medallón para un relieve propio), **camionero anillado** y **facetado** (caras
  triangulares alternadas con medallones).
* **Hueco para** el vaso de polímero, el adaptador, **los dos juntos** o **un STL
  propio** (de revolución: el motor lee el perfil y verifica el volumen).
* El hueco sale del perfil exacto de los STL de los insertos, con **holgura** ajustable.
* **Autoajuste**: el mate crece en alto y ancho hasta cumplir la **pared** y el **fondo**
  mínimos (medidos de verdad, incluso en las facetas y los medallones).
* Una sola **malla cerrada** sin booleanas (piel → boca → hueco), descarga en **STL o
  3MF** con la licencia en los metadatos. Vista con el inserto adentro, corte y capas.
* Componente de Grasshopper: `grasshopper/gh_mate_hueco.py` (mismo motor con
  booleanas de Rhino y mates propios en Brep/Mesh).

* **Web (home de herramientas):** https://yoelalmiron1997.github.io/eden3d/
* **Mate con hueco:** https://yoelalmiron1997.github.io/eden3d/mate.html
* **Generador de macetas:** https://yoelalmiron1997.github.io/eden3d/macetas.html
* **Tablero de calidad:** https://yoelalmiron1997.github.io/eden3d/calidad/

> © 2026 Eden3D — Yoel Almirón. **Todos los derechos reservados.** El repositorio es
> público para poder verse, pero no es código abierto: ver [LICENSE](LICENSE).

## Cómo funciona

```
engine/          motor paramétrico en Python puro (el mismo que usa Grasshopper)
                 mate_core.py / mate_web.py: motor del Mate con hueco
web/             página estática: visor three.js + motor corriendo en el navegador (Pyodide)
specs/           requisitos con ID (Spec-Driven Development)
tests/motor/     pytest: geometría, autorriego (booleanas exactas), exportación, licencia
tests/web/       Playwright: la web de punta a punta, con el motor real
tools/           build de la página, matriz de trazabilidad, generadores de fondos
grasshopper/     componente de Rhino 8 (Eden3D Studio en Grasshopper)
```

GitHub Pages sólo sirve archivos estáticos, así que **el motor corre dentro del
navegador** con [Pyodide](https://pyodide.org) en un Web Worker: no hay servidor ni
se sube nada. El mismo módulo (`engine/eden_web.py`) se testea con CPython en
`tests/motor`, así que lo que valida la suite es lo que ve el cliente.

## Calidad: specs → tests → tablero

1. Cada requisito vive en `specs/*.yml` con un ID (`AUT-001`, `WEB-004`, …) y un
   criterio de aceptación. Ver [specs/README.md](specs/README.md).
2. Cada test declara qué verifica: `@pytest.mark.spec("AUT-001")`.
3. En cada push, GitHub Actions corre los tests del motor y los e2e, arma la
   **matriz de trazabilidad** y aplica el **gate**: falla si una spec activa no tiene
   tests, si un test no está atado a una spec, si referencia un ID inexistente o si
   algo falla.
4. En `main` se publica la web y el tablero de calidad (con historial por versión).

## Correr en local

```bash
npm ci                                   # Pyodide + three.js para la web
pip install -r requirements-dev.txt
python -m playwright install chromium

python tools/build_site.py --out _site   # arma la web
python -m http.server 8000 -d _site      # http://localhost:8000

python -m pytest tests/motor --resultados reports/motor.json
EDEN3D_SITE=_site python -m pytest tests/web --resultados reports/web.json
python tools/spec_matrix.py --strict --resultados reports/motor.json reports/web.json
```

`EDEN3D_TODO=1` corre los tests del motor sobre los 17 diseños (por defecto, una muestra de 4).

## Activar GitHub Pages (una sola vez)

*Settings → Pages → Build and deployment → Source: **GitHub Actions***.

## Licencia

Propietaria, todos los derechos reservados: [LICENSE](LICENSE). Las bibliotecas de
terceros conservan sus licencias: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
