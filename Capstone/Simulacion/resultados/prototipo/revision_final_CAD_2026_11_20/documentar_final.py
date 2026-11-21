"""Memorias definitivas A.3--A.8; solo lee resultados de esta revisión."""
from componentes_final import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Circle
import zipfile
import re

def fmt(x,n=3):return f'{float(x):.{n}f}'.replace('.',',')
def tex(n,t):
    protected=r'(\\(?:cite|texttt|label|ref|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}|\$[^$]*\$)'
    parts=re.split(protected,t)
    for i in range(0,len(parts),2):
        v=re.sub(r'(?<=[a-záéíóúñ])(?=\d)',' ',parts[i])
        v=re.sub(r'(?<=\d)(?=(?:MPa|GPa|kN|mm|N|kgf|kg|m)\b)',r'\\,',v)
        v=v.replace('AISI304','AISI 304').replace('datosCAD','datos CAD')
        v=re.sub(r'(?<=[a-záéíóúñ])(?=(?:FEM|CAD|ABS|NHBB)\b)',' ',v)
        v=re.sub(r'(?<=[a-záéíóúñ]),(?=\d)',', ',v)
        parts[i]=v
    for i in range(1,len(parts),2):
        if parts[i].startswith('$'):
            if parts[i-1] and (parts[i-1][-1].isalnum() or parts[i-1][-1]=='.'):parts[i-1]+=' '
            if i+1<len(parts) and parts[i+1] and parts[i+1][0].isalnum():parts[i+1]=' '+parts[i+1]
        elif parts[i].startswith(r'\cite') and parts[i-1] and parts[i-1][-1].isalnum():parts[i-1]+='~'
    t=''.join(parts)
    t=re.sub(r'\$(?=(?:MPa|GPa|kN|mm|N)\b)','$ ',t)
    (D/n).write_text(t,encoding='utf-8')
def tabla(headers,rows):
    return '\\begin{center}\\begin{tabular}{'+'l'*len(headers)+'}\\toprule\n'+' & '.join(headers)+'\\\\\\midrule\n'+'\n'.join(' & '.join(map(str,r))+'\\\\' for r in rows)+'\n\\bottomrule\\end{tabular}\\end{center}\n'
def figura(n,width='.85'):return '\\begin{center}\\includegraphics[width='+width+'\\linewidth]{'+n+'}\\end{center}\n'

def main():
    a,d=entradas_fem();r=json.loads((D/'resumen_componentes.json').read_text(encoding='utf-8'));c=json.loads((D/'resumen_3C.json').read_text(encoding='utf-8'))
    fem=pd.concat([pd.read_csv(f) for f in D.glob('fem_h*.csv')],ignore_index=True).sort_values(['h_mm','paso'],ascending=[False,True])
    fem.to_csv(D/'convergencia_FEM.csv',index=False);hs=sorted(fem.h_mm.unique(),reverse=True)
    fine=fem[fem.h_mm==hs[-1]];prev=fem[fem.h_mm==hs[-2]]
    stress=float(fine.VM_max_MPa.max());disp=float(fine.desplazamiento_max_mm.max())
    es=abs(stress/prev.VM_max_MPa.max()-1);eu=abs(disp/prev.desplazamiento_max_mm.max()-1)
    conv=es<=.05 and eu<=.05
    mf=dict(VM_max_MPa=stress,desplazamiento_max_mm=disp,n_304_referencia=210/stress,
            convergencia_envolvente=bool(conv),cambio_VM_rel=es,cambio_u_rel=eu,
            criterio_VM=.05,criterio_u=.05,estados=sorted(fem.paso.unique().tolist()),estados_ultima_malla=fine.paso.to_list(),mallas_h_mm=hs,
            reaccion_sentido_traccion_max_n=float(fine.reaccion_axial_negativa_n.max()),
            estado='Cumple el cribado bajo hipótesis adoptadas' if conv and stress<210 else 'No cerrado: no convergencia o fluencia de referencia',aprobacion_incondicional=False)
    r['FEM']=mf;r['3C']=c;guardar('resumen_final.json',r)
    # Completar comparación separada del informe definitivo.
    comp=pd.read_csv(D/'comparacion_resultados.csv');comp=comp[~comp.resultado.str.startswith('FEM')]
    oldr=json.loads((S/'resultados/prototipo/viabilidad_funcional_2026_11_20/resumen_integrado.json').read_text(encoding='utf-8'))
    extra=[]
    for label,x,y,u in [('FEM matriz tensión',oldr['FEM_matriz']['VM_max_malla_fina_MPa'],stress,'MPa'),('FEM matriz desplazamiento',oldr['FEM_matriz']['u_max_malla_fina_mm'],disp,'mm')]:
        extra.append(dict(resultado=label,anterior=x,actualizado=y,unidad=u,variacion_pct=100*(y/x-1),estado='Recalculado por cambio de apoyo',explicacion='Matriz idéntica; apoyo de tuerca menor y nuevos casos correlacionados'))
    comp=pd.concat([comp,pd.DataFrame(extra)],ignore_index=True);comp.to_csv(D/'comparacion_resultados.csv',index=False)
    b=pd.read_csv(D/'rodamientos_608.csv');ar=r['arbol'];ma=r['manivela']
    oldb=pd.read_csv(S/'resultados/prototipo/viabilidad_funcional_2026_11_20/rodamientos_608.csv')
    nuevos=[]
    for label,x,y,unit,why in [
        ('608 carga radial máxima',oldb.Fr_max_n.max(),b.Frmax_n.max(),'N','Nuevos centros y masaCAD del rodillo'),
        ('608 factor estático mínimo',oldb.S0_referencia.min(),b.S0.min(),'1','Mismas capacidades EZO, nuevas cargas'),
        ('608 vida mínima de referencia',oldb.L10_millones_vueltas_rodillo.min(),b.L10_millones_rev.min(),'10^6rev','Mismo método V1,2 por anillo exterior'),
        ('Flecha transversal árbol',oldr['arbol']['flecha_transversal_envolvente_max_m']*1000,ar['flecha_transversal_envolvente_m']*1000,'mm','Mayor voladizo de mano y menor separación de guías'),
        ('Presión máxima apoyo matriz',oldr['matriz']['p_apoyo_max_pa']/1e6,r['matriz']['pmax_apoyo_pa']/1e6,'MPa','Reducción del área efectiva de apoyo')]:
        nuevos.append(dict(resultado=label,anterior=float(x),actualizado=float(y),unidad=unit,variacion_pct=100*(y/x-1),estado='Recalculado condicionado',explicacion=why))
    comp=comp[~comp.resultado.isin([x['resultado'] for x in nuevos])]
    comp=pd.concat([comp,pd.DataFrame(nuevos)],ignore_index=True);comp.to_csv(D/'comparacion_resultados.csv',index=False)
    # Figuras reales del historial y de geometría extraída.
    fig,axs=plt.subplots(2,1,figsize=(9,5.5),sharex=True)
    axs[0].plot(d.angulo_grados,d.fuerza_total_n);axs[0].set_ylabel('Fuerza total [N]')
    axs[1].plot(d.angulo_grados,d.torque_total_nm,color='tab:orange');axs[1].set_ylabel('Torque [N m]');axs[1].set_xlabel('Ángulo de matriz [°]')
    for ax in axs:ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(D/'fuerzas_torque.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(9,5.5),sharex=True)
    for j,color in [(1,'tab:blue'),(2,'tab:orange')]:
        axs[0].plot(d.angulo_grados,d[f'holgura_r{j}_min_m']*1000,color=color,ls='-' if j==1 else '--',label=f'R{j} borde mínimo')
        axs[0].plot(d.angulo_grados,d[f'holgura_r{j}_max_m']*1000,color=color,ls=':' if j==1 else '-.',label=f'R{j} borde máximo')
    axs[0].set_ylabel('Holgura [mm]');axs[0].legend(ncol=2,fontsize=8)
    axs[1].plot(d.angulo_grados,d.flecha_max_m*1000,label='Flecha máxima eje');axs[1].set_ylabel('Flecha [mm]');axs[1].set_xlabel('Ángulo de matriz [°]')
    for ax in axs:ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(D/'holguras_flecha.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,5.5));holes=pd.read_csv(D/'perforaciones.csv')
    for h in holes.itertuples():ax.add_patch(Circle((h.x_mm,h.y_mm),3,fill=False,lw=.6))
    ax.add_patch(Circle((0,0),49.5,fill=False));ax.add_patch(Circle((0,0),6.5,fill=False))
    for ro in a['rodillos']:
        ph=ro['angulo_rad'];x,y=ro['centro_local_matriz_mm'][:2];v=np.array([math.cos(ph),math.sin(ph)])*15
        ax.plot([x-v[0],x+v[0]],[y-v[1],y+v[1]],lw=5,label=f"Rodillo {ro['solido_id']}")
    ax.set_aspect('equal');ax.set_xlim(-52,52);ax.set_ylim(-52,52);ax.set_xlabel('x matriz [mm]');ax.set_ylabel('y matriz [mm]');ax.legend()
    fig.tight_layout();fig.savefig(D/'geometria_contacto.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(9,3.8))
    for paso,g in fem.groupby('paso'):
        axs[0].plot(g.tetraedros,g.VM_max_MPa,'o-',label=f'Estado {paso}');axs[1].plot(g.tetraedros,g.desplazamiento_max_mm,'o-')
    axs[0].set_ylabel('Máximo von Mises [MPa]');axs[1].set_ylabel('Máximo desplazamiento [mm]');axs[0].legend()
    for ax in axs:ax.set_xlabel('Tetraedros');ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0));ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(D/'convergencia_fem.png',dpi=180);plt.close(fig)
    paso=int(fine.loc[fine.VM_max_MPa.idxmax(),'paso'])
    with np.load(D/f'fem_h{hs[-1]:g}_paso{paso}.npz') as z:
        p=z['p'];tet=z['tet'];vm=z['VM'];top=abs(p[tet,1])<1e-6;ids=np.flatnonzero(top.sum(axis=1)==3);faces=np.array([tet[i][top[i]] for i in ids])
        verts=np.stack([p[faces,0],-p[faces,2]],axis=-1);fig,ax=plt.subplots(figsize=(6.2,5.5));pc=PolyCollection(verts,array=vm[ids],cmap='viridis',edgecolors='none',clim=(0,stress));ax.add_collection(pc)
        ax.set_xlim(-51,51);ax.set_ylim(-51,51);ax.set_aspect('equal');ax.set_xlabel('x matriz [mm]');ax.set_ylabel('y matriz [mm]');ax.set_title(f'FEM definitivo: estado {paso}')
        fig.colorbar(pc,ax=ax,label='Von Mises del tetraedro adyacente [MPa]');fig.tight_layout();fig.savefig(D/'FEM_matriz.png',dpi=180);plt.close(fig)
    # Cuerpo principal breve, únicamente resultados definitivos.
    tex('subseccion_verificacion_mecanica.tex',r'''\subsection{Verificación mecánica del prototipo definitivo}
La revisión utiliza el ensamble STEP definitivo y el escenario manual de
biomasa de4mm. La matriz conserva102 canales de6mm y longitud10mm;
se mantiene la presión teórica de Holm2,25867MPa y el coeficiente efectivo
de torque0,1. Se corrigió el primer momento tangencial de las intersecciones
parciales, conservando la versión histórica y sin modificar las ecuaciones
de presión ni de torque. El modelo acoplado convergió en los1440 estados.
'''+tabla(['Magnitud','Resultado definitivo'],[
        ['Fuerza total máxima',fmt(c['Fmax_n'],2)+r' N'],['Torque máximo',fmt(c['Tmax_nm'],5)+r' N\,m'],
        ['Fuerza manual ideal, radio165mm',fmt(ma['Fmax_ideal_n'],2)+' N'],['Flecha máxima del M8',fmt(c['flecha_max_m']*1000,4)+' mm'],
        ['Tensión nominal máxima del M8',fmt(c['sigma_max_pa']/1e6,2)+' MPa'],['Holguras de ambos rodillos',fmt(min(c['g1_min_m'],c['g2_min_m'])*1000,4)+'--'+fmt(max(c['g1_max_m'],c['g2_max_m'])*1000,4)+' mm'],
        ['Matriz, von Mises FEM',fmt(stress,2)+' MPa'],['Matriz, desplazamiento FEM',fmt(disp,5)+' mm']])+r'''
El eje transversal se calcula con núcleo de referencia6,466mm para
M8$\times$1,25 y doble empotramiento como condición de diseño; el cilindro
CAD de8mm no se interpreta como sección maciza resistente. Se conservan
las conclusiones resistentes condicionadas del M8 y del ABS, sin volver
a seleccionar concentradores.

Los alojamientos de los608 son ahora22mm, compatibles nominalmente con
su diámetro exterior. Con capacidades EZO de referencia y carga axial
nula en estos rodamientos, el factor estático mínimo es '''+fmt(b.S0.min(),2)+r'''
\cite{ezo_608zz_2026}. La matriz AISI304 se comprobó mediante un nuevo FEM
porque el apoyo inferior cambió a la cara de tuerca de radio9,525mm.
El cociente entre el límite de fluencia de referencia210MPa y el pico
calculado es '''+fmt(210/stress,2)+r''', condicionado a la fijación idealizada
y a la condición de material considerada\cite{outokumpu_core_2026}.

El árbol mide235mm. Sus nuevas estaciones de apoyo aumentan la envolvente
nominal de flexión, compresión y torsión a '''+fmt(ar['VM_envolvente_max_pa']/1e6,2)+r'''MPa;
su resistencia real continúa condicionada al grado y raíz del hilo corrido.
El soporte y el buje incorporados son dimensionalmente compatibles,
pero debe materializarse la retención axial del árbol dentro del buje
y la transmisión de torque en las uniones árbol--matriz--manivela.
La capacidad del rodamiento principal no se deduce de sus dimensiones.

Las cargas de compactación y el esfuerzo manual cambian muy poco; el CAD
mejora el montaje de los608, aunque modifica la flexión del árbol y el
apoyo de matriz. La conclusión de viabilidad mecánica sigue siendo
favorable bajo las hipótesis adoptadas, sin aprobar las uniones todavía
no verificadas ni declarar funcionamiento experimental. Las memorias
A.3--A.8 contienen el detalle reproducible y las limitaciones.
''')
    tex('anexo_A3.tex',r'''\subsection{Modelo de compactación y acoplamiento}
\label{app:prototipo_A3}
Se emplea exclusivamente el prototipo definitivo y biomasa de4mm.
La identidad geométrica de la matriz se contrastó por volumen,102 centros
y muestreo bidireccional de frontera, con tolerancia$10^{-5}$mm.
El radio de cada rodillo es26mm, su ancho radial30mm, sus centros están
a27,75mm del eje principal y la separación inicial es0,5mm.
El marco de cálculo se alinea con el eje transversal real, girado30grados
respecto del eje globalX; no se usan sus cajas envolventes como longitudes.
\begin{align}
 P&=\frac{P_{N0}}{\nu_{LR}}\left[\exp\left(4\mu_p\nu_{LR}L/D\right)-1\right],\\
 P_{N0}&=0,281\ {\rm MPa},\quad\nu_{LR}=0,203,\quad\mu_p=0,715,
 \quad L/D=10/6,\quad P=2,25867\ {\rm MPa}.
\end{align}
Los coeficientes y el procedimiento se conservan de EP2
\cite{equipo_entrega2_2026}; esta presión es una estimación de diseño,
no una calibración experimental de aserrín.

\subsubsection*{Áreas y centroides corregidos}
Para cada abscisa radial$r$, se recorta el segmento circular mediante
$t_-=\max(t_c-\sqrt{a^2-(r-r_c)^2},-L_c/2)$ y
$t_+=\min(t_c+\sqrt{a^2-(r-r_c)^2},L_c/2)$, donde$a=3$mm.
El ancho de huella conserva la ley empleada en el modelo previo:
\begin{equation}
 L_c(g)=\sqrt{D_R(h-g)-(h-g)^2},\qquad h=4\ {\rm mm}.
\end{equation}
Con$\ell=\max(t_+-t_-,0)$ y pesos de Gauss$w_k$:
\begin{align}
 \widetilde A&=\sum_k w_k\ell_k,\qquad A=\min(\widetilde A,\pi a^2),\\
 \bar r&=\frac{\sum_k w_k r_k\ell_k}{\widetilde A},\qquad
 \bar t=\frac{\tfrac12\sum_k w_k(t_{+,k}^2-t_{-,k}^2)
 \mathbf1_{\ell_k>0}}{\widetilde A}.
\end{align}
La corrección anula el primer momento de intervalos vacíos. La
normalización del centroide usa el área integrada antes de su recorte
numérico al área circular; el área de fuerza continúa limitada por
$\pi a^2$. Para$A=0$ el centroide no se usa. La implementación corregida
es una versión separada; el código histórico permanece intacto.
Se verificó en los1440 estados que todo centroide positivo pertenece
al disco y a la huella recortada. Se contrastaron simetría, contacto nulo
y el centroide analítico de un semidisco.

\subsubsection*{Iteración geométrica--estructural}
Para cada ángulo se recalculan$F_{ij}=PA_{ij}$ y
$T=0,1\sum_{ij}r_iF_{ij}$, manteniendo el radio de perforación empleado
por EP2. El reparto entre608 conserva fuerzas y primeros momentos.
La viga de Euler--Bernoulli devuelve desplazamientos y pendientes, y
$g_j(r)=g_0+u_j+\alpha_j(r-r_j)$ actualiza la huella.
Se mantiene relajación0,5, tolerancia de holgura$10^{-9}$m, cambio relativo
de fuerza$10^{-5}$ y máximo100 iteraciones. La solución se reevalúa antes
de aceptar convergencia. No se fuerza coincidencia con resultados previos.
'''+tabla(['Resultado','Valor'],[
        ['Estados convergidos',f"{c['convergidos']}/1440"],['Iteraciones máximas',str(c['iteraciones_max'])],['Fuerza máxima',fmt(c['Fmax_n'],3)+' N'],
        ['Fuerza media',fmt(c['Fmedia_n'],3)+' N'],['Torque máximo',fmt(c['Tmax_nm'],6)+r' N\,m'],['Torque medio',fmt(c['Tmedio_nm'],6)+r' N\,m']])+r'''
Los máximos de fuerza y torque corresponden a estados distintos;
se conservan las series completas y se evita mezclarlos al verificar.
Los contrastes de cuadratura128 y malla de viga160 divisiones se ejecutan
en32 estados con inicio independiente. Sus errores se documentan en
\texttt{validacion\_numerica\_3C.csv}; el error de discretización no debe
confundirse con el residuo de convergencia de una iteración.
'''+figura('geometria_contacto.png','.65')+figura('fuerzas_torque.png'))
    tex('anexo_A4.tex',r'''\subsection{Eje transversal M8}
\label{app:prototipo_A4}
El CAD representa un cilindro exterior8mm y longitud160mm; el diseño
adoptado es varilla M8$\times$1,25. Se conserva el núcleo resistente de
referencia$d_r=6,466$mm, $E=210$GPa, $I=\pi d_r^4/64$.
Los centros de fijación separados'''+fmt(abs(a['taladros_soporte_transversal'][1]['centro_eje_mm'][0]-a['taladros_soporte_transversal'][0]['centro_eje_mm'][0]),6)+r'''mm
se extraen de los dos taladros8mm de la cámara. Se imponen desplazamiento
y giro nulos como condición de diseño; esto no demuestra por sí solo
la rigidez real de los soportesABS o la precarga de las tuercas.
\begin{equation}
 \sigma_{b,\rm nom}=\frac{32\sqrt{M_y^2+M_z^2}}{\pi d_r^3}.
\end{equation}
'''+tabla(['Magnitud','Resultado definitivo'],[
        ['Tensión nominal máxima',fmt(c['sigma_max_pa']/1e6,3)+' MPa'],['Flecha máxima de viga',fmt(c['flecha_max_m']*1000,5)+' mm'],
        ['R1 holgura mínima/máxima',fmt(c['g1_min_m']*1000,5)+' / '+fmt(c['g1_max_m']*1000,5)+' mm'],
        ['R2 holgura mínima/máxima',fmt(c['g2_min_m']*1000,5)+' / '+fmt(c['g2_max_m']*1000,5)+' mm'],
        ['R1 desplazamiento máximo de centro',fmt(c['u1_centro_max_m']*1000,5)+' mm'],['R2 desplazamiento máximo de centro',fmt(c['u2_centro_max_m']*1000,5)+' mm']])+r'''
Las holguras de la tabla son envolventes de estados convergidos, no valores
simultáneos asociados a todos los máximos. Se conserva la clase8.8 como
candidata y$S_{y,\min}=640$MPa condicionado a conformidad del producto
\cite{boellhoff_manual_8100_2023}.
El cociente nominal$640/'''+fmt(c['sigma_max_pa']/1e6,3)+r'''='''+fmt(640e6/c['sigma_max_pa'],3)+r'''$
no incorpora concentración local de rosca y no constituye una aprobación
resistente. Se mantienen las limitaciones previamente documentadas de
seguridad estática/fatiga, sin repetir el estudio de$K_t$ ni la comparación
de diámetros. La geometría del montaje ha cambiado; los resultados de
flecha y tensión nominal se recalcularon, no se trasladaron del modelo anterior.
'''+figura('holguras_flecha.png'))
    tex('anexo_A5.tex',r'''\subsection{Rodamientos y apoyos}
\label{app:prototipo_A5}
Los cuatro608 conservan dimensiones8$\times$22$\times$7mm. Los alojamientos
de rodillo son ahora22mm y7mm axiales. El desfase axial de0,3mm coincide
con el chaflán del anillo: su tramo cilíndrico activo6,4mm queda dentro
del asiento7mm, sin una incompatibilidad de montaje por ese saliente nominal.
Se mantienen las condiciones de ajuste y retención como especificación
de fabricación, sin deducirlas del nombreSKF de la instanciaCAD.

Con la reacción normal de compactación$R_N$ guardada por3C, el peso de
rodillo$R_W$ repartido en sus centros, y la tangente efectiva del modelo:
\begin{align}
 F_r&=\sqrt{(R_N-R_W)^2+(0,1R_N)^2},\quad F_a=0,\\
 P&=1,2F_r,\quad P_0=F_r,\quad
 P_{eq}=\left[\frac1{1440}\sum P_i^3\right]^{1/3},\\
 S_0&=C_0/\max(P_0),\qquad L_{10}=(C/P_{eq})^3.
\end{align}
Las capacidades EZO de referencia son$C=3300$N,$C_0=1370$N
\cite{ezo_608zz_2026}. El factor1,2 por giro del anillo exterior se conserva
del procedimiento NHBB\cite{nhbb_vida_exterior_2026}; no se asignan esas
capacidades a unidades de compra cuya marca no se haya identificado.
La ponderación es por ángulo/revoluciones. Sin velocidad manual definida
no se convierte la vida a horas ni se predice vida experimental.
'''+tabla(['ID','Máx.$F_r$ [N]','$P_{eq}$ [N]','$S_0$','$L_{10}$ [$10^6$rev]'],[
        [str(int(x.id)),fmt(x.Frmax_n,2),fmt(x.Peq_n,2),fmt(x.S0,3),fmt(x.L10_millones_rev,1)] for x in b.itertuples()])+r'''
\subsubsection*{Apoyo del árbol principal}
Se identifican por geometría el cuerpo52, el rodamiento53 con agujero25,4mm
y el buje55 de exterior25,4mm, interior12,7mm y longitud36mm. El buje cubre
el tramo cilíndrico31,0134mm del rodamiento. La compatibilidad dimensional
no acredita su capacidad: no se dispone de$C,C_0$ ni factores axial/radial
de la referencia comercial concreta, por lo que no se inventan$S_0$ o vida.
La demanda radial del modelo manual en ese apoyo es'''+fmt(ar['Rprincipal_radial_manual_max_n'],2)+r'''N;
si recibe todo el empuje axial, debe admitir aproximadamente'''+fmt(ar['demanda_axial_soporte_n'],2)+r'''N,
incluyendo pesos de referencia de matriz y árbol. Estos valores no se
reparten axialmente entre los608 de los rodillos. Los tornillos radiales
del rodamiento actúan sobre el exterior del buje; no prueban una unión
axial entre el interior12,7mm del buje y el árbol.
''')
    mat_estado='La envolvente satisface el criterio numérico y el cribado elástico condicionado.' if conv else 'La envolvente no satisface todavía el criterio numérico; no se cierra su factor de seguridad.'
    casos_tabla=[]
    for paso in sorted(fem.paso.unique()):
        co=d[d.paso==paso].iloc[0];ff=fem[fem.paso==paso];best=ff[ff.h_mm==ff.h_mm.min()].iloc[0]
        casos_tabla.append([str(int(paso)),fmt(co.angulo_grados,2),fmt(co.fuerza_total_n,3),fmt(co.torque_total_nm,6),fmt(best.h_mm,2),fmt(best.VM_max_MPa,3)])
    tex('anexo_A6.tex',r'''\subsection{Matriz AISI304 y FEM}
\label{app:prototipo_A6}
La geometría del sólido de matriz coincide con la fuente anterior:
99mm exteriores,102 canales6mm, placa perforada10mm, cubo y filetes reales.
Se reutilizan su geometría, material de diseño y ecuaciones de elasticidad;
no se reutiliza la soluciónFEM porque el apoyo inferior es ahora la cara
de la tuerca1/2--13, sin la arandela inferior anterior.
Sus bordes circulares medidos tienen radio exterior9,525mm. La zona común
plana de apoyo está limitada por el bore de matriz6,5mm; su área es
$A_s=\pi(9,525^2-6,5^2)='''+fmt(r['matriz']['area_apoyo_m2']*1e6,3)+r'''$mm$^2$.
\begin{equation}
 p_{\min,\max}=F/A_s\mp Mr_o/I_s,\qquad
 I_s=\pi(r_o^4-r_i^4)/4.
\end{equation}
La presión máxima del equilibrio global es'''+fmt(r['matriz']['pmax_apoyo_pa']/1e6,3)+r'''MPa
y la mínima'''+fmt(r['matriz']['pmin_apoyo_pa']/1e6,3)+r'''MPa.
El contacto global permanece comprimido; ello no demuestra una distribución
unilateral completa ni la capacidad de fricción real de la unión.

\subsubsection*{Modelo y frontera}
Se importa el sólido STEP verificado en Gmsh/OCC. Se conservan placa,
agujeros, toros y filetes. En la cara plana inferior$y=26$mm del STEP
individual se incorpora una curva de mallado de radio9,525mm, sin editar
el STEP original. Se restringen los desplazamientos del anillo6,5--9,525mm,
como apoyo rígido, bilateral y adherente: la retención y el torque deben
ser efectivamente provistos por la unión. No se fija la periferia.
Se emplean$E=200000$MPa,$\nu=0,30$ y$R_{p0,2}=210$MPa para304 de
referencia H/P a20gradosC\cite{outokumpu_core_2026};$\nu$ es hipótesis
elástica. Los datos no certifican el material suministrado.

Las fuerzas de cada canal se recuperan con la integración corregida y
las holguras guardadas, sin nuevas iteraciones. Se aplican tracciones
equivalentes en paredes de canales, uniformes axialmente como hipótesis,
conservando$F_i$, fuerza total, torque y primer momento normal global.
La distribución positiva en paredes no representa un campo medido de
biomasa ni su presión radial interna. Se resuelve elasticidad3D con
tetraedros lineales, CG/PyAMG y residuo relativo objetivo$10^{-9}$.
Se estudian los estados correlacionados de máximos de fuerza y torque,
no una combinación ficticia de ambos máximos.
El refinamiento adicional de frontera de1mm permite hasta1,25mm en el
interior y se aplica solo al caso gobernante636, después de verificar
ambos casos636 y1291 hasta1,25mm. El caso de fuerza máxima1291 queda
por debajo del gobernante en esas mallas; no se repite innecesariamente.
'''+tabla(['Estado',r'$\theta$ [$^\circ$]','$F$ [N]','$T$ [N m]',r'$h_{\rm malla}$ [mm]',r'$\sigma_{VM}$ [MPa]'],casos_tabla)+tabla([r'$h_{\rm malla}$ [mm]','Tetraedros',r'Máx.$\sigma_{VM}$ [MPa]','Máx.$|u|$ [mm]'],[
        [fmt(h,2),str(int(fem[fem.h_mm==h].tetraedros.iloc[0])),fmt(fem[fem.h_mm==h].VM_max_MPa.max(),3),fmt(fem[fem.h_mm==h].desplazamiento_max_mm.max(),5)] for h in hs])+r'''
El cambio de envolvente entre las dos últimas mallas es'''+fmt(es*100,2)+r'''\% en tensión
y'''+fmt(eu*100,2)+r'''\% en desplazamiento, frente al criterio declarado5\% en ambos.
'''+mat_estado+r'''
El máximo de la malla fina es'''+fmt(stress,3)+r'''MPa y el desplazamiento máximo
'''+fmt(disp,6)+r'''mm. El cociente de referencia$210/\sigma_{VM}='''+fmt(210/stress,3)+r'''$
se limita a estos casos y a las hipótesis de fijación/material. No se ha
resuelto contacto no lineal ni el historialFEM completo. La convergencia
de una envolvente no asegura la de cada pico secundario, cuyos cambios
se tabulan por separado. La máxima suma de reacciones axiales en sentido
de tracción de la malla fina es'''+fmt(mf['reaccion_sentido_traccion_max_n'],3)+r'''N:
es un diagnóstico de la restricción bilateral, no una fuerza definitiva
para dimensionar una tuerca. El peso de matriz,aproximadamente3,97N,
se omite en el FEM frente a918N y se incluye en la demanda del apoyo axial.
'''+figura('convergencia_fem.png')+figura('FEM_matriz.png','.70'))
    tex('anexo_A7.tex',r'''\subsection{Árbol principal definitivo}
\label{app:prototipo_A7}
Se mide un diámetro exterior12,7mm y longitud235mm. Las tuercasCAD son
de familia1/2--13, coherentes nominalmente con la varilla de media pulgada;
no se considera el cilindro como evidencia de una varilla lisa ni se
deduce de esa designación el grado o diámetro mínimo resistente real.
Las estaciones medidas en el marco del solver son:
'''+tabla(['Estación','Coordenada axial [mm]'],[
        ['Guía de placa16',fmt(ar['guia_superior_y_m']*1000,4)],['Centro de agujero del rodamiento53',fmt(ar['apoyo_inferior_bore_y_m']*1000,4)],
        ['Unión manivela--árbol',fmt(ar['union_brazo_y_m']*1000,4)],['Centro de empuñadura',fmt(ar['centro_mano_y_m']*1000,4)]])+r'''
La separación entre guías es'''+fmt(ar['separacion_guias_m']*1000,3)+r'''mm.
La fuerza de mano se traslada a su unión real como fuerza y par flector,
manteniendo la excentricidad axial62mm. No se prolonga ficticiamente el
árbol hasta el centro de la mano. Las ecuaciones nominales son:
\begin{align}
 \sigma_N&=4F/(\pi d^2),&\tau_T&=16T/(\pi d^3),\\
 \sigma_{VM}&=\sqrt{\sigma_N^2+3\tau_T^2},&
 \delta_N&=FL/(EA),\quad\theta=TL/(GJ).
\end{align}
La flexión se calcula por la vigaEB de EP2 con las dos guías radiales
ideales, giros libres, y cargas/par de manivela en su estación efectiva.
Se mantiene$E=210$GPa y$\nu=0,30$ de referencia, sin atribuirles una clase
resistente. La envolvente flectora combina orientaciones posibles dentro
de un mismo estado correlacionado, sin mezclar máximos de otros ángulos.
'''+tabla(['Magnitud nominal','Resultado'],[
        ['Compresión máxima',fmt(ar['sigma_axial_max_pa']/1e6,3)+' MPa'],['Cortante de torsión máximo',fmt(ar['tau_max_pa']/1e6,3)+' MPa'],
        ['Von Mises axial--torsión, correlacionado',fmt(ar['VM_nominal_max_pa']/1e6,3)+' MPa'],['Envolvente con flexión',fmt(ar['VM_envolvente_max_pa']/1e6,3)+' MPa'],
        ['Acortamiento sobre235mm',fmt(ar['delta_axial_max_m']*1000,5)+' mm'],['Giro sobre235mm',fmt(ar['giro_max_rad']*180/math.pi,4)+' grados'],
        ['Flecha transversal de referencia',fmt(ar['flecha_transversal_envolvente_m']*1000,5)+' mm'],['Reacción radial manual, apoyo inferior',fmt(ar['Rprincipal_radial_manual_max_n'],3)+' N']])+r'''
La sección de12,7mm es la referencia nominal exterior: faltan la raíz
efectiva y el grado de la varilla para dar un factor de seguridad real,
igual que en la revisión precedente. No se traslada la clase8.8 del M8
a este árbol. Si todo el empuje se transmite por él, el apoyo debe recibir
'''+fmt(ar['demanda_axial_soporte_n'],2)+r'''N, con pesos de referencia.
El buje transmite carga axial solamente si el árbol queda retenido en él;
una coincidencia cilíndrica12,7/12,7 no demuestra esa retención.
''')
    rmlo=2/3*(9.525**3-6.5**3)/(9.525**2-6.5**2)/1000;rmup=2/3*(12**3-6.5**3)/(12**2-6.5**2)/1000
    tex('anexo_A8.tex',r'''\subsection{Accionamiento manual y uniones}
\label{app:prototipo_A8}
El radio efectivo entre ejes es165mm, medido perpendicularmente al árbol.
La manivela conserva el tramo cilíndrico recto15mm y su forma anterior;
su posición axial cambia y se incluye en A.7. Para cada estado:
\begin{equation}
 F_h=T/r_h,\qquad r_h=0,165\ {\rm m}.
\end{equation}
La fuerza ideal máxima es'''+fmt(ma['Fmax_ideal_n'],3)+r'''N.
'''+tabla(['Eficiencia mecánica hipotética',r'$F_{h,\max}$ [N]'],[
        [fmt(eta,1),fmt(ma['Fmax_ideal_n']/eta,3)] for eta in [1,.8,.6]])+r'''
Estas eficiencias no son mediciones. De forma general
$F_h=(T+T_{\text{pérdidas}})/r_h$. Un atasco no queda acotado por el torque
de operación:$T_{\rm mano}=r_hF_{\rm mano}$; no se inventa una carga máxima
de mano ni se declara resistencia al atasco.
El esfuerzo nominal del tramo recto es
\begin{equation}
 \sigma_b=32T/(\pi d_b^3)='''+fmt(ma['sigma_tramo_recto_pa']/1e6,3)+r'''\ {\rm MPa},\quad d_b=15\ {\rm mm}.
\end{equation}
No es el máximo del agujero o codo. Se conservan los pendientes de
material y unión del brazo, sin investigar nuevas alternativas.

\subsubsection*{Matriz--árbol y árbol--buje}
La tuerca inferior apoya directamente en matriz; la arandela superior
permanece. Para presión uniforme, el radio medio de cada cara anular es
$r_m=\tfrac23(r_o^3-r_i^3)/(r_o^2-r_i^2)$: se obtienen
$r_{m,\inf}='''+fmt(rmlo*1000,4)+r'''$mm y
$r_{m,\sup}='''+fmt(rmup*1000,4)+r'''$mm.
La condición global de transmisión por fricción, si ese es el mecanismo
efectivo, es
\begin{equation}
 T\leq\mu(N_{\inf}r_{m,\inf}+N_{\sup}r_{m,\sup}).
\end{equation}
Una condición conservadora con el menor radio sería
$\mu\sum N_i\geq'''+fmt(c['Tmax_nm']/rmlo,2)+r'''$N.
No se asigna una precarga o fricción no documentada. Las tuercas de familia
adecuada permiten definir ese apriete, pero el modeloCAD no lo acredita.
El FEM adherente supone que la unión resiste el torque; no verifica por
sí solo esa condición. La unión manivela--árbol también requiere un
mecanismo real de apriete o transmisión positiva; el agujero12,7mm no
basta para demostrarlo. El buje de adaptación resuelve el diámetro del
rodamiento principal, pero no se identifica un bloqueo axial positivo
del árbol al buje en el CAD.

\subsubsection*{Conclusión funcional de esta revisión}
El CAD resuelve la holgura exterior de los608 y añade un apoyo principal
con adaptación de diámetro. La fuerza de compactación y el esfuerzo
manual permanecen prácticamente iguales; la flexión del árbol y la huella
de apoyo de matriz sí cambian y fueron recalculadas. La viabilidad bajo
las hipótesis de diseño se mantiene, condicionada a materializar la
retención axial y transmisión de torque indicadas y a las condiciones
resistentes ya pendientes, sin afirmar funcionamiento experimental.
''')
    tex('anexos_A3_A8.tex','% Dentro de la sección A del documento receptor.\n\\setcounter{subsection}{2}\n'+'\n'.join(f'\\input{{anexo_A{i}}}' for i in range(3,9))+'\n')
    unidades={'10^6rev':r'$10^6$ rev','mm2':r'mm$^2$','Nm':'N m','1':'--'}
    tex('comparacion_revision.tex',r'\section*{Comparación con la revisión anterior (referencia histórica)}'+'\n'+tabla(['Resultado','Unidad','Anterior','Definitivo',r'Cambio [\%]'],[
        [x.resultado,unidades.get(x.unidad,x.unidad),fmt(x.anterior,4),fmt(x.actualizado,4),fmt(x.variacion_pct,3)] for x in comp.itertuples()]))
    estados=[dict(componente='Compactación/M8',estado='Recalculado',conclusion='1440 estados convergidos; holguras positivas, resistencia local M8 condicionada como antes'),
        dict(componente='608',estado='Recalculado',conclusion='Capacidad EZO de referencia suficiente; alojamiento22/22 compatible'),
        dict(componente='Matriz',estado='Geometría/material reutilizados, FEM recalculado',conclusion=mf['estado']),
        dict(componente='Árbol',estado='Recalculado condicionado',conclusion='Nuevas longitudes/apoyos; grado/raíz y capacidad del rodamiento principal pendientes'),
        dict(componente='Manivela',estado='Geometría reutilizada verificada; fuerza recalculada',conclusion='Radio165mm; uniones resistentes y retención del árbol al buje condicionadas')]
    pd.DataFrame(estados).to_csv(D/'estado_verificaciones.csv',index=False);guardar('conservacion_final.json',conservar())
    print(json.dumps(mf,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
