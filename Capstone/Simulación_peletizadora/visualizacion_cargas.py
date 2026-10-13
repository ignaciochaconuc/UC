"""Visualizaciones comparativas de presión y cargas de la Etapa 2B."""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import EllipseCollection
import numpy as np

from cinematica import estado_contacto, rotar
from config import Parametros
from modelos.presion import MODELOS_PRESION, calcular_presion_pa, factor_presion
from visualizacion import _preparar_ejes


ETIQUETAS = {
    "cuadratico": "A: cuadrático",
    "senoidal": "B: senoidal",
    "constante": "C: constante máxima",
}


def grafico_perfiles(parametros: Parametros, ruta: Path) -> None:
    u = np.linspace(0.0, 1.0, 501)
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for modelo in MODELOS_PRESION:
        ax.plot(u, parametros.presion_maxima_pa * factor_presion(u, modelo) / 1e6, label=ETIQUETAS[modelo])
    ax.set(xlabel="Posición normalizada u", ylabel="Presión [MPa]", ylim=(0, 46))
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_fuerzas(resultados, modelo: str, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(resultados["tiempo_s"], resultados["fuerza_rodillo_1_n"] / 1e3, label="Rodillo 1")
    ax.plot(resultados["tiempo_s"], resultados["fuerza_rodillo_2_n"] / 1e3, label="Rodillo 2")
    ax.plot(resultados["tiempo_s"], resultados["fuerza_total_n"] / 1e3, color="black", alpha=0.7, label="Total")
    ax.set(xlabel="Tiempo [s]", ylabel="Fuerza axial equivalente [kN]", title=ETIQUETAS[modelo])
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_torque(resultados_por_modelo: dict, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    for modelo, resultados in resultados_por_modelo.items():
        ax.plot(resultados["tiempo_s"], resultados["torque_resistente_nm"], label=ETIQUETAS[modelo])
    ax.set(xlabel="Tiempo [s]", ylabel="Torque resistente [N m]")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_potencia(resultados_por_modelo: dict, parametros: Parametros, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    for modelo, resultados in resultados_por_modelo.items():
        ax.plot(resultados["tiempo_s"], resultados["potencia_resistente_w"] / 1e3, label=ETIQUETAS[modelo])
    if parametros.eficiencia_transmision is None:
        referencia = parametros.potencia_motor_w / 1e3
        etiqueta = "Motor nominal (referencia; no potencia disponible en matriz)"
    else:
        referencia = parametros.potencia_motor_w * parametros.eficiencia_transmision / 1e3
        etiqueta = "Potencia nominal estimada en matriz"
    ax.axhline(referencia, ls="--", color="black", lw=1.4, label=etiqueta)
    ax.set(xlabel="Tiempo [s]", ylabel="Potencia [kW]")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_resumen(resumen, ruta: Path) -> None:
    metricas = (
        ("fuerza_total_n", 1e3, "Fuerza total [kN]"),
        ("torque_resistente_nm", 1.0, "Torque [N m]"),
        ("potencia_resistente_w", 1e3, "Potencia [kW]"),
    )
    modelos_presentes = [
        modelo for modelo in MODELOS_PRESION if modelo in set(resumen["modelo"])
    ]
    etiquetas_cortas = {
        "cuadratico": "Cuad.",
        "senoidal": "Sen.",
        "constante": "Const.",
    }
    fig, ejes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
    x = np.arange(len(modelos_presentes))
    ancho = 0.36
    for ax, (metrica, escala, ylabel) in zip(ejes, metricas, strict=True):
        datos = resumen[resumen["metrica"] == metrica].set_index("modelo")
        maximos = [datos.loc[m, "maximo"] / escala for m in modelos_presentes]
        promedios = [datos.loc[m, "promedio"] / escala for m in modelos_presentes]
        ax.bar(x - ancho / 2, maximos, ancho, label="Máximo")
        ax.bar(x + ancho / 2, promedios, ancho, label="Promedio")
        ax.set_xticks(x, [etiquetas_cortas[m] for m in modelos_presentes])
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.2)
    ejes[0].legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def guardar_animacion_presion(
    coordenadas_iniciales_m: np.ndarray,
    tiempos_completos_s: np.ndarray,
    modelo: str,
    parametros: Parametros,
    ruta: Path,
    maximo_cuadros: int = 181,
) -> None:
    """Renderiza un subconjunto visual sin reducir la resolución numérica."""
    indices = np.linspace(0, len(tiempos_completos_s) - 1, min(maximo_cuadros, len(tiempos_completos_s)), dtype=int)
    tiempos = tiempos_completos_s[indices]
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    _preparar_ejes(ax, parametros)
    diametro_mm = parametros.diametro_agujero_m * 1_000
    agujeros = EllipseCollection(
        widths=diametro_mm,
        heights=diametro_mm,
        angles=0,
        units="xy",
        offsets=np.empty((0, 2)),
        offset_transform=ax.transData,
        cmap="inferno",
        norm=plt.Normalize(0.0, parametros.presion_maxima_pa / 1e6),
        edgecolors="white",
        linewidths=0.35,
        zorder=5,
    )
    ax.add_collection(agujeros)
    barra = fig.colorbar(agujeros, ax=ax, shrink=0.72)
    barra.set_label("Presión [MPa]")
    texto = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", family="monospace")
    ax.set_title(f"Presión instantánea — {ETIQUETAS[modelo]}")

    def actualizar(indice: int):
        tiempo = tiempos[indice]
        angulo = parametros.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        presion = np.zeros(len(coordenadas))
        conteos = []
        for angulo_rodillo in (0.0, math.pi):
            activa, u = estado_contacto(coordenadas, angulo_rodillo, parametros)
            presion += calcular_presion_pa(u, activa, parametros.presion_maxima_pa, modelo)
            conteos.append(int(activa.sum()))
        agujeros.set_offsets(coordenadas * 1_000)
        agujeros.set_array(presion / 1e6)
        texto.set_text(
            f"t = {tiempo:.4f} s\nθ = {math.degrees(angulo):6.1f}°\n"
            f"R1 = {conteos[0]:2d} | R2 = {conteos[1]:2d}"
        )
        return agujeros, texto

    animacion = FuncAnimation(fig, actualizar, frames=len(tiempos), blit=False)
    animacion.save(ruta, writer=PillowWriter(fps=parametros.fps_animacion), dpi=100)
    plt.close(fig)
