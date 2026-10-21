"""5E.1: importar cargas verificadas, inventariar geometría y preparar resistencia."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from transmision.poleas import validar_parametros, verificar_resistencia


def leer_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def leer_csv(p):
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def separar_cargas(fila, polea, radio_mm):
    """Importa una fila sincronizada; audita Fr y T con el radio propio."""
    if polea not in ("motriz", "conducida"):
        raise ValueError("Polea desconocida")
    if not math.isfinite(radio_mm) or radio_mm <= 0:
        raise ValueError("Radio de referencia positivo requerido")
    if fila.get("admisible_no_negatividad", "").lower() != "true":
        raise ValueError("No usar como carga estructural un caso no admisible en 5D.2")
    delta = float(fila["delta_total_n"])
    T = float(fila[f"torque_correas_{polea}_firmado_nm"])
    fx, fy, fr = (float(fila[f"{polea}_{c}_n"]) for c in ("fx", "fy", "fr"))
    if not all(math.isfinite(x) for x in (delta, T, fx, fy, fr)) or delta < 0:
        raise ValueError("Cargas no finitas o magnitud de delta negativa")
    if not math.isclose(abs(T), delta*radio_mm/1000, abs_tol=1e-9, rel_tol=1e-10):
        raise ValueError("Torque incompatible con el radio propio de la polea")
    if not math.isclose(fr, math.hypot(fx, fy), rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError("Resultante no coincide con componentes correlacionadas")
    return {"polea": polea, "escenario": fila["escenario"], "criterio": fila.get("criterio", "motor_nominal_externo"),
            "paso": int(fila["paso"]) if fila.get("paso") else None,
            "tiempo_s": float(fila["tiempo_s"]) if fila.get("tiempo_s") else None,
            "angulo_3c_grados": float(fila["angulo_grados"]) if fila.get("angulo_grados") else None,
            "radio_referencia_mm": radio_mm, "delta_total_n": delta,
            "torque_correas_firmado_nm": T, "fx_n": fx, "fy_n": fy, "fr_n": fr,
            "origen_torque": "equilibrio de torque 5D.2", "origen_fuerzas": "cierre simétrico condicional 5D.2"}


def ejecutar(parametros=RAIZ/"parametros_poleas.json", salida=RAIZ/"resultados/etapa_5e1"):
    salida = Path(salida).resolve()
    base = RAIZ/"resultados"
    if salida != (base/"etapa_5e1").resolve() and salida.is_relative_to(base.resolve()):
        raise ValueError("Dentro de resultados usar exclusivamente etapa_5e1 para proteger históricos")
    if salida in RAIZ.resolve().parents or salida == RAIZ.resolve():
        raise ValueError("No usar una raíz de proyecto como salida")
    config = leer_json(Path(parametros))
    entradas = [f for f in base.glob("*.*") if f.is_file()]
    for carpeta in ("etapa_5c", "etapa_5d1", "etapa_5d2"):
        entradas += [f for f in (base/carpeta).rglob("*") if f.is_file()]
    otro = RAIZ.parent/"Analisis_matriz_eje_vertical"
    entradas += [f for f in otro.rglob("*") if f.is_file() and not any(x in f.parts for x in ("__pycache__", ".pytest_cache"))]
    contacto = RAIZ.parent/"Simulación_peletizadora"
    entradas += [f for f in contacto.rglob("*") if f.is_file() and not any(x in f.parts for x in ("__pycache__", ".pytest_cache"))]
    entradas += [RAIZ/"parametros.json", Path(parametros), RAIZ/"referencias.bib", RAIZ/"especificacion_fem_poleas.md"]
    hashes = {str(f.resolve()): hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    geometria = leer_csv(base/"etapa_5c/poleas_y_gargantas.csv")
    criticos = leer_csv(base/"etapa_5d2/casos_criticos_correlacionados.csv")
    nominal = leer_csv(base/"etapa_5d2/motor_nominal_externo.csv")
    cargas, verificaciones, pendientes, conocidas = [], [], [], []
    for polea in ("motriz", "conducida"):
        g = next(r for r in geometria if r["polea"] == polea)
        dimension = config["poleas"][polea]
        validar_parametros(dimension, config["material"], float(g["diametro_exterior_cad_mm"]))
        conocidas.append({"polea": polea, "diametro_referencia_mm": float(g["diametro_referencia_mm"]),
            "diametro_exterior_cad_reportado_mm": float(g["diametro_exterior_cad_mm"]), "gargantas": int(g["numero_gargantas"]),
            "ancho_llanta_normativo_no_medido_mm": float(g["ancho_llanta_nominal_mm"]),
            "fuente": "resultados/etapa_5c/poleas_y_gargantas.csv; CAD de polea no disponible",
            "estado": "diámetros reportados y dimensiones normativas; estructura interna pendiente"})
        for k, v in dimension.items():
            if v is None:
                pendientes.append({"polea": polea, "parametro": k, "estado": "pendiente",
                                   "nota": "confirmar aplicabilidad: disco o radios, unión real y plano CAD"})
        for r in criticos+nominal:
            carga = separar_cargas(r, polea, float(g["diametro_referencia_mm"])/2)
            cargas.append(carga)
            for check in verificar_resistencia(carga, dimension, config["material"]):
                verificaciones.append({"polea": polea, "escenario": carga["escenario"], "criterio": carga["criterio"], **check})
    # Sensibilidades heredadas son envolventes, sin componentes o tiempo correlacionados.
    sensibilidad = []
    for r in leer_csv(base/"etapa_5d2/sensibilidad_Ts.csv"):
        for polea in ("motriz", "conducida"):
            sensibilidad.append({**r, "polea": polea,
                "fr_max_heredada_n": float(r["conducida_fr_max_admisible_n"]) if r["conducida_fr_max_admisible_n"] else None,
                "torque_correlacionado_nm": None, "tiempo_correlacionado_s": None,
                "uso_resistencia": "pendiente de estado completo; no combinar envolvente con torque nominal"})
    archivos_cad = [str(f.relative_to(RAIZ.parent)) for f in RAIZ.parent.rglob("*")
                    if f.is_file() and f.suffix.lower() in (".step", ".stp", ".ipt", ".iam", ".dwg", ".dxf", ".pdf")]
    inventario = {"archivos_cad_y_planos_detectados": archivos_cad,
        "hallazgo": "Solo DXF de matriz; no CAD o plano acotado de poleas en los formatos buscados",
        "exclusiones": ["Ø50 de matriz no define agujero de polea", "Ø58 y 12 mm de resalte de árbol no definen cubo de polea",
                        "36 mm de espesor matriz no define cuerpo de polea", "Vanos supuestos 50/100 mm no definen voladizo real",
                        "Sy 1045 +QT del análisis de matriz/árbol no se transfiere al AISI 1045 de suministro desconocido"],
        "evidencias": ["../Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional/README.md",
                       "../Analisis_matriz_eje_vertical/Etapa_4D_FEM_preliminar/README.md", "resultados/etapa_5c/poleas_y_gargantas.csv"]}
    resumen = {"etapa": "5E.1", "estado": "preparación estructural; sin aceptación de resistencia",
        "geometria_conocida": conocidas, "material": config["material"], "cargas": cargas,
        "verificaciones": verificaciones, "inventario": inventario,
        "fem_ejecutado": False, "factores_seguridad": None,
        "propiedades_material_pendientes": [k for k,v in config["material"].items() if v is None],
        "limitaciones": ["Cargas condicionales heredadas, no cargas experimentales",
                         "No se conoce topología del cuerpo ni cubo", "No asignar tensiones ni FS sin geometría y material",
                         "No se incluyen peso ni fuerzas de rotación propias de la polea sin densidad y volumen",
                         "Torques propios motriz y conducida; no se usa Fr*radio como torque de transmisión",
                         "Gates respalda gargantas y Ts, no propiedades de 1045 ni fórmulas de resistencia"]}
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"cargas_poleas.csv", cargas)
    guardar_csv(salida/"geometria_conocida.csv", conocidas)
    guardar_csv(salida/"dimensiones_pendientes.csv", pendientes)
    guardar_csv(salida/"sensibilidad_pretension_separada.csv", sensibilidad)
    guardar_csv(salida/"verificaciones.csv", [{**r, "faltantes": "; ".join(r["faltantes"]),
                    "resultado": json.dumps(r["resultado"], ensure_ascii=False)} for r in verificaciones])
    (salida/"especificacion_fem.md").write_text((RAIZ/"especificacion_fem_poleas.md").read_text(encoding="utf-8"), encoding="utf-8")
    for nombre, obj in (("resumen", resumen), ("parametros_utilizados", config), ("inventario_fuentes", inventario), ("trazabilidad_sha256", hashes)):
        (salida/f"{nombre}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    conservados = all(hashlib.sha256(Path(n).read_bytes()).hexdigest() == v for n, v in hashes.items())
    if not conservados:
        raise RuntimeError("Se alteró una entrada histórica")
    guardar_csv(salida/"validaciones.csv", [{"validacion": nombre, "cumple": True} for nombre in (
        "torques_a_radio_propio_y_resultantes_correlacionadas", "cargas_nominales_y_sensibilidades_separadas", "sha256_entradas_conservadas")])
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parametros", type=Path, default=RAIZ/"parametros_poleas.json")
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados/etapa_5e1")
    args = parser.parse_args()
    r = ejecutar(args.parametros, args.salida)
    print(json.dumps({"estado": r["estado"], "cargas": r["cargas"], "fem_ejecutado": r["fem_ejecutado"]}, indent=2, ensure_ascii=False))
