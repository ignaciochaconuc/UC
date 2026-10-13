"""Gráficos y animación del modelo geométrico de superposición."""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import EllipseCollection
from matplotlib.patches import Circle, Rectangle
import numpy as np

from cinematica import rotar
from modelos.superposicion import (
    coordenadas_locales,
    fraccion_cobertura,
    interseccion_disco_rectangulo,
    limites_huella,
)
from visualizacion import _preparar_ejes


ETIQUETAS_2C = {
    "cuadratico": "A: cuadrático",
    "senoidal": "B: senoidal",
    "constante": "C: constante",
    "area_superposicion": "D: superposición de áreas",
}


def grafico_ejemplos_cobertura(parametros, ruta: Path) -> None:
    limites = limites_huella(parametros)
    x_min, x_max, y_min, y_max = limites
    radio = parametros.diametro_agujero_m / 2
    x_medio = (x_min + x_max) / 2
    casos = [
        ("Fuera", (x_medio, y_max + 1.5 * radio)),
        ("Borde", (x_medio, y_max)),
        ("Esquina", (x_min, y_min)),
        ("Contenida", (x_medio, 0.0)),
    ]
    fig, ejes = plt.subplots(1, 4, figsize=(13, 3.6), constrained_layout=True)
    for ax, (nombre, centro) in zip(ejes, casos, strict=True):
        areas, _, _ = interseccion_disco_rectangulo(
            np.array([centro]), radio, limites, parametros.orden_cuadratura_superposicion
        )
        cobertura = fraccion_cobertura(areas, radio)[0]
        margen = 2.2 * radio
        ax.add_patch(
            Rectangle(
                (x_min * 1e3, y_min * 1e3),
                (x_max - x_min) * 1e3,
                (y_max - y_min) * 1e3,
                facecolor="#f5a623",
                alpha=0.30,
                edgecolor="#a65f00",
            )
        )
        ax.add_patch(
            Circle(
                (centro[0] * 1e3, centro[1] * 1e3),
                radio * 1e3,
                facecolor="#277da1",
                alpha=0.65,
                edgecolor="black",
            )
        )
        ax.set(
            xlim=((centro[0] - margen) * 1e3, (centro[0] + margen) * 1e3),
            ylim=((centro[1] - margen) * 1e3, (centro[1] + margen) * 1e3),
            title=f"{nombre}\nCobertura = {100*cobertura:.1f} %",
            xlabel="radial [mm]",
        )
        ax.set_aspect("equal")
        ax.grid(alpha=0.15)
    ejes[0].set_ylabel("tangencial [mm]")
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_fuerzas_area(resultados, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(resultados["tiempo_s"], resultados["fuerza_rodillo_1_n"] / 1e3, label="Rodillo 1")
    ax.plot(resultados["tiempo_s"], resultados["fuerza_rodillo_2_n"] / 1e3, label="Rodillo 2")
    ax.plot(resultados["tiempo_s"], resultados["fuerza_total_n"] / 1e3, color="black", alpha=0.7, label="Total")
    ax.set(xlabel="Tiempo [s]", ylabel="Fuerza axial equivalente [kN]")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_torque_cuatro(resultados_por_modelo: dict, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    for modelo, datos in resultados_por_modelo.items():
        ax.plot(datos["tiempo_s"], datos["torque_resistente_nm"], label=ETIQUETAS_2C[modelo])
    ax.set(xlabel="Tiempo [s]", ylabel="Torque resistente [N m]")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_comparacion_fuerzas(resumen_comparativo, ruta: Path) -> None:
    modelos = list(resumen_comparativo["modelo"])
    x = np.arange(len(modelos))
    ancho = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax.bar(x - ancho / 2, resumen_comparativo["fuerza_total_max_n"] / 1e3, ancho, label="Máxima")
    ax.bar(x + ancho / 2, resumen_comparativo["fuerza_total_media_n"] / 1e3, ancho, label="Media")
    ax.set_xticks(x, [ETIQUETAS_2C[m].split(":", 1)[0] for m in modelos])
    ax.set(ylabel="Fuerza total [kN]", xlabel="Modelo")
    ax.grid(axis="y", alpha=0.2)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_resultantes(resultados, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(resultados["tiempo_s"], resultados["resultante_centroide_radial_r1_m"] * 1e3, label="Rodillo 1")
    ax.plot(resultados["tiempo_s"], resultados["resultante_centroide_radial_r2_m"] * 1e3, label="Rodillo 2")
    ax.set(xlabel="Tiempo [s]", ylabel="Posición radial de la resultante [mm]")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def grafico_convergencia(convergencia, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    for caso, datos in convergencia.groupby("caso"):
        ax.loglog(datos["orden"], datos["error_relativo"].clip(lower=1e-16), marker="o", label=caso)
    ax.set(xlabel="Orden de Gauss–Legendre", ylabel="Error relativo respecto de orden 512")
    ax.grid(which="both", alpha=0.25)
    ax.legend()
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def guardar_animacion_cobertura(
    coordenadas_iniciales_m: np.ndarray,
    tiempos_completos_s: np.ndarray,
    parametros,
    ruta: Path,
) -> None:
    indices = np.linspace(
        0,
        len(tiempos_completos_s) - 1,
        min(parametros.cuadros_animacion_superposicion, len(tiempos_completos_s)),
        dtype=int,
    )
    tiempos = tiempos_completos_s[indices]
    radio = parametros.diametro_agujero_m / 2
    limites = limites_huella(parametros)
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    _preparar_ejes(ax, parametros)
    agujeros = EllipseCollection(
        widths=parametros.diametro_agujero_m * 1e3,
        heights=parametros.diametro_agujero_m * 1e3,
        angles=0,
        units="xy",
        offsets=np.empty((0, 2)),
        offset_transform=ax.transData,
        cmap="viridis",
        norm=plt.Normalize(0.0, 1.0),
        edgecolors="white",
        linewidths=0.35,
        zorder=5,
    )
    ax.add_collection(agujeros)
    barra = fig.colorbar(agujeros, ax=ax, shrink=0.72)
    barra.set_label("Fracción de cobertura")
    texto = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", family="monospace")
    ax.set_title("Superposición disco–huella")

    def actualizar(indice: int):
        tiempo = tiempos[indice]
        angulo = parametros.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        coberturas = np.zeros(len(coordenadas))
        conteos = []
        for angulo_rodillo in (0.0, math.pi):
            locales = coordenadas_locales(coordenadas, angulo_rodillo)
            areas, _, _ = interseccion_disco_rectangulo(
                locales, radio, limites, parametros.orden_cuadratura_superposicion
            )
            fracciones = fraccion_cobertura(areas, radio)
            coberturas += fracciones
            conteos.append(int(np.count_nonzero(fracciones > 0.0)))
        agujeros.set_offsets(coordenadas * 1e3)
        agujeros.set_array(coberturas)
        texto.set_text(
            f"t = {tiempo:.4f} s\nθ = {math.degrees(angulo):6.1f}°\n"
            f"R1 = {conteos[0]:2d} | R2 = {conteos[1]:2d}"
        )
        return agujeros, texto

    animacion = FuncAnimation(fig, actualizar, frames=len(tiempos), blit=False)
    animacion.save(ruta, writer=PillowWriter(fps=parametros.fps_animacion), dpi=100)
    plt.close(fig)
