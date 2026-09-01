import os
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


RUTA_CSV = (
    "resultados_parametricos_HESS/"
    "resultados_100_casos_HESS.csv"
)

CARPETA_GRAFICOS = "graficos_parametricos_HESS"
os.makedirs(CARPETA_GRAFICOS, exist_ok=True)

df = pd.read_csv(RUTA_CSV)



TOLERANCIA_SOC = 0.01  # 1 punto porcentual de SoC

df["delta_soc_calculado"] = (
    df["soc_final"] - df["soc_inicial"]
)

df["error_soc_pct"] = (
    df["delta_soc_calculado"].abs() * 100
)

df["ciclico_1pct"] = (
    df["delta_soc_calculado"].abs() <= TOLERANCIA_SOC
)

# RTE expresado como porcentaje para los gráficos
df["RTE_pct"] = 100 * df["RTE"]

print("Casos totales:", len(df))
print("Casos cíclicos:", df["ciclico_1pct"].sum())
print("Casos no cíclicos:", (~df["ciclico_1pct"]).sum())


def crear_matriz(df, columna):
    """
    Filas: número de stacks PEMFC.
    Columnas: horas de almacenamiento.
    """
    matriz = df.pivot(
        index="n_pemfc",
        columns="storage_hours",
        values=columna
    )

    return matriz.sort_index().sort_index(axis=1)


matriz_ciclica = crear_matriz(df, "ciclico_1pct")



def graficar_error_soc(df):
    matriz_error = crear_matriz(df, "error_soc_pct")
    matriz_ciclica = crear_matriz(df, "ciclico_1pct")

    valores = matriz_error.to_numpy(dtype=float)
    horas = matriz_error.columns.to_numpy()
    stacks = matriz_error.index.to_numpy()

    fig, ax = plt.subplots(figsize=(11, 7))

    imagen = ax.imshow(
        valores,
        origin="lower",
        aspect="auto",
        cmap="YlOrRd"
    )

    barra = fig.colorbar(imagen, ax=ax)
    barra.set_label(
        r"Error de ciclo $|SoC_f-SoC_0|$ [%]"
    )

    ax.set_xticks(np.arange(len(horas)))
    ax.set_xticklabels(horas)

    ax.set_yticks(np.arange(len(stacks)))
    ax.set_yticklabels(stacks)

    ax.set_xlabel("Horas de almacenamiento")
    ax.set_ylabel("Número de stacks PEMFC")
    ax.set_title(
        "Comprobación de condición cíclica\n"
        "Tolerancia máxima: 1 % de SoC"
    )

    for i in range(len(stacks)):
        for j in range(len(horas)):
            error = matriz_error.iloc[i, j]
            ciclico = bool(matriz_ciclica.iloc[i, j])

            if pd.isna(error):
                texto = "-"
            elif ciclico:
                texto = f"{error:.2f}%"
            else:
                texto = f"{error:.2f}%\nNC"

            ax.text(
                j,
                i,
                texto,
                ha="center",
                va="center",
                fontsize=7
            )

    plt.tight_layout()

    ruta = os.path.join(
        CARPETA_GRAFICOS,
        "mapa_error_soc_ciclicidad.png"
    )

    plt.savefig(ruta, dpi=300, bbox_inches="tight")
    plt.show()


def graficar_heatmap_ciclico(
    df,
    columna,
    titulo,
    etiqueta_barra,
    nombre_archivo,
    formato=".2f",
    cmap_nombre="viridis"
):
    matriz_valor = crear_matriz(df, columna)
    matriz_ciclica = crear_matriz(df, "ciclico_1pct")

    # Los resultados no cíclicos no se consideran válidos
    matriz_valida = matriz_valor.where(matriz_ciclica)

    valores = matriz_valida.to_numpy(dtype=float)
    horas = matriz_valida.columns.to_numpy()
    stacks = matriz_valida.index.to_numpy()

    # Los NaN se mostrarán en gris
    cmap = copy.copy(plt.get_cmap(cmap_nombre))
    cmap.set_bad("lightgray")

    valores_mascara = np.ma.masked_invalid(valores)

    fig, ax = plt.subplots(figsize=(11, 7))

    imagen = ax.imshow(
        valores_mascara,
        origin="lower",
        aspect="auto",
        cmap=cmap
    )

    barra = fig.colorbar(imagen, ax=ax)
    barra.set_label(etiqueta_barra)

    ax.set_xticks(np.arange(len(horas)))
    ax.set_xticklabels(horas)

    ax.set_yticks(np.arange(len(stacks)))
    ax.set_yticklabels(stacks)

    ax.set_xlabel("Horas de almacenamiento")
    ax.set_ylabel("Número de stacks PEMFC")
    ax.set_title(titulo)

    for i in range(len(stacks)):
        for j in range(len(horas)):
            ciclico = bool(matriz_ciclica.iloc[i, j])
            valor = matriz_valor.iloc[i, j]

            if not ciclico:
                texto = "NC"
            elif pd.isna(valor):
                texto = "-"
            else:
                texto = format(valor, formato)

            ax.text(
                j,
                i,
                texto,
                ha="center",
                va="center",
                fontsize=8
            )

    plt.tight_layout()

    ruta = os.path.join(
        CARPETA_GRAFICOS,
        nombre_archivo
    )

    plt.savefig(ruta, dpi=300, bbox_inches="tight")
    plt.show()



graficar_error_soc(df)


# RTE
graficar_heatmap_ciclico(
    df=df,
    columna="RTE_pct",
    titulo="RTE según horas de almacenamiento y stacks PEMFC",
    etiqueta_barra="RTE [%]",
    nombre_archivo="mapa_RTE.png",
    formato=".2f",
    cmap_nombre="viridis"
)


graficar_heatmap_ciclico(
    df=df,
    columna="E_vendida_MWh",
    titulo="Energía total vendida",
    etiqueta_barra="Energía vendida [MWh]",
    nombre_archivo="mapa_energia_vendida.png",
    formato=".0f",
    cmap_nombre="plasma"
)

graficar_heatmap_ciclico(
    df=df,
    columna="P_descarga_real_prom_MW",
    titulo="Potencia promedio real de descarga",
    etiqueta_barra="Potencia promedio [MW]",
    nombre_archivo="mapa_potencia_descarga_promedio.png",
    formato=".2f",
    cmap_nombre="cividis"
)


def graficar_rte_vs_stacks(df):
    df_lineas = df.copy()

    # No graficar RTE como válido cuando el caso no es cíclico.
    # Los NaN producen interrupciones en las líneas.
    df_lineas["RTE_ciclico_pct"] = np.where(
        df_lineas["ciclico_1pct"],
        df_lineas["RTE_pct"],
        np.nan
    )

    matriz = df_lineas.pivot(
        index="storage_hours",
        columns="n_pemfc",
        values="RTE_pct"
    )

    matriz = matriz.sort_index().sort_index(axis=1)

    fig, ax = plt.subplots(figsize=(11, 7))

    for horas in matriz.index:
        ax.plot(
            matriz.columns,
            matriz.loc[horas],
            marker="o",
            linewidth=1.5,
            label=f"{horas:g} h"
        )

    ax.set_xlabel("Número de stacks PEMFC")
    ax.set_ylabel("RTE [%]")
    ax.set_title(
        "Efecto del número de stacks sobre el RTE\n"
        "Cada línea representa horas de almacenamiento"
    )

    ax.set_xticks(matriz.columns)
    ax.grid(True, alpha=0.3)

    ax.legend(
        title="Almacenamiento",
        bbox_to_anchor=(1.02, 1),
        loc="upper left"
    )

    plt.tight_layout()

    ruta = os.path.join(
        CARPETA_GRAFICOS,
        "lineas_RTE_vs_stacks.png"
    )

    plt.savefig(ruta, dpi=300, bbox_inches="tight")
    plt.show()


graficar_rte_vs_stacks(df)