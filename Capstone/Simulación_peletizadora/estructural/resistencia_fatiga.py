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
) -> float:
    if material.se_corregido_pa is None or material.sut_pa is None:
        return math.nan
    # Se omite el beneficio de una media compresiva: aproximación conservadora.
    inverso = entalla.kf*abs(amplitud_nominal_pa)/material.se_corregido_pa
    inverso += entalla.kt*max(media_nominal_pa, 0.0)/material.sut_pa
    return math.inf if inverso == 0 else 1/inverso


def analizar_resistencia(
    casos: dict[str, ResultadoCaso], sistema: SistemaViga,
    numero_angulos: int = 72,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna secciones, historiales gobernantes, ciclos y sensibilidad."""
    angulos = np.linspace(0, 2*math.pi, numero_angulos, endpoint=False)
    resumen_nominal = []; historiales = []; ciclos_salida = []; sensibilidad = []
    for nombre_caso, caso in casos.items():
        for seccion in secciones_criticas(sistema.config):
            mv, mh = momentos_seccion(caso, sistema, seccion)
            tensiones = np.vstack([tension_flexion_punto(mv, mh, seccion.diametro_m, phi) for phi in angulos])
            ind_abs = np.unravel_index(np.argmax(np.abs(tensiones)), tensiones.shape)
            sigma_nom_max = float(np.abs(tensiones[ind_abs]))
            phi_estatico = float(angulos[ind_abs[0]])
            # Busca el punto material con el menor Goodman del escenario medio/moderado.
            candidatos = []
            for j, phi in enumerate(angulos):
                ciclos = contar_rainflow(tensiones[j])
                if len(ciclos):
                    factores = [factor_goodman(r.amplitud_pa, r.media_pa, MATERIALES[2], ENTALLAS[1]) for _, r in ciclos.iterrows()]
                    candidatos.append((min(factores), j, int(np.argmin(factores)), ciclos))
            if candidatos:
                _, jcrit, iciclo, ciclos_crit = min(candidatos, key=lambda z: z[0])
                phi_fatiga = float(angulos[jcrit]); ciclo_gob = ciclos_crit.iloc[iciclo]
            else:
                jcrit = ind_abs[0]; phi_fatiga = float(angulos[jcrit]); ciclos_crit = contar_rainflow(tensiones[jcrit])
                ciclo_gob = pd.Series({"amplitud_pa": 0., "media_pa": float(tensiones[jcrit, 0]), "conteo": 0.})
            resumen_nominal.append({"caso": nombre_caso, "seccion": seccion.nombre, "x_m": seccion.x_m,
                                    "lado": seccion.lado, "tipo": seccion.tipo, "diametro_m": seccion.diametro_m,
                                    "momento_resultante_max_nm": float(np.max(np.hypot(mv, mh))),
                                    "esfuerzo_nominal_max_pa": sigma_nom_max,
                                    "tiempo_esfuerzo_max_s": float(caso.tiempos_s[ind_abs[1]]),
                                    "angulo_carga_esfuerzo_max_grados": float(caso.angulos_grados[ind_abs[1]]),
                                    "angulo_material_estatico_rad": phi_estatico,
                                    "angulo_material_fatiga_rad": phi_fatiga,
                                    "sigma_min_pa": float(tensiones[jcrit].min()), "sigma_max_pa": float(tensiones[jcrit].max()),
                                    "sigma_media_extremos_pa": float((tensiones[jcrit].max()+tensiones[jcrit].min())/2),
                                    "sigma_alternante_extremos_pa": float((tensiones[jcrit].max()-tensiones[jcrit].min())/2),
                                    "incertidumbre": seccion.incertidumbre})
            for k in range(tensiones.shape[1]):
                historiales.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                    "tiempo_s": caso.tiempos_s[k], "angulo_carga_grados": caso.angulos_grados[k],
                                    "angulo_material_rad": phi_fatiga, "tension_nominal_pa": tensiones[jcrit, k]})
            for _, ciclo in ciclos_crit.iterrows():
                ciclos_salida.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                      "angulo_material_rad": phi_fatiga, **ciclo.to_dict()})
            for material in MATERIALES:
                for entalla in ENTALLAS:
                    n_est = (material.sy_pa/(entalla.kt*sigma_nom_max)
                             if material.sy_pa is not None and sigma_nom_max > 0 else math.nan)
                    n_fat = (factor_goodman(float(ciclo_gob.amplitud_pa), float(ciclo_gob.media_pa), material, entalla)
                             if len(caso.tiempos_s) > 1 else math.nan)
                    sensibilidad.append({"caso": nombre_caso, "seccion": seccion.nombre,
                                         "material": material.nombre, "entalla": entalla.nombre,
                                         "sy_pa": material.sy_pa, "sut_pa": material.sut_pa,
                                         "se_corregido_pa": material.se_corregido_pa,
                                         "kt": entalla.kt, "q": entalla.q, "kf": entalla.kf,
                                         "esfuerzo_nominal_max_pa": sigma_nom_max,
                                         "esfuerzo_local_estatico_pa": entalla.kt*sigma_nom_max,
                                         "von_mises_local_estimado_pa": entalla.kt*sigma_nom_max,
                                         "amplitud_nominal_gobernante_pa": float(ciclo_gob.amplitud_pa),
                                         "media_nominal_gobernante_pa": float(ciclo_gob.media_pa),
                                         "factor_seguridad_fluencia": n_est,
                                         "factor_seguridad_goodman": n_fat})
    return (pd.DataFrame(resumen_nominal), pd.DataFrame(historiales),
            pd.DataFrame(ciclos_salida), pd.DataFrame(sensibilidad))
