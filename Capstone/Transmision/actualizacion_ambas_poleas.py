"""5E.1 revisión conjunta Inventor; importación sin regenerar históricos."""

import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_poleas import leer_csv, separar_cargas
from transmision.polea_inventor import verificar_inventor, verificar_motriz_inventor, torsion_cubo_liso_polea
from transmision.poleas import verificar_resistencia

SALIDA = RAIZ/"resultados/etapa_5e1/revision_ambas_poleas_2026_10_21"


def ejecutar(salida=SALIDA):
    salida=Path(salida).resolve()
    if salida != SALIDA.resolve() and salida.is_relative_to((RAIZ/"resultados").resolve()):
        raise ValueError("Dentro de resultados usar exclusivamente la nueva revisión conjunta")
    if salida == RAIZ or salida in RAIZ.parents:
        raise ValueError("No usar raíz de proyecto como salida")
    config=json.loads((RAIZ/"parametros_poleas.json").read_text(encoding="utf-8"))
    documentos={"motriz":"POLEA 2.pdf","conducida":"POLEA 1 (1).pdf"}
    for polea,nombre in documentos.items():
        if not (RAIZ/nombre).is_file():
            raise FileNotFoundError(f"Incorporar plano vigente {nombre}")
        if config["poleas"][polea]["documento_cad"] != nombre:
            raise ValueError("Fuente geométrica incompatible con revisión vigente")
    entradas=[f for f in (RAIZ/"resultados").rglob("*") if f.is_file() and not f.is_relative_to(SALIDA)]
    for carpeta in ("Simulación_peletizadora","Analisis_matriz_eje_vertical"):
        entradas += [f for f in (RAIZ.parent/carpeta).rglob("*") if f.is_file() and not any(
            k in f.parts for k in ("__pycache__",".pytest_cache"))]
    entradas += [RAIZ/n for n in documentos.values()]+[RAIZ/"parametros_poleas.json",RAIZ/"parametros.json"]
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    geometria={"motriz":verificar_motriz_inventor(config),"conducida":verificar_inventor(config)}
    origen=RAIZ/"resultados/etapa_5d2"
    casos=leer_csv(origen/"casos_criticos_correlacionados.csv")+leer_csv(origen/"motor_nominal_externo.csv")
    cargas=[]; torsiones=[]; verificaciones=[]; dimensiones=[]; fuentes=[]
    no_aplicables={"numero_radios","geometria_radios","seccion_radios_mm"}
    for polea in documentos:
        p=config["poleas"][polea]
        fuentes.append({"polea":polea,"archivo":documentos[polea],"sha256":hashes[str((RAIZ/documentos[polea]).resolve())],
                        "tipo_fuente":"plano interno del equipo, no normativa","pagina":1})
        for k,v in p.items():
            if k == "origen_cotas":
                continue
            estado="pendiente" if v is None else "confirmado_plano"
            if k in no_aplicables:
                estado="no_aplicable_cuerpo_aligerado"
            elif k == "diametro_referencia_nominal_mm":
                estado="nominal_diseno_5a"
            elif k == "diametro_interior_cubo_mm":
                estado="derivado_radio_acotado"
            elif k == "diametro_aberturas_mm":
                estado="cota_en_una_abertura_patron_por_cotejar"
            dimensiones.append({"polea":polea,"parametro":k,"valor":v,"estado":estado,
                "fuente":documentos[polea],"interpretacion":p["origen_cotas"].get(k,
                    "Pendiente de cota y función resistente" if v is None else "Vista frontal/lateral/corte A-A del plano vigente")})
        for fila in casos:
            c=separar_cargas(fila,polea,p["diametro_referencia_nominal_mm"]/2)
            cargas.append(c)
            torsion=torsion_cubo_liso_polea(c["torque_correas_firmado_nm"],config,polea)
            torsiones.append({**c,**torsion})
            verificaciones.append({"polea":polea,"escenario":c["escenario"],"criterio":c["criterio"],
                "comprobacion":"torsion_cubo_liso_parcial","estado":"calculado_nominal_condicionado",
                "faltantes":[],"resultado":torsion,"alcance":torsion["limitaciones"]})
            for v in verificar_resistencia(c,p,config["material"]):
                verificaciones.append({"polea":polea,"escenario":c["escenario"],"criterio":c["criterio"],**v})
    resumen={"revision":"ambas_poleas_inventor_2026_10_21","fuentes":fuentes,"geometria":geometria,
        "material":config["material"],"cargas":cargas,"torsion_nominal_parcial":torsiones,
        "verificaciones":verificaciones,"fem_ejecutado":False,"resistencia_aprobada":False,"factores_seguridad":None,
        "convenciones":"Marco y cargas heredadas de 5D.2; torque de correas con signo y radio propio de cada polea",
        "limitaciones":["No transferir cotas entre planos de piezas distintas",
            "34° motriz coincide nominalmente con Gates, sin aprobar toda la polea; 34° conducida discrepa con 38°",
            "Secciones lisas omiten chaveteros y M5; no son esfuerzos máximos reales",
            "AISI 1045 sin condición o propiedades asignadas", "Patrones de aberturas y espesores internos pendientes",
            "10 JS9 de la motriz es ancho de chavetero; no longitud ni altura efectiva de chaveta",
            "62 y 78,60 son envolventes, no longitudes activas de unión"]}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,filas in (("fuentes_geometricas",fuentes),("dimensiones_confirmadas_pendientes",dimensiones),
                         ("cargas_correlacionadas",cargas),("torsion_parcial_cubos",torsiones)):
        guardar_csv(salida/f"{nombre}.csv",filas)
    guardar_csv(salida/"verificaciones.csv",[{**r,"faltantes":"; ".join(r["faltantes"]),
                 "resultado":json.dumps(r["resultado"],ensure_ascii=False)} for r in verificaciones])
    guardar_csv(salida/"sensibilidad_pretension_separada.csv",leer_csv(
        RAIZ/"resultados/etapa_5e1/sensibilidad_pretension_separada.csv"))
    for nombre,obj in (("resumen",resumen),("parametros_utilizados",config),("trazabilidad_sha256",hashes)):
        (salida/f"{nombre}.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    (salida/"especificacion_fem.md").write_text((RAIZ/"especificacion_fem_ambas_poleas_inventor.md").read_text(encoding="utf-8"),encoding="utf-8")
    conservados=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    if not conservados:
        raise RuntimeError("Se alteró una entrada histórica")
    guardar_csv(salida/"validaciones.csv",[{"validacion":n,"cumple":True} for n in (
        "sha256_historicos_y_revision_conducida_conservados","coherencia_diametros_y_axiales_motriz",
        "torque_propio_y_fuerzas_correlacionadas","material_sin_aprobacion_resistencia")])
    return resumen


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--salida",type=Path,default=SALIDA)
    args=parser.parse_args()
    r=ejecutar(args.salida)
    print(json.dumps({"geometria":r["geometria"],"torsiones":r["torsion_nominal_parcial"]},indent=2,ensure_ascii=False))
