"""Postproceso exclusivo del CAD definitivo; propiedades y métodos ya adoptados."""
from auditar import D,S,guardar
from pathlib import Path
from simular_final import entradas as entradas_3C
import json,math,hashlib
import numpy as np,pandas as pd

def conservar():
    base=json.loads((D/'historicos_sha256.json').read_text(encoding='utf-8'));repo=S.parents[1]
    mal=[p for p,h in base.items() if not (repo/p).is_file() or hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h]
    if mal:raise ValueError('Históricos alterados: '+str(mal))
    entrada=json.loads((D/'entrada_identificada.json').read_text(encoding='utf-8'))
    original=Path(entrada['archivo_proporcionado'])
    if original.exists() and hashlib.sha256(original.read_bytes()).hexdigest()!=entrada['SHA_nuevo']:raise ValueError('El STEP adjunto cambió')
    copia=D/entrada['copia_inmutable_en_revision']
    if hashlib.sha256(copia.read_bytes()).hexdigest()!=entrada['SHA_nuevo']:raise ValueError('La copia del STEP cambió')
    return dict(archivos_historicos=len(base),alterados=0,STEP_adjunto_intacto=True)

def entradas_fem():
    a,c,h=entradas_3C();df=pd.read_csv(D/'serie_3C_definitiva.csv')
    if len(df)!=1440 or not df.convergio.all():raise ValueError('No usar cargas sin converger')
    return a,df

def seccion(F,T,d,L,E=210e9):
    A=math.pi*d*d/4;J=math.pi*d**4/32;G=E/2.6
    sig=F/A;tau=16*T/(math.pi*d**3)
    return sig,tau,np.sqrt(sig*sig+3*tau*tau),F*L/(E*A),T*L/(G*J)

def main():
    conservar();a,df=entradas_fem();inv=a['inventario'];F=df.fuerza_total_n.to_numpy();T=df.torque_total_nm.to_numpy()
    shaft=a['arbol_principal'];ds=2*shaft['cilindros'][0]['radio_mm']/1000;L=shaft['cilindros'][0]['largo_mm']/1000
    arm=next(x for x in inv if any(abs(c['radio_mm']-7.5)<1e-5 and c['largo_mm']>100 for c in x['cilindros']))
    mainaxis=np.array(shaft['cilindros'][0]['centro_eje_mm'])
    grip=next(c for c in arm['cilindros'] if abs(c['radio_mm']-10)<1e-5)
    rad=float(np.linalg.norm((np.array(grip['centro_eje_mm'])-mainaxis)[[0,2]]))/1000
    attach=next(c for c in arm['cilindros'] if abs(c['radio_mm']-6.35)<1e-5)
    up=next(c['centro_eje_mm'][1]/1000 for c in inv[15]['cilindros'] if abs(c['radio_mm']-6.5)<1e-5)
    bearing=inv[52];low=next(c['centro_eje_mm'][1]/1000 for c in bearing['cilindros'] if abs(c['radio_mm']-12.7)<1e-5)
    hand=grip['centro_eje_mm'][1]/1000;ya=attach['centro_eje_mm'][1]/1000
    span=up-low;over=low-hand;Ph=T/rad
    sig,tau,vm,delta,twist=seccion(F,T,ds,L)
    # Resultantes de normales con centroides corregidos, marco del solver.
    q=np.zeros((3,len(df)));Ti=np.array(a['correspondencia_matriz']['local_matriz_a_ensamble'])
    for j,ro in enumerate(a['rodillos'],1):
        rr=df[f'centroide_radial_r{j}_m'].to_numpy();tt=df[f'centroide_tangencial_r{j}_m'].to_numpy();ph=ro['angulo_rad']
        xy=np.array([rr*np.cos(ph)-tt*np.sin(ph),rr*np.sin(ph)+tt*np.cos(ph)])
        q+=(Ti[:3,:2]@xy)*df[f'fuerza_r{j}_n'].to_numpy()
    Mn=np.linalg.norm(q[[0,2]],axis=0)
    lateral=.1*(df.fuerza_r1_n.to_numpy()-df.fuerza_r2_n.to_numpy())
    ymat=inv[a['matriz_id']-1]['bbox_mm'][4]/1000
    Menv=Ph*over+Mn+abs(lateral)*abs(ymat-up)
    vmenv=np.sqrt((sig+32*Menv/(math.pi*ds**3))**2+3*tau**2)
    # Árbol completo: mismas funciones EB de EP2, nuevas guías y brazo real.
    from peletizadora.verificaciones import resolver_viga
    ymin=shaft['bbox_mm'][1]/1000;gu=np.array([up,low])-ymin;xa=ya-ymin;xm=ymat-ymin
    nod=np.unique(np.r_[np.linspace(0,L,81),gu,xa,xm]);idx=lambda x:int(np.argmin(abs(nod-x)))
    f=np.zeros((2*len(nod),3));f[2*idx(xa),0]=1;f[2*idx(xa)+1,0]=hand-ya;f[2*idx(xm),1]=1;f[2*idx(xm)+1,2]=1
    _,sol=resolver_viga(nod,[dict(nombre='arbol_nominal',x_inicio_m=0,x_fin_m=L,diametro_exterior_m=ds)],210e9,f,[2*idx(x) for x in gu],'GuíaCAD16 y centro de bore del rodamiento53: hipótesis radiales rígidas')
    uenv=abs(sol.desplazamientos[::2,0,None])*Ph[None,:]+abs(sol.desplazamientos[::2,1,None])*abs(lateral)[None,:]+abs(sol.desplazamientos[::2,2,None])*Mn[None,:]
    tab=df[['paso','angulo_grados','fuerza_total_n','torque_total_nm']].copy()
    for k,v in dict(sigma_axial_pa=sig,tau_torsion_pa=tau,VM_axial_torsion_pa=vm,VM_envolvente_pa=vmenv,delta_axial_m=delta,giro_rad=twist,
        fuerza_manual_n=Ph,Rguia_superior_manual_n=-Ph*over/span,Rrodamiento_principal_manual_n=Ph*(1+over/span),M_normales_nm=Mn,flecha_arbol_envolvente_m=uenv.max(axis=0)).items():tab[k]=v
    ri=.0065;ro=.009525;A=math.pi*(ro*ro-ri*ri);Ia=math.pi*(ro**4-ri**4)/4
    tab['pmin_apoyo_matriz_pa']=F/A-Mn*ro/Ia;tab['pmax_apoyo_matriz_pa']=F/A+Mn*ro/Ia
    tab.to_csv(D/'serie_componentes.csv',index=False)
    bs=[];loads=[]
    for b in a['rodamientos']:
        n=b['solido_id'];rod=min(a['rodillos'],key=lambda z:np.linalg.norm(np.array(z['centro_CAD_mm'])-b['centro_CAD_mm']))
        par=sorted(sorted(a['rodamientos'],key=lambda z:np.linalg.norm(np.array(z['centro_CAD_mm'])-rod['centro_CAD_mm']))[:2],key=lambda z:z['centro_CAD_mm'][0])
        x1,x2=[z['centro_CAD_mm'][0]/1000 for z in par];xc=rod['centro_CAD_mm'][0]/1000
        W=inv[rod['solido_id']-1]['volumen_mm3']*1e-9*7900*9.80665
        rw=(x2-xc)/(x2-x1) if n==par[0]['solido_id'] else (xc-x1)/(x2-x1)
        N=df[f'carga_normal_608_{n}_n'].to_numpy();Fr=np.hypot(N-rw*W,.1*N);P=1.2*Fr;Peq=float(np.mean(P**3)**(1/3))
        bs.append(dict(id=n,Frmax_n=float(Fr.max()),Peq_n=Peq,S0=1370/float(Fr.max()),L10_millones_rev=(3300/Peq)**3,
                       C_ref_n=3300,C0_ref_n=1370,L10h=None,estado='Referencia EZO/Fa0/V1,2, marca comprada no identificada'))
        loads.append(pd.DataFrame(dict(paso=df.paso,id=n,N_contacto_n=N,peso_asignado_n=rw*W,Fr_n=Fr,P_n=P)))
    pd.DataFrame(bs).to_csv(D/'rodamientos_608.csv',index=False);pd.concat(loads).to_csv(D/'cargas_608.csv.gz',index=False,compression='gzip')
    Wmat=inv[a['matriz_id']-1]['volumen_mm3']*1e-9*7900*9.80665;Warbol=shaft['volumen_mm3']*1e-9*7850*9.80665
    r=dict(arbol=dict(d_nominal_m=ds,L_m=L,guia_superior_y_m=up,apoyo_inferior_bore_y_m=low,separacion_guias_m=span,
        union_brazo_y_m=ya,centro_mano_y_m=hand,voladizo_mano_m=over,VM_nominal_max_pa=float(vm.max()),
        sigma_axial_max_pa=float(sig.max()),tau_max_pa=float(tau.max()),VM_envolvente_max_pa=float(vmenv.max()),delta_axial_max_m=float(delta.max()),
        giro_max_rad=float(twist.max()),flecha_transversal_envolvente_m=float(uenv.max()),Rprincipal_radial_manual_max_n=float((Ph*(1+over/span)).max()),
        Rguia_superior_manual_max_n=float((Ph*over/span).max()),demanda_axial_soporte_n=float(F.max()+Wmat+Warbol),
        grado=None,raiz_resistente_m=None,factor_seguridad=None,rosca_CAD='Tuercas1/2-13, verificar varilla real',
        soporte='Cuerpo52/rodamiento53/buje55 presentes; C,C0 y retención axial de árbol al buje no acreditadas'),
        matriz=dict(geometria_reutilizada=True,material='AISI304',ri_apoyo_m=ri,ro_apoyo_m=ro,area_apoyo_m2=A,
        pmax_apoyo_pa=float(tab.pmax_apoyo_matriz_pa.max()),pmin_apoyo_pa=float(tab.pmin_apoyo_matriz_pa.min()),
        paso_momento_normales_max=int(df.paso.iloc[int(np.argmax(Mn))]),FEM_reutilizable=False,
        motivo_FEM='Apoyo inferior cambia: arandelaR11,5 efectiva -> cara tuercaR9,525, reducción de área46%; repetir solución, matriz material iguales'),
        manivela=dict(radio_m=rad,Fmax_ideal_n=float(Ph.max()),sigma_tramo_recto_pa=float(32*T.max()/(math.pi*.015**3)),
            material=None,factor_seguridad=None,union='Agujero cilíndrico12,7 y árbol12,7: transmisión por apriete/unión positiva sin acreditar'),
        apoyo_principal=dict(id_cuerpo=52,id_rodamiento=53,id_buje=55,bore_rodamiento_mm=25.4,bore_buje_mm=12.7,exterior_buje_mm=25.4,
            longitud_buje_mm=36,solape_bore_mm=31.0134,C_n=None,C0_n=None,retencion_axial_arbol_buje='No hay bloqueo positivo modelado entre árbol12,7 y buje; tornillos del rodamiento actúan sobre exterior25,4'),
        conservacion=conservar())
    guardar('resumen_componentes.json',r)
    old=pd.read_csv(S/'resultados/prototipo/acoplado_m8_2026_11_20/serie_M8x1.25_h4mm.csv');oo=json.loads((S/'resultados/prototipo/viabilidad_funcional_2026_11_20/resumen_integrado.json').read_text(encoding='utf-8'))
    rows=[]
    for nombre,col,factor,unidad,razon in [('Fuerza máxima','fuerza_total_n',1,'N','Rodillos centrados y nueva luz de fijaciones; centroides corregidos'),('Torque máximo','torque_total_nm',1,'Nm','Geometría prácticamente conservada; máximo en otro estado'),('Flecha M8','flecha_max_m',1000,'mm','Luz y repartos corregidos, mismo núcleo6,466'),('Tensión nominal M8','sigma_nominal_max_pa',1e-6,'MPa','Mismo modelo doblemente empotrado, nueva luz'),('Holgura mínima R1','holgura_r1_min_m',1000,'mm','Deformación y simetría del nuevo montaje')]:
        x=float(old[col].min() if 'Holgura' in nombre else old[col].max())*factor;y=float(df[col].min() if 'Holgura' in nombre else df[col].max())*factor
        rows.append(dict(resultado=nombre,anterior=x,actualizado=y,unidad=unidad,variacion_pct=100*(y/x-1),estado='Recalculado',explicacion=razon))
    for nombre,x,y,un,why in [('Longitud árbol',.2,L,'m','Cilindro medido200->235mm'),('Fuerza manual',oo['Fmanual_ideal_max_n'],Ph.max(),'N','Mismo radio165mm; nuevo torque'),('VM árbol con flexión',oo['arbol']['VM_envolvente_con_desequilibrio_max_pa']/1e6,vmenv.max()/1e6,'MPa','Nuevo apoyo inferior y mayor voladizo de la mano'),('Radio apoyo matriz',11.5,9.525,'mm','Arandela inferior eliminada; apoya directamente cara de tuerca'),('Área apoyo matriz',math.pi*(11.5**2-6.5**2),A*1e6,'mm2','Reducción de contacto inferior exige nuevoFEM')]:
        rows.append(dict(resultado=nombre,anterior=x,actualizado=float(y),unidad=un,variacion_pct=100*(y/x-1),estado='Recalculado',explicacion=why))
    pd.DataFrame(rows).to_csv(D/'comparacion_resultados.csv',index=False)
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
