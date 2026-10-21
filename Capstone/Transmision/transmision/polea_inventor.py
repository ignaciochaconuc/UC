"""Lectura trazable del plano vigente de conducida; verificaciones parciales."""

import math
from .poleas import seccion_anular, validar_parametros


def verificar_inventor(config):
    p = config["poleas"]["conducida"]
    validar_parametros(p, config["material"], p["diametro_crestas_gargantas_mm"])
    n = p["numero_aberturas"]
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("Cantidad de aberturas entera positiva requerida")
    if p["tipo_cuerpo"] != "aligerado_aberturas_circulares" or p["numero_radios"] is not None:
        raise ValueError("Mantener cuerpo aligerado; no convertir seis aberturas en seis radios")
    if p["diametro_interior_llanta_mm"] is not None:
        raise ValueError("PDF no confirma diámetro interior de llanta; no usar Ø258 como interior")
    raiz = p["diametro_crestas_gargantas_mm"]-2*p["profundidad_radial_garganta_mm"]
    if not math.isclose(raiz, p["diametro_fondo_gargantas_mm"], abs_tol=1e-8):
        raise ValueError("Cotas de fondo y profundidad de garganta incoherentes")
    if p["diametro_pestanas_mm"] <= p["diametro_crestas_gargantas_mm"]:
        raise ValueError("Pestañas deben superar crestas")
    if p["longitud_cubo_mm"] <= p["ancho_llanta_cad_mm"]:
        raise ValueError("Envolvente de cubo debe superar ancho de llanta en esta revisión")
    s = seccion_anular(p["diametro_exterior_cubo_mm"], p["diametro_interior_cubo_mm"])
    return {"diametro_fondo_verificado_mm": raiz,
        "saliente_cubo_sobre_cara_exterior_pestana_mm": p["longitud_cubo_mm"]-p["ancho_llanta_cad_mm"],
        "seccion_anular_lisa_cubo": s,
        "area_total_aberturas_proyeccion_mm2": n*math.pi*p["diametro_aberturas_mm"]**2/4,
        "nota_area": "Solo suma de círculos; no es área resistente neta, masa ni volumen",
        "angulo_cad_grados": p["angulo_garganta_cad_grados"], "angulo_gates_280_grados": 38.,
        "diferencia_angulo_grados": p["angulo_garganta_cad_grados"]-38.,
        "compatibilidad_normativa_aprobada": False}


def torsion_cubo_liso(torque_nm, config):
    if not math.isfinite(torque_nm):
        raise ValueError("Torque debe ser finito")
    p = config["poleas"]["conducida"]
    s = verificar_inventor(config)["seccion_anular_lisa_cubo"]
    return {"tau_torsion_nominal_lisa_mpa": abs(torque_nm)*1000*(p["diametro_exterior_cubo_mm"]/2)/s["J_mm4"],
        "estado": "componente nominal parcial; no resistencia aprobada",
        "limitaciones": "Sección Ø75/Ø35 lisa, ignora chavetero, taladro M5, entallas y flexión; no calcula FS"}
