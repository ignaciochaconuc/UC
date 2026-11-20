"""Postproceso resistente M8; consume3C guardado y no llama a simular()."""
import json,os,time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from acoplado_m8 import entradas,BASE
from peletizadora.acoplado_prototipo import ModeloAcoplado
from peletizadora.resistencia_m8 import (reconstruir,factor_estatico_nominal,ciclos_ep2,
    requisitos_fatiga,exigencias_apoyos,sensibilidad_fijacion)
from peletizadora.informes import guardar_json
from herramientas.control_resistencia_m8 import verificar,sha

RAIZ=Path(__file__).resolve().parent
ORIGEN=RAIZ/'resultados/prototipo/acoplado_m8_2026_11_20'
SALIDA=RAIZ/'resultados/prototipo/resistencia_m8_2026_11_20'

def ejecutar():
    verificar();a,c,holes=entradas()
    conf=json.loads((RAIZ/'configuraciones/resistencia_m8.json').read_text(encoding='utf-8'))
    SALIDA.mkdir(parents=True,exist_ok=True)
    p=SALIDA/'parametros_utilizados.json'
    if p.exists() and json.loads(p.read_text(encoding='utf-8'))!=conf:raise ValueError('Cambió configuración; crear nueva revisión')
    guardar_json(p,conf)
    modelo=ModeloAcoplado(a,holes,c,c['varillas'][1])
    estaticos=[];fatiga=[];apoyos=[];rigidez=[];nominales=[];validaciones=[];historias=[];t0=time.monotonic()
    for h in c['capas_m']:
        serie=pd.read_csv(ORIGEN/f'serie_M8x1.25_h{h*1000:g}mm.csv')
        fy,fz,my,mz,sigma=reconstruir(modelo,serie)
        tau=16*np.hypot(my[:,[0,2]],mz[:,[0,2]])/(3*np.pi*modelo.d**2)
        maximos=sigma.max(axis=(0,1));idx=np.unravel_index(np.argmax(sigma),sigma.shape)
        nominales.append(dict(capa_m=h,sigma_nominal_max_pa=float(sigma.max()),tau_corte_nominal_max_pa=float(tau.max()),
            x_m=float(modelo.nodos[idx[0]+idx[1]]),paso_sigma_max=int(serie.paso.iloc[idx[2]]),
            fuerza_correlacionada_n=float(serie.fuerza_total_n.iloc[idx[2]]),torque_correlacionado_nm=float(serie.torque_total_nm.iloc[idx[2]]),
            limite_modelo='Sección uniforme de raíz6,466mm, elasticidad y doble empotramiento hipotéticos. Sin axial de precarga.'))
        for mat in conf['clases']:
            for ent in conf['entallas']:
                estaticos.append(dict(capa_m=h,clase=mat['clase'],Kt_sensibilidad=ent['Kt'],entalla=ent['nombre'],
                    sigma_nominal_max_pa=float(sigma.max()),Sy_min_clase_pa=mat['Sy_min_pa'],
                    n_flexion_condicional=factor_estatico_nominal(mat['Sy_min_pa'],float(sigma.max()),ent['Kt']),
                    Kt_max_permitido_solo_n1=mat['Sy_min_pa']/float(sigma.max()),
                    n_corte_nominal_solo=mat['Sy_min_pa']/(np.sqrt(3)*float(tau.max())),
                    factor_estatico_real=None,aprobado=False,
                    estado='Factor de flexión condicionado a producto certificado de clase yKt supuesto; no incluye precarga,entallas verificadas,fretting,aplastamiento ni montaje'))
        ciclos=ciclos_ep2(my,mz,modelo,conf['fatiga']['fibras'])
        ciclos.to_csv(SALIDA/f'ciclos_rainflow_h{h*1000:g}mm.csv.gz',index=False,compression='gzip')
        req=requisitos_fatiga(ciclos,conf['clases'],conf['entallas'])
        for r in req:r['capa_m']=h
        fatiga.extend(req)
        bajos=ciclos_ep2(my,mz,modelo,conf['fatiga']['fibras_contraste'])
        req_bajos=requisitos_fatiga(bajos,conf['clases'],conf['entallas'])
        for alto,bajo in zip(req,req_bajos):
            Sealto=alto['Se_min_requerido_n1_pa'];Sebajo=bajo['Se_min_requerido_n1_pa']
            validaciones.append(dict(capa_m=h,clase=alto['clase'],entalla=alto['entalla'],
                fibras=144,fibras_contraste=72,error_Se_requerido_relativo=None if Sealto is None or Sebajo is None else abs(Sealto-Sebajo)/max(Sealto,1),
                error_reconstruccion_sigma_pa=float(np.max(abs(maximos-serie.sigma_nominal_max_pa)))))
        # Exportar el historial firmado del punto que gobierna el requisito
        # de referencia8.8/moderado, sin presentarlo como único caso material.
        fila=next(r for r in req if r['clase']=='8.8' and r['entalla']=='sensibilidad_EP2_moderada')
        from peletizadora.resistencia_m8 import secciones_de_carga,tension_flexion_punto
        seccion=next(x for x in secciones_de_carga(modelo) if x[0]==fila['seccion'])
        _,e,lado,x=seccion
        signo=-1 if lado==0 else 1
        firmado=tension_flexion_punto(signo*my[e,1+2*lado],signo*mz[e,1+2*lado],modelo.d,fila['phi_rad'])
        historia=serie[['paso','angulo_grados']].copy();historia['sigma_firmada_pa']=firmado
        historia['capa_m']=h;historia['seccion']=fila['seccion'];historia['phi_rad']=fila['phi_rad'];historias.append(historia)
        for r in exigencias_apoyos(serie,a,conf):r['capa_m']=h;apoyos.append(r)
        for r in sensibilidad_fijacion(modelo,fy,fz,conf):r['capa_m']=h;rigidez.append(r)
        print('Postproceso',h*1000,'mm; sigma',float(sigma.max()/1e6),'MPa; ciclos',len(ciclos),flush=True)
    for nombre,filas in [('factores_estaticos_condicionados',estaticos),('requisitos_fatiga_Goodman',fatiga),
        ('demandas_apoyos_ABS',apoyos),('sensibilidad_rigidez_fijaciones',rigidez),
        ('tensiones_nominales_correlacionadas',nominales),('validaciones_numericas',validaciones),
        ('clases_comerciales',conf['clases'])]:
        pd.DataFrame(filas).to_csv(SALIDA/f'{nombre}.csv',index=False)
    pd.concat(historias).to_csv(SALIDA/'historial_firmado_referencia.csv.gz',index=False,compression='gzip')
    from peletizadora.memoria_resistencia_m8 import generar
    generar(SALIDA,a,conf,estaticos,fatiga,apoyos)
    fig,ax=plt.subplots(figsize=(7,4))
    for mat in conf['clases']:
        r=[x for x in estaticos if x['clase']==mat['clase'] and x['capa_m']==.004]
        ax.plot([x['Kt_sensibilidad'] for x in r],[x['n_flexion_condicional'] for x in r],marker='o',label='Clase'+mat['clase'])
    ax.axhline(1,color='k',ls='--');ax.set(xlabel='Kt supuesto referido a tensión de raíz',ylabel='Factor de flexión condicional',
        title='Capa4mm; sin precarga ni aprobación. Kt no identificado en producto real.')
    ax.legend();fig.tight_layout();fig.savefig(SALIDA/'sensibilidad_estatica.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for historia in historias:
        ax.plot(historia.angulo_grados,historia.sigma_firmada_pa/1e6,label=f"Capa{historia.capa_m.iloc[0]*1000:g}mm")
    ax.set(xlabel='Ángulo de matriz [°]',ylabel='Tensión nominal firmada [MPa]',
        title='Fibras fijas que gobiernan el requisito8.8/Kt1,5; no flexión rotativa alternante')
    ax.legend();fig.tight_layout();fig.savefig(SALIDA/'historiales_firmados.png',dpi=170);plt.close(fig)
    fuentes=[RAIZ/'configuraciones/resistencia_m8.json',Path(__file__),RAIZ/'peletizadora/resistencia_m8.py',
        RAIZ/'peletizadora/memoria_resistencia_m8.py',RAIZ/'peletizadora/acoplado_prototipo.py',
        RAIZ.parent/'Simulación_peletizadora/estructural/resistencia_fatiga.py',RAIZ/'fisica/ABS_referencia.json',
        RAIZ/'fisica/referencias_resistencia_m8.bib']
    fuentes.extend(ORIGEN/f'serie_M8x1.25_h{h*1000:g}mm.csv' for h in c['capas_m'])
    guardar_json(SALIDA/'fuentes_sha256.json',{os.path.relpath(p,RAIZ).replace('\\','/'):sha(p) for p in fuentes})
    guardar_json(SALIDA/'resumen.json',dict(alternativa_preferente='M8, no aprobado',modelo_3C_modificado=False,
        resultados_3C_recalculados=False,factor_estatico_real=None,factor_fatiga_real=None,
        escenario_nominal_unico=None,casos=nominales,tiempo_s=time.monotonic()-t0,conservacion=verificar(),
        pendientes=['Kt/Kf de raíz y primeraespira, clase de lote, Se/proceso/superficie, precarga y ciclo deuso',
            'Rigidez y contacto de fijacionesABS, asientos608 y transiciones del eje liso',
            'Ninguna aprobación de montaje o vida sin esos datos']))
    return nominales

if __name__=='__main__':ejecutar()
