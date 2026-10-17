"""Utilidades de sección y mallado para la viga escalonada."""

from __future__ import annotations

import math
import numpy as np

from .config_eje import ConfiguracionEje, SegmentoEje


def validar_segmentos(segmentos: tuple[SegmentoEje, ...], longitud_m: float) -> None:
    if not segmentos:
        raise ValueError("La geometría del eje está vacía")
    if not math.isclose(segmentos[0].x_inicio_m, 0.0, abs_tol=1e-12):
        raise ValueError("La geometría no comienza en x=0")
    if not math.isclose(segmentos[-1].x_fin_m, longitud_m, abs_tol=1e-12):
        raise ValueError("La geometría no termina en la longitud total")
    for anterior, actual in zip(segmentos, segmentos[1:]):
        if not math.isclose(anterior.x_fin_m, actual.x_inicio_m, abs_tol=1e-12):
            raise ValueError("Los segmentos tienen vacíos o superposiciones")
    for segmento in segmentos:
        if segmento.longitud_m <= 0 or segmento.diametro_exterior_m <= segmento.diametro_interior_m:
            raise ValueError(f"Segmento inválido: {segmento.nombre}")


def segmento_en_x(segmentos: tuple[SegmentoEje, ...], x_m: float) -> SegmentoEje:
    for indice, segmento in enumerate(segmentos):
        ultimo = indice == len(segmentos) - 1
        if segmento.x_inicio_m <= x_m < segmento.x_fin_m or (ultimo and x_m <= segmento.x_fin_m):
            return segmento
    raise ValueError(f"x={x_m} queda fuera de la geometría")


def crear_malla(
    config: ConfiguracionEje,
    posiciones_obligatorias_m: np.ndarray | list[float] | tuple[float, ...],
    longitud_maxima_elemento_m: float | None = None,
) -> np.ndarray:
    """Crea nodos incluyendo cambios de sección, rodamientos y cargas."""
    validar_segmentos(config.segmentos, config.longitud_m)
    hmax = longitud_maxima_elemento_m or config.longitud_maxima_elemento_m
    obligatorias = {
        0.0,
        config.longitud_m,
        *config.rodamientos_izquierdos_m,
        *config.rodamientos_derechos_m,
    }
    for segmento in config.segmentos:
        obligatorias.add(segmento.x_inicio_m)
        obligatorias.add(segmento.x_fin_m)
    for posicion in np.asarray(posiciones_obligatorias_m, dtype=float).ravel():
        if posicion < -1e-12 or posicion > config.longitud_m + 1e-12:
            raise ValueError(f"Posición obligatoria fuera del eje: {posicion}")
        obligatorias.add(float(posicion))
    base = sorted(round(x, 12) for x in obligatorias)
    nodos: list[float] = [base[0]]
    for a, b in zip(base, base[1:]):
        divisiones = max(1, math.ceil((b - a) / hmax))
        nodos.extend(np.linspace(a, b, divisiones + 1)[1:].tolist())
    return np.unique(np.round(nodos, 12))


def propiedades_elementos(
    nodos_m: np.ndarray, segmentos: tuple[SegmentoEje, ...]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    medios = (nodos_m[:-1] + nodos_m[1:]) / 2
    seleccion = [segmento_en_x(segmentos, x) for x in medios]
    areas = np.array([s.area_m2 for s in seleccion])
    inercias = np.array([s.inercia_m4 for s in seleccion])
    radios = np.array([s.radio_exterior_m for s in seleccion])
    nombres = [s.nombre for s in seleccion]
    return areas, inercias, radios, nombres

