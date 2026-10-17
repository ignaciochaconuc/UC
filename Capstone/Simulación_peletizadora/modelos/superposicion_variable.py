"""Intersección disco-huella con longitud tangencial variable radialmente."""

from __future__ import annotations

import math
import numpy as np

from .superposicion import _gauss_legendre


def longitud_contacto_desde_holgura(
    holgura_m: np.ndarray | float, diametro_rodillo_m: float, espesor_biomasa_m: float
) -> np.ndarray:
    """Longitud de contacto geométrica; g<0 es una incompatibilidad explícita."""
    g = np.asarray(holgura_m, dtype=float)
    if np.any(g < 0):
        raise ValueError("Holgura negativa: incompatibilidad geométrica del modelo desacoplado")
    profundidad = np.maximum(espesor_biomasa_m-g, 0.0)
    if np.any(profundidad > diametro_rodillo_m):
        raise ValueError("Profundidad efectiva fuera del límite geométrico circular")
    return np.sqrt(np.maximum(diametro_rodillo_m*profundidad-profundidad**2, 0.0))


def interseccion_disco_huella_variable(
    centros_locales_m: np.ndarray,
    radio_agujero_m: float,
    limites_radiales_m: tuple[float, float],
    holgura_centro_m: float,
    pendiente_holgura_radial: float,
    radio_centro_rodillo_m: float,
    diametro_rodillo_m: float,
    espesor_biomasa_m: float,
    orden: int = 64,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Área y centroide de discos contra una huella de semiancho Lc(g(r))/2."""
    centros = np.asarray(centros_locales_m, dtype=float)
    if centros.ndim != 2 or centros.shape[1] != 2:
        raise ValueError("Los centros deben tener forma (n,2)")
    rmin, rmax = limites_radiales_m
    # La holgura lineal extrema ocurre en uno de los bordes radiales.
    g_bordes = holgura_centro_m + pendiente_holgura_radial*(np.array([rmin, rmax])-radio_centro_rodillo_m)
    if np.min(g_bordes) < 0:
        raise ValueError("El perfil de holgura contiene valores negativos")
    x0, y0 = centros[:, 0], centros[:, 1]
    a = np.maximum(rmin, x0-radio_agujero_m)
    b = np.minimum(rmax, x0+radio_agujero_m)
    validos = b > a
    areas = np.zeros(len(centros)); cx = np.full(len(centros), np.nan); cy = np.full(len(centros), np.nan)
    if not np.any(validos):
        return areas, cx, cy
    indices = np.flatnonzero(validos); av = a[indices]; bv = b[indices]
    nodos, pesos = _gauss_legendre(orden)
    mitad = (bv-av)/2; medio = (av+bv)/2
    x = medio[:, None] + mitad[:, None]*nodos
    semi_disco = np.sqrt(np.maximum(radio_agujero_m**2-(x-x0[indices, None])**2, 0.0))
    g = holgura_centro_m + pendiente_holgura_radial*(x-radio_centro_rodillo_m)
    lc = longitud_contacto_desde_holgura(g, diametro_rodillo_m, espesor_biomasa_m)
    inferior = np.maximum(y0[indices, None]-semi_disco, -lc/2)
    superior = np.minimum(y0[indices, None]+semi_disco, lc/2)
    altura = np.maximum(superior-inferior, 0.0)
    factor = mitad[:, None]*pesos
    area = np.sum(factor*altura, axis=1)
    mx = np.sum(factor*x*altura, axis=1)
    my = np.sum(factor*.5*(superior**2-inferior**2), axis=1)
    area_disco = math.pi*radio_agujero_m**2
    area = np.clip(area, 0, area_disco); positivos = area > np.finfo(float).eps*area_disco
    areas[indices] = area
    cx[indices[positivos]] = mx[positivos]/area[positivos]
    cy[indices[positivos]] = my[positivos]/area[positivos]
    return areas, cx, cy
