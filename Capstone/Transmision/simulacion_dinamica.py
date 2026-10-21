"""Posproceso 5D.2 independiente; no importa ni ejecuta modelos previos."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from transmision.dinamica import evaluar, angulo_ramales


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def historicos():
    base = RAIZ/"resultados"
    return sorted([f for f in base.glob("*.*") if f.is_file()] + [
        f for carpeta in ("etapa_5c", "etapa_5d1") for f in (base/carpeta).rglob("*") if f.is_file()])


def ejecutar(salida=RAIZ/"resultados/etapa_5d2", signo_giro=1, condicional=True):
    salida = Path(salida).resolve()
    base = (RAIZ/"resultados").resolve()
    if salida == base or salida in base.parents or any(
        salida == base/c or base/c in salida.parents for c in ("etapa_5c", "etapa_5d1")):
        raise ValueError("Salida debe estar separada de históricos 5A–5D.1")
    if not condicional and (salida/"tensiones_y_fuerzas_condicionales_3c.csv").exists():
        raise ValueError("Para solo equilibrio, usar una salida distinta que no contenga resultados condicionales anteriores")
    p = leer_json(RAIZ/"parametros.json")
    h = leer_json(base/"resumen.json")
    c = leer_json(base/"etapa_5c/resumen.json")
    d1 = leer_json(base/"etapa_5d1/resumen.json")["principal"]
    fuente = RAIZ.parent/"Simulación_peletizadora/resultados/etapa_3c_acoplamiento/series_temporales_acopladas.csv"
    entradas = historicos()+[fuente, RAIZ/"parametros.json"]
    hashes = {str(f.resolve()): hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    if p["numero_correas"] != d1["numero_correas"] or p["centros_mm"] != c["ajuste_centros"]["centros_nominales_mm"]:
        raise ValueError("Parámetros incompatibles con históricos")
    with fuente.open(encoding="utf-8", newline="") as archivo:
        serie = [r for r in csv.DictReader(archivo) if r["modelo"] == "inclinacion"]
    if len(serie) != 1440 or [int(r["paso"]) for r in serie] != list(range(1440)) or any(r["convergio"].lower() != "true" for r in serie):
        raise ValueError("3C requiere 1440 estados consecutivos convergidos")
    Ts = d1["tension_estatica_base_n"]
    filas = []
    for r in serie:
        filas.append({"escenario": "historial_3c_inclinacion", "paso": int(r["paso"]),
                      "tiempo_s": float(r["tiempo_s"]), "angulo_grados": float(r["angulo_grados"]),
                      "potencia_3c_original_w": float(r["potencia_resistente_w"]),
                      **evaluar(float(r["torque_resistente_nm"]), Ts, p, signo_giro, condicional)})
    # Escenario externo ideal: P/v, sin factor de servicio ni pérdidas asumidas.
    v = h["etapa_5a"]["velocidad_correa_m_s"]
    torque_nominal = 1000*p["potencia_motor_kw"]/v*p["diametro_conducida_mm"]/2000
    nominal = {"escenario": "motor_nominal_ideal_externo_a_3c", "potencia_motor_kw": p["potencia_motor_kw"],
               "eficiencia_supuesta": 1., **evaluar(torque_nominal, Ts, p, signo_giro, condicional)}
    criticos = []
    criterios = [("torque_maximo", "torque_conducida_magnitud_nm", max)]
    if condicional:
        criterios += [("fuerza_resultante_maxima", "conducida_fr_n", max),
                      ("tension_floja_minima", "flojo_individual_n", min)]
    for etiqueta, campo, selector in criterios:
        validos = [r for r in filas if r.get(campo) is not None]
        if validos:
            criticos.append({"criterio": etiqueta, **selector(validos, key=lambda r: r[campo])})
    sensibilidad = []
    if condicional:
        for factor in (.8, 1., 1.2, 1.5):
            temporal = [evaluar(r["torque_conducida_magnitud_nm"], Ts*factor, p, signo_giro) for r in filas]
            for nombre, datos in (("historial_3c_inclinacion", temporal),
                                  ("motor_nominal_ideal_externo_a_3c", [evaluar(torque_nominal, Ts*factor, p, signo_giro)])):
                validos = [r for r in datos if r["admisible_no_negatividad"]]
                sensibilidad.append({"escenario": nombre, "factor_Ts_hipotetico": factor, "Ts_individual_n": Ts*factor,
                    "todos_no_negativos": len(validos) == len(datos),
                    "instantes_inadmisibles": len(datos)-len(validos),
                    "tension_floja_minima_n": min(r["flojo_individual_n"] for r in datos),
                    "conducida_fr_max_admisible_n": max((r["conducida_fr_n"] for r in validos), default=None),
                    "estado": "sensibilidad hipotética; no instrucción de tensado"})
    errores = [abs(r["delta_total_n"]*p["diametro_conducida_mm"]/2000-r["torque_conducida_magnitud_nm"]) for r in filas]
    errores_vectoriales = []
    if condicional:
        for r in filas+[nominal]:
            if r["admisible_no_negatividad"]:
                errores_vectoriales.extend((abs(r["conducida_fx_n"]+r["motriz_fx_n"]),
                    abs(r["conducida_fy_n"]+r["motriz_fy_n"]),
                    abs(r["conducida_fy_n"]-signo_giro*r["delta_total_n"]*math.sin(angulo_ramales(p))),
                    abs(p["numero_correas"]*(r["tenso_individual_n"]-r["flojo_individual_n"])-r["delta_total_n"])))
    resumen = {
        "modelo_condicional_activado": condicional, "intervalos_3c": len(filas), "alpha_grados": math.degrees(angulo_ramales(p)),
        "equilibrio": {"torque_max_nm": max(r["torque_conducida_magnitud_nm"] for r in filas),
            "torque_medio_nm": sum(r["torque_conducida_magnitud_nm"] for r in filas)/len(filas),
            "delta_total_max_n": max(r["delta_total_n"] for r in filas),
            "delta_total_media_n": sum(r["delta_total_n"] for r in filas)/len(filas),
            "delta_individual_max_n_reparto_uniforme": max(r["delta_individual_n"] for r in filas)},
        "casos_criticos_correlacionados": criticos, "motor_nominal_externo": nominal,
        "convenciones": {"x": "desde conducida hacia motor", "y": "perpendicular en el plano; z=x cruz y",
            "giro": signo_giro, "positivo": "antihorario visto desde +z; inferior tenso; Fy conducida positivo",
            "negativo": "horario visto desde +z; superior tenso; Fy conducida negativo",
            "motriz": "fuerza opuesta en el MISMO marco x,y; torque de correas opuesto al del motor",
            "torque_3c": "magnitud resistente; torque aplicado por correa tiene el signo de giro"},
        "hipotesis": ["Reparto uniforme entre tres correas; no deducido de equilibrio",
            "F_tenso+F_flojo=2Ts constante por hipótesis propia, no procedimiento Gates",
            "Modelo cuasiestático de fuerzas de tramos sin inercia distribuida y sin pérdidas",
            "Ts completo de 5D.1 tomado como referencia; no se identifica con tensión centrífuga ni se suma otro término",
            "No se comprueba adherencia: R Gates no se usa como razón dinámica límite",
            "Fuerzas solo interpretables cuando ambos ramales son no negativos; esto no garantiza ausencia de deslizamiento"],
        "limitaciones": ["Carga neta en plano de polea; no reacciones de rodamientos", "Pendientes rigidez, fricción y dinámica real",
            "3C conserva 516 rpm; transmisión ideal 517,857 rpm; no se reescala torque ni potencia original",
            "Motor nominal es escenario ideal externo con eficiencia 1, no máximo sincronizado de 3C"],
        "fuente_gates": "gates_vbelt_2004 solo para Ts heredado de 5D.1; modelo simétrico y vectorial son propios",
        "verificacion_modelo_condicional": ({"todos_estados_3c_no_negativos": all(r["admisible_no_negatividad"] for r in filas),
            "tension_floja_minima_n": min(r["flojo_individual_n"] for r in filas),
            "motor_nominal_no_negativo": nominal["admisible_no_negatividad"]} if condicional else None),
    }
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"diferencias_tensiones_3c.csv", [{k: r[k] for k in (
        "escenario", "paso", "tiempo_s", "angulo_grados", "torque_conducida_magnitud_nm", "delta_total_n", "delta_individual_n")} for r in filas])
    if condicional:
        guardar_csv(salida/"tensiones_y_fuerzas_condicionales_3c.csv", filas)
        guardar_csv(salida/"sensibilidad_Ts.csv", sensibilidad)
    guardar_csv(salida/"casos_criticos_correlacionados.csv", criticos)
    guardar_csv(salida/"motor_nominal_externo.csv", [nominal])
    conservados = all(hashlib.sha256(Path(n).read_bytes()).hexdigest() == valor for n, valor in hashes.items())
    if not conservados or max(errores) > 1e-10 or max(errores_vectoriales, default=0.) > 1e-9:
        raise RuntimeError("Falló conservación o equilibrio de torque")
    guardar_csv(salida/"validaciones.csv", [{"validacion": "equilibrio_torque", "cumple": True, "error_maximo": max(errores)},
        {"validacion": "sha256_entradas_conservados", "cumple": conservados, "error_maximo": 0.},
        {"validacion": "equilibrio_vectorial_y_reparto_si_condicional", "cumple": True,
         "error_maximo": max(errores_vectoriales, default=0.)}])
    (salida/"resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    (salida/"trazabilidad_sha256.json").write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados/etapa_5d2")
    parser.add_argument("--signo-giro", type=int, choices=(-1, 1), default=1)
    parser.add_argument("--solo-equilibrio", action="store_true")
    args = parser.parse_args()
    print(json.dumps(ejecutar(args.salida, args.signo_giro, not args.solo_equilibrio), indent=2, ensure_ascii=False))
