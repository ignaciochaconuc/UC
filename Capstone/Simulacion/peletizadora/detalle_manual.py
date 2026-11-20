"""Verificaciones de detalle: reutiliza EP2 y consume estados CAD conservados.

No ejecuta scripts históricos con efectos secundarios ni inventa apoyos reales.
"""
import math
import numpy as np
import pandas as pd
from .nucleo import positivo
from .verificaciones import presion_canal,resolver_viga,vida_bolas
from .legado import repartir_entre_rodamientos


def agua_base_humeda(m0,w0,wf):
    positivo(m0,'masa inicial')
    if not all(isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) for x in (w0,wf)) or not 0<=w0<=wf<1:
        raise ValueError('Humedades en fracción base húmeda: 0 <= inicial <= final < 1')
    return m0*(wf-w0)/(1-wf)


def fuerza_manual(torque,radio):
    positivo(radio,'radio efectivo')
    t=np.asarray(torque,dtype=float)
    if not np.isfinite(t).all() or np.any(t<0):raise ValueError('Torque resistente no negativo y finito')
    return t/radio


def radio_manivela_CAD(analisis):
    eje=analisis['arbol_principal']['cilindros'][0]
    origen=np.array(eje['centro_eje_mm']);u=np.array(eje['eje'])
    manivela=next(p for p in analisis['inventario'] if p['clasificacion']=='brazo_manivela')
    paralelos=[c for c in manivela['cilindros'] if abs(np.dot(c['eje'],u))>1-1e-6]
    distancias=[np.linalg.norm((np.array(c['centro_eje_mm'])-origen)-np.dot(np.array(c['centro_eje_mm'])-origen,u)*u) for c in paralelos]
    lejano=int(np.argmax(distancias))
    return dict(radio_ejes_mm=float(distancias[lejano]),centro_eje_empunadura_CAD_mm=paralelos[lejano]['centro_eje_mm'],
        solido_id=manivela['id'],metodo='Distancia perpendicular entre eje principal y eje cilíndrico paralelo de empuñadura; no longitud de bbox',
        limitacion='Radio entre ejes, no posición real de la mano ni dirección aplicada')


def presiones(config,dim):
    h=config['Holm'];L=dim['longitudes_cilindricas_restrictivas_mm'][0]/1000
    D=dim['diametros_efectivos_mm'][0]/1000
    p=presion_canal(h['PN0_pa'],h['mu_pared'],h['nu_LR'],L,D)
    literal=presion_canal(h['PN0_pa'],h['mu_pared'],h['nu_LR'],h['L_D_documento_redondeado']*D,D)
    comercial=presion_canal(h['PN0_pa'],h['mu_pared'],h['nu_LR'],6*D,D)
    return dict(P_CAD_pa=p,P_literal_transcripcion_pa=literal,L_activa_m=L,D_canal_m=D,L_D=L/D,
        lambda_p_CAD=p/h['P_comercial_documento_pa'],lambda_p_literal=literal/h['P_comercial_documento_pa'],
        diferencia_44_vs_43_70_pa=44e6-h['P_comercial_documento_pa'],
        P_comercial_L_D6_pa=comercial,diferencia_44_vs_Holm6_relativa=44e6/comercial-1,
        origen_43_70='Entrega_2.pdf PDFp14 A.2.2 ec4, evaluada sin redondear43,70433MPa;43,70 redondeo2decimales y44 redondeo a MPa entero',
        estado='Estimación de diseño documentada para coeficientes de rastrojo de maíz20%; extrapolación a aserrín12–15% no calibrada')


def reparto_CAD(df,analisis,mu):
    """Reparto EP2, con ejes globales: normal +Y y tangente -lado*Z.

    Los centroides radiales disponibles se proyectan sobre X; se omite
    desplazamiento tangencial del centroide y pesos no identificados.
    """
    b=analisis['rodamientos'];Ti=np.array(analisis['correspondencia_matriz']['local_matriz_a_ensamble'])
    tabla=df[['paso','angulo_grados']].copy();errores_f=[];errores_m=[]
    for j,rod in enumerate(analisis['rodillos'],1):
        par=sorted(sorted(b,key=lambda x:np.linalg.norm(np.array(x['centro_CAD_mm'])-rod['centro_CAD_mm']))[:2],key=lambda x:x['centro_CAD_mm'][0])
        xa,xb=[x['centro_CAD_mm'][0]/1000 for x in par]
        r=df[f'centroide_radial_r{j}_m'].to_numpy();a=rod['angulo_rad']
        xf=Ti[0,0]*r*np.cos(a)+Ti[0,1]*r*np.sin(a)+Ti[0,3]/1000
        rep=repartir_entre_rodamientos(df[f'fuerza_r{j}_n'].to_numpy(),xf,xa,xb)
        signo=-np.sign(rod['centro_CAD_mm'][0]-Ti[0,3])
        for bearing,F in zip(par,(rep.reaccion_a_n,rep.reaccion_b_n)):
            n=bearing['solido_id'];tabla[f'Y_b{n}_n']=F;tabla[f'Z_b{n}_n']=signo*mu*F
        errores_f.append(float(np.max(abs(rep.reaccion_a_n+rep.reaccion_b_n-df[f'fuerza_r{j}_n']))))
        errores_m.append(float(np.max(abs(rep.reaccion_a_n*xa+rep.reaccion_b_n*xb-df[f'fuerza_r{j}_n']*xf))))
    return tabla,dict(error_fuerzas_n=max(errores_f),error_momentos_nm=max(errores_m))


def viga_detalle(tabla,analisis,diametro,E,divisiones=80):
    for nombre,v in [('diámetro',diametro),('E',E)]:positivo(v,nombre)
    if not isinstance(divisiones,int) or divisiones<4:raise ValueError('Resolución de viga inválida')
    eje=analisis['eje_transversal'];x0=eje['bbox_mm'][0]/1000;L=eje['cilindros'][0]['largo_mm']/1000
    apoyos=[t['centro_eje_mm'][0]/1000-x0 for t in analisis['taladros_soporte_transversal']]
    posiciones={b['solido_id']:b['centro_CAD_mm'][0]/1000-x0 for b in analisis['rodamientos']}
    claves=np.unique(np.r_[0,L,apoyos,list(posiciones.values())])
    # Subdividir entre puntos físicos evita elementos casi nulos al
    # superponer una malla uniforme y centrosCAD próximos a sus nodos.
    nodos=np.unique(np.round(np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/(L/divisiones)))+1) for a,b in zip(claves[:-1],claves[1:])]),12))
    indice=lambda x:int(np.argmin(abs(nodos-x)))
    fy=np.zeros((2*len(nodos),len(tabla)));fz=fy.copy()
    for n,x in posiciones.items():fy[2*indice(x)]+=tabla[f'Y_b{n}_n'];fz[2*indice(x)]+=tabla[f'Z_b{n}_n']
    segmentos=[dict(nombre='seccion_uniforme_condicionada',x_inicio_m=0,x_fin_m=L,diametro_exterior_m=diametro)]
    restringidos=[2*indice(x) for x in apoyos]
    sy,y=resolver_viga(nodos,segmentos,E,fy,restringidos,'Hipótesis articulada rígida en centros de taladrosCAD, no validación de carcasa impresa')
    _,z=resolver_viga(nodos,segmentos,E,fz,restringidos,'Misma hipótesis en plano Z')
    ey=sy.fuerzas_extremo_elementos(y.desplazamientos);ez=sy.fuerzas_extremo_elementos(z.desplazamientos)
    M=np.hypot(ey[:,[1,3]],ez[:,[1,3]]).max(axis=(0,1))
    V=np.hypot(ey[:,[0,2]],ez[:,[0,2]]).max(axis=(0,1))
    sigma=32*M/(math.pi*diametro**3);tau=16*V/(3*math.pi*diametro**2)
    # Los máximos de flexión superficial y corte central NO son co-localizados.
    # Se guardan separados; no fabricar von Mises como si lo fueran.
    flecha=np.hypot(y.desplazamientos[::2],z.desplazamientos[::2]).max(axis=0)
    serie=tabla[['paso','angulo_grados']].copy()
    serie['M_flexion_resultante_max_nm']=M;serie['V_resultante_max_n']=V
    serie['sigma_flexion_nominal_max_pa']=sigma;serie['tau_corte_nominal_max_pa']=tau
    serie['flecha_resultante_max_m']=flecha
    desplazamiento_contacto=[]
    for j,rod in enumerate(analisis['rodillos'],1):
        par=sorted(sorted(analisis['rodamientos'],key=lambda b:np.linalg.norm(np.array(b['centro_CAD_mm'])-rod['centro_CAD_mm']))[:2],key=lambda b:b['centro_CAD_mm'][0])
        xa,xb=[posiciones[b['solido_id']] for b in par]
        ua=y.desplazamientos[2*indice(xa)];ub=y.desplazamientos[2*indice(xb)]
        xc=rod['centro_CAD_mm'][0]/1000-x0
        uc=ua+(ub-ua)*(xc-xa)/(xb-xa)
        pendiente=(ub-ua)/(xb-xa)
        bordes=np.array([uc-pendiente*rod['ancho_mm']/2000,uc+pendiente*rod['ancho_mm']/2000])
        serie[f'cambio_holgura_centro_r{j}_m']=uc
        serie[f'cambio_holgura_borde_min_r{j}_m']=bordes.min(axis=0)
        serie[f'cambio_holgura_borde_max_r{j}_m']=bordes.max(axis=0)
        desplazamiento_contacto.append(float(np.max(abs(bordes))))
    balances=[]
    for i,a in enumerate(apoyos):
        Ry=y.reacciones[2*indice(a)];Rz=z.reacciones[2*indice(a)]
        serie[f'R_Y_apoyo{i+1}_n']=Ry;serie[f'R_Z_apoyo{i+1}_n']=Rz
    for u,cargas in ((y,fy),(z,fz)):
        rr=np.zeros_like(u.reacciones)
        rr[restringidos]=u.reacciones[restringidos]
        balances.extend([float(np.max(abs(rr[::2].sum(axis=0)+cargas[::2].sum(axis=0)))),
            float(np.max(abs(np.array(nodos)@(rr[::2]+cargas[::2]))))])
    gap=min(r['separacion_envolvente_matriz_mm'] for r in analisis['rodillos'])/1000
    sal=dict(diametro_resistente_hipotetico_m=diametro,E_hipotetico_pa=E,divisiones=divisiones,
        sigma_flexion_nominal_max_pa=float(sigma.max()),tau_corte_nominal_max_pa=float(tau.max()),
        Sy_min_flexion_n1_pa=float(sigma.max()),Sy_min_corte_VM_n1_pa=float(math.sqrt(3)*tau.max()),
        flecha_resultante_max_m=float(flecha.max()),flecha_sobre_holgura_CAD=float(flecha.max()/gap),
        E_necesario_para_flecha_igual_holgura_pa=float(E*flecha.max()/gap),
        cambio_holgura_contacto_max_m=max(desplazamiento_contacto),cambio_holgura_sobre_gap_CAD=max(desplazamiento_contacto)/gap,
        equilibrio_error_fuerzas_n=max(balances[::2]),equilibrio_error_momentos_nm=max(balances[1::2]),factor_seguridad_aprobado=None,
        nota='Sin entallas, peso, plasticidad o rigidezABS; Sy requerido n=1 es umbral nominal, no selección ni FS')
    # Ciclos firmados en fibras fijas de un eje NO giratorio. No emplear
    # la envolvente positiva de M como si fuera un ciclo de esfuerzo real.
    candidatos=[]
    for psi in np.linspace(0,2*math.pi,16,endpoint=False):
        fibra=32*(ey[:,[1,3]]*math.cos(psi)+ez[:,[1,3]]*math.sin(psi))/(math.pi*diametro**3)
        alto=fibra.max(axis=2);bajo=fibra.min(axis=2);amplitud=(alto-bajo)/2;media=(alto+bajo)/2
        ix=np.unravel_index(np.argmax(amplitud),amplitud.shape)
        candidatos.append((float(amplitud[ix]),float(media[ix]),float(psi),int(ix[0]),int(ix[1])))
    amp,media,psi,elemento,extremo=max(candidatos)
    sal.update(sigma_alternante_nominal_fibra_pa=amp,sigma_media_misma_fibra_pa=media,
        angulo_fibra_rad=psi,elemento_fibra=elemento,extremo_fibra=extremo,
        fatiga='Solo rango de extremos de una vuelta en fibra fija de mayor amplitud entre16direcciones; no conteo rainflow ni daño. Faltan Sut,Se,Kt,Kf,acabado y régimen; no FS de fatiga.')
    return serie,sal


def seccion_arbol(F,T,d):
    """Ecuaciones nominales de4B extraídas a función pura; no importar su runner."""
    positivo(d,'diámetro resistente')
    F=np.asarray(F,dtype=float);T=np.asarray(T,dtype=float)
    if F.shape!=T.shape or not np.isfinite(F).all() or not np.isfinite(T).all():raise ValueError('Estados F/T no correlacionados')
    sigma=4*F/(math.pi*d*d);tau=16*T/(math.pi*d**3)
    return sigma,tau,np.sqrt(sigma**2+3*tau**2)


def referencia_608(tabla,analisis,config):
    """Capacidad nominal de referencia: no representa el rodamiento comprado."""
    c=config['rodamientos_referencia'];filas=[]
    for b in analisis['rodamientos']:
        n=b['solido_id'];P=np.hypot(tabla[f'Y_b{n}_n'],tabla[f'Z_b{n}_n'])
        rod=min(analisis['rodillos'],key=lambda x:np.linalg.norm(np.array(x['centro_CAD_mm'])-b['centro_CAD_mm']))
        for rpm_matriz in c['rpm_matriz_sensibilidad']:
            rpm=rpm_matriz*rod['radio_posicion_mm']/(rod['diametro_mm']/2)
            vida=vida_bolas(P,c['C_n'],c['C0_n'],rpm,c['Fa_n_hipotetica'],c['fuente'])
            filas.append(dict(rodamiento_id=n,rpm_matriz_hipotetica=rpm_matriz,rpm_rodillo_hipotetica=rpm,
                carga_max_n=float(P.max()),**vida,estado='Referencia EZO, Fa=0 hipotética, pesos angulares uniformes, rodadura ideal; asientos no resueltos'))
    return filas


def contactos_CAD(path):
    from .ensamble import leer_ensamble
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    hojas,meta=leer_ensamble(path);solidos={i['id']:s for s,i in hojas};filas=[]
    for a,b in ((8,14),(8,15),(14,13),(15,16),(8,12),(8,2),(8,7),(8,37),(12,20)):
        medida=BRepExtrema_DistShapeShape(solidos[a],solidos[b]);medida.Perform()
        if not medida.IsDone():raise ValueError('DistanciaCAD no resuelta')
        filas.append(dict(solido_a=a,solido_b=b,distancia_minima_mm=medida.Value(),sha256_STEP=meta['sha256'],
            interpretacion='Distancia geométrica mínima; cero puede ser punto/arista/cara o intersección. No prueba área resistente, apriete ni fuerza.'))
    return filas
