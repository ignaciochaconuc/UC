"""5D.1: referencia Gates SPA envuelta, tensión estática y comprobación."""

import math
from .calculos import geometria, positivos
from .catalogo import FUENTE

CONSTANTES_SPA = {"R": 2.5, "M": .12, "Y_n": 20.}
FUENTE_5D1 = {
    "clave_bibtex": "gates_vbelt_2004", "url": FUENTE["url"],
    "paginas_impresas": [33, 34], "paginas_pdf_desde_uno": [35, 36],
    "tabla": 13, "fila": "SPA individual convencional; no SPA* moulded notch",
    "formulas": [6, 7, 8, 9, 10, 11, 12], "constantes": CONSTANTES_SPA,
    "unidades": {"P": "kW de accionamiento", "v": "m/s", "M": "N s²/m²",
                 "Y": "N", "t_Ld_delta": "mm", "Ts_F": "N", "R_G_N": "adimensionales"},
    "metodo_tramo": "Tangente exacta; fórmula 7 del manual es aproximada",
    "condicion_formulas_11_12": "Al menos una polea libre para girar durante la medición",
    "fecha_consulta": "2026-10-21",
}


def entero_positivo(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("Número de correas entero positivo requerido")


def constantes_spa(perfil="SPA", construccion="Super HC wrapped"):
    if (perfil, construccion) != ("SPA", "Super HC wrapped"):
        raise ValueError("Constantes solo verificadas para Gates SPA Super HC convencional envuelta")
    return dict(CONSTANTES_SPA)


def tension_estatica(potencia_kw, numero_correas, velocidad_m_s, G, R=2.5, M=.12):
    """Fórmula 6, entrada kW y m/s; salida N por correa."""
    positivos(potencia_kw=potencia_kw, velocidad_m_s=velocidad_m_s, G=G, R=R, M=M)
    entero_positivo(numero_correas)
    if G > 1 or R <= G:
        raise ValueError("Se requiere 0<G<=1 y R>G")
    return 475*((R-G)/G)*potencia_kw/(numero_correas*velocidad_m_s)+M*velocidad_m_s**2


def tramo_libre(a_mm, d_mm, D_mm):
    # Reutiliza las validaciones de geometría sin duplicar sus ecuaciones cinemáticas.
    geometria(d_mm, D_mm, a_mm, 1.)
    return math.sqrt(a_mm**2-((D_mm-d_mm)/2)**2)


def deflexion_recomendada(tramo_mm):
    positivos(tramo_mm=tramo_mm)
    return tramo_mm/100


def fuerzas_deflexion(Ts_n, tramo_mm, longitud_mm, Y_n=20., polea_libre=True):
    positivos(Ts_n=Ts_n, tramo_mm=tramo_mm, longitud_mm=longitud_mm, Y_n=Y_n)
    if tramo_mm >= longitud_mm/2 or not isinstance(polea_libre, bool):
        raise ValueError("Tramo incompatible con longitud o condición de medición inválida")
    correccion = tramo_mm/longitud_mm*Y_n if polea_libre else Y_n
    return {"fuerza_minima_n": (Ts_n+correccion)/25,
            "fuerza_maxima_n": (1.5*Ts_n+correccion)/25,
            "formulas": "11–12" if polea_libre else "9–10",
            "polea_libre": polea_libre}


def resolver_5d1(p, historico_5b):
    c = constantes_spa(p["perfil"], p["construccion"])
    g = geometria(p["diametro_motriz_mm"], p["diametro_conducida_mm"], p["centros_mm"], p["rpm_motor"])
    if not p["etapa_5c"]["diametros_referencia_confirmados"]:
        raise ValueError("Se requieren diámetros de referencia confirmados")
    G = historico_5b["factor_abrazamiento"]
    t = tramo_libre(p["centros_mm"], p["diametro_motriz_mm"], p["diametro_conducida_mm"])
    Ts = tension_estatica(p["potencia_motor_kw"], p["numero_correas"], g["velocidad_correa_m_s"], G, c["R"], c["M"])
    principal = {"potencia_accionamiento_kw": p["potencia_motor_kw"],
                 "potencia_diseno_historica_no_usada_kw": historico_5b["potencia_diseno_kw"],
                 "numero_correas": p["numero_correas"], "G": G,
                 "velocidad_m_s": g["velocidad_correa_m_s"], "tension_estatica_base_n": Ts,
                 "tramo_libre_exacto_mm": t, "deflexion_mm": deflexion_recomendada(t),
                 **fuerzas_deflexion(Ts, t, p["longitud_correa_mm"], c["Y_n"])}
    a, d, D = p["centros_mm"], p["diametro_motriz_mm"], p["diametro_conducida_mm"]
    aproximado = a*(1-.125*((D-d)/a)**2)
    return {"principal": principal, "constantes": c,
            "contraste_formula_7": {"tramo_aproximado_mm": aproximado, "diferencia_vs_exacto_mm": aproximado-t},
            "alternativa_poleas_inmovilizadas": fuerzas_deflexion(Ts, t, p["longitud_correa_mm"], c["Y_n"], False),
            "correas_individuales": [{"correa": i, **principal} for i in range(1, p["numero_correas"]+1)],
            "tensiones_dinamicas_ramales": None, "cargas_laterales_ejes": None}


def sensibilidad(p, historico_5b):
    base = resolver_5d1(p, historico_5b)["principal"]
    filas = []
    # Escenarios de fórmula, no selección comercial: geometría/construcción fijas.
    for n in (2, 3, 4):
        for potencia in (4.194, 4.805, 5.5):
            for G in (.94, .96):
                Ts = tension_estatica(potencia, n, base["velocidad_m_s"], G)
                filas.append({"numero_correas": n, "potencia_accionamiento_kw": potencia, "G": G,
                              "tension_estatica_base_n": Ts,
                              **fuerzas_deflexion(Ts, base["tramo_libre_exacto_mm"], p["longitud_correa_mm"]),
                              "estado": "sensibilidad de fórmula; sin aprobación comercial ni cambio de montaje",
                              "cambio_numero_requiere_poleas": n != p["numero_correas"]})
    return filas
