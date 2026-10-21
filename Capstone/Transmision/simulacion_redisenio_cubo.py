"""Ejecutar solo 5E.2-A; lectura de históricos sin regenerarlos."""
import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_chavetas import leer_json
from transmision.chavetas import candidata_normalizada, comprobar_eje_real, FUENTES_CHAVETAS
from transmision.redisenio_cubo import comparar_cubos, comprobar_aberturas

SALIDA=RAIZ/"resultados/etapa_5e2a"
FUENTES_NUEVAS={
    "ganter_din6885_2_low_2026": {
        "url":"https://live-katalog.ganternorm.com/pdf/ganter/en/6885-2.pdf?dispositiontype=attachment",
        "lectura":"Fila d=38: b=10, h=8; cubo q=2,1 +0,2; eje 6 +0,2 mm. Extracto, no norma completa.",
        "consulta":"2026-10-21"},
    "ringfeder_rfn7012_2026": {
        "url":"https://www.ringfeder.com/products/locking-assemblies/rfn-7012/",
        "lectura":"Unión por fricción comercial; no autocentrante, requiere centrado previo. No se selecciona tamaño ni capacidad para este proyecto.",
        "consulta":"2026-10-21"}}

PENDIENTES=[
    "Coordenadas x,y reales de los ocho centros Ø13 respecto al eje, tolerancias y extensión axial de cada abertura",
    "Espesores de cuerpo/llanta, transiciones cubo-cuerpo y radios de filete; ubicación y profundidad del M5",
    "Plano/ficha del eje real del motor: diámetro, longitud útil, hombros, chavetero, radios y tolerancias",
    "Longitud activa de chaveta (no envolvente axial 62 mm), forma de extremos, chaflanes y contacto real",
    "Profundidades y tolerancias de ambos chaveteros; alturas portantes efectivas y radios de fondo",
    "Condición y propiedades trazables de AISI 1045, material de chaveta y eje; cargas de servicio/fatiga",
    "Definir ajuste de centrado y retención axial; no atribuir torque ni retención al M5 sin cálculo",
    "Verificar cubo debilitado por ranura/M5 y unión con cuerpo, separado del cortante/aplastamiento de chaveta"]


def ejecutar(parametros=RAIZ/"parametros_redisenio_cubo.json",salida=SALIDA):
    salida=Path(salida).resolve()
    if salida != SALIDA.resolve() and (salida.is_relative_to(RAIZ.resolve()) or salida in RAIZ.resolve().parents):
        raise ValueError("No sobrescribir archivos de proyecto; usar etapa_5e2a o carpeta temporal externa")
    entradas=[f for f in (RAIZ/"resultados").rglob("*") if f.is_file() and not f.is_relative_to(SALIDA)]
    for carpeta in ("Simulación_peletizadora","Analisis_matriz_eje_vertical"):
        entradas += [f for f in (RAIZ.parent/carpeta).rglob("*") if f.is_file()
                     and not any(k in f.parts for k in ("__pycache__",".pytest_cache"))]
    entradas += [RAIZ/n for n in ("POLEA 1 (1).pdf","POLEA 2.pdf","parametros_poleas.json",
                                 "parametros_chavetas.json","parametros.json")]
    entradas += [Path(parametros),Path(__file__),RAIZ/"transmision/redisenio_cubo.py",
                 RAIZ/"transmision/chavetas.py",RAIZ/"metodologia_redisenio_cubo.md"]
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    p=leer_json(Path(parametros)); geometria=leer_json(RAIZ/"parametros_poleas.json")
    motriz=geometria["poleas"]["motriz"]
    union=leer_json(RAIZ/"parametros_chavetas.json")["uniones"]["motriz"]
    candidata=candidata_normalizada(motriz["diametro_interior_cubo_mm"])
    diametros=[motriz["diametro_exterior_cubo_mm"],*p["diametros_exteriores_candidatos_mm"]]
    ligamentos=comparar_cubos(diametros,motriz["diametro_interior_cubo_mm"],candidata["b_mm"],
        [candidata["profundidad_cubo_nominal_mm"],candidata["profundidad_cubo_max_mm"]])
    interferencias=[]
    for D in diametros:
        interferencias += comprobar_aberturas(D,motriz["diametro_aberturas_mm"],
            motriz["coordenadas_centros_aberturas_mm"],p["fuente_coordenadas_aberturas"],
            p["solapamiento_axial_cubo_aberturas_confirmado"])
    # Importación directa de E2; no recalcular contacto, torque ni escenarios.
    anterior=leer_json(RAIZ/"resultados/etapa_5e2/resumen.json")
    cargas=[r for r in anterior["fuerzas_correlacionadas"] if r["polea"]=="motriz"]
    alternativas=[
        {"alternativa":"Cubo mayor con candidata alta DIN 6885-1", "ventaja":"Conserva provisionalmente agujero y candidata; aumenta ligamentos",
         "limitacion":"Interferencia de aberturas, unión al cuerpo y resistencia pendientes; ningún diámetro aprobado"},
        {"alternativa":"Chavetero bajo, extracto Ganter DIN 6885-2", "ventaja":"Menor profundidad en cubo: 2,1 a 2,3 mm para d38, b10 h8",
         "limitacion":"Profundiza asiento del eje a 6 a 6,2 mm; exige modificar y comprobar eje, contacto y ambos mecanizados; no intercambiable ni aprobado"},
        {"alternativa":"Anillo de fijación por fricción, ejemplo RINGFEDER RfN 7012", "ventaja":"Alternativa comercial sin transmisión por chaveta",
         "limitacion":"No es una norma DIN de chaveta ni equivalencia; requiere tamaño disponible, envolvente, presiones, material, cargas combinadas y centrado propio; no se confirma tamaño para Ø38"}]
    resumen={"etapa":"5E.2-A","cad_modificado":False,"resistencia_aprobada":False,
        "factores_seguridad":None,"fem_ejecutado":False,"material":geometria["material"],
        "ligamentos":ligamentos,"interferencias":interferencias,"cargas_motriz_importadas":cargas,
        "eje_real":comprobar_eje_real(motriz["diametro_interior_cubo_mm"],union["diametro_eje_real_mm"],union["fuente_eje_real"]),
        "alternativas_union":alternativas,"pendientes":PENDIENTES,
        "chaveta_vs_cubo":"Ampliar diámetro exterior no cambia fuerza tangencial ni cortante/aplastamiento de chaveta si T,d,b,L y contacto se mantienen. Sus verificaciones reales siguen pendientes; no confundir con resistencia del cubo.",
        "primera_alternativa_a_estudiar_inventor_mm":55,
        "justificacion":"Punto de comparación intermedio: más reserva geométrica que Ø50 y menor ocupación radial que Ø60. No optimización resistente ni recomendación definitiva; validar primero aberturas y eje real. Ø50 reduce intervención y Ø60 ofrece mayor reserva pero invade más la zona del cuerpo.",
        "limitaciones":["Esquinas ideales sin filetes, cotas nominales salvo profundidad extrema; tolerancias reales pendientes",
            "No existe espesor mínimo resistente validado; ligamento positivo solo demuestra contención local ideal",
            "No hay coordenadas CAD de aberturas; no se infieren de píxeles, simetría ni círculo aparente",
            "Umbral radial de tangencia no es holgura resistente recomendada; falta evaluación tridimensional",
            "Conducida e históricos intactos; discrepancia SPA conducida 34/38 grados sigue pendiente"],
        "fuentes":{**FUENTES_CHAVETAS,**FUENTES_NUEVAS}}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,filas in (("ligamentos_geometricos",ligamentos),("interferencias",interferencias),
        ("cargas_motriz_heredadas",cargas),("alternativas_union",alternativas),
        ("requisitos_pendientes",[{"requisito":s,"estado":"pendiente"} for s in PENDIENTES])):
        guardar_csv(salida/f"{nombre}.csv",filas)
    for nombre,obj in (("resumen",resumen),("parametros_utilizados",p),("trazabilidad_sha256",hashes)):
        (salida/f"{nombre}.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    (salida/"metodologia.md").write_text((RAIZ/"metodologia_redisenio_cubo.md").read_text(encoding="utf-8"),encoding="utf-8")
    if not all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items()):
        raise RuntimeError("Entrada histórica alterada")
    guardar_csv(salida/"validaciones.csv",[{"validacion":"SHA256_entradas_e_historicos_conservados","cumple":True}])
    return resumen


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--salida",type=Path,default=SALIDA)
    args=parser.parse_args()
    r=ejecutar(salida=args.salida)
    print(json.dumps({"ligamentos":r["ligamentos"],"resistencia_aprobada":False},indent=2))
