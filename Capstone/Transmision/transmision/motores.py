"""Compatibilidad nominal 5E.2-B. No selecciona motor ni aprueba una unión."""
import math
from .calculos import positivos
from .poleas import no_negativo
from .chavetas import comprobar_eje_real


def cabida_axial(extension_mm, envolvente_mm, inicio_mm=None):
    positivos(extension_mm=extension_mm, envolvente_mm=envolvente_mm)
    if inicio_mm is not None:
        no_negativo(inicio_mm=inicio_mm)
    cabe=envolvente_mm <= extension_mm
    return {"extension_eje_mm":extension_mm,"envolvente_cubo_mm":envolvente_mm,
        "diferencia_extension_envolvente_mm":extension_mm-envolvente_mm,
        "cabe_envolvente_en_longitud_nominal":cabe,
        "posicion_inicio_desde_hombro_mm":inicio_mm,
        "cabe_en_posicion_propuesta":None if inicio_mm is None else inicio_mm+envolvente_mm <= extension_mm,
        "longitud_contacto_efectiva_mm":None,
        "estado":"condicion_necesaria_no_montaje_aprobado" if cabe else "envolvente_supera_extension"}


def comprobar_carga_radial(carga_n, catalogo=None, distancia_mm=None,
                          referencia_axial=None, condiciones_verificadas=False):
    """Compara solo una capacidad documentada aplicable al mismo montaje.

    catalogo: admisible_n, distancia_mm, referencia_axial, fuente, condiciones.
    La posición de referencia NO se presupone (hombro, punta o rodamiento).
    No se extrapola con distancia, rpm, orientación ni vida.
    """
    no_negativo(carga_n=carga_n)
    if distancia_mm is not None:
        no_negativo(distancia_mm=distancia_mm)
    if not isinstance(condiciones_verificadas,bool):
        raise ValueError("Condiciones verificadas debe ser bool")
    base={"carga_condicional_correas_n":carga_n,"distancia_aplicacion_mm":distancia_mm,
          "referencia_axial":referencia_axial,"admisible_catalogo_n":None,
          "utilizacion_radial":None,"cumple_comparacion_carga_correas":None,
          "montaje_aprobado":False}
    if catalogo is None:
        return {**base,"estado":"pendiente_capacidad_fabricante_y_montaje"}
    positivos(admisible_n=catalogo["admisible_n"])
    no_negativo(distancia_mm=catalogo["distancia_mm"])
    if not catalogo.get("fuente") or not catalogo.get("condiciones") or not catalogo.get("referencia_axial"):
        raise ValueError("Capacidad requiere fuente, condiciones y referencia axial")
    base["admisible_catalogo_n"]=catalogo["admisible_n"]
    if (distancia_mm is None or referencia_axial != catalogo["referencia_axial"]
        or not math.isclose(distancia_mm,catalogo["distancia_mm"],abs_tol=1e-9,rel_tol=0)
        or not condiciones_verificadas):
        return {**base,"estado":"pendiente_correspondencia_condiciones_catalogo"}
    return {**base,"utilizacion_radial":carga_n/catalogo["admisible_n"],
        "cumple_comparacion_carga_correas":carga_n <= catalogo["admisible_n"],
        "estado":"comparacion_solo_correas_no_incluye_peso_ni_otras_cargas"}


def comparar_motor(motor, polea, rpm_historica, inicio_mm=None):
    for k in ("potencia_kw","rpm_nominal","diametro_eje_mm","extension_eje_mm","frecuencia_hz"):
        positivos(**{k:motor[k]})
    positivos(rpm_historica=rpm_historica)
    for k in ("polos","fases"):
        if isinstance(motor[k],bool) or not isinstance(motor[k],int) or motor[k] <= 0:
            raise ValueError("Polos y fases requieren enteros positivos")
    eta=motor["eficiencia_electrica_nominal"]
    if eta is not None:
        positivos(eficiencia_electrica=eta)
        if eta > 1:
            raise ValueError("Eficiencia eléctrica debe ser <=1")
    b=motor["ancho_chavetero_mm"]
    if b is not None:
        positivos(ancho_chavetero_mm=b)
    eje=comprobar_eje_real(polea["diametro_interior_cubo_mm"],motor["diametro_eje_mm"],motor["url"])
    return {"motor":motor["id"],"potencia_kw":motor["potencia_kw"],"polos":motor["polos"],
        "fases":motor["fases"],"frecuencia_hz":motor["frecuencia_hz"],
        "coincide_configuracion_5_5kw_4p_50hz":motor["potencia_kw"]==5.5 and motor["polos"]==4 and motor["fases"]==3 and motor["frecuencia_hz"]==50,
        "diametro_eje_mm":motor["diametro_eje_mm"],"coincide_agujero_nominal":eje["coincidencia_nominal"],
        "ajuste_eje_cubo":"pendiente_tolerancias_y_montaje",
        "ancho_chavetero_motor_mm":b,"coincide_ancho_nominal":None if b is None else b==polea["ancho_chaveta_mm"],
        "chaveta_resistencia_aprobada":False,"rpm_nominal_comercial":motor["rpm_nominal"],
        "rpm_historica_no_modificada":rpm_historica,"diferencia_rpm":motor["rpm_nominal"]-rpm_historica,
        "diferencia_rpm_porcentaje":100*(motor["rpm_nominal"]/rpm_historica-1),
        "montaje":motor["montaje"],"eficiencia_electrica":eta,
        "eficiencia_mecanica_correas":None,"motor_seleccionado":False,
        **cabida_axial(motor["extension_eje_mm"],polea["longitud_cubo_mm"],inicio_mm)}
