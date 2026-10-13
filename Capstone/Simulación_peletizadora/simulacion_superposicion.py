"""Etapa 2C: cargas por área de superposición disco–huella."""

from __future__ import annotations

import argparse
import math

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from cinematica import estado_contacto, rotar
from config import DIRECTORIO_RESULTADOS_SUPERPOSICION, PARAMETROS
from modelos.presion import MODELOS_PRESION
from modelos.superposicion import (
    coordenadas_locales,
    fraccion_cobertura,
    interseccion_disco_rectangulo,
    limites_huella,
)
from modelos.torque import contribuciones_torque_nm, potencia_resistente_w
from simulacion import obtener_geometria
from simulacion_cargas import simular_modelo
from visualizacion_superposicion import (
    grafico_comparacion_fuerzas,
    grafico_convergencia,
    grafico_ejemplos_cobertura,
    grafico_fuerzas_area,
    grafico_resultantes,
    grafico_torque_cuatro,
    guardar_animacion_cobertura,
)


MODELOS_2C = (*MODELOS_PRESION, "area_superposicion")


def _promedio_ponderado(valores: np.ndarray, pesos: np.ndarray) -> float:
    suma = float(np.sum(pesos))
    return float(np.sum(valores * pesos) / suma) if suma > 0.0 else math.nan


def simular_area_superposicion(
    coordenadas_iniciales_m: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tiempos = np.linspace(
        0.0, PARAMETROS.periodo_revolucion_s, PARAMETROS.pasos_por_revolucion + 1
    )
    radio_agujero = PARAMETROS.diametro_agujero_m / 2.0
    area_agujero = math.pi * radio_agujero**2
    limites = limites_huella(PARAMETROS)
    radios_reales = np.linalg.norm(coordenadas_iniciales_m, axis=1)
    filas_agregadas: list[dict] = []
    filas_individuales: list[dict] = []

    for paso, tiempo in enumerate(tiempos):
        angulo = PARAMETROS.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        fuerzas_rodillo = []
        superpuestas_rodillo = []
        centros_activos_rodillo = []
        resultantes: list[dict[str, float]] = []
        torque_total = 0.0
        coberturas_positivas: list[np.ndarray] = []

        for numero, angulo_rodillo in enumerate((0.0, math.pi), start=1):
            locales = coordenadas_locales(coordenadas, angulo_rodillo)
            areas, centroide_r, centroide_t = interseccion_disco_rectangulo(
                locales,
                radio_agujero,
                limites,
                PARAMETROS.orden_cuadratura_superposicion,
            )
            coberturas = fraccion_cobertura(areas, radio_agujero)
            positiva = areas > np.finfo(float).eps * area_agujero
            fuerzas = PARAMETROS.presion_maxima_pa * areas
            torques = contribuciones_torque_nm(
                fuerzas, radios_reales, PARAMETROS.coeficiente_resistencia_tangencial
            )
            fuerza_rodillo = float(np.sum(fuerzas))
            fuerzas_rodillo.append(fuerza_rodillo)
            superpuestas_rodillo.append(int(np.count_nonzero(positiva)))
            mascara_centros, _ = estado_contacto(coordenadas, angulo_rodillo, PARAMETROS)
            centros_activos_rodillo.append(int(np.count_nonzero(mascara_centros)))
            torque_total += float(np.sum(torques))
            coberturas_positivas.append(coberturas[positiva])

            resultantes.append(
                {
                    "centro_radial": _promedio_ponderado(locales[:, 0], fuerzas),
                    "centro_tangencial": _promedio_ponderado(locales[:, 1], fuerzas),
                    "centroide_radial": _promedio_ponderado(centroide_r[positiva], fuerzas[positiva]),
                    "centroide_tangencial": _promedio_ponderado(centroide_t[positiva], fuerzas[positiva]),
                }
            )

            for indice in np.flatnonzero(positiva):
                filas_individuales.append(
                    {
                        "paso": paso,
                        "tiempo_s": tiempo,
                        "angulo_grados": np.degrees(angulo),
                        "id_agujero": int(indice + 1),
                        "rodillo": numero,
                        "radio_agujero_m": radios_reales[indice],
                        "x_centro_global_m": coordenadas[indice, 0],
                        "y_centro_global_m": coordenadas[indice, 1],
                        "centro_local_radial_m": locales[indice, 0],
                        "centro_local_tangencial_m": locales[indice, 1],
                        "area_efectiva_m2": area_agujero,
                        "area_superpuesta_m2": areas[indice],
                        "fraccion_cobertura": coberturas[indice],
                        "centroide_superposicion_radial_m": centroide_r[indice],
                        "centroide_superposicion_tangencial_m": centroide_t[indice],
                        "fuerza_axial_n": fuerzas[indice],
                        "torque_nm": torques[indice],
                    }
                )

        coberturas_instante = np.concatenate(coberturas_positivas)
        fuerza_total = sum(fuerzas_rodillo)
        fila = {
            "tiempo_s": tiempo,
            "angulo_rad": angulo,
            "angulo_grados": np.degrees(angulo),
            "centros_activos_rodillo_1": centros_activos_rodillo[0],
            "centros_activos_rodillo_2": centros_activos_rodillo[1],
            "perforaciones_superpuestas_rodillo_1": superpuestas_rodillo[0],
            "perforaciones_superpuestas_rodillo_2": superpuestas_rodillo[1],
            "perforaciones_superpuestas_total": sum(superpuestas_rodillo),
            "cobertura_positiva_min": float(np.min(coberturas_instante)),
            "cobertura_positiva_max": float(np.max(coberturas_instante)),
            "cobertura_positiva_media": float(np.mean(coberturas_instante)),
            "fuerza_rodillo_1_n": fuerzas_rodillo[0],
            "fuerza_rodillo_2_n": fuerzas_rodillo[1],
            "fuerza_total_n": fuerza_total,
            "torque_resistente_nm": torque_total,
            "potencia_resistente_w": float(
                potencia_resistente_w(torque_total, PARAMETROS.omega_rad_s)
            ),
            "limite_uniforme_superpuestos_n": sum(superpuestas_rodillo)
            * PARAMETROS.presion_maxima_pa
            * area_agujero,
        }
        for numero, resultante in enumerate(resultantes, start=1):
            for nombre, valor in resultante.items():
                fila[f"resultante_{nombre}_r{numero}_m"] = valor
        filas_agregadas.append(fila)

    return pd.DataFrame(filas_agregadas), pd.DataFrame(filas_individuales)


def estudio_convergencia() -> pd.DataFrame:
    limites = limites_huella(PARAMETROS)
    x_min, x_max, y_min, y_max = limites
    radio = PARAMETROS.diametro_agujero_m / 2
    x_medio = (x_min + x_max) / 2
    casos = {
        "medio_borde": (x_medio, y_max),
        "esquina": (x_min + 0.35 * radio, y_max - 0.20 * radio),
        "doble_borde": (x_min - 0.25 * radio, y_min + 0.40 * radio),
    }
    filas = []
    for nombre, centro in casos.items():
        referencia = interseccion_disco_rectangulo(
            np.array([centro]), radio, limites, orden=512
        )[0][0]
        for orden in (8, 16, 32, 64, 128, 256):
            area = interseccion_disco_rectangulo(
                np.array([centro]), radio, limites, orden=orden
            )[0][0]
            filas.append(
                {
                    "caso": nombre,
                    "orden": orden,
                    "area_m2": area,
                    "area_referencia_m2": referencia,
                    "error_relativo": abs(area - referencia) / referencia,
                }
            )
    return pd.DataFrame(filas)


def resumen_area(agregados: pd.DataFrame, individuales: pd.DataFrame) -> pd.DataFrame:
    muestra = agregados.iloc[:-1]
    individuales_muestra = individuales[individuales["paso"] < PARAMETROS.pasos_por_revolucion]
    especificaciones = {
        "fuerza_rodillo_1_n": "N",
        "fuerza_rodillo_2_n": "N",
        "fuerza_total_n": "N",
        "torque_resistente_nm": "N m",
        "potencia_resistente_w": "W",
        "perforaciones_superpuestas_rodillo_1": "perforaciones",
        "perforaciones_superpuestas_rodillo_2": "perforaciones",
        "perforaciones_superpuestas_total": "perforaciones",
    }
    filas = []
    for metrica, unidad in especificaciones.items():
        indice_max = muestra[metrica].idxmax()
        filas.append(
            {
                "metrica": metrica,
                "minimo": float(muestra[metrica].min()),
                "maximo": float(muestra[metrica].max()),
                "promedio": float(muestra[metrica].mean()),
                "unidad": unidad,
                "tiempo_maximo_s": float(muestra.loc[indice_max, "tiempo_s"]),
                "angulo_maximo_grados": float(muestra.loc[indice_max, "angulo_grados"]),
            }
        )
    coberturas = individuales_muestra["fraccion_cobertura"]
    indice_cobertura = coberturas.idxmax()
    filas.append(
        {
            "metrica": "fraccion_cobertura_contactos",
            "minimo": float(coberturas.min()),
            "maximo": float(coberturas.max()),
            "promedio": float(coberturas.mean()),
            "unidad": "1",
            "tiempo_maximo_s": float(individuales_muestra.loc[indice_cobertura, "tiempo_s"]),
            "angulo_maximo_grados": float(individuales_muestra.loc[indice_cobertura, "angulo_grados"]),
        }
    )
    return pd.DataFrame(filas)


def resumen_comparativo(resultados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    filas = []
    for modelo, datos in resultados.items():
        muestra = datos.iloc[:-1]
        filas.append(
            {
                "modelo": modelo,
                "fuerza_total_max_n": float(muestra["fuerza_total_n"].max()),
                "fuerza_total_media_n": float(muestra["fuerza_total_n"].mean()),
                "torque_max_nm": float(muestra["torque_resistente_nm"].max()),
                "torque_medio_nm": float(muestra["torque_resistente_nm"].mean()),
                "potencia_max_w": float(muestra["potencia_resistente_w"].max()),
                "potencia_media_w": float(muestra["potencia_resistente_w"].mean()),
            }
        )
    return pd.DataFrame(filas)


def ejecutar(modelos: tuple[str, ...], crear_animacion: bool) -> None:
    coordenadas, fuente = obtener_geometria("auto")
    salida = DIRECTORIO_RESULTADOS_SUPERPOSICION
    salida.mkdir(parents=True, exist_ok=True)
    resultados: dict[str, pd.DataFrame] = {}
    agregados_area = individuales_area = None

    for modelo in modelos:
        if modelo == "area_superposicion":
            agregados_area, individuales_area = simular_area_superposicion(coordenadas)
            resultados[modelo] = agregados_area
            agregados_area.to_csv(salida / "cargas_area_superposicion.csv", index=False)
            individuales_area.to_csv(
                salida / "contribuciones_area_superposicion.csv.gz",
                index=False,
                compression="gzip",
            )
            resumen_area(agregados_area, individuales_area).to_csv(
                salida / "resumen_area_superposicion.csv", index=False
            )
            grafico_fuerzas_area(agregados_area, salida / "fuerzas_area_superposicion.png")
            grafico_resultantes(agregados_area, salida / "resultante_radial.png")
            grafico_ejemplos_cobertura(PARAMETROS, salida / "ejemplos_cobertura.png")
        else:
            agregados, _ = simular_modelo(coordenadas, modelo)
            resultados[modelo] = agregados

    comparacion = resumen_comparativo(resultados)
    comparacion.to_csv(salida / "comparacion_modelos.csv", index=False)
    grafico_torque_cuatro(resultados, salida / "torque_cuatro_modelos.png")
    grafico_comparacion_fuerzas(comparacion, salida / "fuerzas_comparacion_modelos.png")

    convergencia = estudio_convergencia()
    convergencia.to_csv(salida / "convergencia_integracion.csv", index=False)
    grafico_convergencia(convergencia, salida / "convergencia_integracion.png")

    if crear_animacion:
        if agregados_area is None:
            agregados_area, _ = simular_area_superposicion(coordenadas)
        guardar_animacion_cobertura(
            coordenadas,
            agregados_area["tiempo_s"].to_numpy(),
            PARAMETROS,
            salida / "animacion_cobertura.gif",
        )

    print(f"Fuente geométrica: {fuente}")
    print(comparacion.to_string(index=False, float_format=lambda valor: f"{valor:.3f}"))
    if agregados_area is not None and individuales_area is not None:
        print("\nResumen del modelo por áreas:")
        print(resumen_area(agregados_area, individuales_area).to_string(index=False, float_format=lambda valor: f"{valor:.6f}"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modelo",
        choices=(*MODELOS_2C, "todos"),
        default="todos",
        help="Ejecuta el modelo geométrico, uno anterior o la comparación completa.",
    )
    parser.add_argument("--sin-animacion", action="store_true", help="Omite el GIF de cobertura.")
    args = parser.parse_args()
    modelos = MODELOS_2C if args.modelo == "todos" else (args.modelo,)
    ejecutar(modelos, crear_animacion=not args.sin_animacion)


if __name__ == "__main__":
    main()
