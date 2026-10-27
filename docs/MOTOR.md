# Edén3D — Motor paramétrico de macetas · v0.4

Herramienta propia para generar, validar y exportar colecciones de macetas FDM.
Primer generador validado: **familia de revolución deformada** (Wave, Spiral/Twist,
Origami facetada, Elegance, Tulip de borde ondulado).

## Contenido

| Archivo | Para qué |
|---|---|
| `eden_core.py` | Motor (Python puro, sin dependencias). Forma base → deformación → pared/fondo/drenaje/borde → validación → STL/3MF/JSON. Corre igual en Rhino 8 y en Python normal. |
| `eden_surface.py` | Piel visible: low poly (facetas planas exactas) y texturas (soga, tejido, piedra, burbujas). |
| `eden_floor.py` | Fondo con patrones de drenaje (círculos, ranuras, hojas, grilla) y triangulación con agujeros. |
| `eden_validate.py` | Validación externa con trimesh: cerrada, orientada, topología, **espesor real medido**. |
| `eden_batch.py` | Colecciones: variantes, barridos de parámetros, tamaños comerciales, plato, exportación STL/3MF/3DM/JSON y `collection_report.csv`. |
| `eden_preview.py` | Hoja de contacto PNG sin abrir Rhino. |
| `grasshopper/gh_eden_pot.py` | Componente "Python 3 Script" para Grasshopper (sliders en vivo + botón exportar). |
| `colecciones/eden_wave_v1.json` | Colección de validación (5 variantes + 1 inválida a propósito). |
| `out/` | Archivos reales generados y validados de esa colección. |

## Instalación (Windows)

1. Copiá la carpeta a, por ejemplo, `C:\Eden3D\motor`.
2. **Grasshopper**: seguí el encabezado de `grasshopper/gh_eden_pot.py`
   (crear 13 entradas y 4 salidas, `lib_path = C:\Eden3D\motor`).
3. **Lotes sin Rhino** (opcional, recomendado para producción):
   ```
   pip install trimesh scipy rhino3dm matplotlib
   python eden_batch.py colecciones\eden_wave_v1.json out
   python eden_preview.py colecciones\eden_wave_v1.json out\preview.png
   ```

## Parámetros principales (mm)

- **Forma**: `height`, `d_base`, `d_max`, `d_mouth`, `belly` (0–1, altura del vientre),
  `polygon_sides`, `polygon_blend`, `polygon_round`, `polygon_twist`.
- **Ondas** (`waves`, lista combinable = interferencia):
  - `radial`: `count`, `amp`, `phase`, `twist` (vueltas), `twist_power` (torsión progresiva),
    `sharp` (1 seno, >1 crestas finas, <1 onda cuadrada suave), `amp_top`/`amp_power` (relieve progresivo).
  - `vertical`: `count` (anillos), `amp`, `n_theta` (>0 = patrón ajedrezado).
  - `asym`, `asym_angle`, `fade_bottom`, `fade_top`.
- **Físico**: `wall`, `floor`, `rim` (`round`/`flat`), `chamfer`, `drain_d`.
- **Calidad**: `quality` = `preview` (diseño en vivo) · `normal` (exportar) · `fine`.

## Validaciones

Errores (descartan la variante): pared/fondo bajo mínimo FDM, amplitud excesiva,
drenaje demasiado grande, **cresta convexa con radio < 1,25 × pared** (la pared
interior se plegaría), anillo interior autointersectado; en lote además falla si
la malla no es cerrada/orientada o si el espesor medido cae bajo 90 % (p5) o 75 % (mín.).
Avisos: voladizo > 50°, base angosta, boca cerrada, pared no múltiplo de 0,4, sin drenaje.

**Un STL válido no garantiza la impresión**: laminá siempre la primera pieza de cada familia.

## Novedades v0.2 (tendencias de MakerWorld / Etsy / Mercado Libre)

| Diseño | Parámetros | Notas |
|---|---|---|
| **Japandi acanalado** | `wave_profile`: `rib` (nervaduras convexas) o `flute` (canales); `wave_duty`; usar `rim: flat` | Con nervaduras finas subí `fade_bottom/fade_top` a 10–12 mm. |
| **Low poly** | `lowpoly_cols`, `lowpoly_rows`, `lowpoly_stagger`, `lowpoly_jitter`, `lowpoly_seed` | Facetas planas exactas; pared interior facetada (espesor parejo). |
| **Texturas** | `tex_type`: `rope`, `knit`, `stone`, `bubbles`; `tex_amp`, `tex_count`, `tex_pitch`, `tex_scale`, `tex_seed` | Relieve siempre hacia afuera: la pared nunca adelgaza. Suma gramos. |
| **Plato oculto** | `mode: hidden_tray`; `tray_h`, `tray_wall`, `tray_clear`, `tray_reservoir` | El plato continúa la forma; encastre circular a 45° (cualquier giro); depósito de agua. No recomendado con facetas muy grandes (la transición se ve). |
| **Plato enroscable** | `mode: screw_tray`; `thread_pitch` (4), `thread_depth` (1), `thread_clear` (0,5), `thread_turns` (3), `tray_h`, `tray_wall` | Rosca derecha con flancos ≤45° (imprime parado, sin soportes). Arriba de la rosca el plato sigue la forma exterior; tope cónico en el borde. En macetas chicas reduce las vueltas sola (mín. 1,75). |
| **Autorriego** | `mode: self_watering`; `sw_reservoir`, `sw_gap`, `sw_wick_d` | Cubremaceta-depósito + inserto con labio que apoya en el borde, agujero de mecha (12 mm) y drenaje. Regar desde arriba: el excedente baja al depósito. |

En Grasshopper cualquier parámetro se usa creando una entrada con su mismo nombre.
La salida `plate` muestra el plato oculto o el inserto ya armado; al exportar, cada pieza sale
apoyada en z=0, lista para el laminador.

Colección de ejemplo: `colecciones/eden_tendencias_v2.json` (8 diseños validados).

## Exportar desde Grasshopper
Creá la entrada `export` y conectale un **Button**. Al apretarlo se exporta en calidad normal (aunque estés en vista previa) a `MACETAS_EDEN3D/exportadas/<modelo>/` (o a `out_dir` si lo conectás): maceta y plato en STL + 3MF y el JSON de parámetros.

## Exportar MUCHOS modelos de una vez (modo colección)
1. En el componente agregá una entrada `collection` y conectale un Panel con la ruta a un .json de colección
   (p. ej. `...\eden3d\colecciones\eden_tendencias_v2.json`).
2. (Opcional) entrada `index` + slider entero 0..N-1 para ver cada modelo de la lista.
3. Apretá el Button de `export`: exporta **todos** los modelos válidos (maceta + plato/inserto, STL + 3MF + JSON)
   a `MACETAS_EDEN3D/exportadas/<modelo>/` y lista en `report` cuáles salieron OK y cuáles se descartaron.
   Grasshopper queda ocupado unos segundos por modelo.

Con colección conectada, los sliders de forma no se aplican (lo que ves es lo que se exporta).
Para nuevos modelos copiá el .json y agregá entradas en `"variants"` (cada una con su `model_id`);
`"export": {"sizes": ["S","M","L"]}` genera además cada tamaño comercial.


## v0.3 — Eden3D Studio (Grasshopper con listas y botones)
Componente nuevo: `grasshopper/gh_eden_studio.py`. Entradas: `lib_path`, `diseno`, `modo`,
`drenaje`, `tamano`, `vista`, `quality`, `exportar`, `exportar_todo`. Las entradas vacías se
completan solas con su lista desplegable o su botón.

| Lista | Opciones |
|---|---|
| diseno | los diseños de `colecciones/catalogo_eden3d.json` (17: ROMBO, ARCOS, OLAS, ACANALADO, LIANA, JAPANDI, ...) |
| modo | Todos (catálogo) · Autorriego con rosca · Plato inclinado con rosca · Plato apoyado · Sin plato · Plato oculto · Plato oculto con rosca · Inserto |
| drenaje | Todos (catálogo) · Hojas · Circular · Ranuras · Sin drenaje |
| tamano | M (original) · Mini · S · L · XL · Todos |
| vista | Armado · Despiece · Corte · Base (marca) · Galería |

**exportar** = el diseño elegido en todas las versiones elegidas. **exportar_todo** = todo el catálogo.
"Todos (catálogo)" usa la matriz `export` del catálogo (por defecto Autorriego con rosca + Plato
apoyado × Hojas + Circular × M).

### Nomenclatura y archivos
`Eden3D-<DISEÑO>-<TAMAÑO>-<MODO>-<DRENAJE>` → `exportadas/Eden3D-<DISEÑO>/`
- `<SKU>.3mf`: todas las piezas del set en un archivo (maceta + plato), con metadatos Eden3D.
- `<SKU>.json`: parámetros y reporte (reproduce el modelo exacto).
- `exportadas/Eden3D_indice.csv`: una fila por SKU (gramos, ml de tierra y de agua, medidas).
- STL sueltos por pieza: poner `"stl": true` en `export` del catálogo.

### Marca
Cada pieza lleva **Eden3D** grabado 0,6 mm en la cara de apoyo (se lee mirando la base desde abajo).
Si el drenaje ocupa el centro, la marca se curva junto al borde; se achica sola hasta 3,5 mm.
Parámetros: `brand` ("" = sin marca), `brand_size`, `brand_depth`.

### Patrones nuevos (`tex_type`)
`lattice` (rombos), `arches` (arcos), `wavy_v` (costillas onduladas verticales), `wavy_h`
(olas horizontales, flanco inferior suave). Controles: `tex_count`, `tex_pitch`, `tex_amp`,
`tex_duty` (ancho de costilla), `tex_wob` (ondulación).

### Plato inclinado con rosca / Autorriego con rosca (`screw_dish`, `screw_dish_sw`)
Cuenco con borde cortado en plano inclinado (`dish_tilt`, 12°) y perno central con rosca macho;
la maceta (diseño intacto) lleva una campana central con rosca hembra y techo a 45°. La punta del
perno apoya en el techo (asiento autocentrante). Imprime sin soportes (voladizos ≤ 45°).

**v0.4 — riego por abajo.** La base de la maceta queda a 1,6 mm del piso del plato
(`dish_reservoir`, 2 mm menos 0,4 de asiento): el agua pasa por debajo, entra por los agujeros de
drenaje y moja la tierra por capilaridad. El borde bajo del plato deja `dish_water` mm de agua
sobre la base (auto: 12 mm o 14 % de la altura), o sea ~11–14 mm de tierra en remojo con el plato
lleno. La rosca tiene `dish_turns` = 4 vueltas (16 mm de enganche; baja sola si la maceta es muy
petisa). El reporte dice cuántos ml hacen falta para mojar la tierra y cuántos entran con el plato
lleno; la salida `agua` de Grasshopper dibuja el agua en azul y `tools/corte_agua.py` hace el corte.

### Tests
* En Grasshopper: botón `tests` (autotest del diseño elegido, S y M).
* Fuera de Rhino: `python eden_selftest.py` (los 17 diseños) y `python -m pytest -q tests`
  (booleanas exactas: el agua entra por los drenajes, maceta y plato no se tocan, sólidos
  cerrados, exportación 3MF, fondos y tiempos). Requiere `pip install pytest trimesh manifold3d rtree`.

### Fondos del render
`renders/fondos/naturaleza`: bosque con mesa de madera, hojas con bokeh, musgo oscuro (generados con
`tools/make_backgrounds_nature.py`, sin fotos de terceros). Tus fotos van en
`renders/fondos/propias` (JPG/PNG, cualquier tamaño): se recortan a 4:5 y se desenfocan solas.
