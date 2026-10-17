"""Casos de carga y posproceso estructural del eje transversal."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from config import PARAMETROS
from .cargas_eje import (
    cargas_peso_rodillos,
    caso_constante_conservador,
    repartir_entre_rodamientos,
)
from .config_eje import ConfiguracionEje
from .viga_eb import SistemaViga, SolucionViga


@dataclass
class ResultadoCaso:
    nombre: str
    tiempos_s: np.ndarray
    angulos_grados: np.ndarray
    solucion_vertical: SolucionViga
    solucion_horizontal: SolucionViga
    cargas_distribuidas_verticales: np.ndarray
    fuerzas_extremo_verticales: np.ndarray
    fuerzas_extremo_horizontales: np.ndarray
    posiciones_extremos_m: np.ndarray
    momento_vertical_nm: np.ndarray
    momento_horizontal_nm: np.ndarray
    momento_resultante_nm: np.ndarray
    esfuerzo_nominal_pa: np.ndarray
    desplazamiento_resultante_m: np.ndarray
    series: pd.DataFrame


def _cargas_base_verticales(
    sistema: SistemaViga, numero_casos: int
) -> tuple[np.ndarray, np.ndarray]:
    cargas = sistema.cargas_vacias(numero_casos)
    distribuidas = sistema.agregar_peso_propio(cargas)
    for x, fuerza in cargas_peso_rodillos(sistema.config).items():
        sistema.agregar_carga_puntual(cargas, x, fuerza)
    return cargas, distribuidas


def _agregar_columnas_rodamientos(
    sistema: SistemaViga,
    cargas: np.ndarray,
    tabla: pd.DataFrame,
    prefijo: str,
) -> None:
    posiciones = (
        *sistema.config.rodamientos_izquierdos_m,
        *sistema.config.rodamientos_derechos_m,
    )
    columnas = (
        f"{prefijo}_r1_rodamiento_a_n",
        f"{prefijo}_r1_rodamiento_b_n",
        f"{prefijo}_r2_rodamiento_a_n",
        f"{prefijo}_r2_rodamiento_b_n",
    )
    for x, columna in zip(posiciones, columnas, strict=True):
        sistema.agregar_carga_puntual(cargas, x, tabla[columna].to_numpy(dtype=float))


def _resultado_caso(
    nombre: str,
    sistema: SistemaViga,
    tiempos_s: np.ndarray,
    angulos_grados: np.ndarray,
    cargas_verticales: np.ndarray,
    distribuidas_verticales: np.ndarray,
    cargas_horizontales: np.ndarray | None = None,
) -> ResultadoCaso:
    if cargas_horizontales is None:
        cargas_horizontales = sistema.cargas_vacias(cargas_verticales.shape[1])
    solucion_v = sistema.resolver(cargas_verticales)
    solucion_h = sistema.resolver(cargas_horizontales)
    extremos_v = sistema.fuerzas_extremo_elementos(
        solucion_v.desplazamientos, distribuidas_verticales
    )
    extremos_h = sistema.fuerzas_extremo_elementos(solucion_h.desplazamientos)

    # Convención de momento interno continua entre extremos del elemento.
    momento_v = np.stack((-extremos_v[:, 1, :], extremos_v[:, 3, :]), axis=1)
    momento_h = np.stack((-extremos_h[:, 1, :], extremos_h[:, 3, :]), axis=1)
    momento_r = np.hypot(momento_v, momento_h)
    esfuerzo = momento_r * sistema.radios[:, None, None] / sistema.inercias[:, None, None]
    posiciones = np.column_stack((sistema.nodos_m[:-1], sistema.nodos_m[1:]))

    v = solucion_v.desplazamientos[0::2, :]
    h = solucion_h.desplazamientos[0::2, :]
    desplazamiento = np.hypot(v, h)
    numero_casos = cargas_verticales.shape[1]
    filas = []
    for j in range(numero_casos):
        indice_m = np.unravel_index(np.argmax(momento_r[:, :, j]), momento_r[:, :, j].shape)
        indice_s = np.unravel_index(np.argmax(esfuerzo[:, :, j]), esfuerzo[:, :, j].shape)
        indice_u = int(np.argmax(desplazamiento[:, j]))
        reacciones_v = solucion_v.reacciones[sistema.restringidos, j]
        reacciones_h = solucion_h.reacciones[sistema.restringidos, j]
        filas.append(
            {
                "caso": nombre,
                "tiempo_s": tiempos_s[j],
                "angulo_grados": angulos_grados[j],
                "momento_max_nm": momento_r[indice_m[0], indice_m[1], j],
                "x_momento_max_m": posiciones[indice_m],
                "esfuerzo_nominal_max_pa": esfuerzo[indice_s[0], indice_s[1], j],
                "x_esfuerzo_max_m": posiciones[indice_s],
                "diametro_en_esfuerzo_max_m": 2 * sistema.radios[indice_s[0]],
                "desplazamiento_max_m": desplazamiento[indice_u, j],
                "x_desplazamiento_max_m": sistema.nodos_m[indice_u],
                "reaccion_vertical_izquierda_n": reacciones_v[0],
                "momento_vertical_izquierdo_nm": reacciones_v[1],
                "reaccion_vertical_derecha_n": reacciones_v[2],
                "momento_vertical_derecho_nm": reacciones_v[3],
                "reaccion_horizontal_izquierda_n": reacciones_h[0],
                "momento_horizontal_izquierdo_nm": reacciones_h[1],
                "reaccion_horizontal_derecha_n": reacciones_h[2],
                "momento_horizontal_derecho_nm": reacciones_h[3],
            }
        )
    return ResultadoCaso(
        nombre,
        tiempos_s,
        angulos_grados,
        solucion_v,
        solucion_h,
        distribuidas_verticales,
        extremos_v,
        extremos_h,
        posiciones,
        momento_v,
        momento_h,
        momento_r,
        esfuerzo,
        desplazamiento,
        pd.DataFrame(filas),
    )


def resolver_casos(
    sistema: SistemaViga,
    tabla_rodamientos: pd.DataFrame,
) -> tuple[dict[str, ResultadoCaso], dict[str, float]]:
    n = len(tabla_rodamientos)
    tiempos = tabla_rodamientos["tiempo_s"].to_numpy()
    angulos = tabla_rodamientos["angulo_grados"].to_numpy()

    # A: pesos solamente.
    cargas_a, dist_a = _cargas_base_verticales(sistema, 1)
    caso_a = _resultado_caso(
        "A_peso_propio", sistema, np.array([0.0]), np.array([0.0]), cargas_a, dist_a
    )

    # B: compactación variable y pesos.
    cargas_b, dist_b = _cargas_base_verticales(sistema, n)
    _agregar_columnas_rodamientos(sistema, cargas_b, tabla_rodamientos, "compactacion")
    caso_b = _resultado_caso(
        "B_compactacion_variable", sistema, tiempos, angulos, cargas_b, dist_b
    )

    # C: B más tangenciales en el plano horizontal.
    cargas_h = sistema.cargas_vacias(n)
    _agregar_columnas_rodamientos(sistema, cargas_h, tabla_rodamientos, "tangencial")
    caso_c = _resultado_caso(
        "C_combinado", sistema, tiempos, angulos, cargas_b, dist_b, cargas_h
    )

    # D: máximos constantes de ambos rodillos impuestos simultáneamente.
    conservador = caso_constante_conservador(sistema.config)
    cargas_d, dist_d = _cargas_base_verticales(sistema, 1)
    cargas_d_h = sistema.cargas_vacias(1)
    for numero, rodamientos in (
        (1, sistema.config.rodamientos_izquierdos_m),
        (2, sistema.config.rodamientos_derechos_m),
    ):
        reparto = repartir_entre_rodamientos(
            conservador[f"fuerza_rodillo_{numero}_n"],
            conservador[f"x_resultante_rodillo_{numero}_m"],
            *rodamientos,
        )
        sistema.agregar_carga_puntual(cargas_d, rodamientos[0], reparto.reaccion_a_n)
        sistema.agregar_carga_puntual(cargas_d, rodamientos[1], reparto.reaccion_b_n)
        signo_tangencial = 1.0 if numero == 1 else -1.0
        mu = PARAMETROS.coeficiente_resistencia_tangencial
        sistema.agregar_carga_puntual(
            cargas_d_h, rodamientos[0], signo_tangencial * mu * reparto.reaccion_a_n
        )
        sistema.agregar_carga_puntual(
            cargas_d_h, rodamientos[1], signo_tangencial * mu * reparto.reaccion_b_n
        )
    caso_d = _resultado_caso(
        "D_constante_conservador", sistema, np.array([math.nan]), np.array([math.nan]),
        cargas_d, dist_d, cargas_d_h
    )

    return {
        "A": caso_a,
        "B": caso_b,
        "C": caso_c,
        "D": caso_d,
    }, conservador


def resolver_instante_combinado(
    sistema: SistemaViga,
    fila_rodamientos: pd.Series,
    nombre: str = "C_instante",
) -> ResultadoCaso:
    """Resuelve un estado C aislado; se usa en convergencia de malla."""
    tabla = fila_rodamientos.to_frame().T
    cargas_v, distribuidas = _cargas_base_verticales(sistema, 1)
    _agregar_columnas_rodamientos(sistema, cargas_v, tabla, "compactacion")
    cargas_h = sistema.cargas_vacias(1)
    _agregar_columnas_rodamientos(sistema, cargas_h, tabla, "tangencial")
    return _resultado_caso(
        nombre,
        sistema,
        np.array([float(fila_rodamientos["tiempo_s"])]),
        np.array([float(fila_rodamientos["angulo_grados"])]),
        cargas_v,
        distribuidas,
        cargas_h,
    )


def equilibrio_global(
    sistema: SistemaViga, solucion: SolucionViga
) -> tuple[np.ndarray, np.ndarray]:
    """Residuos de fuerza y momento de cargas externas más reacciones."""
    x = sistema.nodos_m
    cargas = solucion.cargas
    reacciones = solucion.reacciones
    suma_fuerzas = np.sum(cargas[0::2, :], axis=0) + np.sum(reacciones[0::2, :], axis=0)
    suma_momentos = (
        np.sum(cargas[0::2, :] * x[:, None], axis=0)
        + np.sum(cargas[1::2, :], axis=0)
        + np.sum(reacciones[0::2, :] * x[:, None], axis=0)
        + np.sum(reacciones[1::2, :], axis=0)
    )
    return suma_fuerzas, suma_momentos


def resumen_casos(casos: dict[str, ResultadoCaso], config: ConfiguracionEje) -> pd.DataFrame:
    filas = []
    for clave, caso in casos.items():
        series = caso.series
        indice_esfuerzo = int(series["esfuerzo_nominal_max_pa"].idxmax())
        indice_momento = int(series["momento_max_nm"].idxmax())
        indice_desplazamiento = int(series["desplazamiento_max_m"].idxmax())
        fila_e = series.loc[indice_esfuerzo]
        fila_m = series.loc[indice_momento]
        fila_u = series.loc[indice_desplazamiento]
        fuerzas_reaccion = np.hypot(
            series[["reaccion_vertical_izquierda_n", "reaccion_vertical_derecha_n"]].to_numpy(),
            series[["reaccion_horizontal_izquierda_n", "reaccion_horizontal_derecha_n"]].to_numpy(),
        )
        momentos_reaccion = np.hypot(
            series[["momento_vertical_izquierdo_nm", "momento_vertical_derecho_nm"]].to_numpy(),
            series[["momento_horizontal_izquierdo_nm", "momento_horizontal_derecho_nm"]].to_numpy(),
        )
        filas.append(
            {
                "caso": caso.nombre,
                "momento_max_nm": fila_m["momento_max_nm"],
                "x_momento_max_m": fila_m["x_momento_max_m"],
                "tiempo_momento_max_s": fila_m["tiempo_s"],
                "esfuerzo_nominal_max_pa": fila_e["esfuerzo_nominal_max_pa"],
                "x_esfuerzo_max_m": fila_e["x_esfuerzo_max_m"],
                "tiempo_esfuerzo_max_s": fila_e["tiempo_s"],
                "desplazamiento_max_m": fila_u["desplazamiento_max_m"],
                "x_desplazamiento_max_m": fila_u["x_desplazamiento_max_m"],
                "tiempo_desplazamiento_max_s": fila_u["tiempo_s"],
                "reaccion_fuerza_max_n": float(np.max(np.abs(fuerzas_reaccion))),
                "reaccion_momento_max_nm": float(np.max(np.abs(momentos_reaccion))),
                "factor_seguridad_fluencia": (
                    config.limite_fluencia_pa / fila_e["esfuerzo_nominal_max_pa"]
                    if config.limite_fluencia_pa is not None else math.nan
                ),
            }
        )
    return pd.DataFrame(filas)


def envolventes_caso(caso: ResultadoCaso, sistema: SistemaViga) -> pd.DataFrame:
    filas = []
    for e in range(len(sistema.longitudes)):
        for extremo in (0, 1):
            filas.append(
                {
                    "x_m": caso.posiciones_extremos_m[e, extremo],
                    "elemento": e,
                    "extremo": extremo,
                    "segmento": sistema.nombres_segmentos[e],
                    "diametro_m": 2 * sistema.radios[e],
                    "momento_resultante_envolvente_nm": float(
                        np.max(caso.momento_resultante_nm[e, extremo, :])
                    ),
                    "esfuerzo_nominal_envolvente_pa": float(
                        np.max(caso.esfuerzo_nominal_pa[e, extremo, :])
                    ),
                }
            )
    return pd.DataFrame(filas)
