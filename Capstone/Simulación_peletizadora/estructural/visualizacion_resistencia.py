"""Gráficos de resistencia estática y fatiga."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _guardar(fig, ruta: Path) -> None:
    fig.tight_layout(); fig.savefig(ruta, dpi=180, bbox_inches="tight"); plt.close(fig)


def esfuerzo_longitudinal(resumen: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for caso, g in resumen.groupby("caso"):
        ax.plot(g.x_m*1e3, g.esfuerzo_nominal_max_pa*1e-6, "o-", label=caso)
    ax.set(xlabel="x [mm]", ylabel="Esfuerzo nominal máximo [MPa]",
           title="Esfuerzo nominal en secciones críticas")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def mapa_secciones(resumen: pd.DataFrame, ruta: Path) -> None:
    base = resumen[resumen.caso == "3C_inclinacion"]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot([0, 270], [0, 0], color="k", lw=5)
    ax.scatter(base.x_m*1e3, base.esfuerzo_nominal_max_pa*1e-6,
               c=base.esfuerzo_nominal_max_pa*1e-6, cmap="plasma", s=70)
    for _, r in base.iterrows():
        ax.annotate(r.seccion.replace("_", "\n"), (r.x_m*1e3, r.esfuerzo_nominal_max_pa*1e-6),
                    xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7, rotation=45)
    ax.set(xlabel="x [mm]", ylabel="Esfuerzo nominal [MPa]", title="Secciones críticas — caso nominal 3C")
    ax.grid(alpha=.25); _guardar(fig, ruta)


def historial_tension(historiales: pd.DataFrame, resumen: pd.DataFrame, ruta: Path) -> None:
    crit = resumen[resumen.caso == "3C_inclinacion"].sort_values("esfuerzo_nominal_max_pa").iloc[-1].seccion
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for caso in ("3A_C_referencia", "3C_inclinacion"):
        d = historiales[(historiales.caso == caso) & (historiales.seccion == crit)]
        ax.plot(d.angulo_carga_grados, d.tension_nominal_pa*1e-6, label=caso)
    ax.axhline(0, color="k", lw=.6); ax.set(xlabel="Ángulo de carga [°]", ylabel="Tensión firmada [MPa]",
                                             title=f"Historia en punto material fijo — {crit}")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def comparar_factores(sens: pd.DataFrame, ruta_estatica: Path, ruta_fatiga: Path) -> None:
    materiales = ["parametrico_bajo", "parametrico_medio", "parametrico_alto",
                  "ovako_qt_mecanizado_R95"]
    d = sens[(sens.caso == "3C_inclinacion") & sens.material.isin(materiales)]
    # Mínimo entre secciones para cada combinación.
    g = d.groupby(["material", "entalla"], as_index=False)[["factor_seguridad_fluencia", "factor_seguridad_goodman"]].min()
    for col, titulo, ruta in (("factor_seguridad_fluencia", "Sensibilidad de resistencia estática", ruta_estatica),
                              ("factor_seguridad_goodman", "Goodman preliminar por escenarios", ruta_fatiga)):
        tabla = g.pivot(index="material", columns="entalla", values=col)
        fig, ax = plt.subplots(figsize=(10, 4.5)); tabla.plot.bar(ax=ax)
        ax.axhline(1, color="tab:red", ls="--"); ax.set(ylabel="Factor de seguridad", title=titulo)
        ax.grid(axis="y", alpha=.25); ax.tick_params(axis="x", rotation=0); _guardar(fig, ruta)


def sensibilidad_kt(sens: pd.DataFrame, ruta: Path) -> None:
    d = sens[(sens.caso == "3C_inclinacion") & (sens.material == "parametrico_medio")]
    i = d.groupby("entalla").factor_seguridad_goodman.idxmin(); d = d.loc[i].sort_values("kt")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(d.kt, d.factor_seguridad_fluencia, "o-", label="Fluencia")
    ax.plot(d.kt, d.factor_seguridad_goodman, "s-", label="Goodman")
    ax.axhline(1, color="tab:red", ls="--")
    ax.set(xlabel="Kt paramétrico", ylabel="Factor de seguridad mínimo", title="Sensibilidad a concentración de esfuerzo")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def sensibilidad_marin(sens: pd.DataFrame, ruta: Path) -> None:
    d = sens[(sens.caso == "3C_inclinacion") & sens.material.str.startswith("ovako_qt_")
             & (sens.entalla == "sensibilidad_moderada")]
    i = d.groupby("material").factor_seguridad_goodman.idxmin(); d = d.loc[i]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for acabado, g in d.groupby("acabado_superficial"):
        g = g.sort_values("confiabilidad_porcentaje")
        ax.plot(g.confiabilidad_porcentaje, g.factor_seguridad_goodman, "o-", label=acabado)
    ax.axhline(1, color="tab:red", ls="--")
    ax.set(xlabel="Confiabilidad asumida [%]", ylabel="Factor Goodman mínimo",
           title="Sensibilidad Marin — SAE 4140 +QT Ovako, Kt=1,5")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)
