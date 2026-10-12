"""Rotación rígida e identificación geométrica de agujeros activos."""

from __future__ import annotations

import math
import numpy as np

from config import Parametros


def rotar(coordenadas_iniciales_m: np.ndarray, angulo_rad: float) -> np.ndarray:
    """Aplica una rotación antihoraria alrededor del origen."""
    c, s = math.cos(angulo_rad), math.sin(angulo_rad)
    matriz = np.array([[c, -s], [s, c]])
    return coordenadas_iniciales_m @ matriz.T


def mascara_contacto(
    coordenadas_m: np.ndarray, angulo_rodillo_rad: float, parametros: Parametros
) -> np.ndarray:
    """Prueba pertenencia a la huella rectangular aproximada de un rodillo."""
    radial = np.array([math.cos(angulo_rodillo_rad), math.sin(angulo_rodillo_rad)])
    tangencial = np.array([-radial[1], radial[0]])
    coordenada_radial = coordenadas_m @ radial
    coordenada_tangencial = coordenadas_m @ tangencial
    r_min, r_max = parametros.limite_radial_rodillo_m
    semi_contacto = parametros.longitud_contacto_m / 2.0
    return (
        (coordenada_radial >= r_min)
        & (coordenada_radial <= r_max)
        & (np.abs(coordenada_tangencial) <= semi_contacto)
    )


def mascaras_rodillos(
    coordenadas_m: np.ndarray, parametros: Parametros
) -> tuple[np.ndarray, np.ndarray]:
    """Retorna las máscaras para dos rodillos diametralmente opuestos."""
    return (
        mascara_contacto(coordenadas_m, 0.0, parametros),
        mascara_contacto(coordenadas_m, math.pi, parametros),
    )
