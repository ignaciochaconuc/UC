"""Gráficos comparativos de la Etapa 3C."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import PARAMETROS
from modelos.superposicion_variable import longitud_contacto_desde_holgura


def _guardar(fig, ruta: Path) -> None:
    fig.tight_layout(); fig.savefig(ruta, dpi=180, bbox_inches="tight"); plt.close(fig)


def holguras_evolucion(serie: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for n, ax in enumerate(axs, 1):
        for zona in ("izquierda", "centro", "derecha"):
            ax.plot(serie.angulo_grados, serie[f"holgura_{zona}_r{n}_m"]*1e3, label=zona)
        ax.set(title=f"Rodillo {n}", xlabel="Ángulo [°]"); ax.grid(alpha=.25); ax.legend()
    axs[0].set_ylabel("Holgura [mm]"); fig.suptitle("Holguras acopladas con inclinación")
    _guardar(fig, ruta)


def comparar_holguras(base: pd.DataFrame, uniforme: pd.DataFrame, inclinada: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for n, (ax, nombre) in enumerate(zip(axs, ("izquierdo", "derecho"), strict=True), 1):
        b = base[(base.caso == "C") & (base.rodillo == nombre)]
        ax.plot(b.angulo_grados, b.holgura_minima_m*1e3, label="3B desacoplado")
        ax.plot(uniforme.angulo_grados, uniforme[f"holgura_minima_r{n}_m"]*1e3, label="3C uniforme")
        ax.plot(inclinada.angulo_grados, inclinada[f"holgura_minima_r{n}_m"]*1e3, label="3C inclinación")
        ax.axhline(.1, color="k", ls=":"); ax.set(title=f"Rodillo {n}", xlabel="Ángulo [°]"); ax.grid(alpha=.25); ax.legend(fontsize=8)
    axs[0].set_ylabel("Holgura mínima [mm]"); fig.suptitle("Comparación desacoplada y acoplada")
    _guardar(fig, ruta)


def comparar_fuerzas(base: pd.DataFrame, uniforme: pd.DataFrame, inclinada: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for n, ax in enumerate(axs, 1):
        ax.plot(base.angulo_grados, base[f"fuerza_rodillo_{n}_n"]/1e3, label="2C")
        ax.plot(uniforme.angulo_grados, uniforme[f"fuerza_rodillo_{n}_n"]/1e3, label="3C uniforme")
        ax.plot(inclinada.angulo_grados, inclinada[f"fuerza_rodillo_{n}_n"]/1e3, label="3C inclinación")
        ax.set(title=f"Rodillo {n}", xlabel="Ángulo [°]"); ax.grid(alpha=.25); ax.legend(fontsize=8)
    axs[0].set_ylabel("Fuerza normal [kN]"); fig.suptitle("Fuerzas normales por rodillo")
    _guardar(fig, ruta)


def comparar_torque_potencia(base: pd.DataFrame, uniforme: pd.DataFrame, inclinada: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for datos, etiqueta in ((base, "2C"), (uniforme, "3C uniforme"), (inclinada, "3C inclinación")):
        axs[0].plot(datos.angulo_grados, datos.torque_resistente_nm, label=etiqueta)
        axs[1].plot(datos.angulo_grados, datos.potencia_resistente_w/1e3, label=etiqueta)
    axs[0].set(ylabel="Torque [N·m]"); axs[1].set(xlabel="Ángulo [°]", ylabel="Potencia [kW]")
    for ax in axs: ax.grid(alpha=.25); ax.legend()
    fig.suptitle("Torque y potencia resistente"); _guardar(fig, ruta)


def deformaciones_inclinaciones(uniforme: pd.DataFrame, inclinada: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for datos, estilo, etiqueta in ((uniforme, "--", "uniforme"), (inclinada, "-", "inclinación")):
        for n in (1, 2):
            axs[0].plot(datos.angulo_grados, datos[f"desplazamiento_centro_r{n}_m"]*1e3, ls=estilo, label=f"R{n} {etiqueta}")
            axs[1].plot(datos.angulo_grados, np.degrees(datos[f"inclinacion_r{n}_rad"]), ls=estilo, label=f"R{n} {etiqueta}")
    axs[0].set(ylabel="Desplazamiento central [mm]"); axs[1].set(xlabel="Ángulo [°]", ylabel="Inclinación [°]")
    for ax in axs: ax.grid(alpha=.25); ax.legend(ncol=2, fontsize=8)
    fig.suptitle("Respuesta cinemática acoplada"); _guardar(fig, ruta)


def historial_convergencia(historia: pd.DataFrame, ruta: Path) -> None:
    pasos = [0, int(historia.groupby("paso").iteracion.max().idxmax())]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
    for p in dict.fromkeys(pasos):
        d = historia[historia.paso == p]
        axs[0].semilogy(d.iteracion, d.residuo_compatibilidad_m*1e3, "o-", label=f"paso {p}")
        axs[1].semilogy(d.iteracion, d.cambio_fuerza_relativo, "o-", label=f"paso {p}")
    axs[0].axhline(1e-6, color="k", ls=":"); axs[0].set(ylabel="Residuo [mm]", xlabel="Iteración")
    axs[1].axhline(1e-5, color="k", ls=":"); axs[1].set(ylabel="Cambio relativo de fuerza", xlabel="Iteración")
    for ax in axs: ax.grid(alpha=.25); ax.legend()
    fig.suptitle("Convergencia en instantes representativos/críticos"); _guardar(fig, ruta)


def perfil_radial_critico(serie: pd.DataFrame, ruta: Path) -> None:
    fila = serie.loc[serie.fuerza_total_n.idxmax()]
    r = np.linspace(*PARAMETROS.limite_radial_rodillo_m, 300)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    for n in (1, 2):
        signo = -1 if n == 1 else 1
        g = fila[f"holgura_centro_r{n}_m"] + signo*fila[f"inclinacion_r{n}_rad"]*(r-PARAMETROS.centro_radial_rodillo_m)
        lc = longitud_contacto_desde_holgura(g, PARAMETROS.diametro_rodillo_m, PARAMETROS.espesor_biomasa_m)
        axs[0].plot(r*1e3, g*1e3, label=f"R{n}"); axs[1].plot(r*1e3, lc*1e3, label=f"R{n}")
    axs[0].set(xlabel="Radio [mm]", ylabel="Holgura [mm]"); axs[1].set(xlabel="Radio [mm]", ylabel="Longitud de contacto [mm]")
    for ax in axs: ax.grid(alpha=.25); ax.legend()
    fig.suptitle(f"Perfil radial en máxima fuerza, θ={fila.angulo_grados:.2f}°")
    _guardar(fig, ruta)


def superposicion_critica(detalle: pd.DataFrame, serie: pd.DataFrame, ruta: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    area_disco = np.pi*(PARAMETROS.diametro_agujero_m/2)**2
    fila = serie.loc[serie.fuerza_total_n.idxmax()]
    r = np.linspace(*PARAMETROS.limite_radial_rodillo_m, 300)
    for n, ax in enumerate(axs, 1):
        d = detalle[detalle.rodillo == n]; frac = d.area_superpuesta_m2/area_disco
        ax.scatter(d.radial_m*1e3, d.tangencial_m*1e3, c=frac, s=15+70*frac, cmap="viridis", vmin=0, vmax=1)
        signo = -1 if n == 1 else 1
        g = fila[f"holgura_centro_r{n}_m"] + signo*fila[f"inclinacion_r{n}_rad"]*(r-PARAMETROS.centro_radial_rodillo_m)
        lc = longitud_contacto_desde_holgura(g, PARAMETROS.diametro_rodillo_m, PARAMETROS.espesor_biomasa_m)
        ax.plot(r*1e3, lc*500, color="tab:red"); ax.plot(r*1e3, -lc*500, color="tab:red")
        ax.set(title=f"Rodillo {n}", xlabel="Radio [mm]"); ax.grid(alpha=.2)
    axs[0].set_ylabel("Coordenada tangencial [mm]")
    fig.suptitle("Superposición y frontera deformada en máxima fuerza")
    _guardar(fig, ruta)
