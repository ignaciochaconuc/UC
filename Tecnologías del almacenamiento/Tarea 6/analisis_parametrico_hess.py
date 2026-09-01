"""Análisis paramétrico HESS: 10 horas de almacenamiento x 10 números de stacks.

Ejecuta 100 casos usando las funciones de ``simulacion_hess.py`` y el motor
físico de ``HESS_model.py``.

Los rangos están al inicio del archivo para que puedan modificarse fácilmente.
"""

from __future__ import annotations

from pathlib import Path
import time

import pandas as pd

from simulacion_hess import cargar_perfil, simular_caso

# =====================================================================
# CONFIGURACIÓN EDITABLE
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_PERFIL = BASE_DIR / "perfil_despacho_completo_preliminar (3).csv"
CARPETA_SALIDA = BASE_DIR / "resultados_parametricos_HESS"

# 10 valores. Incluyen las 18 h del caso base.
HORAS_ALMACENAMIENTO = [4, 6, 8, 10, 12, 14, 16, 18, 21, 24]

# Número de stacks PEMFC instalados. Se mantienen 100 stacks PEMEL.
# Se incluyen valores sobre el umbral de activación para identificar una meseta.
N_STACKS_PEMFC = [50, 60, 70, 80, 90, 100, 106, 120, 135, 150]

N_STACKS_PEMEL = 100
POTENCIA_PLANTA_MW = 100.0
P_STACK_PEMFC_MW = 0.70
ETA_FC_GUESS = 0.50
SOC_INICIAL = 0.50
DT_S = 3600.0
TOLERANCIA_SOC_CICLICO = 0.01


def ejecutar_analisis_parametrico() -> pd.DataFrame:
    """Ejecuta las 100 combinaciones y guarda tablas de resultados."""
    if len(HORAS_ALMACENAMIENTO) != 10 or len(N_STACKS_PEMFC) != 10:
        raise ValueError(
            "El análisis solicitado debe contener exactamente 10 valores "
            "para cada variable (10 x 10 = 100 casos)."
        )

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    df_perfil = cargar_perfil(ARCHIVO_PERFIL)

    resultados: list[dict] = []
    total = len(HORAS_ALMACENAMIENTO) * len(N_STACKS_PEMFC)
    contador = 0
    inicio = time.perf_counter()

    for horas in HORAS_ALMACENAMIENTO:
        for n_pemfc in N_STACKS_PEMFC:
            contador += 1
            print(
                f"[{contador:03d}/{total}] "
                f"Simulando storage_hours={horas}, n_pemfc={n_pemfc}...",
                flush=True,
            )

            try:
                resumen, _ = simular_caso(
                    df_perfil=df_perfil,
                    storage_hours=horas,
                    n_pemfc=n_pemfc,
                    n_pemel=N_STACKS_PEMEL,
                    x_MW=POTENCIA_PLANTA_MW,
                    p_stack_pemfc_MW=P_STACK_PEMFC_MW,
                    eta_fc_guess=ETA_FC_GUESS,
                    soc0=SOC_INICIAL,
                    dt_s=DT_S,
                    retornar_horario=False,
                )
                resumen["caso"] = contador
                resumen["estado_simulacion"] = "ok"
                resumen["error"] = ""
            except Exception as exc:  # Mantiene el loop aunque falle un caso.
                resumen = {
                    "caso": contador,
                    "storage_hours": horas,
                    "n_pemfc": n_pemfc,
                    "estado_simulacion": "error",
                    "error": str(exc),
                }

            resultados.append(resumen)

    df_resultados = pd.DataFrame(resultados)
    columnas_inicio = [
        "caso",
        "storage_hours",
        "n_pemfc",
        "estado_simulacion",
        "error",
    ]
    otras = [c for c in df_resultados.columns if c not in columnas_inicio]
    df_resultados = df_resultados[columnas_inicio + otras]

    ruta_resultados = CARPETA_SALIDA / "resultados_100_casos_HESS.csv"
    df_resultados.to_csv(ruta_resultados, index=False)

    df_ok = df_resultados[df_resultados["estado_simulacion"] == "ok"].copy()
    if df_ok.empty:
        raise RuntimeError(
            "Ningún caso terminó correctamente. Revise la columna error en "
            f"{ruta_resultados.name}."
        )

    # Tablas 10 x 10 para facilitar los gráficos y mapas de calor posteriores.
    metricas_pivot = {
        "margen_total_USD": "matriz_margen_USD.csv",
        "RTE": "matriz_RTE.csv",
        "E_vendida_MWh": "matriz_energia_vendida_MWh.csv",
        "soc_final": "matriz_soc_final.csv",
        "abs_delta_soc": "matriz_desbalance_soc.csv",
        "P_descarga_real_prom_MW": "matriz_potencia_descarga_prom_MW.csv",
    }

    for metrica, nombre_archivo in metricas_pivot.items():
        if metrica not in df_ok.columns:
            continue
        matriz = df_ok.pivot(
            index="storage_hours",
            columns="n_pemfc",
            values=metrica,
        )
        matriz.to_csv(CARPETA_SALIDA / nombre_archivo)

    # El criterio aún es preliminar: maximiza el margen energético, sin CAPEX.
    # Se priorizan diseños cíclicos y sin limitaciones materiales.
    factibles = df_ok[
        (df_ok["abs_delta_soc"] <= TOLERANCIA_SOC_CICLICO)
        & (df_ok["sin_limites_materiales"] == True)  # noqa: E712
    ].copy()

    if not factibles.empty:
        ranking = factibles.sort_values(
            ["margen_total_USD", "storage_hours", "n_pemfc"],
            ascending=[False, True, True],
        )
        criterio = "máximo margen entre casos cíclicos y sin límites materiales"
    else:
        # Respaldo si ningún diseño cumple la tolerancia cíclica.
        ranking = df_ok.sort_values(
            ["abs_delta_soc", "margen_total_USD"],
            ascending=[True, False],
        )
        criterio = "menor desbalance de SoC y luego máximo margen"

    ranking.to_csv(
        CARPETA_SALIDA / "ranking_preliminar_HESS.csv",
        index=False,
    )

    mejor = ranking.iloc[0]
    pd.DataFrame(
        [
            {
                **mejor.to_dict(),
                "criterio_seleccion_preliminar": criterio,
                "advertencia": (
                    "Este no es el diseño económico final: faltan CAPEX, OPEX, "
                    "LCOS y VPN."
                ),
            }
        ]
    ).to_csv(
        CARPETA_SALIDA / "mejor_caso_preliminar_HESS.csv",
        index=False,
    )

    # Se guarda el perfil horario solamente para el mejor caso preliminar.
    resumen_mejor, df_mejor = simular_caso(
        df_perfil=df_perfil,
        storage_hours=float(mejor["storage_hours"]),
        n_pemfc=int(mejor["n_pemfc"]),
        n_pemel=N_STACKS_PEMEL,
        x_MW=POTENCIA_PLANTA_MW,
        p_stack_pemfc_MW=P_STACK_PEMFC_MW,
        eta_fc_guess=ETA_FC_GUESS,
        soc0=SOC_INICIAL,
        dt_s=DT_S,
        retornar_horario=True,
    )
    if df_mejor is not None:
        df_mejor.to_csv(
            CARPETA_SALIDA / "perfil_horario_mejor_caso_preliminar.csv",
            index=False,
        )
    pd.DataFrame([resumen_mejor]).to_csv(
        CARPETA_SALIDA / "resumen_mejor_caso_preliminar.csv",
        index=False,
    )

    duracion = time.perf_counter() - inicio
    print("\nAnálisis terminado.")
    print(f"Casos ejecutados: {len(df_resultados)}")
    print(f"Casos con error: {(df_resultados['estado_simulacion'] == 'error').sum()}")
    print(f"Tiempo total: {duracion:.1f} s")
    print(f"Resultados guardados en: {CARPETA_SALIDA}")
    print("\nMejor caso preliminar:")
    print(
        mejor[
            [
                "storage_hours",
                "n_pemfc",
                "RTE",
                "margen_total_USD",
                "soc_final",
                "abs_delta_soc",
            ]
        ].to_string()
    )
    print(
        "\nNota: el mejor caso definitivo debe seleccionarse después de "
        "incorporar CAPEX, OPEX, LCOS y VPN."
    )

    return df_resultados


if __name__ == "__main__":
    ejecutar_analisis_parametrico()
