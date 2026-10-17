"""Etapa 3D: resistencia estática y fatiga preliminar del eje transversal."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from config import RAIZ_PROYECTO
from estructural.acoplamiento import tabla_rodamientos_desde_serie
from estructural.analisis import resolver_caso_cargas_rodamientos, resolver_casos
from estructural.cargas_eje import cargar_serie_2c, tabla_fuerzas_rodamientos
from estructural.config_eje import CONFIG_EJE
from estructural.geometria_eje import crear_malla
from estructural.resistencia_fatiga import (
    ENTALLAS, MATERIALES, analizar_resistencia, secciones_criticas,
)
from estructural.viga_eb import SistemaViga
from estructural.visualizacion_resistencia import (
    comparar_factores, esfuerzo_longitudinal, historial_tension, mapa_secciones, sensibilidad_kt,
)


SALIDA = RAIZ_PROYECTO / "resultados" / "etapa_3d_resistencia_fatiga"


def _resumen_factores(sens: pd.DataFrame, nominal: pd.DataFrame) -> pd.DataFrame:
    filas = []
    ubicaciones = nominal.set_index(["caso", "seccion"])
    for claves, g in sens.groupby(["caso", "material", "entalla"], sort=False):
        for criterio, columna in (("fluencia", "factor_seguridad_fluencia"), ("goodman", "factor_seguridad_goodman")):
            validos = g[np.isfinite(g[columna])]
            if len(validos):
                r = validos.loc[validos[columna].idxmin()]
                x = ubicaciones.loc[(r.caso, r.seccion), "x_m"]
                valor = r[columna]
            else:
                r = g.iloc[0]; x = ubicaciones.loc[(r.caso, r.seccion), "x_m"]; valor = np.nan
            filas.append({"caso": claves[0], "material": claves[1], "entalla": claves[2],
                          "criterio": criterio, "factor_seguridad_minimo": valor,
                          "seccion_gobernante": r.seccion, "x_m": x})
    return pd.DataFrame(filas)


def _sensibilidad_angular(caso, sistema) -> pd.DataFrame:
    filas = []
    for n in (36, 72, 144):
        nominal, _, _, sens = analizar_resistencia({"3C_inclinacion": caso}, sistema, n)
        d = sens[(sens.material == "parametrico_medio") & (sens.entalla == "sensibilidad_moderada")]
        filas.append({"numero_puntos_materiales": n,
                      "esfuerzo_nominal_max_pa": nominal.esfuerzo_nominal_max_pa.max(),
                      "factor_fluencia_min": d.factor_seguridad_fluencia.min(),
                      "factor_goodman_min": d.factor_seguridad_goodman.min()})
    return pd.DataFrame(filas)


def ejecutar(graficos: bool = True) -> pd.DataFrame:
    SALIDA.mkdir(parents=True, exist_ok=True)
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)

    serie_3c = pd.read_csv(RAIZ_PROYECTO/"resultados"/"etapa_3c_acoplamiento"/"series_temporales_acopladas.csv")
    serie_3c = serie_3c[serie_3c.modelo == "inclinacion"].reset_index(drop=True)
    caso_3c = resolver_caso_cargas_rodamientos(
        sistema, tabla_rodamientos_desde_serie(serie_3c, CONFIG_EJE), "3C_inclinacion"
    )
    casos_3a, _ = resolver_casos(
        sistema, tabla_fuerzas_rodamientos(cargar_serie_2c(CONFIG_EJE), CONFIG_EJE)
    )
    casos = {"3C_inclinacion": caso_3c, "3A_C_referencia": casos_3a["C"],
             "3A_D_conservador": casos_3a["D"]}

    nominal, historiales, ciclos, sensibilidad = analizar_resistencia(casos, sistema, 144)
    factores = _resumen_factores(sensibilidad, nominal)
    angular = _sensibilidad_angular(caso_3c, sistema)

    # La reconstrucción debe reproducir el máximo nominal FEM de cada caso.
    verificaciones = []
    for nombre, caso in casos.items():
        fem = float(caso.series.esfuerzo_nominal_max_pa.max())
        reconstruido = float(nominal[nominal.caso == nombre].esfuerzo_nominal_max_pa.max())
        error = abs(reconstruido-fem)/max(fem, 1.0)
        verificaciones.append({"validacion": f"reproduce_maximo_{nombre}", "error_relativo": error, "cumple": error < 2e-3})
    verificaciones.append({"validacion": "refinamiento_angular_72_144", "error_relativo":
                           abs(angular.esfuerzo_nominal_max_pa.iloc[1]-angular.esfuerzo_nominal_max_pa.iloc[2])/
                           angular.esfuerzo_nominal_max_pa.iloc[2], "cumple": True})
    validaciones = pd.DataFrame(verificaciones)
    if not validaciones.cumple.all():
        raise RuntimeError("Falló la reconstrucción de esfuerzos 3D")

    pd.DataFrame([asdict(s) for s in secciones_criticas(CONFIG_EJE)]).to_csv(SALIDA/"secciones_criticas.csv", index=False)
    pd.DataFrame([asdict(m) for m in MATERIALES]).to_csv(SALIDA/"escenarios_material.csv", index=False)
    pd.DataFrame([{**asdict(e), "kf": e.kf} for e in ENTALLAS]).to_csv(SALIDA/"escenarios_entallas.csv", index=False)
    nominal.to_csv(SALIDA/"esfuerzos_nominales_secciones.csv", index=False)
    historiales.to_csv(SALIDA/"historiales_tension_puntos_materiales.csv", index=False)
    ciclos.to_csv(SALIDA/"conteo_rainflow.csv", index=False)
    sensibilidad.to_csv(SALIDA/"sensibilidad_material_entallas.csv", index=False)
    factores.to_csv(SALIDA/"resumen_factores_seguridad.csv", index=False)
    angular.to_csv(SALIDA/"sensibilidad_refinamiento_angular.csv", index=False)
    validaciones.to_csv(SALIDA/"validaciones.csv", index=False)
    parametros = {
        "numero_puntos_materiales": 144,
        "criterio_estatico": "flexión uniaxial local; von Mises=abs(sigma) sin torsión",
        "criterio_fatiga": "rainflow periódico y Goodman modificado preliminar",
        "tratamiento_media_compresiva": "se ignora su beneficio en Goodman",
        "torque_matriz_aplicado_al_eje": False,
        "advertencia": "Sy, Sut, Se, Kt y q son escenarios paramétricos, no propiedades verificadas",
    }
    (SALIDA/"parametros.json").write_text(json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")

    if graficos:
        esfuerzo_longitudinal(nominal, SALIDA/"esfuerzo_longitudinal.png")
        mapa_secciones(nominal, SALIDA/"secciones_criticas.png")
        historial_tension(historiales, nominal, SALIDA/"historial_tension_critica.png")
        comparar_factores(sensibilidad, SALIDA/"comparacion_resistencia_estatica.png", SALIDA/"comparacion_fatiga.png")
        sensibilidad_kt(sensibilidad, SALIDA/"sensibilidad_concentracion.png")
    return factores


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    resultado = ejecutar(not args.sin_graficos)
    print(resultado.to_string(index=False))
