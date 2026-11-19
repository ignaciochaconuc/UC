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
