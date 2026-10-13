"""Intersección determinista disco-rectángulo y sus centroides.

La integral se reduce a una dimensión: en cada coordenada radial se recorta el
segmento vertical del disco contra los límites tangenciales del rectángulo. Una
cuadratura fija de Gauss–Legendre evita variabilidad estadística y permite integrar
en forma vectorizada muchos agujeros a la vez.
"""

from __future__ import annotations

from functools import lru_cache
import math

import numpy as np


@lru_cache(maxsize=None)
def _gauss_legendre(orden: int) -> tuple[np.ndarray, np.ndarray]:
    if orden < 4:
        raise ValueError("El orden de cuadratura debe ser al menos 4")
    return np.polynomial.legendre.leggauss(orden)


def interseccion_disco_rectangulo(
    centros_locales_m: np.ndarray,
    radio_m: float,
    limites_rectangulo_m: tuple[float, float, float, float],
    orden: int = 64,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retorna área y centroide local de cada intersección.

    Los centros se expresan como columnas radial y tangencial. Para área nula,
    ambas coordenadas del centroide se devuelven como ``NaN``.
    """
    centros = np.asarray(centros_locales_m, dtype=float)
    if centros.ndim != 2 or centros.shape[1] != 2:
        raise ValueError("centros_locales_m debe tener forma (n, 2)")
    if radio_m <= 0:
        raise ValueError("El radio debe ser positivo")
    x_min, x_max, y_min, y_max = limites_rectangulo_m
    if not (x_min < x_max and y_min < y_max):
        raise ValueError("Los límites del rectángulo no son válidos")

    x0, y0 = centros[:, 0], centros[:, 1]
    area_disco = math.pi * radio_m**2
    areas = np.zeros(len(centros))
    centroides_x = np.full(len(centros), np.nan)
    centroides_y = np.full(len(centros), np.nan)

    contenidas = (
        (x0 - radio_m >= x_min)
        & (x0 + radio_m <= x_max)
        & (y0 - radio_m >= y_min)
        & (y0 + radio_m <= y_max)
    )
    areas[contenidas] = area_disco
    centroides_x[contenidas] = x0[contenidas]
    centroides_y[contenidas] = y0[contenidas]

    fuera = (
        (x0 + radio_m <= x_min)
        | (x0 - radio_m >= x_max)
        | (y0 + radio_m <= y_min)
        | (y0 - radio_m >= y_max)
    )
    parciales = ~(contenidas | fuera)
    if not np.any(parciales):
        return areas, centroides_x, centroides_y

    indices = np.flatnonzero(parciales)
    xp, yp = x0[indices], y0[indices]
    a = np.maximum(x_min, xp - radio_m)
    b = np.minimum(x_max, xp + radio_m)
    nodos, pesos = _gauss_legendre(orden)
    mitad = (b - a) / 2.0
    medio = (a + b) / 2.0
    x = medio[:, None] + mitad[:, None] * nodos[None, :]
    semi_altura = np.sqrt(np.maximum(radio_m**2 - (x - xp[:, None]) ** 2, 0.0))
    inferior = np.maximum(yp[:, None] - semi_altura, y_min)
    superior = np.minimum(yp[:, None] + semi_altura, y_max)
    altura = np.maximum(superior - inferior, 0.0)
    factor = mitad[:, None] * pesos[None, :]

    area = np.sum(factor * altura, axis=1)
    momento_x = np.sum(factor * x * altura, axis=1)
    momento_y = np.sum(factor * 0.5 * (superior**2 - inferior**2), axis=1)
    area = np.clip(area, 0.0, area_disco)
    positiva = area > np.finfo(float).eps * area_disco

    areas[indices] = area
    centroides_x[indices[positiva]] = momento_x[positiva] / area[positiva]
    centroides_y[indices[positiva]] = momento_y[positiva] / area[positiva]
    return areas, centroides_x, centroides_y


def fraccion_cobertura(areas_m2: np.ndarray, radio_m: float) -> np.ndarray:
    area_disco = math.pi * radio_m**2
    return np.clip(np.asarray(areas_m2) / area_disco, 0.0, 1.0)


def limites_huella(parametros) -> tuple[float, float, float, float]:
    r_min, r_max = parametros.limite_radial_rodillo_m
    semi_tangencial = parametros.longitud_contacto_m / 2.0
    return r_min, r_max, -semi_tangencial, semi_tangencial


def coordenadas_locales(
    coordenadas_globales_m: np.ndarray, angulo_rodillo_rad: float
) -> np.ndarray:
    """Transforma coordenadas globales a ejes radial/tangencial del rodillo."""
    radial = np.array([math.cos(angulo_rodillo_rad), math.sin(angulo_rodillo_rad)])
    tangencial = np.array([-radial[1], radial[0]])
    return np.column_stack(
        (coordenadas_globales_m @ radial, coordenadas_globales_m @ tangencial)
    )
