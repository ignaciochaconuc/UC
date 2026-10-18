"""Gráficos de la verificación preliminar de rodamientos."""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _guardar(fig, ruta: Path) -> None:
    fig.tight_layout(); fig.savefig(ruta, dpi=180, bbox_inches="tight"); plt.close(fig)


def cargas_revolucion(cargas: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for nombre, g in cargas.groupby("rodamiento"):
        ax.plot(g.angulo_grados, g.carga_radial_resultante_n/1e3, label=nombre)
    ax.set(xlabel="Ángulo [°]", ylabel="Carga radial resultante [kN]",
           title="Carga radial de los cuatro rodamientos — 3C")
    ax.grid(alpha=.25); ax.legend(ncol=2); _guardar(fig, ruta)


def comparar_cargas(resumen: pd.DataFrame, ruta: Path) -> None:
    x = np.arange(len(resumen)); ancho=.36
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(x-ancho/2, resumen.carga_radial_max_n/1e3, ancho, label="Máxima")
    ax.bar(x+ancho/2, resumen.carga_dinamica_equivalente_n/1e3, ancho, label="Peq")
    ax.set_xticks(x, resumen.rodamiento); ax.set(ylabel="Carga [kN]", title="Carga máxima y dinámica equivalente")
    ax.grid(axis="y", alpha=.25); ax.legend(); _guardar(fig, ruta)


def vida_l10(resumen: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8))
    barras=ax.bar(resumen.rodamiento, resumen.l10_horas)
    ax.bar_label(barras, fmt="%.0f h", padding=3, fontsize=8)
    ax.set(ylabel="L10h [h]", title="Vida básica nominal ISO 281 (90 %)")
    ax.grid(axis="y", alpha=.25); _guardar(fig, ruta)


def factor_estatico(resumen: pd.DataFrame, conservador: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8)); x=np.arange(len(resumen)); ancho=.36
    ax.bar(x-ancho/2, resumen.factor_estatico_s0, ancho, label="3C nominal")
    ax.bar(x+ancho/2, conservador.factor_estatico_s0, ancho, label="3A-D artificial")
    ax.set_xticks(x, resumen.rodamiento); ax.set(ylabel="S0=C0/P0,max", title="Factor estático por rodamiento")
    ax.grid(axis="y", alpha=.25); ax.legend(); _guardar(fig, ruta)


def sensibilidad_vida(sens: pd.DataFrame, rodamiento_critico: str, ruta: Path) -> None:
    d=sens[(sens.rodamiento==rodamiento_critico)&(sens.factor_capacidad_dinamica==1.0)
           &(sens.factor_deslizamiento_cinematico==1.0)]
    fig, ax=plt.subplots(figsize=(9,4.8))
    for fv,g in d.groupby("factor_velocidad"):
        g=g.sort_values("factor_carga")
        ax.plot(g.factor_carga, g.l10_horas, "o-", label=f"velocidad ×{fv:.1f}")
    ax.set_yscale("log"); ax.set(xlabel="Factor de carga", ylabel="L10h [h]",
                                  title=f"Sensibilidad de vida — {rodamiento_critico}")
    ax.grid(alpha=.25, which="both"); ax.legend(); _guardar(fig,ruta)
