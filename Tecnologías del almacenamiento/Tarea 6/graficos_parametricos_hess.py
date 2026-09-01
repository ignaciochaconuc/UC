"""Lectura, impresión y visualización del análisis paramétrico HESS.

Archivos esperados
------------------
1. resultados_100_casos_HESS.csv
2. perfil_horario_mejor_caso_preliminar.csv  (opcional)

El script:
- verifica y recalcula la RTE;
- imprime tablas y mejores casos;
- genera mapas de calor;
- genera curvas y gráficos de comparación;
- genera gráficos horarios del mejor caso, si existe el archivo horario.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =====================================================================
# CONFIGURACIÓN
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent

# Cambia estas rutas si tus CSV están en otra carpeta.
RUTA_RESULTADOS = BASE_DIR / "resultados_parametricos_HESS" / "resultados_100_casos_HESS.csv"
RUTA_HORARIO_MEJOR = BASE_DIR / "resultados_parametricos_HESS" / "perfil_horario_mejor_caso_preliminar.csv"
CARPETA_GRAFICOS = BASE_DIR / "graficos_parametricos_HESS"

TOL_SOC = 0.01            # condición cíclica: |SoC final - SoC inicial| <= 1 %
TOP_N = 10
MOSTRAR_GRAFICOS = True   # False: guarda los gráficos sin abrir ventanas


# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================
def cargar_resultados(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta}. Modifica RUTA_RESULTADOS al inicio del script."
        )

    df = pd.read_csv(ruta)

    columnas_minimas = {
        "storage_hours",
        "n_pemfc",
        "E_comprada_MWh",
        "E_vendida_MWh",
    }
    faltantes = columnas_minimas.difference(df.columns)
    if faltantes:
        raise ValueError(
            "Faltan columnas indispensables en el CSV: "
            + ", ".join(sorted(faltantes))
        )

    # Excluir casos fallidos, si la columna existe.
    if "estado_simulacion" in df.columns:
        df = df[df["estado_simulacion"].astype(str).str.lower() == "ok"].copy()

    columnas_numericas = [
        "storage_hours",
        "n_pemfc",
        "E_comprada_MWh",
        "E_vendida_MWh",
        "RTE",
        "margen_total_USD",
        "soc_inicial",
        "soc_final",
        "delta_soc",
        "abs_delta_soc",
        "P_descarga_real_prom_MW",
        "P_descarga_real_max_MW",
        "V_H2_m3",
        "V_O2_m3",
        "horas_above_max_power",
        "horas_inventory_limited",
        "horas_tank_capacity_limited",
        "horas_tanque_vacio",
        "horas_tanque_lleno",
    ]
    for columna in columnas_numericas:
        if columna in df.columns:
            df[columna] = pd.to_numeric(df[columna], errors="coerce")

    # Recalcular RTE para revisar consistencia.
    df["RTE_calculada"] = np.where(
        df["E_comprada_MWh"] > 0,
        df["E_vendida_MWh"] / df["E_comprada_MWh"],
        np.nan,
    )

    if "RTE" not in df.columns:
        df["RTE"] = df["RTE_calculada"]

    df["error_RTE"] = (df["RTE"] - df["RTE_calculada"]).abs()

    if "abs_delta_soc" not in df.columns:
        if "delta_soc" in df.columns:
            df["abs_delta_soc"] = df["delta_soc"].abs()
        elif {"soc_inicial", "soc_final"}.issubset(df.columns):
            df["delta_soc"] = df["soc_final"] - df["soc_inicial"]
            df["abs_delta_soc"] = df["delta_soc"].abs()
        else:
            df["abs_delta_soc"] = np.nan

    df["caso_ciclico"] = df["abs_delta_soc"] <= TOL_SOC

    return df.sort_values(["storage_hours", "n_pemfc"]).reset_index(drop=True)


def guardar_o_mostrar(nombre: str) -> None:
    CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(CARPETA_GRAFICOS / nombre, dpi=300, bbox_inches="tight")
    if MOSTRAR_GRAFICOS:
        plt.show()
    else:
        plt.close()


def mapa_calor(
    df: pd.DataFrame,
    metrica: str,
    titulo: str,
    etiqueta_barra: str,
    nombre_archivo: str,
    formato: str = ".2f",
) -> None:
    if metrica not in df.columns:
        print(f"No se genera {titulo}: falta la columna '{metrica}'.")
        return

    matriz = (
        df.pivot(index="storage_hours", columns="n_pemfc", values=metrica)
        .sort_index()
        .sort_index(axis=1)
    )

    valores = matriz.to_numpy(dtype=float)

    plt.figure(figsize=(12, 7))
    imagen = plt.imshow(valores, aspect="auto", origin="lower")
    plt.colorbar(imagen, label=etiqueta_barra)

    plt.xticks(
        ticks=np.arange(len(matriz.columns)),
        labels=[str(int(x)) for x in matriz.columns],
    )
    plt.yticks(
        ticks=np.arange(len(matriz.index)),
        labels=[f"{x:g}" for x in matriz.index],
    )

    plt.xlabel("Número de stacks PEMFC")
    plt.ylabel("Horas de almacenamiento")
    plt.title(titulo)

    # Escribir el valor dentro de cada celda.
    for i in range(valores.shape[0]):
        for j in range(valores.shape[1]):
            valor = valores[i, j]
            if np.isfinite(valor):
                plt.text(j, i, format(valor, formato), ha="center", va="center", fontsize=8)

    guardar_o_mostrar(nombre_archivo)


def imprimir_resumen(df: pd.DataFrame) -> None:
    print("\n" + "=" * 74)
    print("RESUMEN DEL ANÁLISIS PARAMÉTRICO HESS")
    print("=" * 74)
    print(f"Casos válidos: {len(df)}")
    print(f"Horas evaluadas: {sorted(df['storage_hours'].dropna().unique())}")
    print(f"Stacks PEMFC evaluados: {sorted(df['n_pemfc'].dropna().unique())}")
    print(f"Máximo error entre RTE guardada y recalculada: {df['error_RTE'].max():.3e}")
    print(f"Casos cíclicos con tolerancia ±{TOL_SOC:.2f}: {df['caso_ciclico'].sum()}")

    columnas_top = [
        "storage_hours",
        "n_pemfc",
        "RTE",
        "E_comprada_MWh",
        "E_vendida_MWh",
        "abs_delta_soc",
    ]
    if "margen_total_USD" in df.columns:
        columnas_top.append("margen_total_USD")
    if "P_descarga_real_prom_MW" in df.columns:
        columnas_top.append("P_descarga_real_prom_MW")

    print(f"\nTOP {TOP_N} CASOS POR RTE")
    print(
        df.nlargest(TOP_N, "RTE")[columnas_top]
        .to_string(index=False, float_format=lambda x: f"{x:,.4f}")
    )

    ciclicos = df[df["caso_ciclico"]].copy()
    if not ciclicos.empty:
        print(f"\nTOP {TOP_N} CASOS CÍCLICOS POR RTE")
        print(
            ciclicos.nlargest(TOP_N, "RTE")[columnas_top]
            .to_string(index=False, float_format=lambda x: f"{x:,.4f}")
        )

        mejor = ciclicos.nlargest(1, "RTE").iloc[0]
        print("\nMEJOR CASO CÍCLICO SEGÚN RTE")
        print(f"Horas de almacenamiento : {mejor['storage_hours']:g} h")
        print(f"Stacks PEMFC             : {int(mejor['n_pemfc'])}")
        print(f"RTE                      : {100 * mejor['RTE']:.2f} %")
        print(f"Energía comprada         : {mejor['E_comprada_MWh']:,.2f} MWh")
        print(f"Energía vendida          : {mejor['E_vendida_MWh']:,.2f} MWh")
        print(f"Desbalance absoluto SoC  : {mejor['abs_delta_soc']:.5f}")
    else:
        print("\nNo hay casos que cumplan la tolerancia cíclica seleccionada.")

    matriz_rte = (
        df.pivot(index="storage_hours", columns="n_pemfc", values="RTE")
        .sort_index()
        .sort_index(axis=1)
    )
    print("\nMATRIZ RTE [%]")
    print((100 * matriz_rte).round(2).to_string())


def crear_graficos_parametricos(df: pd.DataFrame) -> None:
    # 1. RTE: indicador central exigido por la tarea.
    mapa_calor(
        df,
        "RTE",
        "Eficiencia round-trip para los 100 casos",
        "RTE [-]",
        "01_mapa_calor_RTE.png",
        formato=".3f",
    )

    # 2. Energía realmente entregada: revela limitación por stacks o inventario.
    mapa_calor(
        df,
        "E_vendida_MWh",
        "Energía total vendida en los 61 días",
        "Energía vendida [MWh]",
        "02_mapa_calor_energia_vendida.png",
        formato=".0f",
    )

    # 3. Desbalance del inventario: distingue resultados comparables/cíclicos.
    mapa_calor(
        df,
        "abs_delta_soc",
        "Desbalance entre SoC final e inicial",
        "|ΔSoC| [-]",
        "03_mapa_calor_desbalance_soc.png",
        formato=".3f",
    )

    # 4. Margen de arbitraje antes de CAPEX/OPEX.
    mapa_calor(
        df,
        "margen_total_USD",
        "Margen energético durante los 61 días",
        "Margen [USD]",
        "04_mapa_calor_margen.png",
        formato=".0f",
    )

    # 5. Potencia promedio real de la PEMFC.
    mapa_calor(
        df,
        "P_descarga_real_prom_MW",
        "Potencia real promedio durante la descarga",
        "Potencia [MW]",
        "05_mapa_calor_potencia_descarga.png",
        formato=".1f",
    )

    # 6. Curvas de RTE en función del número de stacks.
    plt.figure(figsize=(11, 7))
    for horas, grupo in df.groupby("storage_hours"):
        grupo = grupo.sort_values("n_pemfc")
        plt.plot(
            grupo["n_pemfc"],
            100 * grupo["RTE"],
            marker="o",
            label=f"{horas:g} h",
        )
    plt.xlabel("Número de stacks PEMFC")
    plt.ylabel("RTE [%]")
    plt.title("Efecto del número de stacks sobre la RTE")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Almacenamiento", ncol=2)
    guardar_o_mostrar("06_RTE_vs_stacks.png")

    # 7. Energía vendida en función del número de stacks.
    plt.figure(figsize=(11, 7))
    for horas, grupo in df.groupby("storage_hours"):
        grupo = grupo.sort_values("n_pemfc")
        plt.plot(
            grupo["n_pemfc"],
            grupo["E_vendida_MWh"],
            marker="o",
            label=f"{horas:g} h",
        )
    plt.xlabel("Número de stacks PEMFC")
    plt.ylabel("Energía vendida [MWh]")
    plt.title("Energía vendida según stacks y capacidad de almacenamiento")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Almacenamiento", ncol=2)
    guardar_o_mostrar("07_energia_vendida_vs_stacks.png")

    # 8. Compromiso entre eficiencia y condición cíclica.
    plt.figure(figsize=(10, 7))
    dispersion = plt.scatter(
        df["abs_delta_soc"],
        100 * df["RTE"],
        s=35 + 2 * df["n_pemfc"],
        c=df["storage_hours"],
    )
    plt.colorbar(dispersion, label="Horas de almacenamiento")
    plt.axvline(TOL_SOC, linestyle="--", label=f"Tolerancia SoC = {TOL_SOC:.2f}")
    plt.xlabel("|SoC final - SoC inicial|")
    plt.ylabel("RTE [%]")
    plt.title("RTE y condición cíclica de los casos")
    plt.grid(True, alpha=0.3)
    plt.legend()
    guardar_o_mostrar("08_RTE_vs_desbalance_soc.png")

    # 9. Relación entre tamaño de tanque y RTE, si se guardó el volumen.
    if "V_H2_m3" in df.columns:
        plt.figure(figsize=(10, 7))
        dispersion = plt.scatter(
            df["V_H2_m3"],
            100 * df["RTE"],
            s=35 + 2 * df["n_pemfc"],
            c=df["n_pemfc"],
        )
        plt.colorbar(dispersion, label="Número de stacks PEMFC")
        plt.xlabel("Volumen del tanque de H₂ [m³]")
        plt.ylabel("RTE [%]")
        plt.title("RTE frente al dimensionamiento del tanque de H₂")
        plt.grid(True, alpha=0.3)
        guardar_o_mostrar("09_RTE_vs_volumen_H2.png")

    # 10. Horas limitadas por potencia para reconocer la meseta de stacks.
    if "horas_above_max_power" in df.columns:
        mapa_calor(
            df,
            "horas_above_max_power",
            "Horas limitadas por potencia máxima de la PEMFC",
            "Horas limitadas",
            "10_mapa_calor_horas_limitadas_potencia.png",
            formato=".0f",
        )


def graficos_horarios_mejor_caso(ruta: Path) -> None:
    if not ruta.exists():
        print(
            "\nNo se encontraron datos horarios del mejor caso. "
            "Se omiten los gráficos horarios."
        )
        return

    df = pd.read_csv(ruta)
    if "timestamp" not in df.columns:
        print("El archivo horario no contiene la columna timestamp.")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values("timestamp").reset_index(drop=True)

    if "soc_H2" in df.columns:
        plt.figure(figsize=(14, 5))
        plt.plot(df["timestamp"], df["soc_H2"], label="SoC H₂")
        if "soc_O2" in df.columns:
            plt.plot(df["timestamp"], df["soc_O2"], label="SoC O₂")
        plt.xlabel("Tiempo")
        plt.ylabel("SoC [-]")
        plt.title("Evolución horaria del estado de carga del mejor caso")
        plt.ylim(-0.05, 1.05)
        plt.grid(True, alpha=0.3)
        plt.legend()
        guardar_o_mostrar("11_soc_mejor_caso.png")

    if {"P_cmd_MW", "P_real_MW"}.issubset(df.columns):
        plt.figure(figsize=(14, 5))
        plt.step(df["timestamp"], df["P_cmd_MW"], where="mid", label="Potencia comandada")
        plt.step(df["timestamp"], df["P_real_MW"], where="mid", label="Potencia real")
        plt.xlabel("Tiempo")
        plt.ylabel("Potencia [MW]")
        plt.title("Potencia comandada y real del mejor caso")
        plt.grid(True, alpha=0.3)
        plt.legend()
        guardar_o_mostrar("12_potencia_mejor_caso.png")

    if "precio_usd_mwh" in df.columns:
        plt.figure(figsize=(14, 5))
        plt.plot(df["timestamp"], df["precio_usd_mwh"])
        plt.xlabel("Tiempo")
        plt.ylabel("Precio [USD/MWh]")
        plt.title("Precio horario utilizado por el mejor caso")
        plt.grid(True, alpha=0.3)
        guardar_o_mostrar("13_precio_mejor_caso.png")

    if "flujo_USD" in df.columns:
        flujo_acumulado = df["flujo_USD"].fillna(0.0).cumsum()
        plt.figure(figsize=(14, 5))
        plt.plot(df["timestamp"], flujo_acumulado)
        plt.xlabel("Tiempo")
        plt.ylabel("Flujo acumulado [USD]")
        plt.title("Flujo energético acumulado del mejor caso")
        plt.grid(True, alpha=0.3)
        guardar_o_mostrar("14_flujo_acumulado_mejor_caso.png")

    if {"eta_el_lhv", "eta_fc_lhv"}.intersection(df.columns):
        plt.figure(figsize=(14, 5))
        if "eta_el_lhv" in df.columns:
            plt.plot(df["timestamp"], 100 * df["eta_el_lhv"], label="PEMEL")
        if "eta_fc_lhv" in df.columns:
            plt.plot(df["timestamp"], 100 * df["eta_fc_lhv"], label="PEMFC")
        plt.xlabel("Tiempo")
        plt.ylabel("Eficiencia LHV [%]")
        plt.title("Eficiencias electroquímicas horarias del mejor caso")
        plt.grid(True, alpha=0.3)
        plt.legend()
        guardar_o_mostrar("15_eficiencias_mejor_caso.png")


def main() -> None:
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.width", 180)
    pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

    df = cargar_resultados(RUTA_RESULTADOS)
    imprimir_resumen(df)
    crear_graficos_parametricos(df)
    graficos_horarios_mejor_caso(RUTA_HORARIO_MEJOR)

    print(f"\nGráficos guardados en: {CARPETA_GRAFICOS}")


if __name__ == "__main__":
    main()
