"""Etapa 3B: desplazamiento, inclinación y holgura de los rodillos."""

from __future__ import annotations

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import pandas as pd

from config import PARAMETROS, RAIZ_PROYECTO
from estructural.analisis import resolver_casos
from estructural.cargas_eje import cargar_serie_2c, tabla_fuerzas_rodamientos
from estructural.config_eje import CONFIG_EJE
from estructural.geometria_eje import crear_malla
from estructural.holgura_rodillos import (
    calcular_cinematica_y_holgura,
    desplazamientos_rodamientos,
    resumen_holgura,
)
from estructural.viga_eb import SistemaViga
from estructural.visualizacion_holgura import (
    graficar_centros,
    graficar_comparacion_holguras,
    graficar_esquema_critico,
    graficar_holgura_instantanea,
    graficar_inclinaciones,
    graficar_rodamientos,
)


SALIDA = RAIZ_PROYECTO / "resultados" / "etapa_3b_holgura_rodillos"


def ejecutar(graficos: bool = True) -> pd.DataFrame:
    SALIDA.mkdir(parents=True, exist_ok=True)
    tabla_cargas = tabla_fuerzas_rodamientos(cargar_serie_2c(CONFIG_EJE), CONFIG_EJE)
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)
    casos, _ = resolver_casos(sistema, tabla_cargas)
    rodamientos = desplazamientos_rodamientos(casos, sistema)
    cinematica, holguras = calcular_cinematica_y_holgura(
        casos, sistema, PARAMETROS.separacion_minima_rodillo_matriz_m
    )
    resumen = resumen_holgura(cinematica, holguras)
    if len(cinematica[(cinematica.caso == "B") & (cinematica.rodillo == "izquierdo")]) != PARAMETROS.pasos_por_revolucion:
        raise RuntimeError("La serie temporal 3B no conserva los 1440 instantes")
    parametros = {
        "holgura_nominal_m": PARAMETROS.separacion_minima_rodillo_matriz_m,
        "convencion_vertical": "positivo aleja el rodillo de la matriz; g=g0+v",
        "modelo_rodillo": "cuerpo rígido, cinemática lineal entre centros de rodamientos",
        "ancho_axial_rodillo_m": .040,
        "matriz": "rígida e inmóvil",
        "contacto_acoplado": False,
        "advertencia_holgura_negativa": "incompatibilidad geométrica del modelo lineal desacoplado, no penetración física",
    }
    (SALIDA/"parametros.json").write_text(json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")
    rodamientos.to_csv(SALIDA/"desplazamientos_rodamientos.csv", index=False)
    cinematica.to_csv(SALIDA/"cinematica_rodillos.csv", index=False)
    holguras.to_csv(SALIDA/"holguras_estimadas.csv", index=False)
    resumen.to_csv(SALIDA/"resumen_estadistico.csv", index=False)
    if graficos:
        graficar_rodamientos(rodamientos, SALIDA/"desplazamientos_rodamientos.png")
        graficar_centros(cinematica, SALIDA/"desplazamientos_centros.png")
        graficar_inclinaciones(cinematica, SALIDA/"inclinacion_rodillos.png")
        graficar_holgura_instantanea(holguras, SALIDA/"holgura_minima_instantanea.png")
        graficar_comparacion_holguras(holguras, SALIDA/"comparacion_holguras.png")
        graficar_esquema_critico(casos, sistema, cinematica, holguras, SALIDA/"esquema_deformado_critico.png")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    print(ejecutar(not args.sin_graficos).to_string(index=False))
