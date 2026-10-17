"""Equilibrio cuasiestático entre contacto geométrico y flexión del eje."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from cinematica import rotar
from config import PARAMETROS
from modelos.superposicion import coordenadas_locales
from modelos.superposicion_variable import interseccion_disco_huella_variable
from .cargas_eje import cargas_peso_rodillos, repartir_entre_rodamientos
from .config_eje import ConfiguracionEje
from .viga_eb import SistemaViga


@dataclass(frozen=True)
class ConfiguracionAcoplamiento:
    relajacion: float = .5
    tolerancia_holgura_m: float = 1e-9
    tolerancia_fuerza_relativa: float = 1e-5
    max_iteraciones: int = 100
    orden_cuadratura: int = 64

    def validar(self) -> None:
        if not 0 < self.relajacion <= 1:
            raise ValueError("La relajación debe pertenecer a (0,1]")
        if self.tolerancia_holgura_m <= 0 or self.tolerancia_fuerza_relativa <= 0:
            raise ValueError("Las tolerancias deben ser positivas")


@dataclass
class EstadoContacto:
    fuerza_n: float
    radial_m: float
    tangencial_m: float
    torque_nm: float
    areas_m2: np.ndarray
    centroides_r_m: np.ndarray
    centroides_t_m: np.ndarray


def _contacto_rodillo(
    locales: np.ndarray, radios_agujeros: np.ndarray, holgura_centro_m: float,
    inclinacion_global_rad: float, numero_rodillo: int, orden: int,
) -> EstadoContacto:
    orientacion = -1.0 if numero_rodillo == 1 else 1.0
    areas, cr, ct = interseccion_disco_huella_variable(
        locales, PARAMETROS.diametro_agujero_m/2, PARAMETROS.limite_radial_rodillo_m,
        holgura_centro_m, orientacion*inclinacion_global_rad,
        PARAMETROS.centro_radial_rodillo_m, PARAMETROS.diametro_rodillo_m,
        PARAMETROS.espesor_biomasa_m, orden,
    )
    fuerzas = PARAMETROS.presion_maxima_pa*areas; total = float(fuerzas.sum())
    positiva = fuerzas > 0
    if total:
        radial = float(np.sum(cr[positiva]*fuerzas[positiva])/total)
        tangencial = float(np.sum(ct[positiva]*fuerzas[positiva])/total)
    else:
        radial = PARAMETROS.centro_radial_rodillo_m; tangencial = 0.0
    torque = float(np.sum(PARAMETROS.coeficiente_resistencia_tangencial*fuerzas*radios_agujeros))
    return EstadoContacto(total, radial, tangencial, torque, areas, cr, ct)


def _base_pesos(sistema: SistemaViga) -> tuple[np.ndarray, np.ndarray]:
    vertical = sistema.cargas_vacias(1); sistema.agregar_peso_propio(vertical)
    for x, fuerza in cargas_peso_rodillos(sistema.config).items():
        sistema.agregar_carga_puntual(vertical, x, fuerza)
    return vertical, sistema.cargas_vacias(1)


def _resolver_estructura(
    sistema: SistemaViga, contactos: tuple[EstadoContacto, EstadoContacto]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vertical, horizontal = _base_pesos(sistema)
    fuerzas_rodamientos: list[float] = []
    for numero, (contacto, rodamientos) in enumerate(zip(
        contactos, (sistema.config.rodamientos_izquierdos_m, sistema.config.rodamientos_derechos_m), strict=True
    ), start=1):
        x_f = sistema.config.centro_matriz_m + (-contacto.radial_m if numero == 1 else contacto.radial_m)
        reparto = repartir_entre_rodamientos(contacto.fuerza_n, x_f, *rodamientos)
        signo_t = 1 if numero == 1 else -1
        for x, fuerza in zip(rodamientos, (float(reparto.reaccion_a_n), float(reparto.reaccion_b_n)), strict=True):
            sistema.agregar_carga_puntual(vertical, x, fuerza)
            sistema.agregar_carga_puntual(horizontal, x, signo_t*PARAMETROS.coeficiente_resistencia_tangencial*fuerza)
            fuerzas_rodamientos.append(fuerza)
    sv = sistema.resolver(vertical); sh = sistema.resolver(horizontal)
    estados = []
    for rodamientos in (sistema.config.rodamientos_izquierdos_m, sistema.config.rodamientos_derechos_m):
        ia, ib = (sistema.indice_nodo(x) for x in rodamientos)
        va, vb = sv.desplazamientos[2*ia, 0], sv.desplazamientos[2*ib, 0]
        estados.extend(((va+vb)/2, (vb-va)/(rodamientos[1]-rodamientos[0])))
    return np.asarray(estados), vertical[:, 0], horizontal[:, 0]


def _perfil_holgura(estado: np.ndarray, numero: int) -> np.ndarray:
    vc, alpha = estado[2*(numero-1):2*numero]
    # Coordenadas axiales globales: extremo izquierdo, centro y extremo derecho.
    if numero == 1:
        xs = np.array((.0515, .0715, .0915))
    else:
        xs = np.array((.1785, .1985, .2185))
    return PARAMETROS.separacion_minima_rodillo_matriz_m + vc + alpha*(xs-xs[1])


def simular_acoplado(
    coordenadas_iniciales_m: np.ndarray, sistema: SistemaViga, modo: str,
    config: ConfiguracionAcoplamiento = ConfiguracionAcoplamiento(),
    pasos: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Simula ``uniforme`` o ``inclinacion`` y retorna serie, historia y áreas críticas."""
    if modo not in {"uniforme", "inclinacion"}:
        raise ValueError("modo debe ser 'uniforme' o 'inclinacion'")
    config.validar(); n = pasos or PARAMETROS.pasos_por_revolucion
    tiempos = np.arange(n)*PARAMETROS.periodo_revolucion_s/PARAMETROS.pasos_por_revolucion
    radios = np.linalg.norm(coordenadas_iniciales_m, axis=1)
    estado = np.zeros(4); fuerza_anterior = np.full(2, np.nan)
    filas = []; historia = []; detalle_critico: list[dict] = []
    for paso, tiempo in enumerate(tiempos):
        angulo = PARAMETROS.omega_rad_s*tiempo; coords = rotar(coordenadas_iniciales_m, angulo)
        convergio = False; motivo = "max_iteraciones"
        for it in range(1, config.max_iteraciones+1):
            contactos = []
            for numero, ar in ((1, 0.0), (2, math.pi)):
                locales = coordenadas_locales(coords, ar)
                vc, alpha = estado[2*(numero-1):2*numero]
                gcentro = PARAMETROS.separacion_minima_rodillo_matriz_m+vc
                alpha_contacto = alpha if modo == "inclinacion" else 0.0
                contactos.append(_contacto_rodillo(locales, radios, gcentro, alpha_contacto, numero, config.orden_cuadratura))
            fuerzas = np.array([c.fuerza_n for c in contactos])
            calculado, _, _ = _resolver_estructura(sistema, tuple(contactos))
            if modo == "uniforme":
                calculado[[1, 3]] = 0.0
            perfiles = np.concatenate([_perfil_holgura(estado, 1), _perfil_holgura(estado, 2)])
            perfiles_calc = np.concatenate([_perfil_holgura(calculado, 1), _perfil_holgura(calculado, 2)])
            residuo = float(np.max(np.abs(perfiles_calc-perfiles)))
            actualizado = (1-config.relajacion)*estado + config.relajacion*calculado
            cambio = float(np.max(np.abs(np.concatenate([_perfil_holgura(actualizado, 1), _perfil_holgura(actualizado, 2)])-perfiles)))
            rel_f = (float(np.max(np.abs(fuerzas-fuerza_anterior)/np.maximum(np.abs(fuerzas), 1.0)))
                     if np.all(np.isfinite(fuerza_anterior)) else math.inf)
            historia.append({"modelo": modo, "paso": paso, "tiempo_s": tiempo,
                              "angulo_grados": math.degrees(angulo), "iteracion": it,
                              "residuo_compatibilidad_m": residuo, "cambio_holgura_m": cambio,
                              "cambio_fuerza_relativo": rel_f, "fuerza_r1_n": fuerzas[0], "fuerza_r2_n": fuerzas[1]})
            estado = actualizado; fuerza_anterior = fuerzas
            if residuo <= config.tolerancia_holgura_m and cambio <= config.tolerancia_holgura_m and rel_f <= config.tolerancia_fuerza_relativa:
                convergio = True; motivo = "convergido"; estado = calculado; break
        if not convergio:
            filas.append({"modelo": modo, "paso": paso, "tiempo_s": tiempo, "angulo_grados": math.degrees(angulo),
                          "convergio": False, "motivo": motivo, "iteraciones": config.max_iteraciones})
            # No usar una solución no convergida como inicio del siguiente instante.
            estado = np.zeros(4); fuerza_anterior[:] = np.nan
            continue
        # Recalcular contacto y cargas con el estado convergido exportado.
        contactos_finales = []
        for numero, ar in ((1, 0.0), (2, math.pi)):
            locales = coordenadas_locales(coords, ar); vc, alpha = estado[2*(numero-1):2*numero]
            contactos_finales.append(_contacto_rodillo(
                locales, radios, PARAMETROS.separacion_minima_rodillo_matriz_m+vc,
                alpha if modo == "inclinacion" else 0.0, numero, config.orden_cuadratura))
        estado_fisico, _, _ = _resolver_estructura(sistema, tuple(contactos_finales))
        torque = sum(c.torque_nm for c in contactos_finales)
        fila = {"modelo": modo, "paso": paso, "tiempo_s": tiempo, "angulo_grados": math.degrees(angulo),
                "convergio": True, "motivo": motivo, "iteraciones": it,
                "torque_resistente_nm": torque, "potencia_resistente_w": torque*PARAMETROS.omega_rad_s}
        for numero, c in enumerate(contactos_finales, 1):
            vc = estado_fisico[2*(numero-1)]
            alpha_fisica = estado_fisico[2*(numero-1)+1]
            perfil = _perfil_holgura(estado, numero)
            fila.update({f"fuerza_rodillo_{numero}_n": c.fuerza_n,
                         f"resultante_radial_r{numero}_m": c.radial_m,
                         f"resultante_tangencial_r{numero}_m": c.tangencial_m,
                         f"desplazamiento_centro_r{numero}_m": vc,
                         f"inclinacion_r{numero}_rad": alpha_fisica,
                         f"holgura_izquierda_r{numero}_m": perfil[0],
                         f"holgura_centro_r{numero}_m": perfil[1],
                         f"holgura_derecha_r{numero}_m": perfil[2],
                         f"holgura_minima_r{numero}_m": float(perfil.min()),
                         f"holgura_maxima_r{numero}_m": float(perfil.max())})
        fila["fuerza_total_n"] = sum(c.fuerza_n for c in contactos_finales)
        filas.append(fila)
    serie = pd.DataFrame(filas)
    # Detalle geométrico en el instante de máxima fuerza total.
    validas = serie[serie.get("convergio", False) == True]
    if len(validas):
        pcrit = int(validas.loc[validas.fuerza_total_n.idxmax(), "paso"])
        row = validas[validas.paso == pcrit].iloc[0]; coords = rotar(coordenadas_iniciales_m, 2*math.pi*pcrit/PARAMETROS.pasos_por_revolucion)
        for numero, ar in ((1, 0.0), (2, math.pi)):
            locales = coordenadas_locales(coords, ar)
            c = _contacto_rodillo(locales, radios, row[f"holgura_centro_r{numero}_m"],
                                  row[f"inclinacion_r{numero}_rad"] if modo == "inclinacion" else 0,
                                  numero, config.orden_cuadratura)
            for i in range(len(locales)):
                detalle_critico.append({"modelo": modo, "paso": pcrit, "rodillo": numero, "id_agujero": i+1,
                                        "radial_m": locales[i, 0], "tangencial_m": locales[i, 1],
                                        "area_superpuesta_m2": c.areas_m2[i], "centroide_radial_m": c.centroides_r_m[i],
                                        "centroide_tangencial_m": c.centroides_t_m[i]})
    return serie, pd.DataFrame(historia), pd.DataFrame(detalle_critico)


def tabla_rodamientos_desde_serie(serie: pd.DataFrame, config_eje: ConfiguracionEje) -> pd.DataFrame:
    """Convierte resultantes acopladas a las columnas estructurales estándar."""
    salida = serie[["tiempo_s", "angulo_grados"]].copy()
    for numero, rodamientos in ((1, config_eje.rodamientos_izquierdos_m), (2, config_eje.rodamientos_derechos_m)):
        f = serie[f"fuerza_rodillo_{numero}_n"].to_numpy()
        r = serie[f"resultante_radial_r{numero}_m"].to_numpy()
        x = config_eje.centro_matriz_m + (-r if numero == 1 else r)
        reparto = repartir_entre_rodamientos(f, x, *rodamientos)
        salida[f"compactacion_r{numero}_rodamiento_a_n"] = reparto.reaccion_a_n
        salida[f"compactacion_r{numero}_rodamiento_b_n"] = reparto.reaccion_b_n
        signo = 1 if numero == 1 else -1
        salida[f"tangencial_r{numero}_rodamiento_a_n"] = signo*PARAMETROS.coeficiente_resistencia_tangencial*reparto.reaccion_a_n
        salida[f"tangencial_r{numero}_rodamiento_b_n"] = signo*PARAMETROS.coeficiente_resistencia_tangencial*reparto.reaccion_b_n
    return salida


def resumen_modelo_acoplado(serie: pd.DataFrame, resultado_estructural) -> dict[str, float | str | bool]:
    """Resumen de contacto, holgura y respuesta estructural de una serie convergida."""
    fila: dict[str, float | str | bool] = {
        "modelo": str(serie.modelo.iloc[0]), "instantes": len(serie),
        "todos_convergieron": bool(serie.convergio.all()),
        "iteraciones_max": int(serie.iteraciones.max()),
        "fuerza_total_max_n": float(serie.fuerza_total_n.max()),
        "fuerza_total_media_n": float(serie.fuerza_total_n.mean()),
        "torque_max_nm": float(serie.torque_resistente_nm.max()),
        "torque_medio_nm": float(serie.torque_resistente_nm.mean()),
        "potencia_max_w": float(serie.potencia_resistente_w.max()),
        "potencia_media_w": float(serie.potencia_resistente_w.mean()),
        "momento_flector_max_nm": float(resultado_estructural.series.momento_max_nm.max()),
        "esfuerzo_nominal_max_pa": float(resultado_estructural.series.esfuerzo_nominal_max_pa.max()),
        "desplazamiento_eje_max_m": float(resultado_estructural.series.desplazamiento_max_m.max()),
    }
    for n in (1, 2):
        cols_g = [f"holgura_izquierda_r{n}_m", f"holgura_centro_r{n}_m", f"holgura_derecha_r{n}_m"]
        valores = serie[cols_g].to_numpy()
        fila.update({
            f"holgura_r{n}_min_m": float(valores.min()),
            f"holgura_r{n}_media_m": float(valores.mean()),
            f"holgura_r{n}_max_m": float(valores.max()),
            f"desplazamiento_centro_r{n}_min_m": float(serie[f"desplazamiento_centro_r{n}_m"].min()),
            f"desplazamiento_centro_r{n}_max_m": float(serie[f"desplazamiento_centro_r{n}_m"].max()),
            f"inclinacion_r{n}_abs_max_rad": float(serie[f"inclinacion_r{n}_rad"].abs().max()),
            f"diferencia_holgura_extremos_r{n}_max_m": float((serie[cols_g[2]]-serie[cols_g[0]]).abs().max()),
            f"fuerza_r{n}_max_n": float(serie[f"fuerza_rodillo_{n}_n"].max()),
            f"fuerza_r{n}_media_n": float(serie[f"fuerza_rodillo_{n}_n"].mean()),
        })
    return fila
