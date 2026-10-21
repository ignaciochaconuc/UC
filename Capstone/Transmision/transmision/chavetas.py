"""5E.2. N, mm y MPa. Candidatas normalizadas, no unión aprobada."""

import math
from .calculos import positivos
from .poleas import no_negativo, chaveta_nominal

FUENTES_CHAVETAS = {
    "ganter_dimensiones": {
        "clave": "ganter_din6885_keyways_2026",
        "url": "https://www.ganternorm.com/fileadmin/user_upload/downloads/technischer%20anhang/technical_information/6885-1.pdf",
        "titulo": "Ganter DIN 6885-1 Keyways, High Hub Keyway, extracto página 2078",
        "lectura": "Filas d=35 y d=38; cubo P9/JS9/D10; profundidad de cubo 3,3 +0,2 y eje 5 +0,2",
        "notacion": "El proveedor llama t2 a profundidad de cubo y t4 a profundidad de eje; t1=d+t2 es medida de control",
        "fecha_consulta": "2026-10-21",
    },
    "ganter_candidata": {
        "clave": "ganter_parallel_keys_2026",
        "url": "https://www.ganternorm.com/en/products/product-family/Stainless-Steel-Quality-Class-4/DIN-6885-Parallel-Keys-Stainless-Steel",
        "lectura": "Candidata 10x8, rango 30...38 y ancho de chaveta h9; solo dimensiones, sin adoptar acero inoxidable del producto",
    },
    "din_estado": {"clave": "din6885_1_2021_catalogo", "url": "https://www.dinmedia.de/en/standard/din-6885-1/346315269",
        "lectura": "Ficha editorial DIN 6885-1:2021-11, forma alta, dimensiones y tolerancias; no se adquirió texto completo"},
    "iso_estado": {"clave": "iso_r773_1969_estado", "url": "https://www.iso.org/standard/5056.html",
        "lectura": "ISO/R 773:1969 retirada el 1998-11-03; referencia histórica, no certificación vigente"},
}


def candidata_normalizada(diametro_mm):
    positivos(diametro_mm=diametro_mm)
    if not 30 < diametro_mm <= 38:
        raise ValueError("Solo se verificó la candidata 10x8 para más de 30 hasta 38 mm inclusive")
    return {"diametro_mm": diametro_mm, "b_mm": 10., "h_mm": 8.,
        "profundidad_cubo_nominal_mm": 3.3, "profundidad_cubo_max_mm": 3.5,
        "profundidad_eje_nominal_mm": 5., "profundidad_eje_max_mm": 5.2,
        "ajuste_ancho_chaveta": "h9", "ajuste_ancho_cubo_candidato": "JS9",
        "estado": "candidata DIN 6885-1 forma alta; no selección comercial ni CAD conforme",
        "fuente": "ganter_din6885_keyways_2026; ganter_parallel_keys_2026"}


def fuerza_tangencial_union(torque_nm, diametro_mm):
    if isinstance(torque_nm, bool) or not isinstance(torque_nm, (int, float)) or not math.isfinite(torque_nm):
        raise ValueError("Torque firmado finito requerido")
    positivos(diametro_mm=diametro_mm)
    return 2*abs(torque_nm)*1000/diametro_mm


def ligamento_cubo(exterior_mm, agujero_mm, ancho_ranura_mm, profundidad_cubo_mm):
    """Cribado geométrico en cubo cilíndrico, no fórmula de resistencia.

    q se mide desde tangente superior del agujero hasta el fondo plano.
    Esquina ideal sin filete; geometría local real sigue siendo necesaria.
    """
    positivos(exterior_mm=exterior_mm, agujero_mm=agujero_mm, ancho_ranura_mm=ancho_ranura_mm)
    no_negativo(profundidad_cubo_mm=profundidad_cubo_mm)
    if exterior_mm <= agujero_mm or ancho_ranura_mm >= agujero_mm:
        raise ValueError("Cubo y ancho de ranura incompatibles")
    radio_ext = exterior_mm/2
    y_fondo = agujero_mm/2+profundidad_cubo_mm
    radio_esquina = math.hypot(ancho_ranura_mm/2,y_fondo)
    central = radio_ext-y_fondo
    esquina = radio_ext-radio_esquina
    return {"pared_radial_lisa_mm": (exterior_mm-agujero_mm)/2,
        "ligamento_central_fondo_mm": central, "ligamento_radial_esquina_ideal_mm": esquina,
        "diametro_exterior_minimo_envolvente_sin_reserva_mm": 2*radio_esquina,
        "fondo_plano_contenido_en_exterior_ideal": central > 0 and esquina > 0,
        "estado": "sin validación resistente; la envolvente sin reserva no es diámetro recomendado"}


def comprobar_eje_real(agujero_mm, eje_real_mm, fuente=None):
    positivos(agujero_mm=agujero_mm)
    if eje_real_mm is None:
        return {"estado": "pendiente_plano_eje_real", "coincidencia_nominal": None}
    positivos(eje_real_mm=eje_real_mm)
    if not fuente:
        raise ValueError("Diámetro de eje requiere fuente trazable")
    coincide=math.isclose(agujero_mm,eje_real_mm,abs_tol=1e-9)
    return {"estado": "nominal_coincidente_ajuste_pendiente" if coincide else "incompatibilidad_nominal",
            "coincidencia_nominal": coincide}


def verificar_longitud_activa(longitud_mm, envolvente_mm):
    positivos(longitud_mm=longitud_mm, envolvente_mm=envolvente_mm)
    if longitud_mm > envolvente_mm:
        raise ValueError("Longitud activa no puede superar envolvente de cubo")
    # Condición necesaria, no suficiente: faltan hombros, extremos y longitud de eje.
    return True


def sensibilidad_chaveta(T_nm, d_mm, candidata, longitudes, envolvente_mm):
    resultados=[]
    # Alturas nominales hipotéticas de contacto lateral por proyección del resalte.
    # No confundir q_cubo=3,3 con contacto: h-t_eje=3 deja 0,3 de holgura de fondo.
    h_cubo=candidata["h_mm"]-candidata["profundidad_eje_nominal_mm"]
    h_eje=candidata["profundidad_eje_nominal_mm"]
    for L in longitudes:
        verificar_longitud_activa(L,envolvente_mm)
        c=chaveta_nominal(abs(T_nm),d_mm,candidata["b_mm"],h_cubo,L)
        resultados.append({"longitud_activa_hipotetica_mm":L,"altura_contacto_cubo_hipotetica_mm":h_cubo,
            "altura_contacto_eje_hipotetica_mm":h_eje,
            "fuerza_tangencial_n":c["fuerza_tangencial_union_n"], "tau_media_chaveta_mpa":c["tau_chaveta_mpa"],
            "presion_media_cubo_mpa":c["presion_contacto_media_mpa"],
            "presion_media_eje_mpa":c["fuerza_tangencial_union_n"]/(h_eje*L),
            "estado":"sensibilidad nominal de una chaveta; no aprobación ni selección comercial"})
    return resultados
