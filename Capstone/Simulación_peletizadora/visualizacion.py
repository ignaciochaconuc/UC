"""Figuras y animación de la matriz plana."""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import EllipseCollection
from matplotlib.patches import Circle, Polygon, Wedge
import numpy as np

from cinematica import mascaras_rodillos, rotar
from config import Parametros


def _rectangulo_local(
    angulo: float, r_min: float, r_max: float, semi_tangencial: float
) -> np.ndarray:
    radial = np.array([math.cos(angulo), math.sin(angulo)])
    tangencial = np.array([-radial[1], radial[0]])
    return np.array(
        [
            r_min * radial - semi_tangencial * tangencial,
            r_max * radial - semi_tangencial * tangencial,
            r_max * radial + semi_tangencial * tangencial,
            r_min * radial + semi_tangencial * tangencial,
        ]
    )


def _preparar_ejes(ax: plt.Axes, parametros: Parametros) -> None:
    ax.add_patch(Circle((0, 0), parametros.radio_matriz_m * 1_000, fill=False, lw=2))
    ax.add_patch(
        Wedge(
            (0, 0),
            parametros.radio_util_exterior_m * 1_000,
            0,
            360,
            width=(parametros.radio_util_exterior_m - parametros.radio_util_interior_m) * 1_000,
            color="#dde7ee",
            alpha=0.55,
            label="Región perforada",
        )
    )
    r_min, r_max = parametros.limite_radial_rodillo_m
    for indice, angulo in enumerate((0.0, math.pi), start=1):
        # Proyección superior del cilindro: ancho axial radial y diámetro tangencial.
        cuerpo = _rectangulo_local(
            angulo, r_min, r_max, parametros.diametro_rodillo_m / 2
        ) * 1_000
        contacto = _rectangulo_local(
            angulo, r_min, r_max, parametros.longitud_contacto_m / 2
        ) * 1_000
        ax.add_patch(
            Polygon(cuerpo, closed=True, color="#777777", alpha=0.12, ec="#555555")
        )
        ax.add_patch(
            Polygon(
                contacto,
                closed=True,
                color="#f5a623",
                alpha=0.38,
                ec="#c87900",
                label="Zona activa aproximada" if indice == 1 else None,
            )
        )
        centro = parametros.centro_radial_rodillo_m * np.array(
            [math.cos(angulo), math.sin(angulo)]
        )
        ax.text(*(centro * 1_000), f"R{indice}", ha="center", va="center", weight="bold")
    ax.annotate(
        "Giro",
        xy=(-62, 78),
        xytext=(-25, 103),
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=.35"},
    )
    limite = parametros.radio_matriz_m * 1_000 * 1.15
    ax.set(xlim=(-limite, limite), ylim=(-limite, limite), xlabel="x [mm]", ylabel="y [mm]")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)


def guardar_figura_estatica(
    coordenadas_iniciales_m: np.ndarray,
    angulo_rad: float,
    parametros: Parametros,
    ruta: Path,
) -> None:
    coordenadas = rotar(coordenadas_iniciales_m, angulo_rad)
    m1, m2 = mascaras_rodillos(coordenadas, parametros)
    colores = np.full(len(coordenadas), "#277da1", dtype=object)
    colores[m1] = "#d62828"
    colores[m2] = "#6a4c93"
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    _preparar_ejes(ax, parametros)
    diametro_mm = parametros.diametro_agujero_m * 1_000
    agujeros = EllipseCollection(
        widths=diametro_mm,
        heights=diametro_mm,
        angles=0,
        units="xy",
        offsets=coordenadas * 1_000,
        offset_transform=ax.transData,
        facecolors=colores,
        edgecolors="white",
        linewidths=0.45,
        zorder=5,
    )
    ax.add_collection(agujeros)
    ax.set_title(
        f"Matriz a {math.degrees(angulo_rad):.1f}° | activos: R1={m1.sum()}, R2={m2.sum()}"
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def guardar_grafico_actividad(resultados, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.step(resultados["tiempo_s"], resultados["activos_rodillo_1"], where="mid", label="Rodillo 1")
    ax.step(resultados["tiempo_s"], resultados["activos_rodillo_2"], where="mid", label="Rodillo 2")
    ax.step(
        resultados["tiempo_s"],
        resultados["activos_total"],
        where="mid",
        color="black",
        alpha=0.65,
        label="Total",
    )
    ax.set(xlabel="Tiempo [s]", ylabel="Número de agujeros activos")
    ax.grid(alpha=0.25)
    ax.legend()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def guardar_animacion(
    coordenadas_iniciales_m: np.ndarray,
    tiempos_s: np.ndarray,
    parametros: Parametros,
    ruta: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    _preparar_ejes(ax, parametros)
    diametro_mm = parametros.diametro_agujero_m * 1_000
    puntos = EllipseCollection(
        widths=diametro_mm,
        heights=diametro_mm,
        angles=0,
        units="xy",
        offsets=np.empty((0, 2)),
        offset_transform=ax.transData,
        edgecolors="white",
        linewidths=0.4,
        zorder=5,
    )
    ax.add_collection(puntos)
    texto = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", family="monospace")

    def actualizar(indice: int):
        tiempo = tiempos_s[indice]
        angulo = parametros.omega_rad_s * tiempo
        coordenadas = rotar(coordenadas_iniciales_m, angulo)
        m1, m2 = mascaras_rodillos(coordenadas, parametros)
        colores = np.full(len(coordenadas), "#277da1", dtype=object)
        colores[m1] = "#d62828"
        colores[m2] = "#6a4c93"
        puntos.set_offsets(coordenadas * 1_000)
        puntos.set_facecolors(colores)
        texto.set_text(
            f"t = {tiempo:.4f} s\nθ = {math.degrees(angulo):6.1f}°\n"
            f"R1 = {m1.sum():2d} | R2 = {m2.sum():2d}"
        )
        return puntos, texto

    animacion = FuncAnimation(fig, actualizar, frames=len(tiempos_s), blit=False)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    animacion.save(ruta, writer=PillowWriter(fps=parametros.fps_animacion), dpi=110)
    plt.close(fig)
