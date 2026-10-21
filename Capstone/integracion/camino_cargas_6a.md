# 6A — Camino de cargas, alcance y prioridades

Auditoría de archivos existentes, no cálculo resistente nuevo. Las rutas de
las tablas son relativas a Capstone. `inventario_componentes.csv/json`
contiene función, acción, evidencia, geometría, comprobaciones, datos y
clasificación por componente. «No confirmado» significa que no se encontró
un detalle verificable en las fuentes revisadas, no que la pieza no exista.

## Esquema mecánico documentado

```text
Motor candidato (no seleccionado)
  → unión eje–polea motriz [CAD45/38 incompatible; propuesta55/38]
  → tres correas → polea conducida → unión al árbol vertical
  → árbol → unión matriz–árbol → matriz → biomasa → rodillos
                                                        ↓
          anillos exteriores / elementos rodantes / anillos interiores
                                                        ↓
                     asientos del eje transversal fijo
                                                        ↓
                contactos y fijaciones de extremos (por definir)
                                                        ↓
                 soportes / carcasa / bastidor (por definir)

Rama de reacción de matriz:
matriz → cara de apoyo / retención reales (no confirmadas)
       → árbol vertical → apoyo axial/localizador y apoyos radiales
       → alojamientos / carcasa → bastidor

Rama de reacción de correa:
poleas → eje del motor / árbol → apoyos → base y estructura
```

Las flechas de potencia y las de reacción no significan que todo el torque
o todas las fuerzas crucen cada pieza de la misma manera. El contacto entre
biomasa y matriz/rodillos produce acciones opuestas: normal, distribución
descentrada y componentes tangenciales. Las cargas que son normales a la
matriz son principalmente transversales al eje de rodillos y longitudinales
al árbol vertical. Debe transformarse cada vector al marco de su unión.
No sumar como acciones externas independientes todos los pares internos
matriz–rodillos y motor–correas. La estructura debe cerrar ese lazo además
de transmitir peso y acciones externas a sus apoyos.

Evidencia: 3A–3D y4A en `Simulación_peletizadora/README.md`,4B–4D de matriz
y `Transmision/resultados/etapa_5f/interfaz_eje_vertical.json`. Las superficies
de contacto, mecanismos de torque y apoyos reales siguen siendo condiciones
pendientes; el esquema no los convierte en piezas confirmadas.

## M24×2, tuercas y unión del eje transversal

El plano `Simulación_peletizadora/Plano_eje_transversal.png` muestra dos
roscasM24×2-6g, eje270mm y tramos extremos29mm. No muestra una especificación
de tuerca, arandela, apoyo o bloqueo que permita certificar el ensamblaje.
Los29mm no equivalen a longitud engranada útil. La representación equivalente
Ø21,5463mm de3A/3D analiza flexión nominal, no resistencia de filetes.

El eje es estacionario. Las reacciones radiales de sus rodamientos no pasan
automáticamente a ser una tracción axial en cada tuerca. En4A se adoptóFa=0
por ausencia de una acción axial documentada, no porque se haya demostrado
que cualquier precarga de montaje sea nula. Deben separarse:

- Cortante y momento de extremos del eje: salen del historial estructural
  correlacionado3C, no de dividir la fuerza total entre dos o cuatro.
- Fuerza axial de apriete: solo existe como valor de diseño si la función
  de la unión exige una precarga y el montaje la permite.
- Presión bajo tuerca/arandela/soporte: requiere identificar superficies
  reales y fuerza que las comprime; no basta usar la fuerza radial del rodillo.
- Arrancamiento de filetes externos e internos, tracción de sección roscada,
  resistencia de tuerca y aflojamiento: requieren engrane útil, materiales,
  tolerancias, carga axial justificada, longitud de apoyo y bloqueo.

Es posible que el cortante pase por contacto eje–taladro o que una unión
apretada requiera fricción; no se elige una opción sin corte de montaje.
Una tuerca apretada por sí sola no demuestra empotramiento capaz de
transmitir los momentos de3A/3C. Si el soporte solo proporciona apoyo
articulado, las conclusiones de rigidez, holgura y fatiga necesitan revisión
posterior autorizada; no se modifica esa hipótesis durante esta auditoría.

3D ya contiene estática/fatiga y sensibilidad a entallas/material Ovako
específico. No se recomienda repetirla como primer paso. Primero se define
la unión y raíz real, y se confirma condición/certificado de la barra; los
factores condicionales publicados no prueban la tuerca ni el soporte.

## Incompatibilidad de los1,6mm

Con ancho de anillo16mm, el rodamiento exterior izquierdo centrado59,5mm
ocupa51,5–67,5mm, pero su asiento útil comienza53,1mm. El derecho centrado
210,5mm ocupa202,5–218,5mm y el asiento termina216,9mm. Ambos anillos tienen
1,6mm sobre un alivioØ29,2 frente a asientoØ30. Fuentes: config_eje.py y
sección de montaje4A del README de rodillos.

No es un solape axial entre rodamientos ni prueba de un empuje sobre tuerca.
Es una discontinuidad del soporte cilíndrico del anillo: se debe confirmar
si es intencional y aceptable con el fabricante o corregir el detalle.
También revisar hombros, radios, chaflanes, ancho real de pista y ajuste.
No declarar automáticamente la vida4A inválida, pero sí condicionada al
montaje, alineación y cargas de borde que ese cálculo no incluye. Resolver
primero por geometría, no iniciar FEM ni un nuevo barrido de vidas.

## Matriz, unión y apoyos verticales

4B/4C documentan boreØ50 y resalteØ58; contacto anular completo y torque
solo por fricción son hipótesis, no mecanismos verificados. El chavetero
visible de matriz no define por sí solo dimensiones activas ni fijación.
Faltan retención superior, contacto real, precarga si se necesita y ajuste.

El FEM4D **sí existe** y se revisó documentalmente; no se ejecuta de nuevo.
Su anillo bilateral, sector tangencial artificial y geometría sin
avellanados/chavetero completo no verifican la unión ni la retención.
Las reacciones axiales negativas diagnosticadas por4D no se convierten en
una carga definitiva de tuerca. Primero definir contacto unilateral y la
retención positiva real; después hacer una comprobación básica de equilibrio,
contacto y torque. Convergencia local/FEM completo puede quedar como detalle,
siempre que el informe no presente resistencia final aprobada.

El `config_apoyos.json` vertical deja centros y apoyo axial ennull. Los118mm
de caras del conjunto transversal no definen separación de rodamientos
verticales. Tampoco el croquisl3=343,3mm fija la distancia entre apoyos.
6208-2RS es mención documental previa; la ficha6208-2RS1 citada no constituye
selección comprobada. C yC0 no son capacidades axiales admisibles directas.

Una vez obtenido el corte, priorizar: reacciones radiales/axiales con estados
simultáneos de matriz y correa, definición localizador/flotante o apoyo de
empuje, capacidad/vida y retención del apoyo crítico, y sección gobernante
del árbol. No dividirFz por dos sin modelo. La interfaz5F aporta fuerzas de
correas condicionadas y signos; falta transformación espacial, alturas y
acciones de peso. No mezclar el motor nominal externo con historial3C.

## Transmisión, estructura y fijaciones

5F no aprobó la transmisión. Se conserva el cubo motrizCAD45/38 y propuesta
55/38, así como discrepancia34°/38° de garganta conducida. Completar solo
los bloqueos de selección/montaje: interferencia de aligeramientos, unión
por chaveta/retención, admisible radial del motor y bloqueo de base móvil.
ElM5 radial no tiene capacidad de torque/retención atribuida. La envolvente
de cubo62 no es longitud activa. No repetir la comparación50/55/60.

La base móvil5C es propuesta de recorrido60mm, no soporte dimensionado;
BEVIB3/B14 y MarathonB14 no definen la misma fijación. Para predimensionar
su bloqueo y anclajes se requiere motor/montaje, peso, resultante de correas,
guías y geometría. Repartir entre tornillos exige DCL, no división arbitraria.

No se encontró en las fuentes revisadas un plano completo de bastidor con
perfiles, espesores, materiales, soldaduras y anclajes que cierre los
empotramientos supuestos. Primero solicitar conjunto y definir esquema de
apoyo. Verificar estáticamente los soportes/uniones que sostienen las
reacciones críticas es básico; optimizar bastidor o dimensionar todo cordón
sin esquema no lo es. Resguardos y acceso seguro requieren concepto antes
del cierre; sus detalles constructivos pueden esperar. No se inventan
tornillos, seguros, pasadores o soldaduras como instalados: solicitar BOM
y calcular únicamente los que transmitan acciones críticas confirmadas.

## Alcance propuesto6B y puerta de entrada

1. **6B.0, revisión de conjunto:** cortes y datum de eje transversal,
   rodamientos, matriz/árbol y carcasa. Resolver1,6mm y función deM24.
2. **6B.1, unión transversal:** DCL, apoyo/rigidez de soporte, tuercasM24,
   presión de apoyo y retención/precarga solo si es su función real.
3. **6B.2, unión matriz–árbol:** transmisión de torque, contacto y retención
   bajo cargas correlacionadas; comprobación básica con geometría real.
4. **6B.3, apoyos verticales:** reacciones, reparto axial y selección crítica
   con posiciones confirmadas e interfaz5F, sin rehacer contacto3C.
5. **6B.4, cierre de estructura:** capacidad/rigidez de las uniones que
   sostienen ambos caminos de reacción. Completar bloqueos de transmisión
   por proveedor/montaje como condición de cierre, no nuevo diseño.

No iniciar estos cálculos con cotas inferidas. Si faltan entradas,6B debe
dejar la comprobación pendiente. No se requiere una campaña FEM nueva para
esta puerta de ingeniería básica, ni repetir simulaciones ya trazables.
Fatiga detallada tras fijar entallas reales, vida ajustada, desgaste y
validación experimental quedan para detalle salvo que se pretenda aprobar
una condición no cubierta por los resultados actuales.

## Hallazgo de consistencia documental

La lectura actual de1440 estados `modelo=inclinacion` da máximoFz
14070,987476941267N, igual al resumen4C. El README general del aporte vertical
advierte otra fuerza14071,128N; esa advertencia no corresponde a los archivos
actuales comprobados. Se registra sin modificar historia ni certificar toda
copia. Para cualquier6B congelar archivos exactos medianteSHA256 y respetar
tiempo/ángulo y marco de referencia.
