"""Etapa 3A: análisis FEM del eje transversal biempotrado."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from config import RAIZ_PROYECTO
from estructural.analisis import (
    equilibrio_global,
    envolventes_caso,
    resolver_casos,
    resolver_instante_combinado,
    resumen_casos,
)
from estructural.cargas_eje import (
    cargar_serie_2c,
    tabla_fuerzas_rodamientos,
    validar_conservacion_reparto,
)
from estructural.config_eje import CONFIG_EJE
from estructural.geometria_eje import crear_malla, validar_segmentos
from estructural.viga_eb import SistemaViga
from estructural.visualizacion_eje import (
    graficar_comparacion,
    graficar_convergencia,
    graficar_cuerpo_libre,
    graficar_deformada,
    graficar_desplazamiento,
    graficar_diagramas,
    graficar_envolventes,
    graficar_geometria,
    graficar_reacciones,
)


SALIDA = RAIZ_PROYECTO / "resultados" / "etapa_3a_eje_transversal"


def _tabla_geometria() -> pd.DataFrame:
    filas = []
    for s in CONFIG_EJE.segmentos:
        fila = asdict(s)
        fila.update(area_m2=s.area_m2, inercia_m4=s.inercia_m4,
                    masa_kg=CONFIG_EJE.densidad_eje_kg_m3*s.area_m2*s.longitud_m)
        filas.append(fila)
    return pd.DataFrame(filas)


def _validar_equilibrio(casos, sistema) -> pd.DataFrame:
    filas = []
    for clave, caso in casos.items():
        for plano, solucion in (("vertical", caso.solucion_vertical), ("horizontal", caso.solucion_horizontal)):
            rf, rm = equilibrio_global(sistema, solucion)
            escala_f = np.maximum(np.sum(np.abs(solucion.cargas[0::2]), axis=0), 1.0)
            escala_m = np.maximum(np.sum(np.abs(solucion.cargas[0::2])*sistema.nodos_m[:, None], axis=0)
                                  + np.sum(np.abs(solucion.cargas[1::2]), axis=0), 1.0)
            rel_f = np.abs(rf)/escala_f; rel_m = np.abs(rm)/escala_m
            if max(float(rel_f.max()), float(rel_m.max())) > CONFIG_EJE.tolerancia_equilibrio_relativa:
                raise RuntimeError(f"El caso {clave}/{plano} no satisface equilibrio")
            if not np.allclose(solucion.desplazamientos[sistema.restringidos], 0.0, atol=1e-15):
                raise RuntimeError(f"El caso {clave}/{plano} viola los empotramientos")
            filas.append({"caso": clave, "plano": plano,
                          "residuo_fuerza_max_n": float(np.abs(rf).max()),
                          "residuo_momento_max_nm": float(np.abs(rm).max()),
                          "residuo_fuerza_relativo_max": float(rel_f.max()),
                          "residuo_momento_relativo_max": float(rel_m.max())})
    return pd.DataFrame(filas)


def _convergencia(tabla: pd.DataFrame, indice_critico: int) -> pd.DataFrame:
    filas = []
    for h_mm in (8.0, 4.0, 2.0, 1.0, 0.5):
        nodos = crear_malla(CONFIG_EJE, [], h_mm/1000)
        sistema = SistemaViga(nodos, CONFIG_EJE)
        caso = resolver_instante_combinado(sistema, tabla.iloc[indice_critico])
        s = caso.series.iloc[0]
        filas.append({"longitud_maxima_elemento_mm": h_mm, "numero_elementos": len(nodos)-1,
                      "desplazamiento_max_mm": s.desplazamiento_max_m*1e3,
                      "momento_max_nm": s.momento_max_nm,
                      "esfuerzo_max_mpa": s.esfuerzo_nominal_max_pa*1e-6,
                      "reaccion_fuerza_izquierda_n": np.hypot(s.reaccion_vertical_izquierda_n, s.reaccion_horizontal_izquierda_n),
                      "reaccion_fuerza_derecha_n": np.hypot(s.reaccion_vertical_derecha_n, s.reaccion_horizontal_derecha_n)})
    salida = pd.DataFrame(filas)
    for col in ("desplazamiento_max_mm", "momento_max_nm", "esfuerzo_max_mpa", "reaccion_fuerza_izquierda_n", "reaccion_fuerza_derecha_n"):
        ref = float(salida[col].iloc[-1]); salida[f"error_relativo_{col}"] = abs(salida[col]-ref)/max(abs(ref), 1e-15)
    return salida


def _diagramas_criticos(caso, sistema, indice: int) -> pd.DataFrame:
    filas = []
    for e in range(len(sistema.longitudes)):
        for extremo in (0, 1):
            filas.append({
                "x_m": caso.posiciones_extremos_m[e, extremo], "elemento": e,
                "extremo": extremo, "segmento": sistema.nombres_segmentos[e],
                "cortante_vertical_n": caso.fuerzas_extremo_verticales[e, 0 if extremo == 0 else 2, indice] * (1 if extremo == 0 else -1),
                "cortante_horizontal_n": caso.fuerzas_extremo_horizontales[e, 0 if extremo == 0 else 2, indice] * (1 if extremo == 0 else -1),
                "momento_vertical_nm": caso.momento_vertical_nm[e, extremo, indice],
                "momento_horizontal_nm": caso.momento_horizontal_nm[e, extremo, indice],
                "momento_resultante_nm": caso.momento_resultante_nm[e, extremo, indice],
                "esfuerzo_nominal_pa": caso.esfuerzo_nominal_pa[e, extremo, indice],
            })
    return pd.DataFrame(filas)


def ejecutar(graficos: bool = True) -> pd.DataFrame:
    SALIDA.mkdir(parents=True, exist_ok=True)
    validar_segmentos(CONFIG_EJE.segmentos, CONFIG_EJE.longitud_m)
    datos = cargar_serie_2c(CONFIG_EJE)
    tabla = tabla_fuerzas_rodamientos(datos, CONFIG_EJE)
    validar_conservacion_reparto(tabla)
    if tabla[["resultante_r1_fuera_rodamientos", "resultante_r2_fuera_rodamientos"]].any().any():
        raise RuntimeError("Una resultante de compactación quedó fuera de sus rodamientos")

    nodos = crear_malla(CONFIG_EJE, [])
    sistema = SistemaViga(nodos, CONFIG_EJE)
    casos, conservador = resolver_casos(sistema, tabla)
    equilibrio = _validar_equilibrio(casos, sistema)
    resumen = resumen_casos(casos, CONFIG_EJE)
    caso_c = casos["C"]
    indice_critico = int(caso_c.series.esfuerzo_nominal_max_pa.to_numpy().argmax())
    envolvente = envolventes_caso(caso_c, sistema)
    convergencia = _convergencia(tabla, indice_critico)

    parametros = CONFIG_EJE.como_dict()
    parametros.update({
        "modelo": "viga Euler-Bernoulli biempotrada, dos planos independientes",
        "numero_elementos": len(nodos)-1,
        "numero_intervalos_carga": len(tabla),
        "diametro_rosca_modelado_como_raiz_basica_m24x2_m": CONFIG_EJE.diametro_equivalente_rosca_m,
        "esfuerzo_reportado": "flexion nominal; no incluye concentraciones ni von Mises",
        "masa_rodillo_advertencia": "estimación desde cavidades axisimétricas del plano; omite ranuras exteriores",
        "convencion_rodillos": "R1 izquierdo, R2 derecho, según Etapa 3A",
        "tangencial_advertencia": "mu_eff=0.1 equivalente no validado experimentalmente",
    })
    (SALIDA/"parametros.json").write_text(json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")
    (SALIDA/"caso_constante_conservador.json").write_text(json.dumps(conservador, indent=2), encoding="utf-8")
    _tabla_geometria().to_csv(SALIDA/"geometria_segmentada.csv", index=False)
    pd.DataFrame([
        {"componente": "eje", "cantidad": 1, "masa_unitaria_kg": CONFIG_EJE.masa_eje_kg, "fuente": "geometría segmentada"},
        {"componente": "rodillo", "cantidad": 2, "masa_unitaria_kg": CONFIG_EJE.masa_rodillo_kg, "fuente": parametros["fuente_masa_rodillo"]},
    ]).to_csv(SALIDA/"resumen_masas.csv", index=False)
    tabla.to_csv(SALIDA/"fuerzas_rodamientos.csv", index=False)
    pd.concat([c.series for c in casos.values()], ignore_index=True).to_csv(SALIDA/"series_temporales_estructurales.csv", index=False)
    pd.concat([c.series[[x for x in c.series if x.startswith("reaccion_") or x.startswith("momento_") or x in ("caso", "tiempo_s", "angulo_grados")]] for c in casos.values()], ignore_index=True).to_csv(SALIDA/"reacciones.csv", index=False)
    resumen.to_csv(SALIDA/"resumen_maximos.csv", index=False)
    equilibrio.to_csv(SALIDA/"validacion_equilibrio.csv", index=False)
    envolvente.to_csv(SALIDA/"envolventes_caso_C.csv", index=False)
    _diagramas_criticos(caso_c, sistema, indice_critico).to_csv(SALIDA/"diagramas_instante_critico.csv", index=False)
    convergencia.to_csv(SALIDA/"convergencia_malla.csv", index=False)

    if graficos:
        graficar_geometria(CONFIG_EJE, SALIDA/"geometria_eje.png")
        graficar_cuerpo_libre(tabla, indice_critico, CONFIG_EJE, SALIDA/"diagrama_cuerpo_libre.png")
        graficar_reacciones(caso_c, SALIDA/"reacciones_revolucion.png")
        graficar_diagramas(caso_c, indice_critico, SALIDA/"diagramas_criticos.png")
        graficar_envolventes(envolvente, SALIDA/"envolvente_momento.png", SALIDA/"envolvente_esfuerzo.png")
        graficar_deformada(caso_c, sistema, indice_critico, SALIDA/"deformada_critica.png")
        graficar_desplazamiento(caso_c, SALIDA/"desplazamiento_revolucion.png")
        graficar_comparacion(resumen, SALIDA/"comparacion_casos.png")
        graficar_convergencia(convergencia, SALIDA/"convergencia_malla.png")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    resultado = ejecutar(not args.sin_graficos)
    print(resultado.to_string(index=False))
