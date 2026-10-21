"""5D.2: equilibrio de torque y cierre simétrico hipotético de tensiones.

Modelo cuasiestático sin inercia del tramo, sin pérdidas y sin término centrífugo
adicional. No es una ley de Gates ni una comprobación de adherencia.
"""

import math
from .calculos import geometria, positivos
from .tension_estatica import entero_positivo


def diferencia_tensiones(torque_nm, radio_m, numero_correas):
    positivos(radio_m=radio_m)
    entero_positivo(numero_correas)
    if isinstance(torque_nm, bool) or not math.isfinite(torque_nm) or torque_nm < 0:
        raise ValueError("Torque debe ser magnitud finita no negativa; invertir giro mediante signo")
    total = torque_nm/radio_m
    return {"delta_total_n": total, "delta_individual_n": total/numero_correas}


def reparto_simetrico(Ts_n, delta_individual_n):
    positivos(Ts_n=Ts_n)
    if not math.isfinite(delta_individual_n) or delta_individual_n < 0:
        raise ValueError("Diferencia de tensiones finita no negativa requerida")
    tenso, flojo = Ts_n+delta_individual_n/2, Ts_n-delta_individual_n/2
    return {"tenso_individual_n": tenso, "flojo_individual_n": flojo,
            "admisible_no_negatividad": flojo >= 0,
            "estado_modelo": "condicional_no_negativo" if flojo >= 0 else "no_admisible_tension_negativa"}


def fuerzas_poleas(tenso_n, flojo_n, numero_correas, alpha_rad, signo_giro=1):
    entero_positivo(numero_correas)
    if signo_giro not in (-1, 1) or isinstance(signo_giro, bool):
        raise ValueError("Signo de giro debe ser +1 o -1")
    if not all(math.isfinite(x) for x in (tenso_n, flojo_n, alpha_rad)) or not 0 <= alpha_rad < math.pi/2 or flojo_n < 0 or tenso_n < flojo_n:
        raise ValueError("Tensiones no negativas ordenadas y ángulo geométrico válido requeridos")
    # Mismo marco x,y para ambas poleas. CCW (+z) en conducida => ramal inferior tenso.
    c, s = math.cos(alpha_rad), math.sin(alpha_rad)
    superior = flojo_n if signo_giro == 1 else tenso_n
    inferior = tenso_n if signo_giro == 1 else flojo_n
    sx, sy = numero_correas*superior*c, -numero_correas*superior*s
    ix, iy = numero_correas*inferior*c, numero_correas*inferior*s
    fx, fy = sx+ix, sy+iy
    return {"conducida_superior_fx_n": sx, "conducida_superior_fy_n": sy,
            "conducida_inferior_fx_n": ix, "conducida_inferior_fy_n": iy,
            "conducida_fx_n": fx, "conducida_fy_n": fy, "conducida_fr_n": math.hypot(fx, fy),
            "motriz_fx_n": -fx, "motriz_fy_n": -fy, "motriz_fr_n": math.hypot(fx, fy)}


def angulo_ramales(p):
    g = geometria(p["diametro_motriz_mm"], p["diametro_conducida_mm"], p["centros_mm"], p["rpm_motor"])
    return math.radians((180-g["abrazamiento_motriz_grados"])/2)


def evaluar(torque_nm, Ts_n, p, signo_giro=1, condicional=True):
    if signo_giro not in (-1, 1) or isinstance(signo_giro, bool):
        raise ValueError("Signo de giro debe ser +1 o -1")
    radio = p["diametro_conducida_mm"]/2000
    delta = diferencia_tensiones(torque_nm, radio, p["numero_correas"])
    fila = {"torque_conducida_magnitud_nm": torque_nm, "signo_giro": signo_giro,
            "torque_correas_conducida_firmado_nm": signo_giro*torque_nm,
            "torque_correas_motriz_firmado_nm": -signo_giro*delta["delta_total_n"]*p["diametro_motriz_mm"]/2000,
            **delta}
    if not condicional:
        return fila
    reparto = reparto_simetrico(Ts_n, delta["delta_individual_n"])
    fila.update({"Ts_individual_n": Ts_n, **reparto})
    if reparto["admisible_no_negatividad"]:
        fila.update(fuerzas_poleas(reparto["tenso_individual_n"], reparto["flojo_individual_n"],
                                   p["numero_correas"], angulo_ramales(p), signo_giro))
    else:
        # No exportar fuerzas físicamente interpretables a partir de tensión negativa.
        fila.update({k: None for k in fuerzas_poleas(0., 0., p["numero_correas"], angulo_ramales(p), signo_giro)})
    return fila
