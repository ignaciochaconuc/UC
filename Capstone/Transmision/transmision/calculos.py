"""Funciones independientes de geometría, capacidad y balance de potencia."""

import math
from .catalogo import capacidad_catalogo, factor_abrazamiento_conservador


def positivos(**valores):
    for nombre, valor in valores.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
            raise ValueError(f"{nombre} debe ser positivo y finito")


def geometria(d: float, D: float, a: float, rpm: float) -> dict:
    """Poleas abiertas, diámetros y centros en mm; longitud exacta y aproximada."""
    positivos(d=d, D=D, a=a, rpm=rpm)
    if D < d or a <= (D+d)/2:
        raise ValueError("Se requiere reducción y poleas sin intersección")
    delta = (D-d)/2
    alpha = math.asin(delta/a)
    return {
        "relacion": D/d,
        "rpm_salida": rpm*d/D,
        "velocidad_correa_m_s": math.pi*d*rpm/60000,
        "longitud_aproximada_mm": 2*a+math.pi*(D+d)/2+(D-d)**2/(4*a),
        "longitud_exacta_mm": 2*math.sqrt(a*a-delta*delta)+math.pi*(D+d)/2+2*delta*alpha,
        "abrazamiento_motriz_grados": math.degrees(math.pi-2*alpha),
        "abrazamiento_conducida_grados": math.degrees(math.pi+2*alpha),
        "cociente_D_menos_d_sobre_a": (D-d)/a,
    }


def centros_para_longitud(d: float, D: float, longitud: float) -> float:
    positivos(d=d, D=D, longitud=longitud)
    inferior = (d+D)/2*(1+1e-12)
    if D < d or longitud <= geometria(d, D, inferior, 1)["longitud_exacta_mm"]:
        raise ValueError("Longitud incompatible con poleas separadas")
    superior = longitud
    for _ in range(80):
        medio = (inferior+superior)/2
        if geometria(d, D, medio, 1)["longitud_exacta_mm"] < longitud:
            inferior = medio
        else:
            superior = medio
    return (inferior+superior)/2


def capacidad_corregida(basica: float, adicional: float, vida: float, G: float, CL: float) -> float:
    positivos(basica=basica, G=G, CL=CL)
    if not all(math.isfinite(x) for x in (adicional, vida)) or adicional < 0 or basica+adicional+vida <= 0 or G > 1:
        raise ValueError("Potencias o factor de abrazamiento inválidos")
    return (basica+adicional+vida)*G*CL


def dimensionar(potencia: float, servicio: float, capacidad: float, cantidad: int) -> dict:
    positivos(potencia=potencia, servicio=servicio, capacidad=capacidad)
    if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad < 1:
        raise ValueError("Cantidad de correas entera positiva requerida")
    diseno = potencia*servicio
    total = cantidad*capacidad
    return {"potencia_diseno_kw": diseno, "capacidad_correa_kw": capacidad,
            "capacidad_total_kw": total, "numero_minimo_correas": math.ceil(diseno/capacidad),
            "margen_capacidad_kw": total-diseno, "margen_sobre_diseno_porcentaje": 100*(total/diseno-1),
            "utilizacion_capacidad": diseno/total, "cumple_capacidad": total >= diseno,
            "factor_servicio_maximo_capacidad": total/potencia}


def balance_motor(potencia: float, eficiencia: float, maxima: float, media: float) -> dict:
    positivos(potencia=potencia, eficiencia=eficiencia, maxima=maxima, media=media)
    if eficiencia > 1 or media > maxima:
        raise ValueError("Eficiencia o potencias resistentes inválidas")
    disponible = potencia*eficiencia
    return {"eficiencia_supuesta": eficiencia, "potencia_disponible_kw": disponible,
            "margen_maximo_kw": disponible-maxima, "margen_medio_kw": disponible-media,
            "cubre_maximo_3c": disponible >= maxima, "cubre_media_3c": disponible >= media,
            "eficiencia_minima_maximo": maxima/potencia, "eficiencia_minima_media": media/potencia}


def resolver(p: dict) -> dict:
    positivos(horas_diarias=p["horas_diarias"], longitud=p["longitud_correa_mm"])
    if p["horas_diarias"] > 24 or p["perfil"] != "SPA" or p["construccion"] != "Super HC wrapped":
        raise ValueError("Horario o construcción de correa no admitidos")
    if p["diametros_son_referencia_supuesto"] is not True or p["vida_base_catalogo_h"] != 12000:
        raise ValueError("Esta evaluación exige diámetros de referencia y base de catálogo 12000 h")
    g = geometria(p["diametro_motriz_mm"], p["diametro_conducida_mm"], p["centros_mm"], p["rpm_motor"])
    c = capacidad_catalogo(p["rpm_motor"], p["diametro_motriz_mm"], g["relacion"], p["longitud_correa_mm"])
    G = factor_abrazamiento_conservador(g["cociente_D_menos_d_sobre_a"])
    neta = capacidad_corregida(c["basica_kw"], c["adicional_relacion_kw"], c["adicional_vida_kw"], G, c["factor_longitud"])
    return {"etapa_5a": {**g, "centros_exactos_para_longitud_comercial_mm": centros_para_longitud(
                p["diametro_motriz_mm"], p["diametro_conducida_mm"], p["longitud_correa_mm"]),
                "diferencia_longitud_exacta_comercial_mm": g["longitud_exacta_mm"]-p["longitud_correa_mm"],
                "diferencia_rpm_vs_3c": g["rpm_salida"]-p["cargas_3c"]["rpm_matriz"]},
            "etapa_5b": {**c, "factor_abrazamiento": G, **dimensionar(p["potencia_motor_kw"], p["factor_servicio"], neta, p["numero_correas"])}}
