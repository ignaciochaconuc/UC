"""Etapa 5C: envolvente de ajuste y gargantas, sin asignar pretensión."""

import math
from .calculos import geometria, positivos
from .catalogo import FUENTE

FUENTE_5C = {
    "url": FUENTE["url"], "clave_bibtex": "gates_vbelt_2004",
    "tabla_recorridos": 11, "pagina_impresa_recorridos": 32,
    "pagina_pdf_recorridos_desde_uno": 34,
    "tabla_gargantas": 18, "pagina_impresa_gargantas": 40,
    "pagina_pdf_gargantas_desde_uno": 42,
    "normas_indicadas_tabla_spa": "DIN 2211 e ISO 4183",
    "verificacion": "Lectura visual del manual original; sin interpolación",
    "fecha_consulta": "2026-10-21",
}


def recorridos_catalogo(longitud_mm: float, perfil: str = "SPA") -> dict:
    positivos(longitud_mm=longitud_mm)
    if perfil != "SPA" or not 1200 <= longitud_mm <= 1999:
        raise ValueError("Solo se ha verificado SPA, longitud de referencia 1200–1999 mm")
    return {"acercamiento_instalacion_mm": 25., "alejamiento_tensado_mm": 35.}


def ajuste_centros(nominal_mm: float, acercamiento_mm: float, alejamiento_mm: float) -> dict:
    positivos(nominal_mm=nominal_mm, acercamiento_mm=acercamiento_mm, alejamiento_mm=alejamiento_mm)
    if acercamiento_mm >= nominal_mm:
        raise ValueError("El acercamiento debe dejar una distancia positiva")
    return {"centros_minimos_mm": nominal_mm-acercamiento_mm, "centros_nominales_mm": nominal_mm,
            "centros_maximos_mm": nominal_mm+alejamiento_mm,
            "recorrido_total_minimo_mm": acercamiento_mm+alejamiento_mm}


def comprobar_diametros(referencia_mm: float, exterior_mm: float) -> dict:
    positivos(referencia_mm=referencia_mm, exterior_mm=exterior_mm)
    if exterior_mm <= referencia_mm:
        raise ValueError("El diámetro exterior SPA debe superar el de referencia")
    diferencia = exterior_mm-referencia_mm
    return {"diametro_referencia_mm": referencia_mm, "diametro_exterior_cad_mm": exterior_mm,
            "diferencia_diametral_mm": diferencia, "altura_radial_cad_mm": diferencia/2,
            "altura_radial_tabla_spa_mm": 2.75,
            "exterior_derivado_tabla_mm": referencia_mm+2*2.75,
            "desviacion_diametral_cad_vs_tabla_mm": diferencia-2*2.75,
            "compatibilidad_exacta_tabla": math.isclose(diferencia, 5.5, abs_tol=1e-9),
            "aceptacion_tolerancia": "pendiente; no se asignó tolerancia para b"}


def gargantas_spa(diametro_mm: float, cantidad: int, correas: int) -> dict:
    positivos(diametro_mm=diametro_mm)
    for n in (cantidad, correas):
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("Gargantas y correas deben ser enteros positivos")
    if cantidad != correas:
        raise ValueError("Se requiere una garganta SPA por cada correa")
    if diametro_mm < 90:
        raise ValueError("Diámetro fuera de la fila SPA verificada")
    return {"numero_gargantas": cantidad, "paso_e_mm": 15., "tolerancia_paso_mm": .30,
            "margen_lateral_f_mm": 10., "tolerancia_margen_mm": .6,
            "ancho_llanta_nominal_mm": (cantidad-1)*15+2*10,
            "ancho_referencia_lp_mm": 11., "profundidad_d_mm": 13.75,
            "tolerancia_profundidad_mas_mm": .25, "tolerancia_profundidad_menos_mm": 0.,
            "altura_b_mm": 2.75, "angulo_garganta_grados": 34. if diametro_mm <= 118 else 38.,
            "tolerancia_angulo_grados": 1., "ancho_boca_go_mm": 12.68 if diametro_mm <= 118 else 12.89,
            "estado": "dimensiones de referencia para cotejo CAD; polea comercial pendiente"}


def resolver_5c(p: dict) -> dict:
    c = p["etapa_5c"]
    if c["diametros_referencia_confirmados"] is not True:
        raise ValueError("5C requiere diámetros de referencia confirmados")
    recorridos = recorridos_catalogo(p["longitud_correa_mm"], p["perfil"])
    ajuste = ajuste_centros(p["centros_mm"], recorridos["acercamiento_instalacion_mm"], recorridos["alejamiento_tensado_mm"])
    poleas = []
    for nombre, clave in (("motriz", "motriz"), ("conducida", "conducida")):
        d = p[f"diametro_{clave}_mm"]
        poleas.append({"polea": nombre, **comprobar_diametros(d, c[f"diametro_exterior_{clave}_mm"]),
                       **gargantas_spa(d, c[f"gargantas_{clave}"], p["numero_correas"])})
    # Solo se evalúa el punto nominal: los extremos son reservas mecánicas de ajuste.
    g = geometria(p["diametro_motriz_mm"], p["diametro_conducida_mm"], p["centros_mm"], p["rpm_motor"])
    if ajuste["centros_minimos_mm"] <= sum(q["diametro_exterior_cad_mm"] for q in poleas)/2:
        raise ValueError("Las poleas exteriores se intersectan en el extremo de instalación")
    return {"recorridos": recorridos, "ajuste_centros": ajuste, "poleas": poleas, "geometria_nominal": g,
            "criterio_operacion": "El nominal es referencia geométrica; la operación depende del tensado. Extremos no operativos para una correa inextensible de 1600 mm.",
            "propuesta_base": "Base móvil del motor guiada longitudinalmente en la línea de centros, reguladores de desplazamiento y bloqueo posterior independiente.",
            "tension_inicial_n": None, "reacciones_ejes": "pendientes de 5D"}
