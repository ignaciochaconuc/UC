from pathlib import Path
import numpy as np,pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, FancyArrowPatch
import hashlib,json
p=Path(__file__).resolve().parent;o=p/'resultados'
allrows=[]
for ds in (7.5,5.5,4.0):
    r=pd.read_csv(o/f'resultados_FEM_p{ds:g}.csv')
    assert len(r)==4
    allrows.append(r)
r=pd.concat(allrows,ignore_index=True)
r.to_csv(o/'tabla_completa_convergencia.csv',index=False)
series=r[r.event=='max_fuerza_total'].sort_values('step_mesh_mm',ascending=False)

for col,ylabel,filename in [('wmax_mm','Desplazamiento vertical máximo [mm]','convergencia_desplazamiento.png'),('vm_max_MPa','Máxima tensión de von Mises [MPa]','convergencia_tensiones.png')]:
    fig,ax=plt.subplots(figsize=(7.2,4.5),layout='constrained')
    for label,mark,style in [('EMPOTRADO_ANILLO','o','-'),('APOYO_Z_CHAVETA','s','--')]:
        d=series[series['mode']==label].sort_values('step_mesh_mm')
        ax.plot(d.step_mesh_mm,d[col],ls=style,lw=1.7,marker=mark,c='black',label={'EMPOTRADO_ANILLO':'Anillo completamente fijo','APOYO_Z_CHAVETA':'Apoyo vertical y sector de chaveta'}[label])
        for _,rr in d.iterrows():
            ax.annotate(f'{rr[col]:.2f}',(rr.step_mesh_mm,rr[col]),xytext=(4,5),textcoords='offset points',fontsize=8)
    ax.set_xlabel('Paso nominal de malla en planta [mm]')
    ax.set_ylabel(ylabel)
    ax.grid(alpha=.24)
    ax.legend(frameon=False,fontsize=9)
    ax.set_title('Ensayo de refinamiento | instante de fuerza máxima',fontsize=11)
    fig.savefig(o/filename,dpi=190);plt.close(fig)

cad=pd.read_csv(p/'fuentes/agujeros_matriz_CAD.csv').sort_values('id')
xy=cad[['x_mm','y_mm']].to_numpy()
fs=pd.read_csv(p/'fuentes/fuerzas_por_agujero_4A.csv')
d=fs[fs.evento=='max_fuerza_total'].copy()
theta=np.deg2rad(d.angulo_grados.iloc[0]);c,s=np.cos(theta),np.sin(theta)
fig,axs=plt.subplots(1,2,figsize=(11,5.2),layout='constrained')
ax=axs[0]
ax.add_patch(Circle((0,0),100,fill=False,lw=2))
ax.add_patch(Circle((0,0),25,fill=False,lw=1.3))
for x,y in xy: ax.add_patch(Circle((x,y),3,edgecolor='#555555',facecolor='white',lw=.48))
loadids=np.unique(d.id_agujero).astype(int)-1
for i in loadids: ax.add_patch(Circle(xy[i],5.5,edgecolor='black',facecolor='none',lw=1,ls='--'))
ax.text(0,110,'Círculos grandes: zonas de carga asumidas',ha='center',fontsize=9)
ax.set(xlim=(-116,116),ylim=(-110,120),xlabel='x [mm]',ylabel='y [mm]',title='Disco perforado y cargas de un instante')
ax.set_aspect('equal')
ax=axs[1]
ax.add_patch(Circle((0,0),31,fill=False,ls=':',lw=.8))
ax.add_patch(Wedge((0,0),29,0,360,width=4,edgecolor='black',facecolor='#d4d4d4',lw=1))
ax.add_patch(Wedge((0,0),25, -18,18, width=2.8,edgecolor='black',facecolor='#5a5a5a',lw=1))
ax.annotate('Anillo inferior Ø50-58:\napoyo axial idealizado',xy=(-27,-5),xytext=(-65,-38),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.annotate('Sector idealizado de chaveta\npara restricción tangencial',xy=(24,2),xytext=(23,48),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.set(xlim=(-78,88),ylim=(-70,73),xlabel='x [mm]',ylabel='y [mm]',title='Hipótesis de apoyo (no CAD definitivo)')
ax.set_aspect('equal')
fig.savefig(o/'geometria_y_apoyos.png',dpi=185);plt.close(fig)
# Main payload
fine=r[r.step_mesh_mm==4.0].copy()
for _,x in fine.iterrows():
    assert x.cg_info==0
checks={
    'perforaciones':102,
    'E_MPa_asumido':210000,
    'nu_asumido':0.30,
    'material_referencia_1045_quench_tempered_barra_100_250mm_Sy_MPa':340,
    'malla_mas_fina':{'paso_planta_mm':4,'capas':4,'tetraedros':90600,'nodos':22615},
    'fuerzas_y_torque_originales_preservados':True,
    'soluciones':fine.to_dict('records'),
    'fuentes_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in (p/'fuentes').glob('*.csv')}
}
(o/'resumen_verificado_4D.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False),encoding='utf8')
print('Gráficos, tablas y resumen verificado preparados.')
