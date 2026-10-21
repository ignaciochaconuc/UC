"""Lectura trazable del plano vigente de conducida; verificaciones parciales."""

import math
from .poleas import seccion_anular, validar_parametros, esfuerzo_cubo


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


def verificar_motriz_inventor(config):
    p = config["poleas"]["motriz"]
    validar_parametros(p, config["material"], p["diametro_crestas_gargantas_mm"])
    if p["tipo_cuerpo"] != "aligerado_aberturas_circulares" or p["numero_radios"] is not None:
        raise ValueError("Motriz aligerada, no disco ni radios rectangulares")
    n = p["numero_aberturas"]
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("Cantidad de aberturas entera positiva requerida")
    if p["diametro_interior_llanta_mm"] is not None:
        raise ValueError("El plano no confirma interior de llanta; Ø78 es fondo de gargantas")
    fondo = p["diametro_crestas_gargantas_mm"]-2*p["profundidad_radial_garganta_mm"]
    if not math.isclose(fondo, p["diametro_fondo_gargantas_mm"], abs_tol=1e-9):
        raise ValueError("Fondo de garganta incompatible con profundidad")
    if not math.isclose(p["ancho_llanta_cad_mm"], p["distancia_caras_interiores_pestanas_mm"]+2*p["espesor_axial_pestana_cota_mm"], abs_tol=1e-9):
        raise ValueError("Anchos axial interior/exterior incompatibles")
    if p["diametro_pestanas_mm"] <= p["diametro_crestas_gargantas_mm"] or p["longitud_cubo_mm"] <= p["ancho_llanta_cad_mm"]:
        raise ValueError("Envolventes incompatibles")
    saliente = p["longitud_cubo_mm"]-p["ancho_llanta_cad_mm"]
    if not math.isclose(saliente+p["espesor_axial_pestana_cota_mm"], p["saliente_cubo_hasta_cara_interior_pestana_mm"], abs_tol=1e-9):
        raise ValueError("Saliente axial incompatible con cotas de pestaña")
    return {"diametro_fondo_verificado_mm": fondo,
        "saliente_cubo_sobre_cara_exterior_pestana_mm": saliente,
        "seccion_anular_lisa_cubo": seccion_anular(p["diametro_exterior_cubo_mm"],p["diametro_interior_cubo_mm"]),
        "espesor_radial_nominal_cubo_liso_mm": (p["diametro_exterior_cubo_mm"]-p["diametro_interior_cubo_mm"])/2,
        "area_total_aberturas_proyeccion_mm2": n*math.pi*p["diametro_aberturas_mm"]**2/4,
        "angulo_cad_grados":p["angulo_garganta_cad_grados"], "angulo_gates_100_grados":34.,
        "coincidencia_angulo_nominal_gates": math.isclose(p["angulo_garganta_cad_grados"],34.,abs_tol=1e-9),
        "compatibilidad_normativa_completa_aprobada":False,
        "nota": "Coincidencia de ángulo no acredita todas las dimensiones normativas ni resistencia"}


def torsion_cubo_liso_polea(torque_nm, config, polea):
    if polea == "conducida":
        return torsion_cubo_liso(torque_nm,config)
    if polea != "motriz":
        raise ValueError("Polea desconocida")
    if not math.isfinite(torque_nm):
        raise ValueError("Torque finito requerido")
    verificar_motriz_inventor(config)
    p=config["poleas"][polea]
    valor=esfuerzo_cubo(abs(torque_nm),0.,0.,p["diametro_exterior_cubo_mm"],p["diametro_interior_cubo_mm"])
    return {"tau_torsion_nominal_lisa_mpa":valor["tau_torsion_mpa"],
        "estado":"componente nominal parcial; no resistencia aprobada",
        "limitaciones":"Anillo liso Ø45/Ø38, excluye chavetero 10 JS9, M5, aligeramientos, entallas y flexión; no FS"}
