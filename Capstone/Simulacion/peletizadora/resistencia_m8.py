"""Postproceso de resultados3C congelados; resistencia y fatiga de EP2."""
import math
import numpy as np
import pandas as pd
from scipy.sparse import diags
from scipy.sparse.linalg import splu
from .nucleo import positivo
from .acoplado_prototipo import ModeloAcoplado
from estructural.resistencia_fatiga import (tension_flexion_punto,contar_rainflow,
    EscenarioMaterial,EscenarioEntalla,factor_goodman,seleccionar_ciclo_goodman)

def reconstruir(modelo,serie):
    if not serie.convergio.all() or len(serie)!=1440 or serie.paso.nunique()!=1440:
        raise ValueError('Se requieren1440estados convergidos y únicos')
    ids=[b['solido_id'] for par in modelo.pares for b in par]
    fy=np.vstack([serie[f'carga_normal_608_{i}_n'].to_numpy() for i in ids])
    fz=fy*np.array(modelo.signos)[:,None]*modelo.c['mu_efectivo']
    my=modelo.MVp[:,:,None]+np.einsum('eik,kn->ein',modelo.MV,fy)
    mz=np.einsum('eik,kn->ein',modelo.MV,fz)
    sigma=32*np.hypot(my[:,[1,3]],mz[:,[1,3]])/(math.pi*modelo.d**3)
    if not np.allclose(sigma.max(axis=(0,1)),serie.sigma_nominal_max_pa,rtol=1e-10,atol=.01):
        raise ValueError('Reconstrucción no coincide con esfuerzos3C guardados')
    return fy,fz,my,mz,sigma

def factor_estatico_nominal(Sy,sigma,Kt=1):
    for n,v in [('Sy',Sy),('sigma',sigma),('Kt',Kt)]:positivo(v,n)
    if Kt<1:raise ValueError('Kt inferior a uno')
    return Sy/(Kt*sigma)

def Se_requerido(amplitud,media,Sut,Kt,Kf,n=1):
    for nombre,v in [('Sut',Sut),('Kt',Kt),('Kf',Kf),('n',n)]:positivo(v,nombre)
    if not np.isfinite(amplitud) or not np.isfinite(media) or amplitud<0:raise ValueError('Ciclo inválido')
    restante=1/n-Kt*max(media,0)/Sut
    if restante<=0:return None
    return Kf*amplitud/restante

def secciones_de_carga(modelo):
    """Ambos lados de fijaciones y puntos de carga; no se inventan transiciones."""
    salida=[]
    for x in np.unique(np.r_[modelo.apoyos,modelo.xb]):
        nodo=modelo.indice(x)
        if nodo>0:salida.append((f'x{x:.9f}_izq',nodo-1,1,x))
        if nodo<len(modelo.nodos)-1:salida.append((f'x{x:.9f}_der',nodo,0,x))
    return salida

def ciclos_ep2(my,mz,modelo,numero_fibras):
    if numero_fibras<8:raise ValueError('Resolución insuficiente')
    angulos=np.linspace(0,2*math.pi,numero_fibras,endpoint=False);filas=[]
    for nombre,e,lado,x in secciones_de_carga(modelo):
        for phi in angulos:
            # EP2/analisis.py: momento interno continuo [-M_i,+M_j].
            signo=-1 if lado==0 else 1
            s=tension_flexion_punto(signo*my[e,1+2*lado],signo*mz[e,1+2*lado],modelo.d,phi)
            ciclos=contar_rainflow(s)
            if len(ciclos):
                ciclos=ciclos.copy();ciclos['seccion']=nombre;ciclos['x_m']=x;ciclos['phi_rad']=phi
                filas.append(ciclos)
    return pd.concat(filas,ignore_index=True) if filas else pd.DataFrame()

def requisitos_fatiga(ciclos,clases,entallas):
    resultados=[]
    for material in clases:
        Sut=material['Sut_min_pa']
        for ent in entallas:
            Kt=ent['Kt'];Kf=1+ent['q']*(Kt-1)
            restante=1-Kt*np.maximum(ciclos.media_pa.to_numpy(),0)/Sut
            imposibles=restante<=0
            requeridos=np.where(imposibles,np.inf,Kf*ciclos.amplitud_pa/np.maximum(restante,1e-300))
            k=int(np.argmax(requeridos));fila=ciclos.iloc[k]
            resultados.append(dict(clase=material['clase'],entalla=ent['nombre'],Kt=Kt,Kf=Kf,
                Se_min_requerido_n1_pa=None if imposibles.any() else float(requeridos[k]),
                imposible_por_media=bool(imposibles.any()),seccion=fila.seccion,x_m=float(fila.x_m),
                phi_rad=float(fila.phi_rad),amplitud_gobernante_pa=float(fila.amplitud_pa),media_mismo_ciclo_pa=float(fila.media_pa),
                conteo_mismo_ciclo=float(fila.conteo),factor_fatiga_real=None,
                estado='RequisitoGoodman conSut mínimo de clase yKt/Kf de sensibilidad; Se real desconocido, noFS aprobado'))
    return resultados

def exigencias_apoyos(serie,analisis,config):
    filas=[];taladros=sorted(analisis['taladros_soporte_transversal'],key=lambda t:t['centro_eje_mm'][0])
    for i,t in enumerate(taladros,1):
        Ry=serie[f'R_Y_A{i}_n'].to_numpy();Rz=serie[f'R_Z_A{i}_n'].to_numpy()
        My=serie[f'M_Y_A{i}_nm'].to_numpy();Mz=serie[f'M_Z_A{i}_nm'].to_numpy()
        R=np.hypot(Ry,Rz);M=np.hypot(My,Mz);largo=t['largo_mm']/1000;d=.008
        # Resultantes firmadas de tracción proyectada lineal. Signo opuesto
        # implica contacto en otro lado del bore, no tracción admisibleABS.
        p1=np.hypot(Ry/(d*largo)+6*My/(d*largo**2),Rz/(d*largo)+6*Mz/(d*largo**2))
        p2=np.hypot(Ry/(d*largo)-6*My/(d*largo**2),Rz/(d*largo)-6*Mz/(d*largo**2))
        pp=np.maximum(p1,p2);k=int(np.argmax(pp));delta=config['fijaciones_ABS']['presupuesto_incremento_holgura_m']
        filas.append(dict(apoyo=i,R_max_n=float(R.max()),M_resultante_max_nm=float(M.max()),
            paso_pico_traccion_proyectada=int(serie.paso.iloc[k]),R_mismo_paso_n=float(R[k]),M_mismo_paso_nm=float(M[k]),
            t_CAD_actual_referencia_m=largo,d_propuesto_m=d,p_media_corte_max_pa=float((R/(d*largo)).max()),
            traccion_proyectada_extrema_con_par_pa=float(pp.max()),
            rigidez_traslacional_min_si_todo_presupuesto_para_traslacion_n_m=float(R.max()/delta),
            presupuesto_hipotetico_delta_m=delta,
            nota='t es paredCADactual, no nuevo taladro8 verificado. Tracción lineal proyectada noFEM/contacto ni admisibleABS; precarga y rigidez reales pendientes.'))
    return filas

def sensibilidad_fijacion(modelo,fy,fz,config):
    """Cargas congeladas: NO itera contacto ni modifica resultados3C."""
    cargas=modelo.peso+np.zeros((len(modelo.Up),fy.shape[1]))
    for j,k in enumerate(modelo.gdl_b):cargas[k]+=fy[j]
    ref=modelo.estado_desde_u(modelo.Up[:,None]+modelo.U@fy)
    ajustes=[(1e12,k) for k in config['fijaciones_ABS']['k_rot_sensibilidad_nm_rad']]
    ajustes.extend((k,1e9) for k in config['fijaciones_ABS']['k_traslacion_sensibilidad_n_m'])
    salida=[]
    for kv,kr in ajustes:
        diagonal=np.zeros(len(modelo.Up))
        for x in modelo.apoyos:
            j=2*modelo.indice(x);diagonal[j]=kv;diagonal[j+1]=kr
        factor=splu((modelo.sistema.K+diags(diagonal)).tocsc())
        uy=factor.solve(cargas);estado=modelo.estado_desde_u(uy);diferencias=[]
        for j,r in enumerate(modelo.rodillos):
            for signo in (-1,1):
                diferencias.append(abs(estado[2*j]-ref[2*j]+signo*r['ancho_mm']/2000*(estado[2*j+1]-ref[2*j+1])))
        delta=float(np.max(diferencias));salida.append(dict(kv_hipotetico_n_m=kv,kr_hipotetico_nm_rad=kr,
            incremento_holgura_abs_max_con_cargas_congeladas_m=delta,
            satisface_solo_presupuesto_hipotetico=delta<=config['fijaciones_ABS']['presupuesto_incremento_holgura_m'],
            estado='Postproceso de rigidez, no nuevo3C ni soporte comercial; contacto no recalculado, no operación convergida'))
    return salida
