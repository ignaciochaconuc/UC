"""5E.1 revisión Inventor vigente, sin sobrescribir la línea base original."""

import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_poleas import leer_csv, separar_cargas
from transmision.poleas import verificar_resistencia
from transmision.polea_inventor import verificar_inventor, torsion_cubo_liso

SALIDA = RAIZ/"resultados/etapa_5e1/revision_inventor_2026_10_21"


def ejecutar(salida=SALIDA):
    salida = Path(salida).resolve()
    if salida != SALIDA.resolve() and salida.is_relative_to((RAIZ/"resultados").resolve()):
        raise ValueError("Usar subcarpeta versionada de revisión para proteger la línea base")
    if salida == RAIZ or salida in RAIZ.parents:
        raise ValueError("No escribir en raíz de proyecto")
    fuente = RAIZ/"POLEA 1 (1).pdf"
    if not fuente.is_file():
        raise FileNotFoundError("Incorporar el plano vigente POLEA 1 (1).pdf")
    historicos = [f for f in (RAIZ/"resultados").rglob("*") if f.is_file() and not f.is_relative_to(SALIDA)]
    # Incluye la línea base 5E.1 y todas las etapas anteriores de los otros subsistemas.
    for carpeta in ("Simulación_peletizadora", "Analisis_matriz_eje_vertical"):
        historicos += [f for f in (RAIZ.parent/carpeta).rglob("*") if f.is_file() and not any(
            k in f.parts for k in ("__pycache__", ".pytest_cache"))]
    historicos += [fuente, RAIZ/"parametros_poleas.json", RAIZ/"parametros.json"]
    hashes = {str(f.resolve()): hashlib.sha256(f.read_bytes()).hexdigest() for f in historicos}
    config = json.loads((RAIZ/"parametros_poleas.json").read_text(encoding="utf-8"))
    p = config["poleas"]["conducida"]
    if p["documento_cad"] != fuente.name:
        raise ValueError("Usar exclusivamente el documento vigente")
    geometria = verificar_inventor(config)
    origen = RAIZ/"resultados/etapa_5d2"
    filas = leer_csv(origen/"casos_criticos_correlacionados.csv")+leer_csv(origen/"motor_nominal_externo.csv")
    cargas = [separar_cargas(f, "conducida", p["diametro_referencia_nominal_mm"]/2) for f in filas]
    torsiones = [{**c, **torsion_cubo_liso(c["torque_correas_firmado_nm"], config)} for c in cargas]
    disponibles = []
    for c in cargas:
        for v in verificar_resistencia(c, p, config["material"]):
            disponibles.append({"escenario": c["escenario"], "criterio": c["criterio"], **v})
    dimensiones = []
    # Fuente y superficies se registran separadas de los parámetros normativos/históricos.
    cotas = [
        ("diametro_referencia_nominal_mm", "nominal_diseno_5a", "Referencia de cinemática heredada; no acotada en este PDF"),
        ("diametro_crestas_gargantas_mm", "cota_cad", "Ø285,60 de crestas de garganta, no envolvente de pestañas"),
        ("diametro_pestanas_mm", "cota_cad", "Ø300 de contorno exterior máximo en vista frontal"),
        ("diametro_fondo_gargantas_mm", "cota_cad_interpretada", "Ø258 oculto coincide con raíz derivada de profundidad 13,80; no interior de llanta"),
        ("diametro_exterior_cubo_mm", "cota_cad", "Ø75 acotado en lateral y círculo oculto frontal"),
        ("diametro_interior_cubo_mm", "derivada_cota_cad", "Ø35=2 R17,50 del agujero circular; chavetero excluido"),
        ("longitud_cubo_mm", "cota_cad_envolvente", "78,60 total de cara saliente de cubo a cara posterior común"),
        ("ancho_llanta_cad_mm", "cota_cad_envolvente", "60 entre caras exteriores axiales de llanta con pestañas; no espesor de cuerpo"),
        ("numero_aberturas", "conteo_vista_frontal", "Seis aberturas circulares; no seis radios rectangulares"),
        ("diametro_aberturas_mm", "cota_patron_por_confirmar", "Ø70 en una abertura; semejanza del patrón visible, cotejar repetición CAD"),
        ("angulo_garganta_cad_grados", "cota_cad", "34 ±0,5° en corte A-A; discrepante con Gates"),
        ("profundidad_radial_garganta_mm", "cota_cad", "13,80 entre cresta y fondo radial de garganta"),
        ("espesor_axial_pestana_cota_mm", "cota_cad", "5 entre cara exterior pestaña y comienzo de crestas en vista lateral"),
        ("saliente_cubo_hasta_cara_interior_pestana_mm", "cota_cad", "23,60 desde extremo cubo hasta cara interior de pestaña; no saliente sobre cara exterior"),
        ("rosca_radial", "cota_cad", "M5x0.8 - 6H radial en cubo; no demuestra capacidad ni retención completa"),
    ]
    for k, estado, superficie in cotas:
        dimensiones.append({"parametro": k, "valor": p[k], "estado": estado, "superficies_y_uso": superficie})
    for k,v in p.items():
        if v is None:
            dimensiones.append({"parametro": k, "valor": None, "estado": "pendiente",
                "superficies_y_uso": "No aplicable numero_radios/geometria_radios/seccion_radios: cuerpo perforado; resto requiere confirmación CAD"})
    resumen = {"revision": p["revision_geometrica"], "fuente": fuente.name, "sha256_pdf": hashes[str(fuente.resolve())],
        "fuente_equipo_no_normativa": True, "geometria": geometria, "cargas_conducida": cargas,
        "torsion_parcial_cubo": torsiones, "otras_verificaciones": disponibles,
        "material": config["material"], "resistencia_aprobada": False, "fem_ejecutado": False,
        "factores_seguridad": None, "dimensiones": dimensiones,
        "advertencias": ["Usar geometría del PDF actual exclusivamente, sin completar cotas con revisión anterior",
            "Ø258 es fondo de garganta compatible con 13,80; diámetro interior real de llanta pendiente",
            "No confundir envolvente axial 78,60 con longitud activa de unión ni 60 con espesor de cuerpo",
            "Gates 38° para Ø280 vs Inventor 34±0,5°; compatibilidad normativa no aprobada",
            "Ø300 es envolvente de pestañas; no cambia Ø280 de referencia ni resultados históricos",
            "Torsión lisa parcial no es resistencia real: chavetero y rosca M5 restan sección y concentran tensión",
            "Diámetro/posición de centros de aligeramientos y espesores no se deducen midiendo píxeles"]}
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida/"dimensiones_confirmadas_y_pendientes.csv", dimensiones)
    guardar_csv(salida/"cargas_conducida.csv", cargas)
    guardar_csv(salida/"torsion_nominal_parcial_cubo.csv", torsiones)
    guardar_csv(salida/"verificaciones_pendientes.csv", [{**v, "faltantes": "; ".join(v["faltantes"]),
                   "resultado": json.dumps(v["resultado"])} for v in disponibles])
    guardar_csv(salida/"sensibilidad_heredada_separada.csv", [r for r in leer_csv(
        RAIZ/"resultados/etapa_5e1/sensibilidad_pretension_separada.csv") if r["polea"] == "conducida"])
    for nombre,obj in (("resumen",resumen),("parametros_utilizados",config),("trazabilidad_sha256",hashes)):
        (salida/f"{nombre}.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    (salida/"especificacion_fem_actualizada.md").write_text((RAIZ/"especificacion_fem_conducida_inventor.md").read_text(encoding="utf-8"),encoding="utf-8")
    conservados = all(hashlib.sha256(Path(n).read_bytes()).hexdigest() == h for n,h in hashes.items())
    if not conservados:
        raise RuntimeError("Se alteraron archivos originales")
    guardar_csv(salida/"validaciones.csv", [{"validacion": "SHA256_historicos_incluida_linea_base_5e1", "cumple": conservados},
        {"validacion": "fondo_garganta_coherente", "cumple": True},
        {"validacion": "normativa_y_resistencia_no_aprobadas", "cumple": True}])
    return resumen


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--salida",type=Path,default=SALIDA)
    args=parser.parse_args()
    r=ejecutar(args.salida)
    print(json.dumps({"geometria":r["geometria"],"torsiones":r["torsion_parcial_cubo"]},indent=2,ensure_ascii=False))
