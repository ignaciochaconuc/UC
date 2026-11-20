"""Escenarios explícitos usando el núcleo compartido y montaje CAD.

Ningún espesor de capa, coeficiente o rpm de esta sensibilidad se presenta
como parámetro operativo medido. No calcula vida con asientos incompatibles.
"""
import copy
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon
from .nucleo import cargas_angulares,resumir
from .legado import repartir_entre_rodamientos
from .verificaciones import resolver_viga,balance_potencia
from .informes import guardar_json


def incorporar_montaje(config,analisis):
    cfg=copy.deepcopy(config);r=cfg['rodillos'];rods=analisis['rodillos']
    if len(rods)!=2:raise ValueError('Se requieren dos rodillos identificados')
    if any(not math.isfinite(x['separacion_envolvente_matriz_mm']) or x['separacion_envolvente_matriz_mm']<0 for x in rods):
        raise ValueError('Separación CAD negativa o no finita: resolver interferencia antes de simular')
    if not all(x['eje_radial_compatible'] for x in rods):raise ValueError('Huella radialEP2 no aplicable a ejesCAD no radiales')
    if len(set(round(x['diametro_mm'],6) for x in rods))!=1 or len(set(round(x['ancho_mm'],6) for x in rods))!=1:
        raise ValueError('Rodillos diferentes requieren geometrías individuales explícitas')
    r.update(diametro_m=rods[0]['diametro_mm']/1000,ancho_m=rods[0]['ancho_mm']/1000,
        centros_radiales_m=[x['radio_posicion_mm']/1000 for x in rods],angulos_rad=[x['angulo_rad'] for x in rods],
        holguras_CAD_m=[float(x['separacion_envolvente_matriz_mm'])/1000 for x in rods],
        fuente_montaje={'archivo':analisis['meta']['archivo'],'sha256':analisis['meta']['sha256'],
            'solidos_rodillos':[x['solido_id'] for x in rods],'marco':'local de Matriz_prototipo.stp; transformación verificada en correspondencia_matriz'},
        geometria_montaje_verificada=True,contacto_documentado=False)
    cfg['componentes']['eje_transversal']['longitud_CAD_m']=analisis['eje_transversal']['cilindros'][0]['largo_mm']/1000
    cfg['ensamble_auditado']={'sha256':analisis['meta']['sha256'],'numero_solidos':analisis['meta']['numero_solidos'],
        'matriz_coincide':analisis['correspondencia_matriz']['coincide']}
    return cfg


def flexion_condicional(config,analisis,df,mu):
    e=config['sensibilidades_ensamble']['eje_M6'];E=e['E_referencia_escenario_pa'];d=e['nucleo_M6x1_escenario_m']
    eje=analisis['eje_transversal'];cil=eje['cilindros'][0]
    # Este ensamble tiene eje paralelo aXCAD. No generalizar una proyección
    # escalar si cambia la orientación del eje en una futura revisión.
    if abs(cil['eje'][0])<1-1e-6:raise ValueError('Eje no paralelo aXCAD; adaptar transformación de viga')
    x0=eje['bbox_mm'][0]/1000;L=cil['largo_mm']/1000
    apoyos=np.array(sorted(t['centro_eje_mm'][0]/1000-x0 for t in analisis['taladros_soporte_transversal']))
    if len(apoyos)!=2:raise ValueError('No se reconocieron dos taladros de soporte transversal')
    bearings=analisis['rodamientos'];pos=np.array(sorted(b['centro_CAD_mm'][0]/1000-x0 for b in bearings))
    nodos=np.unique(np.r_[np.linspace(0,L,81),apoyos,pos]);n=len(df)
    vertical=np.zeros((2*len(nodos),n));tangencial=vertical.copy()
    Tinv=np.array(analisis['correspondencia_matriz']['local_matriz_a_ensamble'])
    for j,rod in enumerate(analisis['rodillos'],1):
        cercanos=sorted(bearings,key=lambda b:np.linalg.norm(np.array(b['centro_CAD_mm'])-rod['centro_CAD_mm']))[:2]
        x_a,x_b=sorted(b['centro_CAD_mm'][0]/1000-x0 for b in cercanos)
        theta=rod['angulo_rad'];rad=df[f'centroide_radial_r{j}_m'].to_numpy()
        # Centroide radial al eje de viga; se conserva momento en cada par.
        xf=(Tinv[0,0]*rad*np.cos(theta)+Tinv[0,1]*rad*np.sin(theta)+Tinv[0,3]/1000)-x0
        reparto=repartir_entre_rodamientos(df[f'fuerza_r{j}_n'].to_numpy(),xf,x_a,x_b)
        for x,F in ((x_a,reparto.reaccion_a_n),(x_b,reparto.reaccion_b_n)):
            indice=int(np.argmin(abs(nodos-x)));vertical[2*indice]+=F
            lado=np.sign(rod['centro_CAD_mm'][0]-Tinv[0,3]);tangencial[2*indice]+=-lado*mu*F
    segmentos=[dict(nombre='nucleo_M6_hipotetico',x_inicio_m=0,x_fin_m=L,diametro_exterior_m=d)]
    restricciones=[2*int(np.argmin(abs(nodos-x))) for x in apoyos]
    sistema,sv=resolver_viga(nodos,segmentos,E,vertical,restricciones,'Escenario: taladrosCAD tratados como apoyos puntuales rígidos;NO rigidezPLAverificada')
    _,sh=resolver_viga(nodos,segmentos,E,tangencial,restricciones,'Mismo escenario, plano tangencial')
    ev=sistema.fuerzas_extremo_elementos(sv.desplazamientos);eh=sistema.fuerzas_extremo_elementos(sh.desplazamientos)
    M=np.hypot(ev[:,[1,3]],eh[:,[1,3]])
    sigma=(M*d/2/sistema.inercias[:,None,None]).max(axis=(0,1))
    u=np.hypot(sv.desplazamientos[0::2],sh.desplazamientos[0::2]).max(axis=0)
    error=float(np.max(abs(sv.reacciones.sum(axis=0)+vertical.sum(axis=0))))
    return {'sigma_nominal_max_pa':float(sigma.max()),'flecha_lineal_max_m':float(u.max()),
        'error_equilibrio_n':error,'apoyos_desde_extremo_eje_m':apoyos.tolist(),
        'luz_entre_taladros_m':float(np.diff(apoyos)[0]),'largo_CAD_m':L,'E_hipotetico_pa':E,
        'diametro_nucleo_hipotetico_m':d,'admisible_o_FS':None,
        'limitacion':'Viga lineal desacoplada, apoyos rígidos hipotéticos en centros de taladros; no montaje verificado. Sin peso,entallas,precarga,plasticidad ni rigidezPLA.'}


def ejecutar_escenarios(config,agujeros,analisis,salida):
    from .nucleo import positivo
    s=config['sensibilidades_ensamble']
    for campo in ('capas_biomasa_m','factores_presion','mu_efectivo','rpm_matriz_parametricas','eficiencia_mecanica'):
        if not s[campo]:raise ValueError('Sensibilidad vacía: '+campo)
        for valor in s[campo]:positivo(valor,campo)
    if any(v>1 for v in s['eficiencia_mecanica']):raise ValueError('Eficiencia mecánica superior a uno')
    p0=config['presion']['valor_pa'];s=config['sensibilidades_ensamble'];mu0=s['mu_referencia_escenario']
    series=[];resumen=[];potencias=[];estructuras=[];geometrias=[];bases=[]
    for h in s['capas_biomasa_m']:
        cfg=copy.deepcopy(config);cfg['rodillos'].update(espesor_biomasa_m=h,contacto_escenario_explicito=True)
        cfg['torque']['mu_efectivo']=mu0
        base,lc=cargas_angulares(agujeros,cfg);bases.append((h,base))
        fina,_=cargas_angulares(agujeros,cfg,cfg['numerico']['cuadratura_contraste'])
        error=float(np.max(abs(fina.fuerza_total_n-base.fuerza_total_n))/max(float(fina.fuerza_total_n.max()),1e-20))
        geometrias.append(dict(capa_hipotetica_m=h,longitud_contacto_m=lc,cuadratura_error_relativo_max=error,
            origen_capa='malla de sensibilidad explícita;NO espesor medido ni separaciónCAD',holguras_CAD_m=cfg['rodillos']['holguras_CAD_m']))
        for factor_p in s['factores_presion']:
            for mu in s['mu_efectivo']:
                d=base.copy();ident=f'h{h:g}_p{p0*factor_p:g}_mu{mu:g}'
                for col in d:
                    if col.startswith('fuerza_'):d[col]*=factor_p
                    if col.startswith('torque_'):d[col]*=factor_p*mu/mu0
                d['escenario']=ident;d['capa_biomasa_hipotetica_m']=h;d['presion_condicionada_pa']=p0*factor_p;d['mu_efectivo_hipotetico']=mu
                series.append(d)
                rr=resumir(d);resumen.append(dict(escenario=ident,capa_hipotetica_m=h,presion_hipotetica_pa=p0*factor_p,mu_hipotetico=mu,
                    fuerza_max_n=rr['fuerza_total_max_n'],fuerza_media_n=rr['fuerza_total_media_n'],torque_max_nm=rr['torque_max_nm'],
                    torque_medio_nm=rr['torque_medio_nm'],fuerza_r1_max_n=rr['fuerza_por_rodillo']['fuerza_r1_n']['max_n'],
                    fuerza_r2_max_n=rr['fuerza_por_rodillo']['fuerza_r2_n']['max_n'],
                    fuerza_r1_media_n=rr['fuerza_por_rodillo']['fuerza_r1_n']['media_n'],
                    fuerza_r2_media_n=rr['fuerza_por_rodillo']['fuerza_r2_n']['media_n'],
                    paso_fuerza_max=rr['caso_fuerza_max']['paso'],paso_torque_max=rr['caso_torque_max']['paso'],
                    estado='simulación condicionada, no condición operativa validada'))
                for rpm in s['rpm_matriz_parametricas']:
                    Pmax=rr['torque_max_nm']*2*math.pi*rpm/60;Pmed=rr['torque_medio_nm']*2*math.pi*rpm/60
                    for eta in s['eficiencia_mecanica']:
                        balance=balance_potencia(config['operacion']['potencia_motor_w'],eta,Pmax,Pmed)
                        potencias.append(dict(escenario=ident,rpm_matriz_hipotetica=rpm,eficiencia_mecanica_hipotetica=eta,
                            potencia_max_w=Pmax,potencia_media_w=Pmed,**balance,
                            estado='velocidad paramétrica,NO derivada de accionamientoCAD;arranque y producción no verificados'))
        # Cribado acotado por h y mu; la presión se escala linealmente en el
        # mismo modelo elástico, nunca como nuevo equilibrio de contacto.
        for mu in s['mu_efectivo']:
            d=base.copy();v=flexion_condicional(cfg,analisis,d,mu)
            for factor in s['factores_presion']:
                for E in s['eje_M6']['E_sensibilidad_pa']:
                    estructuras.append(dict(capa_biomasa_hipotetica_m=h,presion_condicionada_pa=p0*factor,mu_hipotetico=mu,
                        E_hipotetico_pa=E,nucleo_M6_hipotetico_m=s['eje_M6']['nucleo_M6x1_escenario_m'],
                        sigma_nominal_max_pa=v['sigma_nominal_max_pa']*factor,
                        flecha_lineal_max_m=v['flecha_lineal_max_m']*factor*v['E_hipotetico_pa']/E,
                        luz_entre_taladros_m=v['luz_entre_taladros_m'],largo_eje_CAD_m=v['largo_CAD_m'],
                        error_equilibrio_n=v['error_equilibrio_n'],estado=v['limitacion']))
    pd.concat(series,ignore_index=True).to_csv(salida/'historial_escenarios.csv.gz',index=False,compression='gzip')
    pd.DataFrame(resumen).to_csv(salida/'resumen_escenarios.csv',index=False)
    pd.DataFrame(potencias).to_csv(salida/'potencia_parametrica.csv',index=False)
    pd.DataFrame(estructuras).to_csv(salida/'eje_M6_cribado_condicionado.csv',index=False)
    pd.DataFrame(geometrias).to_csv(salida/'contacto_sensibilidad.csv',index=False)
    fig,ax=plt.subplots(figsize=(7,4))
    for h,d in bases:ax.plot(d.angulo_grados,d.fuerza_total_n,label=f'Capa supuesta {h*1000:g} mm')
    ax.set(xlabel='Ángulo de matriz [°]',ylabel='Fuerza total [N]',title='Posiciones CAD; p=2,26MPa, μ efectivo=0,1 (escenarios)');ax.legend()
    fig.tight_layout();fig.savefig(salida/'cargas_condicionadas.png',dpi=160);plt.close(fig)
    return {'resultados':resumen,'contactos':geometrias,'estados_por_escenario':config['numerico']['estados'],
        'escenarios_totales':len(resumen),'velocidad_real_matriz':None,'potencia_real':None,
        'verificacion_rodamientos':'No se asigna vida a montaje608con dos interfaces sin adaptación ni fabricante comprado confirmado',
        'eje_M6':'Solo cribado con hipótesis explícitas de soporte,núcleo yE;ningúnFS ni fatiga del4140',
        'hipotesis':s}


def guardar_ensamble(analisis,agujeros,config,salida,solidos=None,dim=None):
    guardar_json(salida/'ensamble_auditado.json',analisis)
    pd.DataFrame([{k:v for k,v in p.items() if k not in ('cilindros','planos','toros')} for p in analisis['inventario']]).to_csv(salida/'componentes_ensamble.csv',index=False)
    pd.DataFrame(analisis['rodillos']).to_csv(salida/'posiciones_rodillos.csv',index=False)
    pd.DataFrame(analisis['rodamientos']).to_csv(salida/'posiciones_rodamientos.csv',index=False)
    pd.DataFrame(analisis['montaje_608']).to_csv(salida/'incompatibilidades_montaje608.csv',index=False)
    guardar_json(salida/'apoyo_inferior_pendiente.json',analisis['apoyo_inferior'])
    pd.DataFrame([
        dict(solido_id=17,estado='ambiguo',alternativas='Portador/barrido solidario al árbol o elemento de agitación; no apoyo estructural confirmado',dato_requerido='Plano funcional, unión al árbol y secuencia de montaje'),
        dict(solido_id=37,estado='ambiguo',alternativas='Anillo de apoyo, separador o retención; capacidad axial no acreditada',dato_requerido='Sección de montaje y fijación'),
        dict(solido_id=38,estado='propuesta_geometrica',alternativas='Lámina/cuchilla; unión y función de corte no verificadas',dato_requerido='Plano de fijación y función del equipo'),
        dict(solido_id=39,estado='propuesta_geometrica',alternativas='Lámina/cuchilla; unión y función de corte no verificadas',dato_requerido='Plano de fijación y función del equipo')
    ]).to_csv(salida/'componentes_ambiguos.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,8))
    for h in agujeros:ax.add_patch(Circle((h['x_mm'],h['y_mm']),h['diametro_efectivo_mm']/2,fill=False,color='.65',linewidth=.6))
    if dim:
        ax.add_patch(Circle((0,0),dim['diametro_exterior_mm']/2,fill=False,color='k'))
        ax.add_patch(Circle((0,0),dim['diametro_bore_mm']/2,fill=False,color='k'))
    for j,r in enumerate(analisis['rodillos'],1):
        theta=r['angulo_rad'];ur=np.array([math.cos(theta),math.sin(theta)]);ut=np.array([-ur[1],ur[0]])
        centro=np.array(r['centro_local_matriz_mm'][:2]);w=r['ancho_mm']
        ax.plot(*(np.array([centro-ur*w/2,centro+ur*w/2]).T),color='tab:red')
        for capa in config['sensibilidades_ensamble']['capas_biomasa_m']:
            from modelos.superposicion_variable import longitud_contacto_desde_holgura
            l=float(longitud_contacto_desde_holgura(r['separacion_envolvente_matriz_mm']/1000,r['diametro_mm']/1000,capa))*1000
            vertices=[centro+sr*ur*w/2+st*ut*l/2 for sr,st in ((-1,-1),(1,-1),(1,1),(-1,1))]
            ax.add_patch(Polygon(vertices,fill=False,linewidth=.7,alpha=.6))
        ax.scatter(*centro,color='tab:red');ax.annotate(f"R{j}: r={r['radio_posicion_mm']:.3f}mm\ngCAD={r['separacion_envolvente_matriz_mm']:.3f}mm",centro+np.array([2,3]),fontsize=8)
    ax.set(xlim=(-55,55),ylim=(-55,55),xlabel='x local matriz [mm]',ylabel='y local matriz [mm]',
        title='Montaje CAD: ejes y centros reales; huellas son escenarios\nCapas supuestas 1/2/4mm, no espesor medido');ax.set_aspect('equal')
    fig.tight_layout();fig.savefig(salida/'planta_compactacion.png',dpi=170);plt.close(fig)
    if solidos:
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopoDS import TopoDS
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        fig,axes=plt.subplots(1,2,figsize=(12,6))
        for pieza in analisis['inventario']:
            ex=TopExp_Explorer(solidos[pieza['id']],TopAbs_EDGE)
            while ex.More():
                c=BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
                puntos=np.array([[c.Value(u).X(),c.Value(u).Y(),c.Value(u).Z()] for u in np.linspace(c.FirstParameter(),c.LastParameter(),12)])
                for ax,indices in zip(axes,((0,1),(2,1))):ax.plot(puntos[:,indices[0]],puntos[:,indices[1]],linewidth=.35,alpha=.45)
                ex.Next()
            centro=pieza['centro_masa_geometrico_mm']
            for ax,indices in zip(axes,((0,1),(2,1))):ax.text(centro[indices[0]],centro[indices[1]],str(pieza['id']),fontsize=6)
        for ax,eje in zip(axes,('X','Z')):ax.set_aspect('equal');ax.set(xlabel=f'{eje} CAD [mm]',ylabel='Y CAD [mm]')
        fig.suptitle('Ensamble STEP: proyecciones de aristas y IDs del inventario; no FEM')
        fig.tight_layout();fig.savefig(salida/'ensamble_componentes.png',dpi=180);plt.close(fig)
