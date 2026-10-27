# Eden3D Studio

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
* **Escenarios**: estudio, oficina, jardín y taller de trabajo, con **iluminación**
  ajustable (estudio, mañana, atardecer, noche) y dirección del sol.
* **Agua animada** en el plato de autorriego, con ondulaciones, gotas y nivel mínimo
  o plato lleno.
* **Foto** de producto 1080×1350 (formato Instagram) con un clic.

* **Web:** https://yoelalmiron1997.github.io/eden3d/
* **Tablero de calidad:** https://yoelalmiron1997.github.io/eden3d/calidad/

> © 2026 Eden3D — Yoel Almirón. **Todos los derechos reservados.** El repositorio es
> público para poder verse, pero no es código abierto: ver [LICENSE](LICENSE).

## Cómo funciona

```
engine/          motor paramétrico en Python puro (el mismo que usa Grasshopper)
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
