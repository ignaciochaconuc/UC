"""Visualizaciones para la Etapa 3B."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analisis import ResultadoCaso
from .config_eje import ConfiguracionEje
from .holgura_rodillos import GeometriaRodilloAxial, geometria_rodillos
from .viga_eb import SistemaViga


def _guardar(fig, ruta: Path) -> None:
    fig.tight_layout(); fig.savefig(ruta, dpi=180, bbox_inches="tight"); plt.close(fig)


def graficar_rodamientos(tabla: pd.DataFrame, ruta: Path) -> None:
    d = tabla[tabla.caso == "C"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for nombre in ("izquierdo_a", "izquierdo_b", "derecho_a", "derecho_b"):
        ax.plot(d.angulo_grados, d[f"v_{nombre}_m"]*1e3, label=nombre.replace("_", " "))
    ax.set(xlabel="Ángulo [°]", ylabel="Desplazamiento vertical [mm]",
           title="Desplazamiento vertical de los cuatro rodamientos — caso C")
    ax.grid(alpha=.25); ax.legend(ncol=2); _guardar(fig, ruta)


def graficar_centros(cinematica: pd.DataFrame, ruta: Path) -> None:
    d = cinematica[cinematica.caso == "C"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for rodillo, g in d.groupby("rodillo"):
        ax.plot(g.angulo_grados, g.v_centro_rodillo_m*1e3, label=rodillo)
    ax.set(xlabel="Ángulo [°]", ylabel="Desplazamiento vertical [mm]",
           title="Desplazamiento de los centros de rodillos — caso C")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def graficar_inclinaciones(cinematica: pd.DataFrame, ruta: Path) -> None:
    d = cinematica[cinematica.caso == "C"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for rodillo, g in d.groupby("rodillo"):
        ax.plot(g.angulo_grados, g.inclinacion_vertical_grados, label=rodillo)
    ax.set(xlabel="Ángulo [°]", ylabel="Inclinación vertical [°]",
           title="Inclinación cinemática de los rodillos — caso C")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def graficar_holgura_instantanea(holguras: pd.DataFrame, ruta: Path) -> None:
    d = holguras[holguras.caso == "C"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for rodillo, g in d.groupby("rodillo"):
        ax.plot(g.angulo_grados, g.holgura_minima_m*1e3, label=rodillo)
    ax.axhline(0, color="tab:red", ls="--", label="incompatibilidad g<0")
    ax.axhline(.1, color="k", ls=":", label="nominal 0,1 mm")
    ax.set(xlabel="Ángulo [°]", ylabel="Holgura mínima [mm]",
           title="Holgura mínima instantánea — caso C")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def graficar_comparacion_holguras(holguras: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, rodillo in zip(axs, ("izquierdo", "derecho"), strict=True):
        for caso in ("B", "C"):
            g = holguras[(holguras.caso == caso) & (holguras.rodillo == rodillo)]
            ax.plot(g.angulo_grados, g.holgura_minima_m*1e3, label=caso)
        d = holguras[(holguras.caso == "D") & (holguras.rodillo == rodillo)]
        ax.axhline(float(d.holgura_minima_m.iloc[0])*1e3, color="tab:green", label="D")
        ax.axhline(0, color="tab:red", ls="--"); ax.axhline(.1, color="k", ls=":")
        ax.set(xlabel="Ángulo [°]", title=f"Rodillo {rodillo}"); ax.grid(alpha=.25); ax.legend()
    axs[0].set_ylabel("Holgura mínima [mm]")
    fig.suptitle("Comparación de holgura mínima: B, C y D")
    _guardar(fig, ruta)


def graficar_esquema_critico(
    casos: dict[str, ResultadoCaso], sistema: SistemaViga, cinematica: pd.DataFrame,
    holguras: pd.DataFrame, ruta: Path,
) -> None:
    indice_global = holguras.holgura_minima_m.idxmin(); crit = holguras.loc[indice_global]
    caso = casos[str(crit.caso)]; indice = int(np.nanargmin(np.abs(caso.tiempos_s-float(crit.tiempo_s))))
    v = caso.solucion_vertical.desplazamientos[0::2, indice]
    amp = .015/max(float(np.max(np.abs(v))), 1e-12)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(sistema.nodos_m*1e3, v*amp*1e3, color="k", lw=2, label=f"eje deformado ×{amp:.0f}")
    ax.plot([0, 270], [-.1*amp, -.1*amp], color="tab:gray", lw=3, label="matriz rígida (referencia amplificada)")
    for geo in geometria_rodillos(sistema.config):
        c = cinematica[(cinematica.caso == crit.caso) & (cinematica.rodillo == geo.nombre)].iloc[indice]
        ax.plot([geo.x_izquierdo_m*1e3, geo.x_derecho_m*1e3],
                [c.v_extremo_izquierdo_m*amp*1e3, c.v_extremo_derecho_m*amp*1e3],
                lw=7, alpha=.7, label=f"rodillo {geo.nombre}")
    texto = (f"Crítico: caso {crit.caso}, rodillo {crit.rodillo}, {crit.zona_holgura_minima}\n"
             f"g={crit.holgura_minima_m*1e3:.4f} mm; θ={crit.angulo_grados:.2f}°")
    ax.text(.02, .97, texto, transform=ax.transAxes, va="top",
            bbox=dict(facecolor="white", alpha=.85, edgecolor=".7"))
    ax.set(xlabel="x [mm]", ylabel="Desplazamiento amplificado [mm]",
           title="Esquema amplificado del estado de menor holgura")
    ax.grid(alpha=.25); ax.legend(loc="lower center", ncol=2, fontsize=8); _guardar(fig, ruta)
