"""Parámetros centrales de la primera etapa de simulación.

Todas las longitudes se almacenan en metros y los tiempos en segundos.
"""

from dataclasses import dataclass
from pathlib import Path
import math


RAIZ_PROYECTO = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Parametros:
    # Datos provenientes de la Entrega 1 y de los planos
    potencia_motor_w: float = 5_500.0
    rpm_motor: float = 1_450.0
    rpm_matriz: float = 516.0
    radio_matriz_m: float = 0.100
    radio_util_interior_m: float = 0.045
    radio_util_exterior_m: float = 0.080
    diametro_agujero_m: float = 0.006
    numero_agujeros: int = 102
    espesor_matriz_m: float = 0.036
    diametro_rodillo_m: float = 0.100
    ancho_rodillo_m: float = 0.020
    numero_rodillos: int = 2
    espesor_biomasa_m: float = 0.004

    # Hipótesis geométrica revisable: rodillo centrado en el anillo útil
    centro_radial_rodillo_m: float = 0.0635

    # Resolución temporal y velocidad de reproducción (no velocidad física)
    pasos_por_revolucion: int = 1440
    fps_animacion: int = 30

    @property
    def omega_rad_s(self) -> float:
        return 2.0 * math.pi * self.rpm_matriz / 60.0

    @property
    def periodo_revolucion_s(self) -> float:
        return 60.0 / self.rpm_matriz

    @property
    def longitud_contacto_m(self) -> float:
        d = self.diametro_rodillo_m
        h = self.espesor_biomasa_m
        return math.sqrt(d * h - h**2)

    @property
    def limite_radial_rodillo_m(self) -> tuple[float, float]:
        mitad = self.ancho_rodillo_m / 2.0
        return (
            self.centro_radial_rodillo_m - mitad,
            self.centro_radial_rodillo_m + mitad,
        )


PARAMETROS = Parametros()

DXF_MATRIZ = RAIZ_PROYECTO / "cara_matriz.dxf"
CSV_AGUJEROS = RAIZ_PROYECTO / "datos" / "agujeros_matriz.csv"
DIRECTORIO_RESULTADOS = RAIZ_PROYECTO / "resultados"
