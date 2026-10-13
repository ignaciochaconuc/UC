"""Hipótesis de distribución espacial de presión en la huella activa."""

from __future__ import annotations

import numpy as np


MODELOS_PRESION = ("cuadratico", "senoidal", "constante")


def factor_presion(u: np.ndarray | float, modelo: str) -> np.ndarray:
    """Evalúa el perfil adimensional en valores de ``u`` dentro de [0, 1]."""
    valores = np.asarray(u, dtype=float)
    if modelo == "cuadratico":
        factor = valores**2
    elif modelo == "senoidal":
        factor = np.sin(np.pi * valores)
    elif modelo == "constante":
        factor = np.ones_like(valores)
    else:
        raise ValueError(f"Modelo de presión desconocido: {modelo}")
    return np.clip(factor, 0.0, 1.0)


def calcular_presion_pa(
    u: np.ndarray, activa: np.ndarray, presion_maxima_pa: float, modelo: str
) -> np.ndarray:
    """Calcula presión y la anula estrictamente fuera de la huella."""
    presion = np.zeros_like(np.asarray(u, dtype=float))
    presion[activa] = presion_maxima_pa * factor_presion(u[activa], modelo)
    return presion
