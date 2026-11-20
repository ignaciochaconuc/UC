# Síntesis técnica: sustitución del patrón escalado por CAD real

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
