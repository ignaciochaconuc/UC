"""Posproceso cinemático de rodillos rígidos y holgura respecto de la matriz."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .analisis import ResultadoCaso
from .config_eje import ConfiguracionEje
from .viga_eb import SistemaViga


@dataclass(frozen=True)
class GeometriaRodilloAxial:
    nombre: str
    x_izquierdo_m: float
    x_derecho_m: float
    x_centro_m: float
    x_rodamiento_a_m: float
    x_rodamiento_b_m: float

    @property
    def ancho_m(self) -> float:
        return self.x_derecho_m - self.x_izquierdo_m


def geometria_rodillos(config: ConfiguracionEje) -> tuple[GeometriaRodilloAxial, ...]:
    return (
        GeometriaRodilloAxial("izquierdo", .0515, .0915, config.centro_rodillo_izquierdo_m,
                              *config.rodamientos_izquierdos_m),
        GeometriaRodilloAxial("derecho", .1785, .2185, config.centro_rodillo_derecho_m,
                              *config.rodamientos_derechos_m),
    )


def cinematica_lineal_rodillo(
    valor_a: np.ndarray | float, valor_b: np.ndarray | float, geo: GeometriaRodilloAxial
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Centro, inclinación y valores extrapolados a ambos extremos."""
    a = np.asarray(valor_a, dtype=float); b = np.asarray(valor_b, dtype=float)
    centro = (a+b)/2
    inclinacion = (b-a)/(geo.x_rodamiento_b_m-geo.x_rodamiento_a_m)
    izquierdo = centro + inclinacion*(geo.x_izquierdo_m-geo.x_centro_m)
    derecho = centro + inclinacion*(geo.x_derecho_m-geo.x_centro_m)
    return centro, inclinacion, izquierdo, derecho


def interpolar_viga_hermite(
    sistema: SistemaViga, desplazamientos: np.ndarray, x_m: float
) -> tuple[np.ndarray, np.ndarray]:
    """Retorna desplazamiento y giro FEM en x para todos los casos/instantes."""
    u = np.asarray(desplazamientos, dtype=float)
    if u.ndim == 1:
        u = u[:, None]
    coincidencias = np.flatnonzero(np.isclose(sistema.nodos_m, x_m, atol=1e-12, rtol=0))
    if len(coincidencias):
        n = int(coincidencias[0])
        return u[2*n].copy(), u[2*n+1].copy()
    e = int(np.searchsorted(sistema.nodos_m, x_m) - 1)
    if e < 0 or e >= len(sistema.longitudes):
        raise ValueError(f"x={x_m} m queda fuera del eje")
    x1 = sistema.nodos_m[e]; L = sistema.longitudes[e]; xi = (x_m-x1)/L
    N = np.array((1-3*xi**2+2*xi**3, L*(xi-2*xi**2+xi**3),
                  3*xi**2-2*xi**3, L*(-xi**2+xi**3)))
    dN = np.array(((-6*xi+6*xi**2)/L, 1-4*xi+3*xi**2,
                   (6*xi-6*xi**2)/L, -2*xi+3*xi**2))
    gdl = [2*e, 2*e+1, 2*e+2, 2*e+3]
    return N @ u[gdl], dN @ u[gdl]


def desplazamientos_rodamientos(
    casos: dict[str, ResultadoCaso], sistema: SistemaViga
) -> pd.DataFrame:
    filas = []
    posiciones = {
        "izquierdo_a": sistema.config.rodamientos_izquierdos_m[0],
        "izquierdo_b": sistema.config.rodamientos_izquierdos_m[1],
        "derecho_a": sistema.config.rodamientos_derechos_m[0],
        "derecho_b": sistema.config.rodamientos_derechos_m[1],
    }
    for clave, caso in casos.items():
        datos: dict[str, np.ndarray] = {
            "caso": np.repeat(clave, len(caso.tiempos_s)),
            "tiempo_s": caso.tiempos_s,
            "angulo_grados": caso.angulos_grados,
        }
        for nombre, x in posiciones.items():
            v, tv = interpolar_viga_hermite(sistema, caso.solucion_vertical.desplazamientos, x)
            w, tw = interpolar_viga_hermite(sistema, caso.solucion_horizontal.desplazamientos, x)
            datos[f"v_{nombre}_m"] = v; datos[f"w_{nombre}_m"] = w
            datos[f"giro_vertical_{nombre}_rad"] = tv
            datos[f"giro_horizontal_{nombre}_rad"] = tw
        filas.append(pd.DataFrame(datos))
    return pd.concat(filas, ignore_index=True)


def calcular_cinematica_y_holgura(
    casos: dict[str, ResultadoCaso], sistema: SistemaViga, holgura_nominal_m: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cinematica: list[pd.DataFrame] = []
    holguras: list[pd.DataFrame] = []
    for clave, caso in casos.items():
        for geo in geometria_rodillos(sistema.config):
            va, tva = interpolar_viga_hermite(sistema, caso.solucion_vertical.desplazamientos, geo.x_rodamiento_a_m)
            vb, tvb = interpolar_viga_hermite(sistema, caso.solucion_vertical.desplazamientos, geo.x_rodamiento_b_m)
            wa, twa = interpolar_viga_hermite(sistema, caso.solucion_horizontal.desplazamientos, geo.x_rodamiento_a_m)
            wb, twb = interpolar_viga_hermite(sistema, caso.solucion_horizontal.desplazamientos, geo.x_rodamiento_b_m)
            veje, tveje = interpolar_viga_hermite(sistema, caso.solucion_vertical.desplazamientos, geo.x_centro_m)
            weje, tweje = interpolar_viga_hermite(sistema, caso.solucion_horizontal.desplazamientos, geo.x_centro_m)
            vc, av, vizq, vder = cinematica_lineal_rodillo(va, vb, geo)
            wc, ah, wizq, wder = cinematica_lineal_rodillo(wa, wb, geo)
            base = {
                "caso": np.repeat(clave, len(caso.tiempos_s)), "rodillo": np.repeat(geo.nombre, len(caso.tiempos_s)),
                "tiempo_s": caso.tiempos_s, "angulo_grados": caso.angulos_grados,
            }
            cinematica.append(pd.DataFrame({**base,
                "x_extremo_izquierdo_m": geo.x_izquierdo_m, "x_centro_m": geo.x_centro_m,
                "x_extremo_derecho_m": geo.x_derecho_m,
                "v_rodamiento_a_m": va, "v_rodamiento_b_m": vb,
                "w_rodamiento_a_m": wa, "w_rodamiento_b_m": wb,
                "giro_eje_vertical_a_rad": tva, "giro_eje_vertical_b_rad": tvb,
                "giro_eje_horizontal_a_rad": twa, "giro_eje_horizontal_b_rad": twb,
                "v_centro_rodillo_m": vc, "w_centro_rodillo_m": wc,
                "v_eje_centro_interpolado_m": veje, "w_eje_centro_interpolado_m": weje,
                "giro_eje_vertical_centro_rad": tveje, "giro_eje_horizontal_centro_rad": tweje,
                "inclinacion_vertical_rad": av, "inclinacion_vertical_grados": np.degrees(av),
                "inclinacion_horizontal_rad": ah, "inclinacion_horizontal_grados": np.degrees(ah),
                "v_extremo_izquierdo_m": vizq, "v_extremo_derecho_m": vder,
                "w_extremo_izquierdo_m": wizq, "w_extremo_derecho_m": wder,
                "diferencia_altura_extremos_m": vder-vizq,
            }))
            g_izq = holgura_nominal_m + vizq; g_c = holgura_nominal_m + vc; g_der = holgura_nominal_m + vder
            matriz_g = np.column_stack((g_izq, g_c, g_der))
            idx_min = np.argmin(matriz_g, axis=1); idx_max = np.argmax(matriz_g, axis=1)
            zonas = np.array(("extremo_izquierdo", "centro", "extremo_derecho"))
            holguras.append(pd.DataFrame({**base,
                "holgura_nominal_m": holgura_nominal_m,
                "holgura_extremo_izquierdo_m": g_izq, "holgura_centro_m": g_c,
                "holgura_extremo_derecho_m": g_der,
                "holgura_minima_m": np.min(matriz_g, axis=1), "zona_holgura_minima": zonas[idx_min],
                "holgura_maxima_m": np.max(matriz_g, axis=1), "zona_holgura_maxima": zonas[idx_max],
                "variacion_minima_vs_nominal_m": np.min(matriz_g, axis=1)-holgura_nominal_m,
                "variacion_maxima_vs_nominal_m": np.max(matriz_g, axis=1)-holgura_nominal_m,
                "incompatibilidad_holgura_negativa": np.min(matriz_g, axis=1) < 0,
            }))
    return pd.concat(cinematica, ignore_index=True), pd.concat(holguras, ignore_index=True)


def resumen_holgura(cinematica: pd.DataFrame, holguras: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for (caso, rodillo), c in cinematica.groupby(["caso", "rodillo"], sort=False):
        h = holguras[(holguras.caso == caso) & (holguras.rodillo == rodillo)]
        metricas = {
            "v_centro_max": c.v_centro_rodillo_m.idxmax(), "v_centro_min": c.v_centro_rodillo_m.idxmin(),
            "inclinacion_abs_max": c.inclinacion_vertical_rad.abs().idxmax(),
            "diferencia_altura_abs_max": c.diferencia_altura_extremos_m.abs().idxmax(),
            "holgura_min": h.holgura_minima_m.idxmin(), "holgura_max": h.holgura_maxima_m.idxmax(),
        }
        fila: dict[str, object] = {"caso": caso, "rodillo": rodillo}
        for nombre, indice in metricas.items():
            fuente = h if nombre.startswith("holgura") else c
            columna = {"v_centro_max": "v_centro_rodillo_m", "v_centro_min": "v_centro_rodillo_m",
                       "inclinacion_abs_max": "inclinacion_vertical_rad",
                       "diferencia_altura_abs_max": "diferencia_altura_extremos_m",
                       "holgura_min": "holgura_minima_m", "holgura_max": "holgura_maxima_m"}[nombre]
            valor = float(fuente.loc[indice, columna])
            fila[f"{nombre}_valor"] = abs(valor) if "abs" in nombre else valor
            fila[f"{nombre}_tiempo_s"] = float(fuente.loc[indice, "tiempo_s"])
            fila[f"{nombre}_angulo_grados"] = float(fuente.loc[indice, "angulo_grados"])
            if nombre.startswith("holgura"):
                fila[f"{nombre}_zona"] = fuente.loc[indice, "zona_holgura_minima" if nombre == "holgura_min" else "zona_holgura_maxima"]
        for zona, columna in (
            ("extremo_izquierdo", "holgura_extremo_izquierdo_m"),
            ("centro", "holgura_centro_m"),
            ("extremo_derecho", "holgura_extremo_derecho_m"),
        ):
            for extremo, funcion in (("min", h[columna].idxmin), ("max", h[columna].idxmax)):
                indice = funcion()
                fila[f"holgura_{zona}_{extremo}_m"] = float(h.loc[indice, columna])
                fila[f"holgura_{zona}_{extremo}_tiempo_s"] = float(h.loc[indice, "tiempo_s"])
                fila[f"holgura_{zona}_{extremo}_angulo_grados"] = float(h.loc[indice, "angulo_grados"])
        fila["existe_holgura_negativa"] = bool(h.incompatibilidad_holgura_negativa.any())
        filas.append(fila)
    return pd.DataFrame(filas)
