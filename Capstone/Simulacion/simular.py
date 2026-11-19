"""Interfaz única: python simular.py --modelo real|prototipo.

La geometría se audita antes de cualquier carga. Ningún resultado de EP2
se sobrescribe ni se usa la geometría escalada archivada como entrada.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from peletizadora.cad import extraer
from peletizadora.informes import guardar_geometria,guardar_json,diferencias_declaradas
from peletizadora.nucleo import cargas_angulares,requisitos_carga,resumir
from herramientas.control_cambios import verificar

RAIZ=Path(__file__).resolve().parent


def cargar_configuracion(modelo,path=None):
    if modelo not in ('real','prototipo'):raise ValueError('Modelo no admitido')
    cfg=json.loads(Path(path or RAIZ/f'configuraciones/{modelo}.json').read_text(encoding='utf-8'))
    if cfg['modelo']!=modelo:raise ValueError('Configuración de otra máquina')
    archivo=(RAIZ/cfg['step']).resolve()
    if archivo.suffix.lower() not in ('.stp','.step') or not archivo.is_relative_to((RAIZ/'geometrias').resolve()):
        raise ValueError('La geometría debe ser un STEP de la carpeta geometrias')
    esperado={'real':'Matriz_real.stp','prototipo':'Matriz_prototipo.stp'}[modelo]
    if archivo.name!=esperado:raise ValueError('STEP no correspondiente a esta configuración')
    for campo in ('estados','cuadratura','cuadratura_contraste'):
        v=cfg['numerico'][campo]
        if isinstance(v,bool) or not isinstance(v,int) or v<4:raise ValueError('Resolución numérica inválida')
    if modelo=='prototipo' and cfg['operacion'].get('rpm_matriz') is None and cfg['operacion'].get('relacion_reduccion') is not None:
        from peletizadora.nucleo import positivo
        i=cfg['operacion']['relacion_reduccion'];positivo(i,'relacion_reduccion')
        cfg['operacion']['rpm_matriz']=cfg['operacion']['rpm_motor']/i
        cfg['operacion']['fuente_rpm_matriz']='Calculada con relación de reducción explícita de esta configuración, no heredada de EP2'
    return cfg


def version_codigo():
    archivos=[f for f in RAIZ.rglob('*') if f.is_file() and f.suffix in ('.py','.json','.bib','.txt','.md')
        and not any(k in f.relative_to(RAIZ).parts for k in ('resultados','control','__pycache__','.pytest_cache','.venv'))]
    h={str(f.relative_to(RAIZ)):hashlib.sha256(f.read_bytes()).hexdigest() for f in archivos}
    return {'python':platform.python_version(),'OCP':importlib.metadata.version('cadquery-ocp'),
        'version_fuentes_sha256':hashlib.sha256(json.dumps(h,sort_keys=True).encode()).hexdigest(),'archivos':h,
        'git':'Sin commit nuevo; git.exe no ejecutable en este entorno. Identificación reproducible por SHA256.'}


def regresion_real(config,agujeros,df,salida):
    referencia=pd.read_csv(RAIZ/config['regresion']['cargas_2C']).iloc[:len(df)]
    coords=pd.read_csv(RAIZ/config['regresion']['coordenadas_EP2'])[['x_mm','y_mm']].to_numpy()
    nuevos=np.array([[a['x_mm'],a['y_mm']] for a in agujeros])
    distancia=float(cKDTree(coords).query(nuevos)[0].max())
    if len(referencia)!=len(df) or not np.allclose(referencia.angulo_grados,df.angulo_grados,atol=1e-10,rtol=0):
        raise ValueError('Estados históricos no correlacionados con corrida nueva')
    diferencias=pd.DataFrame({'paso':df.paso,'angulo_grados':df.angulo_grados})
    resumen={'distancia_max_centros_STEP_vs_CSV_EP2_mm':distancia,
        'criterio':'Comparar con2C área-superposición, no forzar coincidencia con3C acoplado',
        'origen_diferencias':'Si geometría/operación coinciden, solo redondeo/orden de suma; se mantienen44MPa y516rpm sin ajuste.'}
    for nuevo,viejo in [('fuerza_total_n','fuerza_total_n'),('fuerza_r1_n','fuerza_rodillo_1_n'),('fuerza_r2_n','fuerza_rodillo_2_n'),
        ('torque_total_nm','torque_resistente_nm'),('potencia_w','potencia_resistente_w')]:
        delta=df[nuevo].to_numpy()-referencia[viejo].to_numpy()
        diferencias[nuevo+'_diferencia']=delta
        resumen[nuevo+'_error_abs_max']=float(np.max(abs(delta)))
    resumen['coincide_2C_numerico']=bool(distancia<1e-5 and resumen['fuerza_total_n_error_abs_max']<1e-5 and resumen['torque_total_nm_error_abs_max']<1e-7)
    diferencias.to_csv(salida/'regresion_2C_por_estado.csv',index=False)
    guardar_json(salida/'regresion_EP2.json',resumen)
    return resumen


def pendientes(config,faltan):
    filas=[dict(verificacion='cargas_contacto',estado='pendiente' if faltan else 'ejecutado_condicionado',datos_faltantes='; '.join(faltan)),
        dict(verificacion='presion_extrusion',estado='condicionada_no_validada',datos_faltantes='PN0,mu_pared,nuLR,biomasa/humedad/temperatura y memoriaEP2; no deducir presión de espesor solamente'),
        dict(verificacion='estructural_y_acoplamiento',estado='pendiente_o_referencia_historica',datos_faltantes='Apoyos físicos, propiedades y montaje propios; no trasladar3C al prototipo'),
        dict(verificacion='matriz_FEM',estado='no_ejecutado',datos_faltantes='Contacto/retención y materiales; triangulación de figura es solo visualización CAD'),
        dict(verificacion='rodamientos',estado='pendiente_de_montaje_propio',datos_faltantes='Cargas individuales,marca/variante,asientos/holguras,Fa y velocidad; en prototipo M6/608Ø8sinadaptador'),
        dict(verificacion='potencia_y_transmision',estado='pendiente_rendimiento_real',datos_faltantes='Velocidad matriz,reducción y pérdidas reales; no importar selección de correas de otra máquina')]
    return filas


def ejecutar(modelo,salida=None,config_path=None):
    config=cargar_configuracion(modelo,config_path)
    salida=Path(salida or RAIZ/f'resultados/{modelo}').resolve()
    if salida.is_relative_to(RAIZ.parent.resolve()) and not salida.is_relative_to((RAIZ/'resultados').resolve()):
        raise ValueError('Dentro de Capstone solo se permite salida Simulacion/resultados')
    if salida in RAIZ.resolve().parents:raise ValueError('Salida demasiado amplia')
    previo=salida/'parametros_utilizados.json'
    if previo.exists() and json.loads(previo.read_text(encoding='utf-8'))!=config:
        raise ValueError('Ya hay otra configuración en salida: usar carpeta de revisión nueva')
    geo_previa=salida/'geometria_STEP.json'
    if geo_previa.exists():
        h=hashlib.sha256((RAIZ/config['step']).read_bytes()).hexdigest()
        if json.loads(geo_previa.read_text(encoding='utf-8'))['sha256']!=h:
            raise ValueError('El STEP cambió: usar carpeta de revisión nueva')
    conservacion=verificar()
    solid,dim,agujeros,pares,caras=extraer(RAIZ/config['step'])
    discrepancias=diferencias_declaradas(config,dim)
    # Auditoría siempre antes de simular; se conserva el dato declarado como referencia.
    guardar_geometria(salida,config,solid,dim,agujeros,pares,caras)
    print(modelo,': CAD',dim['diametro_exterior_mm'],'mm;',dim['numero_canales'],'conductos; auditoría guardada antes de cargas')
    faltan=requisitos_carga(config)
    if not dim['validacion_pasantes'] or (dim['ligamento_min_cilindrico_mm'] is not None and dim['ligamento_min_cilindrico_mm']<=0):
        faltan.append('validación topológica de conductos/ligamentos')
    if dim['clasificacion_funcional_ambigua']:faltan.append('clasificación de familias de perforaciones auxiliares/extrusión')
    estado='pendiente_datos_contacto' if faltan else 'cargas_desacopladas_ejecutadas'
    resumen={'modelo':modelo,'estado':estado,'geometria':dim,'discrepancias_declaradas':discrepancias,
        'parametros_fisicos':config,'fuente_geometrica':'STEP sin escalamiento','cargas':None,'seguridad_estructural_aprobada':False,
        'pendientes':pendientes(config,faltan),'historicos':conservacion,
        'nota':'No comparar escenarios como equivalentes por escala; CAD de matriz no determina montaje ni material.'}
    if not faltan:
        df,largo=cargas_angulares(agujeros,config)
        fina,_=cargas_angulares(agujeros,config,config['numerico']['cuadratura_contraste'])
        suma=sum(df[c] for c in df if c.startswith('fuerza_r'))
        equilibrio=float(np.max(abs(suma-df.fuerza_total_n)))
        convergencia=float(np.max(abs(fina.fuerza_total_n-df.fuerza_total_n))/fina.fuerza_total_n.max())
        df.to_csv(salida/'historial_cargas.csv',index=False)
        resumen['cargas']=resumir(df)
        resumen['longitud_contacto_m']=largo
        resumen['validaciones_cargas']={'error_suma_fuerzas_n':equilibrio,'cuadratura_error_relativo_max':convergencia,
            'estados_sin_extremo_duplicado':len(df),'no_acoplamiento_3C':'Cobertura2C con presión constante; no usar resultados como3C'}
        if modelo=='real':resumen['regresion']=regresion_real(config,agujeros,df,salida)
        fig,ax=plt.subplots(1,2,figsize=(11,4))
        ax[0].plot(df.angulo_grados,df.fuerza_total_n/1000,label='Total')
        for c in df:
            if c.startswith('fuerza_r'):ax[0].plot(df.angulo_grados,df[c]/1000,label=c)
        ax[0].set(xlabel='Ángulo [°]',ylabel='F [kN]',title=f'{modelo}: cobertura STEP desacoplada');ax[0].legend(fontsize=8)
        ax[1].plot(df.angulo_grados,df.torque_total_nm);ax[1].set(xlabel='Ángulo [°]',ylabel='T [N·m]',title='Torque resistente de escenario EP2')
        fig.tight_layout();fig.savefig(salida/'cargas_angulares.png',dpi=160);plt.close(fig)
    pd.DataFrame(resumen['pendientes']).to_csv(salida/'verificaciones_pendientes.csv',index=False)
    guardar_json(salida/'parametros_utilizados.json',config)
    guardar_json(salida/'version_codigo.json',version_codigo())
    resumen['historicos']=verificar()
    guardar_json(salida/'resumen.json',resumen)
    guardar_json(salida/'conservacion_historica.json',resumen['historicos'])
    guardar_json(salida/'validaciones.json',{'BRep_valido':dim['geometria_valida'],'pasantes_verificados':dim['validacion_pasantes'],
        'cuentas_topologicas_independientes_coinciden':all(v==dim['numero_canales'] for v in dim['cuenta_independiente_circulos_por_plano'].values()),
        'SHA256_historicos_conservados':True,'cargas_ejecutadas':not faltan,
        'detalle_cargas':resumen.get('validaciones_cargas'),'seguridad_estructural_no_aprobada':True})
    comparar()
    return resumen


def comparar():
    filas=[]
    for modelo in ('real','prototipo'):
        p=RAIZ/f'resultados/{modelo}/resumen.json'
        if not p.exists():continue
        r=json.loads(p.read_text(encoding='utf-8'));d=r['geometria'];c=r['cargas']
        filas.append(dict(modelo=modelo,estado=r['estado'],diametro_matriz_mm=d['diametro_exterior_mm'],
            altura_total_mm=d['espesor_total_envolvente_mm'],espesor_perforado_mm=d['espesor_zona_perforada_mm'],
            bore_mm=d['diametro_bore_mm'],numero_perforaciones=d['numero_canales'],diametros_mm=str(d['diametros_efectivos_mm']),
            longitud_cilindrica_mm=str(d['longitudes_cilindricas_restrictivas_mm']),Lcil_D=str(d['relaciones_Lcil_D']),
            area_abierta_mm2=d['area_abierta_efectiva_mm2'],ligamento_min_mm=d['ligamento_min_cilindrico_mm'],
            fuerza_max_n=None if c is None else c['fuerza_total_max_n'],fuerza_media_n=None if c is None else c['fuerza_total_media_n'],
            torque_max_nm=None if c is None else c['torque_max_nm'],torque_medio_nm=None if c is None else c['torque_medio_nm'],
            potencia_max_w=None if c is None else c['potencia_max_w'],rpm_matriz=r['parametros_fisicos']['operacion']['rpm_matriz'],
            esfuerzos_nuevos_pa=None,desplazamientos_nuevos_m=None,
            nota='Sin equivalencia de operación por escala; campos vacíos son pendientes, NO cero; estructura histórica no recalculada'))
    if filas:
        destino=RAIZ/'resultados';destino.mkdir(exist_ok=True)
        pd.DataFrame(filas).to_csv(destino/'comparacion_modelos.csv',index=False)
        pd.DataFrame(filas).to_csv(destino/'tabla_para_informe.csv',index=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--modelo',choices=('real','prototipo'),required=True)
    parser.add_argument('--salida',type=Path);parser.add_argument('--config',type=Path)
    args=parser.parse_args();r=ejecutar(args.modelo,args.salida,args.config)
    print(json.dumps({'modelo':r['modelo'],'estado':r['estado'],'cargas':r['cargas'],'pendientes':r['pendientes']},ensure_ascii=False,indent=2))
