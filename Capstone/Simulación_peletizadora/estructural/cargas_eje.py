"""Importación y transformación de las cargas de las Etapas 2B y 2C."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config import PARAMETROS, RAIZ_PROYECTO
from .config_eje import ConfiguracionEje


RUTA_CARGAS_2C = RAIZ_PROYECTO / "resultados" / "etapa_2c" / "cargas_area_superposicion.csv"
RUTA_CARGAS_CONSTANTES = RAIZ_PROYECTO / "resultados" / "etapa_2b" / "cargas_constante.csv"
RUTA_INDIVIDUALES_CONSTANTES = (
    RAIZ_PROYECTO / "resultados" / "etapa_2b" / "agujeros_activos_constante.csv.gz"
)


@dataclass(frozen=True)
class RepartoRodillo:
    fuerza_n: np.ndarray
    posicion_resultante_m: np.ndarray
    reaccion_a_n: np.ndarray
    reaccion_b_n: np.ndarray
    fuera_entre_rodamientos: np.ndarray


def repartir_entre_rodamientos(
    fuerza_n: np.ndarray | float,
    x_f_m: np.ndarray | float,
    x_a_m: float,
    x_b_m: float,
) -> RepartoRodillo:
    fuerza = np.asarray(fuerza_n, dtype=float)
    x_f = np.asarray(x_f_m, dtype=float)
    reaccion_a = fuerza * (x_b_m - x_f) / (x_b_m - x_a_m)
    reaccion_b = fuerza * (x_f - x_a_m) / (x_b_m - x_a_m)
    fuera = (x_f < x_a_m) | (x_f > x_b_m)
    return RepartoRodillo(fuerza, x_f, reaccion_a, reaccion_b, fuera)


def cargar_serie_2c(config: ConfiguracionEje) -> pd.DataFrame:
    datos = pd.read_csv(RUTA_CARGAS_2C).iloc[: PARAMETROS.pasos_por_revolucion].copy()
    requeridas = {
        "tiempo_s",
        "angulo_grados",
        "fuerza_rodillo_1_n",
        "fuerza_rodillo_2_n",
        "resultante_centroide_radial_r1_m",
        "resultante_centroide_radial_r2_m",
    }
    faltantes = requeridas - set(datos.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en las cargas 2C: {sorted(faltantes)}")
    # Convención solicitada en 3A: R1 se refleja al lado izquierdo y R2 al derecho.
    datos["x_resultante_rodillo_1_m"] = (
        config.centro_matriz_m - datos["resultante_centroide_radial_r1_m"]
    )
    datos["x_resultante_rodillo_2_m"] = (
        config.centro_matriz_m + datos["resultante_centroide_radial_r2_m"]
    )
    return datos


def tabla_fuerzas_rodamientos(datos: pd.DataFrame, config: ConfiguracionEje) -> pd.DataFrame:
    izquierda = repartir_entre_rodamientos(
        datos["fuerza_rodillo_1_n"].to_numpy(),
        datos["x_resultante_rodillo_1_m"].to_numpy(),
        *config.rodamientos_izquierdos_m,
    )
    derecha = repartir_entre_rodamientos(
        datos["fuerza_rodillo_2_n"].to_numpy(),
        datos["x_resultante_rodillo_2_m"].to_numpy(),
        *config.rodamientos_derechos_m,
    )
    salida = datos[
        [
            "tiempo_s",
            "angulo_grados",
            "fuerza_rodillo_1_n",
            "fuerza_rodillo_2_n",
            "x_resultante_rodillo_1_m",
            "x_resultante_rodillo_2_m",
        ]
    ].copy()
    salida["compactacion_r1_rodamiento_a_n"] = izquierda.reaccion_a_n
    salida["compactacion_r1_rodamiento_b_n"] = izquierda.reaccion_b_n
    salida["compactacion_r2_rodamiento_a_n"] = derecha.reaccion_a_n
    salida["compactacion_r2_rodamiento_b_n"] = derecha.reaccion_b_n
    salida["resultante_r1_fuera_rodamientos"] = izquierda.fuera_entre_rodamientos
    salida["resultante_r2_fuera_rodamientos"] = derecha.fuera_entre_rodamientos

    mu = PARAMETROS.coeficiente_resistencia_tangencial
    # Convención horizontal: izquierda +, derecha -, coherente con tangentes
    # opuestas de una matriz que gira antihorariamente.
    salida["tangencial_r1_rodamiento_a_n"] = mu * izquierda.reaccion_a_n
    salida["tangencial_r1_rodamiento_b_n"] = mu * izquierda.reaccion_b_n
    salida["tangencial_r2_rodamiento_a_n"] = -mu * derecha.reaccion_a_n
    salida["tangencial_r2_rodamiento_b_n"] = -mu * derecha.reaccion_b_n
    return salida


def cargas_peso_rodillos(config: ConfiguracionEje) -> dict[float, float]:
    peso = config.masa_rodillo_kg * config.gravedad_m_s2
    resultado: dict[float, float] = {}
    for centro, rodamientos in (
        (config.centro_rodillo_izquierdo_m, config.rodamientos_izquierdos_m),
        (config.centro_rodillo_derecho_m, config.rodamientos_derechos_m),
    ):
        reparto = repartir_entre_rodamientos(-peso, centro, *rodamientos)
        resultado[rodamientos[0]] = float(reparto.reaccion_a_n)
        resultado[rodamientos[1]] = float(reparto.reaccion_b_n)
    return resultado


def caso_constante_conservador(config: ConfiguracionEje) -> dict[str, float]:
    agregados = pd.read_csv(RUTA_CARGAS_CONSTANTES).iloc[: PARAMETROS.pasos_por_revolucion]
    individuales = pd.read_csv(RUTA_INDIVIDUALES_CONSTANTES)
    salida: dict[str, float] = {}
    for numero in (1, 2):
        columna = f"fuerza_rodillo_{numero}_n"
        paso = int(agregados[columna].idxmax())
        fuerza = float(agregados.loc[paso, columna])
        activas = individuales[
            (individuales["paso"] == paso)
            & (individuales["rodillo_activo"] == numero)
        ]
        radio = float(
            np.average(activas["radio_m"], weights=activas["fuerza_axial_n"])
        )
        salida[f"fuerza_rodillo_{numero}_n"] = fuerza
        salida[f"radio_resultante_rodillo_{numero}_m"] = radio
        salida[f"paso_maximo_rodillo_{numero}"] = paso
    salida["x_resultante_rodillo_1_m"] = (
        config.centro_matriz_m - salida["radio_resultante_rodillo_1_m"]
    )
    salida["x_resultante_rodillo_2_m"] = (
        config.centro_matriz_m + salida["radio_resultante_rodillo_2_m"]
    )
    return salida


def validar_conservacion_reparto(tabla: pd.DataFrame, tolerancia: float = 1e-9) -> None:
    for numero in (1, 2):
        suma = (
            tabla[f"compactacion_r{numero}_rodamiento_a_n"]
            + tabla[f"compactacion_r{numero}_rodamiento_b_n"]
        )
        error = np.max(np.abs(suma - tabla[f"fuerza_rodillo_{numero}_n"]))
        escala = max(float(tabla[f"fuerza_rodillo_{numero}_n"].abs().max()), 1.0)
        if error / escala > tolerancia:
            raise ValueError(f"El reparto del rodillo {numero} no conserva la fuerza")
