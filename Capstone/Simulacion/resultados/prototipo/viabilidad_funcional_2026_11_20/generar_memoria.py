"""Compone tablas y memoria de esta revisión desde cálculos guardados."""
from calculos import *
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def fmt(x,n=2):return f'{x:.{n}f}'.replace('.',',')


def espaciado(texto):
    protegidos=r'(\\(?:cite|texttt|label|ref|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}|\$[^$]*\$)'
    trozos=re.split(protegidos,texto)
    for i in range(0,len(trozos),2):
        t=trozos[i]
        t=re.sub(r'(?<=[a-záéíóúñ])(?=\d)',' ',t)
        t=re.sub(r'(?<=\d)(?=(?:MPa|GPa|kN|mm|N|kgf|kg|m)\b)',r'\\,',t)
        t=t.replace('EZO608ZZ','EZO 608ZZ')
        t=t.replace('AISI304','AISI 304')
        trozos[i]=t
    return re.sub(r'\$(?=(?:MPa|GPa|kN|mm|N)\b)','$ ',''.join(trozos))


def main():
    r=json.loads((D/'resumen_analitico.json').read_text(encoding='utf-8'))
    archivos=sorted(D.glob('fem_h*.csv'))
    f=pd.concat([pd.read_csv(p) for p in archivos],ignore_index=True).sort_values(['h_mm','paso'],ascending=[False,True])
    f.to_csv(D/'convergencia_FEM_completa.csv',index=False)
    hs=sorted(f.h_mm.unique(),reverse=True);fina=f[f.h_mm==hs[-1]];previa=f[f.h_mm==hs[-2]]
    cambio_vm=abs(fina.VM_max_MPa.max()/previa.VM_max_MPa.max()-1)
    cambio_u=abs(fina.desplazamiento_max_mm.max()/previa.desplazamiento_max_mm.max()-1)
    conv=(cambio_vm<=.05 and cambio_u<=.05)
    por_caso=[]
    for paso in fina.paso:
        x=fina[fina.paso==paso].iloc[0];y=previa[previa.paso==paso].iloc[0]
        por_caso.append(dict(paso=int(paso),cambio_VM_rel=abs(x.VM_max_MPa/y.VM_max_MPa-1),
                             cambio_u_rel=abs(x.desplazamiento_max_mm/y.desplazamiento_max_mm-1)))
    pd.DataFrame(por_caso).to_csv(D/'convergencia_por_caso.csv',index=False)
    sf=float(fina.VM_max_MPa.max());disp=float(fina.desplazamiento_max_mm.max())
    m=dict(mallas_h_mm=hs,criterio_VM_rel=.05,criterio_u_rel=.05,cambio_VM_ultimas=cambio_vm,
           cambio_u_ultimas=cambio_u,convergencia_envolvente_casos=bool(conv),VM_max_malla_fina_MPa=sf,
           u_max_malla_fina_mm=disp,n_304_referencia_sobre_pico=210/sf,
           n_304_validado_bajo_hipotesis=210/sf if conv else None,
           reaccion_axial_sentido_traccion_suma_max_n=float(fina.reaccion_axial_negativa_n.max()),
           aprobacion_incondicional=False,
           casos_correlacionados=sorted(fina.paso.to_list()),
           alcance_convergencia='Envolvente máxima de tres casos, no implica convergencia de cada pico secundario',
           convergencia_por_caso=por_caso,
           estado='Cumple bajo geometría, material de diseño y fijación idealizada' if conv and sf<210 else
                  'Pico local no converge al criterio; no se cierra su factor de seguridad')
    r['FEM_matriz']=m;guardar('resumen_integrado.json',r)
    b=pd.read_csv(D/'rodamientos_608.csv')
    estados=[
        dict(componente='Árbol principal',resultado='14,00 MPa axial-torsión; envolvente flexión20,31 MPa, d nominal12,7mm',
             conclusion='Falta dato indispensable',pendiente='Paso/diámetro de raíz, grado acero y apoyo axial de carga aproximada0,924kN'),
        dict(componente='608 de rodillos',resultado=f"Fr máximo{b.Fr_max_n.max():.2f}N, S0 mínimo{b.S0_referencia.min():.3f}; capacidad referencia suficiente",
             conclusion='Cumple capacidad condicionada; montaje CAD directo no cumple',pendiente='Asiento/adaptador24/22 y apoyo interior M8; marca adquirida para capacidad garantizada'),
        dict(componente='Matriz304',resultado=f'VM malla fina{sf:.3f}MPa, u{disp:.5f}mm; cociente210/VM={210/sf:.3f}',
             conclusion=m['estado'],pendiente='Realizar fijación central adherente y confirmar condición304; no FEM de contacto'),
        dict(componente='Manivela',resultado='F ideal16,85N; tramo recto15mm: flexión nominal8,39MPa',
             conclusion='Falta material y unión resistente',pendiente='Material del brazo y mecanismo que transmita2,7804Nm al árbol, sin deslizamiento'),
    ]
    pd.DataFrame(estados).to_csv(D/'estado_componentes.csv',index=False)
    a,_=entradas();g=[]
    for nombre,valor,unidad,origen in [
        ('Árbol diámetro',12.7,'mm','Sólido12, cilindro1'),('Árbol longitud',200,'mm','Sólido12'),
        ('Guía superior centroY',-14.299602054092,'mm','Placa1 taladro13'),
        ('Guía inferior centroY',-90.2905232523622,'mm','Placa9 taladro13; rodamiento no presente'),
        ('Unión brazo centroY',-132.299602054092,'mm','Sólido20, cilindro de agujero12,7'),
        ('Mano centro empuñaduraY',-194.299602054092,'mm','Sólido20, cilindro20x29'),
        ('Manivela radio entre ejes',165,'mm','Sólido20 vs eje12, método auditoría previa'),
        ('Manivela tramo recto diámetro',15,'mm','Sólido20, cilindro7; no neto de la unión'),
        ('Matriz contacto plano radio interior',6.5,'mm','MatrizSTEP, bore13'),
        ('Matriz contacto plano radio exterior',11.5,'mm','Cara8 plana y fileteR1; no usar arandelaR12 completa'),
        ('Alojamiento rodamiento',24,'mm','Rodillos18/19'),('608 exterior',22,'mm','Sólidos33-36'),
    ]:g.append(dict(parametro=nombre,valor=valor,unidad=unidad,fuente_CAD=origen))
    pd.DataFrame(g).to_csv(D/'geometria_utilizada.csv',index=False)
    # Figura de convergencia: resultados científicos calculados, no representación de un FEM inexistente.
    fig,axs=plt.subplots(1,2,figsize=(9,3.7))
    for paso,gg in f.groupby('paso'):
        axs[0].plot(gg.tetraedros,gg.VM_max_MPa,'o-',label=f'Estado {paso}')
        axs[1].plot(gg.tetraedros,gg.desplazamiento_max_mm,'o-')
    axs[0].set_ylabel('Máximo von Mises [MPa]');axs[1].set_ylabel('Desplazamiento máximo [mm]')
    for ax in axs:ax.set_xlabel('Tetraedros P1');ax.grid(alpha=.3);ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0))
    axs[0].legend(fontsize=8);fig.tight_layout();fig.savefig(D/'convergencia_matriz.png',dpi=180);plt.close(fig)
    # Mapa real de la tensión de tetraedros adyacentes a la cara de trabajo.
    from matplotlib.collections import PolyCollection
    gobernante=int(fina.loc[fina.VM_max_MPa.idxmax(),'paso'])
    with np.load(D/f'fem_h{hs[-1]:g}_paso{gobernante}.npz') as z:
        pts=z['p'];tet=z['tet'];vm=z['VM']
        top=abs(pts[tet,1])<1e-6;ids=np.flatnonzero(top.sum(axis=1)==3)
        faces=np.array([tet[i][top[i]] for i in ids])
        verts=np.stack([pts[faces,0],-pts[faces,2]],axis=-1)
        fig,ax=plt.subplots(figsize=(6,5.3))
        pc=PolyCollection(verts,array=vm[ids],cmap='viridis',edgecolors='none',clim=(0,sf));ax.add_collection(pc)
        ax.set_xlim(-51,51);ax.set_ylim(-51,51);ax.set_aspect('equal')
        ax.set_xlabel('x canónico [mm]');ax.set_ylabel('y canónico [mm]')
        ax.set_title(f'Matriz STEP: caso {gobernante}, h={hs[-1]:g} mm')
        fig.colorbar(pc,ax=ax,label='Von Mises de tetraedro adyacente [MPa]')
        fig.tight_layout();fig.savefig(D/'FEM_matriz_cara_trabajo.png',dpi=180);plt.close(fig)
    filas='\n'.join(f"{int(x.id)} & {fmt(x.Fr_max_n)} & {fmt(x.P_equivalente_n)} & {fmt(x.S0_referencia,3)} & {fmt(x.L10_millones_vueltas_rodillo,1)} \\\\" for x in b.itertuples())
    cm='\n'.join(f"{str(h).replace('.',',')} & {int(f[f.h_mm==h].tetraedros.iloc[0])} & {fmt(f[f.h_mm==h].VM_max_MPa.max(),3)} & {fmt(f[f.h_mm==h].desplazamiento_max_mm.max(),5)} \\\\" for h in hs)
    conclusion=('La matriz cumple el cribado elástico bajo estas hipótesis, con '
                f'$n_y={fmt(210/sf)}$ respecto del límite de fluencia de referencia.' if conv else
                'El pico local no satisface aún el criterio numérico; el cociente de referencia no se presenta como factor de seguridad cerrado.')
    principal=r'''\section{Ingeniería de Detalles: viabilidad mecánica del prototipo}
Se utiliza exclusivamente el escenario acoplado M8 de 4 mm de biomasa:
presión de Holm 2,25867 MPa, coeficiente efectivo de torque 0,1,
fuerza máxima 918,00 N y torque máximo 2,7804 N\,m. El accionamiento es
manual, con manivela de 165 mm; el ABS es material de diseño de carcasa.
El modelo M8 de doble empotramiento y sus conclusiones se conservan, sin
repetir la comparación de diámetros ni el estudio de concentradores.
EP2 se emplea como respaldo de equilibrio, resistencia nominal, vida de
rodamientos y elasticidad tridimensional\cite{equipo_entrega2_2026}.

\paragraph{Árbol principal.}
Para la sección nominal circular de 12,7 mm se obtienen
$\sigma_{\rm axial}=7,25$ MPa, $\tau_T=6,91$ MPa y
$\sigma_{\rm VM}=14,00$ MPa en el mismo estado de carga.
Incluyendo la flexión manual y una envolvente correlacionada del pequeño
desequilibrio de compactación, la demanda nominal es 20,31 MPa.
Con $E=210$ GPa, la compresión sobre 200 mm es 0,00690 mm y el giro
torsional 0,1545 grados. Con dos guías radiales ideales en las placas CAD,
la flecha transversal estimada es 0,0183 mm. Estos valores corresponden
al diámetro exterior liso de referencia: el producto descrito en EP2 es
hilo corrido de media pulgada. Para cerrar su resistencia faltan el paso,
diámetro de raíz y grado del acero; no se asigna un factor de seguridad
al producto desconocido. El apoyo axial debe transmitir aproximadamente
0,924 kN al bastidor, incluyendo pesos de referencia de matriz y árbol;
no aparece un rodamiento axial instalado en el STEP.

\paragraph{Rodamientos de los rodillos.}
Con las reacciones correlacionadas y los pesos de los rodillos, la carga
radial máxima es 272,47 N. Para la referencia EZO608ZZ,
$C=3300$ N y $C_0=1370$ N\cite{ezo_608zz_2026}, resulta
$S_{0,\min}=5,03$: capacidad estática suficiente bajo $F_a=0$.
Se calculó la vida básica por revoluciones con corrección por giro del
anillo exterior\cite{nhbb_vida_exterior_2026}; la mínima es
$1,253\times10^9$ revoluciones del rodillo, como referencia idealizada,
sin atribuir esa vida a los rodamientos adquiridos de marca desconocida.
No se calculan horas sin velocidad manual definida. El montaje directo
del CAD no queda operativo: alojamiento24 frente a exterior22mm deja
1mm radial sin apoyo y exige asiento/adaptador con retención definida.
El apoyo interior debe corresponder al M8 adoptado, con asiento apropiado.

\paragraph{Matriz perforada.}
Se emplea la matriz STEP de 99 mm, 102 perforaciones6mm, espesor perforado
10mm y cuerpo central real. El apoyo plano efectivo central es el anillo
de radios6,5--11,5mm. La presión máxima calculada es 3,32MPa y el
contacto permanece en compresión en el equilibrio global.
Para evaluar la flexión local se ejecutó FEM tridimensional sobre el STEP,
con cargas equivalentes por canal y fijación adherente de ese anillo,
en tres estados críticos correlacionados.
La malla más fina entrega \VALSTRESS{}MPa y \VALDISP{}mm.
La envolvente cambia\VMREF{}\% en tensión y\UREF{}\% en desplazamiento
en el último refinamiento; el anexo detalla los cambios por caso.
\VALCONCLUSION{}
El material de diseño es AISI304 con $R_{p0,2}=210$MPa de referencia para
producto plano H/P a20 grados Celsius\cite{outokumpu_core_2026}; no es un
certificado de la pieza. La fijación debe transmitir también el torque;
el FEM adherente no demuestra por sí solo que la unión real no patine.

\paragraph{Manivela y funcionamiento.}
La fuerza manual ideal máxima es $2,7804/0,165=16,85$N.
Con eficiencias supuestas de0,8 y0,6 sería21,06 y28,08N; no son pérdidas
medidas. El tramo recto CAD de15mm presenta flexión nominal8,39MPa.
Faltan el material del brazo y el mecanismo de unión al árbol para verificar
su resistencia completa; un agujero cilíndrico coincidente no garantiza
transmisión de torque. Un atasco no queda limitado al torque de operación:
$T_{\rm mano}=0,165F_{\rm mano}$. No se declara resistencia a un atasco
de magnitud desconocida.

\paragraph{Conclusión de diseño.}
La demanda manual calculada es moderada y los608 de referencia tienen
capacidad suficiente. Para disponer de un conjunto funcional deben
resolverse tres interfaces concretas: asiento de los608, apoyo axial del
árbol y transmisión/retención en las uniones matriz--árbol--manivela.
Se requieren además el grado/paso del árbol y el material del brazo.
Estas conclusiones son de cálculo, sin validación de extrusión ni de
funcionamiento experimental. El anexo documenta ecuaciones, FEM y datos
pendientes, sin alterar CAD ni modelos históricos.
'''.replace(r'\VALSTRESS{}',fmt(sf)).replace(r'\VALDISP{}',fmt(disp,5)).replace(r'\VALCONCLUSION{}',conclusion).replace(r'\VMREF{}',fmt(100*cambio_vm)).replace(r'\UREF{}',fmt(100*cambio_u))
    (D/'seccion_ingenieria_detalles.tex').write_text(espaciado(principal),encoding='utf-8')
    anexo=r'''\section{Memoria de cálculo mecánica del prototipo manual}
\subsection{Entradas y trazabilidad}
Se leen los1440 estados de
\texttt{serie\_M8x1.25\_h4mm.csv}, las auditorías geométricas del ensamble,
\texttt{Prototipo.stp} y \texttt{Matriz\_prototipo.stp}; no se ejecuta ni
modifica el acoplamiento3C. EP2, páginas PDF10--11, define el árbol como
hilo corrido zincado de media pulgada y el inoxidable304 para matriz y
rodillos. Ingeniería de Detalles, página PDF3, confirma accionamiento
manual y matriz304; página PDF2 confirma carcasaABS. Los resultados antiguos
1,029kN y3,255N\,m no se mezclan con el escenario vigente918N/2,7804N\,m.
Los archivos anteriores se verifican por SHA256.

\subsection{Árbol: axial, torsión, flexión y rigidez}
Se reutiliza la metodología nominal de EP2 y4B:
\begin{align}
 A&=\pi d^2/4,& I&=\pi d^4/64,& J&=\pi d^4/32,\\
 \sigma_N&=F/A,&\tau_T&=16T/(\pi d^3),&
 \sigma_{\rm VM}&=\sqrt{\sigma_N^2+3\tau_T^2},\\
 \delta_N&=FL/(EA),& \theta_T&=TL/(GJ),&G&=E/[2(1+\nu)].
\end{align}
Se usa la sección exterior nominal12,7mm y longitud completa200mm como
referencia de acortamiento/giro. El par se introduce en la unión del brazo
a42,009mm por debajo de la guía inferior; la mano está62mm más abajo.
La fuerza de mano se traslada a esa unión como fuerza más un par flector,
sin prolongar ficticiamente el árbol hasta la empuñadura.

Las guías ideales se sitúan en los centros de las placasCAD1 y9,
separadas75,991mm. Para la mano, el voladizo equivalente respecto de la
guía inferior es104,009mm. El equilibrio produce reacciones radiales de
39,915N en la guía inferior y23,064N en sentido contrario en la superior
para el máximo torque; no son cargas axiales ni reacciones de rodamientos
reales seleccionados. El momento manual máximo es1,7526N\,m.
Se suma, como envolvente de orientaciones posibles en cada mismo estado,
el momento normal de compactación y el efecto de su resultante tangencial
desequilibrada. La máxima demanda nominal equivalente es20,31MPa.

La flecha de0,0183mm proviene de la formulación Euler--Bernoulli de EP2,
con ambos desplazamientos radiales restringidos en las guías, giros libres,
y superposición de fuerzas y pares correlacionados. El acero se modela
con $E=210$GPa y $\nu=0,30$ como referencias elásticas, sin convertirlas
en una clase resistente. El modelo ideal de guía no equivale al contacto
real de un hilo corrido dentro de un taladro.
Como cribado de estabilidad, para200mm y longitud eficaz conservadora
$KL=400$mm resulta $P_{cr}=\pi^2EI/(KL)^2=16,54$kN sobre la sección lisa.
No es un factor de seguridad de pandeo de la varilla roscada.

Los requisitos mínimos nominales quedan explícitos:
$S_y\geq20,31$MPa para $n_y\geq1$ en la envolvente calculada;
para un material conocido, $n_y=S_y/\sigma_{\rm VM}$ se evaluará con
el diámetro resistente real y geometría de la unión. El zincado no define
$S_y$. No se trasladan al árbol los640MPa candidatos del eje transversal.

El apoyo axial debe cerrar el camino matriz--árbol--bastidor o proporcionar
un camino alternativo explícito. La fuerza máxima de compactación es918N;
los pesos de referencia de matriz304 y árbol de acero suman5,92N, de donde
se obtiene una demanda aproximada924N. Los608 de rodillos no constituyen
el apoyo axial del árbol12,7mm. Las tuercas M12 nombradas en CAD no son
equivalentes a las de media pulgada documentadas en compras; comprobar
paso real de las tuercas de media pulgada, sin tratar M12 como pieza seleccionada.

\subsection{Rodamientos608: cargas y capacidades}
Se importan las cuatro reacciones normales del3C; no se reparten918N en
cuatro partes iguales. Se añade el peso de cada rodillo,4,143N con densidad
de referencia7900kg/m$^3$, repartido según sus centrosCAD. En cada rodamiento:
\begin{align}
 F_r(t)&=\sqrt{[R_N(t)-R_W]^2+[0,1R_N(t)]^2},\\
 P(t)&=1,2F_r(t),&P_0(t)&=F_r(t),\\
 P_{eq}&=\left[\frac1{1440}\sum P(t)^3\right]^{1/3},&
 L_{10}&=(C/P_{eq})^3,&S_0&=C_0/\max(P_0).
\end{align}
La ponderación es por ángulo/revoluciones, no una velocidad manual
constante supuesta. Se adopta $F_a=0$ en la dirección del eje del rodillo;
la fuerza normal de compactación es radial para estos rodamientos.
El factor1,2 corresponde al anillo exterior giratorio respecto de la carga
según el procedimiento publicado por NHBB\cite{nhbb_vida_exterior_2026},
como estimación conservadora de referencia, no una atribución de fórmula
particular a EZO. Se emplean las capacidades oficiales EZO608ZZ
\cite{ezo_608zz_2026}; la marca de las unidades extraídas de ruedas sigue
sin identificar.
\begin{center}\begin{tabular}{rrrrr}\toprule
ID&$F_{r,\max}$[N]&$P_{eq}$[N]&$S_0$&$L_{10}$[$10^6$rev]\\\midrule
\FILAS608{}
\bottomrule\end{tabular}\end{center}
La conversión a revoluciones de manivela usa rodadura ideal al radio
central del rodillo; no se publica vida en horas ni vida real de servicio
sin velocidad, lubricación, contaminación y montaje definidos.
Las capacidades de referencia no resuelven el alojamiento24/22:
sin adaptador/asiento, la pista exterior no transmite correctamente
la reacción ni mantiene la holgura de operación.

\subsection{Matriz: apoyo y necesidad de FEM}
La placa perforada de10mm incluye ligamentos mínimos1,36mm y una transición
toroidal al cubo; no se sustituye por un disco macizo uniforme de26mm.
La cara de arandela inferior realmente plana es el anillo6,5--11,5mm,
área282,743mm$^2$; el filete exterior limita el contacto plano antes de
alcanzar el radio12mm de la arandela. Con $I_a=\pi(r_o^4-r_i^4)/4$:
\begin{equation}
 p_{\min,\max}=\frac{F}{\pi(r_o^2-r_i^2)}\mp\frac{Mr_o}{I_a}.
\end{equation}
Para los1440 estados, $p_{\min}\geq3,054$MPa y $p_{\max}\leq3,320$MPa.
La excentricidad máxima0,09195mm es menor que el núcleo central3,7935mm.
Este equilibrio justifica un apoyo comprimido, pero no calcula la flexión
local de los ligamentos; por eso se ejecuta un FEM acotado, siguiendo la
elasticidad3D de EP2, con geometría propia del prototipo.

\subsection{FEM ejecutado y comprobaciones numéricas}
Se importó el sólido de \texttt{Matriz\_prototipo.stp} con OpenCASCADE de
Gmsh4.15.2, incluyendo102 agujeros, cubo, toros y filetes existentes.
Se ensamblaron tetraedros lineales de elasticidad isotrópica con
scikit-fem12.0.2, gradiente y tensor de tensiones por elemento; solución
CG con precondicionador de elasticidad PyAMG5.4.1, residuo relativo objetivo
$10^{-9}$. Las unidades son N,mm,MPa. Se adoptan $E=200000$MPa,
$\nu=0,30$ y $R_{p0,2}=210$MPa para304 de referencia: $E$ y resistencia
se respaldan en Outokumpu H/P\cite{outokumpu_core_2026}; $\nu$ es hipótesis
elástica del modelo, no propiedad certificada del producto.

\textbf{Condición de borde:} desplazamientos nulos en la cara plana del
anillo de arandela en $y_{CAD}=26$mm. Representa un apoyo rígido y adherente
con torque transmitido por la unión; no se supone que la matriz esté
soldada a toda la carcasa ni se restringe su periferia. El soporte axial
y el apriete que evitan deslizamiento deben materializarse; no fueron
modelados la tuerca, contacto con fricción ni el ABS. La suma de reacciones
axiales en sentido de tracción en la malla fina alcanza\RNEG{}N.
Es diagnóstico de la fijación bilateral idealizada: debe existir retención
o precompresión, y no se interpreta esa suma como fuerza definitiva de una
tuerca. La presión global media positiva no demuestra por sí sola que
todo punto de contacto unilateral permanezca cerrado.

\textbf{Cargas:} se recuperaron las áreas por canal mediante las holguras
y pendientes ya guardadas, sin iterar ni actualizar3C. El total de fuerzas
y el torque se contrastaron con el estado original. Se distribuyeron
tracciones axiales y tangenciales equivalentes sobre las paredes reales
de los canales, con reparto uniforme a lo largo de su longitud como
idealización; no se aplica presión a nodos inexistentes dentro de agujeros.
Esta idealización de tracciones no reproduce un campo local de presión
radial ni el comportamiento de biomasa dentro del canal.

Se detectó una inconsistencia del centroide tangencial de intersecciones
parciales del legado: algunos centroides individuales quedan fuera del
círculo de3mm. En el estado476, por ejemplo, el canal12 tiene3,898N y
distancia9,024mm entre su centro y el centroide calculado. El código de
integración del primer momento tangencial incluye contribuciones de
intervalos verticales vacíos; el área y el primer momento radial usan
altura recortada. \textbf{No se corrigió ni reejecutó el3C histórico.}
En el FEM se conserva cada fuerza de canal y el primer momento global
del estado, usando distribuciones positivas sobre las paredes con un
pequeño desplazamiento común de los centroides equivalentes. No se
interpretan los centroides parciales imposibles como puntos físicos.
La tabla de cargas de cada malla deja trazabilidad de esta regularización.
La presión de Holm y las fuerzas/torques importados no se sustituyen.

Se estudiaron los estados críticos correlacionados476,541 y625
(máximos de fuerza/torque, fuerza de rodillo y momento de normales).
No se combinaron máximos de estados diferentes ni se ejecutó un FEM de
los1440 estados. Los resultados resistentes se circunscriben a estos
casos representativos. La convergencia se evalúa sobre la envolvente
máxima de esos mismos casos, con tolerancias declaradas5\% para tensión
y5\% para desplazamiento entre las dos últimas mallas.
\begin{center}\begin{tabular}{rrrr}\toprule
$h$[mm]&Tetraedros&$\max\sigma_{VM}$[MPa]&$\max|u|$[mm]\\\midrule
\MALLAS{}
\bottomrule\end{tabular}\end{center}
Cambios de las dos últimas mallas: tensión\CAMBIOVM{}\% y
desplazamiento\CAMBIOU{}\%. \CONCLUSION{}
La convergencia de la solución discreta no valida automáticamente
la fricción, el apriete o la representación local de cargas de biomasa.
La tabla \texttt{convergencia\_por\_caso.csv} registra también los cambios
de cada caso individual: la convergencia de la envolvente no implica que
cada pico secundario haya alcanzado el mismo5\%. El factor publicado
se refiere a la envolvente calculada, no a una cota matemática de todos
los estados angulares ni a una certificación de tensiones locales reales.
\begin{center}\includegraphics[width=.95\linewidth]{convergencia_matriz.png}\end{center}
\begin{center}\includegraphics[width=.70\linewidth]{FEM_matriz_cara_trabajo.png}\end{center}
El mapa muestra el valor del tetraedro adyacente a cada triángulo de la
cara de trabajo, sin alisado nodal. El peso propio de la matriz,3,97N,
se omite en el FEM frente a918N de compactación; se incluye como demanda
adicional del apoyo axial. La deformación de matriz no se realimenta
al3C histórico en esta revisión.

\subsection{Manivela, pérdidas y uniones}
Se verifica el equilibrio $F_h=T/r_h$ para $r_h=0,165$m.
El máximo ideal16,851N corresponde a aproximadamente1,72kgf, sin convertir
ese valor en una recomendación ergonómica. Para pérdidas se publica
$F_h=T/(\eta r_h)$ con $\eta$ explícitamente hipotética, o de forma
general $F_h=(T+T_{\rm pérdidas})/r_h$. Sin pérdidas medidas no se declara
una fuerza real de accionamiento. Los atascos no se limitan por el
torque nominal calculado; faltan carga máxima manual admisible y capacidad
de las uniones para verificar esa condición.

En el tramo recto circular15mm se estima
$\sigma_b=32T/(\pi d^3)=8,391$MPa. El valor no describe el máximo en
agujero de unión, cambios de sección o codos. La fuerza tangencial
equivalente sobre la interfaz12,7mm es $2T/d=437,86$N. Falta el material
del brazo y la forma de transmitir el torque al árbol; no basta declarar
coincidencia de diámetros de agujero y eje.

Para la matriz--árbol por fricción, el radio de referencia de contacto
uniforme es $r_m=\frac23(r_o^3-r_i^3)/(r_o^2-r_i^2)=9,2315$mm.
Una condición necesaria global es
\begin{equation}
 \mu r_m\sum N_i\geq2,7804\,{\rm N\,m},\qquad
 \mu\sum N_i\geq301,19\,{\rm N}.
\end{equation}
Se deben considerar las caras realmente comprimidas. No se asigna
coeficiente de fricción ni precarga arbitraria. Una unión positiva
alternativa requeriría su propia geometría y resistencia, no seleccionada
en esta entrega. Un apoyo axial deslizante también introduce pérdidas;
especificar su superficie o elemento rodante antes de dar por operativo
el conjunto.

\subsection{Cierre proporcionado al objetivo funcional}
Los datos indispensables se limitan a: grado/paso del árbol; material y
unión de manivela; asiento y retención de608; apoyo axial del árbol y
apriete/retención de matriz. No se exige certificación industrial ni se
abre una comparación de nuevos motores, materiales o diámetros del M8.
La demanda es numéricamente compatible con accionamiento manual, pero no
demuestra extrusión estable ni montaje funcional sin resolver esas
interfaces. Los modelos y fuentes originales quedan intactos.
'''.replace(r'\FILAS608{}',filas).replace(r'\MALLAS{}',cm).replace(r'\CAMBIOVM{}',fmt(100*cambio_vm)).replace(r'\CAMBIOU{}',fmt(100*cambio_u)).replace(r'\CONCLUSION{}',conclusion).replace(r'\RNEG{}',fmt(float(fina.reaccion_axial_negativa_n.max()),3))
    (D/'anexo_memoria_mecanica.tex').write_text(espaciado(anexo),encoding='utf-8')
    print(json.dumps(m,ensure_ascii=False,indent=2))
    guardar('conservacion_final.json',conservar())


if __name__=='__main__':main()
