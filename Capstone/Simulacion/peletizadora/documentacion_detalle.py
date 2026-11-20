"""Tablas y redacción trazables, sin declarar aprobado lo pendiente."""
import json
import math
import re
import pandas as pd
from .informes import guardar_json

def generar(raiz,salida,config,p,resumen,resistencia,arboles):
    trazabilidad=[]
    def tr(param,valor,unidad,ecuacion,fuente,aplicacion,estado):
        trazabilidad.append(dict(parametro=param,valor=valor,unidad=unidad,ecuacion=ecuacion,fuente_exacta=fuente,aplicacion_prototipo=aplicacion,estado=estado))
    cad='resultados/prototipo/revision_ensamble_2026_11_19/ensamble_auditado.json'
    tr('PN0',281000,'Pa','P=PN0/nu*(exp(4*mu*nu*L/D)-1)','Entrega_2.pdf PDFp14 A.2.2 ec4; Detalles PDFp3 ec1; significado Stelte2011 ec1–2','Estimación de diseño','EP2 adopta parámetros rastrojo de maíz20% de Tumuluru ref9; tabla externa no inspeccionada')
    tr('nu_LR',.203,'1','Deformación transversal R por carga longitudinal L','Entrega_2.pdf PDFp14 A.2.2 ec4; Stelte2011 ec1–2','Parámetro anisótropo de biomasa, no nu del acero','Valor documental, no calibración de aserrín')
    tr('mu_pared',.715,'1','Fricción biomasa–canal','Entrega_2.pdf PDFp14 A.2.2 ec4; Detalles PDFp3 ec1','No confundir con mu efectivo de torque0,1','Valor documental; no certificar peor caso de aserrín')
    tr('L_activa',.010,'m','c=L/D','geometria_STEP.json/longitudes_cilindricas_restrictivas_mm; cad.py/extraer','Cilindro de canal, no altura26mm','CAD verificado; ocupación efectiva por pellet no medida')
    tr('D',.006,'m','c=L/D','geometria_STEP.json/diametros_efectivos_mm','Conductos102','CAD verificado')
    tr('P_Holm_CAD',p['P_CAD_pa'],'Pa','presion_canal(PN0,mu,nu,L,D)','peletizadora/verificaciones.py/presion_canal; ecuación publicada por Stelte2011','Presión uniforme como carga equivalente EP2','Estimación teórica no experimental')
    tr('PM_documento',43700000,'Pa','lambda_p=Pp/PM','Detalles PDFp3 ec1 y lambda_p; Entrega_2.pdf PDFp14 ec4 para L/D6','43,70433MPa sin redondear','43,70 y44 redondeos diferentes de misma fórmula')
    tr('PM_simulacion_EP2',44000000,'Pa','F_i=p*A_cubierta_i','../Simulación_peletizadora/config.py/Parametros; resultados/etapa_3c_acoplamiento/parametros.json','Regresión comercial intacta','Constante de modelo EP2, no calibración recuperada')
    tr('capa',[.001,.002,.004],'m','Lc=sqrt(Drod*(h-g)-(h-g)^2), h>g','Entrega_2.pdf PDFp15 ec9 y PDFp17 ec19–20; modelos/superposicion_variable.py','Sensibilidades conservadas;4mm documental del COMERCIAL','No se define capa del prototipo en Detalles; no nominal físico seleccionado')
    tr('g_CAD',.0005,'m','Altura centro menos radio rodillo',cad+'/rodillos','No equivale a capa de biomasa','CAD, no galga física')
    tr('centros_radiales',[.0278380640336,.0276619359664],'m','Transformación rígida XCAF',cad+'/rodillos','Sin escalamiento comercial','CAD verificado')
    tr('mu_efectivo',.1,'1','T=sum(mu_eff*F_i*r_i)','../Simulación_peletizadora/modelos/torque.py/contribuciones_torque_nm; escenarios previos','Solo escenarios de torque','Hipótesis, no coeficiente de Holm')
    tr('superposicion','área parcial','m2','F_i=p*A(disco intersección huella)','../Simulación_peletizadora/modelos/superposicion.py/interseccion_disco_rectangulo','1440 estados originales conservados','Cuadratura64/128 contrastada revisión previa')
    tr('reparto608','por centroide radial','N','Ra=F*(xb-xf)/(xb-xa), Rb=F-Ra','../Simulación_peletizadora/estructural/cargas_eje.py/repartir_entre_rodamientos','CentrosCAD; proyección de centroide radial, sin componente tangencial del centroide','Equilibrio bajo hipótesis de rodillo rígido y asientos resueltos')
    tr('eje_transversal','6x160','mm','K*u=f; sigma_b=M*d/(2I)','../Simulación_peletizadora/estructural/viga_eb.py/SistemaViga; '+cad,'Viga articulada en taladrosCAD, diferente del biempotramientoEP2','Apoyos rígidos hipotéticos')
    tr('d_nucleo_M6x1',.004773,'m','I=pi*d^4/64','TR Fastenings tabla Metric coarse, filaM6, URL referencias.bib/tr_rosca_m6_2026','Referencia de rosca; no medición de varilla','Verificado catálogo, pendiente producto')
    tr('E_escenarios',[180e9,205e9,220e9],'Pa','u proporcional a 1/E','configuraciones/detalle_manual.json/sensibilidad_eje; sensibilidad previa','No propiedades del grado comprado','Hipotético, sin asignar4140')
    tr('608_referencia',[3300,1370],'N','Peq=(mean(P^3))^(1/3), L10=(C/Peq)^3, L10h=1e6*L10/(60*n)','EZO608ZZ ficha oficial eid00913; ../Simulación_peletizadora/estructural/rodamientos.py','Referencia EZO; Fa0 y rodadura ideal hipotéticas, pesos angulares uniformes','Sin aprobación del producto ni asientos')
    tr('arbol_nominal',.0127,'m','sigma=4F/(pi*d²), tau=16T/(pi*d³), VM=sqrt(sigma²+3tau²)','../Analisis_matriz_eje_vertical/Etapa_4B_matriz_arbol_condicional/simulacion_etapa_4B.py; ecuaciones README','Función pura nueva, sin ejecutar runner histórico; todaF/T en sección es condicional','Sin raíz, flexión ni apoyos resueltos')
    tr('radio_manivela',.165,'m','F=T/r','Solicitud apartado5; '+cad+'/inventario/id20/cilindros','Radio entre ejes medido165mm','GeometríaCAD; mano tangente ideal')
    tr('agua','10% a12/15%','kg','m_agua=m0*(wf-w0)/(1-wf)','Ingenieria_de_Detalles.pdf PDFp1 ec2 y PDFp2 sección1.2','Base húmeda, sin evaporación ni pérdidas','Balance reproducido; humedad real pendiente')
    tr('material_impreso','ABS diseño confirmado','identidad','E_comp referencia2,20/2,16GPa; E_tracción2,40/2,30GPa','Detalles PDFpp3/2:ABS, ratificado por equipo; StratasysABS-M30 PDFpp6–7 tabla5','Propiedades típicas de referencia para condicionesF900-T16; no impresión actual','Sin selección de filamento/proceso ni validación de pieza')
    pd.DataFrame(trazabilidad).to_csv(salida/'trazabilidad_parametros.csv',index=False)
    estados=[
        ('presion','estimacion_de_diseno','Coeficientes y ecuación recuperados en EP2A.2.2 y Detalles1.1; maíz20%','Tabla original de Tumuluru, especie, temperatura, granulometría y humedad reales del aserrín'),
        ('cargas','alternativas_condicionadas','Tres capas y presión calculada; sin nominal único','Espesor alimentado, contacto/deformación, presión y mu efectivos'),
        ('manivela','equilibrio_ideal_verificado','RadioCAD165mm; F=T/r,19,727N para3,255Nm','Pérdidas, arranque, atascamiento, fuerza máxima prevista, retención y unión'),
        ('eje_M6','cribado_condicionado_critico','Flexión/corte/ciclos nominales y malla; deformación relevante respecto al gap','Grado,paso,raíz,Kt/Kf,asientos,rigidez de apoyos y validación de deformación'),
        ('608_asientos','incompatible_sin_resolver','Diferencias diametrales2mm en ambas interfaces; no adaptación identificada','Solución de montaje, tolerancias, ajustes y alineación axial'),
        ('608_vida','comparacion_referencia','EZO608ZZ C3300/C01370; Fa0 y velocidades10/30rpm de matriz hipotéticas','Marca adquirida, velocidad/ciclo, carga axial, montaje y lubricación'),
        ('arbol','seccion_lisa_condicionada','Axial+torsión correlacionadas; no asumir ausencia de flexión','Raíz/paso, material, apoyo localizador, axial y radial, geometría de uniones'),
        ('soporte_inferior','pendiente','UCF201-8/UCFL201-8 candidatos; no condición de empotramiento','Variante exacta, huella/altura, accesibilidad, capacidad radial/axial y rigidez'),
        ('matriz_FEM','no_ejecutado','CAD99/10/26,ligamento1,36; EP2 usa TET4 elástico y apoyo anular condicionado','Contacto real arandela/matriz, pretensión/retención, unión al árbol, nu/material y cargas3D locales'),
        ('uniones_tuercas','pendiente_critico','ArandelasCADØ24/13×2,5; EP2p11 compra tuercasANSI1/2 y eje1/2, pero CAD declaraM12','Reconciliar CAD con piezas1/2 documentadas; paso, longitud engranada, clase, apriete y bloqueo'),
        ('carcasa_ABS','diseno_con_referencia_condicionada','ABS confirmado; referenciasXZ/ZX, reacciones, presión proyectada y rigidez requerida','Definir filamento, orientación, relleno, paredes, contactos, fijación al bastidor y verificación de apoyo/fluencia lenta'),
        ('fatiga','no_aprobada','Ciclos firmados de fibras fijas, no envolvente escalar como alternancia','Sut,Se,Kf,Kt,acabado, vida y régimen de atascamientos'),
        ('ensayo_aserrin','protocolo_propuesto','12–15% base húmeda;500g iniciales','Especie,tamiz,humedad medida,temperatura,datos de fuerza/torque y calidad del pellet')]
    pd.DataFrame([dict(componente=c,estado=e,disponible=v,datos_pendientes=d,aprobado=False) for c,e,v,d in estados]).to_csv(salida/'estado_verificaciones.csv',index=False)
    riesgos=[
        ('P1','Montaje de rodillos y608','Resolver interfaces6/8 y22/24 antes de ensayo; no hay transferencia de carga verificable actualmente'),
        ('P1','Flexión y contacto M6','La deformación elástica hipotética puede superar0,5mm; verificar montaje, raíz y desplazamiento, sin acoplar automáticamente'),
        ('P1','Árbol y soporte inferior','Falta soporte y fijación; M12/Ø12,7 requiere reconciliar familia de rosca y retención'),
        ('P1','Unión matriz/manivela/árbol','Definir transferencia de torque y bloqueo axial; no asignar torque a tuerca sin precarga/rozamiento'),
        ('P2','CarcasaABS y bastidor','ABS confirmado para diseño; definir proceso y geometría de impresión, comprobar reacción de apoyos y rigidez'),
        ('P2','Presión y material de prueba','Validar presión/torque y efecto de humedad; aserrín no calibra coeficientes automáticamente'),
        ('P2','Matriz perforada','Definir apoyo real y material antes de FEM; refinar ligamentos y contacto con arandelas'),
        ('P2','Fatiga, aflojamiento y atasco','Sin ciclo de uso, Kf y límite de fuerza manual no se certifica duración ni resistencia al bloqueo')]
    pd.DataFrame([dict(prioridad=a,modo=b,accion=c,probabilidad=None) for a,b,c in riesgos]).to_csv(salida/'riesgos_y_pendientes.csv',index=False)
    fuentes=dict(fecha_consulta='2026-11-20',documentos_detalles_originales='Ambos PDF revisados. Detalles es imagen: PDFp3=impresa1(sección1.1), PDFp2=impresa2(resultados y1.2), PDFp1=continuación yec2; orden invertido.',
        EP2='Entrega_2.pdf: A.2.1 PDFpp13–14; A.2.2 PDFp14 ec4; A.3 PDFpp14–17; A.4 PDFpp17–21; A.5 PDFpp21–23; A.6 PDFpp24–26; A.7/A.8 PDFpp26–29; compras y prototipo PDFpp10–13.',
        remisiones_inconsistentes='Detalles cita A.1.1/A.1.2/A.1.3 y A.2.2 para resultados prototipo; en Entrega_2 esas secciones no contienen una memoria angular de prototipo. Se mapea por contenido, no se inventa anexo faltante.',
        Holm_2006='DOI10.1021/ef0503360, acceso editorial403; derivación original no leída',
        Holm_2007='DOI10.1021/ef070156l, ficha editorial/resumen consultados; no se atribuyen coeficientes al texto completo',
        Stelte_2011='Postprint DTU6337845, ecuaciones1–2 en páginasPDF3–4; significado de símbolos y limitación de proceso revisados',
        EZO='https://www.ezo-brg.co.jp/english/product/spec.php?eid=00913; fila608ZZ, C3300N,C01370N',
        TR='https://www.trfastenings.com/knowledge-base/thread-geometries/metric-coarse-standard; filaM6, P1mm, dmenor4,773mm',
        Tumuluru='Springer DOI10.1007/978-3-030-62888-8 ficha editorial consultada; tabla de parámetros no accesible. Origen maíz20% establecido por EP2p14, no validado independientemente.',
        ABS='StratasysABS-M30 PDFpp1/6/7: valores típicos, muestras negrasF900-T16 capa0,254mm; tabla5 XZ/ZX. No diseño aprobado ni material comercial seleccionado.',
        claves_existentes_reutilizadas=['stelte_presion_2011','tr_rosca_m6_2026','ezo_608zz_2026','equipo_step_prototipo_2026'])
    guardar_json(salida/'fuentes_documentales.json',fuentes)
    seccion=r'''% Sección independiente; NO modifica Overleaf. Requiere amsmath, booktabs, graphicx, biblatex.
\section{Ingeniería de detalles del prototipo manual}
\subsection{Modelo de compactación y presión}
Se adopta accionamiento manual por manivela de radio nominal y CAD $165\,\mathrm{mm}$.
El motor de $0,18\,\mathrm{kW}$ se conserva como antecedente y no como accionamiento nominal.
La decisión sigue Ingeniería de Detalles, sección1.1\parencite{equipo_detalles_prototipo_2026}.
La ecuación de Holm reproducida por Stelte et al.\ \parencite{stelte_presion_2011} permite estimar
\begin{equation}P=\frac{P_{N0}}{\nu_{LR}}\left[\exp\left(4\mu_w\nu_{LR}\frac{L}{D}\right)-1\right].\end{equation}
Los coeficientes $P_{N0}=0,281\,\mathrm{MPa}$, $\nu_{LR}=0,203$ y $\mu_w=0,715$
se recuperan de EP2, Anexo A.2.2, ecuación4\parencite{equipo_entrega2_2026}.
EP2 los adopta para rastrojo de maíz al20\,\% de humedad; su transferencia al aserrín requiere validación.
Con $L=10\,\mathrm{mm}$ y $D=6\,\mathrm{mm}$ se obtiene $P=2,25867\,\mathrm{MPa}$.
La estimación no constituye medición ni calibración del aserrín.
\subsection{Solicitaciones y accionamiento manual}
La matriz CAD tiene $102$ canales y dos rodillos $52\times30\,\mathrm{mm}$,
a radios $27,838$ y $27,662\,\mathrm{mm}$, con separación geométrica $0,5\,\mathrm{mm}$.
Se conservan tres capas supuestas como alternativas, sin seleccionar una condición nominal física.
El reparto parcial de área y los torques se obtienen del núcleo EP2 con $1440$ estados correlacionados.
La fuerza manual ideal supone aplicación tangencial y $F_h=T/0,165$; no incluye pérdidas ni atasco.
\begin{table}[ht]\centering
\begin{tabular}{rrrrr}\toprule
Capa [mm]&$F_{\max}$ [N]&$\bar F$ [N]&$T_{\max}$ [N m]&$F_{h,\max}$ [N]\\\midrule
'''
    for r in resumen:seccion+=f"{r['capa_supuesta_m']*1000:.0f} & {r['fuerza_max_n']:.2f} & {r['fuerza_media_n']:.2f} & {r['torque_max_nm']:.4f} & {r['fuerza_manual_max_ideal_n']:.2f}"+r'\\'+'\n'
    seccion+=r'''\bottomrule\end{tabular}
\caption{Alternativas condicionadas con presión teórica y $\mu_{\mathrm{ef}}=0,1$.}
\end{table}
\begin{figure}[ht]\centering
\includegraphics[width=0.85\linewidth]{cargas_y_manivela.png}
\caption{Variación angular de las cargas equivalentes y fuerza manual ideal; no representa una medición.}
\end{figure}
El cálculo anterior $3,255/0,165=19,727\,\mathrm{N}$ es aritméticamente consistente;
sus cargas se conservan como referencia documental, no como simulación del CAD actual.
Las remisiones de Detalles no coinciden con la numeración de EP2; los anexos A.2.1/A.2.2 disponibles
definen el predimensionamiento comercial y no proporcionan un historial angular del prototipo.
\subsection{Verificación de componentes}
El cribado Euler--Bernoulli del eje transversal considera apoyos articulados rígidos hipotéticos
en taladros de carcasa, conservando los centros CAD de los cuatro rodamientos.
La sensibilidad compara el cilindro liso de $6\,\mathrm{mm}$ y el núcleo de referencia
M6 por 1 de $4,773\,\mathrm{mm}$\parencite{tr_rosca_m6_2026}.
No se conocen grado, raíz real ni rigidez del montaje. La deformación calculada es relevante
respecto de la holgura, por lo que el contacto desacoplado exige revisión física.
Los asientos presentan diferencias diametrales de $2\,\mathrm{mm}$ en ambas interfaces
eje--608 y 608--rodillo. La comparación EZO\parencite{ezo_608zz_2026} no certifica los rodamientos adquiridos.
El árbol se comprueba solo como sección lisa axial--torsional condicionada;
su flexión y apoyos no están resueltos. UCF201-8 y UCFL201-8 permanecen sin selección.
\subsection{Limitaciones y validación pendiente}
No se aprueba resistencia, fatiga, unión roscada, carcasa ni soporte inferior.
Se adopta ABS para el diseño por prioridad de Detalles, ratificada por el equipo;
PLA queda como antecedente de EP2. No hay piezas impresas ni ensayos actuales.
Para comparación se usan probetas ABS-M30 F900-T16 de capa $0,254\,\mathrm{mm}$,
con módulos de compresión XZ/ZX de $2,20/2,16\,\mathrm{GPa}$\parencite{stratasys_abs_m30_0222a}.
No se trasladan como mínimos garantizados a otra impresión ni se calcula un factor de seguridad global.
No se ejecuta FEM de la matriz sin justificar contacto y retención; las figuras CAD no son FEM.
El protocolo de aserrín prescribe humedad de $12$--$15\,\%$ en base húmeda.
Para $500\,\mathrm{g}$ iniciales al $10\,\%$, alcanzar $15\,\%$ exige añadir $29,412\,\mathrm{g}$
de agua, conservando la masa seca. Faltan ensayos para validar presión, torque y calidad del pellet.
La trazabilidad, sensibilidades y verificaciones nominales se documentan en el anexo independiente.
'''
    (salida/'seccion_informe.tex').write_text(seccion,encoding='utf-8')
    anexo=r'''% Anexo independiente. Cálculos nominales; no aprobación de fabricación.
\section{Memoria de cálculo del prototipo manual}
\subsection{Presión y preparación de material}
Los argumentos de la exponencial son adimensionales; $P_{N0}$ fija la unidad de presión.
La relación CAD exacta es $10/6$; el valor redondeado $1,667$ da $2,25938\,\mathrm{MPa}$.
El cociente con $43,70\,\mathrm{MPa}$ es aproximadamente $0,0517$.
La diferencia de $0,30\,\mathrm{MPa}$ respecto a los $44\,\mathrm{MPa}$ de EP2 está identificada;
la ecuación4 de EP2 da $43,70433\,\mathrm{MPa}$ al usar $L/D=6$, justificando ambos redondeos.
El canal restrictivo CAD comercial es $31,5\,\mathrm{mm}$, mientras el predimensionamiento usa
$36\,\mathrm{mm}$; no se modifica retrospectivamente la presión44MPa de sus simulaciones.
\begin{equation}m_w=m_0\frac{w_f-w_0}{1-w_f}.\end{equation}
\subsection{Equilibrio y resistencia nominal}
\begin{align}
F_i&=P A_{i,\mathrm{cubierta}},&T&=\sum_i\mu_{\mathrm{ef}}F_i r_i,\\
R_a&=F\frac{x_b-x_F}{x_b-x_a},&R_b&=F-R_a,\\
\mathbf K\mathbf u&=\mathbf f,&I&=\frac{\pi d^4}{64},\\
\sigma_b&=\frac{32M}{\pi d^3},&\tau_{V,\max}&=\frac{16V}{3\pi d^2}.
\end{align}
La flexión máxima superficial y el corte máximo central no están co-localizados;
no se combinan sus envolventes como un estado real de von Mises.
El umbral nominal $S_{y,\mathrm{req}}=\sigma_{b,\max}$ para $n=1$ no incluye entallas ni reserva de diseño.
Los ciclos de fibra fija dan $\sigma_m=(\sigma_{\max}+\sigma_{\min})/2$ y
$\sigma_a=(\sigma_{\max}-\sigma_{\min})/2$. Un criterio posterior de Goodman requeriría
$K_f\sigma_a/S_e+K_t\max(\sigma_m,0)/S_{ut}\leq1/n$, según EP2 ecuación38, y correcciones documentadas;
no se asignan esos valores al material desconocido.
El cribado usa el rango de extremos de una vuelta en 16 direcciones fijas, no un conteo rainflow
ni daño acumulado. EP2 empleó 144 fibras y rainflow; sus resultados resistentes no se transfieren.
\begin{table}[ht]\centering\begin{tabular}{rrrrr}\toprule
Capa [mm]&$d$ [mm]&$\sigma_b$ [MPa]&$u_{\max}$ [mm]&$\Delta g_{\max}$ [mm]\\\midrule
'''
    for r in resistencia:
        if r['E_hipotetico_pa']==205e9:
            h=next(x['capa_supuesta_m'] for x in resumen if x['escenario']==r['escenario'])
            anexo+=f"{h*1000:.0f} & {r['diametro_resistente_hipotetico_m']*1000:.3f} & {r['sigma_flexion_nominal_max_pa']/1e6:.2f} & {r['flecha_resultante_max_m']*1000:.3f} & {r['cambio_holgura_contacto_max_m']*1000:.3f}"+r'\\'+'\n'
    anexo+=r'''\bottomrule\end{tabular}
\caption{Cribado elástico desacoplado, $E=205\,\mathrm{GPa}$ hipotético. No certifica régimen elástico.}
\end{table}
\begin{figure}[ht]\centering
\includegraphics[width=0.95\linewidth]{eje_flecha_y_holgura.png}
\caption{Sensibilidad de flexión y variación geométrica de holgura; no son mediciones.}
\end{figure}
La traslación de los rodamientos y su diferencia se proyectan sobre el rodillo rígido,
estimando traslación y variación de holgura en bordes; se omite deformación de matriz y carcasa.
No se itera el contacto hasta definir las interfaces y propiedades.
\subsection{Rodamientos, árbol y soporte}
\begin{align}
P_{eq}&=\left(\sum_jw_jP_j^3/\sum_jw_j\right)^{1/3},&L_{10}&=(C/P_{eq})^3,\\
L_{10h}&=10^6L_{10}/(60n),&S_0&=C_0/P_{0,\max},\\
\sigma_z&=4F/(\pi d^2),&\tau_t&=16T/(\pi d^3),\\
\sigma_{\mathrm{VM},zT}&=\sqrt{\sigma_z^2+3\tau_t^2},&p_{\mathrm{proy}}&=R/(d_h t).
\end{align}
La comparación 608 supone $F_a=0$, pesos angulares uniformes y rodadura ideal al radio central,
con velocidades de matriz supuestas de $10$ y $30\,\mathrm{rpm}$. No es vida del montaje real.
La sección de árbol supone toda la carga axial y torque en el diámetro liso CAD;
la raíz real y la flexión deben resolverse antes de una comprobación resistente.
La presión proyectada en taladros y la rigidez $k\geq R/\delta$ son requisitos condicionados;
$\delta=0,05\,\mathrm{mm}$ es presupuesto ilustrativo, no tolerancia aprobada ni módulo mínimo de ABS.
No existe factor de seguridad calculable para el producto comprado sin propiedades identificadas.
Para el diseñoABS se compara $p/E_c$ únicamente como indicador uniaxial homogéneo y
$A/L\geq k/E_c$ como requisito de un apoyo ideal a compresión. Ninguno resuelve la flexión,
contacto concentrado o anisotropía de la carcasa real; no son desplazamientos predichos de la pieza.
'''
    (salida/'anexo_calculos.tex').write_text(anexo,encoding='utf-8')
    # Exportar únicamente las claves existentes utilizadas; sin duplicarlas.
    bib=(raiz/'referencias.bib').read_text(encoding='utf-8')
    entradas=re.split(r'(?=^@)',bib,flags=re.M)
    claves=fuentes['claves_existentes_reutilizadas']
    seleccion=[e for e in entradas if any(re.match(r'@\w+\{'+k+r',',e) for k in claves)]
    nuevas=(raiz/'fisica/referencias_detalle.bib').read_text(encoding='utf-8')
    (salida/'referencias_reutilizables.bib').write_text('\n'.join(seleccion)+'\n'+nuevas,encoding='utf-8')
    wrapper=r'''\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{amsmath,booktabs,graphicx}
\usepackage[backend=biber]{biblatex}
\addbibresource{referencias_reutilizables.bib}
\begin{document}
\input{seccion_informe.tex}
\appendix
\input{anexo_calculos.tex}
\printbibliography
\end{document}
'''
    (salida/'revision_independiente.tex').write_text(wrapper,encoding='utf-8')
