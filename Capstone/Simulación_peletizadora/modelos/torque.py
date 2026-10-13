"""Modelo resistente simplificado heredado de la Entrega 1."""

from __future__ import annotations

import numpy as np


def contribuciones_torque_nm(
    fuerzas_axiales_n: np.ndarray,
    radios_m: np.ndarray,
    coeficiente_resistencia_tangencial: float,
) -> np.ndarray:
    """Retorna magnitudes resistentes no negativas por perforación."""
    return (
        np.asarray(radios_m)
        * coeficiente_resistencia_tangencial
        * np.asarray(fuerzas_axiales_n)
    )


def potencia_resistente_w(torque_nm: float | np.ndarray, omega_rad_s: float):
    return np.asarray(torque_nm) * omega_rad_s
