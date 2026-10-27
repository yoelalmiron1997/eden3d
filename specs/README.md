# Specs de Eden3D (Spec-Driven Development)

Cada requisito del producto vive acá, con un **ID estable**. Los tests declaran qué
spec verifican y la integración continua arma la **matriz de trazabilidad** que se
publica en la página de calidad (`/calidad/`).

```
specs/*.yml  ──►  tests marcados @pytest.mark.spec("AUT-001")  ──►  reports/*.json
                                   │
                                   ▼
                     tools/spec_matrix.py  ──►  calidad/data.json  +  gate de CI
```

## Cómo se escribe una spec

```yaml
- id: AUT-001                 # PREFIJO-NNN, nunca se reutiliza ni se renumera
  titulo: La maceta queda casi apoyada en el plato
  descripcion: Qué tiene que pasar y por qué importa (en lenguaje de negocio).
  criterio: >                 # criterio de aceptación verificable
    Dado un diseño en modo autorriego, la luz entre la base de la maceta y el piso
    del plato está entre 1 y 2 mm.
  prioridad: alta             # alta | media | baja
  nivel: motor                # motor | web | render | rendimiento
  estado: activa              # activa | pendiente | obsoleta
```

* **activa**: tiene que tener al menos un test y todos sus tests tienen que pasar.
* **pendiente**: requisito acordado que todavía no se implementó; se muestra en la
  matriz pero no rompe el build.
* **obsoleta**: se deja por historia; un test que la siga referenciando avisa.

## Cómo se ata un test a una spec

```python
import pytest

@pytest.mark.spec("AUT-001", "AUT-005")
def test_base_apoyada_y_rosca_larga(...):
    ...
```

Un test puede cubrir varias specs y una spec puede tener varios tests.

## Qué hace fallar el build (gate)

`python tools/spec_matrix.py --strict` falla si:

1. una spec **activa** no tiene ningún test;
2. un test referencia un ID que no existe en `specs/`;
3. algún test de una spec activa falla;
4. hay un test sin `@pytest.mark.spec` (todo lo que se testea tiene que estar pedido).

## Flujo para evolucionar el producto

1. Escribir o cambiar la spec (estado `pendiente`) y abrir el PR.
2. Implementar + escribir el test con el marker.
3. Pasar la spec a `activa`. El CI verifica que esté cubierta y en verde.
4. Al mergear a `main` se publica la web y la página de calidad actualizada.

## Áreas

| Prefijo | Área | Archivo |
|---|---|---|
| AUT | Autorriego con rosca | `autorriego.yml` |
| GEO | Geometría e imprimibilidad | `geometria.yml` |
| EXP | Exportación y nomenclatura | `exportacion.yml` |
| PER | Rendimiento | `rendimiento.yml` |
| REN | Render para Instagram (Rhino) | `render.yml` |
| WEB | Página web | `web.yml` |
| LIC | Licencia y autoría | `licencia.yml` |
| QA | Proceso de calidad (gate y tablero) | `calidad.yml` |
| PLA | Plantas y cuidados | `plantas.yml` |
| VIS | Visor 3D (luz y agua) | `visor.yml` |
