"""Etapa 5E.2: predimensionamiento, sin modificar históricos ni aprobar uniones."""

import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_poleas import leer_csv
from transmision.chavetas import (FUENTES_CHAVETAS, candidata_normalizada,
    fuerza_tangencial_union, ligamento_cubo, comprobar_eje_real, sensibilidad_chaveta)

SALIDA=RAIZ/"resultados/etapa_5e2"
REVISION=RAIZ/"resultados/etapa_5e1/revision_ambas_poleas_2026_10_21"


def leer_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def ejecutar(parametros=RAIZ/"parametros_chavetas.json", salida=SALIDA):
    salida=Path(salida).resolve()
    if salida != SALIDA.resolve() and salida.is_relative_to((RAIZ/"resultados").resolve()):
        raise ValueError("Dentro de resultados usar únicamente etapa_5e2")
    if salida == RAIZ or salida in RAIZ.parents:
        raise ValueError("No usar raíz de proyecto como salida")
    actual=leer_json(RAIZ/"parametros_poleas.json")
    historico=leer_json(REVISION/"parametros_utilizados.json")
    if actual != historico:
        raise ValueError("Parámetros estructurales difieren de revisión conjunta; revisar línea base")
    p=leer_json(Path(parametros))
    longitudes=p["longitudes_activas_sensibilidad_mm"]
    if not longitudes:
        raise ValueError("Se requieren longitudes explícitas de sensibilidad")
    entradas=[f for f in (RAIZ/"resultados").rglob("*") if f.is_file() and not f.is_relative_to(SALIDA)]
    for carpeta in ("Simulación_peletizadora","Analisis_matriz_eje_vertical"):
        entradas += [f for f in (RAIZ.parent/carpeta).rglob("*") if f.is_file() and not any(
            k in f.parts for k in ("__pycache__",".pytest_cache"))]
    entradas += [RAIZ/"POLEA 1 (1).pdf",RAIZ/"POLEA 2.pdf",RAIZ/"parametros_poleas.json",Path(parametros)]
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    cargas=leer_csv(REVISION/"cargas_correlacionadas.csv")
    candidatas=[]; geometria=[]; fuerzas=[]; sensibilidad=[]; estados=[]
    for nombre in ("motriz","conducida"):
        plano=actual["poleas"][nombre]; u=p["uniones"][nombre]
        d=plano["diametro_interior_cubo_mm"]
        c=candidata_normalizada(d)
        eje=comprobar_eje_real(d,u["diametro_eje_real_mm"],u["fuente_eje_real"])
        b_cad=plano["ancho_chaveta_mm"]
        candidata={"polea":nombre, **c, "ancho_chavetero_cad_mm":b_cad,
            "ancho_cad_coincide_nominal": None if b_cad is None else b_cad == c["b_mm"],
            "ajuste_cubo_cad":plano.get("tolerancia_ancho_chavetero"),
            "eje_real_estado":eje["estado"]}
        candidatas.append(candidata)
        for etiqueta,q in (("nominal_candidata",c["profundidad_cubo_nominal_mm"]),
                           ("maximo_tolerancia_candidata",c["profundidad_cubo_max_mm"])):
            geometria.append({"polea":nombre,"escenario_geometrico":etiqueta,
                "profundidad_cubo_hipotetica_mm":q, **ligamento_cubo(plano["diametro_exterior_cubo_mm"],d,c["b_mm"],q)})
        for carga in (r for r in cargas if r["polea"] == nombre):
            T=float(carga["torque_correas_firmado_nm"])
            F=fuerza_tangencial_union(T,d)
            caso={"polea":nombre,"escenario":carga["escenario"],"criterio":carga["criterio"],
                "paso":carga["paso"],"tiempo_s":carga["tiempo_s"],"angulo_3c_grados":carga["angulo_3c_grados"],
                "torque_union_magnitud_nm":abs(T),"diametro_contacto_nominal_mm":d,"fuerza_tangencial_union_n":F,
                "estado":"equilibrio con diámetro nominal de agujero; eje real por confirmar"}
            fuerzas.append(caso)
            for r in sensibilidad_chaveta(T,d,c,longitudes,plano["longitud_cubo_mm"]):
                sensibilidad.append({**caso,**r})
        datos_ausentes=[k for k,v in u.items() if v is None]
        for comprobacion,estado,razon in (
            ("transmision_torque_chaveta","pendiente","Confirmar chaveta única, asiento y geometría activa; candidata no implica unión conforme"),
            ("cortante_chaveta_real","pendiente","Faltan largo activo y material; solo sensibilidad nominal calculada"),
            ("aplastamiento_cubo_y_eje_real","pendiente","Alturas efectivas y propiedades de cubo/eje/chaveta pendientes"),
            ("cubo_debilitado","incompatibilidad_geometrica_candidata" if nombre=="motriz" else "pendiente_resistencia",
             "Forma alta 10x8 no deja reserva geométrica confiable en Ø45/Ø38" if nombre=="motriz" else "Ligamento positivo no certifica resistencia, entallas ni contacto"),
            ("centrado_y_ajuste_eje_cubo",eje["estado"],"Diámetros reales y tolerancias de ajuste pendientes; no se confirma eje de motor por su potencia"),
            ("tornillo_m5_y_retencion_axial","pendiente","No se atribuye al M5 transmisión de torque ni carga axial sin montaje, grado, punta y engrane"),
            ("factor_seguridad","pendiente","Materiales y geometría local sin confirmar; no se calcula FS")):
            estados.append({"polea":nombre,"comprobacion":comprobacion,"estado":estado,"detalle":razon,
                "datos_union_ausentes":"; ".join(datos_ausentes)})
    resumen={"etapa":"5E.2","uniones_aprobadas":False,"fem_ejecutado":False,"factores_seguridad":None,
        "candidatas":candidatas,"ligamentos_geometricos":geometria,"fuerzas_correlacionadas":fuerzas,
        "estados_verificacion":estados,"fuentes":FUENTES_CHAVETAS,
        "material_cubo_candidato":actual["material"],"material_chaveta":p["material_chaveta"],
        "interpretacion_motriz":"Cubo Ø45/Ø38 no aprobable para chavetero alto candidato: centro 0,2 a 0 mm; envolvente de esquina ideal invade exterior. Revisar cubo/unión antes de fabricar; el CAD real no tiene profundidad confirmada.",
        "supuestos_sensibilidad":["Una chaveta transmite todo el torque, carga uniforme sobre longitud activa hipotética",
            "Longitudes 20/30/40/50 mm son escenarios de largo activo, no referencias comerciales ni largo total de extremos redondeados",
            "Contacto nominal hipotético en cubo h-t_eje=3 mm; contacto en eje 5 mm, no dimensiones reales confirmadas",
            "Presiones calculadas son medias; no tensiones de esquina ni cálculo integral del cubo",
            "La sensibilidad aritmética no elimina la incompatibilidad geométrica de motriz"],
        "normas":"DIN 6885-1:2021-11 identificada en ficha editorial; dimensiones de extracto técnico Ganter. ISO/R 773:1969 retirada; no se declara cumplimiento integral de norma de pago.",
        "spa_conducida":"34° CAD frente a 38° Gates: discrepancia pendiente, sin modificar",
        "pendientes_clave":["Ejes reales y planos de motor/árbol con diámetros y tolerancias",
            "Cubo motriz y chavetero rediseñados o unión alternativa justificada; no seleccionar automáticamente",
            "Geometría local, profundidad, radios, chaveta activa y material trazable",
            "Funciones separadas: torque por chaveta, centrado por ajuste, retención axial diseñada"]}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,filas in (("candidatas_normalizadas",candidatas),("ligamentos_cubo",geometria),
                         ("fuerzas_union_correlacionadas",fuerzas),("sensibilidad_longitud_activa",sensibilidad),
                         ("estado_verificaciones",estados)):
        guardar_csv(salida/f"{nombre}.csv",filas)
    for nombre,obj in (("resumen",resumen),("parametros_utilizados",p),("fuentes",FUENTES_CHAVETAS),
                       ("trazabilidad_sha256",hashes)):
        (salida/f"{nombre}.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    (salida/"ecuaciones_y_limites.md").write_text((RAIZ/"metodologia_chavetas.md").read_text(encoding="utf-8"),encoding="utf-8")
    conservados=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    if not conservados:
        raise RuntimeError("Se alteró una entrada histórica")
    guardar_csv(salida/"validaciones.csv",[{"validacion":n,"cumple":True} for n in (
        "SHA256_historicos_conservados","candidatas_filas_diametros_verificados","largo_hipotetico_no_supera_envolvente",
        "escenarios_3c_y_motor_separados","sin_aprobacion_ni_FS_ficticio")])
    return resumen


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--parametros",type=Path,default=RAIZ/"parametros_chavetas.json")
    parser.add_argument("--salida",type=Path,default=SALIDA)
    args=parser.parse_args()
    r=ejecutar(args.parametros,args.salida)
    print(json.dumps({"candidatas":r["candidatas"],"ligamentos":r["ligamentos_geometricos"],
                      "fuerzas":r["fuerzas_correlacionadas"],"conclusion":r["interpretacion_motriz"]},indent=2,ensure_ascii=False))
