"""5E.1: verificaciones nominales condicionadas a geometría documentada.

N, mm y MPa internamente; torque y momentos externos en N m.
Son aproximaciones elementales, no una validación integral de la polea.
"""

import math
from .calculos import positivos


def no_negativo(**valores):
    for nombre, valor in valores.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
            raise ValueError(f"{nombre} debe ser finito y no negativo")


def seccion_anular(exterior_mm, interior_mm):
    positivos(exterior_mm=exterior_mm)
    no_negativo(interior_mm=interior_mm)
    if interior_mm >= exterior_mm:
        raise ValueError("Diámetro interior debe ser menor que exterior")
    return {"area_mm2": math.pi*(exterior_mm**2-interior_mm**2)/4,
            "I_mm4": math.pi*(exterior_mm**4-interior_mm**4)/64,
            "J_mm4": math.pi*(exterior_mm**4-interior_mm**4)/32}


def esfuerzo_cubo(torque_nm, fuerza_n, excentricidad_mm, exterior_mm, interior_mm):
    """Sección anular lisa con flexión Fr*e y torsión Saint-Venant.

    No incluye cortante transversal, contacto, chavetero ni concentradores.
    No calcula reacciones del eje: e es una distancia local especificada.
    """
    no_negativo(torque_nm=torque_nm, fuerza_n=fuerza_n, excentricidad_mm=excentricidad_mm)
    s = seccion_anular(exterior_mm, interior_mm)
    radio = exterior_mm/2
    tau = torque_nm*1000*radio/s["J_mm4"]
    sigma = fuerza_n*excentricidad_mm*radio/s["I_mm4"]
    return {"tau_torsion_mpa": tau, "sigma_flexion_mpa": sigma,
            "von_mises_parcial_mpa": math.hypot(sigma, math.sqrt(3)*tau)}


def cortante_disco(torque_nm, radio_seccion_mm, espesor_mm):
    """Flujo uniforme de torsión en cuerpo disco: T=2*pi*r²*t*tau.

    Solo componente torsional media: no resuelve carga radial ni flexión de placa.
    """
    no_negativo(torque_nm=torque_nm)
    positivos(radio_seccion_mm=radio_seccion_mm, espesor_mm=espesor_mm)
    return torque_nm*1000/(2*math.pi*radio_seccion_mm**2*espesor_mm)


def chaveta_nominal(torque_nm, diametro_eje_mm, ancho_mm, altura_contacto_mm, longitud_mm):
    """Una chaveta paralela con todo el torque; altura de contacto explícita."""
    no_negativo(torque_nm=torque_nm)
    positivos(diametro_eje_mm=diametro_eje_mm, ancho_mm=ancho_mm,
              altura_contacto_mm=altura_contacto_mm, longitud_mm=longitud_mm)
    f = 2*torque_nm*1000/diametro_eje_mm
    return {"fuerza_tangencial_union_n": f, "tau_chaveta_mpa": f/(ancho_mm*longitud_mm),
            "presion_contacto_media_mpa": f/(altura_contacto_mm*longitud_mm)}


def validar_parametros(p, material, exterior_cad_mm):
    for k, v in p.items():
        if v is not None and (k.endswith("_mm") and not isinstance(v, (dict, list))):
            if k == "desfase_plano_correas_seccion_cubo_mm":
                no_negativo(**{k: v})
            else:
                positivos(**{k: v})
    if p["tipo_cuerpo"] not in (None, "disco", "radios"):
        raise ValueError("Tipo de cuerpo debe ser disco o radios confirmado")
    if p["numero_radios"] is not None:
        n = p["numero_radios"]
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("Número de radios entero positivo")
    if p["tipo_cuerpo"] == "disco" and p["numero_radios"] is not None:
        raise ValueError("Un disco continuo no debe incluir número de radios")
    di, de = p["diametro_interior_cubo_mm"], p["diametro_exterior_cubo_mm"]
    if di is not None and de is not None:
        seccion_anular(de, di)
    if de is not None and de >= exterior_cad_mm:
        raise ValueError("Cubo exterior incompatible con exterior de polea")
    if p["diametro_interior_llanta_mm"] is not None:
        if p["diametro_interior_llanta_mm"] >= exterior_cad_mm or (de is not None and de >= p["diametro_interior_llanta_mm"]):
            raise ValueError("Llanta interior incompatible con cubo o diámetro exterior")
    for campo in ("limite_fluencia_mpa", "resistencia_ultima_mpa", "modulo_young_mpa", "densidad_kg_m3"):
        if material.get(campo) is not None:
            positivos(**{campo: material[campo]})
            if not all(material.get(k) for k in ("condicion_suministro", "forma_y_seccion_producto", "fuente_propiedades")):
                raise ValueError("Propiedades requieren condición, producto y fuente trazable")
    nu = material.get("poisson")
    if nu is not None and (isinstance(nu, bool) or not isinstance(nu, (int, float)) or not math.isfinite(nu) or not -1 < nu < .5):
        raise ValueError("Poisson debe estar entre -1 y 0,5")
    if nu is not None and not all(material.get(k) for k in ("condicion_suministro", "forma_y_seccion_producto", "fuente_propiedades")):
        raise ValueError("Poisson también requiere fuente y condición documentadas")


def verificar_resistencia(carga, p, material):
    """Ausencia de datos produce pendiente con lista explícita, nunca valores típicos."""
    comprobaciones = []
    def fila(nombre, campos, calcular, alcance):
        faltantes = [k for k in campos if p.get(k) is None]
        comprobaciones.append({"comprobacion": nombre,
            "estado": "pendiente" if faltantes else "calculado_nominal_condicionado",
            "faltantes": faltantes, "resultado": None if faltantes else calcular(), "alcance": alcance})
    T, F = abs(carga["torque_correas_firmado_nm"]), carga["fr_n"]
    fila("cubo_flexion_torsion", ["diametro_exterior_cubo_mm", "diametro_interior_cubo_mm", "desfase_plano_correas_seccion_cubo_mm"],
         lambda: esfuerzo_cubo(T, F, p["desfase_plano_correas_seccion_cubo_mm"], p["diametro_exterior_cubo_mm"], p["diametro_interior_cubo_mm"]),
         "Sección anular lisa, sin chavetero, contacto ni cortante transversal; no es esfuerzo máximo real")
    if p["tipo_cuerpo"] == "disco":
        fila("cuerpo_disco_torsion_media", ["diametro_exterior_cubo_mm", "espesor_cuerpo_mm"],
             lambda: {"tau_media_mpa": cortante_disco(T, p["diametro_exterior_cubo_mm"]/2, p["espesor_cuerpo_mm"])},
             "Solo flujo torsional uniforme en unión al cubo; excluye flexión y fuerza radial")
    else:
        comprobaciones.append({"comprobacion": "cuerpo_disco_o_radios", "estado": "pendiente",
            "faltantes": ["tipo_cuerpo", "geometria_radios", "seccion_radios_mm", "espesor_cuerpo_mm"],
            "resultado": None, "alcance": "Confirmar topología; reparto entre radios requiere rigidez, orientación y geometría, no repartir arbitrariamente"})
    if p["tipo_union_eje"] == "chaveta_paralela_unica":
        fila("chaveta_corte_aplastamiento", ["diametro_interior_cubo_mm", "ancho_chaveta_mm", "altura_contacto_chaveta_mm", "longitud_activa_chaveta_mm"],
             lambda: chaveta_nominal(T, p["diametro_interior_cubo_mm"], p["ancho_chaveta_mm"], p["altura_contacto_chaveta_mm"], p["longitud_activa_chaveta_mm"]),
             "Promedios en una chaveta; material propio, entallas y contacto del cubo pendientes")
    else:
        comprobaciones.append({"comprobacion": "union_eje_cubo", "estado": "pendiente", "faltantes": ["tipo_union_eje", "ajustes_tolerancias_retencion"],
            "resultado": None, "alcance": "No suponer chaveta, interferencia, tornillos ni geometría de asiento"})
    comprobaciones.extend([
        {"comprobacion": "llanta_gargantas_filetes", "estado": "pendiente", "faltantes": ["espesor_residual_llanta_mm", "diametro_interior_llanta_mm", "filetes_gargantas_mm", "distribucion_contacto"],
         "resultado": None, "alcance": "FEM real para flexión local, contacto y concentración"},
        {"comprobacion": "factor_seguridad_polea", "estado": "pendiente", "faltantes": ["geometria_completa", "condicion_suministro", "fuente_propiedades", "limite_fluencia_mpa", "criterio_aceptacion"],
         "resultado": None, "alcance": "No usar un von Mises parcial como máximo de la polea; no se calcula FS integral ni fatiga"}])
    return comprobaciones
