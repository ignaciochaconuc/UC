"""Revisión independiente de resultados M6/M8 con el algoritmo3C compartido."""
from pathlib import Path
import json,time,argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from peletizadora.acoplado_prototipo import ModeloAcoplado,resumir_acoplado
from peletizadora.informes import guardar_json
from herramientas.control_acoplado_m8 import verificar,sha

RAIZ=Path(__file__).resolve().parent
BASE=RAIZ/'resultados/prototipo/revision_ensamble_2026_11_19'
SALIDA=RAIZ/'resultados/prototipo/acoplado_m8_2026_11_20'

def entradas():
    a=json.loads((BASE/'ensamble_auditado.json').read_text(encoding='utf-8'))
    c=json.loads((RAIZ/'configuraciones/acoplado_m8.json').read_text(encoding='utf-8'))
    holes=pd.read_csv(BASE/'perforaciones_STEP.csv')
    if sha(RAIZ/'geometrias/Prototipo.stp')!=a['meta']['sha256']:raise ValueError('Ensamble no corresponde al auditado')
    return a,c,holes

def ejecutar():
    verificar();a,c,holes=entradas();SALIDA.mkdir(parents=True,exist_ok=True)
    parametros=SALIDA/'parametros_utilizados.json'
    if parametros.exists() and json.loads(parametros.read_text(encoding='utf-8'))!=c:raise ValueError('Cambió configuración; crear otra revisión')
    guardar_json(parametros,c)
    resumen=[];criticos=[];validaciones=[];t0=time.monotonic()
    for varilla in c['varillas']:
        modelo=ModeloAcoplado(a,holes,c,varilla)
        for h in c['capas_m']:
            nombre=f"{varilla['nombre']}_h{h*1000:g}mm"
            df,hist=modelo.simular(h)
            df.to_csv(SALIDA/f'serie_{nombre}.csv',index=False)
            hist.to_csv(SALIDA/f'iteraciones_{nombre}.csv.gz',index=False,compression='gzip')
            r=resumir_acoplado(df);r.update(varilla=varilla['nombre'],capa_m=h,E_pa=modelo.E,d_resistente_m=modelo.d)
            resumen.append(r);guardar_json(SALIDA/f'resumen_{nombre}.json',r)
            print(nombre,'convergieron',r['convergidos'],'/',r['estados'],'Fmax',r.get('Fmax_n'),'Tmax',r.get('Tmax_nm'),flush=True)
            if r['todos_convergieron']:
                for campo in ('fuerza_total_n','torque_total_nm','sigma_nominal_max_pa','flecha_max_m','holgura_r1_max_m','holgura_r2_max_m'):
                    row=df.loc[df[campo].idxmax()].to_dict();row['critico_por']=campo;criticos.append(row)
            # Contrastes en los mismos32ángulos, con arranque desde cero para
            # no confundir independencia del estado inicial con continuidad.
            d0,_=modelo.simular(h,pasos=32,inicial_cero=True)
            for tipo,valor in [('cuadratura',128),('relajacion',.35),('relajacion',.7),('malla',160)]:
                mm=ModeloAcoplado(a,holes,c,varilla,divisiones=160) if tipo=='malla' else modelo
                dc,_=mm.simular(h,pasos=32,orden=128 if tipo=='cuadratura' else None,
                    relajacion=valor if tipo=='relajacion' else None,inicial_cero=True)
                ok=bool(d0.convergio.all() and dc.convergio.all())
                fila=dict(varilla=varilla['nombre'],capa_m=h,contraste=tipo,valor=valor,todos_convergieron=ok)
                if ok:
                    fila.update(error_Fmax_rel=float(np.max(abs(dc.fuerza_total_n-d0.fuerza_total_n))/d0.fuerza_total_n.max()),
                        error_Tmax_rel=float(np.max(abs(dc.torque_total_nm-d0.torque_total_nm))/d0.torque_total_nm.max()),
                        error_g_abs_m=float(max(np.max(abs(dc[f'holgura_r{j}_centro_m']-d0[f'holgura_r{j}_centro_m'])) for j in (1,2))))
                validaciones.append(fila)
            if varilla['nombre'].startswith('M8'):
                for E in c['material']['E_sensibilidad_pa']:
                    dm,_=ModeloAcoplado(a,holes,c,varilla,E=E).simular(h,pasos=32,inicial_cero=True)
                    er=resumir_acoplado(dm);er.update(varilla=varilla['nombre'],capa_m=h,E_pa=E,estado='sensibilidad32angulos, no otro material certificado')
                    guardar_json(SALIDA/f"sensibilidad_E_{E:g}_h{h*1000:g}mm.json",er)
    pd.DataFrame(resumen).drop(columns=['no_convergidos']).to_csv(SALIDA/'comparacion_M6_M8.csv',index=False)
    pd.DataFrame(criticos).to_csv(SALIDA/'casos_criticos_correlacionados.csv',index=False)
    pd.DataFrame(validaciones).to_csv(SALIDA/'validaciones_numericas.csv',index=False)
    comparaciones=[]
    for h in c['capas_m']:
        m6=next(r for r in resumen if r['capa_m']==h and r['varilla'].startswith('M6'))
        m8=next(r for r in resumen if r['capa_m']==h and r['varilla'].startswith('M8'))
        if m6['todos_convergieron'] and m8['todos_convergieron']:
            comparaciones.append(dict(capa_m=h,reduccion_flecha_porcentaje=100*(1-m8['flecha_max_m']/m6['flecha_max_m']),
                reduccion_sigma_porcentaje=100*(1-m8['sigma_max_pa']/m6['sigma_max_pa']),
                incremento_F_porcentaje=100*(m8['Fmax_n']/m6['Fmax_n']-1),
                holgura_M8_positiva=bool(min(m8['g1_min_m'],m8['g2_min_m'])>0),
                holgura_M8_menor_capa=bool(max(m8['g1_max_m'],m8['g2_max_m'])<h),
                tolerancia_funcional_aprobada=False,nota='No existe banda operativa admisible documentada; sin validación física del empotramiento o del material'))
    pd.DataFrame(comparaciones).to_csv(SALIDA/'efecto_del_cambio_M6_M8.csv',index=False)
    from peletizadora.memoria_acoplado_m8 import generar
    generar(SALIDA,a,c,resumen,comparaciones)
    fuentes=[RAIZ/'configuraciones/acoplado_m8.json',RAIZ/'geometrias/Prototipo.stp',BASE/'ensamble_auditado.json',BASE/'perforaciones_STEP.csv',
        RAIZ/'peletizadora/acoplado_prototipo.py',RAIZ/'peletizadora/memoria_acoplado_m8.py',Path(__file__),
        RAIZ.parent/'Simulación_peletizadora/estructural/acoplamiento.py',RAIZ.parent/'Simulación_peletizadora/modelos/superposicion_variable.py',
        RAIZ.parent/'Simulación_peletizadora/estructural/viga_eb.py',RAIZ/'fisica/materiales.json',RAIZ/'fisica/referencias_acoplado_m8.bib']
    import os
    guardar_json(SALIDA/'fuentes_sha256.json',{os.path.relpath(p,RAIZ).replace('\\','/'):sha(p) for p in fuentes})
    guardar_json(SALIDA/'resumen_integral.json',dict(casos=resumen,comparacion=comparaciones,conservacion=verificar(),
        segundos=time.monotonic()-t0,seguridad_aprobada=False,CAD_modificado=False,modelo='3C con inclinación, presión uniforme y viga elástica EB'))
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for v in c['varillas']:
        rr=[r for r in resumen if r['varilla']==v['nombre'] and r['todos_convergieron']]
        ax[0].plot([r['capa_m']*1000 for r in rr],[r['flecha_max_m']*1000 for r in rr],marker='o',label=v['nombre'])
        ax[1].plot([r['capa_m']*1000 for r in rr],[max(r['g1_max_m'],r['g2_max_m'])*1000 for r in rr],marker='o',label=v['nombre'])
    ax[0].set(xlabel='Capa supuesta [mm]',ylabel='Flecha máxima convergida [mm]')
    ax[1].axhline(.5,color='k',ls='--',label='Separación CAD inicial0,5mm')
    ax[1].set(xlabel='Capa supuesta [mm]',ylabel='Holgura máxima convergida [mm]')
    for x in ax:x.legend()
    fig.suptitle('Comparación acoplada: mismos empotramientos hipotéticos y acero de referencia')
    fig.tight_layout();fig.savefig(SALIDA/'comparacion_acoplada.png',dpi=170);plt.close(fig)
    return resumen

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();ejecutar()
