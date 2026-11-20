"""Cobertura y cargas compartidas. SI: m, N, Pa, N m, W, s.

No conoce nombres de máquinas, cantidades esperadas o geometrías escaladas.
Conserva la ecuación de torque EP2 por radio del centro de perforación.
"""
import math
import numpy as np
import pandas as pd
from .legado import interseccion_disco_rectangulo, coordenadas_locales, contribuciones_torque_nm, potencia_resistente_w
from modelos.superposicion_variable import longitud_contacto_desde_holgura


def positivo(valor,nombre):
    if isinstance(valor,bool) or not isinstance(valor,(int,float)) or not math.isfinite(valor) or valor<=0:
        raise ValueError(nombre+': se requiere un número positivo finito')


def requisitos_carga(config):
    r=config['rodillos'];faltan=[]
    for clave in ('centros_radiales_m','angulos_rad','espesor_biomasa_m','fuente_montaje'):
        if r.get(clave) is None:faltan.append('rodillos.'+clave)
    if r.get('contacto_documentado') is not True and r.get('contacto_escenario_explicito') is not True:faltan.append('rodillos.contacto_documentado')
    if config['torque'].get('mu_efectivo') is None:faltan.append('torque.mu_efectivo')
    if config['presion'].get('valor_pa') is None:faltan.append('presion.valor_pa')
    return faltan


def cargas_angulares(agujeros,config,orden=None):
    faltan=requisitos_carga(config)
    if faltan:raise ValueError('Cargas pendientes: '+', '.join(faltan))
    r=config['rodillos'];op=config['operacion'];num=config['numerico']
    n=num['estados']
    if isinstance(n,bool) or not isinstance(n,int) or n<4:raise ValueError('Número de estados inválido')
    for k in ('diametro_m','ancho_m','espesor_biomasa_m'):positivo(r[k],k)
    if r['espesor_biomasa_m']>=r['diametro_m']:raise ValueError('Capa incompatible con radio de rodillo')
    if len(r['centros_radiales_m'])!=len(r['angulos_rad']) or not r['angulos_rad']:raise ValueError('Posiciones incompatibles')
    p=config['presion']['valor_pa'];mu=config['torque']['mu_efectivo']
    positivo(p,'presion');positivo(mu,'mu_efectivo')
    rpm=op.get('rpm_matriz')
    if rpm is not None:positivo(rpm,'rpm_matriz')
    xy=np.array([[a['x_mm'],a['y_mm']] for a in agujeros])/1000
    radios=np.linalg.norm(xy,axis=1);diam=np.array([a['diametro_efectivo_mm'] for a in agujeros])/1000
    if not np.isfinite(xy).all() or np.any(diam<=0):raise ValueError('Geometría inválida')
    if r.get('holguras_CAD_m') is not None:
        if len(r['holguras_CAD_m'])!=len(r['centros_radiales_m']):raise ValueError('Falta holgura de algún rodillo')
        largos=np.asarray(longitud_contacto_desde_holgura(np.array(r['holguras_CAD_m']),r['diametro_m'],r['espesor_biomasa_m']))
    else:
        largos=np.full(len(r['centros_radiales_m']),math.sqrt(r['diametro_m']*r['espesor_biomasa_m']-r['espesor_biomasa_m']**2))
    filas=[]
    for paso in range(n):
        theta=2*math.pi*paso/n;co=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
        globales=xy@co.T
        fila=dict(paso=paso,angulo_grados=360*paso/n,tiempo_s=None if rpm is None else paso/n*60/rpm,
            escenario='cobertura_EP2_desacoplada_con_STEP',fuerza_total_n=0.,torque_total_nm=0.)
        for j,(centro,angulo) in enumerate(zip(r['centros_radiales_m'],r['angulos_rad']),1):
            largo=float(largos[j-1]);fila[f'longitud_contacto_r{j}_m']=largo
            positivo(centro,'centro_radial');
            if not math.isfinite(angulo):raise ValueError('Ángulo de montaje no finito')
            if centro-r['ancho_m']/2<=0:raise ValueError('Rodillos cruzan eje; comprobar solapamiento')
            limites=(centro-r['ancho_m']/2,centro+r['ancho_m']/2,-largo/2,largo/2)
            locales=coordenadas_locales(globales,angulo)
            areas=np.zeros(len(xy));cr=np.full(len(xy),np.nan)
            for valor in np.unique(diam):
                ids=np.flatnonzero(diam==valor)
                if largo>0:aa,cc,_=interseccion_disco_rectangulo(locales[ids],valor/2,limites,orden or num['cuadratura'])
                else:aa=np.zeros(len(ids));cc=np.full(len(ids),np.nan)
                areas[ids]=aa;cr[ids]=cc
            F=p*areas;T=contribuciones_torque_nm(F,radios,mu);positiva=areas>1e-16
            suma=float(F.sum());torque=float(T.sum())
            fila[f'fuerza_r{j}_n']=suma;fila[f'torque_r{j}_nm']=torque
            fila[f'perforaciones_activas_r{j}']=int(positiva.sum())
            fila[f'perforaciones_parciales_r{j}']=int(np.sum(positiva&(areas<np.pi*diam**2/4*(1-1e-9))))
            fila[f'centroide_radial_r{j}_m']=float(np.dot(F[positiva],cr[positiva])/suma) if suma else None
            fila['fuerza_total_n']+=suma;fila['torque_total_nm']+=torque
        fila['potencia_w']=None if rpm is None else float(potencia_resistente_w(fila['torque_total_nm'],2*math.pi*rpm/60))
        filas.append(fila)
    return pd.DataFrame(filas),float(largos[0]) if np.allclose(largos,largos[0]) else largos.tolist()


def resumir(df):
    indice=int(df.fuerza_total_n.idxmax());it=int(df.torque_total_nm.idxmax())
    return dict(estados=len(df),fuerza_total_max_n=float(df.fuerza_total_n.max()),fuerza_total_media_n=float(df.fuerza_total_n.mean()),
        torque_max_nm=float(df.torque_total_nm.max()),torque_medio_nm=float(df.torque_total_nm.mean()),
        potencia_max_w=None if df.potencia_w.isna().all() else float(df.potencia_w.max()),
        potencia_media_w=None if df.potencia_w.isna().all() else float(df.potencia_w.mean()),
        caso_fuerza_max=df.iloc[indice].where(pd.notnull(df.iloc[indice]),None).to_dict(),
        caso_torque_max=df.iloc[it].where(pd.notnull(df.iloc[it]),None).to_dict(),
        fuerza_por_rodillo={c:{'max_n':float(df[c].max()),'media_n':float(df[c].mean())} for c in df if c.startswith('fuerza_r')})
