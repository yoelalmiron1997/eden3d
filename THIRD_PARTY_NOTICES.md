# Componentes de terceros

La página web incluye (en `vendor/`, copiados durante el build) bibliotecas de
terceros que **no** forman parte de la Obra de Eden3D y se distribuyen bajo sus
propias licencias:

| Componente | Versión | Licencia | Fuente |
|---|---|---|---|
| Pyodide (Python en WebAssembly) | 0.27.7 | Mozilla Public License 2.0 | https://github.com/pyodide/pyodide |
| three.js (visor 3D), OrbitControls, RoomEnvironment y GroundedSkybox | 0.170.0 | MIT | https://github.com/mrdoob/three.js |
| jsPDF (guía de uso en PDF) | 4.2.1 | MIT | https://github.com/parallax/jsPDF |
| Foto 360° "Chinese Garden" (escenario Jardín, `assets/escenarios/jardin_chino.jpg`) | 2k | CC0 1.0 (dominio público) | Poly Haven — https://polyhaven.com/a/chinese_garden |

Para los tests y la integración continua se usan, sin distribuirse con la web:
pytest (MIT), Playwright (Apache 2.0), trimesh (MIT), manifold3d (Apache 2.0),
NumPy (BSD), Pillow (MIT-CMU), PyYAML (MIT) y Rtree (MIT).

Los textos completos de las licencias de Pyodide, three.js y jsPDF se copian junto a
cada biblioteca en `vendor/` al construir la página.
