"""Etapa 4C: reacciones solo si apoyos realmente conocidos, y contacto condicional.

No modifica las 1440 muestras de 3C/4A. Unidades internas: mm, N, N mm.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
DATOS = BASE / 'datos' / 'series_4A_sin_modificar.csv'
SALIDAS = BASE / 'resultados'
SALIDAS.mkdir(exist_ok=True)

# Datos geométricos verificables; 118 mm es distancia ENTRE CARAS TRANSVERSALES
D_HUECO = 50.0
D_RESALTE = 58.0
R_IN = D_HUECO/2
R_OUT = D_RESALTE/2
A = np.pi * (R_OUT**2-R_IN**2)
I = np.pi/4 * (R_OUT**4-R_IN**4)
Z = I / R_OUT
R_MEDIO_PONDERADO = (2/3)*(R_OUT**3-R_IN**3)/(R_OUT**2-R_IN**2)

s = pd.read_csv(DATOS).copy()
assert len(s)==1440 and np.allclose(s.F1_N+s.F2_N, s.Fz_normal_N, rtol=1e-9)
assert np.isclose(s.Fz_normal_N.max(),14070.98747694,atol=0.02)
assert np.isclose(s.T_resistente_3C_Nm.max(),88.92396579,atol=0.001)

# El siguiente modelo SOLO aplica si toda la carga axial y el momento atraviesan
# una cara ANULAR Ø50/Ø58 en contacto ELÁSTICO PLANO TOTAL, sin separación.
s['p_med_MPa'] = s.Fz_normal_N/A
s['p_flex_ext_MPa'] = s.M_flexion_normales_Nm*1000/Z
s['p_max_ideal_MPa'] = s.p_med_MPa+s.p_flex_ext_MPa
s['p_min_ideal_MPa'] = s.p_med_MPa-s.p_flex_ext_MPa
s['e_resultante_mm'] = 1000*s.M_flexion_normales_Nm/s.Fz_normal_N
s['margen_nucleo_contacto'] = (Z/A)/s.e_resultante_mm
s['mu_min_solo_friccion'] = 1000*s.T_resistente_3C_Nm/(s.Fz_normal_N*R_MEDIO_PONDERADO)
s.to_csv(SALIDAS/'envolvente_anillo_condicional.csv',index=False)

# Resumen en instantes SIN fusionar máximos no coincidentes.
def fila_max(c):
 return s.loc[s[c].idxmax()]
def fila_min(c):
 return s.loc[s[c].idxmin()]
casos = {
 'max_fuerza_axial': fila_max('Fz_normal_N'),
 'max_momento_normal': fila_max('M_flexion_normales_Nm'),
 'max_presion_anular': fila_max('p_max_ideal_MPa'),
 'min_presion_anular': fila_min('p_min_ideal_MPa'),
 'max_excentricidad': fila_max('e_resultante_mm'),
 'max_requerimiento_friccion': fila_max('mu_min_solo_friccion'),
}
columnas=['angulo_grados','Fz_normal_N','M_flexion_normales_Nm','T_resistente_3C_Nm','e_resultante_mm','p_med_MPa','p_max_ideal_MPa','p_min_ideal_MPa','mu_min_solo_friccion']
res=pd.DataFrame({k: v[columnas] for k,v in casos.items()}).T
res.index.name='caso'
res.to_csv(SALIDAS/'casos_criticos_union.csv')

# Verificación dimensional: geometría entrada de biomasa; no recálculo de fuerzas 3C.
Drod=100.0; h0=4.0
L01=np.sqrt(Drod*(h0-0.1)-(h0-0.1)**2)
L03=np.sqrt(Drod*(h0-0.3)-(h0-0.3)**2)

# Reacciones sobre árbol vertical: no se ejecutan sin posiciones de sus apoyos.
# Todos los z en mm sobre el mismo eje, y carga radial real de correa (N).
# zM corresponde a la altura donde se reduce la matriz a fuerza/couple equivalentes.
# axial 'A'/'B' define rodamiento de empuje, o None si no identificado.
config = json.loads((BASE/'config_apoyos.json').read_text(encoding='utf-8'))
reacciones_status='PENDIENTE: centros de rodamientos verticales y pretensión/dirección de correa no confirmados.'
if all(config.get(k) is not None for k in ['zA_mm','zB_mm','zM_mm','zP_mm','F_correa_N','angulo_correa_grados']):
 zA,zB,zM,zP=(float(config[k]) for k in ['zA_mm','zB_mm','zM_mm','zP_mm'])
 assert zB>zA, 'Orden de apoyos requerido: zB > zA.'
 Fa=float(config['F_correa_N']);phi=np.deg2rad(config['angulo_correa_grados'])
 Fbx=Fa*np.cos(phi);Fby=Fa*np.sin(phi)
 # Única fuerza lateral que permite 4A: resultante tangencial aprox. sobre y.
 Fmx=np.zeros(len(s));Fmy=s.F_tangencial_neta_aprox_y_N.to_numpy()
 # Balance de fuerzas y momentos globales con z positivo a lo largo del árbol.
 # z×F_x = +M_y, z×F_y = -M_x
 RBx=-(s.My_normales_Nm.to_numpy()*1000+(zM-zA)*Fmx+(zP-zA)*Fbx)/(zB-zA)
 RBy=(s.Mx_normales_Nm.to_numpy()*1000-(zM-zA)*Fmy-(zP-zA)*Fby)/(zB-zA)
 RAx=-RBx-Fmx-Fbx
 RAy=-RBy-Fmy-Fby
 reac=s[['angulo_grados']].copy()
 reac['RA_x_N']=RAx;reac['RA_y_N']=RAy;reac['RB_x_N']=RBx;reac['RB_y_N']=RBy
 reac['RA_radial_N']=np.hypot(RAx,RAy);reac['RB_radial_N']=np.hypot(RBx,RBy)
 reac.to_csv(SALIDAS/'reacciones_condicionales.csv',index=False)
 reacciones_status='CALCULADAS CON ENTRADAS DE USUARIO; verificar si sus coordenadas son centros reales de los rodamientos.'

# Imágenes de apoyo: magnitudes, no un FEM ni distribución real de contacto.
fig,ax=plt.subplots(figsize=(9,4.5))
ax.plot(s.angulo_grados,s.p_max_ideal_MPa,label='Presión máxima ideal')
ax.plot(s.angulo_grados,s.p_min_ideal_MPa,label='Presión mínima ideal')
ax.plot(s.angulo_grados,s.p_med_MPa,label='Presión media')
ax.set(xlabel='Giro de la matriz (grados)',ylabel='Presión nominal (MPa)',title='Anillo Ø50/Ø58: contacto completo hipotético')
ax.legend();ax.grid(True,alpha=.3);fig.tight_layout()
fig.savefig(SALIDAS/'presiones_anillo_condicional.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.5))
ax.plot(s.angulo_grados,s.e_resultante_mm,label='Excentricidad instantánea')
ax.axhline(Z/A,linestyle='--',label='Límite contacto completo ideal')
ax.set(xlabel='Giro de la matriz (grados)',ylabel='Excentricidad equivalente (mm)',title='Excentricidad de las cargas normales sobre la matriz')
ax.legend();ax.grid(True,alpha=.3);fig.tight_layout()
fig.savefig(SALIDAS/'excentricidad_vs_limite.png',dpi=160);plt.close(fig)

resumen={
 'muestras':len(s),'Fz_max_N':float(s.Fz_normal_N.max()),
 'T_max_Nm':float(s.T_resistente_3C_Nm.max()),
 'M_normales_max_Nm':float(s.M_flexion_normales_Nm.max()),
 'diametros_anillo_mm':[D_HUECO,D_RESALTE],
 'area_anillo_mm2':A,'inercia_diametral_mm4':I,'modulo_contacto_mm3':Z,
 'excentricidad_limite_mm':Z/A,
 'excentricidad_max_mm':float(s.e_resultante_mm.max()),
 'angulo_excentricidad_max_deg':float(fila_max('e_resultante_mm').angulo_grados),
 'presion_min_global_MPa':float(s.p_min_ideal_MPa.min()),
 'presion_max_global_MPa':float(s.p_max_ideal_MPa.max()),
 'angulo_presion_max_deg':float(fila_max('p_max_ideal_MPa').angulo_grados),
 'angulo_presion_min_deg':float(fila_min('p_min_ideal_MPa').angulo_grados),
 'radio_contacto_efectivo_mm':R_MEDIO_PONDERADO,
 'mu_requerida_friccion_solo_max':float(s.mu_min_solo_friccion.max()),
 'Lc_gap_01_mm':L01,'Lc_gap_03_mm':L03,
 'cambio_Lc_porcentaje':100*(L03/L01-1),
 'distancia_118mm':'mínima separación entre DOS CARAS de eje transversal, NO centros de rodamientos del árbol vertical',
 'reacciones_estado':reacciones_status,
 'advertencia':'Resultados del anillo IDEAL y CONDICIONALES a que transmite Fz+M y mantiene contacto plano completo. No son contacto FEM ni seguridad de retención; torque solo por fricción es un escenario hipotético.'
}
(SALIDAS/'resumen_4C.json').write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(resumen,ensure_ascii=False,indent=2))
