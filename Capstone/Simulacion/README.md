# Simulación unificada de la peletizadora

Arquitectura vigente desde el **19-11-2026**. Las matrices STEP son la fuente
geométrica principal. No se modifican EP2, sus memorias, configuraciones ni
resultados históricos. La implementación escalada de ayer se retiró del
uso activo mediante archivo reversible: véase [AUDITORIA.md](AUDITORIA.md).

## Instalación y ejecución

Desde `Capstone/Simulacion`:

```powershell
python -m pip install -r requirements.txt
python simular.py --modelo real
python simular.py --modelo prototipo
python -m pytest tests -q
# Regresión completa en procesos separados:
python herramientas/ejecutar_pruebas.py
python herramientas/control_cambios.py
```

Se usa **OpenCascade mediante cadquery-ocp 7.9.3.1.1**, instalado y probado
con Python 3.14 de 64 bits. La dependencia incluye el binding y VTK; no
requiere Inventor ni licencia CAD. Puede instalarse en un entorno virtual
si se prefiere. No sustituir un error de importación por coordenadas
inventadas o por el CSV escalado retirado.

Para otra revisión explícita de parámetros, conservar la anterior:

```powershell
python simular.py --modelo prototipo --config configuraciones/prototipo.json --salida resultados/prototipo_revision_2
```

El comando del prototipo **sí termina correctamente**, pero por ahora genera
auditoría geométrica y pendientes, no una simulación operativa ficticia.
No se admite sobrescribir una carpeta con otra configuración o con un STEP
de hash diferente. Los dos comandos principales actualizan la tabla de
comparación a partir de sus respectivos resúmenes guardados.

## Estructura

```text
Simulacion/
  geometrias/             Matriz_real.stp y Matriz_prototipo.stp
  configuraciones/       real.json y prototipo.json; sin coordenadas manuales
  fisica/                propiedades, condiciones y materialidad
  peletizadora/
    cad.py               extracción y auditoría OpenCascade
    legado.py            acceso de solo lectura a funciones puras de EP2
    nucleo.py            un único modelo angular parametrizado
    verificaciones.py    viga, rodamientos, presión y balance con datos explícitos
    informes.py          tablas y visualización de topología CAD
  herramientas/          inventario, conservación y diagnósticos CAD
  control/               estado previo y lista exacta del retiro reversible
  resultados/
    real/                geometría auditada y corrida desacoplada
    prototipo/           geometría auditada y datos pendientes
    comparacion_modelos.csv
    tabla_para_informe.csv
  tests/
  simular.py
```

La carpeta `Capstone/Prototipo` contiene solo un aviso de migración.
Sus 39 archivos científicos previos se conservan sin alteraciones en
`Capstone/archivo/Prototipo_escalado_2026_11_18/`. No deben interpretarse
sus resultados como resultados actuales. Se preservaron también pruebas,
fuentes y documentación; no se efectuó borrado irreversible. La verificación
de los **486 archivos anteriores** comprueba sus hashes originales o los
de su destino archivado.

## Geometría extraída y validada

| Magnitud | Real | Prototipo |
|---|---:|---:|
| Diámetro exterior | 200 mm | **99 mm**, no 100 mm |
| Altura axial total | 36 mm | **26 mm**, incluye prolongación central |
| Espesor de zona perforada | 36 mm | 10 mm |
| Agujero central | 50 mm, cajeado no circular | 13 mm |
| Conductos independientes | 102 | 102 |
| Diámetro efectivo | 6 mm | 6 mm |
| Longitud cilíndrica restrictiva | 31,5 mm | 10 mm |
| L cilíndrica / D | 5,25 | 1,6667 |
| Bocas de entrada | Ø9 mm y cono | No se detectan conos |
| Distancia mínima entre centros | 12,422 mm | 7,360 mm |
| Ligamento cilíndrico mínimo | 6,422 mm | **1,360 mm** |
| Ligamento entre bocas | 3,422 mm | 1,360 mm |
| Área abierta efectiva de conductos | 2883,982 mm² | 2883,982 mm² |

Las cantidades resultan de la topología, **no de imponer 102 agujeros**.
Cada conducto real tiene cilindro restrictivo de 31,5 mm, transición
cónica de 1,5 mm y boca cilíndrica de 3 mm. Se agrupan por eje/centro y se
comprueban como canales pasantes. Los 102 conos no son otros 102 agujeros.
El conteo se contrasta con círculos de contorno independientes en las dos
caras; las aristas partidas de una misma circunferencia se unen, no se
cuentan por separado. Los dos pequeños cilindros parciales del cajeado
central del real se reportan para revisión, no como agujeros de extrusión.

En el prototipo hay cuatro superficies toroidales de redondeo y una
prolongación central. **No usar los 26 mm como longitud de extrusión**.
La altura de la zona perforada sigue siendo 10 mm. Las discrepancias se
guardan antes de calcular cargas; las declaraciones históricas no se editan.

Los dos sólidos declaran milímetros. El marco local es dextrógiro:
`x=XCAd, y=−ZCAD, z=YCAD`. La transformación exacta y el origen están en
el JSON. No define por sí sola orientación de rodillos o del ensamble.
CSV en mm; ecuaciones de carga en SI: m, N, Pa, N·m, W y s.

El ligamento anterior de 0,211 mm era consecuencia del patrón escalado
retirado y **no corresponde al STEP del prototipo**. Se verificaron
duplicados, diámetro efectivo, unidades y pertenencia al sólido. El nuevo
1,36 mm es una distancia geométrica, no un margen de resistencia aprobado.

## Qué se ejecutó

### Máquina real

Se mantienen los parámetros documentados de EP2: dos rodillos Ø100×40 mm,
centro radial 63,5 mm, capa de biomasa de 4 mm, presión estimada 44 MPa,
coeficiente efectivo de torque 0,1 y velocidad de matriz 516 rpm. La
configuración conserva la fuente de esas hipótesis, sin derivarlas del STEP.

Se ejecuta la cobertura parcial desacoplada equivalente al modelo **2C**,
con 1440 estados sin duplicar el extremo 360°. La intersección disco–huella,
el torque y la potencia reutilizan las funciones originales de EP2.

| Resultado | Máximo | Media |
|---|---:|---:|
| Fuerza total | 14.432,818 N | 12.699,205 N |
| Fuerza por rodillo, máximo individual / media | 8.249,372 N | 6.349,603 N |
| Torque | 91,0287 N·m | 79,4860 N·m |
| Potencia a 516 rpm | 4.918,770 W | 4.295,058 W |

El máximo individual de un rodillo no se suma con el del otro como si
ocurrieran juntos. Se guardan completos los estados correlacionados de
máxima fuerza y máximo torque.

La geometría coincide con los centros históricos: distancia máxima 0 mm.
La diferencia de fuerza frente a 2C es aproximadamente 4,4·10⁻¹¹ N y la de
torque 3,0·10⁻¹³ N: orden de suma/redondeo. No se ajustaron parámetros.
No confundir esta corrida con **3C acoplado**: sus valores históricos
14.070,987 N, 88,924 N·m y 4.805,041 W siguen conservados y corresponden a
otra hipótesis de contacto/deformación. No son el objetivo de regresión de
un cálculo desacoplado. Tampoco se cambia 516 rpm por las 517,857 rpm de 5A.

Se contrasta cuadratura 64/128 y se verifica suma de fuerzas y P=Tω. Los
resultados numéricos de convergencia se guardan, sin presentarlos como
validación experimental. No se vuelve a ejecutar el FEM ni las etapas 3C/3D.

### Prototipo

Se completó importación, clasificación, medición y auditoría geométrica.
Se conservan motor Siemens de 180 W/1350 rpm, rodillos Ø52×30 mm, M6 de
100 mm, árbol nominal de 12,7 mm, cuatro 608ZZ y materiales previstos.
**No se heredan centro radial 31,75 mm, capa 2 mm, montaje a ras, mu=0,1
ni reducciones hipotéticas de la implementación retirada.**

Faltan datos concretos para ejecutar cargas:

- Centro radial de cada rodillo respecto al eje de matriz, con datum.
- Ángulo/orientación de cada rodillo o corte de montaje confirmado.
- Huella/capa de biomasa y condición de contacto, con fuente.
- Hipótesis propia del coeficiente efectivo de torque.
- Velocidad de matriz o relación real de transmisión para calcular potencia.

Las posiciones permanecen en `null`, junto con una bandera de contacto no
documentado. Aunque se complete la geometría de la matriz, el sistema no
puede inferir esos datos. Si se aportan después, completar explícitamente
una revisión de configuración y su fuente, y usar otra carpeta de salida.
Si la velocidad sigue pendiente, el núcleo puede entregar cargas/torque
angulares pero deja tiempo físico y potencia pendientes, no en cero.

## Presión, materiales y verificaciones

Se conservan **44 MPa como estimación histórica** y **2,26 MPa solo como
escenario preliminar condicionado**. No se recuperó una memoria EP2 con
PN0, fricción de pared y parámetros de biomasa suficientes para recalcular
presión con las longitudes CAD. La función de canal publicada por Stelte
et al. se conserva con argumentos explícitos; no se invoca con constantes
inventadas. El coeficiente de fricción de extrusión, el coeficiente efectivo
de torque y el Poisson de biomasa permanecen separados. L/D no basta para
deducir presión, potencia, calidad de pellet o comportamiento de arranque.

`fisica/materiales.json` distingue propiedades de referencia y producto
real. El 304 es previsto, no certificado; zincado no identifica grado de
varilla; no hay propiedades isótropas garantizadas para PLA impreso. Las
referencias verificadas anteriores se migraron sin cambiar sus fechas de
consulta, y se añadieron las fuentes internas STEP y la documentación OCP.

Los adaptadores compartidos de viga y rodamientos exigen segmentos,
propiedades, apoyos, cargas y fabricante explícitos. Para el prototipo
siguen pendientes asiento M6/608Ø8, apoyos, engrane/retención por tuercas,
propiedades de varillas y PLA y condición axial. No se calculan factores
de seguridad ni vidas de la pieza adquirida desconocida. El acoplamiento
3C no se traslada automáticamente. El FEM de matriz y las reacciones de
apoyos tampoco se ejecutan con restricciones inventadas.

## Entregables y trazabilidad

Cada carpeta contiene parámetros utilizados, hash del STEP, dimensiones,
perforaciones y sus caras asociadas, distribución radial/angular, todos los
pares de distancias/ligamentos, comparación con lo declarado, inventario de
caras, entidades para revisión, contornos CAD y visualización 3D. La malla
de esa figura solo visualiza el sólido: **no es FEM**.

La carpeta real incluye historial angular, resumen y regresión por estado.
La carpeta del prototipo incluye pendientes, sin fuerzas ficticias. El CSV
`resultados/tabla_para_informe.csv` usa celdas vacías para magnitudes no
calculadas, nunca ceros. Los modelos no son equivalentes por escala.

`version_codigo.json` identifica código y entradas mediante SHA256, versión
Python y OCP. `validaciones.json` y `conservacion_historica.json` registran
controles por configuración. `control/` conserva el estado previo y el plan
de retiro. No se hacen commits, push, cambios de CAD ni edición de memorias
históricas. Véanse [AUDITORIA.md](AUDITORIA.md) y
[INFORME_TECNICO.md](INFORME_TECNICO.md).

La verificación vigente reúne **15 pruebas nuevas + 193 históricas = 208
pruebas aprobadas**, además de los validadores de matriz 4A, 4B y 4D. El
log completo queda en `resultados/pruebas_ejecutadas.json`. Una prueba
adicional con sólidos sintéticos de uno y dos conductos demuestra que el
extractor no impone 102 y que marca familias diferentes para revisión; esos
sólidos de prueba no sustituyen los STEP del equipo.

## Revisión vigente: ensamble del prototipo, 19-11-2026

Los apartados anteriores describen la línea base conservada. Ahora el mismo
ejecutable importa `geometrias/Prototipo.stp` mediante XCAF, conserva las
transformaciones de instancia y verifica la matriz contra su STEP individual.
Las posiciones se incorporan a `parametros_utilizados.json`; los parámetros
declarados, con las incógnitas físicas sin rellenar, se guardan por separado.

```powershell
python simular.py --modelo prototipo
python simular.py --modelo real
python herramientas/pruebas_ensamble.py
python herramientas/control_ensamble.py
```

La salida vigente es `resultados/{modelo}/revision_ensamble_2026_11_19/`.
Las salidas anteriores permanecen intactas. La comparación nueva se guarda
en `resultados/revision_ensamble_2026_11_19/`. El modelo real conserva su
configuración y su regresión contra 2C, que no es el modelo acoplado 3C.

El ensamble contiene 39 sólidos. Los rodillos son Ø52×30 mm, con radios de
posición 27,838064 y 27,661936 mm y separación geométrica de 0,500 mm respecto
de la cara de trabajo. Esa separación **no es una capa de biomasa medida**.
Se ejecutan 27 escenarios de 1440 estados con capas supuestas de 1/2/4 mm,
presiones de 1,13/2,26/4,52 MPa y μ efectivo de 0,05/0,1/0,2. Se reutilizan
las integrales parciales y el modelo de torque de EP2; no se calibra presión.
La velocidad y potencia reales siguen pendientes. `potencia_parametrica.csv`
explora velocidades explícitas y eficiencias mecánicas, sin atribuir 1350 rpm
a la matriz. No se identifica transmisión motorizada en el ensamble.

`ensamble_auditado.json`, `componentes_ensamble.csv`, `posiciones_rodillos.csv`
y los gráficos de planta y aristas documentan las geometrías y piezas ambiguas.
`historial_escenarios.csv.gz` conserva los estados correlacionados.
El cribado lineal del eje M6 usa apoyos rígidos **hipotéticos** en los centros
de taladros CAD, núcleo M6×1 de escenario y módulos elásticos de sensibilidad;
no verifica la rigidez del PLA, el grado ni las entallas de la varilla.
No se asignan factores de seguridad ni vidas a los rodamientos.

El montaje no está resuelto: eje Ø6/608 Ø8 y 608 Ø22/alojamiento Ø24 presentan
dos diferencias diametrales de 2 mm. No se reconoce adaptador. El eje CAD mide
160 mm, frente a los 100 mm nominales anteriores. El apoyo inferior del árbol
Ø12,7 y sus tornillos están ausentes: UCF201-8 y UCFL201-8 siguen como candidatos.
Las tuercas CAD declaradas M12 requieren revisar compatibilidad con Ø12,7.
Consúltese el informe para resultados, condiciones y datos pendientes.

La suite vigente reúne 24 pruebas unificadas y 193 históricas (217), además
de los validadores 4A/4B/4D. El registro nuevo queda en
`resultados/revision_ensamble_2026_11_19/pruebas_ejecutadas.json`.
Se verifican por SHA256 los 552 archivos de la línea base incremental;
las cinco fuentes autorizadas tienen respaldo previo y los resultados y CAD
históricos están protegidos. El control original de 486 archivos sigue activo.
