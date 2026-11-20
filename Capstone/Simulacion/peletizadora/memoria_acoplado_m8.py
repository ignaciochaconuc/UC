"""Memoria de cálculo generada desde los resultados acoplados, sin tocar informes previos."""
from .informes import guardar_json

def generar(destino,a,c,resumen,comparaciones):
    texto=r'''% Memoria autónoma para incorporar después al informe. Requiere amsmath, booktabs y biblatex.
\section{Actualización del eje transversal: M8 y acoplamiento de contacto}
Se estudia una varilla de acero al carbono zincado M8 por1,25, comparada con M6 por1
bajo condiciones equivalentes. No se modifica el STEP ni se certifica el grado comprado.
Se emplean núcleos de referencia $6,466$ y $4,773\,\mathrm{mm}$, según la tabla de TR Fastenings\parencite{tr_rosca_m6_2026},
con $I=\pi d^4/64$. No se utiliza el área resistente a tracción como sección de flexión.
El módulo de referencia $E=210\,\mathrm{GPa}$ corresponde a acero al carbono, según SCI/BCSA\parencite{sci_acero_elastico_2026};
el recubrimiento zincado no identifica grado ni límite elástico. Se contrasta $E=200/220\,\mathrm{GPa}$.
Los pesos usan densidades de referencia y volúmenes CAD; no son masas medidas.

\subsection{Geometría y restricciones}
Se conserva la longitudCAD de $160\,\mathrm{mm}$. Ambos empotramientos se sitúan en los centros
de los taladros laterales de cámara, separados $108,411756\,\mathrm{mm}$, imponiendo traslación y giro
nulos en ambos planos. Los extremos físicos restantes están en voladizo. No se confunde esta luz
con la longitud total ni se atribuye rigidez infinita comprobada al ABS.
Los centros de rodillos y cuatro rodamientos se conservan del ensamble auditado.
El diámetro de varilla M8 es una propuesta analítica: los taladros de cámara del CAD siguen siendo
de $6\,\mathrm{mm}$. Su incompatibilidad de montaje debe resolverse sin editar aquí el diseño.
La coincidencia nominal M8 con bore608 de $8\,\mathrm{mm}$ no verifica asiento roscado,
ajuste, alineación ni apriete. El alojamiento de rodillo de $24\,\mathrm{mm}$ sigue sin ajustarse
al exterior608 de $22\,\mathrm{mm}$.

\subsection{Algoritmo recuperado de EP2, modelo3C}
Se reutilizan la integral de superposición variable y la viga Euler--Bernoulli de EP2\parencite{equipo_entrega2_2026}.
Se parametrizan su geometría, presión y condiciones de borde, sin modificar los parámetros globales comerciales.
Para cada uno de los1440estados se actualiza
\begin{align}
g_j(r)&=g_{0j}+v_{cj}+\alpha_{rj}(r-r_{cj}),\\
L_c(r)&=\sqrt{D_r\max(h-g_j(r),0)-\max(h-g_j(r),0)^2},\\
F_j&=P\sum_i A_{ij}(g_j),\qquad T=\mu_{\mathrm{ef}}\sum_{j,i}r_iP A_{ij},\\
\mathbf K\mathbf u&=\mathbf f(\mathbf g),\qquad
\mathbf s^{k+1}=(1-\lambda)\mathbf s^k+\lambda\mathbf s_{\mathrm{calc}}^k.
\end{align}
Se usan $P=2,258670672\,\mathrm{MPa}$, $\mu_{\mathrm{ef}}=0,1$ y las capas supuestas1/2/4mm,
sin seleccionar una condición nominal física. La presión es teórica y uniforme, no medida ni constitutiva.
Las fuerzas se reparten en cada par608 por equilibrio de fuerza y momento usando el centroide de área.
Los desplazamientos de sus centros determinan la traslación e inclinación del rodillo rígido.
Se transforma la pendiente global al eje radial propio de cada rodillo; no se reutilizan signos de posición comerciales.
El torque de la matriz no se aplica como torsión adicional al eje transversal.

La relajación de referencia es $\lambda=0,5$, con máximo100iteraciones por estado.
Se exige residuo de compatibilidad y cambio de perfil de holgura inferiores a $10^{-9}\,\mathrm{m}$,
y cambio relativo de las fuerzas por rodillo inferior a $10^{-5}$, con denominador mínimo1N,
como en EP2. El contacto se recalcula al final y se reverifica contra la deformación exportada.
Un estado no convergido se registra como tal y no se usa para iniciar el siguiente;
las holguras negativas se rechazan sin recortarlas para forzar solución.

\subsection{Resultados y límites}
\begin{table}[ht]\centering
\begin{tabular}{lrrrrr}\toprule
Varilla/capa&$F_{\max}$ [N]&$T_{\max}$ [N m]&$u_{\max}$ [mm]&$\sigma_{b,\max}$ [MPa]&Iter.\\\midrule
'''
    for r in resumen:
        if not r['todos_convergieron']:
            texto+=r'\multicolumn{6}{l}{Caso no completamente convergido; consultar registro.}\\'+'\n';continue
        texto+=f"{r['varilla']}/{r['capa_m']*1000:g}mm & {r['Fmax_n']:.2f} & {r['Tmax_nm']:.4f} & {r['flecha_max_m']*1000:.4f} & {r['sigma_max_pa']/1e6:.2f} & {r['iteraciones_max']}"+r'\\'+'\n'
    texto+=r'''\bottomrule\end{tabular}
\caption{Casos acoplados con fijaciones hipotéticas idénticas. Tensiones nominales elásticas, sin concentraciones.}
\end{table}
\begin{table}[ht]\centering\begin{tabular}{lrrrr}\toprule
Varilla/capa&$g_{1,\min}$&$g_{1,\max}$&$g_{2,\min}$&$g_{2,\max}$\\\midrule
'''
    for r in resumen:
        if r['todos_convergieron']:
            texto+=f"{r['varilla']}/{r['capa_m']*1000:g}mm & {r['g1_min_m']*1000:.4f} & {r['g1_max_m']*1000:.4f} & {r['g2_min_m']*1000:.4f} & {r['g2_max_m']*1000:.4f}"+r'\\'+'\n'
    texto+=r'''\bottomrule\end{tabular}\caption{Holguras convergidas en mm; envolventes angulares y radiales por rodillo.}\end{table}
La condición geométrica de holgura positiva y menor que la capa se verifica separadamente
de la aceptación funcional. No existe una banda de holgura operativa admisible documentada.
Mantener holgura positiva no significa mantener exactamente los $0,5\,\mathrm{mm}$ iniciales.
Tampoco la convergencia matemática acredita el régimen elástico real: faltan grado, límite elástico,
raíz/tolerancia de rosca, concentradores, rigidez de montaje y adaptación608.
No se presenta factor de seguridad, fatiga ni aprobación del montaje. La matriz y la carcasa
se consideran rígidas para esta iteración, no como resultado FEM.
'''
    (destino/'memoria_acoplado_M8.tex').write_text(texto,encoding='utf-8')
    conclusiones=r'''\subsection{Conclusión comparativa del eje transversal}
Los seis casos M6/M8 conservaron presión, capas y fijaciones idénticas. La comparación
no usa como referencia equivalente el M6 articulado de la revisión anterior: cambiar
empotramientos y añadir acoplamiento también modifica su respuesta.
'''
    for r in comparaciones:
        conclusiones+=f"Para la capa supuesta de ${r['capa_m']*1000:g}\\,\\mathrm{{mm}}$, M8 reduce la flecha un ${r['reduccion_flecha_porcentaje']:.2f}\\,\\%$ y la tensión nominal un ${r['reduccion_sigma_porcentaje']:.2f}\\,\\%$ frente a M6. "
    conclusiones+=r'''
La mayor rigidez reduce la apertura de holgura y aumenta ligeramente el área cubierta y las cargas convergidas;
por ello no se supone que el cambio de varilla mantenga las fuerzas fijas.
El M8 conserva holgura positiva y menor que la capa supuesta en todos los casos, bajo los
empotramientos y propiedades de referencia. No mantiene exactamente los $0,5\,\mathrm{mm}$ iniciales.
Sin tolerancia funcional admisible, resistencia del producto y rigidez de uniones no se declara
que la separación sea adecuada para el funcionamiento real ni que el eje esté aprobado.
La siguiente definición de diseño debe confirmar clase/paso/raíz de la varilla, fijaciones enABS,
asientos608, tolerancias de holgura y validación del material compactado. No se modifica CAD.
'''
    maximo=max((r['sigma_max_pa'] for r in resumen if r.get('todos_convergieron') and r['varilla'].startswith('M8')),default=None)
    if maximo is not None:
        conclusiones+=f"\nEl límite elástico tendría que superar al menos ${maximo/1e6:.2f}\\,\\mathrm{{MPa}}$ para compatibilidad nominal con la flexión elástica del caso M8 más exigente, aun sin concentradores ni reserva de diseño. Este umbral necesario no es un factor de seguridad ni certifica el material.\n"
    (destino/'conclusiones_acoplado_M8.tex').write_text(conclusiones,encoding='utf-8')
    import re
    raiz=destino.parents[2]
    fuentes_bib=[raiz/'referencias.bib',raiz/'fisica/referencias_detalle.bib',raiz/'fisica/referencias_acoplado_m8.bib']
    claves=['tr_rosca_m6_2026','sci_acero_elastico_2026','equipo_entrega2_2026'];partes=[]
    for fuente in fuentes_bib:
        for e in re.split(r'(?=^@)',fuente.read_text(encoding='utf-8'),flags=re.M):
            if any(re.match(r'@\w+\{'+k+r',',e) for k in claves):partes.append(e)
    (destino/'referencias_reutilizables.bib').write_text('\n'.join(partes),encoding='utf-8')
    instrucciones='''Revisión acoplada M6/M8 — 20-11-2026
Ejecución desde Capstone/Simulacion: python acoplado_m8.py
Pruebas: python -m pytest tests/test_acoplado_m8.py -q
Conservación: python herramientas/control_acoplado_m8.py

No se editan CAD, parámetros o resultados anteriores. La nueva sección M8 se
aplica solo al modelo analítico. El empotramiento se impone en los taladros
laterales de cámara, no en los extremos libres de la varilla160mm.
ComparaciónM6/M8: mismoE210GPa, geometría, presión, capas y condiciones de borde.
Los resultados articulados M6 anteriores no son la comparación equivalente.
MarcoCAD: compactación sobre rodillos en+Y, pesos en-Y; tangenciales opuestas
enZ. Los camposM_Y_A son pares conjugados al giro en el planoY (momento globalZ);
M_Z_A son pares del planoZ (momento global-Y), no componentes sobre esos ejes homónimos.
La memoriaLaTeX está preparada como inclusión, no compilada ni insertada en Overleaf.
Consultar fuentes.json y los archivos por escenario. MáximosF/T/esfuerzo/flecha
pueden ocurrir en estados diferentes; casos_criticos_correlacionados.csv los conserva.
Validaciones: contraste32ángulos para cuadratura64/128, relajación0,35/0,5/0,7,
malla80/160 y sensibilidadesE200/220GPa delM8. No sustituyen el barrido1440 nominal.
Material: acero al carbono zincado de referencia. Confirmar clase y producto;
no trasladar Sy/Sut del4140. Masa de varilla usa cilindro nominal como límite superior.
Fuentes de ecuaciones: EP2acoplamiento.py3C y memoriaEntrega_2.pdf A.3.6/A.4.
'''
    (destino/'LEEME.txt').write_text(instrucciones,encoding='utf-8')
    guardar_json(destino/'fuentes.json',dict(
        seccion={'url':'https://www.trfastenings.com/knowledge-base/thread-geometries/metric-coarse-standard','filas':'M6x1 d1=4,773mm; M8x1,25 d1=6,466mm','consulta':'2026-11-20','limite':'Referencia de tabla, raíz y tolerancias de varilla real pendientes'},
        elasticidad={'url':'https://steelconstruction.info/topics/design/steel-material-properties','apartado':'Other mechanical properties of steel: E210000N/mm²','consulta':'2026-11-20','limite':'Referencia para acero al carbono, no certificación de una clase de varilla'},
        densidad_varilla={'fuente':'Referencia7850kg/m3 del modeloEP2 y tabla de parámetros de acero del Handbook3 JRC indexada','limite':'Sensibilidad de masa de cilindro nominal, no medición'},
        densidad_rodillos={'fuente':'fisica/materiales.json, referenciaOutokumpu Core3047900kg/m3','limite':'Densidad de diseño, no certificado de piezas'},
        algoritmo='../Simulación_peletizadora/estructural/acoplamiento.py: tolerancias, relajación y contacto inclinado3C',
        cambios='Se eliminan geometrías/globales comerciales codificadas; se recuperan las funciones puras de contacto y EB, con matriz de influencia equivalente para eficiencia.',
        restricciones='Dos planos de taladrosCAD, traslación y giro nulos en cada plano; hipótesis de doble empotramiento',
        CAD_incompatibilidades=['M8no pasa por taladrosCADØ6: cambio físico pendiente, no ejecutado','Bore608Ø8no equivale a asiento verificado sobre roscaM8','AlojamientoØ24frente608Ø22 sigue pendiente'],
        limite_funcional='Sin banda de holgura admisible documentada: se informa positividad y contacto geométrico, no aprobación operativa.'))
