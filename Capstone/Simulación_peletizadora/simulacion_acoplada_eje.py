"""Etapa 3C: equilibrio acoplado contacto geométrico--deformación del eje."""

from __future__ import annotations

import argparse
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from config import PARAMETROS, RAIZ_PROYECTO
from simulacion import obtener_geometria
from estructural.acoplamiento import (
    ConfiguracionAcoplamiento,
    resumen_modelo_acoplado,
    simular_acoplado,
    tabla_rodamientos_desde_serie,
)
from estructural.analisis import equilibrio_global, resolver_caso_cargas_rodamientos, resolver_casos
from estructural.cargas_eje import cargar_serie_2c, tabla_fuerzas_rodamientos
from estructural.config_eje import CONFIG_EJE
from estructural.geometria_eje import crear_malla
from estructural.holgura_rodillos import calcular_cinematica_y_holgura
from estructural.viga_eb import SistemaViga
from estructural.visualizacion_acoplamiento import (
    comparar_fuerzas, comparar_holguras, comparar_torque_potencia,
    deformaciones_inclinaciones, historial_convergencia, holguras_evolucion,
    perfil_radial_critico, superposicion_critica,
)


SALIDA = RAIZ_PROYECTO / "resultados" / "etapa_3c_acoplamiento"


def _resumen_desacoplado(base: pd.DataFrame, estructural, holguras: pd.DataFrame) -> dict:
    fila = {
        "modelo": "desacoplado_2C_3A_3B", "instantes": len(base), "todos_convergieron": True,
        "iteraciones_max": 0, "fuerza_total_max_n": base.fuerza_total_n.max(),
        "fuerza_total_media_n": base.fuerza_total_n.mean(), "torque_max_nm": base.torque_resistente_nm.max(),
        "torque_medio_nm": base.torque_resistente_nm.mean(), "potencia_max_w": base.potencia_resistente_w.max(),
        "potencia_media_w": base.potencia_resistente_w.mean(),
        "momento_flector_max_nm": estructural.series.momento_max_nm.max(),
        "esfuerzo_nominal_max_pa": estructural.series.esfuerzo_nominal_max_pa.max(),
        "desplazamiento_eje_max_m": estructural.series.desplazamiento_max_m.max(),
    }
    for n, nombre in ((1, "izquierdo"), (2, "derecho")):
        h = holguras[(holguras.caso == "C") & (holguras.rodillo == nombre)]
        gaps = h[["holgura_extremo_izquierdo_m", "holgura_centro_m", "holgura_extremo_derecho_m"]].to_numpy()
        fila.update({f"holgura_r{n}_min_m": gaps.min(), f"holgura_r{n}_media_m": gaps.mean(), f"holgura_r{n}_max_m": gaps.max(),
                     f"desplazamiento_centro_r{n}_min_m": h.holgura_centro_m.min()-PARAMETROS.separacion_minima_rodillo_matriz_m,
                     f"desplazamiento_centro_r{n}_max_m": h.holgura_centro_m.max()-PARAMETROS.separacion_minima_rodillo_matriz_m,
                     f"inclinacion_r{n}_abs_max_rad": np.nan,
                     f"diferencia_holgura_extremos_r{n}_max_m": np.max(np.abs(gaps[:, 2]-gaps[:, 0])),
                     f"fuerza_r{n}_max_n": base[f"fuerza_rodillo_{n}_n"].max(),
                     f"fuerza_r{n}_media_n": base[f"fuerza_rodillo_{n}_n"].mean()})
    return fila


def _validaciones(sistema, casos_acoplados, series, historiales, detalle, reproduccion) -> pd.DataFrame:
    filas = []
    for nombre, caso in casos_acoplados.items():
        for plano, sol in (("vertical", caso.solucion_vertical), ("horizontal", caso.solucion_horizontal)):
            rf, rm = equilibrio_global(sistema, sol)
            escala_f = np.maximum(np.sum(np.abs(sol.cargas[0::2]), axis=0), 1.0)
            escala_m = np.maximum(np.sum(np.abs(sol.cargas[0::2])*sistema.nodos_m[:, None], axis=0)
                                  + np.sum(np.abs(sol.cargas[1::2]), axis=0), 1.0)
            relativo = max(float(np.max(np.abs(rf)/escala_f)), float(np.max(np.abs(rm)/escala_m)))
            filas.append({"validacion": f"equilibrio_{nombre}_{plano}", "valor": relativo, "cumple": relativo < CONFIG_EJE.tolerancia_equilibrio_relativa})
        h = historiales[nombre]
        final = h.sort_values("iteracion").groupby("paso").tail(1)
        filas.append({"validacion": f"residuo_compatibilidad_{nombre}", "valor": final.residuo_compatibilidad_m.max(),
                      "cumple": final.residuo_compatibilidad_m.max() <= 1e-9})
        filas.append({"validacion": f"cambio_fuerza_{nombre}", "valor": final.cambio_fuerza_relativo.max(),
                      "cumple": final.cambio_fuerza_relativo.max() <= 1e-5})
        filas.append({"validacion": f"1440_instantes_{nombre}", "valor": len(series[nombre]), "cumple": len(series[nombre]) == 1440})
        area_max = np.pi*(PARAMETROS.diametro_agujero_m/2)**2
        d = detalle[nombre]
        filas.append({"validacion": f"areas_geometricas_{nombre}", "valor": d.area_superpuesta_m2.max(),
                      "cumple": bool(((d.area_superpuesta_m2 >= 0) & (d.area_superpuesta_m2 <= area_max*(1+1e-12))).all())})
    filas.append({"validacion": "reproduccion_3C0_3A", "valor": reproduccion[0], "cumple": reproduccion[0] < 1e-12})
    filas.append({"validacion": "reproduccion_3C0_3B", "valor": reproduccion[1], "cumple": reproduccion[1] < 1e-12})
    return pd.DataFrame(filas)


def _eventos_extremos(series, estructurales) -> pd.DataFrame:
    filas = []
    for modelo, s in series.items():
        for n in (1, 2):
            especificaciones = {
                "fuerza_max": (f"fuerza_rodillo_{n}_n", "max", "N", "resultante"),
                "desplazamiento_centro_max": (f"desplazamiento_centro_r{n}_m", "max", "m", "centro"),
                "desplazamiento_centro_min": (f"desplazamiento_centro_r{n}_m", "min", "m", "centro"),
                "inclinacion_abs_max": (f"inclinacion_r{n}_rad", "abs", "rad", "rodillo"),
            }
            for metrica, (col, operacion, unidad, posicion) in especificaciones.items():
                indice = s[col].abs().idxmax() if operacion == "abs" else (s[col].idxmax() if operacion == "max" else s[col].idxmin())
                r = s.loc[indice]
                filas.append({"modelo": modelo, "rodillo": n, "metrica": metrica, "valor": r[col], "unidad": unidad,
                              "tiempo_s": r.tiempo_s, "angulo_grados": r.angulo_grados, "posicion": posicion})
            cols = [f"holgura_izquierda_r{n}_m", f"holgura_centro_r{n}_m", f"holgura_derecha_r{n}_m"]
            matriz = s[cols].to_numpy(); plano = int(np.argmin(matriz)); i, j = np.unravel_index(plano, matriz.shape)
            r = s.iloc[i]
            filas.append({"modelo": modelo, "rodillo": n, "metrica": "holgura_min", "valor": matriz[i, j], "unidad": "m",
                          "tiempo_s": r.tiempo_s, "angulo_grados": r.angulo_grados,
                          "posicion": ("extremo_izquierdo", "centro", "extremo_derecho")[j]})
        e = estructurales[modelo].series
        for metrica, col, xcol, unidad in (
            ("momento_flector_max", "momento_max_nm", "x_momento_max_m", "N m"),
            ("esfuerzo_nominal_max", "esfuerzo_nominal_max_pa", "x_esfuerzo_max_m", "Pa"),
            ("desplazamiento_eje_max", "desplazamiento_max_m", "x_desplazamiento_max_m", "m"),
        ):
            i = e[col].idxmax(); r = e.loc[i]
            filas.append({"modelo": modelo, "rodillo": 0, "metrica": metrica, "valor": r[col], "unidad": unidad,
                          "tiempo_s": r.tiempo_s, "angulo_grados": r.angulo_grados, "posicion": f"x={r[xcol]:.9g} m"})
    return pd.DataFrame(filas)


def _sensibilidad(coordenadas, sistema) -> pd.DataFrame:
    filas = []
    configuraciones = [
        ("cuadratura", ConfiguracionAcoplamiento(orden_cuadratura=o)) for o in (32, 64, 128)
    ] + [
        ("tolerancia", ConfiguracionAcoplamiento(tolerancia_holgura_m=t)) for t in (1e-8, 1e-9, 1e-10)
    ] + [
        ("relajacion", ConfiguracionAcoplamiento(relajacion=l)) for l in (.35, .5, .7)
    ]
    for estudio, cfg_local in configuraciones:
        s, h, _ = simular_acoplado(coordenadas, sistema, "inclinacion", cfg_local, pasos=1)
        filas.append({"estudio": estudio, "orden": cfg_local.orden_cuadratura,
                      "tolerancia_holgura_m": cfg_local.tolerancia_holgura_m,
                      "relajacion": cfg_local.relajacion, "convergio": bool(s.convergio.all()),
                      "iteraciones": int(s.iteraciones.max()), "fuerza_total_n": float(s.fuerza_total_n.iloc[0]),
                      "holgura_minima_m": float(min(s.holgura_minima_r1_m.iloc[0], s.holgura_minima_r2_m.iloc[0])),
                      "residuo_final_m": float(h.iloc[-1].residuo_compatibilidad_m)})
    return pd.DataFrame(filas)


def ejecutar(graficos: bool = True) -> pd.DataFrame:
    SALIDA.mkdir(parents=True, exist_ok=True)
    coordenadas, fuente = obtener_geometria("auto")
    sistema = SistemaViga(crear_malla(CONFIG_EJE, []), CONFIG_EJE)
    cfg = ConfiguracionAcoplamiento()

    # 3C-0: reconstrucción desacoplada con las cargas originales.
    base = cargar_serie_2c(CONFIG_EJE)
    casos_base, _ = resolver_casos(sistema, tabla_fuerzas_rodamientos(base, CONFIG_EJE))
    cin_base, holg_base = calcular_cinematica_y_holgura(casos_base, sistema, PARAMETROS.separacion_minima_rodillo_matriz_m)
    hist_3a = pd.read_csv(RAIZ_PROYECTO/"resultados"/"etapa_3a_eje_transversal"/"series_temporales_estructurales.csv")
    hist_3b = pd.read_csv(RAIZ_PROYECTO/"resultados"/"etapa_3b_holgura_rodillos"/"holguras_estimadas.csv")
    ref3a = hist_3a[hist_3a.caso == "C_combinado"].desplazamiento_max_m.to_numpy()
    nuevo3a = casos_base["C"].series.desplazamiento_max_m.to_numpy()
    ref3b = hist_3b[(hist_3b.caso == "C") & (hist_3b.rodillo == "izquierdo")].holgura_minima_m.to_numpy()
    nuevo3b = holg_base[(holg_base.caso == "C") & (holg_base.rodillo == "izquierdo")].holgura_minima_m.to_numpy()
    reproduccion = (float(np.max(np.abs(ref3a-nuevo3a))), float(np.max(np.abs(ref3b-nuevo3b))))

    series = {}; historiales = {}; detalles = {}; estructurales = {}
    for nombre in ("uniforme", "inclinacion"):
        serie, historia, detalle = simular_acoplado(coordenadas, sistema, nombre, cfg)
        if len(serie) != PARAMETROS.pasos_por_revolucion or not serie.convergio.all():
            fallos = serie[~serie.convergio] if "convergio" in serie else serie
            raise RuntimeError(f"El modelo {nombre} no convergió en todos los instantes: {len(fallos)} fallos")
        tabla = tabla_rodamientos_desde_serie(serie, CONFIG_EJE)
        estructural = resolver_caso_cargas_rodamientos(sistema, tabla, f"3C_{nombre}")
        series[nombre], historiales[nombre], detalles[nombre], estructurales[nombre] = serie, historia, detalle, estructural

    resumen = pd.DataFrame([
        _resumen_desacoplado(base, casos_base["C"], holg_base),
        resumen_modelo_acoplado(series["uniforme"], estructurales["uniforme"]),
        resumen_modelo_acoplado(series["inclinacion"], estructurales["inclinacion"]),
    ])
    referencia = resumen.iloc[0]
    for metrica in ("fuerza_total_max_n", "fuerza_total_media_n", "torque_max_nm", "torque_medio_nm",
                    "potencia_max_w", "potencia_media_w", "momento_flector_max_nm", "esfuerzo_nominal_max_pa", "desplazamiento_eje_max_m"):
        resumen[f"cambio_vs_desacoplado_{metrica}_porcentaje"] = 100*(resumen[metrica]/referencia[metrica]-1)

    validaciones = _validaciones(sistema, estructurales, series, historiales, detalles, reproduccion)
    # Una nueva solución en 0° representa también 360° por periodicidad geométrica.
    cierre, _, _ = simular_acoplado(coordenadas, sistema, "inclinacion", cfg, pasos=1)
    error_periodico = abs(float(cierre.fuerza_total_n.iloc[0])-float(series["inclinacion"].fuerza_total_n.iloc[0]))
    validaciones.loc[len(validaciones)] = {"validacion": "periodicidad_0_360_fuerza_n", "valor": error_periodico, "cumple": error_periodico < 1e-6}
    sensibilidad = _sensibilidad(coordenadas, sistema)
    if not validaciones.cumple.all():
        raise RuntimeError("Falló una validación 3C; revisar validaciones.csv")

    parametros = {**cfg.__dict__, "presion_maxima_pa": PARAMETROS.presion_maxima_pa,
                  "holgura_referencia_m": PARAMETROS.separacion_minima_rodillo_matriz_m,
                  "espesor_biomasa_m": PARAMETROS.espesor_biomasa_m,
                  "huella_tangencial": "simétrica", "fuente_geometria": fuente,
                  "advertencia": "presión impuesta; no es una ley constitutiva presión-holgura"}
    (SALIDA/"parametros.json").write_text(json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.concat(series.values(), ignore_index=True).to_csv(SALIDA/"series_temporales_acopladas.csv", index=False)
    pd.concat([s[[c for c in s if "fuerza" in c or "resultante" in c or c in ("modelo","paso","tiempo_s","angulo_grados")]] for s in series.values()], ignore_index=True).to_csv(SALIDA/"fuerzas_resultantes.csv", index=False)
    pd.concat([s[[c for c in s if "holgura" in c or "inclinacion" in c or "desplazamiento" in c or c in ("modelo","paso","tiempo_s","angulo_grados")]] for s in series.values()], ignore_index=True).to_csv(SALIDA/"holguras_inclinaciones.csv", index=False)
    pd.concat([e.series for e in estructurales.values()], ignore_index=True).to_csv(SALIDA/"resultados_estructurales.csv", index=False)
    pd.concat(historiales.values(), ignore_index=True).to_csv(SALIDA/"historial_convergencia.csv", index=False)
    pd.concat(detalles.values(), ignore_index=True).to_csv(SALIDA/"superposicion_instantes_criticos.csv", index=False)
    resumen.to_csv(SALIDA/"resumen_comparativo.csv", index=False)
    validaciones.to_csv(SALIDA/"validaciones.csv", index=False)
    sensibilidad.to_csv(SALIDA/"sensibilidad_numerica.csv", index=False)
    _eventos_extremos(series, estructurales).to_csv(SALIDA/"eventos_extremos.csv", index=False)

    if graficos:
        holguras_evolucion(series["inclinacion"], SALIDA/"evolucion_holguras.png")
        comparar_holguras(holg_base, series["uniforme"], series["inclinacion"], SALIDA/"comparacion_holguras.png")
        comparar_fuerzas(base, series["uniforme"], series["inclinacion"], SALIDA/"comparacion_fuerzas.png")
        comparar_torque_potencia(base, series["uniforme"], series["inclinacion"], SALIDA/"comparacion_torque_potencia.png")
        deformaciones_inclinaciones(series["uniforme"], series["inclinacion"], SALIDA/"deformaciones_inclinaciones.png")
        historial_convergencia(historiales["inclinacion"], SALIDA/"historial_convergencia.png")
        perfil_radial_critico(series["inclinacion"], SALIDA/"perfil_radial_critico.png")
        superposicion_critica(detalles["inclinacion"], series["inclinacion"], SALIDA/"superposicion_huella_deformada.png")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    print(ejecutar(not args.sin_graficos).to_string(index=False))
