"""Ejecuta una revolución de la primera etapa geométrica/cinemática."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from cinematica import mascaras_rodillos, rotar
from config import CSV_AGUJEROS, DIRECTORIO_RESULTADOS, DXF_MATRIZ, PARAMETROS
from geometria import (
    cargar_agujeros_csv,
    cargar_agujeros_dxf,
    generar_geometria_provisional,
    guardar_agujeros_csv,
    validar_geometria,
)
from visualizacion import guardar_animacion, guardar_figura_estatica, guardar_grafico_actividad


def obtener_geometria(modo: str = "auto") -> tuple[np.ndarray, str]:
    """Prioridad auto: CSV real, DXF real y, por último, respaldo provisional."""
    if modo in ("auto", "csv") and CSV_AGUJEROS.exists():
        return cargar_agujeros_csv(CSV_AGUJEROS), "CSV extraído del DXF"
    if modo in ("auto", "dxf") and DXF_MATRIZ.exists():
        coordenadas = cargar_agujeros_dxf(DXF_MATRIZ, PARAMETROS.numero_agujeros)
        guardar_agujeros_csv(coordenadas, CSV_AGUJEROS, "cara_matriz.dxf")
        return coordenadas, "DXF suministrado"
    if modo in ("auto", "provisional"):
        return generar_geometria_provisional(PARAMETROS), "geometría provisional"
    raise FileNotFoundError(f"No está disponible la fuente geométrica solicitada: {modo}")


def simular_revolucion(coordenadas_iniciales_m: np.ndarray) -> pd.DataFrame:
    tiempos = np.linspace(
        0.0,
        PARAMETROS.periodo_revolucion_s,
        PARAMETROS.pasos_por_revolucion + 1,
    )
    filas = []
    for tiempo in tiempos:
        angulo = PARAMETROS.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        m1, m2 = mascaras_rodillos(coordenadas, PARAMETROS)
        filas.append(
            {
                "tiempo_s": tiempo,
                "angulo_rad": angulo,
                "angulo_grados": np.degrees(angulo),
                "activos_rodillo_1": int(m1.sum()),
                "activos_rodillo_2": int(m2.sum()),
                "activos_total": int(m1.sum() + m2.sum()),
            }
        )
    return pd.DataFrame(filas)


def resumen_actividad(resultados: pd.DataFrame) -> pd.DataFrame:
    # Se excluye el punto final duplicado (360° = 0°) de las estadísticas.
    muestra = resultados.iloc[:-1]
    filas = []
    for etiqueta, columna in (
        ("Rodillo 1", "activos_rodillo_1"),
        ("Rodillo 2", "activos_rodillo_2"),
        ("Total", "activos_total"),
    ):
        filas.append(
            {
                "componente": etiqueta,
                "minimo": int(muestra[columna].min()),
                "maximo": int(muestra[columna].max()),
                "promedio": float(muestra[columna].mean()),
            }
        )
    return pd.DataFrame(filas)


def ejecutar(modo: str, crear_gif: bool = True) -> None:
    coordenadas, fuente = obtener_geometria(modo)
    metricas = validar_geometria(coordenadas, PARAMETROS)
    resultados = simular_revolucion(coordenadas)
    resumen = resumen_actividad(resultados)

    DIRECTORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(DIRECTORIO_RESULTADOS / "actividad_una_revolucion.csv", index=False)
    resumen.to_csv(DIRECTORIO_RESULTADOS / "resumen_actividad.csv", index=False)
    guardar_grafico_actividad(resultados, DIRECTORIO_RESULTADOS / "actividad_vs_tiempo.png")
    guardar_figura_estatica(
        coordenadas,
        np.deg2rad(30.0),
        PARAMETROS,
        DIRECTORIO_RESULTADOS / "instante_30_grados.png",
    )
    if crear_gif:
        guardar_animacion(
            coordenadas,
            resultados["tiempo_s"].to_numpy(),
            PARAMETROS,
            DIRECTORIO_RESULTADOS / "animacion_matriz.gif",
        )

    print(f"Fuente geométrica: {fuente}")
    print(f"Período: {PARAMETROS.periodo_revolucion_s:.6f} s")
    print(f"Longitud de contacto aproximada: {PARAMETROS.longitud_contacto_m * 1_000:.3f} mm")
    print(
        "Radios de centros: "
        f"{metricas['radio_minimo_m'] * 1_000:.3f} a "
        f"{metricas['radio_maximo_m'] * 1_000:.3f} mm"
    )
    print(resumen.to_string(index=False, float_format=lambda valor: f"{valor:.3f}"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometria",
        choices=("auto", "csv", "dxf", "provisional"),
        default="auto",
        help="Fuente de centros; auto prioriza CSV y DXF reales.",
    )
    parser.add_argument("--sin-gif", action="store_true", help="Omite la animación para una ejecución rápida.")
    argumentos = parser.parse_args()
    ejecutar(argumentos.geometria, crear_gif=not argumentos.sin_gif)


if __name__ == "__main__":
    main()
