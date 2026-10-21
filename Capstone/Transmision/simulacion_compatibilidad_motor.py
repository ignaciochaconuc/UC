"""5E.2-B: comparación documentada, sin regenerar etapas anteriores."""
import argparse
import hashlib
import json
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_chavetas import leer_json
from transmision.motores import comparar_motor, comprobar_carga_radial

SALIDA=RAIZ/"resultados/etapa_5e2b"
PENDIENTES=[
    "Plano de eje específico de ambos motores: tolerancia Ø38, hombro, radio, chaflán y coordenadas axiales",
    "Chavetero Marathon: ancho, altura de chaveta, profundidades, radios, tolerancias y largo activo; en BEVI F10 nominal sí publicado, resto por confirmar",
    "No interpretar GA41 de BEVI como profundidad confirmada sin esquema; solicitar plano dimensional",
    "Longitud efectiva de contacto, posición del cubo, hombros, arandela/separadores y retención axial diseñados; 62 mm no es largo activo",
    "Carga radial admisible de cada fabricante para su eje, configuración de rodamientos, rpm, vida y sentido de carga",
    "Distancia axial del plano resultante de las tres correas y referencia exacta de la tabla de carga radial",
    "Peso y centro de masa de polea, orientación de eje y otras cargas para combinar con las correas; no asumir resultante completa del motor",
    "Montaje BEVI B3/B14 o Marathon B14: definir base/brida, fijaciones, alineación y tensado; B14 no equivale a base móvil de patas B3",
    "Compatibilidad de alimentación, conexión, arranque y régimen real; 8 h/día no define vida de rodamientos",
    "Interferencias de cubo Ø50/55/60 con aligeramientos CAD; condición AISI1045, sección debilitada, M5 y resistencia pendientes"]


def ejecutar(parametros=RAIZ/"parametros_motores.json",salida=SALIDA):
    salida=Path(salida).resolve()
    if salida != SALIDA.resolve() and (salida.is_relative_to(RAIZ.resolve()) or salida in RAIZ.resolve().parents):
        raise ValueError("Usar salida etapa_5e2b o carpeta temporal externa al proyecto")
    entradas=[f for f in RAIZ.rglob('*') if f.is_file() and not f.is_relative_to(SALIDA)
              and not any(s in f.parts for s in ('__pycache__','.pytest_cache'))]
    for carpeta in ('Simulación_peletizadora','Analisis_matriz_eje_vertical'):
        entradas += [f for f in (RAIZ.parent/carpeta).rglob('*') if f.is_file()
                     and not any(s in f.parts for s in ('__pycache__','.pytest_cache'))]
    entradas.append(Path(parametros))
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    p=leer_json(Path(parametros)); historico=leer_json(RAIZ/'parametros.json')
    polea=leer_json(RAIZ/'parametros_poleas.json')['poleas']['motriz']
    previo=leer_json(RAIZ/'resultados/etapa_5e2a/resumen.json')
    d2=leer_json(RAIZ/'resultados/etapa_5d2/resumen.json')
    critico=next(c for c in d2['casos_criticos_correlacionados'] if c['criterio']=='fuerza_resultante_maxima')
    nominal=d2['motor_nominal_externo']
    montaje=p['montaje_propuesto']
    comparacion=[]; radial=[]
    for m in p['motores']:
        comparacion.append(comparar_motor(m,polea,historico['rpm_motor'],montaje['posicion_inicio_cubo_desde_hombro_mm']))
        for escenario,c in (('maximo_3c_condicional',critico),('motor_nominal_ideal_historico',nominal)):
            radial.append({'motor':m['id'],'escenario':escenario,
                **comprobar_carga_radial(c['motriz_fr_n'],m['capacidad_radial'],
                    montaje['distancia_plano_resultante_correas_desde_referencia_catalogo_mm'],montaje['referencia_axial_catalogo'])})
    resumen={'etapa':'5E.2-B','motor_seleccionado':None,'montaje_aprobado':False,
        'cad_modificado':False,'fem_ejecutado':False,'factores_seguridad':None,
        'comparacion_motores':comparacion,'verificacion_radial':radial,
        'alternativas_cubo_5e2a_sin_recalcular':previo['ligamentos'],
        'material_candidato':previo['material'], 'pendientes':PENDIENTES,
        'eficiencias':'5,5 kW se interpreta como potencia mecánica nominal de salida. La eficiencia eléctrica relaciona salida con entrada eléctrica, no es eficiencia de correas; no se usa para reducir de nuevo los 5,5 kW ni para recalcular etapas previas.',
        'velocidades':'1470/1475 rpm son velocidades nominales publicadas. Los 1500 rpm del título Marathon corresponden a la clase síncrona 4 polos/50 Hz, no a su dato nominal de 1475. Se conserva 1450 rpm y torque 36,221 N·m históricos sin escalar.',
        'alcance_radial':'Fuerzas de correas heredadas dependen del modelo simétrico condicional de 5D.2; no son capacidad admisible ni reacción de rodamiento. No se extrapolan por rpm comerciales. Nominal motor externo y sensibilidades de pretensión permanecen separados.',
        'sensibilidades_pretension_originales':'resultados/etapa_5d2/sensibilidad_Ts.csv; sin mezclar ni regenerar',
        'continuidad_cubo55':'Puede continuar predimensionamiento en copia CAD manteniendo Ø38 provisional: coincidencia nominal con ambos candidatos. No aprobar Ø55 sin interferencias, geometría local, materiales, cargas admisibles y unión verificadas.',
        'fuentes_consultadas':p}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,filas in (('comparacion_motores',comparacion),('verificacion_carga_radial',radial),
                         ('alternativas_cubo_heredadas',previo['ligamentos']),
                         ('requisitos_pendientes',[{'requisito':r,'estado':'pendiente'} for r in PENDIENTES])):
        guardar_csv(salida/f'{nombre}.csv',filas)
    for nombre,obj in (('resumen',resumen),('parametros_utilizados',p),('trazabilidad_sha256',hashes)):
        (salida/f'{nombre}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    (salida/'metodologia.md').write_text((RAIZ/'metodologia_compatibilidad_motor.md').read_text(encoding='utf-8'),encoding='utf-8')
    if not all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items()):
        raise RuntimeError('Archivo anterior modificado')
    guardar_csv(salida/'validaciones.csv',[{'validacion':'SHA256_historicos_y_entradas_conservados','cumple':True}])
    return resumen


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--parametros',type=Path,default=RAIZ/'parametros_motores.json')
    parser.add_argument('--salida',type=Path,default=SALIDA)
    args=parser.parse_args()
    r=ejecutar(args.parametros,args.salida)
    print(json.dumps(r['comparacion_motores'],ensure_ascii=False,indent=2))
