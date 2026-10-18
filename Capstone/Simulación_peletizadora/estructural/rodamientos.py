"""Cargas y vida básica de los cuatro rodamientos internos de los rodillos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import numpy as np
import pandas as pd

from config import PARAMETROS
from .acoplamiento import tabla_rodamientos_desde_serie
from .cargas_eje import cargas_peso_rodillos, caso_constante_conservador, repartir_entre_rodamientos
from .config_eje import ConfiguracionEje


@dataclass(frozen=True)
class ConfiguracionRodamiento:
    designacion_diseno: str = "6206-2RS"
    modelo_referencia: str = "FAG 6206-2RSR"
    fabricante: str = "FAG / Schaeffler"
    tipo: str = "rígido de bolas, una hilera, doble sellado"
    diametro_interior_m: float = .030
    diametro_exterior_m: float = .062
    ancho_m: float = .016
    capacidad_dinamica_n: float = 20_700.0
    capacidad_estatica_n: float = 11_300.0
    velocidad_limite_rpm: float = 6_700.0
    fuente: str = "fag_6206_2rsr_rs_2026"
    url: str = "https://es.rs-online.com/web/p/rodamientos-de-bolas/0311952"

    def como_dict(self) -> dict:
        return asdict(self)


RODAMIENTO_FAG = ConfiguracionRodamiento()
RODAMIENTO_KOYO = ConfiguracionRodamiento(
    modelo_referencia="KOYO/JTEKT 6206 2RS",
    fabricante="KOYO / JTEKT",
    capacidad_dinamica_n=24_300.0,
    velocidad_limite_rpm=7_000.0,
    fuente="koyo_jtekt_6206_2rs_2026",
    url="https://koyo.jtekt.co.jp/en/products/detail/print.php?pno=6206+2RS",
)
CONFIG_RODAMIENTO = RODAMIENTO_KOYO
ALTERNATIVAS_RODAMIENTO = (RODAMIENTO_FAG, RODAMIENTO_KOYO)
OBJETIVOS_VIDA_H = (5_000.0, 8_000.0, 10_000.0, 20_000.0)


def velocidad_rodillo_rpm(
    rpm_matriz: float, radio_contacto_m: float, radio_rodillo_m: float,
    factor_deslizamiento: float = 1.0,
) -> float:
    if rpm_matriz < 0 or radio_contacto_m <= 0 or radio_rodillo_m <= 0 or factor_deslizamiento < 0:
        raise ValueError("Parámetros de velocidad no válidos")
    return rpm_matriz*radio_contacto_m/radio_rodillo_m*factor_deslizamiento


def carga_radial_resultante(vertical_n, horizontal_n) -> np.ndarray:
    return np.hypot(np.asarray(vertical_n, dtype=float), np.asarray(horizontal_n, dtype=float))


def carga_dinamica_equivalente(cargas_n, pesos_revoluciones=None) -> float:
    cargas = np.asarray(cargas_n, dtype=float)
    if np.any(cargas < 0) or cargas.size == 0:
        raise ValueError("Las cargas radiales deben ser no negativas y no vacías")
    if pesos_revoluciones is None:
        pesos = np.ones_like(cargas)
    else:
        pesos = np.asarray(pesos_revoluciones, dtype=float)
        if pesos.shape != cargas.shape or np.any(pesos < 0) or pesos.sum() <= 0:
            raise ValueError("Pesos de revoluciones no válidos")
    return float(np.sum(cargas**3*pesos)/np.sum(pesos))**(1/3)


def vida_l10_millones(capacidad_dinamica_n: float, carga_equivalente_n: float) -> float:
    if capacidad_dinamica_n <= 0 or carga_equivalente_n <= 0:
        raise ValueError("C y P deben ser positivos")
    return (capacidad_dinamica_n/carga_equivalente_n)**3


def vida_l10_horas(l10_millones: float, rpm: float) -> float:
    if l10_millones < 0 or rpm <= 0:
        raise ValueError("L10 y rpm deben ser válidos")
    return 1e6*l10_millones/(60*rpm)


def factor_estatico(capacidad_estatica_n: float, carga_estatica_max_n: float) -> float:
    if capacidad_estatica_n <= 0 or carga_estatica_max_n <= 0:
        raise ValueError("C0 y P0 deben ser positivos")
    return capacidad_estatica_n/carga_estatica_max_n


def _nombres_y_posiciones(config: ConfiguracionEje):
    return (
        ("R1_A", 1, "a", config.rodamientos_izquierdos_m[0]),
        ("R1_B", 1, "b", config.rodamientos_izquierdos_m[1]),
        ("R2_A", 2, "a", config.rodamientos_derechos_m[0]),
        ("R2_B", 2, "b", config.rodamientos_derechos_m[1]),
    )


def cargas_rodamientos_3c(serie_3c: pd.DataFrame, config: ConfiguracionEje) -> pd.DataFrame:
    tabla = tabla_rodamientos_desde_serie(serie_3c, config)
    pesos = cargas_peso_rodillos(config)
    filas = []
    for nombre, rodillo, letra, x in _nombres_y_posiciones(config):
        vertical_comp = tabla[f"compactacion_r{rodillo}_rodamiento_{letra}_n"].to_numpy()
        horizontal = tabla[f"tangencial_r{rodillo}_rodamiento_{letra}_n"].to_numpy()
        peso = pesos[x]
        vertical = vertical_comp+peso
        radial = carga_radial_resultante(vertical, horizontal)
        filas.append(pd.DataFrame({
            "caso": "3C_inclinacion", "rodamiento": nombre, "rodillo": rodillo,
            "posicion_x_m": x, "tiempo_s": serie_3c.tiempo_s.to_numpy(),
            "angulo_grados": serie_3c.angulo_grados.to_numpy(),
            "carga_vertical_compactacion_n": vertical_comp,
            "carga_vertical_peso_n": peso, "carga_vertical_total_n": vertical,
            "carga_horizontal_n": horizontal, "carga_axial_n": 0.0,
            "carga_radial_resultante_n": radial, "carga_dinamica_instantanea_n": radial,
        }))
    return pd.concat(filas, ignore_index=True)


def cargas_rodamientos_conservadoras(config: ConfiguracionEje) -> pd.DataFrame:
    caso = caso_constante_conservador(config); pesos = cargas_peso_rodillos(config); filas = []
    for nombre, rodillo, letra, x in _nombres_y_posiciones(config):
        rodamientos = config.rodamientos_izquierdos_m if rodillo == 1 else config.rodamientos_derechos_m
        reparto = repartir_entre_rodamientos(
            caso[f"fuerza_rodillo_{rodillo}_n"], caso[f"x_resultante_rodillo_{rodillo}_m"], *rodamientos
        )
        fcomp = float(reparto.reaccion_a_n if letra == "a" else reparto.reaccion_b_n)
        signo = 1 if rodillo == 1 else -1
        horizontal = signo*PARAMETROS.coeficiente_resistencia_tangencial*fcomp
        vertical = fcomp+pesos[x]
        filas.append({"caso": "3A_D_conservador_artificial", "rodamiento": nombre,
                      "rodillo": rodillo, "posicion_x_m": x,
                      "carga_vertical_compactacion_n": fcomp, "carga_vertical_peso_n": pesos[x],
                      "carga_vertical_total_n": vertical, "carga_horizontal_n": horizontal,
                      "carga_axial_n": 0.0,
                      "carga_radial_resultante_n": math.hypot(vertical, horizontal),
                      "carga_dinamica_instantanea_n": math.hypot(vertical, horizontal)})
    return pd.DataFrame(filas)


def resumen_rodamientos(
    cargas: pd.DataFrame, config_rodamiento: ConfiguracionRodamiento,
    rpm_rodillo: float,
) -> pd.DataFrame:
    filas = []
    for nombre, g in cargas.groupby("rodamiento", sort=False):
        radial = g.carga_radial_resultante_n.to_numpy(); peq = carga_dinamica_equivalente(radial)
        imax = int(np.argmax(radial)); l10 = vida_l10_millones(config_rodamiento.capacidad_dinamica_n, peq)
        filas.append({"rodamiento": nombre, "caso": g.caso.iloc[0],
                      "modelo": config_rodamiento.modelo_referencia,
                      "seleccionado": config_rodamiento == CONFIG_RODAMIENTO,
                      "carga_radial_min_n": float(radial.min()), "carga_radial_media_n": float(radial.mean()),
                      "carga_radial_max_n": float(radial.max()), "carga_dinamica_equivalente_n": peq,
                      "tiempo_carga_max_s": (float(g.iloc[imax].tiempo_s) if "tiempo_s" in g else math.nan),
                      "angulo_carga_max_grados": (float(g.iloc[imax].angulo_grados) if "angulo_grados" in g else math.nan),
                      "l10_millones_revoluciones": l10, "l10_horas": vida_l10_horas(l10, rpm_rodillo),
                      "factor_estatico_s0": factor_estatico(config_rodamiento.capacidad_estatica_n, float(radial.max())),
                      "rpm_rodillo": rpm_rodillo})
    return pd.DataFrame(filas)


def sensibilidad_vida(
    resumen_nominal: pd.DataFrame, config: ConfiguracionRodamiento,
    rpm_base: float,
) -> pd.DataFrame:
    filas = []
    for _, r in resumen_nominal.iterrows():
        for factor_carga in (.8, 1.0, 1.2, 1.5):
            for factor_velocidad in (.9, 1.0, 1.1):
                for factor_deslizamiento in (.9, 1.0, 1.1):
                    for factor_capacidad in (.9, 1.0, 1.1):
                        peq = r.carga_dinamica_equivalente_n*factor_carga
                        rpm = rpm_base*factor_velocidad*factor_deslizamiento
                        c = config.capacidad_dinamica_n*factor_capacidad
                        l10 = vida_l10_millones(c, peq)
                        filas.append({"rodamiento": r.rodamiento, "factor_carga": factor_carga,
                                      "factor_velocidad": factor_velocidad,
                                      "factor_deslizamiento_cinematico": factor_deslizamiento,
                                      "factor_capacidad_dinamica": factor_capacidad,
                                      "carga_equivalente_n": peq, "rpm": rpm,
                                      "capacidad_dinamica_n": c, "l10_horas": vida_l10_horas(l10, rpm)})
    return pd.DataFrame(filas)


def capacidad_requerida_para_vida(peq_n: float, rpm: float, objetivo_horas: float) -> float:
    if min(peq_n, rpm, objetivo_horas) <= 0:
        raise ValueError("Los parámetros deben ser positivos")
    return peq_n*(60*rpm*objetivo_horas/1e6)**(1/3)
