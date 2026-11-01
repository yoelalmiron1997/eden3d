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
* **Patitas articuladas** (`engine/eden_patitas.py`, diseño propio): patitas, bracitos o
  los dos, con **zapatillas**, botitas o patas de pato, de 2 a 5 eslabones y holgura
  ajustable. Se imprimen **ya armadas** (print in place) acostadas en la cama: bisagras de
  anillo y barra, sin restas booleanas, con la holgura exacta entre eslabones. Van siempre
  en la maceta **sin plato**, **clavadas a la base**: un zócalo abraza el pie de la
  maceta y de ahí salen las caderas. En
  la web, "Sentarla en el borde" la pone sobre un estante con las patas colgando y los
  bracitos saludando.
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

* **17 modelos**, todos lisos: imperial clásico, camionero, torpedo, copa y pera, moderno
  cilíndrico, **cohete** (con aletas y banda para la guarda), **vaso redondeado**,
  **camionero anillado**, **facetado** (caras triangulares alternadas), **triangular**, **con patitas**, **low poly
  torcido** e **irregular** (caras planas de verdad), **vaso cónico**, **labio grueso** y
  **cubos 3D** (relieve de cubos en perspectiva).
* **Hueco para** el **polímero escalonado**, el **polímero base**, **los dos juntos** o **un STL
  propio** (de revolución: el motor lee el perfil y verifica el volumen).
* El hueco sale del perfil exacto de los STL de los insertos, con **holgura** ajustable.
* **Autoajuste**: el mate crece en alto y ancho hasta cumplir la **pared** y el **fondo**
  mínimos (medidos de verdad, incluso en las facetas y los medallones).
* Una sola **malla cerrada** sin booleanas (piel → boca → hueco), descarga en **STL o
  3MF** con la licencia en los metadatos. Vista con el inserto adentro, corte y capas.
* **Relieve de texto o SVG** proyectado sobre la piel (`engine/mate_deco.py`): el SVG se
  rellena sólido (paths, formas básicas, transform, fill-rule) y se apoya en el radio
  real del mate. En la web se acomoda con un **gumball** (mover sobre la superficie,
  girar y escalar; atajos G, R y S) que lo vuelve a apoyar sobre la piel mientras se
  arrastra.
* **9 tipografías** para el texto (`engine/mate_fuentes.py`): la de trazos de Eden3D y 8
  libres y gruesas, fáciles de imprimir (Archivo Black, Anton, Fredoka, Lilita One, Russo
  One, Bungee, Luckiest Guy y Pacifico; licencias en `engine/fuentes/LICENCIAS.md`,
  convertidas con `tools/fuentes.py`), más un **grosor** para engordar letras y dibujos.
* **Cebar el mate** (`web/mate-cebado.js`): animación de la yerba que cae adentro del
  inserto, el mate que se inclina para armar la **montañita** (ángulo ajustable), el agua
  caliente y transparente que entra por el costado bajo (el agua interactiva del plato de las macetas:
  gotas, olas y ondas al tocarla), la bombilla (5 estilos argentinos: resorte, resorte de
  color, filtro cuadrado, cuchara y pala) y el vapor. **Separar** saca el inserto
  con todo adentro, con animación en loop. El motor le pasa a la web la cavidad del
  inserto (`summary.cavidad`).
* **Medallón encastrable**: el diseño va en una pieza circular aparte que entra en un
  bolsillo del mate (fondo plano, proyectado sobre la piel). La pieza se imprime con la
  base plana en la cama y se descarga como `_MEDALLON.stl` (o en el 3MF).
* **Marca de agua grabada debajo de la base** ("Eden3D" por defecto; con **Pro** se cambia
  el texto o se saca).
* **Cuña** opcional (10–45°, 45° por defecto) con un hueco para el pie, para dejar el
  mate inclinado y armar la montañita; se descarga aparte (`_CUNA.stl`) o en el 3MF.
* Componente de Grasshopper: `grasshopper/gh_mate_hueco.py` (mismo motor con
  booleanas de Rhino y mates propios en Brep/Mesh).

### Sopa de letras 3D

Tercera herramienta: **sopas de letras para imprimir, cortadas en piezas que encastran**
(`web/sopa.html`, motor `engine/sopa_core.py`).

* Escribís las palabras (con Ñ, acentos y espacios: se limpian solas) y la dificultad:
  fácil (→ ↓), media (+ diagonales) o difícil (también al revés). "Otra mezcla" cambia
  la semilla; con la misma semilla sale siempre la misma sopa.
* Tablero con **letras en relieve** (fuente de trazos de `eden_font`) y placa opcional
  con la **lista de palabras**.
* Se corta en **piezas de rompecabezas** según la cama de la impresora (mínimo 2 × 2):
  los cortes van entre celdas (ninguna letra queda partida) y las **lengüetas** van en
  la franja libre entre letras, con **holgura** ajustable (cada lado se corre la mitad).
  Las lengüetas son robustas: tamaño adaptado al espacio libre de cada corte (cuello de
  ≥ 3 mm, cabeza 1,55 veces el cuello), filetes en la raíz y base de 4,5 mm.
* **Bloques para marcar**: todos iguales, uno por letra (se imprimen tantos como letras
  tiene la palabra más larga). Cada bloque encastra en **cualquier** letra: todas las
  letras del tablero miden lo mismo de alto (la Ñ y la Q se aplastan un poco) y el
  hueco del bloque las agarra por arriba y por abajo con el *ajuste*. Se ponen sobre la
  palabra encontrada y se reusan; como son iguales, no delatan dónde está cada palabra.
  En la web, tocar una palabra pone los bloques sobre sus letras.
* Vista 3D con piezas separables y la **solución** resaltada; vista 2D de la sopa.
  Descarga en 3MF (una pieza por objeto, acomodadas en la cama) o STL. Para letras de
  otro color: cambio de filamento a la altura de la base.

* **Web (home de herramientas):** https://yoelalmiron1997.github.io/eden3d/
* **Sopa de letras 3D:** https://yoelalmiron1997.github.io/eden3d/sopa.html
* **Mate con hueco:** https://yoelalmiron1997.github.io/eden3d/mate.html
* **Topper para tortas:** https://yoelalmiron1997.github.io/eden3d/topper.html
* **Chapitas para collares:** https://yoelalmiron1997.github.io/eden3d/chapita.html
* **Generador de macetas:** https://yoelalmiron1997.github.io/eden3d/macetas.html
* **Tablero de calidad:** https://yoelalmiron1997.github.io/eden3d/calidad/

> © 2026 Eden3D — Yoel Almirón. **Todos los derechos reservados.** El repositorio es
> público para poder verse, pero no es código abierto: ver [LICENSE](LICENSE).

### Topper para tortas

Cuarta herramienta: **toppers para tortas en una sola pieza** (`web/topper.html`, motor
`engine/topper_core.py`).

* Hasta **3 líneas** (por ejemplo Feliz / Cumpleaños / el nombre), cada una con su
  **tipografía** y su tamaño: 16 tipografías libres, 11 cursivas (Great Vibes, Dancing
  Script, Lobster, Pacifico, Satisfy, Allura, Cookie, Yellowtail, Kaushan Script,
  Parisienne, Alex Brush) y 5 gruesas. Licencias en `engine/fuentes/LICENCIAS.md`.
* **Siempre unido**: el texto se dibuja en una grilla fina, se le pone el **contorno**
  (primero se cierran las luces entre letras y después se engorda sólo lo pedido, así no
  quedan gordas), se suma el **marco** (círculo, corazón, flor, rombo o sol) y lo que
  queda suelto (tildes, puntos, palabras separadas) se une con **puentes** cortos; un test
  verifica que la pieza es una sola región.
* **Los huecos de las letras quedan abiertos** (la panza de la a, el ojo de la e, el 8):
  el contorno no los tapa.
* **Colores**: un color; **dos alturas** (letras en relieve arriba de la base: en cualquier
  impresora, pausa y cambio de filamento a mano en esa capa, que el reporte indica); o
  **misma altura** (letras al ras, de color en las últimas capas, para AMS / multicolor).
  El 3MF trae base y letras como partes de un objeto para asignar un filamento a cada una.
* **Más de un punto de apoyo**: las líneas se apilan por su perfil (se tocan donde se
  cruzan las letras) y cada una se apoya en la de abajo en al menos dos lugares (si no se
  tocan, un pilar corto en la columna de menos luz); las piezas sueltas grandes se unen
  con dos puentes.
* 1 o 2 **palitos** con punta que bajan `largo` mm por debajo de lo más bajo de la pieza
  (en un corazón se clavan cerca de la punta) y se clavan en material macizo.
* **Años**: el número que cumple (1 a 3 cifras) en cualquier tipografía, solo o con
  estrellas, corazones, corona o "años" abajo; en una pieza aparte, con sus palitos y los
  mismos colores. El 3MF trae el topper y el número uno al lado del otro.
* Vista **en la torta** (`web/torta.js`): crema, chocolate, chocotorta, Oreo, pasta frola,
  rogel, frutillas o selva negra, con texturas dibujadas en el navegador, apoyada en la
  mesa; el topper y el número entran desde arriba y se clavan. O plano, como se imprime.
  **🎉 Cumpleaños**: velitas prendidas, ráfagas y lluvia de confeti que se apoya en la
  torta y la mesa, y la cámara girando. Descarga en 3MF o STL.

### Chapitas para collares

Quinta herramienta: **chapitas con el nombre de tu perro o gato** (`web/chapita.html`,
motor `engine/chapita_core.py`, que reusa la grilla y las tipografías del topper).

* Formas: **hueso, gato, corazón, círculo, óvalo y pescado**, del ancho pedido, con un
  ojal arriba al centro y el agujero para la argolla del collar (la argolla se ve en el visor).
* El **nombre** (hasta 14 letras) y una **segunda línea** opcional (teléfono, apellido)
  salen lo más grandes que entran sin pisar el borde, el ojal ni las patitas; si la letra
  queda de menos de 4 mm, se avisa.
* Letras **en relieve** (con borde y patitas en el hueso y el óvalo) o **grabadas**.
* Colores: uno; **dos** (las letras arriba, cambio de filamento a mano en la altura que
  indica el reporte); o **al ras para AMS**. Descarga en 3MF (una pieza con sus partes) o STL.
* **Llavero en el visor** (`web/llavero.js`): argolla partida, cadenita y ganchito. Puesto, la
  chapita cuelga y se hamaca; "Sacar la argolla" anima todo hasta quedar en la mesa con el
  ganchito abierto, y "Poner la argolla" lo vuelve a colgar.

En todas las herramientas la vista 3D se mira **desde todos los ángulos**: la cámara gira
libre (también por debajo; la mesa y el escenario se esconden para ver la base) y hay
botones Frente, Atrás, Izq., Der., Arriba, Abajo, 3/4 y 360°.

## Cómo funciona

```
engine/          motor paramétrico en Python puro (el mismo que usa Grasshopper)
                 mate_core.py / mate_web.py: motor del Mate con hueco
                 sopa_core.py / sopa_web.py: motor de la Sopa de letras 3D
                 topper_core.py / topper_web.py: motor del Topper para tortas
                 chapita_core.py / chapita_web.py: motor de las Chapitas para collares
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
