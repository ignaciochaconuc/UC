"""Modelos desacoplados del prototipo. SI: m, N, Pa, N m, W.

Todos los montajes y presiones numéricos por defecto son escenarios,
no características físicas verificadas. No ejecuta los modelos comerciales.
"""
import math
from types import SimpleNamespace
import numpy as np
import pandas as pd
from scipy.sparse.linalg import splu
from reutilizacion import (interseccion_disco_rectangulo, coordenadas_locales,
    contribuciones_torque_nm, potencia_resistente_w, SistemaViga, SegmentoEje,
    repartir_entre_rodamientos, carga_dinamica_equivalente, vida_l10_millones,
    vida_l10_horas, factor_estatico, velocidad_rodillo_rpm)


def positivo(valor,nombre):
    if isinstance(valor,bool) or not isinstance(valor,(int,float)) or not math.isfinite(valor) or valor<=0:
        raise ValueError(f'{nombre}: positivo y finito requerido')


def presion_canal(presion_previa_pa,mu_pared,nu_LR,longitud_activa_m,diametro_m):
    """Stelte et al.2011, ecuaciones1–2: PN0/nu*(exp(4*mu*nu*L/D)-1).

    nu_LR es de BIOMASA ortótropa, no Poisson del acero. mu_pared no es
    mu_eff de torque. No hay calibración disponible por defecto.
    """
    for nombre,v in [('PN0',presion_previa_pa),('mu_pared',mu_pared),('nu_LR',nu_LR),('L',longitud_activa_m),('D',diametro_m)]:
        positivo(v,nombre)
    argumento=4*mu_pared*nu_LR*longitud_activa_m/diametro_m
    if argumento>700:
        raise ValueError('Fuera de rango numérico; revisar parámetros del modelo')
    return presion_previa_pa/nu_LR*math.expm1(argumento)


def validar_parametros(p):
    for seccion,claves in [('matriz',('diametro_m','espesor_m','diametro_agujero_m','diametro_central_m')),
        ('rodillos',('diametro_m','ancho_m','centro_radial_m','espesor_biomasa_escenario_m')),
        ('eje_transversal',('diametro_nominal_m','longitud_m','diametro_nucleo_escenario_m')),
        ('motor',('potencia_mecanica_nominal_w','rpm_nominal'))]:
        for k in claves:
            positivo(p[seccion][k],seccion+'.'+k)
    n=p['numerico']['posiciones_angulares']
    if isinstance(n,bool) or not isinstance(n,int) or n<4:
        raise ValueError('Se requieren al menos4 posiciones angulares enteras')
    if p['matriz']['numero_agujeros']!=102 or p['rodillos']['numero']!=2 or p['rodamientos']['cantidad']!=4:
        raise ValueError('Esta configuración exige102 agujeros,2 rodillos y4 rodamientos')
    if not 0<p['patron']['factor_coordenadas']<=1:
        raise ValueError('Escala geométrica explícita entre0 y1')
    r=p['rodillos'];m=p['matriz'];e=p['eje_transversal'];b=p['rodamientos']
    if not 0<r['espesor_biomasa_escenario_m']<r['diametro_m']:
        raise ValueError('Espesor de biomasa fuera de dominio de contacto')
    if r['centro_radial_m']-r['ancho_m']/2 <= m['diametro_central_m']/2 or r['centro_radial_m']+r['ancho_m']/2>m['diametro_m']/2:
        raise ValueError('Huella radial fuera del anillo de matriz')
    if e['diametro_nucleo_escenario_m']>e['diametro_nominal_m'] or 2*b['ancho_m']>r['ancho_m']:
        raise ValueError('Núcleo o montaje de rodamientos imposible')
    for seccion,key in [('presion','factores_sensibilidad'),('motor','reducciones_sensibilidad'),
        ('motor','eficiencias_mecanicas_sensibilidad'),('resistencia_tangencial','mu_escenarios'),
        ('eje_transversal','E_escenarios_pa'),('eje_transversal','Sy_escenarios_pa')]:
        if not p[seccion][key]:
            raise ValueError('Sensibilidad vacía')
        for v in p[seccion][key]:
            positivo(v,key)
    if any(v>1 for v in p['motor']['eficiencias_mecanicas_sensibilidad']):
        raise ValueError('Eficiencia mecánica fuera de0..1')
    return True


def reconstruir_patron(p,ruta):
    df=pd.read_csv(ruta)
    if len(df)!=p['matriz']['numero_agujeros'] or not df['id'].is_unique:
        raise ValueError('Cantidad/ID de agujeros incompatible')
    xy=df[['x_mm','y_mm']].to_numpy(dtype=float)*p['patron']['factor_coordenadas']/1000
    if not np.isfinite(xy).all():
        raise ValueError('Coordenadas no finitas')
    m=p['matriz'];rh=m['diametro_agujero_m']/2
    dist=np.linalg.norm(xy[:,None,:]-xy[None,:,:],axis=2)
    np.fill_diagonal(dist,np.inf)
    gap=float(dist.min()-2*rh)
    borde=float((m['diametro_m']/2-np.linalg.norm(xy,axis=1)-rh).min())
    bore=float((np.linalg.norm(xy,axis=1)-rh-m['diametro_central_m']/2).min())
    if min(gap,borde,bore)<=0:
        raise ValueError('Patrón escalado produce intersección de perforaciones o bordes')
    salida=pd.DataFrame({'id':df['id'],'x_mm':xy[:,0]*1000,'y_mm':xy[:,1]*1000,
        'origen':'centros comerciales escalados por indicación equipo, no medidos',
        'factor_coordenadas':p['patron']['factor_coordenadas']})
    return xy,salida,{'ligamento_min_agujeros_mm':gap*1000,'ligamento_min_borde_exterior_mm':borde*1000,
        'ligamento_min_bore_mm':bore*1000,'L_sobre_D':m['espesor_m']/m['diametro_agujero_m'],
        'holgura_diametral_bore_arbol_mm':1000*(m['diametro_central_m']-p['arbol_principal']['diametro_nominal_m']),
        'sin_aprobacion_resistente':True}


def contacto_angular(p,xy,orden=None):
    r=p['rodillos'];m=p['matriz'];n=p['numerico']['posiciones_angulares']
    longitud=math.sqrt(r['diametro_m']*r['espesor_biomasa_escenario_m']-r['espesor_biomasa_escenario_m']**2)
    limites=(r['centro_radial_m']-r['ancho_m']/2,r['centro_radial_m']+r['ancho_m']/2,-longitud/2,longitud/2)
    radios=np.linalg.norm(xy,axis=1);rh=m['diametro_agujero_m']/2
    area_disco=math.pi*rh**2
    filas=[];detalles=[]
    for paso in range(n):
        theta=paso*2*math.pi/n
        rot=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
        globales=xy@rot.T
        fila={'paso':paso,'angulo_grados':360*paso/n,'escenario':'geometria_escalada_desacoplada'}
        for j,ang in enumerate((0,math.pi),1):
            locales=coordenadas_locales(globales,ang)
            areas,cr,ct=interseccion_disco_rectangulo(locales,rh,limites,orden or p['numerico']['cuadratura'])
            positiva=areas>area_disco*1e-12
            suma=float(areas.sum())
            fila[f'area_r{j}_m2']=suma
            fila[f'centroide_radial_r{j}_m']=float(np.dot(areas[positiva],cr[positiva])/suma) if suma else math.nan
            fila[f'torque_por_presion_y_mu_r{j}_m3']=float(contribuciones_torque_nm(areas,radios,1).sum())
            fila[f'perforaciones_activas_r{j}']=int(positiva.sum())
            fila[f'perforaciones_parciales_r{j}']=int(np.sum(positiva&(areas<area_disco*(1-1e-9))))
            for k in np.flatnonzero(positiva):
                detalles.append(dict(paso=paso,angulo_grados=360*paso/n,rodillo=j,id_agujero=k+1,
                    area_superpuesta_m2=areas[k],fraccion=areas[k]/area_disco,
                    centroide_radial_m=cr[k],centroide_tangencial_m=ct[k]))
        fila['area_total_m2']=fila['area_r1_m2']+fila['area_r2_m2']
        filas.append(fila)
    return pd.DataFrame(filas),pd.DataFrame(detalles),longitud


def cargas(p,geometria,presion,mu):
    positivo(presion,'presion');positivo(mu,'mu')
    d=geometria.copy()
    d['presion_escenario_pa']=presion;d['mu_escenario']=mu
    for j in (1,2):
        d[f'fuerza_r{j}_n']=presion*d[f'area_r{j}_m2']
        d[f'torque_r{j}_nm']=presion*mu*d[f'torque_por_presion_y_mu_r{j}_m3']
    d['fuerza_total_n']=d['fuerza_r1_n']+d['fuerza_r2_n']
    d['torque_total_nm']=d['torque_r1_nm']+d['torque_r2_nm']
    d['escenario']='p_y_mu_no_validados_geometria_escalada'
    return d


def posiciones_rodamientos(p):
    r=p['rodillos'];b=p['rodamientos'];L=p['eje_transversal']['longitud_m']
    offset=(r['ancho_m']-b['ancho_m'])/2
    centros=[L/2-r['centro_radial_m'],L/2+r['centro_radial_m']]
    posiciones=np.array([centros[0]-offset,centros[0]+offset,centros[1]-offset,centros[1]+offset])
    if np.any(posiciones<=0) or np.any(posiciones>=L):
        raise ValueError('Montaje supuesto no cabe en eje')
    return posiciones


def repartir_cargas(p,d):
    pos=posiciones_rodamientos(p);L=p['eje_transversal']['longitud_m']
    resultado=[]
    for j,sgn in ((1,-1),(2,1)):
        reparto=repartir_entre_rodamientos(d[f'fuerza_r{j}_n'].to_numpy(),
            L/2+sgn*d[f'centroide_radial_r{j}_m'].to_numpy(),*pos[2*(j-1):2*j])
        if reparto.fuera_entre_rodamientos.any():
            raise ValueError('Resultante sale de apoyos supuestos: no aprobar reparto')
        resultado.extend([reparto.reaccion_a_n,reparto.reaccion_b_n])
    return np.array(resultado)


class VigaEscenario(SistemaViga):
    def __init__(self,nodos,L,diametro,E,tipo):
        config=SimpleNamespace(segmentos=(SegmentoEje('M6_nucleo_equivalente_escenario',0,L,diametro),),modulo_young_pa=E)
        super().__init__(nodos,config)
        if tipo=='biapoyado':
            self.restringidos=np.array([0,self.numero_gdl-2])
            self.libres=np.setdiff1d(np.arange(self.numero_gdl),self.restringidos)
            self._factor=splu(self.K[self.libres][:,self.libres].tocsc())
        elif tipo!='biempotrado':
            raise ValueError('Apoyo desconocido')


def eje_transversal(p,d,tipo,paso=None):
    e=p['eje_transversal'];L=e['longitud_m'];diam=e['diametro_nucleo_escenario_m']
    pos=posiciones_rodamientos(p);f=repartir_cargas(p,d)
    nodos=np.unique(np.r_[np.linspace(0,L,math.ceil(L/(paso or p['numerico']['paso_viga_m']))+1),pos])
    viga=VigaEscenario(nodos,L,diam,e['E_referencia_escenario_pa'],tipo)
    vertical=viga.cargas_vacias(len(d));horizontal=vertical.copy()
    for i,x in enumerate(pos):
        viga.agregar_carga_puntual(vertical,float(x),-f[i])
        # Ramas tangenciales opuestas para rodillos opuestos; misma convención histórica.
        viga.agregar_carga_puntual(horizontal,float(x),f[i]*d['mu_escenario'].to_numpy()*(1 if i<2 else -1))
    sv=viga.resolver(vertical);sh=viga.resolver(horizontal)
    ev=viga.fuerzas_extremo_elementos(sv.desplazamientos);eh=viga.fuerzas_extremo_elementos(sh.desplazamientos)
    M=np.hypot(np.stack((-ev[:,1],ev[:,3]),axis=1),np.stack((-eh[:,1],eh[:,3]),axis=1))
    sigma=(M*diam/2/viga.inercias[:,None,None]).max(axis=(0,1))
    u=np.hypot(sv.desplazamientos[0::2],sh.desplazamientos[0::2]).max(axis=0)
    residuo=np.abs(sv.reacciones[0]+sv.reacciones[-2]-d['fuerza_total_n'].to_numpy()).max()
    salida=pd.DataFrame({'paso':d['paso'],'angulo_grados':d['angulo_grados'],'apoyo_escenario':tipo,
        'sigma_flexion_nominal_pa':sigma,'desplazamiento_lineal_max_m':u,
        'reaccion_vertical_izquierda_n':sv.reacciones[0],'reaccion_vertical_derecha_n':sv.reacciones[-2],
        'gran_desplazamiento_alerta':u/L>.02})
    return salida,{'apoyo':tipo,'sigma_nominal_max_pa':float(sigma.max()),'desplazamiento_max_m':float(u.max()),
        'u_sobre_L':float(u.max()/L),'equilibrio_vertical_error_n':float(residuo),
        'u_sobre_espesor_biomasa_escenario':float(u.max()/p['rodillos']['espesor_biomasa_escenario_m']),
        'contacto_rigido_desacoplado_por_revisar':bool(u.max()>0.1*p['rodillos']['espesor_biomasa_escenario_m']),
        'fuera_regimen_pequena_deformacion':bool((u/L>.02).any()),
        'modelo':'Viga lineal equivalente; sin entalla real, peso, precarga, flexibilidad de carcasa o adaptador; no seguridad aprobada'}


def vida_referencia(p,d):
    radiales=repartir_cargas(p,d)*math.hypot(1,p['resistencia_tangencial']['mu_referencia_escenario'])
    b=p['rodamientos'];filas=[]
    for i,f in enumerate(radiales):
        Peq=carga_dinamica_equivalente(f);L10=vida_l10_millones(b['capacidad_dinamica_referencia_n'],Peq)
        for reduccion in p['motor']['reducciones_sensibilidad']:
            rpm=velocidad_rodillo_rpm(p['motor']['rpm_nominal']/reduccion,p['rodillos']['centro_radial_m'],p['rodillos']['diametro_m']/2)
            filas.append(dict(rodamiento=i+1,referencia=b['referencia_comparacion'],Peq_n=Peq,Fr_max_n=float(f.max()),
                S0_referencia=factor_estatico(b['capacidad_estatica_referencia_n'],float(f.max())),
                reduccion_hipotetica=reduccion,rpm_rodillo_hipotetica=rpm,L10_millones_ref=L10,L10h_ref=vida_l10_horas(L10,rpm),
                estado='solo referencia EZO,Fa0 supuesto,adaptador y fabricante comprado pendientes'))
    return pd.DataFrame(filas)


def balance_potencia(p,geometria):
    filas=[];motor=p['motor']
    for factor in p['presion']['factores_sensibilidad']:
        presion=p['presion']['referencia_equipo_pa']*factor
        for mu in p['resistencia_tangencial']['mu_escenarios']:
            d=cargas(p,geometria,presion,mu);Tmax=float(d['torque_total_nm'].max());Tmedia=float(d['torque_total_nm'].mean())
            for i in motor['reducciones_sensibilidad']:
                rpm=motor['rpm_nominal']/i;omega=2*math.pi*rpm/60
                for eta in motor['eficiencias_mecanicas_sensibilidad']:
                    disp=motor['potencia_mecanica_nominal_w']*eta;Pmax=float(potencia_resistente_w(Tmax,omega))
                    filas.append(dict(presion_pa=presion,mu_escenario=mu,reduccion_hipotetica=i,rpm_matriz_hipotetica=rpm,
                        eficiencia_mecanica_hipotetica=eta,torque_max_nm=Tmax,potencia_max_w=Pmax,
                        potencia_media_w=float(potencia_resistente_w(Tmedia,omega)),potencia_disponible_w=disp,
                        margen_potencia_max_w=disp-Pmax,cubre_maximo_en_escenario=bool(disp>=Pmax),
                        reduccion_minima_cubrir_maximo_ideal=Tmax*2*math.pi*motor['rpm_nominal']/(60*disp),
                        nota='no selección ni arranque comprobado; presión,mu,pérdidas y velocidad no validados'))
    return pd.DataFrame(filas)


def demanda_arbol(p,d):
    filas=[];arbol=p['arbol_principal']
    for factor in arbol['factores_diametro_nucleo_sensibilidad']:
        diam=arbol['diametro_nominal_m']*factor
        A=math.pi*diam**2/4
        sigma=d['fuerza_total_n'].to_numpy()/A
        tau=16*d['torque_total_nm'].to_numpy()/(math.pi*diam**3)
        vm=np.sqrt(sigma**2+3*tau**2)
        k=int(np.argmax(vm))
        filas.append(dict(factor_diametro_hipotetico=factor,diametro_equivalente_hipotetico_m=diam,
            sigma_axial_max_pa=float(sigma.max()),tau_torsion_max_pa=float(tau.max()),
            vm_axial_torsion_max_pa=float(vm[k]),paso_vm_max=int(d.iloc[k]['paso']),
            fuerza_correlacionada_n=float(d.iloc[k]['fuerza_total_n']),torque_correlacionado_nm=float(d.iloc[k]['torque_total_nm']),
            estado='demanda_si_transmite_total;sección circular hipotética,excluye flexión,entallas,tuercas y apoyos;sinFS'))
    return pd.DataFrame(filas)
