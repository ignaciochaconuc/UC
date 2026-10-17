"""Geometría, materiales y posiciones configurables del eje transversal."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class SegmentoEje:
    nombre: str
    x_inicio_m: float
    x_fin_m: float
    diametro_exterior_m: float
    diametro_interior_m: float = 0.0

    @property
    def longitud_m(self) -> float:
        return self.x_fin_m - self.x_inicio_m

    @property
    def area_m2(self) -> float:
        return math.pi * (self.diametro_exterior_m**2 - self.diametro_interior_m**2) / 4

    @property
    def inercia_m4(self) -> float:
        return math.pi * (self.diametro_exterior_m**4 - self.diametro_interior_m**4) / 64

    @property
    def radio_exterior_m(self) -> float:
        return self.diametro_exterior_m / 2


@dataclass(frozen=True)
class ConfiguracionEje:
    longitud_m: float = 0.270
    modulo_young_pa: float = 205e9
    coeficiente_poisson: float = 0.29
    densidad_eje_kg_m3: float = 7850.0
    gravedad_m_s2: float = 9.80665
    limite_fluencia_pa: float | None = None
    resistencia_ultima_pa: float | None = None

    # Rosca M24x2: diámetro menor básico aproximado d3=d-1,22687P.
    diametro_equivalente_rosca_m: float = 0.0215463

    # Posiciones axiales medidas desde el extremo izquierdo.
    centro_matriz_m: float = 0.135
    rodamientos_izquierdos_m: tuple[float, float] = (0.0595, 0.0835)
    rodamientos_derechos_m: tuple[float, float] = (0.1865, 0.2105)
    centro_rodillo_izquierdo_m: float = 0.0715
    centro_rodillo_derecho_m: float = 0.1985

    # Estimación de masa del rodillo AISI 8620 desde la sección del plano.
    densidad_rodillo_kg_m3: float = 7850.0
    diametro_exterior_rodillo_m: float = 0.09999
    ancho_rodillo_m: float = 0.040
    diametro_agujero_pasante_rodillo_m: float = 0.056
    diametro_alojamiento_rodamiento_m: float = 0.062
    profundidad_alojamiento_por_lado_m: float = 0.016
    masa_rodillo_ingresada_kg: float | None = None

    longitud_maxima_elemento_m: float = 0.002
    tolerancia_equilibrio_relativa: float = 1e-8

    @property
    def segmentos(self) -> tuple[SegmentoEje, ...]:
        dr = self.diametro_equivalente_rosca_m
        return (
            SegmentoEje("rosca_izquierda_M24x2_equivalente", 0.0000, 0.0290, dr),
            SegmentoEje("asiento_izquierdo_exterior", 0.0290, 0.0515, 0.0300),
            SegmentoEje("alivio_izquierdo", 0.0515, 0.0531, 0.0292),
            SegmentoEje("asiento_rodillo_izquierdo", 0.0531, 0.0915, 0.0300),
            SegmentoEje("tramo_central", 0.0915, 0.1785, 0.0360),
            SegmentoEje("asiento_rodillo_derecho", 0.1785, 0.2169, 0.0300),
            SegmentoEje("alivio_derecho", 0.2169, 0.2185, 0.0292),
            SegmentoEje("asiento_derecho_exterior", 0.2185, 0.2410, 0.0300),
            SegmentoEje("rosca_derecha_M24x2_equivalente", 0.2410, 0.2700, dr),
        )

    @property
    def volumen_rodillo_estimado_m3(self) -> float:
        de = self.diametro_exterior_rodillo_m
        dp = self.diametro_agujero_pasante_rodillo_m
        da = self.diametro_alojamiento_rodamiento_m
        b = self.ancho_rodillo_m
        profundidad_total = 2 * self.profundidad_alojamiento_por_lado_m
        volumen_anular_base = math.pi * (de**2 - dp**2) * b / 4
        volumen_contramandrinado = math.pi * (da**2 - dp**2) * profundidad_total / 4
        return volumen_anular_base - volumen_contramandrinado

    @property
    def masa_rodillo_kg(self) -> float:
        if self.masa_rodillo_ingresada_kg is not None:
            return self.masa_rodillo_ingresada_kg
        return self.densidad_rodillo_kg_m3 * self.volumen_rodillo_estimado_m3

    @property
    def masa_eje_kg(self) -> float:
        return self.densidad_eje_kg_m3 * sum(s.area_m2 * s.longitud_m for s in self.segmentos)

    def como_dict(self) -> dict:
        datos = asdict(self)
        datos["masa_rodillo_utilizada_kg"] = self.masa_rodillo_kg
        datos["masa_eje_kg"] = self.masa_eje_kg
        datos["fuente_masa_rodillo"] = (
            "ingresada" if self.masa_rodillo_ingresada_kg is not None
            else "estimada_sin_ranuras_exteriores"
        )
        return datos


CONFIG_EJE = ConfiguracionEje()

