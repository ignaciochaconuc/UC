"""Revisión manual integrada. No ejecuta ni sobrescribe simulaciones históricas."""
from pathlib import Path
import json
import math
import hashlib
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from peletizadora.informes import guardar_json
from peletizadora.nucleo import resumir
from peletizadora.detalle_manual import (presiones,radio_manivela_CAD,fuerza_manual,agua_base_humeda,
    reparto_CAD,viga_detalle,seccion_arbol,referencia_608,contactos_CAD)
from herramientas.control_detalle import verificar,sha

RAIZ=Path(__file__).resolve().parent
ANTERIOR=RAIZ/'resultados/prototipo/revision_ensamble_2026_11_19'
SALIDA=RAIZ/'resultados/prototipo/detalle_manual_2026_11_20'


def ejecutar():
    conservacion=verificar()
    documentos=json.loads((RAIZ/'control/detalle_manual_2026_11_20/documentos_recibidos.json').read_text(encoding='utf-8'))
    for nombre,esperado in documentos.items():
        if sha(RAIZ.parent/nombre)!=esperado:raise ValueError('Documento original cambió: '+nombre)
    config=json.loads((RAIZ/'configuraciones/detalle_manual.json').read_text(encoding='utf-8'))
    if (SALIDA/'parametros_utilizados.json').exists() and json.loads((SALIDA/'parametros_utilizados.json').read_text(encoding='utf-8'))!=config:
        raise ValueError('Parámetros diferentes: conservar revisión y crear otra carpeta de salida')
    analisis=json.loads((ANTERIOR/'ensamble_auditado.json').read_text(encoding='utf-8'))
    dim=json.loads((ANTERIOR/'geometria_STEP.json').read_text(encoding='utf-8'))
    if sha(RAIZ/'geometrias/Prototipo.stp')!=analisis['meta']['sha256']:raise ValueError('Ensamble alterado')
    SALIDA.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(contactos_CAD(RAIZ/'geometrias/Prototipo.stp')).to_csv(SALIDA/'distancias_uniones_CAD.csv',index=False)
    p=presiones(config,dim);manivela=radio_manivela_CAD(analisis)
    if abs(manivela['radio_ejes_mm']/1000-config['radio_manivela_nominal_m'])>1e-6:raise ValueError('RadioCAD y radio nominal difieren; revisar antes de usar')
    historial=pd.read_csv(ANTERIOR/'historial_escenarios.csv.gz')
    resumen=[];series=[];resistencia=[];vidas=[];apoyos=[];criticos=[];mallas=[];ejes_series=[];arboles=[]
    ejemplo_agua=[dict(masa_inicial_kg=config['material_prueba']['masa_inicial_kg'],w0_base_humeda=config['material_prueba']['humedad_inicial_base_humeda'],
        wf_base_humeda=wf,agua_kg=agua_base_humeda(config['material_prueba']['masa_inicial_kg'],config['material_prueba']['humedad_inicial_base_humeda'],wf))
        for wf in config['material_prueba']['humedades_objetivo']]
    for h in config['escenarios_conservados']['capas_m']:
        mu=config['escenarios_conservados']['mu_efectivo_torque']
        base=historial[np.isclose(historial.capa_biomasa_hipotetica_m,h)&np.isclose(historial.presion_condicionada_pa,2260000)&np.isclose(historial.mu_efectivo_hipotetico,mu)].copy().reset_index(drop=True)
        if len(base)!=1440 or base.paso.nunique()!=1440:raise ValueError('No hay 1440 estados únicos correlacionados')
        d=base.copy();factor=p['P_CAD_pa']/2260000
        for col in d:
            if col.startswith(('fuerza_','torque_')):d[col]*=factor
        d['escenario']=f'manual_h{h:g}_Holm_CAD';d['presion_condicionada_pa']=p['P_CAD_pa']
        d['F_manivela_ideal_n']=fuerza_manual(d.torque_total_nm,config['radio_manivela_nominal_m'])
        d['tiempo_s']=None;d['potencia_w']=None
        series.append(d)
        r=resumir(d);jF=int(d.fuerza_total_n.idxmax());jT=int(d.torque_total_nm.idxmax())
        fila=dict(escenario=d.escenario.iloc[0],capa_supuesta_m=h,presion_estimada_pa=p['P_CAD_pa'],mu_efectivo=mu,
            fuerza_max_n=r['fuerza_total_max_n'],fuerza_media_n=r['fuerza_total_media_n'],torque_max_nm=r['torque_max_nm'],torque_medio_nm=r['torque_medio_nm'],
            fuerza_r1_max_n=float(d.fuerza_r1_n.max()),fuerza_r2_max_n=float(d.fuerza_r2_n.max()),
            suma_maximos_independientes_n=float(d.fuerza_r1_n.max()+d.fuerza_r2_n.max()),
            fuerza_manual_max_ideal_n=float(d.F_manivela_ideal_n.max()),fuerza_manual_media_ideal_n=float(d.F_manivela_ideal_n.mean()),
            longitud_contacto_m=float(d.longitud_contacto_r1_m.iloc[0]),area_total_max_m2=r['fuerza_total_max_n']/p['P_CAD_pa'],
            paso_fuerza_max=jF,paso_torque_max=jT,estado='alternativa condicionada, no nominal físico ni ensayo')
        resumen.append(fila)
        for tipo,indice in [('Fmax',jF),('Tmax',jT),('R1max',int(d.fuerza_r1_n.idxmax())),('R2max',int(d.fuerza_r2_n.idxmax()))]:
            row=d.iloc[indice].to_dict();row['tipo_critico']=tipo;criticos.append(row)
        tabla,error_reparto=reparto_CAD(d,analisis,mu)
        if error_reparto['error_fuerzas_n']>1e-8 or error_reparto['error_momentos_nm']>1e-8:raise ValueError('Reparto no conserva fuerza/momento')
        tabla['escenario']=fila['escenario'];tabla.to_csv(SALIDA/f'reacciones_608_h{h:g}.csv',index=False)
        for vida in referencia_608(tabla,analisis,config):vidas.append(dict(escenario=fila['escenario'],**vida))
        sd=config['sensibilidad_eje']
        for diam in sd['diametros_resistentes_m']:
            E=sd['E_referencia_pa'];serie,rr=viga_detalle(tabla,analisis,diam,E,80)
            serie['escenario']=fila['escenario'];serie['diametro_resistente_hipotetico_m']=diam;serie['E_hipotetico_pa']=E;ejes_series.append(serie)
            for Es in sd['E_sensibilidad_pa']:
                salida=dict(rr);salida.update(E_hipotetico_pa=Es,flecha_resultante_max_m=rr['flecha_resultante_max_m']*E/Es,
                    cambio_holgura_contacto_max_m=rr['cambio_holgura_contacto_max_m']*E/Es,
                    flecha_sobre_holgura_CAD=rr['flecha_sobre_holgura_CAD']*E/Es,
                    cambio_holgura_sobre_gap_CAD=rr['cambio_holgura_sobre_gap_CAD']*E/Es)
                resistencia.append(dict(escenario=fila['escenario'],**salida))
            if diam==sd['diametros_resistentes_m'][0]:
                for divisiones in (40,80,160):
                    _,rmesh=viga_detalle(tabla,analisis,diam,E,divisiones)
                    mallas.append(dict(escenario=fila['escenario'],**rmesh))
            # La placa recibe la reacción opuesta; aquí se guardan magnitudes
            # por apoyo, nunca una fuerza de tuerca inferida de carga radial.
            if diam==sd['diametros_resistentes_m'][0]:
                taladros=analisis['taladros_soporte_transversal']
                for i,taladro in enumerate(taladros):
                    R=np.hypot(serie[f'R_Y_apoyo{i+1}_n'],serie[f'R_Z_apoyo{i+1}_n'])
                    j=int(np.argmax(R));espesor=taladro['largo_mm']/1000;diam_h=taladro['radio_mm']*2/1000
                    delta=analisis['rodillos'][0]['separacion_envolvente_matriz_mm']/1000*config['sensibilidad_soporte_ABS']['fraccion_holgura_para_desplazamiento']
                    apoyos.append(dict(escenario=fila['escenario'],apoyo=i+1,paso_max=j,reaccion_resultante_max_n=float(R.iloc[j]),
                        Y_sobre_eje_n=float(serie[f'R_Y_apoyo{i+1}_n'].iloc[j]),Z_sobre_eje_n=float(serie[f'R_Z_apoyo{i+1}_n'].iloc[j]),
                        espesor_local_CAD_m=espesor,diametro_taladro_m=diam_h,
                        presion_proyectada_requerida_pa=float(R.max()/(diam_h*espesor)),
                        desplazamiento_presupuesto_hipotetico_m=delta,rigidez_secante_min_hipotetica_n_m=float(R.max()/delta),
                        estado='Reacción de viga rígidamente apoyada; p=R/(d*t) promedio nominal, no esfuerzo máximo ni resistenciaABS'))
        # Reutilización de ecuaciones nominales4B sin ejecutar su script
        # histórico. Toda F axial en la sección es una hipótesis explícita.
        diam_arbol=analisis['apoyo_inferior']['diametro_arbol_mm']/1000
        sa,tt,vm=seccion_arbol(d.fuerza_total_n,d.torque_total_nm,diam_arbol)
        idx=int(np.argmax(vm))
        arboles.append(dict(escenario=fila['escenario'],diametro_liso_CAD_m=diam_arbol,paso_VM_max=idx,
            F_correlacionada_n=float(d.fuerza_total_n.iloc[idx]),T_correlacionado_nm=float(d.torque_total_nm.iloc[idx]),
            sigma_axial_pa=float(sa[idx]),tau_torsion_pa=float(tt[idx]),VM_axial_torsion_pa=float(vm[idx]),
            Sy_min_nominal_n1_pa=float(vm[idx]),factor_seguridad=None,
            estado='Solo si sección lisa transmite toda F yT; sin flexión, raíz real, apoyos o unión verificados'))
    pd.DataFrame(resumen).to_csv(SALIDA/'solicitaciones_manuales.csv',index=False)
    pd.concat(series).to_csv(SALIDA/'historial_manual.csv.gz',index=False,compression='gzip')
    pd.concat(ejes_series).to_csv(SALIDA/'historial_eje_condicionado.csv.gz',index=False,compression='gzip')
    for nombre,datos in [('casos_criticos_correlacionados',criticos),('eje_sensibilidad',resistencia),('convergencia_viga',mallas),
        ('rodamientos_EZO_referencia',vidas),('carcasa_impresa_cargas_y_requisitos',apoyos),('arbol_secciones_nominales',arboles),('acondicionamiento_aserrin',ejemplo_agua)]:
        pd.DataFrame(datos).to_csv(SALIDA/f'{nombre}.csv',index=False)
    abs_ref=json.loads((RAIZ/'fisica/ABS_referencia.json').read_text(encoding='utf-8'))
    abs_comparacion=[]
    for apoyo in apoyos:
        for material in abs_ref['orientaciones']:
            abs_comparacion.append(dict(escenario=apoyo['escenario'],apoyo=apoyo['apoyo'],orientacion_referencia=material['orientacion'],
                E_compresion_referencia_pa=material['E_compresion_pa'],E_traccion_referencia_pa=material['E_traccion_pa'],
                fluencia_traccion_tipica_referencia_pa=material['fluencia_traccion_tipica_pa'],
                presion_proyectada_pa=apoyo['presion_proyectada_requerida_pa'],
                epsilon_indicador_uniaxial_homogeneo=apoyo['presion_proyectada_requerida_pa']/material['E_compresion_pa'],
                A_sobre_L_requerido_si_compresion_uniforme_m=apoyo['rigidez_secante_min_hipotetica_n_m']/material['E_compresion_pa'],
                factor_seguridad=None,estado='DiseñoABS: propiedades típicas F900-T16, no mínimo garantizado. Indicador p/E y requisitoEA/L, no deformación de carcasa ni aprobación de apoyo.'))
    pd.DataFrame(abs_comparacion).to_csv(SALIDA/'ABS_comparacion_propiedades_y_rigidez.csv',index=False)
    antiguos=config['cargas_antiguas_transcritas']
    comercial_path=RAIZ.parent/'Simulación_peletizadora/resultados/etapa_3c_acoplamiento/resumen_comparativo.csv'
    comercial=pd.read_csv(comercial_path).query("modelo == 'inclinacion'").iloc[0]
    guardar_json(SALIDA/'consistencia_razones_antiguas.json',dict(
        fuerza_total_por_lambda_F_n=float(comercial.fuerza_total_max_n*antiguos['lambda_F']),
        fuerza_rodillo_por_lambda_F_n=float(comercial.fuerza_r1_max_n*antiguos['lambda_F']),
        torque_por_lambda_T_nm=float(comercial.torque_max_nm*antiguos['lambda_T']),
        fuerza_total_reportada_n=antiguos['fuerza_max_n'],fuerza_rodillo_reportada_n=antiguos['fuerza_individual_reportada_n'],torque_reportado_nm=antiguos['torque_max_nm'],
        conclusion='Coincidencia por redondeo con razones documentadas aplicadas a máximos3C; no demuestra derivación geométrica ni estados del prototipo. Remisiones internas no coinciden con anexosEP2 disponibles.'))
    reconciliacion=[]
    for r in resumen:
        reconciliacion.append(dict(escenario=r['escenario'],F_antigua_transcrita_n=antiguos['fuerza_max_n'],T_antiguo_transcrito_nm=antiguos['torque_max_nm'],
            F_actual_condicionada_n=r['fuerza_max_n'],T_actual_condicionado_nm=r['torque_max_nm'],
            diferencia_F_relativa_a_antiguo=r['fuerza_max_n']/antiguos['fuerza_max_n']-1,
            diferencia_T_relativa_a_antiguo=r['torque_max_nm']/antiguos['torque_max_nm']-1,
            diferencia_presion_relativa_a_2_26MPa=p['P_CAD_pa']/2260000-1,
            area_implicita_F_antigua_m2=antiguos['fuerza_max_n']/p['P_literal_transcripcion_pa'],
            fuente_antigua='Ingenieria_de_Detalles.pdf PDFp2, continuación1.1; EP2 A.2.1/A.2.2 PDFpp13–14 no contienen historial del prototipo',
            conclusion='Presión no explica diferencia principal; documentos no especifican huella, capa ni estados originales del prototipo. No se ajustan parámetros para igualar.' ))
    pd.DataFrame(reconciliacion).to_csv(SALIDA/'reconciliacion_resultados.csv',index=False)
    pd.DataFrame([
        dict(parametro='Matriz',documento_anterior='Nominal100mm y10mm,102 agujeros6mm; DetallesPDFp3',CAD_actual='99mm;10perforado;26total;102 agujeros6mm',diagnostico='Discrepancia nominal1mm; no escala pura'),
        dict(parametro='Rodillos',documento_anterior='52x30mm EP2PDFp11',CAD_actual='52x30mm',diagnostico='Dimensiones compatibles; no confirma huella real'),
        dict(parametro='Centros de rodillos',documento_anterior='No especificados numéricamente para prototipo en páginas recibidas',CAD_actual='27,838064 y27,661936mm',diagnostico='Geometría anterior insuficiente para comparación de histograma'),
        dict(parametro='Capa de biomasa',documento_anterior='4mm en COMERCIAL EP2PDFp15, no nominal del prototipo',CAD_actual='Sensibilidades1/2/4mm',diagnostico='Hipótesis distintas/no completamente documentadas'),
        dict(parametro='Separación',documento_anterior='Prototipo no especificado en Detalles;0,1mm en comercial',CAD_actual='0,5mm nominalCAD, no galga medida',diagnostico='No trasladar holgura comercial'),
        dict(parametro='Longitud tangencial',documento_anterior='Sin valor del prototipo; ecuaciones9/19 deEP2',CAD_actual='5,074/8,703/13,029mm',diagnostico='Huella anterior no recuperable; convenciónLc deEP2 conservada sin ajustar'),
        dict(parametro='Presión',documento_anterior='2,259MPa teóricos DetallesPDFp3 ec1',CAD_actual='2,258671MPa exactos y2,26MPa revisión previa',diagnostico='Diferencia0,0588% no explica diferencia dominante'),
        dict(parametro='Área abierta',documento_anterior='Detalles afirma aumento al escalar matriz',CAD_actual='Área absoluta102*pi*3²=2883,982mm² igual a comercial; aumenta fracción de cara',diagnostico='Distinguir área abierta absoluta, fracción y área parcialmente cubierta'),
        dict(parametro='Torque',documento_anterior='mu efectivo0,1 EP2p14/16; detalle da3,255Nm sin historialpropio',CAD_actual='sum(mu_eff*Fi*ri) por radios reales de agujeros',diagnostico='No usar0,715 como mu de torque ni inferir brazo físico de Tmax/Fmax no correlacionados'),
        dict(parametro='Máximos',documento_anterior='1029Ntotal y586Nporrodillo sin estado; compatibles con razones aplicadas a envolventes3C',CAD_actual='Máximos por estado y por rodillo conservados separados',diagnostico='2*586=1172 no es1029; no error probado si máximos no simultáneos, definición anterior ambigua'),
        dict(parametro='Modelo angular',documento_anterior='EP2 tiene1440 estados de comercial; Detalles no aporta historialprototipo',CAD_actual='1440 estados reales de matrizSTEP, máximosF/T separados',diagnostico='No se ha detectado error de regresión; no forzar equivalencia entre geometrías'),
        dict(parametro='Remisiones',documento_anterior='Detalles cita A.1.1/A.1.2/A.1.3 yA.2.2 para prototipo',CAD_actual='EP2A.2.1/A.2.2 son predimensionamiento comercial',diagnostico='Inconsistencia de referencias entre versiones; se identifica por contenido')
    ]).to_csv(SALIDA/'auditoria_hipotesis_antiguas_vs_CAD.csv',index=False)
    interfaz=[];uniones=[]
    for d,r in zip(series,resumen):
        f=d[['paso','angulo_grados','escenario','fuerza_total_n','torque_total_nm','F_manivela_ideal_n']].copy()
        f=f.rename(columns={'fuerza_total_n':'F_axial_compactacion_n','torque_total_nm':'T_resistente_nm','F_manivela_ideal_n':'F_lateral_mano_tangencial_ideal_n'})
        f['M_normales_solo_proyeccion_radial_nm']=abs(d.fuerza_r1_n*d.centroide_radial_r1_m-d.fuerza_r2_n*d.centroide_radial_r2_m)
        f['nota']='Magnitudes de entrada, no reacciones: axial matriz hacia-YCAD, torque resistenteopuesto al giro; dirección mano dependeángulo. Momento solo proyección radial, omite centroides tangenciales. Pesos, pérdidas y atasco pendientes.'
        interfaz.append(f)
        # Anillo ideal de la arandelaCAD: no asumir contacto completo ni
        # precarga real. Se deriva geometría del sólido identificado14.
        arandela=next(x for x in analisis['inventario'] if x['id']==14)
        radios=sorted(c['radio_mm']/1000 for c in arandela['cilindros']);ri,ro=radios[0],radios[-1]
        area=math.pi*(ro**2-ri**2);reff=2*(ro**3-ri**3)/(3*(ro**2-ri**2))
        uniones.append(dict(escenario=r['escenario'],area_anillo_ideal_m2=area,radio_friccion_uniforme_ideal_m=reff,
            presion_media_max_si_todaF_en_una_arandela_pa=r['fuerza_max_n']/area,
            producto_mu_por_normal_necesario_max_n=r['torque_max_nm']/reff,
            k_axial_min_formula='F_axial(t)/delta_axial_admisible; delta y reparto por apoyo sin definir',
            resistencia_axial_total_al_menos_n=r['fuerza_max_n'],factor_seguridad=None,
            estado='AnilloCADØ24/13, contacto completo y presión uniforme hipotéticos; producto mu*N no es precarga conocida. Sin aprobación de fricción, rosca, soporte o arandela.'))
    pd.concat(interfaz).to_csv(SALIDA/'interfaz_arbol_soportes_manual.csv.gz',index=False,compression='gzip')
    pd.DataFrame(uniones).to_csv(SALIDA/'uniones_y_soporte_axial_condicionados.csv',index=False)
    guardar_json(SALIDA/'parametros_utilizados.json',config)
    guardar_json(SALIDA/'presion_y_manivela.json',dict(presion=p,manivela_CAD=manivela,
        fuerza_antigua_ideal_n=float(fuerza_manual(antiguos['torque_max_nm'],config['radio_manivela_nominal_m'])),
        fuerza_con_perdidas_conocidas_n=None,arranque_atascamiento_n=None,
        estado='Accionamiento manual por instrucción del equipo; no usar motor180W como nominal'))
    _documentar(config,p,resumen,resistencia,arboles)
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    for d,r in zip(series,resumen):
        axes[0].plot(d.angulo_grados,d.fuerza_total_n,label=f"Capa supuesta {r['capa_supuesta_m']*1000:g} mm")
        axes[1].plot(d.angulo_grados,d.F_manivela_ideal_n)
    axes[0].set(ylabel='F total [N]',title='CAD + presión teórica; alternativas condicionadas');axes[0].legend()
    axes[1].set(xlabel='Ángulo matriz [°]',ylabel='F manivela ideal [N]')
    fig.tight_layout();fig.savefig(SALIDA/'cargas_y_manivela.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for diam in config['sensibilidad_eje']['diametros_resistentes_m']:
        grupo=[x for x in resistencia if x['diametro_resistente_hipotetico_m']==diam and x['E_hipotetico_pa']==205e9]
        capas=[r['capa_supuesta_m']*1000 for r in resumen]
        axes[0].plot(capas,[x['sigma_flexion_nominal_max_pa']/1e6 for x in grupo],marker='o',label=f'd supuesto={diam*1000:g} mm')
        axes[1].plot(capas,[x['cambio_holgura_contacto_max_m']*1000 for x in grupo],marker='o',label=f'd supuesto={diam*1000:g} mm')
    axes[0].set(xlabel='Capa supuesta [mm]',ylabel='Flexión nominal máxima [MPa]')
    axes[1].axhline(.5,color='k',linestyle='--',label='Separación inicial CAD0,5mm')
    axes[1].set(xlabel='Capa supuesta [mm]',ylabel='Cambio de holgura en bordes [mm]')
    for ax in axes:ax.legend(fontsize=8)
    fig.suptitle('Cribado elástico desacoplado; E=205GPa y apoyos rígidos hipotéticos. Sin aprobación resistente.')
    fig.tight_layout();fig.savefig(SALIDA/'eje_flecha_y_holgura.png',dpi=160);plt.close(fig)
    guardar_json(SALIDA/'resumen.json',dict(accionamiento='manual_manivela',nominal_fisico_unico=None,
        presion_estimada=p,solicitaciones=resumen,seguridad_aprobada=False,
        documentos_originales_detalles_disponibles=True,conservacion=verificar()))
    entradas=[RAIZ/'configuraciones/detalle_manual.json',RAIZ/'geometrias/Prototipo.stp',RAIZ/'geometrias/Matriz_prototipo.stp',
        ANTERIOR/'historial_escenarios.csv.gz',ANTERIOR/'ensamble_auditado.json',ANTERIOR/'geometria_STEP.json',
        RAIZ/'peletizadora/detalle_manual.py',Path(__file__),RAIZ/'referencias.bib',RAIZ/'peletizadora/verificaciones.py',comercial_path,
        RAIZ.parent/'Documentacion/Entrega_2.pdf',RAIZ.parent/'Documentacion/Ingenieria_de_Detalles.pdf',
        RAIZ/'peletizadora/documentacion_detalle.py',RAIZ/'control/detalle_manual_2026_11_20/solicitud_equipo.txt',RAIZ/'fisica/ABS_referencia.json',RAIZ/'fisica/referencias_detalle.bib']
    guardar_json(SALIDA/'fuentes_sha256.json',{os.path.relpath(f,RAIZ):sha(f) for f in entradas})
    from simular import version_codigo
    guardar_json(SALIDA/'version_codigo.json',version_codigo())
    return resumen


def _documentar(config,p,resumen,resistencia,arboles):
    # Documentación y LaTeX se generan desde las mismas tablas numéricas.
    from peletizadora.documentacion_detalle import generar
    generar(RAIZ,SALIDA,config,p,resumen,resistencia,arboles)


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(ejecutar(),ensure_ascii=False,indent=2))
