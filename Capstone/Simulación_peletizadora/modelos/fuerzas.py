"""Conversión de presión de extrusión a fuerza axial equivalente."""

from __future__ import annotations

import math
import numpy as np


def area_perforacion_m2(diametro_m: float) -> float:
    return math.pi * diametro_m**2 / 4.0


def fuerzas_axiales_n(presiones_pa: np.ndarray, diametro_m: float) -> np.ndarray:
    return np.asarray(presiones_pa) * area_perforacion_m2(diametro_m)
