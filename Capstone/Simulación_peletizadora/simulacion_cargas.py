"""Etapa 2B: presión, fuerza axial, torque y potencia durante una revolución."""

from __future__ import annotations

import argparse
import math

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from cinematica import estado_contacto, rotar
from config import DIRECTORIO_RESULTADOS_CARGAS, PARAMETROS
from modelos.fuerzas import fuerzas_axiales_n
from modelos.presion import MODELOS_PRESION, calcular_presion_pa
from modelos.torque import contribuciones_torque_nm, potencia_resistente_w
from simulacion import obtener_geometria
from visualizacion_cargas import (
    grafico_fuerzas,
    grafico_perfiles,
    grafico_potencia,
    grafico_resumen,
    grafico_torque,
    guardar_animacion_presion,
)


UNIDADES = {
    "activos_rodillo_1": "agujeros",
    "activos_rodillo_2": "agujeros",
    "activos_total": "agujeros",
    "fuerza_rodillo_1_n": "N",
    "fuerza_rodillo_2_n": "N",
    "fuerza_total_n": "N",
    "torque_resistente_nm": "N m",
    "potencia_resistente_w": "W",
}


def simular_modelo(
    coordenadas_iniciales_m: np.ndarray, modelo: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna serie agregada y estados individuales activos de un modelo."""
    tiempos = np.linspace(
        0.0, PARAMETROS.periodo_revolucion_s, PARAMETROS.pasos_por_revolucion + 1
    )
    radios = np.linalg.norm(coordenadas_iniciales_m, axis=1)
    filas_agregadas: list[dict] = []
    filas_individuales: list[dict] = []

    for paso, tiempo in enumerate(tiempos):
        angulo = PARAMETROS.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        fuerzas_rodillos = []
        torque_total = 0.0
        conteos = []

        for numero_rodillo, angulo_rodillo in enumerate((0.0, math.pi), start=1):
            activa, u = estado_contacto(coordenadas, angulo_rodillo, PARAMETROS)
            presiones = calcular_presion_pa(
                u, activa, PARAMETROS.presion_maxima_pa, modelo
            )
            fuerzas = fuerzas_axiales_n(presiones, PARAMETROS.diametro_agujero_m)
            torques = contribuciones_torque_nm(
                fuerzas, radios, PARAMETROS.coeficiente_resistencia_tangencial
            )
            fuerzas_rodillos.append(float(fuerzas.sum()))
            torque_total += float(torques.sum())
            indices_activos = np.flatnonzero(activa)
            conteos.append(len(indices_activos))
            for indice in indices_activos:
                filas_individuales.append(
                    {
                        "paso": paso,
                        "id_agujero": int(indice + 1),
                        "tiempo_s": tiempo,
                        "angulo_rad": angulo,
                        "angulo_grados": np.degrees(angulo),
                        "rodillo_activo": numero_rodillo,
                        "radio_m": radios[indice],
                        "u": u[indice],
                        "presion_pa": presiones[indice],
                        "fuerza_axial_n": fuerzas[indice],
                        "torque_nm": torques[indice],
                    }
                )

        fuerza_total = sum(fuerzas_rodillos)
        filas_agregadas.append(
            {
                "tiempo_s": tiempo,
                "angulo_rad": angulo,
                "angulo_grados": np.degrees(angulo),
                "activos_rodillo_1": conteos[0],
                "activos_rodillo_2": conteos[1],
                "activos_total": sum(conteos),
                "fuerza_rodillo_1_n": fuerzas_rodillos[0],
                "fuerza_rodillo_2_n": fuerzas_rodillos[1],
                "fuerza_total_n": fuerza_total,
                "torque_resistente_nm": torque_total,
                "potencia_resistente_w": float(
                    potencia_resistente_w(torque_total, PARAMETROS.omega_rad_s)
                ),
            }
        )
    return pd.DataFrame(filas_agregadas), pd.DataFrame(filas_individuales)


def crear_resumen(resultados_por_modelo: dict[str, pd.DataFrame]) -> pd.DataFrame:
    filas = []
    for modelo, resultados in resultados_por_modelo.items():
        muestra = resultados.iloc[:-1]
        for metrica, unidad in UNIDADES.items():
            filas.append(
                {
                    "modelo": modelo,
                    "metrica": metrica,
                    "minimo": float(muestra[metrica].min()),
                    "maximo": float(muestra[metrica].max()),
                    "promedio": float(muestra[metrica].mean()),
                    "unidad": unidad,
                }
            )
    return pd.DataFrame(filas)


def ejecutar(modelos: tuple[str, ...], animacion: str | None) -> pd.DataFrame:
    coordenadas, fuente = obtener_geometria("auto")
    salida = DIRECTORIO_RESULTADOS_CARGAS
    salida.mkdir(parents=True, exist_ok=True)
    resultados_por_modelo: dict[str, pd.DataFrame] = {}

    for modelo in modelos:
        agregados, individuales = simular_modelo(coordenadas, modelo)
        resultados_por_modelo[modelo] = agregados
        agregados.to_csv(salida / f"cargas_{modelo}.csv", index=False)
        # Solo se almacenan estados activos; los omitidos tienen P=F=T=0.
        individuales.to_csv(
            salida / f"agujeros_activos_{modelo}.csv.gz",
            index=False,
            compression="gzip",
        )
        grafico_fuerzas(agregados, modelo, salida / f"fuerzas_{modelo}.png")

    resumen = crear_resumen(resultados_por_modelo)
    resumen.to_csv(salida / "resumen_modelos.csv", index=False)
    grafico_perfiles(PARAMETROS, salida / "perfiles_presion.png")
    grafico_torque(resultados_por_modelo, salida / "torque_comparativo.png")
    grafico_potencia(resultados_por_modelo, PARAMETROS, salida / "potencia_comparativa.png")
    grafico_resumen(resumen, salida / "resumen_comparativo.png")

    if animacion is not None:
        referencia = resultados_por_modelo.get(animacion)
        if referencia is None:
            referencia, _ = simular_modelo(coordenadas, animacion)
        guardar_animacion_presion(
            coordenadas,
            referencia["tiempo_s"].to_numpy(),
            animacion,
            PARAMETROS,
            salida / f"animacion_presion_{animacion}.gif",
        )

    print(f"Fuente geométrica: {fuente}")
    print(f"Fuerza a 44 MPa por perforación: {PARAMETROS.presion_maxima_pa * math.pi * PARAMETROS.diametro_agujero_m**2 / 4:.3f} N")
    principales = resumen[resumen["metrica"].isin(("fuerza_total_n", "torque_resistente_nm", "potencia_resistente_w"))]
    print(principales.to_string(index=False, float_format=lambda valor: f"{valor:.3f}"))
    return resumen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modelo",
        choices=(*MODELOS_PRESION, "todos"),
        default="todos",
        help="Ejecuta un escenario o la comparación completa.",
    )
    parser.add_argument(
        "--animacion",
        choices=(*MODELOS_PRESION, "ninguna"),
        default="cuadratico",
        help="Animación reducida; no altera los 1440 intervalos numéricos.",
    )
    args = parser.parse_args()
    modelos = MODELOS_PRESION if args.modelo == "todos" else (args.modelo,)
    animacion = None if args.animacion == "ninguna" else args.animacion
    ejecutar(modelos, animacion)


if __name__ == "__main__":
    main()
