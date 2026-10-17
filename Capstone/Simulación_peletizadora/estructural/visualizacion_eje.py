"""Gráficos del análisis estructural del eje transversal."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analisis import ResultadoCaso
from .config_eje import ConfiguracionEje
from .viga_eb import SistemaViga


def _guardar(fig, ruta: Path) -> None:
    fig.tight_layout()
    fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)


def graficar_geometria(config: ConfiguracionEje, ruta: Path) -> None:
    fig, (ax, axd) = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
    for s in config.segmentos:
        x = np.array([s.x_inicio_m, s.x_fin_m]) * 1e3
        r = s.diametro_exterior_m * 500
        ax.fill_between(x, -r, r, alpha=.55, step="post")
        axd.plot(x, [2*r, 2*r], lw=4)
    for x in (*config.rodamientos_izquierdos_m, *config.rodamientos_derechos_m):
        ax.axvline(x * 1e3, color="tab:red", ls="--", lw=.9)
    ax.set(ylabel="Radio [mm]", title="Geometría longitudinal y centros de rodamientos")
    ax.axis("equal"); ax.grid(alpha=.25)
    axd.set(xlabel="x [mm]", ylabel="Diámetro [mm]"); axd.grid(alpha=.25)
    _guardar(fig, ruta)


def graficar_cuerpo_libre(tabla: pd.DataFrame, indice: int, config: ConfiguracionEje, ruta: Path) -> None:
    fila = tabla.iloc[indice]
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot([0, config.longitud_m*1e3], [0, 0], color="k", lw=5)
    posiciones = (*config.rodamientos_izquierdos_m, *config.rodamientos_derechos_m)
    columnas = (
        "compactacion_r1_rodamiento_a_n", "compactacion_r1_rodamiento_b_n",
        "compactacion_r2_rodamiento_a_n", "compactacion_r2_rodamiento_b_n",
    )
    escala = max(abs(float(fila[c])) for c in columnas)
    for x, c in zip(posiciones, columnas, strict=True):
        f = float(fila[c]); dy = 1.5 * f / escala
        ax.annotate("", (x*1e3, dy), (x*1e3, 0), arrowprops=dict(arrowstyle="->", color="tab:blue", lw=2))
        ax.text(x*1e3, dy + .12*np.sign(dy), f"{f:.0f} N", ha="center", fontsize=8)
    ax.plot([0, 0], [-1.8, 1.8], color="tab:red", lw=3)
    ax.plot([270, 270], [-1.8, 1.8], color="tab:red", lw=3)
    ax.set(xlabel="x [mm]", yticks=[], ylim=(-2, 2), title=f"Diagrama de cuerpo libre, caso C, θ={fila['angulo_grados']:.2f}°")
    ax.grid(axis="x", alpha=.25)
    _guardar(fig, ruta)


def graficar_reacciones(caso: ResultadoCaso, ruta: Path) -> None:
    s = caso.series
    fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for lado_f, lado_m in (("izquierda", "izquierdo"), ("derecha", "derecho")):
        axs[0].plot(s.angulo_grados, s[f"reaccion_vertical_{lado_f}_n"], label=f"Vertical {lado_f}")
        axs[0].plot(s.angulo_grados, s[f"reaccion_horizontal_{lado_f}_n"], ls="--", label=f"Horizontal {lado_f}")
        axs[1].plot(s.angulo_grados, s[f"momento_vertical_{lado_m}_nm"], label=f"Vertical {lado_f}")
        axs[1].plot(s.angulo_grados, s[f"momento_horizontal_{lado_m}_nm"], ls="--", label=f"Horizontal {lado_f}")
    axs[0].set(ylabel="Fuerza [N]"); axs[1].set(xlabel="Ángulo [°]", ylabel="Momento [N·m]")
    for ax in axs: ax.grid(alpha=.25); ax.legend(ncol=2, fontsize=8)
    fig.suptitle("Reacciones en los empotramientos durante una revolución")
    _guardar(fig, ruta)


def _extremos_xy(caso: ResultadoCaso, valores: np.ndarray, indice: int) -> tuple[np.ndarray, np.ndarray]:
    return caso.posiciones_extremos_m.ravel()*1e3, valores[:, :, indice].ravel()


def graficar_diagramas(caso: ResultadoCaso, indice: int, ruta: Path) -> None:
    xv, mv = _extremos_xy(caso, caso.momento_vertical_nm, indice)
    _, mh = _extremos_xy(caso, caso.momento_horizontal_nm, indice)
    # Cortantes internos en la cara izquierda/derecha de cada elemento.
    vv = np.column_stack((caso.fuerzas_extremo_verticales[:, 0, indice], -caso.fuerzas_extremo_verticales[:, 2, indice])).ravel()
    vh = np.column_stack((caso.fuerzas_extremo_horizontales[:, 0, indice], -caso.fuerzas_extremo_horizontales[:, 2, indice])).ravel()
    fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axs[0].plot(xv, vv, label="Plano vertical"); axs[0].plot(xv, vh, label="Plano horizontal")
    axs[1].plot(xv, mv, label="Plano vertical"); axs[1].plot(xv, mh, label="Plano horizontal")
    axs[0].set(ylabel="Cortante interno V [N]"); axs[1].set(xlabel="x [mm]", ylabel="Momento flector [N·m]")
    for ax in axs: ax.axhline(0, color="k", lw=.6); ax.grid(alpha=.25); ax.legend()
    fig.suptitle(f"Diagramas críticos, caso C, θ={caso.angulos_grados[indice]:.2f}°")
    _guardar(fig, ruta)


def graficar_envolventes(envolvente: pd.DataFrame, ruta_m: Path, ruta_s: Path) -> None:
    for columna, escala, ylabel, titulo, ruta in (
        ("momento_resultante_envolvente_nm", 1, "Momento [N·m]", "Envolvente de momento flector resultante", ruta_m),
        ("esfuerzo_nominal_envolvente_pa", 1e-6, "Esfuerzo nominal [MPa]", "Envolvente de esfuerzo nominal de flexión", ruta_s),
    ):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(envolvente.x_m*1e3, envolvente[columna]*escala)
        ax.set(xlabel="x [mm]", ylabel=ylabel, title=titulo); ax.grid(alpha=.25)
        _guardar(fig, ruta)


def graficar_deformada(caso: ResultadoCaso, sistema: SistemaViga, indice: int, ruta: Path) -> None:
    v = caso.solucion_vertical.desplazamientos[0::2, indice]
    h = caso.solucion_horizontal.desplazamientos[0::2, indice]
    u = np.hypot(v, h)
    amp = .10*sistema.config.longitud_m/max(float(u.max()), 1e-15)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(sistema.nodos_m*1e3, np.zeros_like(v), color=".6", label="Sin deformar")
    ax.plot(sistema.nodos_m*1e3, v*amp*1e3, label=f"Vertical ×{amp:.0f}")
    ax.plot(sistema.nodos_m*1e3, h*amp*1e3, label=f"Horizontal ×{amp:.0f}")
    ax.set(xlabel="x [mm]", ylabel="Desplazamiento amplificado [mm]", title="Deformada en el instante crítico")
    ax.grid(alpha=.25); ax.legend(); _guardar(fig, ruta)


def graficar_desplazamiento(caso: ResultadoCaso, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(caso.series.angulo_grados, caso.series.desplazamiento_max_m*1e3)
    ax.set(xlabel="Ángulo [°]", ylabel="Desplazamiento máximo [mm]", title="Desplazamiento máximo durante una revolución")
    ax.grid(alpha=.25); _guardar(fig, ruta)


def graficar_comparacion(resumen: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    x = np.arange(len(resumen)); etiquetas = resumen.caso.str[0]
    for ax, col, factor, ylabel in zip(axs, ("momento_max_nm", "esfuerzo_nominal_max_pa", "desplazamiento_max_m"), (1, 1e-6, 1e3), ("N·m", "MPa", "mm"), strict=True):
        ax.bar(x, resumen[col]*factor); ax.set_xticks(x, etiquetas); ax.set_ylabel(ylabel); ax.grid(axis="y", alpha=.25)
    fig.suptitle("Comparación de máximos por caso de carga"); _guardar(fig, ruta)


def graficar_convergencia(tabla: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    for ax, col, ylabel in zip(axs, ("desplazamiento_max_mm", "momento_max_nm", "esfuerzo_max_mpa"), ("Desplazamiento [mm]", "Momento [N·m]", "Esfuerzo [MPa]"), strict=True):
        ax.plot(tabla.longitud_maxima_elemento_mm, tabla[col], "o-"); ax.invert_xaxis(); ax.set(xlabel="h máximo [mm]", ylabel=ylabel); ax.grid(alpha=.25)
    fig.suptitle("Convergencia de malla en el instante crítico"); _guardar(fig, ruta)
