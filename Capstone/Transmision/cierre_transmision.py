"""5F: leer, contrastar e integrar; no ejecutar simulaciones anteriores."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from simulacion_transmision import RAIZ, guardar_csv
from simulacion_chavetas import leer_json
from transmision.cierre import parametro, verificar_utilizacion, verificar_historial, estado_cierre

SALIDA=RAIZ/'resultados/etapa_5f'


def tabla(ruta):
    with (RAIZ/ruta).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def ejecutar(salida=SALIDA):
    salida=Path(salida).resolve()
    if salida!=SALIDA.resolve() and (salida.is_relative_to(RAIZ.resolve()) or salida in RAIZ.resolve().parents):
        raise ValueError('No sobrescribir históricos: usar etapa_5f o temporal externo')
    entradas=[f for f in RAIZ.rglob('*') if f.is_file() and not f.is_relative_to(SALIDA)
              and not any(k in f.parts for k in ('__pycache__','.pytest_cache'))]
    for carpeta in ('Simulación_peletizadora','Analisis_matriz_eje_vertical'):
        entradas += [f for f in (RAIZ.parent/carpeta).rglob('*') if f.is_file()
                     and not any(k in f.parts for k in ('__pycache__','.pytest_cache'))]
    hashes={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in entradas}
    p=leer_json(RAIZ/'parametros.json')
    ab=leer_json(RAIZ/'resultados/resumen.json'); a=ab['etapa_5a']; b=ab['etapa_5b']
    c=leer_json(RAIZ/'resultados/etapa_5c/resumen.json')
    d1=leer_json(RAIZ/'resultados/etapa_5d1/resumen.json')['principal']
    d2=leer_json(RAIZ/'resultados/etapa_5d2/resumen.json')
    e2=leer_json(RAIZ/'resultados/etapa_5e2/resumen.json')
    ea=leer_json(RAIZ/'resultados/etapa_5e2a/resumen.json')
    eb=leer_json(RAIZ/'resultados/etapa_5e2b/resumen.json')
    poleas=leer_json(RAIZ/'parametros_poleas.json')
    eq=tabla('resultados/etapa_5d2/diferencias_tensiones_3c.csv')
    cond=tabla('resultados/etapa_5d2/tensiones_y_fuerzas_condicionales_3c.csv')
    verificar_historial(eq,cond,d2['intervalos_3c'])
    verificar_utilizacion(b['potencia_diseno_kw'],b['capacidad_total_kw'],b['utilizacion_capacidad'])
    crit=next(r for r in d2['casos_criticos_correlacionados'] if r['criterio']=='fuerza_resultante_maxima')
    nominal=d2['motor_nominal_externo']
    # Controles de identidad/unidades, no nuevas simulaciones.
    if not math.isclose(a['relacion'],p['diametro_conducida_mm']/p['diametro_motriz_mm']):
        raise ValueError('Relación y diámetros contradictorios')
    if not math.isclose(a['rpm_salida']-p['cargas_3c']['rpm_matriz'],a['diferencia_rpm_vs_3c']):
        raise ValueError('Diferencia de velocidades inconsistente')
    for r in cond:
        if not math.isclose(float(r['delta_total_n'])*p['diametro_conducida_mm']/2000,
                            float(r['torque_conducida_magnitud_nm']),rel_tol=1e-10):
            raise ValueError('Equilibrio/unidades N mm frente a N m incoherente')
    valores=[]
    def agregar(nombre,valor,unidad,estado,fuente,escenario='predimensionamiento_historico',nota=''):
        valores.append(parametro(nombre,valor,unidad,estado,fuente,escenario,nota))
    for nombre,key,u in (('relacion','relacion','1'),('salida_ideal','rpm_salida','rpm'),
        ('diferencia_salida_vs_3c','diferencia_rpm_vs_3c','rpm'),('velocidad_correa','velocidad_correa_m_s','m/s'),
        ('abrazamiento_motriz','abrazamiento_motriz_grados','grado'),('abrazamiento_conducida','abrazamiento_conducida_grados','grado')):
        agregar(nombre,a[key],u,'verificado','resultados/resumen.json#etapa_5a')
    for key,u in (('potencia_motor_kw','kW'),('rpm_motor','rpm'),('horas_diarias','h/dia'),('factor_servicio','1'),
        ('diametro_motriz_mm','mm'),('diametro_conducida_mm','mm'),('centros_mm','mm'),('longitud_correa_mm','mm'),('numero_correas','1')):
        agregar(key,p[key],u,'propuesta' if key=='factor_servicio' else 'verificado','parametros.json',nota='Valor adoptado para predimensionamiento; no selección comercial definitiva')
    for key,u in (('potencia_diseno_kw','kW'),('capacidad_total_kw','kW'),('utilizacion_capacidad','1'),('margen_capacidad_kw','kW')):
        agregar(key,b[key],u,'condicionado_modelo','resultados/resumen.json#etapa_5b',nota='Solo Gates SPA Super HC convencional; G conservador 0,94')
    for key,val in c['ajuste_centros'].items():
        agregar(key,val,'mm','verificado','resultados/etapa_5c/resumen.json',nota='Extremos de instalación/ajuste, no funcionamiento normal de correa inextensible')
    for key,u in (('tension_estatica_base_n','N'),('deflexion_mm','mm'),('fuerza_minima_n','N'),('fuerza_maxima_n','N')):
        agregar(key,d1[key],u,'condicionado_modelo','resultados/etapa_5d1/resumen.json',nota='Procedimiento Gates, construcción y condiciones de medición de 5D.1')
    for nombre,key,u in (('torque_maximo_conducida','torque_conducida_magnitud_nm','N m'),
                         ('diferencia_tensiones_total_maxima','delta_total_n','N'),('fuerza_lateral_maxima_3c','conducida_fr_n','N')):
        agregar(nombre,crit[key],u,'condicionado_modelo' if u=='N' and key=='conducida_fr_n' else 'verificado',
            'resultados/etapa_5d2/resumen.json','historial_3c_inclinacion',nota='T y delta por equilibrio; Fr depende de hipótesis de tensión media constante')
    for nombre,D,d,estado,fuente in (
        ('cubo_motriz_CAD',poleas['poleas']['motriz']['diametro_exterior_cubo_mm'],poleas['poleas']['motriz']['diametro_interior_cubo_mm'],'incompatible','parametros_poleas.json'),
        ('cubo_conducida_CAD',poleas['poleas']['conducida']['diametro_exterior_cubo_mm'],poleas['poleas']['conducida']['diametro_interior_cubo_mm'],'verificado','parametros_poleas.json'),
        ('cubo_motriz_propuesto',ea['primera_alternativa_a_estudiar_inventor_mm'],poleas['poleas']['motriz']['diametro_interior_cubo_mm'],'propuesta','resultados/etapa_5e2a/resumen.json')):
        agregar(nombre+'_exterior',D,'mm',estado,fuente,nota='Ø55 adoptado como propuesta de predimensionamiento 5F, NO plano CAD ejecutado; CAD no equivale a resistencia aprobada')
        agregar(nombre+'_agujero',d,'mm',estado,fuente)
    for key,valor in (('chaveta_ancho',e2['candidatas'][0]['b_mm']),('chaveta_altura',e2['candidatas'][0]['h_mm'])):
        agregar(key,valor,'mm','propuesta','resultados/etapa_5e2/resumen.json',nota='Candidata DIN6885-1; largo activo y contacto real pendientes')
    for i,nombre in enumerate(('motriz','conducida')):
        agregar('gargantas_'+nombre,c['poleas'][i]['numero_gargantas'],'1','verificado','resultados/etapa_5c/resumen.json')
        agregar('angulo_CAD_'+nombre,poleas['poleas'][nombre]['angulo_garganta_cad_grados'],'grado','verificado','parametros_poleas.json',nota='Dato geométrico, no aceptación normativa')
        agregar('angulo_Gates_'+nombre,c['poleas'][i]['angulo_garganta_grados'],'grado','verificado','resultados/etapa_5c/resumen.json')
    for motor in eb['comparacion_motores']:
        agregar('rpm_comercial_'+motor['motor'],motor['rpm_nominal_comercial'],'rpm','verificado','resultados/etapa_5e2b/resumen.json',motor['motor'],nota='Candidato no seleccionado; no sustituye1450rpm')
    balance=tabla('resultados/balance_motor_eficiencias.csv')
    for r in balance:
        eta=float(r['eficiencia_supuesta']); disponible=float(r['potencia_disponible_kw'])
        if not 0<eta<=1 or not math.isclose(disponible,p['potencia_motor_kw']*eta):
            raise ValueError('Balance de potencia o eficiencia incoherente')
        if (r['cubre_maximo_3c']=='True')!=(disponible>=p['cargas_3c']['potencia_max_kw']):
            raise ValueError('Estado de balance incoherente')
    matriz=[]
    def control(nombre,estado,esencial,fuente,limite):
        matriz.append(dict(verificacion=nombre,estado=estado,esencial_aprobacion=esencial,fuente=fuente,limite=limite))
    control('cinematica_ideal','verificado',True,'resultados/resumen.json','No corrige 516 rpm ni garantiza velocidad real')
    control('capacidad_tres_correas_referencia','verificado',False,'resultados/resumen.json','Utilización 0,729 para construcción Gates; no motor más potente disponible')
    control('correa_comercial_y_equivalencia','pendiente',True,'parametros.json','DIN7753 por sí sola no prueba equivalencia Gates')
    control('tensado_procedimiento_referencia','condicionado_modelo',False,'resultados/etapa_5d1/resumen.json','No tensiones dinámicas exactas ni adherencia garantizada')
    control('cargas_vectoriales','condicionado_modelo',True,'resultados/etapa_5d2/resumen.json','Promedio Ts constante y reparto uniforme; validar montaje/pretensión')
    control('tres_gargantas','verificado',False,'resultados/etapa_5c/resumen.json','Configuración, no conformidad completa CAD')
    control('compatibilidad_gargantas_CAD','pendiente',True,'resultados/etapa_5c/resumen.json; parametros_poleas.json','Conducida34° CAD frente38° Gates; exteriores +0,1 mm frente tabla, aceptación pendiente')
    control('cubo_original_motriz_chavetero_alto','incompatible',True,'resultados/etapa_5e2/resumen.json','Ø45/38 no contiene esquina ideal; no fabricar como aprobado')
    control('redisenio_cubo55','propuesta',True,'resultados/etapa_5e2a/resumen.json','Adoptado solo en predimensionamiento; validar interferencias y actualizar CAD posteriormente')
    control('resistencia_poleas_chavetas_uniones','pendiente',True,'resultados/etapa_5e2/resumen.json','Largo activo, materiales/condición, tolerancias, entallas y retención pendientes; sin FS')
    control('balance_potencia','condicionado_modelo',True,'resultados/balance_motor_eficiencias.csv','Suficiencia depende de eficiencia mecánica y servicio; no usar eficiencia eléctrica')
    control('motor_y_carga_radial','pendiente',True,'resultados/etapa_5e2b/resumen.json','Candidatos, no selección; punto de aplicación y capacidad radial no confirmados')
    control('montaje_base_y_protecciones','pendiente',True,'resultados/etapa_5c/resumen.json','Base guiada/bloqueada, alineación, retención, tensado y resguardo por detallar')
    control('integracion_eje_vertical','pendiente',True,'resultados/etapa_5d2/resumen.json','Faltan apoyos y ubicación espacial polea; no reacciones calculadas')
    pendientes=[dict(prioridad=i+1,pendiente=texto,tipo=tipo) for i,(texto,tipo) in enumerate([
        ('Resolver garganta conducida34/38°, equivalencia y referencia comercial de correas','detalle'),
        ('Estudiar Ø55/38 con coordenadas reales de aligeramientos; corregir CAD solo tras validar','detalle'),
        ('Confirmar motor, plano de eje, admisible radial y posición real del plano de correas','proveedor'),
        ('Completar chavetas, largos activos, materiales/condición, ajustes y retención axial','detalle'),
        ('Verificar poleas debilitadas y transiciones; análisis local/FEM solo con datos suficientes','detalle'),
        ('Entregar interfaz a eje vertical y ubicar apoyos antes de calcular reacciones','integracion'),
        ('Dimensionar base, bloqueo, pernos, alineación y resguardo','detalle'),
        ('Validar servicio/arranques, tensión de instalación, velocidad/deslizamiento y pérdidas reales','experimental')])]
    fuentes=[]
    bib=(RAIZ/'referencias.bib').read_text(encoding='utf-8')
    for match in re.finditer(r'@(\w+)\{([^,]+),(.*?)(?=\n@|\Z)',bib,re.S):
        bloque=match.group(3); url=re.search(r'url\s*=\s*\{([^}]+)',bloque)
        fuentes.append(dict(clave_bibtex=match.group(2),url=url.group(1) if url else '',
            uso='Referencia existente consultada en etapas previas; alcance y acceso según nota BibTeX',archivo='referencias.bib'))
    if len({r['clave_bibtex'] for r in fuentes})!=len(fuentes) or not fuentes:
        raise ValueError('Bibliografía ausente o duplicada')
    interfaz={'destino':'Analisis_matriz_eje_vertical; sin modificar sus cálculos',
        'archivo_serie_completa':'resultados/etapa_5d2/tensiones_y_fuerzas_condicionales_3c.csv',
        'archivo_equilibrio':'resultados/etapa_5d2/diferencias_tensiones_3c.csv',
        'archivo_criticos':'resultados/etapa_5d2/casos_criticos_correlacionados.csv',
        'archivo_motor_externo':'resultados/etapa_5d2/motor_nominal_externo.csv',
        'archivo_sensibilidades_separadas':'resultados/etapa_5d2/sensibilidad_Ts.csv',
        'columnas_eje_vertical':{'conducida_fx_n':'N','conducida_fy_n':'N','conducida_fr_n':'N',
            'torque_correas_conducida_firmado_nm':'N m','tiempo_s':'s','angulo_grados':'grado','paso':'índice'},
        'marco':d2['convenciones'],'hipotesis':d2['hipotesis'],'numero_estados':len(cond),
        'caso_3c_correlacionado':crit,'caso_nominal_ideal_externo':nominal,
        'aplicacion':'Resultante en plano de polea; no aplicar simultáneamente tensiones de ramales y resultante (duplicaría cargas). Preservar correlación T,Fx,Fy,paso,tiempo.',
        'transformacion_espacial':'Pendiente: orientación del plano de correas, posición axial/radial de polea y ejes globales. No se supone coincidencia con marco estructural.',
        'reacciones_rodamientos_calculadas':False,
        'faltantes':['Posición axial exacta de apoyos y polea','Orientación espacial y transformación de ejes','Peso/centro de gravedad y otras acciones','Estado simultáneo de cargas del otro subsistema'],
        'sin_reescalado':'Cargas3C corresponden a516rpm; no escalar ni sumar máximos de distintos estados o escenarios.'}
    anexos=[dict(tema=t,archivo=f,alcance=lim) for t,f,lim in [
        ('Geometría exacta y aproximada','resultados/resumen.json','Incluye contraste G0,947 no adoptado'),
        ('Sensibilidad factor servicio','resultados/sensibilidad_factor_servicio.csv','No sustituye FS1,3 preliminar'),
        ('Balance de potencia','resultados/balance_motor_eficiencias.csv','Eficiencias mecánicas supuestas, no eléctricas'),
        ('Historial correlacionado','resultados/etapa_5d2/tensiones_y_fuerzas_condicionales_3c.csv','1440 estados intactos'),
        ('Sensibilidad pretensión','resultados/etapa_5d2/sensibilidad_Ts.csv','No instrucciones de fabricante'),
        ('Poleas y especificación FEM','especificacion_fem_ambas_poleas_inventor.md','Preparación, no FEM ejecutado'),
        ('Sensibilidad largo chavetas','resultados/etapa_5e2/sensibilidad_longitud_activa.csv','Largos hipotéticos, no selección'),
        ('Alternativas cubo','resultados/etapa_5e2a/ligamentos_geometricos.csv','Ligamentos, no resistencia'),
        ('Motores comerciales','resultados/etapa_5e2b/resumen.json','BEVI directo; Marathon indexado/403, plano pendiente')]]
    cierre=estado_cierre(matriz)
    resumen={'etapa':'5F',**cierre,'parametros_predimensionamiento':valores,'matriz_verificaciones':matriz,
        'motor_comercial':eb['comparacion_motores'],'balance_potencia_heredado':balance,
        'eficiencia_mecanica_minima_maximo':float(balance[0]['eficiencia_minima_maximo']),
        'eficiencia_mecanica_minima_media':float(balance[0]['eficiencia_minima_media']),
        'separacion_eficiencias':eb['eficiencias'],'interfaz_eje_vertical':interfaz,
        'pendientes_priorizados':pendientes,'bibliografia':fuentes,'anexos':anexos,
        'criterio_cierre':'Cierre documental de ingeniería básica, no aprobación para fabricación/compra; Ø55/38 propuesta adoptada en5F, CAD vigente Ø45/38.',
        'advertencias_historicas_superadas':'5A/5B aún dicen confirmar diámetros y pendientes ramales/tensado; se conservan literalmente. 5C confirma diámetros de referencia;5D aporta tensado y modelo dinámico condicional, no aprobación física.',
        'tensiones_cubos':'Valores de secciones lisas son nominales simplificados, no máximos locales reales; sin factores de seguridad asignados.',
        'factores_seguridad_componentes_no_verificados':None,'fem_ejecutado':False,'historial_3c_modificado':False}
    salida.mkdir(parents=True,exist_ok=True)
    for nombre,filas in (('parametros_definitivos_predimensionamiento',valores),('resultados_informe_principal',valores),
                         ('matriz_verificaciones',matriz),('calculos_y_sensibilidades_anexos',anexos),
                         ('referencias_tecnicas',fuentes),('pendientes_priorizados',pendientes),('balance_potencia_heredado',balance)):
        guardar_csv(salida/f'{nombre}.csv',filas)
    for nombre,obj in (('resumen_integral',resumen),('interfaz_eje_vertical',interfaz),('trazabilidad_sha256',hashes)):
        (salida/f'{nombre}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in hashes.items()):
        raise RuntimeError('Histórico alterado')
    guardar_csv(salida/'validaciones.csv',[dict(validacion=n,cumple=True) for n in
        ('SHA256_historicos_conservados','1440_estados_correlacionados','unidades_equilibrio','utilizacion_capacidad','escenarios_separados')])
    return resumen


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--salida',type=Path,default=SALIDA)
    r=ejecutar(parser.parse_args().salida)
    print(json.dumps({k:r[k] for k in ('listo_redaccion_ingenieria_basica','transmision_aprobada','bloqueos_aprobacion')},indent=2,ensure_ascii=False))
