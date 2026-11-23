# -*- coding: utf-8 -*-
# © 2026 TecnoBear — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
Cotizador: cuánto material lleva lo que se descarga
===================================================
Cada generador arma exactamente las mismas piezas que van al 3MF (calidad normal) y
acá se mide cada malla: volumen y superficie. Con eso la web estima los gramos como un
laminador (paredes y tapas macizas + el relleno elegido del interior) y el costo con el
precio del kilo que puso la persona. La cuenta de gramos está en web/cotizador.js para
que cambiar material, relleno o precio sea instantáneo.
"""
import math


def medir(V, F):
    """(volumen mm³, superficie mm², superficie que mira arriba, superficie que mira abajo).
    El laminador hace macizos los techos y pisos con capas (5 arriba y 3 abajo) y las
    paredes con perímetros: por eso se separa la superficie por hacia dónde mira."""
    vol = 0.0
    area = 0.0
    arriba = 0.0
    abajo = 0.0
    for a, b, c in F:
        ax, ay, az = V[a]
        bx, by, bz = V[b]
        cx, cy, cz = V[c]
        vol += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx))
        ux, uy, uz = bx - ax, by - ay, bz - az
        wx, wy, wz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        area += n
        if n > 0:
            c = nz / n                      # coseno con la vertical (el tamaño de la normal es 2·área)
            if c > 0.5:
                arriba += n * c
            elif c < -0.5:
                abajo += -n * c
    if vol < 0:                             # malla con las caras al revés: se invierte arriba/abajo
        arriba, abajo = abajo, arriba
    return abs(vol) / 6.0, area / 2.0, arriba / 2.0, abajo / 2.0


def pieza(nombre, V, F, cantidad=1, color=1, grupo=None):
    vol, area, arriba, abajo = medir(V, F)
    return {"nombre": nombre, "grupo": grupo or nombre, "cantidad": int(cantidad), "color": int(color),
            "volumen_mm3": round(vol, 1), "area_mm2": round(area, 1),
            "arriba_mm2": round(arriba, 1), "abajo_mm2": round(abajo, 1)}


def resultado(piezas, sku, notas=()):
    return {"sku": sku, "piezas": piezas, "notas": list(notas),
            "colores": max([p["color"] for p in piezas] or [1])}
