"""5E.2-A: cribado geométrico, sin resistencia ni selección definitiva."""
import math
from .calculos import positivos
from .chavetas import ligamento_cubo


def comparar_cubos(diametros, agujero_mm, ancho_mm, profundidades):
    if not diametros or not profundidades or len(set(diametros)) != len(diametros):
        raise ValueError("Listas explícitas no vacías y diámetros únicos requeridos")
    return [{"diametro_exterior_mm": D, "agujero_mm": agujero_mm,
             "ancho_chavetero_mm": ancho_mm, "profundidad_cubo_mm": q,
             **ligamento_cubo(D, agujero_mm, ancho_mm, q)}
            for D in diametros for q in profundidades]


def comprobar_aberturas(exterior_mm, diametro_abertura_mm, coordenadas=None,
                       fuente=None, solapamiento_axial=None):
    """Distancia mínima entre círculos proyectados; no resuelve unión 3D.

    Coordenadas cartesianas mm respecto al eje, nunca medidas en píxeles.
    Un hueco que intersecte la envolvente puede exigir rediseñar su transición.
    """
    positivos(exterior_mm=exterior_mm, diametro_abertura_mm=diametro_abertura_mm)
    if solapamiento_axial is not None and not isinstance(solapamiento_axial, bool):
        raise ValueError("Solapamiento axial debe ser bool o None")
    limite=(exterior_mm+diametro_abertura_mm)/2
    base={"diametro_exterior_mm": exterior_mm,
          "radio_centro_abertura_para_tangencia_mm": limite,
          "reserva_minima_exigida_mm": None,
          "solapamiento_axial_confirmado": solapamiento_axial}
    if coordenadas is None:
        return [{**base, "abertura": None, "separacion_proyectada_mm": None,
                 "interseccion_proyectada": None, "interferencia_3d": None,
                 "estado": "pendiente_coordenadas_CAD_y_extension_axial"}]
    if not fuente or len(coordenadas) != 8:
        raise ValueError("Ocho centros reales y fuente CAD trazable requeridos")
    puntos=[]
    for xy in coordenadas:
        if len(xy) != 2 or any(isinstance(v,bool) or not isinstance(v,(int,float))
                              or not math.isfinite(v) for v in xy):
            raise ValueError("Cada centro requiere x,y finitos en mm")
        puntos.append(tuple(xy))
    if len(set(puntos)) != 8:
        raise ValueError("Centros duplicados")
    resultados=[]
    for i,(x,y) in enumerate(puntos,1):
        gap=math.hypot(x,y)-limite
        resultados.append({**base,"abertura":i,"x_mm":x,"y_mm":y,
            "separacion_proyectada_mm":gap,"interseccion_proyectada":gap < 0,
            "interferencia_3d": (gap < 0) if solapamiento_axial is True else
                                 False if solapamiento_axial is False else None,
            "fuente":fuente,
            "estado":"cribado_proyectado_no_resistencia; tangencia no deja reserva"})
    return resultados
