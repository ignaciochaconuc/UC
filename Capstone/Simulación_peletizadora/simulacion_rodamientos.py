"""Etapa 4A: verificación preliminar de los rodamientos de los rodillos."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import hashlib

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from config import PARAMETROS, RAIZ_PROYECTO
from estructural.config_eje import CONFIG_EJE
from estructural.rodamientos import (
    CONFIG_RODAMIENTO,
    ALTERNATIVAS_RODAMIENTO,
    OBJETIVOS_VIDA_H,
    capacidad_requerida_para_vida,
    cargas_rodamientos_3c,
    cargas_rodamientos_conservadoras,
    resumen_rodamientos,
    sensibilidad_vida,
    velocidad_rodillo_rpm,
)
from estructural.visualizacion_rodamientos import (
    cargas_revolucion,
    comparar_cargas,
    factor_estatico,
    sensibilidad_vida as grafico_sensibilidad,
    vida_l10,
)


SALIDA = RAIZ_PROYECTO / "resultados" / "etapa_4a_rodamientos_rodillos"
RUTA_3C = RAIZ_PROYECTO / "resultados" / "etapa_3c_acoplamiento" / "series_temporales_acopladas.csv"


def _validar_reparto(serie: pd.DataFrame, cargas: pd.DataFrame) -> pd.DataFrame:
    """Comprueba fuerza y momento de la compactación, antes de sumar el peso."""
    filas = []
    for numero, nombres, posiciones in (
        (1, ("R1_A", "R1_B"), CONFIG_EJE.rodamientos_izquierdos_m),
        (2, ("R2_A", "R2_B"), CONFIG_EJE.rodamientos_derechos_m),
    ):
        a = cargas[cargas.rodamiento == nombres[0]].reset_index(drop=True)
        b = cargas[cargas.rodamiento == nombres[1]].reset_index(drop=True)
        fuerza = serie[f"fuerza_rodillo_{numero}_n"].to_numpy()
        radio = serie[f"resultante_radial_r{numero}_m"].to_numpy()
        x_f = CONFIG_EJE.centro_matriz_m + (-radio if numero == 1 else radio)
        suma = a.carga_vertical_compactacion_n.to_numpy() + b.carga_vertical_compactacion_n.to_numpy()
        momento = (
            a.carga_vertical_compactacion_n.to_numpy()*posiciones[0]
            + b.carga_vertical_compactacion_n.to_numpy()*posiciones[1]
        )
        escala_f = max(float(np.max(np.abs(fuerza))), 1.0)
        escala_m = max(float(np.max(np.abs(fuerza*x_f))), 1.0)
        error_f = float(np.max(np.abs(suma-fuerza))/escala_f)
        error_m = float(np.max(np.abs(momento-fuerza*x_f))/escala_m)
        filas.extend((
            {"validacion": f"conservacion_fuerza_rodillo_{numero}", "error_relativo": error_f,
             "cumple": error_f < 1e-12},
            {"validacion": f"conservacion_momento_rodillo_{numero}", "error_relativo": error_m,
             "cumple": error_m < 1e-12},
        ))
    filas.extend((
        {"validacion": "intervalos_3C_inclinacion", "error_relativo": abs(len(serie)-1440)/1440,
         "cumple": len(serie) == 1440},
        {"validacion": "resultados_3C_no_modificados", "error_relativo": 0.0,
         "cumple": RUTA_3C.exists()},
        {"validacion": "carga_axial_externa_nula", "error_relativo": 0.0,
         "cumple": bool((cargas.carga_axial_n == 0).all())},
    ))
    return pd.DataFrame(filas)


def _tabla_objetivos(resumen: pd.DataFrame, rpm: float) -> pd.DataFrame:
    filas = []
    for _, row in resumen.iterrows():
        for horas in OBJETIVOS_VIDA_H:
            requerida = capacidad_requerida_para_vida(row.carga_dinamica_equivalente_n, rpm, horas)
            filas.append({
                "rodamiento": row.rodamiento,
                "objetivo_vida_h": horas,
                "capacidad_dinamica_requerida_n": requerida,
                "margen_C_referencia": CONFIG_RODAMIENTO.capacidad_dinamica_n/requerida,
            })
    return pd.DataFrame(filas)


def _documentar_montaje() -> str:
    return """# Condiciones de montaje y operación pendientes — KOYO/JTEKT 6206 2RS

- El eje transversal permanece estacionario y el rodillo gira con los anillos exteriores. La pista exterior ve una carga circunferencial; el ajuste debe seleccionarse con las tablas del fabricante para la carga, material y temperatura reales. No se prescribe aquí una tolerancia.
- Confirmar metrología y acabado de los asientos de 30 mm y alojamientos de 62 mm, además de hombros, radios, coaxialidad y método de retención axial.
- Inconsistencia geométrica a resolver: con centros en 59,5 y 210,5 mm y ancho B=16 mm, los rodamientos exteriores ocupan axialmente 51,5--67,5 y 202,5--218,5 mm. El modelo actual deja los asientos de Ø30 mm en 53,1--91,5 y 178,5--216,9 mm, por lo que 1,6 mm de cada anillo interior exterior coincide con un alivio de Ø29,2 mm. Confirmar si es un voladizo/alivio intencional o corregir plano y modelo.
- Dos rodamientos rígidos por rodillo separados 24 mm pueden sufrir carga de borde si sus centros se desalinean. Verificar la desalineación admisible del KOYO 6206 2RS frente a la inclinación calculada en 3C, la rigidez real de alojamientos y las tolerancias acumuladas.
- No se ha impuesto precarga ni holgura interna. Definirlas después de conocer ajustes, gradientes térmicos y expansión diferencial; evitar que ambos rodamientos bloqueen indebidamente la dilatación axial.
- Confirmar que no existan empujes axiales de proceso o montaje. Si aparecen, deben recalcularse P y P0 con factores X, Y y e documentados para la variante elegida.
- Validar grasa, intervalo de relubricación, compatibilidad de sellos 2RS, temperatura, velocidad, polvo, humedad y contaminación de biomasa. La vida ISO 281 exportada no incluye esos efectos.
- La ficha KOYO indica dimensiones de montaje de referencia da=35--37,5 mm, Da máximo 57 mm y radio ra máximo 1 mm. Comprobar los hombros reales contra estas dimensiones; no equivalen a tolerancias de ajuste.
"""


def ejecutar(graficos: bool = True) -> pd.DataFrame:
    SALIDA.mkdir(parents=True, exist_ok=True)
    hash_3c = hashlib.sha256(RUTA_3C.read_bytes()).hexdigest()
    historica = pd.read_csv(RUTA_3C)
    serie = historica[historica.modelo == "inclinacion"].reset_index(drop=True)
    rpm = velocidad_rodillo_rpm(
        PARAMETROS.rpm_matriz, PARAMETROS.centro_radial_rodillo_m,
        PARAMETROS.diametro_rodillo_m/2,
    )
    cargas = cargas_rodamientos_3c(serie, CONFIG_EJE)
    conservadoras = cargas_rodamientos_conservadoras(CONFIG_EJE)
    resumen = resumen_rodamientos(cargas, CONFIG_RODAMIENTO, rpm)
    resumen_conservador = resumen_rodamientos(conservadoras, CONFIG_RODAMIENTO, rpm)
    sensibilidad = sensibilidad_vida(resumen, CONFIG_RODAMIENTO, rpm)
    objetivos = _tabla_objetivos(resumen, rpm)
    comparacion = pd.concat([
        resumen_rodamientos(cargas, alternativa, rpm)
        for alternativa in ALTERNATIVAS_RODAMIENTO
    ], ignore_index=True)
    comparacion_conservadora = pd.concat([
        resumen_rodamientos(conservadoras, alternativa, rpm)
        for alternativa in ALTERNATIVAS_RODAMIENTO
    ], ignore_index=True)
    seleccion = []
    for alternativa in ALTERNATIVAS_RODAMIENTO:
        tabla = comparacion[comparacion.modelo == alternativa.modelo_referencia]
        fila = {**asdict(alternativa), "seleccionado": alternativa == CONFIG_RODAMIENTO,
                "estado": "seleccionado" if alternativa == CONFIG_RODAMIENTO else "referencia_historica",
                "vida_minima_l10h": float(tabla.l10_horas.min())}
        for horas in OBJETIVOS_VIDA_H:
            fila[f"satisface_{int(horas)}_h_todos_los_apoyos"] = bool((tabla.l10_horas >= horas).all())
        seleccion.append(fila)
    critico = resumen.loc[resumen.carga_dinamica_equivalente_n.idxmax()]
    objetivos_critico = objetivos[objetivos.rodamiento == critico.rodamiento].copy()
    objetivos_critico["objetivo_obligatorio"] = False
    for alternativa in ALTERNATIVAS_RODAMIENTO:
        objetivos_critico[f"satisface_{alternativa.fuente}"] = (
            objetivos_critico.capacidad_dinamica_requerida_n <= alternativa.capacidad_dinamica_n)
    validaciones = _validar_reparto(serie, cargas)
    validaciones.loc[len(validaciones)] = [
        "SHA256_3C_conservado", 0.0,
        hashlib.sha256(RUTA_3C.read_bytes()).hexdigest() == hash_3c]
    if not validaciones.cumple.all():
        raise RuntimeError("Falló una validación de la Etapa 4A")

    cargas.to_csv(SALIDA/"cargas_temporales_rodamientos.csv", index=False)
    conservadoras.to_csv(SALIDA/"cargas_caso_conservador_3a_d.csv", index=False)
    resumen.to_csv(SALIDA/"resumen_rodamientos_nominal.csv", index=False)
    resumen_conservador.to_csv(SALIDA/"resumen_rodamientos_conservador.csv", index=False)
    pd.concat([resumen, resumen_conservador], ignore_index=True).to_csv(
        SALIDA/"comparacion_nominal_conservador.csv", index=False)
    sensibilidad.to_csv(SALIDA/"sensibilidad_vida.csv", index=False)
    objetivos.to_csv(SALIDA/"capacidad_requerida_objetivos_vida.csv", index=False)
    comparacion.to_csv(SALIDA/"comparacion_fag_koyo_nominal.csv", index=False)
    comparacion_conservadora.to_csv(SALIDA/"comparacion_fag_koyo_conservador.csv", index=False)
    pd.DataFrame(seleccion).to_csv(SALIDA/"tabla_seleccion_rodamientos.csv", index=False)
    objetivos_critico.to_csv(SALIDA/"objetivos_vida_rodamiento_critico.csv", index=False)
    validaciones.to_csv(SALIDA/"validaciones.csv", index=False)
    (SALIDA/"condiciones_montaje_operacion.md").write_text(_documentar_montaje(), encoding="utf-8")
    parametros = {
        "rodamiento_referencia": asdict(CONFIG_RODAMIENTO),
        "rodamiento_seleccionado": asdict(CONFIG_RODAMIENTO),
        "cantidad_seleccionada": 4,
        "alternativas": seleccion,
        "objetivos_vida_exploratorios_h": OBJETIVOS_VIDA_H,
        "requisito_vida_obligatorio_h": None,
        "sha256_serie_3c": hash_3c,
        "norma_vida_basica": "ISO 281:2007; L10=(C/P)^3 para rodamiento de bolas",
        "rpm_matriz": PARAMETROS.rpm_matriz,
        "radio_contacto_m": PARAMETROS.centro_radial_rodillo_m,
        "radio_rodillo_m": PARAMETROS.diametro_rodillo_m/2,
        "rpm_rodillo_sin_deslizamiento": rpm,
        "factores_velocidad_evaluados": [.9, 1.0, 1.1],
        "factores_deslizamiento_cinematico_evaluados": [.9, 1.0, 1.1],
        "factores_carga_evaluados": [.8, 1.0, 1.2, 1.5],
        "factores_capacidad_dinamica_evaluados": [.9, 1.0, 1.1],
        "carga_axial_externa_n": 0.0,
        "exponente_vida_bolas": 3,
        "intervalos_por_revolucion": len(serie),
        "masa_rodillo_kg": CONFIG_EJE.masa_rodillo_kg,
        "advertencia": "Vida básica L10 al 90 %; no es vida ajustada ni garantía individual.",
    }
    (SALIDA/"parametros.json").write_text(
        json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([asdict(CONFIG_RODAMIENTO)]).to_csv(SALIDA/"fuente_tecnica_rodamiento.csv", index=False)
    (SALIDA/"ejecucion_resumen.txt").write_text(resumen.to_string(index=False), encoding="utf-8")

    if graficos:
        cargas_revolucion(cargas, SALIDA/"carga_radial_revolucion.png")
        comparar_cargas(resumen, SALIDA/"carga_maxima_vs_equivalente.png")
        vida_l10(resumen, SALIDA/"vida_nominal_l10h.png")
        factor_estatico(resumen, resumen_conservador, SALIDA/"factor_estatico.png")
        critico = str(resumen.loc[resumen.l10_horas.idxmin(), "rodamiento"])
        grafico_sensibilidad(sensibilidad, critico, SALIDA/"sensibilidad_vida.png")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    print(ejecutar(not args.sin_graficos).to_string(index=False))
