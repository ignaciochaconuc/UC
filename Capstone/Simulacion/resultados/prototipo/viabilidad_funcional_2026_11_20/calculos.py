"""Postproceso exclusivo M8/h4 mm; no ejecuta el acoplamiento ni runners históricos."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
import pandas as pd

D=Path(__file__).resolve().parent
S=D.parents[2]
REPO=S.parents[1]
sys.path.insert(0,str(S))

def guardar(nombre,obj):
    (D/nombre).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def conservar():
    base=json.loads((D/'historicos_sha256.json').read_text(encoding='utf-8'))
    mal=[p for p,h in base.items() if not (REPO/p).is_file() or hashlib.sha256((REPO/p).read_bytes()).hexdigest()!=h]
    if mal:raise ValueError('Históricos alterados: '+str(mal))
    return dict(archivos_verificados=len(base),alterados=0)

def entradas():
    conservar()
    a=json.loads((S/'resultados/prototipo/revision_ensamble_2026_11_19/ensamble_auditado.json').read_text(encoding='utf-8'))
    df=pd.read_csv(S/'resultados/prototipo/acoplado_m8_2026_11_20/serie_M8x1.25_h4mm.csv')
    if len(df)!=1440 or df.paso.nunique()!=1440 or not df.convergio.all() or not np.all(df.capa_m==.004):
        raise ValueError('Se requieren los 1440 estados originales M8/h4 convergidos')
    return a,df

def seccion_arbol(F,T,d=.0127,E=210e9,L=.2,nu=.3):
    if min(d,E,L)>0 and 0<=nu<.5:pass
    else:raise ValueError('Geometría/elasticidad inválidas')
    F,T=np.asarray(F),np.asarray(T)
    if F.shape!=T.shape or not np.isfinite(F).all() or not np.isfinite(T).all():raise ValueError('Cargas no correlacionadas')
    A=math.pi*d*d/4;I=math.pi*d**4/64;J=2*I;G=E/(2*(1+nu))
    sigma=F/A;tau=16*T/(math.pi*d**3)
    return dict(sigma_axial_pa=sigma,tau_torsion_pa=tau,sigma_VM_pa=np.sqrt(sigma*sigma+3*tau*tau),
                acortamiento_m=F*L/(E*A),giro_rad=T*L/(G*J),A_m2=A,I_m4=I,J_m4=J)

def presion_anular(F,M,ri,ro):
    if not 0<ri<ro:raise ValueError('Radios inválidos')
    A=math.pi*(ro*ro-ri*ri);I=math.pi*(ro**4-ri**4)/4
    return F/A-M*ro/I,F/A+M*ro/I

def resultados():
    a,df=entradas();F=df.fuerza_total_n.to_numpy();T=df.torque_total_nm.to_numpy();mu=.1
    ar=seccion_arbol(F,T);tab=df[['paso','angulo_grados','fuerza_total_n','torque_total_nm']].copy()
    for k,v in ar.items():
        if np.ndim(v):tab[k]=v
    # Centroide de fuerzas normales en el marco canónico solidario con la matriz.
    rotados=[]
    for j,r in enumerate(a['rodillos'],1):
        phi=r['angulo_rad'];rr=df[f'centroide_radial_r{j}_m'].to_numpy();tt=df[f'centroide_tangencial_r{j}_m'].to_numpy()
        xy=np.array([rr*np.cos(phi)-tt*np.sin(phi),rr*np.sin(phi)+tt*np.cos(phi)])
        rotados.append(xy*df[f'fuerza_r{j}_n'].to_numpy())
    q=sum(rotados);M=np.linalg.norm(q,axis=0);e=M/F
    tab['momento_normales_nm']=M;tab['excentricidad_normal_m']=e
    pmin,pmax=presion_anular(F,M,.0065,.0115)
    tab['p_min_apoyo_matriz_pa']=pmin;tab['p_max_apoyo_matriz_pa']=pmax
    # Flexión del árbol por manivela, dos guías ideales: solo equilibrio, no apoyo inventado.
    upper=-14.299602054092;lower=-90.2905232523622;hand=-194.299602054092
    span=(upper-lower)/1000;overhang=(lower-hand)/1000
    handF=T/.165
    tab['fuerza_manual_ideal_n']=handF
    tab['reaccion_radial_guia_superior_n']=-handF*overhang/span
    tab['reaccion_radial_guia_inferior_n']=handF*(1+overhang/span)
    # Fuerza lateral equivalente del par de rodillos, coherente con la convención 3C.
    lateral=mu*(df.fuerza_r1_n.to_numpy()-df.fuerza_r2_n.to_numpy())
    tab['lateral_modelo_rodillos_n']=lateral
    # M debido al accionamiento puro: no añade un momento externo arbitrario de mano.
    Mb=handF*overhang
    sigmab=32*Mb/(math.pi*.0127**3)
    tab['M_arbol_manivela_nm']=Mb
    tab['sigma_VM_arbol_con_flexion_manual_pa']=np.sqrt((ar['sigma_axial_pa']+sigmab)**2+3*ar['tau_torsion_pa']**2)
    brazo_matriz=(43.2003979459081-upper)/1000
    Menv=Mb+M+abs(lateral)*brazo_matriz
    tab['M_arbol_envolvente_correlacionada_nm']=Menv
    tab['sigma_VM_arbol_envolvente_pa']=np.sqrt((ar['sigma_axial_pa']+32*Menv/(math.pi*.0127**3))**2+3*ar['tau_torsion_pa']**2)
    # Misma formulación EB de EP2 para la flexión del árbol, sin tocar 3C.
    # Mano fuera de la longitud del árbol: trasladar fuerza y par a su unión real.
    from peletizadora.verificaciones import resolver_viga
    ymin=a['arbol_principal']['bbox_mm'][1]/1000
    xg=np.array([lower,upper])/1000-ymin
    union=-132.299602054092/1000-ymin;xm=43.2003979459081/1000-ymin
    nodos=np.unique(np.r_[np.linspace(0,.2,81),xg,union,xm]);ind=lambda x:int(np.argmin(abs(nodos-x)))
    cargas=np.zeros((2*len(nodos),3));cargas[2*ind(union),0]=1
    cargas[2*ind(union)+1,0]=(-194.299602054092+132.299602054092)/1000
    cargas[2*ind(xm),1]=1;cargas[2*ind(xm)+1,2]=1
    _,sol=resolver_viga(nodos,[dict(nombre='arbol_nominal',x_inicio_m=0,x_fin_m=.2,diametro_exterior_m=.0127)],
        210e9,cargas,[2*ind(x) for x in xg],'Dos guías radiales rígidas en placasCAD; apoyo axial independiente pendiente')
    env_u=abs(sol.desplazamientos[::2,0,None])*handF[None,:]+abs(sol.desplazamientos[::2,1,None])*abs(lateral)[None,:]+abs(sol.desplazamientos[::2,2,None])*M[None,:]
    tab['flecha_arbol_envolvente_m']=env_u.max(axis=0)
    tab.to_csv(D/'serie_correlacionada.csv',index=False)
    # 608: solo cargas 3C exportadas. Peso rodillo añadido como acción radial colineal opuesta.
    bearing=[];bs=[]
    for b in a['rodamientos']:
        n=b['solido_id'];rod=min(a['rodillos'],key=lambda r:np.linalg.norm(np.array(r['centro_CAD_mm'])-b['centro_CAD_mm']))
        par=sorted(sorted(a['rodamientos'],key=lambda z:np.linalg.norm(np.array(z['centro_CAD_mm'])-rod['centro_CAD_mm']))[:2],key=lambda z:z['centro_CAD_mm'][0])
        xa,xb=[z['centro_CAD_mm'][0]/1000 for z in par];xc=rod['centro_CAD_mm'][0]/1000
        vol=next(z['volumen_mm3'] for z in a['inventario'] if z['id']==rod['solido_id'])
        W=vol*1e-9*7900*9.80665
        reparto=(xb-xc)/(xb-xa) if b['solido_id']==par[0]['solido_id'] else (xc-xa)/(xb-xa)
        fy=df[f'carga_normal_608_{n}_n'].to_numpy();fz=mu*fy
        P=np.hypot(fy-reparto*W,fz);V=1.2
        Peq=float(np.mean((V*P)**3)**(1/3))
        # La media es por ángulo/revoluciones, no por tiempo; sin rpm impuesta no se publican horas.
        ratio=rod['radio_posicion_mm']/(rod['diametro_mm']/2)
        L10=(3300/Peq)**3
        bearing.append(dict(id=n,Fr_max_n=float(P.max()),P_equivalente_n=Peq,P0_max_n=float(P.max()),
            C_referencia_n=3300,C0_referencia_n=1370,S0_referencia=1370/float(P.max()),
            L10_millones_vueltas_rodillo=L10,L10_millones_vueltas_manivela=L10/ratio,
            C_min_una_millon_vueltas_n=Peq,Fa_n_hipotesis=0,peso_rodillo_n=W,
            V_giro_anillo_exterior_NHBB=V,
            L10h=None,estado='Cumple capacidad de referencia EZO; montaje y fabricante comprado pendientes'))
        bs.append(pd.DataFrame(dict(paso=df.paso,id=n,F_normal_contacto_n=fy,F_tangencial_n=fz,
                                    F_peso_asignado_n=reparto*W,Fr_n=P,P_dinamica_n=V*P)))
    pd.DataFrame(bearing).to_csv(D/'rodamientos_608.csv',index=False)
    pd.concat(bs).to_csv(D/'serie_rodamientos.csv.gz',index=False,compression='gzip')
    # Manivela: tramo recto circular Ø15 identificado en CAD, no diámetro mínimo universal.
    dh=.015;Z=math.pi*dh**3/32;sig=T.max()/Z
    perdida=[dict(eficiencia_mecanica_hipotetica=eta,torque_mano_nm=float(T.max()/eta),
                  fuerza_mano_n=float(T.max()/(eta*.165)),es_requisito=False) for eta in [1.,.8,.6]]
    pd.DataFrame(perdida).to_csv(D/'accionamiento_y_perdidas.csv',index=False)
    # Requisitos de unión por fricción; coeficiente y precarga permanecen explícitamente desconocidos.
    ri=.0065;ro=.0115;reff=2/3*(ro**3-ri**3)/(ro**2-ri**2)
    req=dict(mu_N_suma_min_n=float(T.max()/reff),radio_medio_contacto_m=reff,
             formula='T <= mu * r_medio * suma(N_i); confirmar caras efectivas y precarga',
             mu_real=None,precarga_real_n=None)
    j=int(np.argmax(ar['sigma_VM_pa']));jb=int(tab.sigma_VM_arbol_con_flexion_manual_pa.idxmax())
    r=dict(escenario='M8 h4 mm manual, resultados3C congelados',Fmax_n=float(F.max()),Tmax_nm=float(T.max()),
        Fmanual_ideal_max_n=float(handF.max()),arbol=dict(d_nominal_m=.0127,L_CAD_m=.2,
        material='Hilo corrido zincado, grado y paso no identificados',E_referencia_pa=210e9,nu_referencia=.3,
        sigma_axial_max_pa=float(ar['sigma_axial_pa'].max()),tau_torsion_max_pa=float(ar['tau_torsion_pa'].max()),
        VM_axial_torsion_max_pa=float(ar['sigma_VM_pa'][j]),paso_VM=int(df.paso.iloc[j]),
        acortamiento_200mm_max_m=float(ar['acortamiento_m'].max()),giro_200mm_max_rad=float(ar['giro_rad'].max()),
        VM_con_flexion_manual_max_pa=float(tab.sigma_VM_arbol_con_flexion_manual_pa.max()),paso_VM_flexion=int(df.paso.iloc[jb]),
        separacion_guias_CAD_m=span,voladizo_mano_m=overhang,
        Rguia_inferior_manual_max_n=float(tab.reaccion_radial_guia_inferior_n.max()),
        Rguia_superior_manual_max_abs_n=float(abs(tab.reaccion_radial_guia_superior_n).max()),
        VM_envolvente_con_desequilibrio_max_pa=float(tab.sigma_VM_arbol_envolvente_pa.max()),
        flecha_transversal_envolvente_max_m=float(tab.flecha_arbol_envolvente_m.max()),
        P_Euler_K2_200mm_n=float(math.pi**2*210e9*ar['I_m4']/(2*.2)**2),
        peso_matriz_referencia_n=next(x['volumen_mm3'] for x in a['inventario'] if x['id']==8)*1e-9*7900*9.80665,
        peso_arbol_referencia_n=a['arbol_principal']['volumen_mm3']*1e-9*7850*9.80665,
        factor_seguridad=None,estado='Dato indispensable: paso/raíz, grado y apoyo axial real. Ø12,7 liso es referencia nominal'),
        matriz=dict(material_diseno='AISI304, EP2 y Detalles',Sy_referencia_pa=210e6,E_referencia_pa=200e9,
        espesor_perforado_mm=10,canales=102,diametro_mm=99,ligamento_min_mm=1.36,
        radio_contacto_plano_ri_m=.0065,radio_contacto_plano_ro_m=.0115,
        p_apoyo_max_pa=float(pmax.max()),p_apoyo_min_pa=float(pmin.min()),excentricidad_max_m=float(e.max()),
        nucleo_central_m=(.0115**2+.0065**2)/(4*.0115),momento_normales_max_nm=float(M.max()),
        paso_momento_normales_max=int(df.paso.iloc[int(np.argmax(M))]),
        decision='Analítica comprueba contacto global, no flexión local perforada; se ejecuta FEM de geometría STEP'),
        manivela=dict(radio_m=.165,tramo_recto_diametro_m=.015,sigma_flexion_nominal_tramo_recto_max_pa=float(sig),
        fuerza_tangencial_union_al_arbol_n=float(2*T.max()/.0127),
        material=None,factor_seguridad=None,estado='Tramo recto calculable; faltan material y detalle resistente de fijación al árbol'),
        union_matriz_arbol=req,conservacion=conservar())
    guardar('resumen_analitico.json',r)
    return r

if __name__=='__main__':
    print(json.dumps(resultados(),ensure_ascii=False,indent=2))
