"""Reconstrucción de tensiones, resistencia estática y fatiga del eje."""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

from .analisis import ResultadoCaso
from .config_eje import ConfiguracionEje
from .viga_eb import SistemaViga


@dataclass(frozen=True)
class SeccionCritica:
    nombre: str
    x_m: float
    lado: str
    diametro_m: float
    tipo: str
    incertidumbre: str


@dataclass(frozen=True)
class EscenarioMaterial:
    nombre: str
    sy_pa: float | None
    sut_pa: float | None
    se_corregido_pa: float | None
    descripcion: str
    factor_superficie: float | None = None
    factor_tamano: float | None = None
    factor_carga: float | None = None
    factor_temperatura: float | None = None
    factor_confiabilidad: float | None = None
    factor_miscelaneo: float | None = None
    material: str = "AISI 4140"
    fabricante: str | None = None
    variante: str | None = None
    fuente: str | None = None
    metodo_se: str = "directo"
    acabado_superficial: str | None = None
    confiabilidad_porcentaje: float | None = None


@dataclass(frozen=True)
class EscenarioEntalla:
    nombre: str
    kt: float
    q: float
    descripcion: str

    @property
    def kf(self) -> float:
        return 1 + self.q*(self.kt-1)


MATERIALES = (
    EscenarioMaterial("no_especificado", None, None, None,
                      "Condición real pendiente; no se calculan factores de seguridad."),
    EscenarioMaterial("parametrico_bajo", 415e6, 655e6, 180e6,
                      "Escenario ilustrativo bajo; no identifica el tratamiento real."),
    EscenarioMaterial("parametrico_medio", 655e6, 850e6, 260e6,
                      "Escenario ilustrativo intermedio; requiere certificación."),
    EscenarioMaterial("parametrico_alto", 950e6, 1050e6, 330e6,
                      "Escenario ilustrativo alto; no debe asumirse sin tratamiento certificado."),
)

MATERIAL_OVAKO = EscenarioMaterial(
    "ovako_4140_qt_documentado", 940e6, 1040e6, None,
    "Referencia documentada de diseño; Se y certificado del material real pendientes.",
    material="SAE 4140 +QT", fabricante="Ovako", variante="6115",
    fuente="ovako_4140_qt_2026", metodo_se="sin_definir",
)

_FACTORES_CONFIABILIDAD = {90.0: .897, 95.0: .868, 99.0: .814}
_ACABADOS_MARIN = {
    "rectificado": (1.58, -.085),
    "mecanizado": (4.51, -.265),
    "laminado_caliente": (57.7, -.718),
}


def escenarios_ovako_marin() -> tuple[EscenarioMaterial, ...]:
    """Escenarios de acabado/confiabilidad; ninguno representa el dato real."""
    salida = []
    for acabado in _ACABADOS_MARIN:
        for confiabilidad in _FACTORES_CONFIABILIDAD:
            salida.append(EscenarioMaterial(
                f"ovako_qt_{acabado}_R{int(confiabilidad)}", 940e6, 1040e6, None,
                "Estimación Marin; acabado y confiabilidad son hipótesis de sensibilidad.",
                factor_carga=1.0, factor_temperatura=1.0, factor_miscelaneo=1.0,
                material="SAE 4140 +QT", fabricante="Ovako", variante="6115",
                fuente="ovako_4140_qt_2026", metodo_se="marin",
                acabado_superficial=acabado, confiabilidad_porcentaje=confiabilidad,
            ))
    return tuple(salida)


MATERIALES_ANALISIS = (*MATERIALES, MATERIAL_OVAKO, *escenarios_ovako_marin())


def factores_marin(material: EscenarioMaterial, diametro_m: float) -> dict[str, float]:
    """Factores de Marin según Shigley; Sut en MPa y diámetro efectivo en mm."""
    if material.metodo_se != "marin" or material.sut_pa is None:
        raise ValueError("El escenario no define una estimación Marin")
    sut_mpa = material.sut_pa/1e6; d_mm = diametro_m*1e3
    if sut_mpa > 1400:
        raise ValueError("Sut queda fuera del dominio adoptado para Se'=0,5 Sut")
    a, b = _ACABADOS_MARIN[material.acabado_superficial]
    ka = a*sut_mpa**b
    if 2.79 <= d_mm <= 51:
        kb = 1.24*d_mm**-.107
    elif 51 < d_mm <= 254:
        kb = 1.51*d_mm**-.157
    else:
        raise ValueError("Diámetro fuera del dominio del factor de tamaño adoptado")
    return {"se_prima_pa": .5*material.sut_pa, "ka": ka, "kb": kb,
            "kc": material.factor_carga or 1.0, "kd": material.factor_temperatura or 1.0,
            "ke": _FACTORES_CONFIABILIDAD[material.confiabilidad_porcentaje],
            "k_misc": material.factor_miscelaneo or 1.0}


def limite_fatiga_efectivo(material: EscenarioMaterial, diametro_m: float | None = None) -> float | None:
    if material.metodo_se == "marin":
        if diametro_m is None:
            raise ValueError("Marin requiere el diámetro de la sección")
        f = factores_marin(material, diametro_m)
        return float(np.prod(list(f.values())))
    return material.se_corregido_pa

ENTALLAS = (
    EscenarioEntalla("nominal_sin_concentracion", 1.0, 0.0,
                     "Solo tensión nominal del diámetro FEM."),
    EscenarioEntalla("sensibilidad_moderada", 1.5, 0.70,
                     "Barrido paramétrico: Kt=1,5 y q=0,70; no calibrado a la geometría final."),
    EscenarioEntalla("sensibilidad_alta", 2.5, 0.90,
                     "Barrido paramétrico: Kt=2,5 y q=0,90; envolvente local no validada."),
)


def secciones_criticas(config: ConfiguracionEje) -> tuple[SeccionCritica, ...]:
    dr = config.diametro_equivalente_rosca_m
    return (
        SeccionCritica("empotramiento_rosca_izquierda", 0.0, "derecha", dr, "rosca",
                       "Distribución local del empotramiento y raíz de rosca no validada."),
        SeccionCritica("fin_rosca_izquierda", .0290, "izquierda", dr, "rosca_transicion",
                       "Radio/acuerdo y geometría real de rosca pendientes."),
        SeccionCritica("alivio_izquierdo_inicio", .0515, "derecha", .0292, "alivio",
                       "Radio del alivio no acotado inequívocamente."),
        SeccionCritica("alivio_izquierdo_fin", .0531, "izquierda", .0292, "alivio",
                       "Radio del alivio no acotado inequívocamente."),
        SeccionCritica("escalon_central_izquierdo", .0915, "izquierda", .0300, "escalon",
                       "Se muestra R1; falta confirmar acabado y radio efectivo."),
        SeccionCritica("escalon_central_derecho", .1785, "derecha", .0300, "escalon",
                       "Se muestra R1; falta confirmar acabado y radio efectivo."),
        SeccionCritica("alivio_derecho_inicio", .2169, "derecha", .0292, "alivio",
                       "Radio del alivio no acotado inequívocamente."),
        SeccionCritica("alivio_derecho_fin", .2185, "izquierda", .0292, "alivio",
                       "Radio del alivio no acotado inequívocamente."),
        SeccionCritica("inicio_rosca_derecha", .2410, "derecha", dr, "rosca_transicion",
                       "Radio/acuerdo y geometría real de rosca pendientes."),
        SeccionCritica("empotramiento_rosca_derecha", .2700, "izquierda", dr, "rosca",
                       "Distribución local del empotramiento y raíz de rosca no validada."),
    )


def _indice_extremo(sistema: SistemaViga, seccion: SeccionCritica) -> tuple[int, int]:
    if seccion.lado == "izquierda":
        candidatos = np.flatnonzero(np.isclose(sistema.nodos_m[1:], seccion.x_m, atol=1e-12))
        extremo = 1
    else:
        candidatos = np.flatnonzero(np.isclose(sistema.nodos_m[:-1], seccion.x_m, atol=1e-12))
        extremo = 0
    if not len(candidatos):
        raise ValueError(f"No hay elemento al lado {seccion.lado} de {seccion.x_m}")
    return int(candidatos[0]), extremo


def momentos_seccion(
    caso: ResultadoCaso, sistema: SistemaViga, seccion: SeccionCritica
) -> tuple[np.ndarray, np.ndarray]:
    e, extremo = _indice_extremo(sistema, seccion)
    return caso.momento_vertical_nm[e, extremo].copy(), caso.momento_horizontal_nm[e, extremo].copy()


def tension_flexion_punto(
    momento_vertical_nm: np.ndarray | float,
    momento_horizontal_nm: np.ndarray | float,
    diametro_m: float,
    angulo_superficie_rad: float,
) -> np.ndarray:
    """Tensión longitudinal firmada en un punto material fijo de la superficie."""
    mv = np.asarray(momento_vertical_nm, dtype=float)
    mh = np.asarray(momento_horizontal_nm, dtype=float)
    modulo_seccion = math.pi*diametro_m**3/32
    return (mv*math.cos(angulo_superficie_rad)+mh*math.sin(angulo_superficie_rad))/modulo_seccion


def _reversiones(historia: np.ndarray) -> np.ndarray:
    x = np.asarray(historia, dtype=float)
    if len(x) < 2 or np.allclose(x, x[0]):
        return np.array([x[0]])
    # Cierre periódico comenzando en el máximo para reducir medios ciclos espurios.
    inicio = int(np.argmax(x)); y = np.r_[x[inicio:], x[:inicio], x[inicio]]
    filtrada = [y[0]]
    for valor in y[1:]:
        if valor != filtrada[-1]: filtrada.append(valor)
    y = np.asarray(filtrada)
    rev = [y[0]]
    for i in range(1, len(y)-1):
        if (y[i]-y[i-1])*(y[i+1]-y[i]) <= 0: rev.append(y[i])
    rev.append(y[-1])
    return np.asarray(rev)


def contar_rainflow(historia: np.ndarray) -> pd.DataFrame:
    """Conteo rainflow de cuatro puntos para una historia periódica cerrada."""
    rev = _reversiones(historia)
    if len(rev) < 2:
        return pd.DataFrame(columns=["rango_pa", "amplitud_pa", "media_pa", "conteo"])
    pila: list[float] = []; ciclos: list[tuple[float, float, float]] = []
    for valor in rev:
        pila.append(float(valor))
        while len(pila) >= 3:
            x = abs(pila[-2]-pila[-3]); y = abs(pila[-1]-pila[-2])
            if y < x: break
            media = (pila[-3]+pila[-2])/2
            if len(pila) == 3:
                ciclos.append((x, media, .5)); pila.pop(0)
            else:
                ciclos.append((x, media, 1.0)); ultimo = pila.pop(); pila[-2:] = [ultimo]
    for a, b in zip(pila, pila[1:]):
        ciclos.append((abs(b-a), (a+b)/2, .5))
    return pd.DataFrame([{"rango_pa": r, "amplitud_pa": r/2, "media_pa": m, "conteo": c}
                         for r, m, c in ciclos if r > 0])


def factor_goodman(
    amplitud_nominal_pa: float, media_nominal_pa: float,
    material: EscenarioMaterial, entalla: EscenarioEntalla,
    diametro_m: float | None = None,
) -> float:
    se = limite_fatiga_efectivo(material, diametro_m)
    if se is None or material.sut_pa is None:
        return math.nan
    # Se omite el beneficio de una media compresiva: aproximación conservadora.
    inverso = entalla.kf*abs(amplitud_nominal_pa)/se
    inverso += entalla.kt*max(media_nominal_pa, 0.0)/material.sut_pa
    return math.inf if inverso == 0 else 1/inverso


def seleccionar_ciclo_goodman(
    ciclos_por_angulo: list[pd.DataFrame], material: EscenarioMaterial,
    entalla: EscenarioEntalla, diametro_m: float,
) -> tuple[float, int | None, pd.Series | None]:
    """Selecciona el ciclo gobernante para una combinación, sin reutilizar otra."""
    se = limite_fatiga_efectivo(material, diametro_m)
    if se is None or material.sut_pa is None:
        return math.nan, None, None
    validos = [(j, c) for j, c in enumerate(ciclos_por_angulo) if len(c)]
    if not validos:
        return math.nan, None, None
    amplitudes = np.concatenate([c.amplitud_pa.to_numpy() for _, c in validos])
    medias = np.concatenate([c.media_pa.to_numpy() for _, c in validos])
    indices_angulo = np.concatenate([np.full(len(c), j, dtype=int) for j, c in validos])
    indices_fila = np.concatenate([np.arange(len(c), dtype=int) for _, c in validos])
    inversos = entalla.kf*np.abs(amplitudes)/se
    inversos += entalla.kt*np.maximum(medias, 0.0)/material.sut_pa
    i = int(np.argmax(inversos)); j = int(indices_angulo[i])
    ciclo = ciclos_por_angulo[j].iloc[int(indices_fila[i])]
    return (math.inf if inversos[i] == 0 else float(1/inversos[i])), j, ciclo


def analizar_resistencia(
    casos: dict[str, ResultadoCaso], sistema: SistemaViga,
    numero_angulos: int = 72,
    materiales: tuple[EscenarioMaterial, ...] = MATERIALES_ANALISIS,
    entallas: tuple[EscenarioEntalla, ...] = ENTALLAS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna secciones, historiales y selección independiente por escenario."""
    angulos = np.linspace(0, 2*math.pi, numero_angulos, endpoint=False)
    resumen_nominal = []; historiales = []; ciclos_salida = []; sensibilidad = []
    nombre_representativo = "ovako_qt_mecanizado_R95"
    for nombre_caso, caso in casos.items():
        for seccion in secciones_criticas(sistema.config):
            mv, mh = momentos_seccion(caso, sistema, seccion)
            tensiones = np.vstack([tension_flexion_punto(mv, mh, seccion.diametro_m, phi) for phi in angulos])
            ciclos_por_angulo = [contar_rainflow(tensiones[j]) for j in range(len(angulos))]
            ind_abs = np.unravel_index(np.argmax(np.abs(tensiones)), tensiones.shape)
            sigma_nom_max = float(np.abs(tensiones[ind_abs])); phi_estatico = float(angulos[ind_abs[0]])
            representante: tuple[int, pd.Series] | None = None
            for material in materiales:
                se_efectivo = limite_fatiga_efectivo(material, seccion.diametro_m)
                fmarin = factores_marin(material, seccion.diametro_m) if material.metodo_se == "marin" else {}
                for entalla in entallas:
                    if len(caso.tiempos_s) > 1:
                        n_fat, mejor_j, mejor_ciclo = seleccionar_ciclo_goodman(
                            ciclos_por_angulo, material, entalla, seccion.diametro_m)
                    else:
                        n_fat, mejor_j, mejor_ciclo = math.nan, None, None
                    n_est = (material.sy_pa/(entalla.kt*sigma_nom_max)
                             if material.sy_pa is not None and sigma_nom_max > 0 else math.nan)
                    sensibilidad.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                         "material": material.nombre, "entalla": entalla.nombre,
                                         "fuente_material": material.fuente, "acabado_superficial": material.acabado_superficial,
                                         "confiabilidad_porcentaje": material.confiabilidad_porcentaje,
                                         "sy_pa": material.sy_pa, "sut_pa": material.sut_pa,
                                         "se_corregido_pa": se_efectivo, **fmarin,
                                         "kt": entalla.kt, "q": entalla.q, "kf": entalla.kf,
                                         "esfuerzo_nominal_max_pa": sigma_nom_max,
                                         "esfuerzo_local_estatico_pa": entalla.kt*sigma_nom_max,
                                         "von_mises_local_estimado_pa": entalla.kt*sigma_nom_max,
                                         "angulo_material_gobernante_rad": (float(angulos[mejor_j]) if mejor_j is not None else math.nan),
                                         "amplitud_nominal_gobernante_pa": (float(mejor_ciclo.amplitud_pa) if mejor_ciclo is not None else math.nan),
                                         "media_nominal_gobernante_pa": (float(mejor_ciclo.media_pa) if mejor_ciclo is not None else math.nan),
                                         "conteo_ciclo_gobernante": (float(mejor_ciclo.conteo) if mejor_ciclo is not None else math.nan),
                                         "factor_seguridad_fluencia": n_est,
                                         "factor_seguridad_goodman": n_fat})
                    if mejor_ciclo is not None:
                        ciclos_salida.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                              "material": material.nombre, "entalla": entalla.nombre,
                                              "angulo_material_rad": float(angulos[mejor_j]),
                                              **mejor_ciclo.to_dict(), "factor_seguridad_goodman": n_fat})
                    if material.nombre == nombre_representativo and entalla == ENTALLAS[1] and mejor_ciclo is not None:
                        representante = (mejor_j, mejor_ciclo)
            jcrit = representante[0] if representante else ind_abs[0]
            phi_fatiga = float(angulos[jcrit])
            resumen_nominal.append({"caso": nombre_caso, "seccion": seccion.nombre, "x_m": seccion.x_m,
                                    "lado": seccion.lado, "tipo": seccion.tipo, "diametro_m": seccion.diametro_m,
                                    "momento_resultante_max_nm": float(np.max(np.hypot(mv, mh))),
                                    "esfuerzo_nominal_max_pa": sigma_nom_max,
                                    "tiempo_esfuerzo_max_s": float(caso.tiempos_s[ind_abs[1]]),
                                    "angulo_carga_esfuerzo_max_grados": float(caso.angulos_grados[ind_abs[1]]),
                                    "angulo_material_estatico_rad": phi_estatico,
                                    "angulo_material_fatiga_representativo_rad": phi_fatiga,
                                    "sigma_min_pa": float(tensiones[jcrit].min()), "sigma_max_pa": float(tensiones[jcrit].max()),
                                    "sigma_media_extremos_pa": float((tensiones[jcrit].max()+tensiones[jcrit].min())/2),
                                    "sigma_alternante_extremos_pa": float((tensiones[jcrit].max()-tensiones[jcrit].min())/2),
                                    "incertidumbre": seccion.incertidumbre})
            for k in range(tensiones.shape[1]):
                historiales.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                    "tiempo_s": caso.tiempos_s[k], "angulo_carga_grados": caso.angulos_grados[k],
                                    "angulo_material_rad": phi_fatiga, "tension_nominal_pa": tensiones[jcrit, k]})
    return (pd.DataFrame(resumen_nominal), pd.DataFrame(historiales),
            pd.DataFrame(ciclos_salida), pd.DataFrame(sensibilidad))
