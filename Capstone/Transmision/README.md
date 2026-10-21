# Transmisión mecánica — Etapas 5A a 5E.2-B

Modelo preliminar de una transmisión abierta por tres correas SPA 1600 entre el
motor de 5,5 kW a 1450 rpm y el eje vertical. Las etapas existentes se consultan
como entradas: [contacto y rodillos](../Simulación_peletizadora/README.md) y
[matriz/eje vertical](../Analisis_matriz_eje_vertical/README.md). Sus cálculos,
fuentes y resultados permanecen sin modificaciones. No se genera informe LaTeX.

## Ejecución y archivos

Desde `Capstone/Transmision`:

```powershell
python -m pip install -r requirements.txt
python simulacion_transmision.py
python -m pytest -q
# Otra parametrización o destino:
python simulacion_transmision.py --parametros parametros.json --salida resultados
```

La ejecución usa únicamente la biblioteca estándar; pytest es para las pruebas.
`parametros.json` contiene los datos de diseño y escenarios. `transmision/`
separa geometría, dimensionamiento, balance motor y datos de catálogo.
Las funciones validan valores positivos y finitos, geometría, eficiencia,
cantidad entera de correas y compatibilidad con el catálogo transcrito.
La geometría es parametrizable; la capacidad de catálogo se restringe a los
puntos verificados. Modificar rpm, diámetro pequeño o longitud exige ampliar
las tablas desde la fuente original; no se extrapolan capacidades.

`resultados/` contiene `geometria_5a.csv`, `capacidad_5b.csv`,
`sensibilidad_factor_servicio.csv`, `balance_motor_eficiencias.csv`,
`contraste_3c.csv`, `resumen.json`, `parametros_utilizados.json` y
`fuentes_y_validacion.json`. Este último registra la referencia y el SHA256 del
resumen 3C leído. Se comparan los datos declarados con la fila `inclinacion`
de `resumen_comparativo.csv` (tolerancia de redondeo: 0,001 kW o N·m).

## Catálogo y decisiones de lectura

Fuente: [Gates, Industrial V-Belt Drive Design Manual, 2004](https://www.gates.com/content/dam/documents-library/catalogs/industrial-v-belt-design-manual-kr.pdf).
Se inspeccionaron visualmente las tablas originales. Las páginas impresas
56–57 son las de SPA (páginas PDF 58–59, contando desde uno). La impresa 55
contiene correcciones SPZ y no se utiliza para SPA.

Se utiliza **SPA Super HC convencional envuelta**, no la construcción MN.
El encabezado excluye las columnas en cursiva para la construcción convencional;
la columna de 100 mm utilizada está en letra normal.

- Potencia básica A: 3,16 kW/correa, intersección exacta de 1450 rpm y 100 mm.
- Adicional B: 0,54 kW/correa, fila exacta de 1450 rpm e intervalo rotulado
  de relación 1,95–3,38 que contiene 2,8. No se interpola entre columnas.
- Factor CL: 0,94 para longitud de referencia SPA 1600, punto exacto.
- Adicional de vida C: cero, base de catálogo de 12.000 h. Esta base permite
  reproducir el dimensionamiento preliminar; no es una vida requerida ni
  una predicción de duración real. Las 8 h/día no fijan por sí solas una vida.
- Para G se obtiene `(D-d)/a=0,364878`. Las filas vecinas dan 0,96 y 0,94.
  No se encontró una autorización explícita para interpolar en el manual
  consultado. Se adopta como decisión conservadora propia el menor factor
  entre ambos extremos: **G=0,94**. No se presenta esa regla como instrucción
  literal del fabricante. La interpolación daría aproximadamente 0,947;
  el contraste con 0,947 se exporta por separado y no gobierna la selección.

Las potencias de estas tablas son específicas de la construcción Gates.
Que una correa genérica cumpla DIN 7753 no confirma idéntica capacidad: falta
verificar fabricante, referencia comercial, longitud de referencia y juego
de tres correas compatibles antes de aprobar la compra.

## 5A: cinemática y geometría

En 5A/5B se adoptaron diámetros de referencia de 100 y 280 mm; 5C confirma
esa identificación y registra los exteriores CAD de 105,6 y 285,6 mm.
Los resultados históricos y su campo `diametros_son_referencia_supuesto`
se conservan; la confirmación actual se registra en `etapa_5c` de los parámetros.
Se asume rodadura ideal, sin deslizamiento ni elasticidad.
Con `d`, `D` y `a` en mm:

```text
i = D/d; n_salida = n_motor/i; v = pi d n_motor / 60000
alpha = asin((D-d)/(2a)); beta_pequeña = pi - 2 alpha
L_aprox = 2a + pi(D+d)/2 + (D-d)^2/(4a)
L_exacta = 2 sqrt(a²-((D-d)/2)²) + pi(D+d)/2 + (D-d) alpha
```

La longitud exacta es la geometría ideal de tangentes y arcos de dos círculos.
Se invierte numéricamente por bisección para comprobar los centros comerciales.

| Magnitud | Resultado |
|---|---:|
| Relación | 2,8 |
| Salida teórica | 517,857 rpm |
| Velocidad de correa | 7,592 m/s |
| Centros suministrados | 493,316 mm |
| Longitud aproximada / exacta | 1599,9541 / 1600,0001 mm |
| Centros para longitud exacta de 1600 mm | 493,31595 mm |
| Abrazamiento motriz / conducida | 158,976° / 201,024° |

La longitud coincide geométricamente con 1600 mm. La velocidad de salida
supera en 1,857 rpm (0,360 %) las 516 rpm usadas en 3C. Se conservan las cargas
heredadas a 516 rpm, sin escalarlas ni recalcular el contacto. El deslizamiento
real y la velocidad de operación siguen pendientes de medición.

## 5B: capacidad y sensibilidad

```text
P_diseño = FS P_motor
P_correa = (A+B+C) G CL
z_mínimo = ceil(P_diseño/P_correa)
margen relativo = (z P_correa/P_diseño - 1) × 100
```

Para FS preliminar 1,3: potencia de diseño **7,15 kW**, capacidad corregida
**3,26932 kW/correa**, capacidad de tres correas **9,80796 kW** y mínimo
**3 correas**. El margen es **2,65796 kW (37,17 % sobre la potencia de diseño)**;
la utilización de capacidad es 72,90 %. Con G=0,947, el contraste da
3,29367 kW/correa, 9,88100 kW totales y también tres correas.

La capacidad adoptada admite FS hasta aproximadamente **1,7833**. Por ejemplo,
FS=1,0 exige dos correas, FS=1,3 y 1,6 exigen tres, y FS=1,8 y 2,0 exigen
cuatro. El CSV incluye todos los escenarios. FS=1,3 es una hipótesis recibida:
faltan confirmar severidad de compactación, arranques, atascos y régimen para
validarla con la clasificación de servicio del fabricante.

## Potencia disponible del motor: comprobación independiente

Se supone que 5,5 kW es potencia mecánica nominal de eje. La potencia de diseño
de correas incorpora servicio; no es una nueva demanda de 7,15 kW al motor.
Para cada eficiencia total supuesta se calcula `P_disponible=eta × 5,5 kW` y
se compara con los valores heredados 4,805 kW máximos y 4,194 kW medios.

| Eficiencia supuesta | Disponible [kW] | Margen máximo [kW] | Margen medio [kW] |
|---:|---:|---:|---:|
| 0,85 | 4,675 | −0,130 | 0,481 |
| 0,87 | 4,785 | −0,020 | 0,591 |
| 0,90 | 4,950 | 0,145 | 0,756 |
| 0,95 | 5,225 | 0,420 | 1,031 |
| 1,00, límite ideal | 5,500 | 0,695 | 1,306 |

La eficiencia mínima aritmética para cubrir el máximo es **87,36 %**; para
la media, **76,25 %**. No se midió una eficiencia ni se comprobaron arranque,
sobrecarga, temperatura o atascos. El torque máximo heredado es 88,924 N·m;
se registra para trazabilidad, sin duplicar los modelos estructurales ni usarlo
para inventar tensiones de ramales.

## Pendientes de selección comercial y cargas (5D)

- Referencias comerciales exactas de las tres correas y poleas, construcción,
  norma y equivalencia de capacidad; confirmar tipo de longitud y de diámetros.
- Perfil de canales, alineación, ancho, número de gargantas y fijaciones.
- Método y valor de tensado del fabricante, recorrido de instalación y retensado,
  posibilidad de mover centros y compatibilidad del conjunto de correas.
- Disposición espacial de motor y eje vertical, orientación de ramales,
  posiciones axiales de polea y apoyos, y voladizos para calcular fuerzas/reacciones.
- Pretensión, masa lineal y datos del fabricante necesarios para separar ramal
  tenso/flojo y efectos centrífugos. Las fuerzas sobre ejes quedan pendientes.
- Arranques, aceleración, régimen real, atascos, condiciones ambientales y
  eficiencia; confirmar si debe alcanzarse exactamente 516 rpm.

Las pruebas cubren geometría analítica, inversión de longitud, unidades,
tabla específica, selección conservadora, redondeo de cantidad, sensibilidad,
balance de potencia, rechazo de entradas incompatibles y trazabilidad de 3C.

## 5C: geometría comercial y recorrido de tensado

Ejecutar separadamente para conservar los archivos históricos de 5A/5B:

```powershell
python simulacion_tensado.py
python -m pytest -q
```

El ejecutable reutiliza `geometria()` de 5A y contrasta `resolver()` con el
histórico validado de 5A/5B, sin regenerarlo. Las salidas propias se guardan en
`resultados/etapa_5c/`: `resumen.json`, `poleas_y_gargantas.csv`,
`ajuste_centros.csv`, `geometria_nominal.csv`, `validaciones.csv`,
`parametros_utilizados.json` y `fuentes_y_trazabilidad.json`.
Los SHA256 permiten comprobar que los archivos originales siguen idénticos.
Los avisos en el resumen histórico reflejan el estado de conocimiento de 5A/5B;
las confirmaciones actuales están en 5C.

### Diámetros confirmados y cotejo de gargantas

| Polea | Referencia [mm] | Exterior CAD [mm] | Diferencia diametral [mm] |
|---|---:|---:|---:|
| Motriz | 100 | 105,6 | 5,6 |
| Conducida | 280 | 285,6 | 5,6 |

La diferencia corresponde a 2,8 mm radiales desde la referencia hasta el
exterior CAD en ambas poleas. La cinemática y longitud utilizan exclusivamente
100 y 280 mm; los exteriores solo se usan para cotejo geométrico e interferencias.

Se verificó visualmente la tabla 18 del mismo manual Gates, página impresa 40
(PDF 42). Su fila SPA remite a DIN 2211 e ISO 4183. Para tres correas
independientes se requieren **tres gargantas SPA alineadas en cada polea**.
Los datos de referencia para cotejar los planos son:

| Magnitud | Motriz | Conducida |
|---|---:|---:|
| Ángulo de garganta | 34° ±1° | 38° ±1° |
| Ancho de referencia lp | 11 mm | 11 mm |
| Paso e entre centros | 15 ±0,30 mm | 15 ±0,30 mm |
| Distancia f del centro extremo al borde | 10 ±0,6 mm | 10 ±0,6 mm |
| Profundidad d de la tabla | 13,75 (+0,25/−0) mm | 13,75 (+0,25/−0) mm |
| Ancho de boca go tabulado | 12,68 mm | 12,89 mm |
| Altura b sobre referencia | 2,75 mm | 2,75 mm |

El ángulo depende del diámetro de referencia: la fila de 90–118 mm usa 34°
y la de más de 118 mm usa 38°. El ancho nominal de llanta calculado es
`B=(z−1)e+2f=50 mm` en ambas poleas. Es una dimensión de referencia, no
un ancho comercial verificado ni el ancho total de una polea con cubo.

**Diferencia pendiente de cotejo CAD:** b=2,75 mm implica exteriores derivados
de 105,50 y 285,50 mm; Inventor muestra 105,60 y 285,60 mm. La diferencia
es +0,10 mm diametral (+0,05 mm radial). Se registran ambos juegos de valores;
no se declara equivalencia exacta ni se inventa una tolerancia para b. Confirmar
el perfil usado por Inventor y el plano/catálogo comercial. Los diámetros por sí
solos no verifican los ángulos, pasos ni la geometría completa de las gargantas.

### Reserva mecánica de ajuste

Se volvió a comprobar la **tabla 11, impresa 32 (PDF 34)**: para SPA con
longitud de referencia 1200–1999 mm corresponden 25 mm mínimos de acercamiento
y 35 mm mínimos de alejamiento. Se selecciona la fila que contiene 1600 mm,
sin interpolación. Estos recorridos son variaciones de distancia entre centros,
no variaciones de longitud de correa.

| Posición/reserva | Distancia entre centros [mm] |
|---|---:|
| Extremo de acercamiento para instalar | 468,316 |
| Referencia nominal geométrica | 493,316 |
| Extremo de alejamiento para retensado | 528,316 |
| Recorrido útil total mínimo | **60,000** |

En nominal se conservan longitud exacta de 1600,0001 mm, abrazamientos
158,976°/201,024°, relación 2,8 y salida 517,857 rpm. La posición nominal es
la referencia geométrica; el punto real de operación depende del tensado y
del estado de la correa. **Los extremos son reservas de montaje y retensado,
no puntos normales de funcionamiento de una correa inextensible de 1600 mm.**
No se calcula una tensión inicial ni se deduce de la diferencia de longitudes.

### Propuesta preliminar de base móvil y pendientes para 5D

Se propone una base del motor guiada longitudinalmente en la línea de centros,
con regulación de desplazamiento y bloqueo posterior independiente. Debe
permitir como mínimo 25 mm hacia la polea conducida y 35 mm hacia afuera,
mantener paralelismo de ejes y coplanaridad de gargantas, y bloquearse después
de ajustar mediante el procedimiento del fabricante. Si la disposición real
de ejes no permite este movimiento, habrá que adaptar el concepto de base.

Los **60 mm son carrera útil de centros**, no longitud final de una ranura:
esta última también depende del diámetro del perno, extremos, arandelas,
holguras de montaje y distancias a bordes. No se asignan dimensiones de pernos,
ranuras, espesores ni capacidad estructural de la base todavía.

Para 5D necesitamos:

- Fabricante y referencia exactos de correas, método de tensado aplicable
  (fuerza-deflexión o frecuencia), parámetros y límites para correas nuevas y
  usadas, y pauta de retensado. No basta la designación DIN 7753 para fijar tensión.
- Masa lineal de la correa, tramo libre real, comportamiento elástico y datos
  necesarios para los efectos centrífugos y reparto entre las tres correas.
- Condición de carga que gobernará ramales (nominal, arranque o atasco),
  aceleración y pérdidas; no se adopta una relación arbitraria entre tensiones.
- Plano de la transmisión: coordenadas y orientación de ejes/ramales, alturas
  axiales de poleas, centros de rodamientos, voladizos y referencia espacial.
  Las cargas laterales requieren sumar vectorialmente las fuerzas de los ramales;
  la diferencia de tensiones por torque no basta para determinar esa suma.
- Plano y masa del motor, posiciones y medidas de patas/agujeros, materiales
  y espesores de base/bastidor, sistema de guía y bloqueo, clase de pernos,
  fricción de contacto y cargas dinámicas para dimensionar uniones y soportes.

Las pruebas 5C incluyen diferencias diametrales/radiales, frontera de tabla,
recorridos, centros, garganta por correa, dimensiones tabuladas y ángulos por
diámetro, rechazo de valores inválidos y conservación numérica y por SHA256
de 5A/5B. No se calculan reacciones del eje vertical ni se modifica su modelo.

## 5D.1: tensión estática y comprobación por deflexión

```powershell
python simulacion_tension_estatica.py
python -m pytest -q
```

El ejecutable lee `parametros.json` y los históricos de transmisión, reutiliza
`geometria()` y escribe exclusivamente en `resultados/etapa_5d1/`. Exporta
`tensado_individual.csv`, `sensibilidad.csv`, `resumen.json`,
`parametros_utilizados.json`, `validaciones.csv` y `fuentes_y_trazabilidad.json`.
La trazabilidad incluye SHA256 de todos los resultados 5A/5B y 5C, verificados
sin ejecutar esos subsistemas. Sus avisos históricos se conservan tal como fueron
emitidos; esta sección completa el tensado que antes figuraba pendiente.

Se verificaron visualmente las páginas impresas 33–34 del manual Gates
(PDF 35–36), fórmulas 6–12 y tabla 13. Se adopta la fila **SPA individual
convencional**, con R=2,5, M=0,12 y Y=20 N. La fila SPA* corresponde a otra
construcción. Estas constantes no se transfieren a correas genéricas DIN 7753.

```text
Ts = 475 ((R-G)/G) P/(N v) + M v²
t_exacto = sqrt(a²-((D-d)/2)²)
delta = t/100
Fmin = (Ts + (t/Ld)Y)/25
Fmax = (1,5 Ts + (t/Ld)Y)/25
```

P es potencia de accionamiento en **kW**; aquí se usan **5,5 kW**, no los
7,15 kW históricos de diseño de correas. v se expresa en m/s y Ts y F en N;
t, Ld y delta usan mm, por lo que t/Ld es adimensional. R, G y N son
adimensionales; M tiene unidades N·s²/m². El coeficiente 475 ya corresponde
a las unidades indicadas y no se debe multiplicar nuevamente P por 1000.

| Correa | Ts base [N] | Tramo libre [mm] | Deflexión [mm] | Fmin [N] | Fmax [N] |
|---|---:|---:|---:|---:|---:|
| 1 | 197,27 | 485,04 | 4,85 | 8,13 | 12,08 |
| 2 | 197,27 | 485,04 | 4,85 | 8,13 | 12,08 |
| 3 | 197,27 | 485,04 | 4,85 | 8,13 | 12,08 |

Se usa el tramo tangente exacto solicitado. La fórmula 7 del manual utiliza
la aproximación `t=a[1−0,125((D−d)/a)²]`, no la raíz exacta; el contraste
se exporta en JSON. No se duplica la cinemática ni se usan diámetros exteriores.

### Condición de medición y procedimiento

Los valores principales anteriores corresponden a las **fórmulas 11–12**,
con al menos una polea libre para girar durante la medición y permitir la
redistribución estática. Esta condición debe confirmarse en el conjunto real.
Para ambas poleas inmovilizadas se exportan separadamente las fórmulas 9–10,
que usan Y completo: aproximadamente **8,69–12,64 N** por correa. No mezclar
los dos intervalos de comprobación.

1. Con el accionamiento detenido y aislado, verificar alineación y la condición
   de libertad de giro prevista; medir el tramo libre real entre tangencias.
2. Aplicar una fuerza **perpendicular**, en el punto medio del tramo y sobre
   una correa individual, hasta alcanzar la deflexión de 4,85 mm. Usar un
   instrumento de fuerza/deflexión y una referencia recta del tramo sin deflectar.
3. Comparar la fuerza medida con el intervalo correspondiente. Ajustar la base
   móvil para corregir el tensado y repetir en las tres correas.
4. Gates indica aproximarse al extremo superior en correas nuevas y al inferior
   para usadas. Bloquear la base y volver a comprobar las tres mediciones y
   la alineación. Confirmar la pauta de retensado de la referencia finalmente comprada.

**Ts** es tensión estática base longitudinal de instalación por correa;
**F** es fuerza transversal aplicada para medir deflexión. Ninguna de estas
magnitudes es por sí sola una tensión dinámica de ramal ni la carga lateral
resultante sobre un eje. El factor 1,5 del límite de comprobación no es el
factor de servicio 1,3 de 5B, ni R=2,5 una razón dinámica T1/T2 medida.

### Sensibilidad y alcance

Se exportan 18 escenarios de fórmula: N=2/3/4, P=4,194/4,805/5,5 kW y
G=0,94/0,96, conservando velocidad y constantes SPA verificadas. Los G son
los extremos tabulados ya verificados en 5B; 0,96 es solo sensibilidad y no
reemplaza el G conservador de la geometría actual. Las potencias reducidas
representan hipótesis de accionamiento, no una nueva selección de motor.
Cambiar N exige revisar gargantas y capacidad; dos o cuatro correas no son
configuraciones aprobadas para las poleas actuales de tres canales. No se
extrapolan capacidades ni se asignan propiedades a otras construcciones.

Las pruebas cubren resultados de contraste, unidades, constantes, condiciones
de medición, entradas inválidas y conservación SHA256 de los históricos.
Para 5D.2 quedan pendientes:

- Confirmación de correa comercial y tensado real alcanzado, posibilidad de
  giro libre y reparto de pretensión entre las tres correas.
- Formulación dinámica con balance de potencia/torque, elasticidad y
  compatibilidad de ramales, masa lineal y tratamiento de efectos centrífugos.
  M es el coeficiente tabulado de esta fórmula, no una ficha completa de masa
  o rigidez para cualquier SPA comercial.
- Condición gobernante de potencia, pérdidas, aceleración y posibles atascos;
  no asumir una razón dinámica T1/T2 a partir del factor R.
- Plano espacial de ramales, poleas y apoyos con posiciones axiales/voladizos
  para obtener fuerzas laterales vectoriales y, posteriormente, reacciones.

Las tensiones y cargas quedaron pendientes al cerrar 5D.1; la sección siguiente
incorpora un modelo condicional. Las reacciones de apoyos siguen pendientes.

## 5D.2: equilibrio de torque, tensiones condicionales y cargas en poleas

```powershell
python simulacion_dinamica.py
python -m pytest -q
# Giro opuesto, en una salida separada:
python simulacion_dinamica.py --signo-giro -1 --salida resultados/etapa_5d2_giro_inverso
# Omitir el modelo de tensiones y exportar solo equilibrio:
python simulacion_dinamica.py --solo-equilibrio --salida resultados/etapa_5d2_equilibrio
```

Se lee el historial completo `series_temporales_acopladas.csv` de 3C, filtrado
por `modelo=inclinacion`: **1440 estados correlacionados y convergidos**.
Se conservan paso, tiempo y ángulo originales. Se leen Ts=197,2723316 N de
5D.1 y la velocidad histórica de 5A. Ningún modelo previo se ejecuta ni sus
resultados se regeneran. Se registran y verifican los SHA256 de las entradas
3C y de todos los resultados 5A–5D.1, además de los parámetros.

### Resultados obtenidos por equilibrio

Para la polea conducida de radio de referencia 0,14 m:

```text
delta_total(t) = T_3C(t)/0,14
delta_individual(t) = delta_total(t)/3  [hipótesis de reparto uniforme]
```

La diferencia total procede directamente del equilibrio de torque. El reparto
individual requiere que las tres correas compartan la carga por igual; no se
deduce del equilibrio global. Los valores del historial son:

| Magnitud | Máximo | Media |
|---|---:|---:|
| Torque resistente 3C [N·m] | 88,923966 | 77,623586 |
| Diferencia total de tensiones [N] | 635,171184 | 554,454186 |
| Diferencia por correa uniforme [N] | 211,723728 | 184,818062 |

El máximo se presenta en el paso 377, ángulo 94,25°, tiempo 0,030442506 s.
La tabla de críticos copia la fila completa correspondiente a cada extremo;
no combina máximos independientes de distintos instantes.

### Hipótesis de cierre de tensiones

El modelo opcional impone por correa `F_tenso=Ts+delta_individual/2` y
`F_flojo=Ts−delta_individual/2`. Mantener la media igual a Ts es una
**hipótesis propia simplificada**, no un procedimiento de Gates ni una
predicción exacta de la transmisión en movimiento. Se usa el Ts completo
heredado de 5D.1 como referencia estática; no se identifica Ts con tensión
centrífuga ni se añade otro término centrífugo. El modelo omite inercia
distribuida y pérdidas en los tramos, sin asignar masa, rigidez o fricción.

En el instante de torque máximo, `F_tenso=303,134196 N` y
`F_flojo=91,410468 N` por correa. Los 1440 estados dan tensiones no negativas.
Si un escenario produce F_flojo negativa se marca como no admisible bajo
este cierre y no se exporta una fuerza vectorial interpretable para él.
La no negatividad no prueba adherencia: no se comprueba deslizamiento ni
se usa R=2,5 de Gates como límite de razón dinámica de tensiones.

### Sistema local y suma vectorial

Se sitúa la conducida en (0,0) y la motriz en (a,0). +x apunta al motor,
+y es perpendicular en el plano y +z=x×y. Superior/inferior se refieren a
los lados +y/−y. El ángulo de las tangentes es **alpha=10,511848°**,
recuperado de la geometría existente de referencia.

Para giro positivo antihorario visto desde +z, el ramal inferior es tenso.
Las direcciones de fuerza sobre la conducida son `(cos alpha,−sin alpha)`
en el superior y `(cos alpha,+sin alpha)` en el inferior. Esto produce torque
positivo de las correas sobre la conducida. Al invertir giro se intercambia
el ramal tenso: cambia el signo de Fy, se conservan Fx y Fr.

```text
Fx_conducida = N (F_tenso+F_flojo) cos alpha
Fy_conducida = signo_giro N (F_tenso−F_flojo) sin alpha
Fr = hypot(Fx,Fy)
F_motriz = −F_conducida  [ambas expresadas en el mismo marco x,y]
```

La fuerza motriz es opuesta por la idealización de tramos sin inercia distribuida.
El torque aplicado por correas en la motriz es de signo opuesto al del motor,
con magnitud `delta_total × 0,05 m`. Los torques firmados en ambas poleas
se registran para auditar esa convención. La suma vectorial es mecánica
elemental propia; Gates se cita exclusivamente para Ts y su construcción.

En el paso crítico, para el giro positivo adoptado:

| Polea | Fx [N] | Fy [N] | Fr [N] |
|---|---:|---:|---:|
| Conducida | +1163,769 | +115,880 | 1169,524 |
| Motriz, mismo marco | −1163,769 | −115,880 | 1169,524 |

Estas fuerzas **dependen del cierre de tensiones**. Fx es constante en este
modelo porque la suma de tensiones se impuso constante; no es un hallazgo
experimental. Fy puede obtenerse de delta y la geometría bajo la convención
de tramos idealizados. No son reacciones de rodamientos ni incluyen pesos,
otros esfuerzos de la matriz, excentricidades o momentos de voladizo.

### Escenario externo: potencia nominal del motor

Se evalúa separadamente `delta_total=5500/v=724,429396 N` con
`v=7,592182 m/s` y eficiencia ideal 1. El torque conducido equivalente es
101,420115 N·m. No se usa la potencia de diseño de correas de 7,15 kW.
Este escenario no pertenece a 3C y no se le asigna un instante de compactación.
Da 318,010564/76,534099 N en ramales tenso/flojo por correa, y
`Fx=1163,769 N`, `Fy=132,164 N`, `Fr=1171,250 N` en la conducida.

3C mantiene sus 516 rpm y potencias originales. La transmisión ideal produce
517,857 rpm: conservar torque y usar esta cinemática implica una potencia
ideal ligeramente diferente. No se reescala el historial 3C para forzar
coincidencia ni se introduce una eficiencia ficticia.

### Sensibilidad hipotética de Ts

| Factor Ts | Ts/correa [N] | Fr máxima 3C [N] | Fr motor nominal [N] |
|---:|---:|---:|---:|
| 0,8 | 157,818 | 938,199 | 940,349 |
| 1,0 | 197,272 | 1169,524 | 1171,250 |
| 1,2 | 236,727 | 1401,323 | 1402,763 |
| 1,5 | 295,908 | 1749,496 | 1750,650 |

Todos estos escenarios dan tensiones no negativas. Son hipótesis para medir
la dependencia de la carga lateral con Ts, **no instrucciones de tensado**
del fabricante. Cada escenario 3C se evalúa sobre sus 1440 instantes; el motor
nominal se conserva como caso externo. No se deduce una recomendación de
reducir o aumentar la pretensión a partir de esta tabla.

### Salidas, pruebas e integración pendiente

En `resultados/etapa_5d2/` se generan:

- `diferencias_tensiones_3c.csv`: historial completo de equilibrio.
- `tensiones_y_fuerzas_condicionales_3c.csv`: tensiones individuales y sumas
  vectoriales de ambas poleas en cada instante, incluidas contribuciones de ramales.
- `casos_criticos_correlacionados.csv`: extremos con su fila sincronizada.
- `motor_nominal_externo.csv` y `sensibilidad_Ts.csv`.
- `resumen.json`, `trazabilidad_sha256.json` y `validaciones.csv`.

Las pruebas verifican torque, fuerzas, momentos de las tangentes, inversión
de giro, caso sin torque, no negatividad, reparto uniforme, separación del
motor nominal, conservación de entradas y ejecución opcional de solo equilibrio.

Para integrar la fuerza en el eje vertical faltan las **posiciones axiales
exactas de la polea y de cada apoyo**, orientación del plano local respecto del
conjunto, voladizos y disposición/fijación radial y axial de rodamientos.
Para validar las tensiones dinámicas reales también faltan pretensión medida,
rigidez/elasticidad y masa de la correa comercial, adherencia, pérdidas y régimen
de arranque/atascos. Todavía no se calculan las reacciones del eje vertical.

## 5E.1: preparación de la verificación estructural de poleas

```powershell
python simulacion_poleas.py
python -m pytest -q
```

Se utiliza `parametros_poleas.json`, separado de los parámetros históricos.
Los campos estructurales y propiedades no confirmados están en **null**.
El ejecutable importa los casos críticos correlacionados y el motor nominal
de 5D.2 sin ejecutar contacto, transmisión ni el análisis de matriz/eje vertical.
Sus resultados se guardan exclusivamente en `resultados/etapa_5e1/`.

### Inventario: qué se conoce y qué no se transfiere

En los archivos del repositorio se localizaron diámetros de referencia
100/280 mm, exteriores CAD reportados 105,6/285,6 mm y tres gargantas SPA.
5C aporta las dimensiones normativas de garganta y 50 mm de ancho nominal
de llanta: **ese ancho no es una cota medida del CAD**. Se mantiene la diferencia
de 0,10 mm entre exterior reportado y el derivado del perfil tabulado.
No se encontró CAD STEP/Inventor o plano acotado de poleas; el único DXF
detectado pertenece a la matriz. Los planos PNG existentes son de matriz,
rodillo y eje transversal, no planos de poleas.

El análisis de matriz/eje vertical contiene Ø50, Ø58 y espesores de la matriz,
resaltes y sensibilidades de vano. No documenta el agujero, cubo, radios o cuerpo
de estas poleas. **Ninguna de esas cotas se ha reutilizado como cota de polea.**
Los Sy 1045 +QT de escenarios anteriores tampoco se transfieren al candidato
AISI 1045 de condición desconocida. E, nu, densidad, Sy, Sut y fatiga permanecen
sin asignar; no hay factores de seguridad aprobados.

### Cargas verificadas y escenarios separados

El marco y las hipótesis son los de 5D.2. Los torques corresponden a fuerzas
de correas sobre cada polea; el torque de reacción transmitido al eje es opuesto.

| Escenario | Polea | Torque firmado [N·m] | Fx [N] | Fy [N] | Fr [N] |
|---|---|---:|---:|---:|---:|
| 3C crítico, paso 377 | Motriz | −31,75856 | −1163,769 | −115,880 | 1169,524 |
| 3C crítico, paso 377 | Conducida | +88,92397 | +1163,769 | +115,880 | 1169,524 |
| Motor nominal ideal externo | Motriz | −36,22147 | −1163,769 | −132,164 | 1171,250 |
| Motor nominal ideal externo | Conducida | +101,42012 | +1163,769 | +132,164 | 1171,250 |

Se auditan `abs(T)=delta_total*r_referencia` y `Fr=hypot(Fx,Fy)` para cada
fila. No se aplica el torque de la conducida a la motriz, ni se confunde
`Fr*r` con el torque transmitido. Los tres criterios críticos heredados
coinciden en el mismo estado en este modelo; se conservan sus etiquetas.
Las resultantes son **cargas condicionales**, dependientes del cierre de
tensiones de 5D.2. El torque requerido procede del equilibrio.

`sensibilidad_pretension_separada.csv` conserva las envolventes 0,8/1/1,2/1,5
Ts del archivo original en filas aparte, para ambas poleas. Las magnitudes
de fuerza en ambas son iguales en 5D.2. Ese archivo no contiene componentes,
torque ni tiempo correlacionados de la sensibilidad: se dejan null y no se
combinan con un máximo nominal para fabricar un caso estructural simultáneo.

### Verificaciones analíticas preparadas

Se implementan funciones independientes con N, mm y MPa, conversión explícita
de N·m a N·mm y rechazo de dimensiones inválidas. Son teoría elemental y
equilibrio propios; **no se atribuyen a Gates**:

- Cubo liso anular: `J=pi(De^4−Di^4)/32`, `I=J/2`,
  `tau=T(De/2)/J`, `sigma_b=Fr e(De/2)/I`. La combinación
  `sqrt(sigma_b²+3tau²)` es solo von Mises parcial: omite cortante transversal,
  chavetero, contacto, concentraciones y redistribución de una polea real.
  e es el desfase local entre plano de carga y sección analizada del cubo;
  no es una distancia a los rodamientos ni una reacción del eje.
- Cuerpo disco continuo: `tau_media=T/(2 pi r² t)`, obtenido al integrar
  torque de cortante uniforme en una sección circular. Solo componente
  torsional media; no resuelve flexión, carga radial ni radios discretos.
- Una chaveta paralela confirmada: `F=2T/d`, `tau=F/(b L)` y
  `p_media=F/(h_contacto L)`. h_contacto debe indicarse explícitamente;
  no se supone la mitad de una altura típica. Se requieren propiedades
  propias de la chaveta para comprobarla.

Actualmente **todas las verificaciones de resistencia están pendientes**:
faltan las dimensiones que esas fórmulas necesitan. Las funciones se prueban
con geometrías sintéticas de prueba, que no son propuestas de dimensiones de
las poleas. No se calcula tensión máxima ni FS de una polea a partir de su
diámetro exterior solamente. El reparto entre radios tampoco se supone sin
rigidez, geometría y orientación de cada radio.

### Dimensiones necesarias para cerrar los cálculos

Para **cada polea**, completar y respaldar con plano/CAD:

- Topología: disco continuo, radios o construcción mixta. Si hay radios:
  número, forma, orientación, longitud libre, conicidad y secciones a lo largo.
- Llanta: diámetro interior, espesor residual mínimo bajo raíces de garganta,
  ancho axial real y espesor de paredes entre gargantas.
- Cuerpo: espesor y perfil radial/axial, vaciados y posición respecto de llanta/cubo.
- Cubo: diámetros interior/exterior, longitud axial y desfase del plano de
  correas respecto de las secciones y superficies que transfieren la carga.
- Filetes de radios–cubo y radios–llanta/cuerpo, raíces de garganta, escalones
  y radios/chaflanes del agujero. No reemplazarlos por esquinas de radio cero.
- Unión real: chaveta/casquillo/interferencia/pernos, tolerancias, longitudes
  activas, chaveteros, detalles de retención axial y contacto con el eje.
- Condición de suministro y sección del producto 1045, tratamiento/certificado,
  propiedades y criterios de resistencia/fatiga aplicables.

La lista de null por polea se exporta en `dimensiones_pendientes.csv`; los campos
no aplicables deben resolverse después de confirmar la topología y unión.

### FEM requerido y salidas

[especificacion_fem_poleas.md](especificacion_fem_poleas.md) prepara el futuro
FEM: CAD real, material trazable, transferencia distribuida de cargas sin
duplicar torque, restricciones en la unión real, fases de radios y al menos
tres mallas. Incluye métricas de equilibrio, deformación, esfuerzos y contacto,
tratamiento de singularidades y contraste con las aproximaciones analíticas.
Los criterios de convergencia propuestos son de trabajo y deben aprobarse;
no son instrucciones Gates ni resultados de un FEM ejecutado.

Las zonas de interés son raíces y paredes de gargantas, uniones de radios con
llanta/cubo, filetes, chavetero y asiento. El máximo esfuerzo puede depender
de la fase angular de los radios, no solo del instante de máximo torque 3C.
Los efectos de rotación y peso propios de la polea requieren densidad y volumen.
No se han ejecutado elementos finitos de poleas ni reutilizado el FEM de matriz.

`resultados/etapa_5e1/` contiene cargas, geometría conocida, verificaciones,
dimensiones pendientes, sensibilidades separadas, parámetros, inventario,
especificación FEM, resumen, validaciones y trazabilidad SHA256 de archivos
anteriores de transmisión y del análisis de matriz/eje vertical. Las pruebas
cubren unidades, geometrías inválidas, torques por radio propio, correlación,
pendientes por datos ausentes y conservación de entradas.

La referencia existente `gates_vbelt_2004` sigue limitada a datos de correas,
tensado y gargantas. No se añadió una ficha de 1045 sin condición confirmada
ni se inventó una fuente para avalar propiedades o un análisis no ejecutado.

## 5E.1 — Revisión geométrica vigente de la conducida (Inventor)

Se incorporó [POLEA 1 (1).pdf](<POLEA 1 (1).pdf>), una hoja con vistas frontal,
lateral y corte A-A, cajetín ag_go de 21-10-2026. Es fuente interna del equipo,
registrada como `equipo_polea_conducida_2026`, no norma. No se combinan cotas con
otras revisiones. Al estar REV vacío se identifica el archivo por SHA256.

```powershell
python actualizacion_polea_inventor.py
python -m pytest -q
```

La configuración vigente está en `parametros_poleas.json`. La línea base anterior
con sus parámetros permanece en `resultados/etapa_5e1/`; **no se debe regenerarla
con la nueva configuración**. La actualización se exporta exclusivamente a
`resultados/etapa_5e1/revision_inventor_2026_10_21/`, con parámetros propios,
tabla de cotas/pendientes, cargas correlacionadas, torsión parcial, verificaciones,
sensibilidad heredada separada, especificación FEM y hashes de los históricos.
Las secciones anteriores describen el estado de la línea base original.

### Cotas leídas y su interpretación

| Dato vigente | Superficie o uso |
|---|---|
| Ø280 de referencia | Nominal de diseño heredado de 5A; no nueva cota explícita en PDF |
| Ø285,60 | Crestas del perfil de gargantas |
| Ø300 | Envolvente exterior de las pestañas; no diámetro de referencia |
| Tres gargantas, 34° ±0,5° | Perfil real que se usará en el análisis estructural |
| 13,80 radial y Ø258 oculto | Profundidad y fondo de las gargantas; `285,60−2×13,80=258,00` |
| Seis círculos, Ø70 acotado en uno | Cuerpo aligerado; confirmar patrón repetido en CAD |
| Ø75 | Exterior del cubo, corroborado en frontal/lateral |
| R17,50 | Radio del agujero central: Ø35 circular derivado, sin chavetero |
| 78,60 axial | Envolvente total desde extremo saliente del cubo a cara posterior común |
| 60 axial | Ancho axial total de llanta con pestañas, no espesor de cuerpo |
| 5 y 23,60 axial | Pestaña y saliente hasta su cara interior; coherentes con saliente exterior 18,60 |
| M5x0.8 - 6H | Rosca radial en cubo; no acredita por sí sola transmisión ni retención |

**Corrección de interpretación:** Ø258 no se incorpora como diámetro interior
de llanta. La coherencia exacta con profundidad radial 13,80 lo identifica con
el fondo de gargantas. El corte muestra otra superficie interior de llanta sin
cota diametral suficiente. Por eso sigue pendiente el espesor residual real;
no se informa falsamente un espesor cero bajo garganta. Tampoco se mide el
PDF por píxeles para completar coordenadas ni cotas resistentes.

Se mantiene el cuerpo como **aligerado con seis aberturas circulares**. No se
supone un disco macizo ni seis radios rectangulares iguales. Faltan centros y
diámetro de reparto, espesores/perfil axial de cuerpo y ligamentos, y filetes.
La vista muestra chavetero, pero no todas sus dimensiones ni la unión efectiva.

### Discrepancia CAD–Gates

Inventor indica **34° ±0,5°**, frente a **38° ±1°** tabulados para SPA con
diámetro de referencia 280 mm en 5C. El análisis estructural usará 34° del plano.
La compatibilidad normativa **no queda aprobada** y la discrepancia no se
elimina cambiando el CAD silenciosamente. También se documenta la envolvente
de pestañas Ø300, que no altera la cinemática histórica basada en Ø280.
La carga sobre gargantas cambia de distribución local con el perfil real;
5D.2 aporta solo resultantes condicionales, no presión validada en flancos.

### Verificaciones que ahora pueden realizarse

Se verifica coherencia de cresta/fondo/profundidad, diferencia de ángulos y
envolventes axiales. Se calculan A, I y J de la sección **idealizada lisa**
Ø75/Ø35 del cubo, y la componente nominal `tau=|T|×1000×37,5/J` para cada
caso correlacionado importado. El resultado se etiqueta parcial: ignora el
chavetero, el taladro roscado, concentraciones, cortante transversal y flexión.
No es una tensión máxima ni permite aprobar la resistencia del cubo o la polea.
La suma de áreas de seis círculos Ø70 solo es área geométrica proyectada;
no se interpreta como volumen, masa o área resistente neta.

La flexión del cubo sigue pendiente del desfase real entre plano de correas y
sección analizada. La llanta requiere su diámetro interior/espesor residual,
paredes, filetes y contacto; el cuerpo requiere espesores y centros de aberturas;
la unión requiere cotas de chavetero, longitud activa, ajustes, tornillo/rosca
y retención. 78,60 no se usa automáticamente como longitud activa de unión.
Las fórmulas de disco continuo se excluyen para este cuerpo aligerado.

AISI 1045 continúa como candidato: condición/producto, E, nu, Sy, Sut, densidad
y fatiga permanecen pendientes. No se calculan factores de seguridad.
El máximo 3C y el motor nominal ideal siguen en filas distintas.

[Especificación FEM actualizada](especificacion_fem_conducida_inventor.md):
aberturas/ligamentos reales, contacto sobre perfil CAD, raíces de garganta,
chavetero/M5 y uniones de cuerpo–cubo/llanta; se requiere estudiar fase angular,
restricciones físicas y convergencia local. **FEM no ejecutado.**

## 5E.1 — Revisión conjunta vigente de ambas poleas

La incorporación de [POLEA 2.pdf](<POLEA 2.pdf>) completa las fuentes geométricas
actualmente disponibles. Plano de equipo, título `Grooved Pulley21`, escala 2:1,
ag_go 21-10-2026, una hoja y REV vacío; su SHA256 queda registrado, al igual
que el del plano vigente de la conducida. Es una fuente interna, no normativa.
La configuración de la **conducida y del material se conserva idéntica** a la
revisión anterior. Solo se actualizó el bloque motriz de `parametros_poleas.json`.

```powershell
python actualizacion_ambas_poleas.py
python -m pytest -q
```

Se escribe únicamente en
`resultados/etapa_5e1/revision_ambas_poleas_2026_10_21/`. No regenerar la línea
base ni la revisión anterior con la configuración nueva. Sus instantáneas y
resultados permanecen archivados. El nuevo ejecutable importa las cargas 5D.2,
sin ejecutar etapas anteriores, y comprueba SHA256 de sus archivos.

### Motriz: superficies y cotas confirmadas

| Cota | Interpretación |
|---|---|
| Ø100 | Referencia nominal heredada de 5A, no cota nueva del PDF |
| Ø105,60 / Ø120 / Ø78 | Crestas, pestañas y fondos de garganta, respectivamente |
| 13,80 radial | Profundidad de garganta; `105,60−2×13,80=78,00` |
| Tres gargantas, 34° ±0,5° | Perfil CAD; coincide en ángulo nominal con Gates para Ø100 |
| Ocho círculos Ø13 | Cuerpo aligerado; el diámetro se acota en una abertura, confirmar repetición CAD |
| Ø45 / R19 | Cubo exterior y agujero circular: Ø38 derivado del radio acotado |
| 10 JS9 | Ancho del chavetero frontal; no longitud ni altura efectiva de chaveta |
| M5x0.8 - 6H | Rosca radial de cubo; longitud engranada y papel resistente pendientes |
| 54 axial | Distancia entre caras exteriores de pestañas |
| 50 axial | Distancia entre caras interiores de pestañas |
| 2 axial | Espesor de pestaña representada; coherencia `54=50+2×2` |
| 62 axial | Extremo saliente del cubo a cara posterior común, en A-A |
| 10 axial lateral | Extremo de cubo hasta cara interior de pestaña: saliente exterior 8+2 |
| 10 / 12 en A-A | Desde caras interior/exterior de pestaña al plano indicado del perfil; no espesor uniforme del cuerpo |
| 15 en A-A | Paso axial de gargantas mostrado, sin reconstruir por píxeles el perfil completo |

El agujero Ø38 pertenece al plano de polea; **no confirma que el eje del motor
real tenga ese diámetro**. La coincidencia debe revisarse con plano/ficha del
motor. Los Ø78/Ø258 siguen siendo fondos de garganta: no se asignan como
interiores de llanta. Los espesores residuales de ambas piezas continúan null.

Los cuerpos se mantienen aligerados con aberturas circulares: ocho Ø13 en
motriz y seis Ø70 en conducida. No se reemplazan por discos macizos ni por
radios rectangulares uniformes. Centros de patrones, espesores, filetes y
geometría local todavía requieren el CAD acotado.

### Verificaciones disponibles y pendientes

Para ambas se pueden verificar las coherencias geométricas indicadas y calcular
A, I, J y la **torsión nominal parcial de cubo liso**: Ø45/Ø38 motriz y Ø75/Ø35
conducida, con los torques propios de las filas correlacionadas. El cálculo
ignora chavetero, taladro M5, entallas, flexión y distribución real de carga;
no es esfuerzo máximo de la pieza ni aprobación de resistencia.

| Componente torsional nominal lisa [MPa] | Motriz Ø45/Ø38 | Conducida Ø75/Ø35 |
|---|---:|---:|
| Máximo 3C | 3,611 | 1,127 |
| Motor nominal ideal | 4,119 | 1,285 |

La pared radial nominal lisa de la motriz es solo **3,5 mm**. Debe comprobarse
el ligamento restante tras mecanizar chavetero y M5; no se deduce a partir del
ancho 10 JS9 ni se supone una profundidad típica. La flexión del cubo permanece
pendiente del desfase local de cargas. Las cotas 62/78,60 no son longitudes
activas de chaveta. La resistencia integral de cuerpo, llanta, contacto y unión
permanece pendiente; AISI 1045 sigue sin E, Sy o factores de seguridad asignados.

La coincidencia angular de la motriz con 34° Gates es una comprobación parcial
del perfil, **no aprobación normativa completa**. La conducida conserva la
discrepancia 34° CAD frente a 38° de la tabla. No se altera ningún plano para
forzar compatibilidad ni se cambian los resultados históricos de capacidad.

Las tablas de esta revisión incluyen fuentes geométricas, dimensiones
confirmadas/derivadas/pendientes, cargas, torsión parcial, estado de todas las
verificaciones, sensibilidad de pretensión separada y manifiesto SHA256.
El máximo 3C y el motor nominal ideal permanecen en filas distintas. No se
combina un máximo de fuerza de sensibilidad con un torque nominal para crear
un caso estructural simultáneo inexistente.

### Requisitos de 5E.2: chavetas y uniones

Para cada polea confirmar el tipo real de unión transmisora, diámetro y
tolerancia de eje/agujero y ajuste; b, h y largo activo de la chaveta;
profundidades de chaveteros en eje y cubo, altura efectiva de contacto,
radios/terminaciones y longitudes de contacto. La motriz aporta únicamente
ancho nominal de chavetero 10 JS9; la conducida aún no aporta todas esas cotas.
No se han transcrito límites numéricos de JS9 sin una fuente aplicable.

Solicitar material/condición de chaveta, cubo y eje, detalle de tornillo M5
(clase, punta, longitud engranada, precarga si corresponde), función del tornillo,
retención axial y condiciones de servicio. Así podrán comprobarse corte,
aplastamiento, ligamentos y unión; las tensiones lisas actuales no bastan.

[Especificación FEM conjunta](especificacion_fem_ambas_poleas_inventor.md):
modelar ambos cuerpos aligerados, raíces, ligamentos, chaveteros y M5, cargas
sobre cada garganta sin duplicar torque, contacto y restricciones reales,
fase angular y convergencia local. **FEM no ejecutado; resistencia no aprobada.**

## 5E.2 — Chavetas y uniones polea–eje

```powershell
python simulacion_chavetas.py
python -m pytest -q
```

El ejecutable importa los parámetros y casos correlacionados de la última
revisión conjunta 5E.1; no vuelve a ejecutar las etapas anteriores ni cambia
los planos. La nueva configuración de escenarios y datos pendientes está en
`parametros_chavetas.json`; `parametros_poleas.json` permanece intacto.

Las salidas en `resultados/etapa_5e2/` incluyen candidatas, ligamentos, fuerzas
correlacionadas, sensibilidad de largo activo, estados, parámetros, fuentes,
ecuaciones y manifiesto SHA256 de históricos. [metodologia_chavetas.md](metodologia_chavetas.md)
documenta notaciones, ecuaciones y límites. No hay FEM ni uniones aprobadas.

### Normalización verificada

Se consultaron el [extracto técnico Ganter DIN 6885-1](https://www.ganternorm.com/fileadmin/user_upload/downloads/technischer%20anhang/technical_information/6885-1.pdf)
y su [ficha de chavetas paralelas](https://www.ganternorm.com/en/products/product-family/Stainless-Steel-Quality-Class-4/DIN-6885-Parallel-Keys-Stainless-Steel).
Para ambos diámetros (35 y 38 mm) resulta candidata **b×h=10×8 mm, forma alta**.
Las profundidades nominales son 5 mm en eje y 3,3 mm en cubo, ambas con
tolerancia +0,2/0 mm en las filas verificadas. No se consideran cotas reales
del CAD. El proveedor usa t2 para profundidad de cubo y t4 para eje; se conserva
esa definición para evitar intercambiar símbolos con otras tablas.

El plano motriz **10 JS9** es coherente en ancho nominal y clase de chavetero
de cubo contemplada por el proveedor. La chaveta candidata tiene ancho h9:
JS9 del chavetero no es tolerancia de chaveta ni ajuste diametral eje–agujero.
No se transcriben desviaciones numéricas JS9 sin una fuente específica.
El ancho del chavetero de la conducida continúa pendiente.

DIN Media identifica [DIN 6885-1:2021-11](https://www.dinmedia.de/en/standard/din-6885-1/346315269)
como forma alta vigente. Se leyó su registro editorial, no el texto completo
de pago; las dimensiones utilizadas provienen del extracto de fabricante.
[ISO/R 773:1969](https://www.iso.org/standard/5056.html) figura **retirada**;
no se presenta como norma actual ni se afirma equivalencia completa vigente.
Todas estas fuentes están registradas sin duplicados en `referencias.bib`.
No se adopta el material inoxidable de la ficha comercial dimensional.

### Fuerzas transmitidas por las uniones

Con el diámetro nominal de contacto del agujero, `F=2|T|×1000/d`:

| Polea | d [mm] | F máximo 3C [N] | F motor nominal ideal [N] |
|---|---:|---:|---:|
| Motriz | 38 | 1671,503 | 1906,393 |
| Conducida | 35 | 5081,369 | 5795,435 |

Son fuerzas de contacto para transmitir torque en la unión, no fuerzas laterales
de correas. Se conservan tiempo/ángulo de 3C y el motor nominal queda como
escenario externo sin instante asignado. Falta demostrar con plano o medición
que los ejes reales tienen Ø38 y Ø35 y tolerancias compatibles. La potencia de
5,5 kW no permite inferir el diámetro del eje del motor.

### Cubo motriz: incompatibilidad prioritaria

Para Ø45/Ø38, la pared lisa nominal es 3,5 mm. La ranura candidata alta de
3,3 mm deja **0,2 mm en el centro**; con su profundidad superior de 3,5 mm
el ligamento central se anula. Al considerar un fondo rectangular de ancho
10 mm, la esquina ideal invade el exterior cilíndrico: ligamento radial
**−0,354 mm nominal** y **−0,549 mm** al límite superior de profundidad.

El diámetro de envolvente sin reserva sería 45,707/46,098 mm para esos dos
casos; **no son diámetros resistentes recomendados**. Solo demuestran que el
ancho de ranura también importa, además de restar profundidad a la pared.
Los radios reales pueden recortar esquinas, pero no justifican ignorar el
ligamento central casi nulo. El M5 debilita adicionalmente una zona aún no definida.

**El cubo motriz actual no puede aprobarse para alojar esa candidata alta**.
Se debe revisar su geometría o una unión alternativa justificada antes de
fabricar. No se asegura que el CAD actual ya tenga q=3,3: la profundidad
real no está confirmada. No se escoge automáticamente otra chaveta, un cubo
mayor ni interferencia. La torsión del anillo liso de 5E.1 no resuelve esta
incompatibilidad ni representa la resistencia del cubo debilitado.

Para Ø75/Ø35 de la conducida, el centro del fondo deja 16,7 mm nominales y
16,5 mm a profundidad máxima; la esquina ideal queda contenida. Esto solo
evita la incompatibilidad geométrica inmediata: no valida contacto, entallas,
fatiga ni factores de seguridad.

### Cortante/aplastamiento y sensibilidad

Las funciones usan `tau=F/(b L_activa)` y `p=F/(h_contacto L_activa)`.
Se exportan escenarios L_activa=20/30/40/50 mm, **no una selección comercial**.
Para la candidata se usa únicamente como hipótesis de contacto nominal
`h_cubo=8−5=3 mm` y `h_eje=5 mm`; la holgura de fondo no es área portante.
Las alturas reales siguen null, igual que los largos activos confirmados.
Las envolventes 62/78,6 mm solo son límites geométricos necesarios, no largos
efectivos disponibles ni justificación de un producto concreto.

Ejemplo de sensibilidad, con L_activa hipotética de 40 mm:

| Escenario | Polea | tau media [MPa] | p media cubo [MPa] |
|---|---|---:|---:|
| Máximo 3C | Motriz | 4,179 | 13,929 |
| Motor nominal ideal | Motriz | 4,766 | 15,887 |
| Máximo 3C | Conducida | 12,703 | 42,345 |
| Motor nominal ideal | Conducida | 14,489 | 48,295 |

Estos esfuerzos medios **no aprueban las uniones**, no solucionan el ligamento
de motriz y no incluyen redistribución, chaflanes, extremos, filetes o fatiga.
Los esfuerzos admisibles de chaveta, eje y cubo requieren material/condición
y fuente propios. No se calculan factores de seguridad ficticios.

### Funciones separadas y datos pendientes

- **Torque:** confirmar si lo transmite una chaveta paralela única y sus
  dimensiones, profundidades de ambos chaveteros, largo activo, radios y contacto.
- **Centrado:** plano/ficha o medición del eje real y tolerancias de eje/agujero.
  Coincidencia nominal por sí sola no define el ajuste.
- **Retención axial:** definir solución y cargas; la rosca M5×0,8 no acredita
  resistencia axial ni torque transmisible sin detalle del tornillo y montaje.

Para seguir hacen falta revisión del cubo motriz, ejes disponibles reales,
materiales y tratamientos, forma/extremos de chavetas, alturas portantes,
detalle M5 (grado, punta, engrane, precarga si aplica), retención y condiciones
de servicio. AISI 1045 permanece candidato, sin propiedades definitivas.
La discrepancia SPA de conducida 34°/38° sigue registrada sin modificación.

## Etapa 5E.2-A — Alternativas del cubo motriz

Evaluación separada, **sin modificar el CAD definitivo**, los parámetros
estructurales vigentes, la conducida ni resultados anteriores. Ejecutar desde
`Capstone/Transmision`:

```powershell
python simulacion_redisenio_cubo.py
python -m pytest -q
```

Parámetros de alternativas en `parametros_redisenio_cubo.json`; metodología,
fuentes, fórmulas y límites en `metodologia_redisenio_cubo.md`. Resultados CSV,
JSON, requisitos y SHA256 en `resultados/etapa_5e2a/`.

Con agujero Ø38 y chavetero alto candidato b10, los ligamentos son:

| Cubo exterior [mm] | Centro q3,3 / q3,5 [mm] | Esquina ideal q3,3 / q3,5 [mm] |
|---|---:|---:|
| 45 actual | 0,2 / 0,0 | −0,354 / −0,549 |
| 50 escenario | 2,7 / 2,5 | 2,146 / 1,951 |
| 55 escenario | 5,2 / 5,0 | 4,646 / 4,451 |
| 60 escenario | 7,7 / 7,5 | 7,146 / 6,951 |

El actual no contiene la esquina ideal. Los candidatos sí la contienen,
pero **ligamento positivo no acredita resistencia**. Faltan coordenadas CAD
de los ocho aligeramientos Ø13 y extensión axial; no se infieren de píxeles.
La función acepta ocho centros trazables y distingue proyección de interferencia
3D. Los radios de centros de mera tangencia son 29/31,5/34/36,5 mm para
Ø45/50/55/60, no holguras recomendadas ni posiciones existentes.

Se propone **estudiar primero Ø55 en Inventor**, por su posición intermedia
entre reserva y ocupación, no por un factor resistente ni optimización.
Ø50 reduce intervención y Ø60 aumenta reserva pero ocupa más cuerpo.
La elección definitiva requiere interferencias, eje real y verificación local.

Las fuerzas de unión heredadas son 1671,503 N (máximo 3C) y 1906,393 N
(motor nominal ideal), separadas y sin recalcular: ampliar el cubo no cambia
la solicitación de chaveta a igual agujero/torque. Faltan largo activo real,
alturas portantes, tolerancias, radios y materiales para verificar cortante y
aplastamiento. El cubo debilitado se verifica aparte, incluyendo M5 y unión
al cuerpo. AISI 1045 sigue candidato sin propiedades ni factores de seguridad.

Se documentan como alternativas el chavetero bajo del extracto Ganter DIN
6885-2 (requiere modificar y comprobar también el eje) y una familia comercial
de anillos de fricción RINGFEDER RfN 7012 (no autocentrante). Ninguna se declara
equivalente, seleccionada ni aprobada. La compatibilidad Ø38 con el motor
real sigue pendiente de plano/ficha; también el ajuste y retención axial.

Las pruebas cubren frontera Ø38 de la candidata, conversión N·m/N·mm,
fuerzas, ligamentos central/esquina, casos inválidos, sensibilidad a largo,
comprobación de ejes pendientes y conservación SHA256 de etapas anteriores.

## Etapa 5E.2-B — Compatibilidad de motores comerciales

Comparación sin selección ni cambio del motor histórico de 1450 rpm.
Desde `Capstone/Transmision`, ejecutar solo la subetapa nueva:

```powershell
python simulacion_compatibilidad_motor.py
python -m pytest -q
```

Datos transcritos y nulos en `parametros_motores.json`; procedimiento y límites
en `metodologia_compatibilidad_motor.md`. CSV/JSON, requisitos y SHA256 en
`resultados/etapa_5e2b/`. No se regeneran las etapas anteriores.

| Referencia comercial | Eje / extensión | Ancho publicado | rpm nominales | Montaje |
|---|---|---|---:|---|
| BEVI 4AL3 132S-4, 121165 | Ø38 / 80 mm | F10 mm | 1470 | B3/B14 |
| Marathon 6RN132S04E30U24B3641-A | Ø38 / 80 mm | Pendiente | 1475 | B14 |

Fuentes oficiales en `referencias.bib`: BEVI consultada directamente;
Marathon consultada en contenido indexado oficial porque el acceso directo
devuelve HTTP403. Su outline anunciado no fue inspeccionado: solicitarlo al
proveedor antes de confirmar chavetero, hombros o tolerancias. Ambos son
referencias de 5,5 kW, cuatro polos, trifásicos, 50 Hz; ninguno se selecciona.

Ø38 coincide **nominalmente** con ambos. Los 10 mm CAD coinciden con F10
de BEVI; en Marathon no se confirma el ancho por analogía de carcasa.
No hay aprobación de ajuste ni chaveta: faltan tolerancias, altura,
profundidades, radios, longitud activa y materiales. BEVI publica GA41 y
DH M12x28; se conservan como cotas de ficha, sin inferir profundidad o
dimensionar retención automáticamente. La fijación axial Marathon queda pendiente.

La envolvente de cubo de 62 mm es menor que los 80 mm de extensión por
18 mm, condición necesaria, **no holgura instalada ni contacto efectivo**.
Faltan posición del cubo, hombros, radios, chaflanes y retención axial.
El B14 del Marathon no equivale a patas B3: confirmar brida/base y tensado.

Se importan 1169,524 N del máximo 3C condicional y 1171,250 N del motor
nominal ideal histórico como escenarios separados de 5D.2. La capacidad
radial de ambos motores queda **pendiente**: pedir valor/curva y condiciones
de aplicación al fabricante, distancia y referencia axial, rpm, vida,
orientación y rodamientos. Faltan plano resultante de correas, peso y centro
de masa de polea y otras cargas. No se inventan admisibles ni reacciones.
Las sensibilidades de pretensión siguen separadas en su archivo original.

1470/1475 difieren de 1450 por +20/+25 rpm (1,379/1,724 %); no se escalan
ni sobrescriben velocidades, torques, capacidad o tensado previos. Los 1500
rpm del título Marathon no sustituyen sus 1475 rpm nominales publicados.
Las eficiencias eléctricas 89,8/89,6 % no son eficiencias de correas ni
reducen nuevamente los 5,5 kW nominales de salida mecánica. Confirmar además
alimentación/conexión: las fichas publican tensiones distintas.

Se conservan por importación las alternativas Ø50/55/60 y sus ligamentos.
**Puede continuar el predimensionamiento de Ø55, no su aprobación**: faltan
interferencias CAD con los ocho aligeramientos, geometría local, materiales
y resistencia de cubo/chaveta/montaje. Ø45 sigue vigente en CAD y mantiene
la incompatibilidad geométrica detectada. No se cambia la polea conducida,
no se ejecuta FEM y no se asignan factores de seguridad ni motor definitivo.
