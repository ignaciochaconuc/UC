"""Extracto mínimo verificado visualmente en Gates 2004, impresas 56–57.

No es una tabla general: fuera de los puntos transcritos se exige revisar catálogo.
Se excluyen expresamente las columnas en cursiva, reservadas a Super HC MN.
"""

import math

FUENTE = {
    "titulo": "Gates Industrial V-Belt Drive Design Manual, 2004",
    "url": "https://www.gates.com/content/dam/documents-library/catalogs/industrial-v-belt-design-manual-kr.pdf",
    "paginas_impresas": [56, 57],
    "paginas_pdf_desde_uno": [58, 59],
    "fecha_consulta": "2026-10-21",
    "construccion": "SPA Super HC wrapped; no Super HC MN",
    "metodo": "A y CL: punto exacto; B: intervalo rotulado; G: menor factor del intervalo, sin interpolación",
}


def capacidad_catalogo(rpm: float, diametro_mm: float, relacion: float, longitud_mm: float) -> dict:
    if not all(math.isfinite(x) and x > 0 for x in (rpm, diametro_mm, relacion, longitud_mm)):
        raise ValueError("Entradas de catálogo positivas y finitas requeridas")
    if (rpm, diametro_mm, longitud_mm) != (1450.0, 100.0, 1600.0):
        raise ValueError("Punto no transcrito: revisar tablas SPA Super HC antes de ampliar el modelo")
    if not 1.95 <= relacion <= 3.38:
        raise ValueError("Relación fuera del intervalo transcrito 1,95–3,38")
    return {"basica_kw": 3.16, "adicional_relacion_kw": .54,
            "adicional_vida_kw": 0.0, "factor_longitud": .94}


def factor_abrazamiento_conservador(cociente: float) -> float:
    """Menor G de los extremos que encierran (D-d)/a; sin extrapolar."""
    puntos = ((0., 1.), (.1, .99), (.2, .97), (.3, .96), (.4, .94),
              (.5, .93), (.6, .91), (.7, .89), (.8, .87), (.9, .85),
              (1., .82), (1.1, .80), (1.2, .77), (1.3, .73), (1.4, .70), (1.5, .65))
    if not math.isfinite(cociente) or not 0 <= cociente <= 1.5:
        raise ValueError("Cociente fuera de la tabla de abrazamiento")
    for x, g in puntos:
        if cociente <= x:
            return g
    raise ValueError("Sin fila de abrazamiento")
