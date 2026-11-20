# Síntesis técnica: sustitución del patrón escalado por CAD real

## Revisión vigente de Ingeniería de Detalles — 20-11-2026

Esta sección incorpora los documentos ahora disponibles en `Capstone/Documentacion`
y sustituye las decisiones preliminares de accionamiento y polímero de los
apartados históricos posteriores. **El diseño vigente es manual, con manivela
de 165 mm y componentes impresos previstos en ABS.** Así lo establece Ingeniería
de Detalles y lo ratificó el equipo. No se están realizando impresiones ni ensayos;
todos los resultados nuevos son análisis de diseño. El motor180W y PLA quedan
como antecedentes, sin modificar sus archivos históricos.

### Documentos, ecuaciones y decisiones recuperadas

Se revisó `Entrega_2.pdf` (75 páginas), especialmente A.2.1/A.2.2 en páginasPDF13–14,
modelo global A.3, viga/acoplamiento/fatiga A.4, rodamientos A.5, matriz A.6 y
árbol/uniones A.7/A.8. Se leyeron visualmente las tres páginas de Detalles,
porque el PDF carece de texto extraíble. Su orden es inverso: PDF3 es la página
impresa1 (sección1.1 y ecuación1), PDF2 contiene las cargas y sección1.2, y PDF1
continúa el material y presenta el balance de humedad, ecuación2.

La matriz completa `trazabilidad_parametros.csv` identifica valor, unidad,
ecuación, fuente exacta, aplicación y estado. Los archivos originales tienen
SHA256 registrados en `control/detalle_manual_2026_11_20/documentos_recibidos.json`.
Las remisiones A.1.1/A.1.2/A.1.3 y A.2.2 de Detalles **no coinciden** con el
contenido de los anexos de esta versión de EP2. A.2.1/A.2.2 disponibles son
predimensionamiento comercial y no proporcionan un historial propio del prototipo.
Se ha recuperado el contenido verificable sin inventar el anexo citado.

La presión se calcula con la función existente `presion_canal`, sin cambiar ecuaciones:

`P=PN0/nu_LR * [exp(4*mu_pared*nu_LR*L/D)-1]`.

EP2PDF14, A.2.2/ec4 adopta PN0=0,281MPa (precompresión), nu_LR=0,203
(relación de Poisson anisótropa de biomasa) y mu_pared=0,715 (fricción biomasa–acero).
EP2 atribuye estos parámetros a rastrojo de maíz al20% de humedad, citando a
Tumuluru, referencia9. Se verificó la ficha editorial de ese libro, pero no su
tabla interna; se distingue la atribución documental de la verificación externa.
La forma y el significado de la ecuación se contrastaron con el postprint de
Stelte2011, ecuaciones1–2. El texto completo de Holm2006 no fue accesible y no
se afirma haber leído su derivación original.

| Evaluación | Presión [MPa] | Interpretación |
|---|---:|---|
| Prototipo, L/D CAD exacto10/6 | 2,258671 | Estimación de diseño |
| Prototipo, L/D redondeado1,667 | 2,259376 | Reproduce2,259MPa de Detalles |
| Comercial, L/D nominal6 | 43,704330 | Redondea43,70MPa o44MPa |

Así se explica la diferencia43,70/44: son precisiones de redondeo diferentes de
la evaluación nominal. La discrepancia frente a44MPa es aproximadamente0,677%.
El cilindro restrictivo del CAD comercial mide31,5mm, mientras el predimensionamiento
usó36mm para L/D6; se registra esta diferencia y **no se recalibran** sus históricos.
Para el prototipo se utilizan10mm efectivos del canal, no26mm de envolvente.
El cociente lambda_p resulta aproximadamente0,0517.

Estos coeficientes de maíz no quedan calibrados para aserrín fino al12–15%.
No se demuestra que sean un límite superior conservador para ese material.
La humedad, especie, temperatura y granulometría pueden cambiar la presión;
tamizar para evitar puentes no prueba una reducción de presión de extrusión.

### Reconciliación de las cargas antiguas y las obtenidas con CAD

DetallesPDF2 documenta Ftotal máxima1,029kN, fuerza por rodillo586N y torque3,255N·m.
Sus factores lambda_F=0,0731 y lambda_T=0,0366, aplicados a máximos comerciales3C,
reproducen esas cifras por redondeo; el cálculo está en `consistencia_razones_antiguas.json`.
Esto respalda su consistencia numérica como referencia documental, pero no
recupera los centros, capa, holgura, huella ni estados angulares que dieron esas
razones para el prototipo. El documento tampoco define si586N es un máximo
individual o una carga simultánea. Dos máximos individuales no deben sumarse
como si ocurrieran en el mismo instante.

Se conservaron los escenarios CAD anteriores y se ajustó **solo** la presión
desde2,26MPa a2,258671MPa por proporcionalidad del mismo modelo uniforme.
No se alteró ningún parámetro para obtener1,029kN o3,255N·m. Para mu_efectivo=0,1:

| Capa supuesta [mm] | Ftotal máxima/media [N] | Tmax/Tmedio [N·m] | Fmanivela máxima/media ideal [N] |
|---:|---:|---:|---:|
| 1 | 389,305 /350,689 | 1,15663 /1,03772 | 7,010 /6,289 |
| 2 | 641,436 /603,690 | 1,93352 /1,78620 | 11,718 /10,825 |
| 4 | 927,994 /910,022 | 2,80679 /2,69189 | 17,011 /16,314 |

La revisión de presión cambia las fuerzas solo0,0588%; no explica la diferencia
principal. En la alternativa4mm la fuerza es9,82% menor y el torque13,77% menor
que las referencias documentales. La auditoría distingue:

- **Hipótesis:** capa y huella anteriores del prototipo no están especificadas;
 4mm es un antecedente comercial, no una condición nominal demostrada del prototipo.
- **Geometría:** la matriz real esØ99, noØ100; se usan centros medidos27,838/27,662mm
 y separación0,5mm. No se reutilizan centros comerciales escalados.
- **Definiciones:** área abierta absoluta sigue siendo102·pi·3²=2883,982mm²;
 aumenta la fracción de cara perforada, no esa área absoluta. Área cubierta es otra magnitud.
- **Máximos:** F yT se extraen en sus propios estados. En4mm, la suma de máximos
 individuales928,581N supera el máximo simultáneo927,994N; ambos se guardan separados.
- **Implementación/documentación:** las regresiones y equilibrio no revelan un
 error del núcleo; hay remisiones incompatibles y datos insuficientes para
 reproducir el historial anterior. No se atribuye un error geométrico específico sin evidencia.

La longitudLc conserva la aproximación y convención de EP2 (ecuaciones9/19);
no se redefine ni se multiplica para hacer coincidir las cargas. Los radios
de torque son los centros reales de cada perforación, según EP2ecuación17,
y mu_efectivo=0,1 no es mu_pared=0,715.

**No se adopta un escenario nominal físico único.** Se conserva1,029kN/3,255N·m
como referencia documental y1/2/4mm como alternativas reproducibles del CAD actual,
condicionadas al contacto y presión. Falta capa de alimentación y respuesta mecánica
para seleccionar una condición operativa.

### Manivela, eje transversal y rodamientos

La distancia perpendicular entre ejes principal y empuñadura del STEP es165mm;
no se midió desde una caja envolvente. El cálculo antiguo3,255/0,165=19,727N
reproduce19,7N. Los esfuerzos manuales de la tabla son ideales y tangenciales;
no incluyen pérdidas conocidas, arranque, fricción de apoyos, atasco o ergonomía.
No se declara facilidad de uso ni suficiencia manual experimental.

Se reutilizó la viga Euler–Bernoulli de EP2 con centrosCAD de los cuatro608 y
taladros laterales separados108,411756mm. Se estudian apoyos articulados rígidos
**hipotéticos**, no empotramientos de ABS ni rigidez infinita del apoyo ausente.
Las normales y tangenciales se reparten conservando fuerzas y momentos.
La malla se subdivide entre puntos físicos para evitar elementos casi nulos
por superposición de una retícula y posicionesCAD.

Resultados elásticos condicionados a E=205GPa (no propiedad del grado comprado):

| Capa [mm] | Diámetro resistente supuesto [mm] | Flexión nominal máxima [MPa] | Flecha global [mm] | Cambio de holgura en contacto [mm] |
|---:|---:|---:|---:|---:|
| 1 | 4,773 | 456,00 | 1,206 | 1,166 |
| 2 | 4,773 | 751,15 | 1,980 | 1,915 |
| 4 | 4,773 | 1121,97 | 2,952 | 2,854 |
| 1 | 6,000 | 229,55 | 0,483 | 0,467 |
| 2 | 6,000 | 378,13 | 0,793 | 0,767 |
| 4 | 6,000 | 564,81 | 1,182 | 1,143 |

Ø4,773 corresponde al perfilM6×1 de referencia de TR, no a raíz medida;
Ø6 es un límite comparativo de cilindro liso, no una raíz de rosca aprobada.
Los umbralesSy requeridos para n=1 son nominales y necesarios, no factores de
seguridad ni selección de grado. No se hereda4140. Se estudian E180/205/220GPa,
corte por separado y rangos de esfuerzo firmados en fibras fijas. El cribado
de extremos no es un conteo rainflow ni una vida a fatiga como la memoriaEP2.

La proyección de desplazamientos de rodamientos sobre cada rodillo rígido muestra
cambios de holgura comparables o mayores que0,5mm. Por ello el contacto
desacoplado sirve de cribado, pero no está justificado como nominal estructural
final. Las tensiones altas tampoco acreditan régimen elástico: sin grado no se
puede afirmar que la flecha real sea la de la solución lineal. Se necesita definir
asientos y rigidez antes de justificar un acoplamiento; no se importó automáticamente3C.

Se calcularon cargas individuales608 y vidas **de referencia EZO**, C3300N/C01370N,
siguiendo media cúbica y L10 de EP2. L10h usa velocidades de matriz10/30rpm
solo como sensibilidad, rodadura ideal al radio central, Fa0 y pesos angulares
uniformes. No son la vida ni la marca certificada del rodamiento comprado,
ni contemplan arranques, contaminación o un montaje con holguras sin resolver.
Permanecen las diferenciasØ6/Ø8 yØ22/Ø24 y desajustes axiales0,2–0,3mm.

### Árbol, uniones, matriz y carcasa ABS

Las secciones lisasØ12,7, suponiendo que transmiten todaF yT correlacionadas,
dan VM axial–torsional máxima5,789/9,745/14,134MPa para1/2/4mm. **No son la
comprobación real del árbol:** faltan raíz/paso, flexión, concentraciones,
geometría de apoyo y unión. La manivela añade fuerza lateral; no se sustituye
por torque puro al definir el futuro apoyo. Se entregan cargas correlacionadas
en `interfaz_arbol_soportes_manual.csv.gz`, sin inventar reacciones inferiores.

Las distancias CAD confirman proximidad de matriz–arandelas–tuercas y una
holgura radial matriz–árbol0,15mm. La matriz no toca la cámara superior (1,5mm)
ni la carcasa inferior (distancia mínima0,414mm); no corresponde empotrar su
borde en ellas. Distancia cero no demuestra área resistente ni pretensión.
Se calcula condicionalmente presión media en una arandela idealØ24/13 y el
producto mu·N mínimo para transmitir torque por fricción uniforme, sin asignar
precarga o coeficiente. EP2PDF11 documenta eje y tuercas de1/2pulgada; el CAD
declara tuercasM12. La discrepancia es de identificación/modelado, no prueba
que las tuercas compradas seanM12: hay que confirmar familia y paso reales.
Tampoco se ha definido el bloqueo de la manivela ni la retención frente al aflojamiento.
EP2PDF11 documenta ocho tuercasM6 compradas, que no se identifican como piezas
separadas del ensamble39sólidos. Deben definirse sus posiciones, arandelas,
longitudes engranadas y la transmisión a las paredes, sin asumir un empotramiento.

UCF201-8/UCFL201-8 permanecen candidatos. El soporte debe transmitir la fuerza
axial completa que corresponda (hasta927,994N en la alternativa4mm, más acciones
omitidas), fuerzas de mano y momentos según su geometría. Sin posición axial,
capacidad de empuje y retención no hay reacciones ni rigidez mínima únicas;
se entrega el requisito paramétrico k_axial>=F/delta_admisible.

El FEM de matriz previsto en EP2A.6 se recuperó metodológicamente: elasticidad3D,
TET4, cargas correlacionadas, restricciones de anillo y convergencia. Para el
prototipo falta justificar contacto matriz–arandela, pretensión, transferencia
de torque, unión al árbol y propiedades/materialidad definitivas. No se ejecutó
un FEM con apoyos ficticios ni se trasladaron las tensiones del disco comercial.
El ligamentoCAD1,36mm identifica una zona a refinar, no un factor de seguridad.

La cámaraABS participa en el camino de carga si sus taladros apoyan el eje.
Por apoyo se obtienen reacciones resultantes máximas aproximadas195/322/465N
para1/2/4mm, bajo la hipótesis de viga. La presión proyectada p=R/(d·t) en los
taladrosCAD es4,93/8,14/11,77MPa; no es la tensión local máxima del ABS.
Para un presupuesto **ilustrativo**, no aprobado, de0,05mm se requieren rigideces
secantes aproximadas3,90/6,44/9,31MN/m por apoyo.

Se incorporaron propiedades típicas de referencia StratasysABS-M30, tabla5,
probetas negrasF900-T16 con capa0,254mm: E de compresiónXZ/ZX=2,20/2,16GPa,
E de tracción2,40/2,30GPa y fluencia a tracción30,8/27,5MPa. La ficha indica
que son valores de comparación, no especificaciones ni mínimos garantizados.
Se usa p/E como indicador uniaxial y A/L>=k/E como requisito de un apoyo ideal,
sin confundirlos con deformaciones de la carcasa. No se divide resistencia de
tracción por presión de apoyo para fabricar un factor de seguridad.
Faltan filamento/proceso, relleno, paredes, orientación, contacto, rigidez de
fijaciones, anisotropía y fluencia lenta; ABS es la familia de diseño confirmada,
no una pieza ya fabricada con esas propiedades.

### Material de prueba, cierre y reproducción

Se reproduce el balance en base húmeda de DetallesPDF1/ec2:
`m_agua=m0*(wf-w0)/(1-wf)`. Para500g iniciales al10%, se añaden11,364g para12%
y29,412g para15%. El lote final a15% pesa529,412g; no se confunde masa inicial
con masa seca ni con masa final. Tamiz, especie y humedad deben verificarse en
la preparación; escoger aserrín no valida automáticamente los coeficientes de maíz.

Los riesgos prioritarios son asientos608 no resueltos, deformación del M6,
unión/retención de matriz y manivela, apoyo axial/radial del árbol y rigidez de
la cámaraABS. No se asignan probabilidades ni se aprueba el diseño para ensayo
o fabricación con estos puntos abiertos. Las referencias documentales no son
resultados experimentales.

Ejecutar `python detalle_prototipo.py` y `python herramientas/pruebas_detalle.py`.
Todas las salidas nuevas están en `resultados/prototipo/detalle_manual_2026_11_20/`.
Se incluyen secciónLaTeX, anexo, envoltorio independiente, bibliografía sin
duplicados, gráficos, trazabilidad, reconciliación, datos correlacionados y
estados de verificación. No hay motorLaTeX/Biber instalado: se validan estructura
y referencias, sin afirmar compilaciónPDF. No se modifica Overleaf, CAD, EP2,
documentos originales ni los27 escenarios previos; no hay commit o push.

Se aprobaron240 pruebas (47 del sistema unificado/detalle,66 EP2,125 transmisión
y2 integración), además de los validadores4A/4B/4D. La conservaciónSHA256 de617
archivos anteriores y de ambos PDF queda registrada. Una futura demostración
funcional del prototipo manual no validará por sí sola la resistencia, potencia
ni capacidad productiva de la máquina comercial, cuya similitud geométrica y
de proceso no se conserva íntegramente.

## Alcance y fuentes

Los dos archivos STEP del equipo se copiaron sin alterar sus nombres ni
bytes desde Downloads a `geometrias/`. Se conservaron hashes y se importaron
mediante OpenCascade. La extracción se contrastó con topología, contornos
y pertenencia al sólido, sin ajustar parámetros para producir un número
esperado de agujeros. Las funciones matemáticas de EP2 se reutilizan en
un único núcleo configurable; los modelos históricos permanecen intactos.

Los parámetros físicos se separan de la geometría. En la máquina real se
conserva la operación documentada EP2. En el prototipo se mantienen sus
componentes nominales, sin trasladar posiciones, propiedades de varillas,
presiones calibradas ni accionamiento del modelo comercial.

## Correcciones geométricas

El STEP del prototipo contiene una matriz Ø99 mm con cuerpo perforado de
10 mm y envolvente total de 26 mm por su prolongación central. El bore es
Ø13 mm. Contiene 102 canales Ø6 mm, sin avellanados cónicos identificados.
La distancia mínima entre centros es 7,36 mm y el ligamento nominal 1,36 mm.
No corresponde al patrón comercial escalado ×0,5. El ligamento 0,211 mm
anterior se retira del uso activo junto con sus cargas y gráficos derivados.

La matriz real conserva Ø200×36 mm y bore Ø50 mm con cajeado central no
circular. Sus 102 canales tienen Ø6 mm, cilindro restrictivo de 31,5 mm,
cono de 1,5 mm y boca cilíndrica Ø9×3 mm. No hay 204 agujeros: las bocas y
conos pertenecen a los mismos 102 canales. El ligamento entre cilindros es
6,422 mm y entre bocas 3,422 mm. Los pequeños cilindros parciales del cajeado
se reportan para revisar y no se cuentan como perforaciones de extrusión.

Ambas matrices tienen área efectiva de conductos de 2883,982 mm². Esto no
implica igual área cubierta por rodillos ni fuerzas equivalentes. Las
longitudes cilíndricas restrictivas dan Lcil/D=5,25 y 1,6667. No se usa la
altura total del prototipo ni se afirma que ese cociente determine por sí
solo la presión de extrusión o toda la fricción en entradas/transiciones.

Los datos se conservan en `perforaciones_STEP.csv`, `geometria_STEP.json`,
`inventario_caras.json` y `distancias_y_ligamentos.csv`. Las figuras de
aristas y sólido CAD permiten comparar con los STEP sin reconstrucción
artificial. La triangulación es visualización, no un FEM ejecutado.

## Resultado comercial y regresión

Con la cobertura desacoplada 2C, presión estimada 44 MPa, μ efectivo 0,1,
rodillos documentados y 516 rpm, se obtienen:

| Magnitud | Máximo | Media |
|---|---:|---:|
| Fuerza total [N] | 14.432,818 | 12.699,205 |
| Torque [N·m] | 91,0287 | 79,4860 |
| Potencia [W] | 4.918,770 | 4.295,058 |

Los 1440 estados se compararon por el mismo ángulo con el archivo 2C de
EP2. Los centros coinciden exactamente y los errores máximos son del orden
de 4,4·10⁻¹¹ N y 3,0·10⁻¹³ N·m. No se cambiaron parámetros para conseguir
esa coincidencia. Se mantuvieron las ecuaciones de fuerza, torque y potencia.

Las cifras históricas de 3C acoplado son menores, por su modelo diferente:
14.070,987 N, 88,924 N·m y 4.805,041 W. No se sustituyen ni se presentan
como resultado de la corrida desacoplada. La extracción CAD no modifica
las reacciones, vidas, resistencia o fatiga calculadas en los históricos.

## Prototipo: modelo preparado, cargas pendientes

La geometría está auditada, pero el STEP es de una matriz aislada. No
contiene posiciones de rodillos, apoyos, capa de biomasa ni transmisión.
Por ello no se publica una nueva fuerza, torque, potencia o flecha del
prototipo. Los valores anteriores 734,7 N y 2,306 N·m pertenecían a hipótesis
escaladas retiradas y no describen la geometría CAD actual.

Para ejecutar el mismo núcleo se necesitan centros radiales y ángulos de
rodillos con fuente de montaje, espesor/contacto documentado e hipótesis
propia de coeficiente efectivo de torque. Para potencia se necesita rpm de
matriz o reducción real desde el motor de 1350 rpm. No se conserva 516 rpm
ni se selecciona una reducción imaginaria. La presión de 2,26 MPa queda
solo como escenario preliminar condicionado, no dato experimental.

Para estructura y rodamientos faltan apoyos, asientos y adaptación M6/Ø8,
condición axial, posiciones, materiales y calidad de varillas. Las tuercas
no prueban transmisión de torque, precarga o retención suficiente por sí
solas. El 304 es previsto; el PLA impreso necesita parámetros de proceso
y geometría. No se asignan factores de seguridad ni propiedades no respaldadas.

## Sensibilidades y límites

Se contrasta cuadratura 64/128 en la corrida real sin cambiar la física.
No se repiten barridos hipotéticos de presión, posiciones, material o
transmisión del prototipo mientras falten sus datos de montaje. Los
adaptadores generales permiten evaluar casos documentados después sin
duplicar las ecuaciones. El acoplamiento comercial no se transfiere por
semejanza ni se ejecuta un FEM con restricciones inventadas.

La tabla `resultados/tabla_para_informe.csv` está preparada para una futura
memoria: distingue real/prototipo, geometría, área, longitud, escenario y
resultados. Las celdas sin cálculo quedan vacías, no cero. Las variables
estructurales nuevas permanecen pendientes. No hay conclusión de equivalencia
directa de cargas ni de seguridad por una relación de escala.

## Conservación y reproducción

Se registró la línea base antes de retirar 39 archivos del uso activo. Los
486 archivos previos se comprueban mediante SHA256, en su ubicación original
o en el archivo reversible del prototipo escalado. Las bibliografías, pruebas
y memorias históricas no se borran. Las salidas nuevas quedan separadas deEP2.

Desde `Capstone/Simulacion`, ejecutar:

```powershell
python -m pip install -r requirements.txt
python simular.py --modelo real
python simular.py --modelo prototipo
python herramientas/ejecutar_pruebas.py
python herramientas/control_cambios.py
```

El resultado del prototipo puede ser legítimamente «pendiente de datos»;
eso no es un fallo de importación. La prueba histórica 4D revisa elementos,
malla y resultados previos, no resuelve un FEM nuevo. No se redactó LaTeX,
no se modificó CAD ni se hicieron commits o push.

## Actualización vigente: ensamble físico del prototipo (19-11-2026)

Esta revisión reemplaza el estado de montaje desconocido del prototipo; los
resultados anteriores se conservan como línea base. No reemplaza la matriz
individual ni el análisis comercial y tampoco valida experimentalmente cargas.

### Evidencia geométrica

`Prototipo.stp`, fuente interna del equipo, SHA256
`673f539ad5a94baa0a41d790fd4d92e4dec35df40ca4392c66db746a2a673b83`,
declara milímetros y contiene 39 sólidos. El lector XCAF recorre instancias y
acumula transformaciones; sus centroides coinciden con la lectura global STEP.
La identificación combina superficies, dimensiones, posición y nombres.
Se reconocen matriz, dos rodillos, eje transversal, árbol principal, cuatro
envolventes 608, cámara, tolva, placas, bastidor, manivela, tuercas y arandelas.
Piezas menores de función incierta conservan su clasificación provisional.
`componentes_ensamble.csv` y `ensamble_componentes.png` relacionan sus IDs.

La matriz montada y `Matriz_prototipo.stp` coinciden: Ø99 mm, envolvente axial
26 mm, longitud cilíndrica perforada 10 mm, bore Ø13 y 102 conductos Ø6.
Se verifica transformación rígida, centros con error menor de 1,6×10⁻¹⁴ mm,
volumen relativo del orden de 10⁻¹⁶ y frontera muestreada bidireccional
(1853 puntos por sentido, tolerancia 10⁻⁵ mm). No se afirma una comparación
booleana exacta de todas las superficies. Las matrices de transformación
están en `ensamble_auditado.json`; no se presupone origen común.

| Magnitud CAD | Rodillo 1 (ID18) | Rodillo 2 (ID19) |
|---|---:|---:|
| Centro global X [mm] | 124,207960 | 68,707960 |
| Centro global Y [mm] | 69,700398 | 69,700398 |
| Centro global Z [mm] | −53,810005 | −53,810005 |
| Radio de posición [mm] | 27,838064 | 27,661936 |
| Ángulo local [rad] | −2,353422306 | 0,788170348 |
| Diámetro / ancho [mm] | 52 / 30 | 52 / 30 |
| Separación de envolvente a matriz [mm] | 0,500 | 0,500 |

Los ejes son paralelos a X global y compatibles con dirección radial. Los
centros distan 55,5 mm; existe una pequeña asimetría respecto del eje principal.
El plano de trabajo está en Y global=43,200398 mm; la normal de trabajo es
−Z en el marco local de la matriz. La figura `planta_compactacion.png` muestra
centros y huellas hipotéticas con las perforaciones reales, sin escala heredada.

### Cargas y potencia condicionadas

La separación CAD no define deformación ni espesor de biomasa. Para explorar
esa incógnita se declaran capas 1/2/4 mm, presiones 1,13/2,26/4,52 MPa y μ
0,05/0,1/0,2: 27 escenarios, cada uno con 1440 estados sin extremo duplicado.
Las intersecciones parciales reutilizan EP2; se utiliza su función de contacto
con la separación CAD y la capa supuesta. Contraste de cuadraturas 64/128:
error relativo máximo de fuerza entre 2,15×10⁻⁵ y 5,50×10⁻⁵.

Ejemplo de sensibilidad, **p=2,26 MPa y μ=0,1, ambos no validados**:

| Capa supuesta [mm] | Longitud tangencial [mm] | F total máxima [N] | F total media [N] | T máximo [N·m] | T medio [N·m] |
|---:|---:|---:|---:|---:|---:|
| 1 | 5,074 | 389,534 | 350,895 | 1,1573 | 1,0383 |
| 2 | 8,703 | 641,813 | 604,045 | 1,9347 | 1,7872 |
| 4 | 13,029 | 928,540 | 910,557 | 2,8084 | 2,6935 |

Máximos de fuerza y torque pueden ocurrir en estados diferentes; se conservan
sus índices y series completas. Estas cifras no recuperan los antiguos valores
734,7 N/2,306 N·m del modelo escalado retirado. No hay potencia operativa
determinada porque la velocidad de matriz y la reducción son desconocidas.
La manivela no acredita una transmisión motorizada. La tabla paramétrica
calcula P=Tω para velocidades supuestas y contrasta 180 W con eficiencias
mecánicas 0,60/0,80/0,95; no prueba suficiencia del motor ni arranque.

### Montaje, cribado estructural y apoyo pendiente

El eje transversal es un cilindro CAD Ø6×160 mm, no una representación de
filetes de rosca. Los taladros laterales de cámara distan 108,411756 mm.
Los centros de los cuatro 608 están en X global 56,907960; 80,507960;
112,407960 y 135,907960 mm. Se detectan dos incompatibilidades: bore608 Ø8
frente a eje Ø6, y alojamiento de rodillo Ø24×7 frente a exterior608 Ø22×7.
No hay adaptador identificado. Además, los centros axiales de asientos y
rodamientos difieren 0,2–0,3 mm. El nombre SKF del CAD no acredita compra.

`eje_M6_cribado_condicionado.csv` presenta sensibilidad de viga lineal con
apoyos puntuales rígidos hipotéticos en los taladros, fuerzas distribuidas por
equilibrio en los pares608, núcleo supuesto 4,773 mm y E=180/205/220 GPa.
No constituye verificación del montaje PLA ni de la rosca real. Ya el escenario
de capa1 mm, p=1,13 MPa, μ=0,05 y E=205 GPa produce aproximadamente
228 MPa nominales y 0,603 mm de flecha; por tanto, es necesario revisar
deformación/contacto y validez del régimen lineal antes de interpretar los
escenarios superiores. No se asignan propiedades resistentes, FS o vida L10.

El árbol principal CAD mide Ø12,7×200 mm. Las tuercas declaradas M12 requieren
confirmar familia y paso: M12 no equivale automáticamente a media pulgada.
El soporte inferior y sus tornillos no están modelados. UCF201-8/UCFL201-8
son candidatos sin selección. La placa inferior es 95×95×5 mm con bore13,
dos taladrosØ5 separados40 mm y separación de envolventes a manivela30,509 mm.
Estas cotas no garantizan que encaje un soporte comercial. Faltan plano de
variante, huella de fijación, altura axial, accesibilidad, material/resistencia
de placa, retención y transmisión al bastidor. No se impone empotramiento.

### Validación y próximos datos

Las salidas nuevas están en `resultados/prototipo/revision_ensamble_2026_11_19/`;
el modelo comercial se reproduce en su propia revisión y conserva la regresión
2C sin modificar su configuración. La suite vigente reúne 217 pruebas y los
validadores históricos4A/4B/4D. El control incremental verifica552 archivos
previos y respalda las cinco fuentes editables; el control original486 continúa.

Para una predicción física se necesitan capa/deformación y presión medidas,
biomasa y humedad, velocidad de matriz/reducción/pérdidas, solución real de
las dos interfaces608, disposición axial, grado/paso/núcleo de varillas y
propiedades/apoyos PLA. Para cerrar árbol y rodamientos se requieren soporte
inferior seleccionado, fijaciones, restricción axial y cargas correlacionadas.
No se ejecutó FEM ni se cambió CAD o diseño, y no se aprobó seguridad mecánica.
