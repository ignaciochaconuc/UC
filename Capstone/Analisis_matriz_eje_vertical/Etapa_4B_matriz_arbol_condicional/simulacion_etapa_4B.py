"""ETAPA 4B: comprobaciones NOMINALES/CONDICIONALES de matriz y árbol.
No es FEM ni obtiene reacciones de apoyos no especificados. Conserva todos
los instantes correlacionados de las 1440 muestras de 3C postprocesadas en 4A.
Python 3.10+, pip install pandas numpy matplotlib.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE = Path(__file__).resolve().parent
OUT=BASE/'resultados'; OUT.mkdir(exist_ok=True)
SRC=BASE/'fuentes'/'series_resultantes_matriz_eje_4A.csv'
df=pd.read_csv(SRC)
need=['angulo_grados','Fz_normal_N','Mx_normales_Nm','My_normales_Nm','M_flexion_normales_Nm','T_resistente_3C_Nm','F_tangencial_neta_aprox_y_N']
assert df.shape[0]==1440 and not df[need].isna().any().any()
assert np.isclose(df.Fz_normal_N.max(),14070.987477,atol=0.05)
assert np.isclose(df.T_resistente_3C_Nm.max(),88.923966,atol=0.05)
F=df['Fz_normal_N'].to_numpy()                  # axial, N
T=df['T_resistente_3C_Nm'].to_numpy()           # torque, Nm
M=df['M_flexion_normales_Nm'].to_numpy()        # momento libre global, Nm; NO interno resuelto
Fy=df['F_tangencial_neta_aprox_y_N'].to_numpy() # fuerza lateral modelo compacto, N
E=210e9; G=80e9
section=[]
for dmm in (35,40,45,50):
 d=dmm*1e-3
 A=np.pi*d*d/4; I=np.pi*d**4/64; J=np.pi*d**4/32
 sig_a=F/A/1e6                    # MPa
 tau=16*T/(np.pi*d**3)/1e6       # MPa
 sig_b=32*M/(np.pi*d**3)/1e6     # MPa; condicional M total presente en sección
 vm_a=np.sqrt(sig_a**2+3*tau**2)
 vm_c=np.sqrt((sig_a+sig_b)**2+3*tau**2)
 k1=vm_a.argmax(); k2=vm_c.argmax()
 section.append(dict(d_mm=dmm, area_mm2=A*1e6, sigma_axial_max_MPa=sig_a.max(),
        tau_torsion_max_MPa=tau.max(), sigma_b_flexion_externa_max_MPa=sig_b.max(),
        von_mises_axial_torsion_max_MPa=vm_a[k1],angulo_max_axial_torsion_deg=df.angulo_grados.iloc[k1],
        von_mises_M_total_condicional_max_MPa=vm_c[k2],angulo_max_condicional_deg=df.angulo_grados.iloc[k2],
        F_kN_en_pico_condicional=F[k2]/1e3,T_Nm_en_pico_condicional=T[k2],M_Nm_en_pico_condicional=M[k2],
        alargamiento_axial_por_100mm_max_mm=F.max()*(.1)/(A*E)*1e3,
        giro_torsion_por_100mm_max_grados=np.degrees(T.max()*.1/(G*J)),
        n_min_1045_QT_370_solo_nominal=370/vm_a.max(),
        n_min_4140_QT_650_solo_nominal=650/vm_a.max(),
        n_1045_370_condicional_M_total=370/vm_c.max(),
        n_4140_650_condicional_M_total=650/vm_c.max()))
sdf=pd.DataFrame(section)
sdf.to_csv(OUT/'verificaciones_nominales_eje.csv',index=False)
# Los instantes críticos nunca se mezclan
crit=[]
for name,series in [('Fz_max',F),('T_res_max',T),('M_normal_max',M),('F_t_lateral_mod_max_abs',np.abs(Fy))]:
 k=int(np.argmax(series)); r=df.iloc[k]
 crit.append(dict(caso=name,angulo_grados=r.angulo_grados,
    Fz_kN=r.Fz_normal_N/1e3,T_Nm=r.T_resistente_3C_Nm,
    M_normal_Nm=r.M_flexion_normales_Nm,
    Mx_Nm=r.Mx_normales_Nm,My_Nm=r.My_normales_Nm,
    Fy_lateral_modelo_N=r.F_tangencial_neta_aprox_y_N))
pd.DataFrame(crit).to_csv(OUT/'instantes_criticos_correlacionados.csv',index=False)
# Resalte/huella axial hipotética: aro Ø58-Ø50 SÓLO SI ambas superficies se apoyan
A_hombro=np.pi*(58**2-50**2)/4 # mm^2
soporte=dict(D_ext_mm=58,D_int_mm=50,area_teorica_contacto_mm2=A_hombro,
  p_media_axial_MPa=F.mean()/A_hombro,
  p_max_axial_MPa=F.max()/A_hombro,
  fuerza_tangencial_en_union_d50_torque_max_N=2*T.max()/.05,
  fuerza_tangencial_en_union_d50_torque_media_N=2*T.mean()/.05,
  peso_aprox_matriz_sin_avellanados_N=7.51*9.81,
  nota='Presión promedio condicionada a contacto anular COMPLETO; no válida si no hay contacto/retención o carga localizada.')
(OUT/'presion_apoyo_condicional.json').write_text(json.dumps(soporte,indent=2,ensure_ascii=False),encoding='utf8')
# Fuerza sobre polea a partir de diferencia de tensiones (sin forzar pretensión): F_radial=T1+T2, T1/T2=k>1.
rp=.280/2
Deltat=T.max()/rp
belt=[]
for k in [1.5,2,3,4,5]:
 f=Deltat*(k+1)/(k-1)
 belt.append(dict(relacion_T1_T2_sup_k=k,delta_tensiones_total_N=Deltat,
                  suma_tensiones_total_N=f,
                  M_solo_carga_polea_a_50mm_condicional_Nm=f*.05,
                  M_solo_carga_polea_a_100mm_condicional_Nm=f*.1,
                  nota='Una suma de fuerzas radial ilustrativa; no equivale a una reacción ni define pretensión real.'))
bdf=pd.DataFrame(belt);bdf.to_csv(OUT/'transmision_condicional.csv',index=False)
# Casos correlacionados + gráfica
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,constrained_layout=True)
a=df.angulo_grados.to_numpy()
axs[0].plot(a,F/1000,label='Fuerza axial Fz'); axs[0].set_ylabel('Fz [kN]'); axs[0].grid(alpha=.2)
axs[1].plot(a,M,label='Momento normales');axs[1].set_ylabel('M [N·m]'); axs[1].grid(alpha=.2)
axs[2].plot(a,T,label='Torque resistente');axs[2].set_ylabel('T [N·m]'); axs[2].set_xlabel('Ángulo de matriz [°]');axs[2].grid(alpha=.2)
for ax in axs:
 for r in crit[:3]:
  ax.axvline(r['angulo_grados'],linewidth=.6,alpha=.4,linestyle=':')
fig.suptitle('Cargas correlacionadas sobre matriz y árbol · Etapa 3C / 4A')
fig.savefig(OUT/'correlacion_cargas.png',dpi=185);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5))
for d in [35,40,45,50]:
 rr=sdf[sdf.d_mm==d].iloc[0]
 ax.scatter(d,rr.von_mises_axial_torsion_max_MPa,s=55,marker='o',color='black')
 ax.scatter(d,rr.von_mises_M_total_condicional_max_MPa,s=55,marker='x',color='black')
ax.plot(sdf.d_mm,sdf.von_mises_axial_torsion_max_MPa,'k-',label='Axial + torsión nominal')
ax.plot(sdf.d_mm,sdf.von_mises_M_total_condicional_max_MPa,'k--',label='Hipótesis: momento total en sección')
ax.set(xlabel='Diámetro de sección lisa [mm]',ylabel='von Mises máxima [MPa]',title='Sensibilidad nominal del árbol (NO verificación final)')
ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(OUT/'sensibilidad_eje.png',dpi=185);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.8))
ax.plot(bdf.relacion_T1_T2_sup_k,bdf.suma_tensiones_total_N/1000,marker='o',color='black')
ax.set(xlabel='Relación de tensiones supuesta T1/T2',ylabel='Carga lateral polea [kN]',title='Sensibilidad a tensión de correa: sin pretensión especificada')
ax.grid(alpha=.25);fig.tight_layout();fig.savefig(OUT/'sensibilidad_correas.png',dpi=185);plt.close(fig)
summary=dict(muestras=len(df),Fz_max_kN=F.max()/1e3,Fz_media_kN=F.mean()/1e3,
T_max_Nm=T.max(),T_medio_Nm=T.mean(),M_normales_max_Nm=M.max(),
F_tangencial_neta_mod_max_abs_N=np.abs(Fy).max(),
secciones=list(section),casos=crit,resalte_condicional=soporte)
(OUT/'resumen_4B.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
print('SIMULACIÓN ANALÍTICA 4B OK; etapas anteriores sin cambios.')
print(sdf[['d_mm','von_mises_axial_torsion_max_MPa','von_mises_M_total_condicional_max_MPa']].round(3).to_string(index=False))
print(pd.DataFrame(crit).round(4).to_string(index=False))
print('P contacto condicional:',round(soporte['p_max_axial_MPa'],3),'MPa; deltacorreas',round(Deltat,2),'N')
